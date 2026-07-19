import asyncio
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from config import get_settings
from infrastructure.uow import UnitOfWork
from modules.media.public import LocalMediaStorage, StorageError
from modules.moderation.domain import (
    ModerationDetails,
    ModerationSubmission,
    PublishAction,
    validate_action,
)
from modules.moderation.exceptions import (
    InvalidModerationTransitionError,
    ModerationConflictError,
    ModerationNotFoundError,
)
from modules.moderation.repository import (
    MediaPreviewRecord,
    ModerationRepository,
    OptimisticWriteError,
    QueueFilters,
)
from modules.submissions.contracts import SubmissionStatus, SubmissionType


class ModerationRepositoryContract(Protocol):
    async def queue(
        self, filters: QueueFilters, limit: int, offset: int
    ) -> tuple[list[ModerationSubmission], int]: ...
    async def get_details(
        self, submission_id: UUID, *, lock: bool = False
    ) -> ModerationDetails | None: ...
    async def get_media_preview(
        self, submission_id: UUID, media_id: UUID
    ) -> MediaPreviewRecord | None: ...
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


class PreviewStorageContract(Protocol):
    def resolve_key(self, key: str) -> Path: ...


PreviewStorageFactory = Callable[[], PreviewStorageContract]


def create_preview_storage() -> PreviewStorageContract:
    return LocalMediaStorage(get_settings().media_storage_root)


@dataclass(frozen=True, slots=True)
class ModerationPreview:
    path: Path
    mime_type: str = "image/webp"


class ModerationService:
    def __init__(
        self,
        uow_factory: UoWFactory = create_moderation_uow,
        preview_storage_factory: PreviewStorageFactory = create_preview_storage,
    ) -> None:
        self._uow_factory = uow_factory
        self._preview_storage_factory = preview_storage_factory

    async def queue(
        self, filters: QueueFilters, limit: int, offset: int
    ) -> tuple[list[ModerationSubmission], int]:
        async with self._uow_factory() as uow:
            return await uow.repository.queue(filters, limit, offset)

    async def details(self, submission_id: UUID) -> ModerationDetails:
        async with self._uow_factory() as uow:
            return await self._require(uow.repository, submission_id)

    async def preview(self, submission_id: UUID, media_id: UUID) -> ModerationPreview:
        async with self._uow_factory() as uow:
            record = await uow.repository.get_media_preview(submission_id, media_id)
        if record is None:
            raise ModerationNotFoundError("Submission media not found")
        try:
            path = self._preview_storage_factory().resolve_key(record.preview_key)
        except StorageError as exc:
            raise ModerationNotFoundError("Submission media not found") from exc
        if not await asyncio.to_thread(path.is_file):
            raise ModerationNotFoundError("Submission media not found")
        return ModerationPreview(path)

    async def claim(
        self, submission_id: UUID, actor_id: UUID, expected_version: int
    ) -> ModerationDetails:
        try:
            async with self._uow_factory() as uow:
                details = await self._require(uow.repository, submission_id, lock=True)
                current = details.submission
                self._assert_state(current, expected_version, SubmissionStatus.PENDING)
                await uow.repository.transition(current, SubmissionStatus.IN_REVIEW, actor_id, None)
                await uow.repository.add_claim(submission_id, actor_id, current.version + 1)
                return replace(
                    details,
                    submission=self._changed(current, SubmissionStatus.IN_REVIEW, actor_id),
                )
        except (IntegrityError, OptimisticWriteError) as exc:
            raise ModerationConflictError("Submission is already claimed") from exc

    async def reject(
        self, submission_id: UUID, actor_id: UUID, expected_version: int, comment: str
    ) -> ModerationDetails:
        return await self._decide(
            submission_id, actor_id, expected_version, comment, SubmissionStatus.REJECTED
        )

    async def request_revision(
        self, submission_id: UUID, actor_id: UUID, expected_version: int, comment: str
    ) -> ModerationDetails:
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
    ) -> ModerationDetails:
        normalized = comment.strip()
        if not normalized:
            raise InvalidModerationTransitionError("Decision comment is required")
        try:
            async with self._uow_factory() as uow:
                details = await self._require(uow.repository, submission_id, lock=True)
                current = details.submission
                self._assert_state(current, expected_version, SubmissionStatus.IN_REVIEW)
                if current.claimed_by != actor_id:
                    raise ModerationConflictError("Submission is claimed by another moderator")
                await uow.repository.transition(current, target, actor_id, normalized)
                await uow.repository.add_decision_audit(current, actor_id, target.value, normalized)
                await uow.repository.remove_claim(submission_id)
                return replace(details, submission=self._changed(current, target, None))
        except OptimisticWriteError as exc:
            raise ModerationConflictError("Submission version conflict") from exc

    @staticmethod
    async def _require(
        repository: ModerationRepositoryContract, submission_id: UUID, *, lock: bool = False
    ) -> ModerationDetails:
        details = await repository.get_details(submission_id, lock=lock)
        if details is None:
            raise ModerationNotFoundError("Submission not found")
        return details

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
