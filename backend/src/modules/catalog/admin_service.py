from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from common.exceptions import ApplicationError, BadRequestError, ConflictError, NotFoundError
from infrastructure.uow import UnitOfWork
from modules.audit.contracts import SqlAuditRepository
from modules.catalog.admin_repository import AdminCatalogRepository, EditableEntity
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
)
from modules.catalog.domain import EntityType, PublicationStatus, RelationType, SourceType
from modules.catalog.models import Entity, Relation, Source


class SourceRequiredError(ApplicationError):
    code = "source_required"
    status_code = 409


class AuditPort(Protocol):
    async def record(
        self,
        *,
        actor_id: UUID,
        action: str,
        resource_type: str,
        resource_id: UUID,
        version: int,
    ) -> None: ...


class AdminCatalogRepositoryPort(Protocol):
    async def list_entities(
        self,
        *,
        query: str | None,
        entity_type: EntityType | None,
        status: PublicationStatus | None,
        limit: int,
        offset: int,
    ) -> AdminEntityPage: ...

    async def create_entity(self, payload: AdminEntityCreate) -> Entity: ...

    async def get_entity(self, entity_id: UUID) -> AdminEntity | None: ...

    async def editable_entity(self, entity_id: UUID) -> EditableEntity | None: ...

    async def update_entity(
        self, editable: EditableEntity, changes: dict[str, object], next_version: int
    ) -> None: ...

    async def verified_source_exists(self, entity_id: UUID) -> bool: ...

    async def list_relations(
        self,
        *,
        entity_id: UUID | None,
        relation_type: RelationType | None,
        limit: int,
        offset: int,
    ) -> AdminRelationPage: ...

    async def create_relation(self, payload: AdminRelationCreate) -> Relation: ...

    async def editable_relation(self, relation_id: UUID) -> Relation | None: ...

    async def get_relation(self, relation_id: UUID) -> AdminRelation | None: ...

    async def update_relation(
        self, model: Relation, changes: dict[str, object], next_version: int
    ) -> None: ...

    async def relation_has_verified_source(self, relation_id: UUID) -> bool: ...

    async def active_entities_exist(self, entity_ids: tuple[UUID, UUID]) -> bool: ...

    async def list_sources(
        self,
        *,
        query: str | None,
        source_type: SourceType | None,
        limit: int,
        offset: int,
    ) -> AdminSourcePage: ...

    async def create_source(self, payload: AdminSourceCreate) -> Source: ...

    async def editable_source(self, source_id: UUID) -> Source | None: ...

    async def get_source(self, source_id: UUID) -> AdminSource | None: ...

    async def update_source(
        self, model: Source, changes: dict[str, object], next_version: int
    ) -> None: ...

    async def source_is_required(self, source_id: UUID) -> bool: ...


class AdminCatalogUoWContract(Protocol):
    @property
    def repository(self) -> AdminCatalogRepositoryPort: ...

    @property
    def audit(self) -> AuditPort: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class AdminCatalogUoW(UnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.repository = AdminCatalogRepository(self.session)
        self.audit = SqlAuditRepository(self.session)
        return self


UoWFactory = Callable[[], AdminCatalogUoWContract]


class AdminCatalogService:
    def __init__(self, uow_factory: UoWFactory) -> None:
        self._uow_factory = uow_factory

    async def list_entities(
        self,
        *,
        query: str | None,
        entity_type: EntityType | None,
        status: PublicationStatus | None,
        limit: int,
        offset: int,
    ) -> AdminEntityPage:
        normalized = query.strip() if query else None
        if normalized == "":
            normalized = None
        async with self._uow_factory() as uow:
            return await uow.repository.list_entities(
                query=normalized,
                entity_type=entity_type,
                status=status,
                limit=limit,
                offset=offset,
            )

    async def create_entity(self, payload: AdminEntityCreate, actor_id: UUID) -> AdminEntity:
        if payload.status is PublicationStatus.PUBLISHED:
            raise SourceRequiredError("A verified source is required before publication")
        try:
            async with self._uow_factory() as uow:
                model = await uow.repository.create_entity(payload)
                entity_id = model.id
                if not isinstance(entity_id, UUID):
                    raise RuntimeError("Catalog persistence did not assign an id")
                await uow.audit.record(
                    actor_id=actor_id,
                    action="catalog.entity.create",
                    resource_type="entity",
                    resource_id=entity_id,
                    version=1,
                )
                return self._require(await uow.repository.get_entity(entity_id))
        except IntegrityError as exc:
            raise ConflictError("Catalog entity conflicts with existing data") from exc

    async def update_entity(
        self, entity_id: UUID, payload: AdminEntityPatch, actor_id: UUID
    ) -> AdminEntity:
        try:
            async with self._uow_factory() as uow:
                editable = self._require_editable(
                    await uow.repository.editable_entity(entity_id), payload.expected_version
                )
                changes = payload.changes()
                self._validate_period(editable, changes)
                await self._require_source_for_publish(uow.repository, editable, changes)
                next_version = editable.entity.version + 1
                if changes:
                    await uow.repository.update_entity(editable, changes, next_version)
                    await uow.audit.record(
                        actor_id=actor_id,
                        action="catalog.entity.update",
                        resource_type="entity",
                        resource_id=entity_id,
                        version=next_version,
                    )
                return self._require(await uow.repository.get_entity(entity_id))
        except IntegrityError as exc:
            raise ConflictError("Catalog entity conflicts with existing data") from exc

    async def archive_entity(self, entity_id: UUID, expected_version: int, actor_id: UUID) -> None:
        async with self._uow_factory() as uow:
            editable = self._require_editable(
                await uow.repository.editable_entity(entity_id), expected_version
            )
            if editable.entity.status is PublicationStatus.ARCHIVED:
                raise ConflictError("Catalog entity is already archived")
            next_version = editable.entity.version + 1
            await uow.repository.update_entity(
                editable, {"status": PublicationStatus.ARCHIVED}, next_version
            )
            await uow.audit.record(
                actor_id=actor_id,
                action="catalog.entity.archive",
                resource_type="entity",
                resource_id=entity_id,
                version=next_version,
            )

    async def list_relations(
        self,
        *,
        entity_id: UUID | None,
        relation_type: RelationType | None,
        limit: int,
        offset: int,
    ) -> AdminRelationPage:
        async with self._uow_factory() as uow:
            return await uow.repository.list_relations(
                entity_id=entity_id,
                relation_type=relation_type,
                limit=limit,
                offset=offset,
            )

    async def create_relation(self, payload: AdminRelationCreate, actor_id: UUID) -> AdminRelation:
        if payload.status is PublicationStatus.PUBLISHED:
            raise SourceRequiredError("A verified source is required before publication")
        async with self._uow_factory() as uow:
            entity_ids = (payload.source_entity_id, payload.target_entity_id)
            if not await uow.repository.active_entities_exist(entity_ids):
                raise BadRequestError("Relation entities must exist and be active")
            model = await uow.repository.create_relation(payload)
            await _record(uow.audit, (actor_id, "catalog.relation.create", "relation", model.id, 1))
            return self._require_relation(await uow.repository.get_relation(model.id))

    async def update_relation(
        self, relation_id: UUID, payload: AdminRelationPatch, actor_id: UUID
    ) -> AdminRelation:
        async with self._uow_factory() as uow:
            model = self._require_relation_model(
                await uow.repository.editable_relation(relation_id),
                payload.expected_version,
                "relation",
            )
            changes = payload.changes()
            _validate_changed_period(model.period_from, model.period_to, changes)
            publishing = (
                changes.get("status") is PublicationStatus.PUBLISHED
                and model.status is not PublicationStatus.PUBLISHED
            )
            if publishing and not await uow.repository.relation_has_verified_source(relation_id):
                raise SourceRequiredError("A verified source is required before publication")
            if changes:
                next_version = model.version + 1
                await uow.repository.update_relation(model, changes, next_version)
                await _record(
                    uow.audit,
                    (actor_id, "catalog.relation.update", "relation", relation_id, next_version),
                )
            return self._require_relation(await uow.repository.get_relation(relation_id))

    async def archive_relation(
        self, relation_id: UUID, expected_version: int, actor_id: UUID
    ) -> None:
        async with self._uow_factory() as uow:
            model = self._require_relation_model(
                await uow.repository.editable_relation(relation_id), expected_version, "relation"
            )
            if model.status is PublicationStatus.ARCHIVED:
                raise ConflictError("Catalog relation is already archived")
            next_version = model.version + 1
            await uow.repository.update_relation(
                model, {"status": PublicationStatus.ARCHIVED}, next_version
            )
            await _record(
                uow.audit,
                (actor_id, "catalog.relation.archive", "relation", relation_id, next_version),
            )

    async def list_sources(
        self,
        *,
        query: str | None,
        source_type: SourceType | None,
        limit: int,
        offset: int,
    ) -> AdminSourcePage:
        normalized = query.strip() if query else None
        async with self._uow_factory() as uow:
            return await uow.repository.list_sources(
                query=normalized or None,
                source_type=source_type,
                limit=limit,
                offset=offset,
            )

    async def create_source(self, payload: AdminSourceCreate, actor_id: UUID) -> AdminSource:
        if payload.status is PublicationStatus.PUBLISHED and not payload.is_verified:
            raise SourceRequiredError("A source must be verified before publication")
        async with self._uow_factory() as uow:
            model = await uow.repository.create_source(payload)
            await _record(uow.audit, (actor_id, "catalog.source.create", "source", model.id, 1))
            return self._require_source(await uow.repository.get_source(model.id))

    async def update_source(
        self, source_id: UUID, payload: AdminSourcePatch, actor_id: UUID
    ) -> AdminSource:
        async with self._uow_factory() as uow:
            model = self._require_source_model(
                await uow.repository.editable_source(source_id),
                payload.expected_version,
                "source",
            )
            changes = payload.changes()
            resulting_status = changes.get("status", model.status)
            resulting_verified = changes.get("is_verified", model.is_verified)
            if resulting_status is PublicationStatus.PUBLISHED and resulting_verified is not True:
                raise SourceRequiredError("A source must be verified before publication")
            await self._prevent_required_source_deactivation(
                uow.repository, model, resulting_status, resulting_verified
            )
            if changes:
                next_version = model.version + 1
                await uow.repository.update_source(model, changes, next_version)
                await _record(
                    uow.audit,
                    (actor_id, "catalog.source.update", "source", source_id, next_version),
                )
            return self._require_source(await uow.repository.get_source(source_id))

    async def archive_source(self, source_id: UUID, expected_version: int, actor_id: UUID) -> None:
        async with self._uow_factory() as uow:
            model = self._require_source_model(
                await uow.repository.editable_source(source_id), expected_version, "source"
            )
            if model.status is PublicationStatus.ARCHIVED:
                raise ConflictError("Catalog source is already archived")
            if (
                model.is_verified
                and model.status is PublicationStatus.PUBLISHED
                and await uow.repository.source_is_required(source_id)
            ):
                raise SourceRequiredError(
                    "A published catalog record requires this verified source"
                )
            next_version = model.version + 1
            await uow.repository.update_source(
                model, {"status": PublicationStatus.ARCHIVED}, next_version
            )
            await _record(
                uow.audit,
                (actor_id, "catalog.source.archive", "source", source_id, next_version),
            )

    @staticmethod
    async def _prevent_required_source_deactivation(
        repository: AdminCatalogRepositoryPort,
        model: Source,
        resulting_status: object,
        resulting_verified: object,
    ) -> None:
        was_eligible = model.is_verified and model.status is PublicationStatus.PUBLISHED
        remains_eligible = (
            resulting_verified is True and resulting_status is PublicationStatus.PUBLISHED
        )
        if was_eligible and not remains_eligible and await repository.source_is_required(model.id):
            raise SourceRequiredError("A published catalog record requires this verified source")

    @staticmethod
    def _require_editable(editable: EditableEntity | None, expected_version: int) -> EditableEntity:
        if editable is None:
            raise NotFoundError("Catalog entity not found")
        if editable.entity.version != expected_version:
            raise ConflictError("Catalog entity version conflict")
        return editable

    @staticmethod
    def _validate_period(editable: EditableEntity, changes: dict[str, object]) -> None:
        period_from = changes.get("period_from", editable.entity.period_from)
        period_to = changes.get("period_to", editable.entity.period_to)
        if period_from is not None and not isinstance(period_from, int):
            raise BadRequestError("Invalid period")
        if period_to is not None and not isinstance(period_to, int):
            raise BadRequestError("Invalid period")
        if period_from is not None and period_to is not None and period_from > period_to:
            raise BadRequestError("Invalid period")

    @staticmethod
    async def _require_source_for_publish(
        repository: AdminCatalogRepositoryPort,
        editable: EditableEntity,
        changes: dict[str, object],
    ) -> None:
        if changes.get("status") is not PublicationStatus.PUBLISHED:
            return
        if editable.entity.status is PublicationStatus.PUBLISHED:
            return
        if not await repository.verified_source_exists(editable.entity.id):
            raise SourceRequiredError("A verified source is required before publication")

    @staticmethod
    def _require(entity: AdminEntity | None) -> AdminEntity:
        if entity is None:
            raise NotFoundError("Catalog entity not found")
        return entity

    @staticmethod
    def _require_relation_model(model: Relation | None, expected_version: int, _: str) -> Relation:
        if model is None:
            raise NotFoundError("Catalog relation not found")
        if model.version != expected_version:
            raise ConflictError("Catalog relation version conflict")
        return model

    @staticmethod
    def _require_source_model(model: Source | None, expected_version: int, _: str) -> Source:
        if model is None:
            raise NotFoundError("Catalog source not found")
        if model.version != expected_version:
            raise ConflictError("Catalog source version conflict")
        return model

    @staticmethod
    def _require_relation(value: AdminRelation | None) -> AdminRelation:
        if value is None:
            raise NotFoundError("Catalog relation not found")
        return value

    @staticmethod
    def _require_source(value: AdminSource | None) -> AdminSource:
        if value is None:
            raise NotFoundError("Catalog source not found")
        return value


AuditValues = tuple[UUID, str, str, UUID, int]


async def _record(audit: AuditPort, values: AuditValues) -> None:
    actor_id, action, resource_type, resource_id, version = values
    await audit.record(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        version=version,
    )


def _validate_changed_period(
    current_from: int | None, current_to: int | None, changes: dict[str, object]
) -> None:
    period_from = changes.get("period_from", current_from)
    period_to = changes.get("period_to", current_to)
    if period_from is not None and not isinstance(period_from, int):
        raise BadRequestError("Invalid period")
    if period_to is not None and not isinstance(period_to, int):
        raise BadRequestError("Invalid period")
    if period_from is not None and period_to is not None and period_from > period_to:
        raise BadRequestError("Invalid period")
