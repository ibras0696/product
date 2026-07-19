from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from common.exceptions import ConflictError, NotFoundError
from modules.submissions.capabilities import CapabilityIssuer, SubmissionCapabilities
from modules.submissions.domain import SubmissionStatus, SubmissionType
from modules.submissions.models import SubmissionModel, SubmissionStatusHistoryModel
from modules.submissions.schemas import SubmissionCreate, SubmissionPatch, SubmissionSubmit
from modules.submissions.service import SubmissionService


class FixedIssuer(CapabilityIssuer):
    @staticmethod
    def issue() -> SubmissionCapabilities:
        return SubmissionCapabilities("o" * 43, "t" * 43)


class AllowingLimiter:
    async def consume_create(self, source: str) -> None:
        pass

    async def consume_status(self, source: str) -> None:
        pass


class FakeRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, SubmissionModel] = {}
        self.comments: dict[UUID, str] = {}

    async def add(self, model: SubmissionModel) -> None:
        now = datetime.now(UTC)
        model.id = uuid4()
        model.created_at = now
        model.updated_at = now
        self.items[model.id] = model

    async def owned(
        self, submission_id: UUID, owner_hash: str, now: datetime
    ) -> SubmissionModel | None:
        model = self.items.get(submission_id)
        if model is None:
            return None
        if model.owner_capability_hash != owner_hash or model.owner_capability_expires_at <= now:
            return None
        return model

    async def tracked(self, tracking_hash: str) -> SubmissionModel | None:
        return next(
            (item for item in self.items.values() if item.tracking_code_hash == tracking_hash), None
        )

    async def latest_public_comment(self, submission_id: UUID) -> str | None:
        return self.comments.get(submission_id)

    async def patch(
        self, model: SubmissionModel, changes: dict[str, object], expected_version: int
    ) -> None:
        for field, value in changes.items():
            setattr(model, field, value)
        model.version = expected_version + 1
        model.updated_at = datetime.now(UTC)

    async def apply_transition(
        self,
        model: SubmissionModel,
        status: SubmissionStatus,
        version: int,
        submitted_at: datetime | None,
        history: SubmissionStatusHistoryModel,
    ) -> None:
        model.status = status
        model.version = version
        model.submitted_at = submitted_at
        model.updated_at = datetime.now(UTC)


class FakeUnitOfWork:
    def __init__(self, repository: FakeRepository) -> None:
        self.repository = repository

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, *_: object) -> None:
        pass


def service(repository: FakeRepository) -> SubmissionService:
    return SubmissionService(lambda: FakeUnitOfWork(repository), FixedIssuer(), AllowingLimiter())


def create_payload() -> SubmissionCreate:
    return SubmissionCreate(
        type=SubmissionType.NEW_ENTITY,
        related_entity_id=None,
        settlement_id=None,
        title="История",
        description="Описание",
        source_description="Архив",
        author_name="Автор",
        contact="author@example.com",
        consent=True,
    )


@pytest.mark.asyncio
async def test_owner_can_patch_and_attacker_or_guessed_uuid_cannot() -> None:
    repository = FakeRepository()
    api = service(repository)
    draft, cookie = await api.create(create_payload(), "source")

    changed = await api.patch(
        draft.id,
        SubmissionPatch(expected_version=1, title="Исправленная история"),
        cookie,
    )
    assert changed.title == "Исправленная история"
    assert changed.version == 2
    with pytest.raises(NotFoundError):
        await api.patch(draft.id, SubmissionPatch(expected_version=2), f"{'a' * 43}.{'b' * 43}")
    with pytest.raises(NotFoundError):
        await api.patch(uuid4(), SubmissionPatch(expected_version=2), cookie)


@pytest.mark.asyncio
async def test_invalid_tracking_and_expired_owner_capability_are_indistinguishable() -> None:
    repository = FakeRepository()
    api = service(repository)
    draft, cookie = await api.create(create_payload(), "source")
    repository.items[draft.id].owner_capability_expires_at = datetime.now(UTC) - timedelta(
        seconds=1
    )

    with pytest.raises(NotFoundError):
        await api.patch(draft.id, SubmissionPatch(expected_version=1), cookie)
    with pytest.raises(NotFoundError):
        await api.status("x" * 43, "source")


@pytest.mark.asyncio
async def test_submit_is_replay_safe_and_revision_supports_partial_patch() -> None:
    repository = FakeRepository()
    api = service(repository)
    draft, cookie = await api.create(create_payload(), "source")

    first = await api.submit(draft.id, SubmissionSubmit(expected_version=1), cookie)
    replay = await api.submit(draft.id, SubmissionSubmit(expected_version=1), cookie)
    assert first.status is SubmissionStatus.PENDING
    assert replay == first

    model = repository.items[draft.id]
    model.status = SubmissionStatus.NEEDS_REVISION
    model.version = 3
    changed = await api.patch(
        draft.id,
        SubmissionPatch(expected_version=3, source_description="Новый источник"),
        cookie,
    )
    assert changed.description == "Описание"
    assert changed.source_description == "Новый источник"
    second = await api.submit(draft.id, SubmissionSubmit(expected_version=4), cookie)
    assert second.status is SubmissionStatus.PENDING


@pytest.mark.asyncio
async def test_submit_requires_consent_and_complete_fields() -> None:
    repository = FakeRepository()
    api = service(repository)
    payload = create_payload().model_copy(update={"consent": False})
    draft, cookie = await api.create(payload, "source")
    with pytest.raises(ConflictError):
        await api.submit(draft.id, SubmissionSubmit(expected_version=1), cookie)
