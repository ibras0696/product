from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.exceptions import ConflictError, ForbiddenError, register_exception_handlers
from middleware.request_context import request_context
from modules.auth.public import AdminAccount, Permission, get_auth_context
from modules.catalog.admin_repository import EditableEntity
from modules.catalog.admin_routes import get_admin_catalog_service, router
from modules.catalog.admin_schemas import (
    AdminEntity,
    AdminEntityCreate,
    AdminEntityPage,
    AdminEntityPatch,
    AdminRelation,
    AdminRelationCreate,
    AdminRelationPage,
    AdminRelationPatch,
    AdminSource,
    AdminSourceCreate,
    AdminSourcePage,
    AdminSourcePatch,
    LocalizedText,
    PageMeta,
)
from modules.catalog.admin_service import AdminCatalogService, SourceRequiredError
from modules.catalog.domain import (
    EntityType,
    PublicationStatus,
    RelationType,
    SourceType,
)
from modules.catalog.models import Entity, EntityText, Relation, Source


class FakeAudit:
    def __init__(self) -> None:
        self.actions: list[tuple[str, UUID, int]] = []

    async def record(self, **values: object) -> None:
        version = values["version"]
        assert isinstance(version, int)
        self.actions.append((str(values["action"]), UUID(str(values["resource_id"])), version))


class FakeRepository:
    def __init__(self) -> None:
        self.entities: dict[UUID, EditableEntity] = {}
        self.relations: dict[UUID, Relation] = {}
        self.sources: dict[UUID, Source] = {}
        self.has_verified_source = False

    async def list_entities(self, **values: object) -> AdminEntityPage:
        limit, offset = values["limit"], values["offset"]
        assert isinstance(limit, int)
        assert isinstance(offset, int)
        items = [self._view(item) for item in self.entities.values()]
        return AdminEntityPage(
            items=items[offset : offset + limit],
            meta=PageMeta(limit=limit, offset=offset, total=len(items)),
        )

    async def create_entity(self, payload: AdminEntityCreate) -> Entity:
        entity = Entity(
            id=uuid4(),
            type=payload.type,
            slug=payload.slug,
            status=payload.status,
            version=1,
            coordinate=None,
            period_from=payload.period_from,
            period_to=payload.period_to,
            district_id=payload.district_id,
        )
        texts = {
            "ru": EntityText(
                id=uuid4(),
                entity_id=entity.id,
                locale="ru",
                title=payload.title.ru,
                short_description=payload.short_description.ru,
                full_description=payload.full_description.ru,
            )
        }
        self.entities[entity.id] = EditableEntity(entity, texts)
        return entity

    async def get_entity(self, entity_id: UUID) -> AdminEntity | None:
        editable = self.entities.get(entity_id)
        return self._view(editable) if editable else None

    async def editable_entity(self, entity_id: UUID) -> EditableEntity | None:
        return self.entities.get(entity_id)

    async def update_entity(
        self, editable: EditableEntity, changes: dict[str, object], next_version: int
    ) -> None:
        for field in ("slug", "period_from", "period_to", "district_id", "status"):
            if field in changes:
                setattr(editable.entity, field, changes[field])
        title = changes.get("title")
        if isinstance(title, LocalizedText):
            editable.texts["ru"].title = title.ru
        editable.entity.version = next_version

    async def verified_source_exists(self, entity_id: UUID) -> bool:
        return self.has_verified_source

    async def active_entities_exist(self, entity_ids: tuple[UUID, UUID]) -> bool:
        return True

    async def list_relations(self, **values: object) -> AdminRelationPage:
        limit, offset = _bounds(values)
        items = [self._relation_view(item) for item in self.relations.values()]
        return AdminRelationPage(
            items=items[offset : offset + limit],
            meta=PageMeta(limit=limit, offset=offset, total=len(items)),
        )

    async def create_relation(self, payload: AdminRelationCreate) -> Relation:
        model = Relation(
            id=uuid4(),
            source_entity_id=payload.source_entity_id,
            target_entity_id=payload.target_entity_id,
            type=payload.type,
            title_ru=payload.title.ru,
            title_ce=payload.title.ce,
            description_ru=payload.description.ru,
            description_ce=payload.description.ce,
            period_from=payload.period_from,
            period_to=payload.period_to,
            status=payload.status,
            version=1,
        )
        self.relations[model.id] = model
        return model

    async def editable_relation(self, relation_id: UUID) -> Relation | None:
        return self.relations.get(relation_id)

    async def get_relation(self, relation_id: UUID) -> AdminRelation | None:
        model = self.relations.get(relation_id)
        return self._relation_view(model) if model else None

    async def update_relation(
        self, model: Relation, changes: dict[str, object], next_version: int
    ) -> None:
        for field, value in changes.items():
            if field not in {"title", "description"}:
                setattr(model, field, value)
        model.version = next_version

    async def relation_has_verified_source(self, relation_id: UUID) -> bool:
        return self.has_verified_source

    async def list_sources(self, **values: object) -> AdminSourcePage:
        limit, offset = _bounds(values)
        items = [self._source_view(item) for item in self.sources.values()]
        return AdminSourcePage(
            items=items[offset : offset + limit],
            meta=PageMeta(limit=limit, offset=offset, total=len(items)),
        )

    async def create_source(self, payload: AdminSourceCreate) -> Source:
        model = Source(id=uuid4(), **payload.model_dump(exclude={"expected_version"}), version=1)
        self.sources[model.id] = model
        return model

    async def editable_source(self, source_id: UUID) -> Source | None:
        return self.sources.get(source_id)

    async def get_source(self, source_id: UUID) -> AdminSource | None:
        model = self.sources.get(source_id)
        return self._source_view(model) if model else None

    async def update_source(
        self, model: Source, changes: dict[str, object], next_version: int
    ) -> None:
        for field, value in changes.items():
            setattr(model, field, value)
        model.version = next_version

    @staticmethod
    def _view(editable: EditableEntity) -> AdminEntity:
        entity, ru = editable.entity, editable.texts["ru"]
        return AdminEntity(
            id=entity.id,
            type=entity.type,
            slug=entity.slug,
            title=LocalizedText(ru=ru.title, ce=None),
            short_description=LocalizedText(ru=ru.short_description, ce=None),
            full_description=LocalizedText(ru=ru.full_description, ce=None),
            coordinates=None,
            period_from=entity.period_from,
            period_to=entity.period_to,
            district_id=entity.district_id,
            status=entity.status,
            version=entity.version,
            relations_count=0,
            sources_count=0,
            media_count=0,
        )

    @staticmethod
    def _relation_view(model: Relation) -> AdminRelation:
        return AdminRelation(
            id=model.id,
            source_entity_id=model.source_entity_id,
            target_entity_id=model.target_entity_id,
            type=model.type,
            title=LocalizedText(ru=model.title_ru, ce=model.title_ce),
            description=LocalizedText(ru=model.description_ru, ce=model.description_ce),
            period_from=model.period_from,
            period_to=model.period_to,
            status=model.status,
            version=model.version,
        )

    @staticmethod
    def _source_view(model: Source) -> AdminSource:
        return AdminSource(
            id=model.id,
            title=model.title,
            type=model.type,
            author=model.author,
            publisher=model.publisher,
            publication_year=model.publication_year,
            url=model.url,
            archive_reference=model.archive_reference,
            description=model.description,
            is_verified=model.is_verified,
            status=model.status,
            version=model.version,
        )


class FakeUoW:
    def __init__(self, repository: FakeRepository, audit: FakeAudit) -> None:
        self.repository = repository
        self.audit = audit

    async def __aenter__(self) -> "FakeUoW":
        return self

    async def __aexit__(self, *_: object) -> None:
        pass


def _bounds(values: dict[str, object]) -> tuple[int, int]:
    limit, offset = values["limit"], values["offset"]
    assert isinstance(limit, int)
    assert isinstance(offset, int)
    return limit, offset


def payload() -> AdminEntityCreate:
    text = LocalizedText(ru="Башня", ce=None)
    return AdminEntityCreate(
        type=EntityType.LANDMARK,
        slug="historical-tower",
        title=text,
        short_description=text,
        full_description=text,
        coordinates=None,
        period_from=1800,
        period_to=1900,
        district_id=None,
    )


@pytest.mark.asyncio
async def test_entity_create_update_archive_are_versioned_and_audited() -> None:
    repository, audit, actor = FakeRepository(), FakeAudit(), uuid4()
    service = AdminCatalogService(lambda: FakeUoW(repository, audit))

    created = await service.create_entity(payload(), actor)
    updated = await service.update_entity(
        created.id,
        AdminEntityPatch(expected_version=1, title=LocalizedText(ru="Обновлённая башня", ce=None)),
        actor,
    )
    await service.archive_entity(created.id, expected_version=2, actor_id=actor)

    assert updated.version == 2
    assert repository.entities[created.id].entity.status is PublicationStatus.ARCHIVED
    assert audit.actions == [
        ("catalog.entity.create", created.id, 1),
        ("catalog.entity.update", created.id, 2),
        ("catalog.entity.archive", created.id, 3),
    ]


@pytest.mark.asyncio
async def test_stale_version_and_publish_without_verified_source_are_rejected() -> None:
    repository, audit = FakeRepository(), FakeAudit()
    service = AdminCatalogService(lambda: FakeUoW(repository, audit))
    created = await service.create_entity(payload(), uuid4())

    with pytest.raises(ConflictError):
        await service.update_entity(
            created.id, AdminEntityPatch(expected_version=9, slug="stale"), uuid4()
        )
    with pytest.raises(SourceRequiredError):
        await service.update_entity(
            created.id,
            AdminEntityPatch(expected_version=1, status=PublicationStatus.PUBLISHED),
            uuid4(),
        )
    assert audit.actions == [("catalog.entity.create", created.id, 1)]


@pytest.mark.asyncio
async def test_relation_and_source_crud_are_bounded_versioned_and_audited() -> None:
    repository, audit, actor = FakeRepository(), FakeAudit(), uuid4()
    service = AdminCatalogService(lambda: FakeUoW(repository, audit))
    text = LocalizedText(ru="Связь", ce=None)
    relation = await service.create_relation(
        AdminRelationCreate(
            source_entity_id=uuid4(),
            target_entity_id=uuid4(),
            type=RelationType.CONNECTED_WITH,
            title=text,
            description=text,
            period_from=None,
            period_to=None,
        ),
        actor,
    )
    relation = await service.update_relation(
        relation.id,
        AdminRelationPatch(expected_version=1, type=RelationType.DESCRIBED_IN),
        actor,
    )
    with pytest.raises(ConflictError):
        await service.update_relation(
            relation.id,
            AdminRelationPatch(expected_version=1, type=RelationType.PART_OF),
            actor,
        )
    await service.archive_relation(relation.id, relation.version, actor)

    source = await service.create_source(
        AdminSourceCreate(
            title="Архив",
            type=SourceType.ARCHIVE_DOCUMENT,
            author=None,
            publisher=None,
            publication_year=None,
            url=None,
            archive_reference="A-1",
            description="Описание",
            is_verified=True,
            status=PublicationStatus.PUBLISHED,
        ),
        actor,
    )
    source = await service.update_source(
        source.id, AdminSourcePatch(expected_version=1, title="Главный архив"), actor
    )
    with pytest.raises(ConflictError):
        await service.update_source(
            source.id, AdminSourcePatch(expected_version=1, title="Устаревшее"), actor
        )
    await service.archive_source(source.id, source.version, actor)

    relations = await service.list_relations(entity_id=None, relation_type=None, limit=1, offset=0)
    sources = await service.list_sources(query=None, source_type=None, limit=1, offset=0)
    assert relations.meta.total == sources.meta.total == 1
    assert repository.relations[relation.id].status is PublicationStatus.ARCHIVED
    assert repository.sources[source.id].status is PublicationStatus.ARCHIVED
    assert [action for action, _, _ in audit.actions] == [
        "catalog.relation.create",
        "catalog.relation.update",
        "catalog.relation.archive",
        "catalog.source.create",
        "catalog.source.update",
        "catalog.source.archive",
    ]


@pytest.mark.asyncio
async def test_relation_and_source_publish_invariants_and_stale_versions() -> None:
    repository, audit = FakeRepository(), FakeAudit()
    service = AdminCatalogService(lambda: FakeUoW(repository, audit))
    text = LocalizedText(ru="Связь", ce=None)
    with pytest.raises(SourceRequiredError):
        await service.create_relation(
            AdminRelationCreate(
                source_entity_id=uuid4(),
                target_entity_id=uuid4(),
                type=RelationType.CONNECTED_WITH,
                title=text,
                description=text,
                period_from=None,
                period_to=None,
                status=PublicationStatus.PUBLISHED,
            ),
            uuid4(),
        )
    with pytest.raises(SourceRequiredError):
        await service.create_source(
            AdminSourceCreate(
                title="Непроверенный источник",
                type=SourceType.WEB_RESOURCE,
                author=None,
                publisher=None,
                publication_year=None,
                url=None,
                archive_reference=None,
                description="",
                is_verified=False,
                status=PublicationStatus.PUBLISHED,
            ),
            uuid4(),
        )


class RoleAuthService:
    def __init__(self, role: str) -> None:
        self._role = role

    async def require_permission(self, token: str | None, permission: str) -> AdminAccount:
        can_read = self._role in {"moderator", "editor", "admin"}
        can_write = self._role in {"editor", "admin"}
        if (permission == Permission.CATALOG_READ and can_read) or (
            permission == Permission.CATALOG_WRITE and can_write
        ):
            return AdminAccount(
                id=uuid4(),
                email="admin@example.com",
                status="active",
                display_name="Admin",
                roles=[],
            )
        raise ForbiddenError("Permission is required")


@pytest.mark.parametrize("role", ["moderator", "editor", "admin"])
def test_admin_roles_have_bounded_catalog_read(role: str) -> None:
    app = FastAPI()
    app.middleware("http")(request_context)
    app.include_router(router, prefix="/api/v1")
    register_exception_handlers(app)
    repository = FakeRepository()
    service = AdminCatalogService(lambda: FakeUoW(repository, FakeAudit()))
    context = SimpleNamespace(
        service=RoleAuthService(role),
        token="session",
        source="test",
    )
    app.dependency_overrides[get_admin_catalog_service] = lambda: service
    app.dependency_overrides[get_auth_context] = lambda: context

    response = TestClient(app).get("/api/v1/admin/catalog/entities?limit=1&offset=0")
    assert response.status_code == 200
    assert response.json()["data"]["meta"] == {"limit": 1, "offset": 0, "total": 0}


def test_unknown_role_is_denied_by_transport() -> None:
    app = FastAPI()
    app.middleware("http")(request_context)
    app.include_router(router, prefix="/api/v1")
    register_exception_handlers(app)
    service = AdminCatalogService(lambda: FakeUoW(FakeRepository(), FakeAudit()))
    context = SimpleNamespace(
        service=RoleAuthService("future"),
        token="session",
        source="test",
    )
    app.dependency_overrides[get_admin_catalog_service] = lambda: service
    app.dependency_overrides[get_auth_context] = lambda: context
    response = TestClient(app).get("/api/v1/admin/catalog/entities")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
