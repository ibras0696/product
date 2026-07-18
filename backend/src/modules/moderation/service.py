from collections.abc import Callable
from dataclasses import replace
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from infrastructure.uow import UnitOfWork
from modules.moderation.domain import ModerationSubmission, PublishAction, validate_action
from modules.moderation.exceptions import (
    InvalidModerationTransitionError,
    ModerationConflictError,
    ModerationNotFoundError,
)
from modules.moderation.repository import ModerationRepository, OptimisticWriteError, QueueFilters
from modules.submissions.contracts import SubmissionStatus, SubmissionType


class ModerationRepositoryContract(Protocol):
    async def queue(
        self, filters: QueueFilters, limit: int, offset: int
    ) -> tuple[list[ModerationSubmission], int]: ...
    async def get(
        self, submission_id: UUID, *, lock: bool = False
    ) -> ModerationSubmission | None: ...
    async def transition(
        self,
        current: ModerationSubmission,
        target: SubmissionStatus,
        actor_id: UUID,
        comment: str | None,
    ) -> None: ...
    async def add_claim(self, submission_id: UUID, actor_id: UUID, version: int) -> None: ...
    async def remove_claim(self, submission_id: UUID) -> None: ...
    async def add_decision_audit(
        self, current: ModerationSubmission, actor_id: UUID, action: str, comment: str
    ) -> None: ...


class ModerationUnitOfWorkContract(Protocol):
    @property
    def repository(self) -> ModerationRepositoryContract: ...

    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class ModerationUnitOfWork(UnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.repository = ModerationRepository(self.session)
        return self


UoWFactory = Callable[[], ModerationUnitOfWorkContract]


def create_moderation_uow() -> ModerationUnitOfWorkContract:
    return ModerationUnitOfWork()


class ModerationService:
    def __init__(self, uow_factory: UoWFactory = create_moderation_uow) -> None:
        self._uow_factory = uow_factory

    async def queue(
        self, filters: QueueFilters, limit: int, offset: int
    ) -> tuple[list[ModerationSubmission], int]:
        async with self._uow_factory() as uow:
            return await uow.repository.queue(filters, limit, offset)

    async def details(self, submission_id: UUID) -> ModerationSubmission:
        async with self._uow_factory() as uow:
            return await self._require(uow.repository, submission_id)

    async def claim(
        self, submission_id: UUID, actor_id: UUID, expected_version: int
    ) -> ModerationSubmission:
        try:
            async with self._uow_factory() as uow:
                current = await self._require(uow.repository, submission_id, lock=True)
                self._assert_state(current, expected_version, SubmissionStatus.PENDING)
                await uow.repository.transition(current, SubmissionStatus.IN_REVIEW, actor_id, None)
                await uow.repository.add_claim(submission_id, actor_id, current.version + 1)
                return self._changed(current, SubmissionStatus.IN_REVIEW, actor_id)
        except (IntegrityError, OptimisticWriteError) as exc:
            raise ModerationConflictError("Submission is already claimed") from exc

    async def reject(
        self, submission_id: UUID, actor_id: UUID, expected_version: int, comment: str
    ) -> ModerationSubmission:
        return await self._decide(
            submission_id, actor_id, expected_version, comment, SubmissionStatus.REJECTED
        )

    async def request_revision(
        self, submission_id: UUID, actor_id: UUID, expected_version: int, comment: str
    ) -> ModerationSubmission:
        return await self._decide(
            submission_id, actor_id, expected_version, comment, SubmissionStatus.NEEDS_REVISION
        )

    @staticmethod
    def validate_publish_action(submission_type: SubmissionType, action: PublishAction) -> None:
        try:
            validate_action(submission_type, action)
        except ValueError as exc:
            raise InvalidModerationTransitionError(
                "Publish action does not match submission type"
            ) from exc

    async def _decide(
        self,
        submission_id: UUID,
        actor_id: UUID,
        expected_version: int,
        comment: str,
        target: SubmissionStatus,
    ) -> ModerationSubmission:
        normalized = comment.strip()
        if not normalized:
            raise InvalidModerationTransitionError("Decision comment is required")
        try:
            async with self._uow_factory() as uow:
                current = await self._require(uow.repository, submission_id, lock=True)
                self._assert_state(current, expected_version, SubmissionStatus.IN_REVIEW)
                if current.claimed_by != actor_id:
                    raise ModerationConflictError("Submission is claimed by another moderator")
                await uow.repository.transition(current, target, actor_id, normalized)
                await uow.repository.add_decision_audit(current, actor_id, target.value, normalized)
                await uow.repository.remove_claim(submission_id)
                return self._changed(current, target, None)
        except OptimisticWriteError as exc:
            raise ModerationConflictError("Submission version conflict") from exc

    @staticmethod
    async def _require(
        repository: ModerationRepositoryContract, submission_id: UUID, *, lock: bool = False
    ) -> ModerationSubmission:
        submission = await repository.get(submission_id, lock=lock)
        if submission is None:
            raise ModerationNotFoundError("Submission not found")
        return submission

    @staticmethod
    def _assert_state(
        current: ModerationSubmission, expected_version: int, expected_status: SubmissionStatus
    ) -> None:
        if current.version != expected_version:
            raise ModerationConflictError("Submission version conflict")
        if current.status is not expected_status:
            raise InvalidModerationTransitionError("Submission cannot make this transition")

    @staticmethod
    def _changed(
        current: ModerationSubmission, status: SubmissionStatus, claimed_by: UUID | None
    ) -> ModerationSubmission:
        return replace(current, status=status, version=current.version + 1, claimed_by=claimed_by)
