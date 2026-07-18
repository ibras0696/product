from collections.abc import Iterable
from typing import cast
from uuid import UUID, uuid4

import pytest
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from common.base_model import BaseDBModel
from modules.catalog.contracts import CatalogPublicationAdapter
from modules.catalog.domain import EntityType, PublicationStatus
from modules.catalog.models import Entity, EntityText, Source
from modules.moderation.contracts import PublishAction, PublishCommand
from modules.publication.contracts import CatalogPublicationResult, PublicationSubmission
from modules.submissions.contracts import SubmissionStatus, SubmissionType


class ScalarItems:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def all(self) -> list[object]:
        return self._items


class FakeSession:
    def __init__(self, scalars: list[object] | None = None) -> None:
        self.scalar_results = list(scalars or [])
        self.text_results: list[list[object]] = []
        self.added: list[object] = []

    def add(self, model: object) -> None:
        self.added.append(model)

    def add_all(self, models: Iterable[object]) -> None:
        self.added.extend(list(models))

    async def flush(self) -> None:
        for model in self.added:
            if isinstance(model, BaseDBModel) and model.id is None:
                model.id = uuid4()

    async def scalar(self, _: object) -> object | None:
        return self.scalar_results.pop(0) if self.scalar_results else None

    async def scalars(self, _: object) -> ScalarItems:
        return ScalarItems(self.text_results.pop(0) if self.text_results else [])


def submission(
    submission_type: SubmissionType, related_entity_id: UUID | None = None
) -> PublicationSubmission:
    return PublicationSubmission(
        id=uuid4(),
        type=submission_type,
        status=SubmissionStatus.IN_REVIEW,
        version=3,
        claimed_by=uuid4(),
        related_entity_id=related_entity_id,
    )


def command(action: str, payload: dict[str, object]) -> PublishCommand:
    return TypeAdapter(PublishCommand).validate_python(
        {
            "action": action,
            "expected_version": 3,
            "idempotency_key": str(uuid4()),
            "comment": "Проверено",
            "payload": payload,
        }
    )


def entity_input() -> dict[str, object]:
    text = {"ru": "Башня", "ce": None}
    return {
        "type": "landmark",
        "slug": "tower",
        "title": text,
        "short_description": text,
        "full_description": text,
        "coordinates": None,
        "period_from": None,
        "period_to": None,
        "district_id": None,
    }


def source_input() -> dict[str, object]:
    return {
        "title": "Архив",
        "type": "archive_document",
        "author": None,
        "publisher": None,
        "publication_year": None,
        "url": None,
        "archive_reference": "A-1",
        "description": "Документ",
    }


def relation_input(source_id: object, target_id: object) -> dict[str, object]:
    text = {"ru": "Связь", "ce": None}
    return {
        "source_entity_id": str(source_id),
        "target_entity_id": str(target_id),
        "type": "connected_with",
        "title": text,
        "description": text,
        "period_from": None,
        "period_to": None,
    }


async def publish(
    session: FakeSession, submission_type: SubmissionType, document: PublishCommand
) -> CatalogPublicationResult:
    adapter = CatalogPublicationAdapter(cast(AsyncSession, session))
    return await adapter.publish(submission(submission_type), document.action, document.payload)


@pytest.mark.asyncio
async def test_create_entity_publishes_sources_and_relations() -> None:
    left = Entity(id=uuid4(), type=EntityType.LANDMARK, slug="a", status="published", version=1)
    right = Entity(id=uuid4(), type=EntityType.LANDMARK, slug="b", status="published", version=1)
    session = FakeSession([left, right])
    document = command(
        "create_entity",
        {
            "entity": entity_input(),
            "relations": [relation_input(left.id, right.id)],
            "sources": [source_input()],
            "approved_media_ids": [],
        },
    )
    result = await publish(session, SubmissionType.NEW_ENTITY, document)
    assert len(result.entity_ids) == len(result.relation_ids) == len(result.source_ids) == 1
    assert any(isinstance(item, EntityText) for item in session.added)


@pytest.mark.asyncio
async def test_update_entity_adds_source_and_applies_patch() -> None:
    entity = Entity(id=uuid4(), type=EntityType.LANDMARK, slug="old", status="published", version=2)
    ru = EntityText(
        id=uuid4(),
        entity_id=entity.id,
        locale="ru",
        title="Старое",
        short_description="Старое",
        full_description="Старое",
    )
    session = FakeSession([entity])
    session.text_results = [[ru]]
    document = command(
        "update_entity",
        {
            "entity_id": str(entity.id),
            "entity_patch": {"slug": "new", "title": {"ru": "Новое", "ce": None}},
            "sources": [source_input()],
            "approved_media_ids": [],
        },
    )
    result = await publish(session, SubmissionType.UPDATE_ENTITY, document)
    assert result.entity_ids == (entity.id,)
    assert entity.slug == "new" and entity.version == 3 and ru.title == "Новое"


@pytest.mark.asyncio
async def test_create_relation_and_add_source_target_links() -> None:
    left = Entity(id=uuid4(), type=EntityType.PERSON, slug="a", status="published", version=1)
    right = Entity(id=uuid4(), type=EntityType.PERSON, slug="b", status="published", version=1)
    relation_document = command(
        "create_relation",
        {"relation": relation_input(left.id, right.id), "sources": [source_input()]},
    )
    relation_result = await publish(
        FakeSession([left, right]), SubmissionType.NEW_RELATION, relation_document
    )
    assert len(relation_result.relation_ids) == len(relation_result.source_ids) == 1

    session = FakeSession([left])
    add_document = command(
        "add_source",
        {"target_type": "entity", "target_id": str(left.id), "source": source_input()},
    )
    source_result = await publish(session, SubmissionType.NEW_SOURCE, add_document)
    assert source_result.entity_ids == (left.id,)
    assert isinstance(next(item for item in session.added if isinstance(item, Source)), Source)


@pytest.mark.asyncio
async def test_publish_media_is_catalog_noop_after_target_validation() -> None:
    entity = Entity(id=uuid4(), type=EntityType.PERSON, slug="a", status="published", version=1)
    document = command(
        "publish_media", {"target_entity_id": str(entity.id), "approved_media_ids": [str(uuid4())]}
    )
    result = await publish(FakeSession([entity]), SubmissionType.NEW_MEDIA, document)
    assert result.entity_ids == result.relation_ids == result.source_ids == ()


@pytest.mark.asyncio
async def test_resolve_report_uses_submission_target_for_patch_and_can_archive() -> None:
    target = Entity(
        id=uuid4(), type=EntityType.LANDMARK, slug="before", status="published", version=1
    )
    session = FakeSession([target])
    session.text_results = [[]]
    patch_document = command(
        "resolve_report", {"resolution": "Исправлено", "entity_patch": {"slug": "after"}}
    )
    adapter = CatalogPublicationAdapter(cast(AsyncSession, session))
    result = await adapter.publish(
        submission(SubmissionType.REPORT_ERROR, target.id),
        PublishAction.RESOLVE_REPORT,
        patch_document.payload,
    )
    assert result.entity_ids == (target.id,) and target.slug == "after"

    archive = Entity(
        id=uuid4(), type=EntityType.LANDMARK, slug="archive", status="published", version=1
    )
    archive_document = command(
        "resolve_report",
        {"resolution": "Архивировано", "archive_entity_id": str(archive.id)},
    )
    result = await CatalogPublicationAdapter(cast(AsyncSession, FakeSession([archive]))).publish(
        submission(SubmissionType.REPORT_ERROR),
        PublishAction.RESOLVE_REPORT,
        archive_document.payload,
    )
    assert result.entity_ids == (archive.id,)
    assert archive.status is PublicationStatus.ARCHIVED


@pytest.mark.asyncio
async def test_create_entity_requires_source_and_report_patch_requires_target() -> None:
    empty = command(
        "create_entity",
        {"entity": entity_input(), "relations": [], "sources": [], "approved_media_ids": []},
    )
    with pytest.raises(ValueError):
        await publish(FakeSession(), SubmissionType.NEW_ENTITY, empty)
    report = command("resolve_report", {"resolution": "Исправить", "entity_patch": {"slug": "new"}})
    with pytest.raises(ValueError, match="target"):
        await CatalogPublicationAdapter(cast(AsyncSession, FakeSession())).publish(
            submission(SubmissionType.REPORT_ERROR),
            PublishAction.RESOLVE_REPORT,
            report.payload,
        )
