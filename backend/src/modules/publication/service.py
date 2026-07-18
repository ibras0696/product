import hashlib
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from modules.moderation.contracts import PublishAction, PublishCommand, validate_action
from modules.publication.domain import (
    CatalogPublicationResult,
    PublicationAuditInput,
    PublicationSubmission,
    StoredPublication,
)
from modules.publication.exceptions import (
    IdempotencyConflictError,
    InvalidPublicationTransitionError,
    PublicationConflictError,
    PublicationNotFoundError,
)
from modules.publication.schemas import PublishResult
from modules.submissions.contracts import SubmissionStatus

AfterCommitHook = Callable[[], Awaitable[None]]


class PublicationRepositoryPort(Protocol):
    async def find(self, idempotency_key: UUID) -> StoredPublication | None: ...
    async def add(self, idempotency_key: UUID, publication: StoredPublication) -> None: ...


class SubmissionPublicationPort(Protocol):
    async def lock(self, submission_id: UUID) -> PublicationSubmission | None: ...
    async def mark_published(
        self, submission: PublicationSubmission, actor_id: UUID, comment: str
    ) -> None: ...


class CatalogPublicationPort(Protocol):
    async def publish(
        self,
        submission: PublicationSubmission,
        action: PublishAction,
        payload: BaseModel,
    ) -> CatalogPublicationResult: ...


class MediaPublicationPort(Protocol):
    async def publish(
        self,
        submission_id: UUID,
        action: PublishAction,
        payload: BaseModel,
        catalog: CatalogPublicationResult,
    ) -> tuple[UUID, ...]: ...


class AuditPublicationPort(Protocol):
    async def record_publication(self, audit: PublicationAuditInput) -> UUID: ...


class InvalidationPort(Protocol):
    async def invalidate_public_catalog(self) -> None: ...


class PublicationUnitOfWork(Protocol):
    @property
    def publications(self) -> PublicationRepositoryPort: ...

    @property
    def submissions(self) -> SubmissionPublicationPort: ...

    @property
    def catalog(self) -> CatalogPublicationPort: ...

    @property
    def media(self) -> MediaPublicationPort: ...

    @property
    def audit(self) -> AuditPublicationPort: ...

    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def after_commit(self, hook: AfterCommitHook) -> None: ...


UoWFactory = Callable[[], PublicationUnitOfWork]


class PublicationService:
    def __init__(self, uow_factory: UoWFactory, invalidation: InvalidationPort) -> None:
        self._uow_factory = uow_factory
        self._invalidation = invalidation

    async def publish(
        self,
        submission_id: UUID,
        actor_id: UUID,
        command: PublishCommand,
    ) -> PublishResult:
        request_hash = _command_hash(command)
        try:
            async with self._uow_factory() as uow:
                replay = await uow.publications.find(command.idempotency_key)
                if replay is not None:
                    uow.after_commit(self._invalidation.invalidate_public_catalog)
                    return self._replay(replay, submission_id, actor_id, request_hash)
                submission = await self._require_submission(uow, submission_id)
                self._validate_submission(submission, actor_id, command)
                try:
                    catalog = await uow.catalog.publish(submission, command.action, command.payload)
                except ValueError as exc:
                    raise InvalidPublicationTransitionError(
                        "Publication payload violates catalog invariants"
                    ) from exc
                media_ids = await uow.media.publish(
                    submission_id, command.action, command.payload, catalog
                )
                audit_id = await uow.audit.record_publication(
                    PublicationAuditInput(
                        submission_id=submission_id,
                        actor_id=actor_id,
                        action=command.action,
                        from_version=submission.version,
                        request_hash=request_hash,
                        comment=command.comment.strip(),
                        catalog=catalog,
                        media_ids=media_ids,
                    )
                )
                await uow.submissions.mark_published(submission, actor_id, command.comment.strip())
                result = _result(submission_id, command.action, catalog, media_ids, audit_id)
                await uow.publications.add(
                    command.idempotency_key,
                    StoredPublication(
                        submission_id=submission_id,
                        actor_id=actor_id,
                        request_hash=request_hash,
                        result=result.model_dump(mode="json"),
                    ),
                )
                uow.after_commit(self._invalidation.invalidate_public_catalog)
                return result
        except IntegrityError as exc:
            return await self._recover_concurrent_replay(
                submission_id, actor_id, command, request_hash, exc
            )

    async def _recover_concurrent_replay(
        self,
        submission_id: UUID,
        actor_id: UUID,
        command: PublishCommand,
        request_hash: str,
        original_error: IntegrityError,
    ) -> PublishResult:
        async with self._uow_factory() as uow:
            stored = await uow.publications.find(command.idempotency_key)
            if stored is None:
                raise PublicationConflictError(
                    "Concurrent publication conflict"
                ) from original_error
            return self._replay(stored, submission_id, actor_id, request_hash)

    @staticmethod
    async def _require_submission(
        uow: PublicationUnitOfWork, submission_id: UUID
    ) -> PublicationSubmission:
        submission = await uow.submissions.lock(submission_id)
        if submission is None:
            raise PublicationNotFoundError("Submission not found")
        return submission

    @staticmethod
    def _validate_submission(
        submission: PublicationSubmission,
        actor_id: UUID,
        command: PublishCommand,
    ) -> None:
        if submission.version != command.expected_version:
            raise PublicationConflictError("Submission version conflict")
        if submission.status is not SubmissionStatus.IN_REVIEW:
            raise InvalidPublicationTransitionError("Submission is not in review")
        if submission.claimed_by != actor_id:
            raise PublicationConflictError("Submission is claimed by another moderator")
        try:
            validate_action(submission.type, command.action)
        except ValueError as exc:
            raise InvalidPublicationTransitionError(
                "Publish action does not match submission type"
            ) from exc

    @staticmethod
    def _replay(
        stored: StoredPublication,
        submission_id: UUID,
        actor_id: UUID,
        request_hash: str,
    ) -> PublishResult:
        if (
            stored.submission_id != submission_id
            or stored.actor_id != actor_id
            or stored.request_hash != request_hash
        ):
            raise IdempotencyConflictError("Idempotency key was used for another request")
        return PublishResult.model_validate(stored.result)


def _command_hash(command: PublishCommand) -> str:
    serialized = command.model_dump_json(exclude={"idempotency_key"})
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _result(
    submission_id: UUID,
    action: PublishAction,
    catalog: CatalogPublicationResult,
    media_ids: tuple[UUID, ...],
    audit_id: UUID,
) -> PublishResult:
    return PublishResult(
        submission_id=submission_id,
        action=action,
        published_entity_ids=list(catalog.entity_ids),
        published_relation_ids=list(catalog.relation_ids),
        published_source_ids=list(catalog.source_ids),
        published_media_ids=list(media_ids),
        audit_id=audit_id,
    )
