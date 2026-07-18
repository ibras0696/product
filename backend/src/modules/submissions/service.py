from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from common.exceptions import ApplicationError, ConflictError, NotFoundError
from infrastructure.uow import UnitOfWork
from modules.submissions.capabilities import (
    CapabilityIssuer,
    SubmissionCapabilities,
    SubmissionRateLimiter,
)
from modules.submissions.domain import (
    InvalidTransitionError,
    Submission,
    SubmissionStatus,
    VersionConflictError,
)
from modules.submissions.models import SubmissionModel, SubmissionStatusHistoryModel
from modules.submissions.repository import SubmissionRepository
from modules.submissions.schemas import (
    SubmissionCreate,
    SubmissionDraft,
    SubmissionPatch,
    SubmissionStatusView,
    SubmissionSubmit,
)


class DraftNotEditableError(ApplicationError):
    code = "draft_not_editable"
    status_code = 409


class SubmissionRepositoryContract(Protocol):
    async def add(self, submission: SubmissionModel) -> None: ...

    async def owned(
        self, submission_id: UUID, owner_hash: str, now: datetime
    ) -> SubmissionModel | None: ...

    async def tracked(self, tracking_hash: str) -> SubmissionModel | None: ...

    async def latest_public_comment(self, submission_id: UUID) -> str | None: ...

    async def patch(
        self, submission: SubmissionModel, changes: dict[str, object], expected_version: int
    ) -> None: ...

    async def apply_transition(
        self,
        submission: SubmissionModel,
        status: SubmissionStatus,
        version: int,
        submitted_at: datetime | None,
        history: SubmissionStatusHistoryModel,
    ) -> None: ...


class SubmissionUnitOfWorkContract(Protocol):
    @property
    def repository(self) -> SubmissionRepositoryContract: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class SubmissionUnitOfWork(UnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.repository = SubmissionRepository(self.session)
        return self


UoWFactory = Callable[[], SubmissionUnitOfWorkContract]


class SubmissionService:
    def __init__(
        self,
        uow_factory: UoWFactory,
        capabilities: CapabilityIssuer,
        rate_limiter: SubmissionRateLimiter,
    ) -> None:
        self._uow_factory = uow_factory
        self._capabilities = capabilities
        self._rate_limiter = rate_limiter

    async def create(self, payload: SubmissionCreate, source: str) -> tuple[SubmissionDraft, str]:
        await self._rate_limiter.consume_create(source)
        issued = self._capabilities.issue()
        now = datetime.now(UTC)
        model = SubmissionModel(
            **payload.model_dump(),
            status=SubmissionStatus.DRAFT,
            version=1,
            owner_capability_hash=self._capabilities.owner_hash(issued.owner_secret),
            owner_capability_expires_at=now + timedelta(days=30),
            tracking_code_hash=self._capabilities.tracking_hash(issued.tracking_code),
        )
        async with self._uow_factory() as uow:
            await uow.repository.add(model)
            result = self._draft_view(model, issued.tracking_code)
        return result, issued.cookie_value

    async def patch(
        self, submission_id: UUID, payload: SubmissionPatch, cookie: str | None
    ) -> SubmissionDraft:
        issued = self._require_cookie(cookie)
        async with self._uow_factory() as uow:
            model = await self._require_owned(uow.repository, submission_id, issued)
            self._require_editable(model)
            self._require_version(model, payload.expected_version)
            changes = payload.changes()
            if changes:
                await uow.repository.patch(model, changes, payload.expected_version)
            return self._draft_view(model, issued.tracking_code)

    async def submit(
        self, submission_id: UUID, payload: SubmissionSubmit, cookie: str | None
    ) -> SubmissionStatusView:
        issued = self._require_cookie(cookie)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            model = await self._require_owned(uow.repository, submission_id, issued)
            if model.status is SubmissionStatus.PENDING:
                return self._status_view(model, issued.tracking_code, None)
            self._require_editable(model)
            self._require_complete(model)
            transitioned = self._transition(model, payload.expected_version)
            change = transitioned.history[-1]
            history = SubmissionStatusHistoryModel(
                submission_id=model.id,
                sequence=change.sequence,
                from_status=change.from_status,
                to_status=change.to_status,
            )
            await uow.repository.apply_transition(
                model, transitioned.status, transitioned.version, now, history
            )
            return self._status_view(model, issued.tracking_code, None)

    async def status(self, tracking_code: str, source: str) -> SubmissionStatusView:
        await self._rate_limiter.consume_status(source)
        tracking_hash = self._capabilities.tracking_hash(tracking_code)
        async with self._uow_factory() as uow:
            model = await uow.repository.tracked(tracking_hash)
            if model is None:
                raise NotFoundError("Submission not found")
            comment = await uow.repository.latest_public_comment(model.id)
            return self._status_view(model, tracking_code, comment)

    async def authorize_owner(
        self,
        submission_id: UUID,
        cookie: str | None,
        *,
        editable: bool,
    ) -> None:
        issued = self._require_cookie(cookie)
        async with self._uow_factory() as uow:
            model = await self._require_owned(uow.repository, submission_id, issued)
            if editable:
                self._require_editable(model)

    async def _require_owned(
        self,
        repository: SubmissionRepositoryContract,
        submission_id: UUID,
        issued: SubmissionCapabilities,
    ) -> SubmissionModel:
        owner_hash = self._capabilities.owner_hash(issued.owner_secret)
        model = await repository.owned(submission_id, owner_hash, datetime.now(UTC))
        if model is None:
            raise NotFoundError("Submission not found")
        return model

    @staticmethod
    def _require_cookie(cookie: str | None) -> SubmissionCapabilities:
        issued = CapabilityIssuer.parse_cookie(cookie)
        if issued is None:
            raise NotFoundError("Submission not found")
        return issued

    @staticmethod
    def _require_editable(model: SubmissionModel) -> None:
        if model.status not in {SubmissionStatus.DRAFT, SubmissionStatus.NEEDS_REVISION}:
            raise DraftNotEditableError("Submission is not editable")

    @staticmethod
    def _require_version(model: SubmissionModel, expected_version: int) -> None:
        if model.version != expected_version:
            raise ConflictError("Submission version conflict")

    @staticmethod
    def _require_complete(model: SubmissionModel) -> None:
        required = (
            model.title,
            model.description,
            model.source_description,
            model.author_name,
            model.contact,
        )
        if not model.consent or any(not value.strip() for value in required):
            raise ConflictError("Required fields and consent are needed before submit")

    @staticmethod
    def _transition(model: SubmissionModel, expected_version: int) -> Submission:
        domain = Submission(
            id=model.id,
            type=model.type,
            status=model.status,
            version=model.version,
        )
        try:
            return domain.transition(SubmissionStatus.PENDING, expected_version=expected_version)
        except VersionConflictError as exc:
            raise ConflictError("Submission version conflict") from exc
        except InvalidTransitionError as exc:
            raise DraftNotEditableError("Submission cannot be submitted") from exc

    @staticmethod
    def _draft_view(model: SubmissionModel, tracking_code: str) -> SubmissionDraft:
        return SubmissionDraft(
            **_view_fields(model),
            related_entity_id=model.related_entity_id,
            settlement_id=model.settlement_id,
            description=model.description,
            source_description=model.source_description,
            author_name=model.author_name,
            contact=model.contact,
            consent=model.consent,
            version=model.version,
            tracking_code=tracking_code,
            created_at=model.created_at,
        )

    @staticmethod
    def _status_view(
        model: SubmissionModel, tracking_code: str, public_comment: str | None
    ) -> SubmissionStatusView:
        return SubmissionStatusView(
            **_view_fields(model),
            tracking_code=tracking_code,
            public_comment=public_comment,
            submitted_at=model.submitted_at,
        )


def _view_fields(model: SubmissionModel) -> dict[str, object]:
    return {
        "id": model.id,
        "type": model.type,
        "title": model.title,
        "status": model.status,
        "updated_at": model.updated_at,
    }
