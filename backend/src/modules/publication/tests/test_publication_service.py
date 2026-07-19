from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, TypeAdapter

from modules.moderation.contracts import PublishAction, PublishCommand
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
)
from modules.publication.service import AfterCommitHook, PublicationService
from modules.submissions.contracts import SubmissionStatus, SubmissionType


def command(*, key: UUID | None = None, comment: str = "Проверено") -> PublishCommand:
    document = {
        "expected_version": 3,
        "idempotency_key": str(key or uuid4()),
        "action": "create_entity",
        "payload": {
            "entity": {
                "type": "person",
                "slug": "person-name",
                "title": {"ru": "Имя", "ce": None},
                "short_description": {"ru": "Кратко", "ce": None},
                "full_description": {"ru": "Описание", "ce": None},
                "coordinates": None,
                "period_from": None,
                "period_to": None,
            },
            "relations": [],
            "sources": [
                {
                    "title": "Книга",
                    "type": "book",
                    "author": None,
                    "publisher": None,
                    "publication_year": None,
                    "url": None,
                    "archive_reference": None,
                    "description": "Проверенный источник",
                }
            ],
            "approved_media_ids": [],
        },
        "comment": comment,
    }
    return TypeAdapter(PublishCommand).validate_python(document)


class FakeInvalidation:
    def __init__(self) -> None:
        self.calls = 0

    async def invalidate_public_catalog(self) -> None:
        self.calls += 1


class FakeUoW:
    def __init__(
        self,
        submission: PublicationSubmission,
        records: dict[UUID, StoredPublication] | None = None,
        fail_on: str | None = None,
    ) -> None:
        self.submission = submission
        self.records = records if records is not None else {}
        self.fail_on = fail_on
        self.publications = FakePublications(self)
        self.submissions = FakeSubmissions(self)
        self.catalog = FakeCatalog(self)
        self.media = FakeMedia(self)
        self.audit = FakeAudit(self)
        self.staged: list[str] = []
        self.committed: list[str] = []
        self.hooks: list[AfterCommitHook] = []
        self.rolled_back = False
        self._record_snapshot: dict[UUID, StoredPublication] = {}

    async def __aenter__(self) -> Self:
        self._record_snapshot = dict(self.records)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc, traceback
        if exc_type is not None or self.fail_on == "commit":
            self.rolled_back = True
            self.records.clear()
            self.records.update(self._record_snapshot)
            self.staged.clear()
            if exc_type is None:
                raise RuntimeError("commit failed")
            return
        self.committed.extend(self.staged)
        for hook in self.hooks:
            await hook()

    def after_commit(self, hook: AfterCommitHook) -> None:
        self.hooks.append(hook)

    def step(self, name: str) -> None:
        if self.fail_on == name:
            raise RuntimeError(f"{name} failed")
        self.staged.append(name)


class FakePublications:
    def __init__(self, uow: FakeUoW) -> None:
        self.uow = uow

    async def find(self, idempotency_key: UUID) -> StoredPublication | None:
        return self.uow.records.get(idempotency_key)

    async def add(self, idempotency_key: UUID, publication: StoredPublication) -> None:
        self.uow.step("idempotency")
        self.uow.records[idempotency_key] = publication


class FakeSubmissions:
    def __init__(self, uow: FakeUoW) -> None:
        self.uow = uow

    async def lock(self, submission_id: UUID) -> PublicationSubmission | None:
        return self.uow.submission if self.uow.submission.id == submission_id else None

    async def mark_published(
        self, submission: PublicationSubmission, actor_id: UUID, comment: str
    ) -> None:
        del submission, actor_id, comment
        self.uow.step("submission")


class FakeCatalog:
    def __init__(self, uow: FakeUoW) -> None:
        self.uow = uow
        self.entity_id = uuid4()

    async def publish(
        self,
        submission: PublicationSubmission,
        action: PublishAction,
        payload: BaseModel,
    ) -> CatalogPublicationResult:
        del submission, action, payload
        self.uow.step("catalog")
        return CatalogPublicationResult(entity_ids=(self.entity_id,))


class FakeMedia:
    def __init__(self, uow: FakeUoW) -> None:
        self.uow = uow

    async def publish(
        self,
        submission_id: UUID,
        action: PublishAction,
        payload: BaseModel,
        catalog: CatalogPublicationResult,
    ) -> tuple[UUID, ...]:
        del submission_id, action, payload, catalog
        self.uow.step("media")
        return ()


class FakeAudit:
    def __init__(self, uow: FakeUoW) -> None:
        self.uow = uow
        self.audit_id = uuid4()

    async def record_publication(self, audit: PublicationAuditInput) -> UUID:
        del audit
        self.uow.step("audit")
        return self.audit_id


def reviewed_submission(actor_id: UUID) -> PublicationSubmission:
    return PublicationSubmission(
        id=uuid4(),
        type=SubmissionType.NEW_ENTITY,
        status=SubmissionStatus.IN_REVIEW,
        version=3,
        claimed_by=actor_id,
    )


async def test_atomic_publish_returns_result_and_invalidates_only_after_commit() -> None:
    actor_id = uuid4()
    uow = FakeUoW(reviewed_submission(actor_id))
    invalidation = FakeInvalidation()

    result = await PublicationService(lambda: uow, invalidation).publish(
        uow.submission.id, actor_id, command()
    )

    assert result.status == "published"
    assert result.published_entity_ids == [uow.catalog.entity_id]
    assert result.audit_id == uow.audit.audit_id
    assert uow.committed == ["catalog", "media", "audit", "submission", "idempotency"]
    assert len(uow.hooks) == 1
    assert invalidation.calls == 1


@pytest.mark.parametrize(
    "failure", ["catalog", "media", "audit", "submission", "idempotency", "commit"]
)
async def test_each_publication_failure_rolls_back_everything_and_emits_no_hook(
    failure: str,
) -> None:
    actor_id = uuid4()
    uow = FakeUoW(reviewed_submission(actor_id), fail_on=failure)
    invalidation = FakeInvalidation()

    with pytest.raises(RuntimeError, match="failed"):
        await PublicationService(lambda: uow, invalidation).publish(
            uow.submission.id, actor_id, command()
        )

    assert uow.rolled_back
    assert uow.committed == []
    assert uow.records == {}
    assert invalidation.calls == 0


async def test_same_idempotency_request_replays_result_without_new_writes() -> None:
    actor_id = uuid4()
    key = uuid4()
    records: dict[UUID, StoredPublication] = {}
    first_uow = FakeUoW(reviewed_submission(actor_id), records)
    invalidation = FakeInvalidation()
    publication = PublicationService(lambda: first_uow, invalidation)
    first = await publication.publish(first_uow.submission.id, actor_id, command(key=key))

    replay_uow = FakeUoW(first_uow.submission, records)
    replayed = await PublicationService(lambda: replay_uow, invalidation).publish(
        replay_uow.submission.id, actor_id, command(key=key)
    )

    assert replayed == first
    assert replay_uow.staged == []
    assert invalidation.calls == 2


async def test_same_key_with_different_payload_conflicts() -> None:
    actor_id = uuid4()
    key = uuid4()
    records: dict[UUID, StoredPublication] = {}
    first_uow = FakeUoW(reviewed_submission(actor_id), records)
    await PublicationService(lambda: first_uow, FakeInvalidation()).publish(
        first_uow.submission.id, actor_id, command(key=key)
    )

    replay_uow = FakeUoW(first_uow.submission, records)
    with pytest.raises(IdempotencyConflictError) as error:
        await PublicationService(lambda: replay_uow, FakeInvalidation()).publish(
            replay_uow.submission.id,
            actor_id,
            command(key=key, comment="Другой результат"),
        )
    assert error.value.code == "idempotency_conflict"


@pytest.mark.parametrize("violation", ["version", "status", "owner", "action"])
async def test_lock_version_status_owner_and_action_are_enforced(violation: str) -> None:
    actor_id = uuid4()
    submission = reviewed_submission(actor_id)
    publish_command = command()
    error_type: type[Exception]
    if violation == "version":
        submission = PublicationSubmission(
            submission.id, submission.type, submission.status, 4, submission.claimed_by
        )
        error_type = PublicationConflictError
    elif violation == "status":
        submission = PublicationSubmission(
            submission.id, submission.type, SubmissionStatus.PENDING, 3, submission.claimed_by
        )
        error_type = InvalidPublicationTransitionError
    elif violation == "owner":
        submission = PublicationSubmission(
            submission.id, submission.type, submission.status, 3, uuid4()
        )
        error_type = PublicationConflictError
    else:
        submission = PublicationSubmission(
            submission.id,
            SubmissionType.NEW_RELATION,
            submission.status,
            3,
            submission.claimed_by,
        )
        error_type = InvalidPublicationTransitionError

    with pytest.raises(error_type):
        await PublicationService(lambda: FakeUoW(submission), FakeInvalidation()).publish(
            submission.id, actor_id, publish_command
        )
