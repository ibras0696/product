from collections.abc import Mapping
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.catalog.domain import (
    EntityType,
    PublicationStatus,
    RelationType,
    SelfRelationForbiddenError,
    SourceRequiredError,
    SourceType,
)
from modules.catalog.models import (
    Entity,
    EntitySource,
    EntityText,
    Relation,
    RelationSource,
    Source,
)
from modules.moderation.contracts import PublishAction
from modules.publication.contracts import CatalogPublicationResult, PublicationSubmission


class CatalogPublicationAdapter:
    """Stages catalog mutations in the publication UoW's existing session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def publish(
        self,
        submission: PublicationSubmission,
        action: PublishAction,
        payload: BaseModel,
    ) -> CatalogPublicationResult:
        values = payload.model_dump()
        if action is PublishAction.CREATE_ENTITY:
            return await self._create_entity(values)
        if action is PublishAction.UPDATE_ENTITY:
            return await self._update_entity(values)
        if action is PublishAction.CREATE_RELATION:
            return await self._create_relation(values)
        if action is PublishAction.ADD_SOURCE:
            return await self._add_source(values)
        if action is PublishAction.PUBLISH_MEDIA:
            await self._require_entity(_uuid(values, "target_entity_id"))
            return CatalogPublicationResult()
        if action is PublishAction.RESOLVE_REPORT:
            return await self._resolve_report(submission, values)
        raise ValueError("Unsupported catalog publication action")

    async def _create_entity(self, payload: Mapping[str, object]) -> CatalogPublicationResult:
        entity_values = _mapping(payload, "entity")
        source_values = _mapping_list(payload, "sources")
        if not source_values:
            raise SourceRequiredError
        entity = await self._new_entity(entity_values)
        sources = [await self._new_source(item) for item in source_values]
        self._session.add_all(
            EntitySource(entity_id=entity.id, source_id=source.id) for source in sources
        )
        relations: list[Relation] = []
        for relation_values in _mapping_list(payload, "relations"):
            relation = await self._new_relation(relation_values)
            relations.append(relation)
            self._session.add_all(
                RelationSource(relation_id=relation.id, source_id=source.id) for source in sources
            )
        await self._session.flush()
        return CatalogPublicationResult(
            entity_ids=(entity.id,),
            relation_ids=tuple(item.id for item in relations),
            source_ids=tuple(item.id for item in sources),
        )

    async def _update_entity(self, payload: Mapping[str, object]) -> CatalogPublicationResult:
        entity = await self._require_entity(_uuid(payload, "entity_id"), lock=True)
        sources = [await self._new_source(item) for item in _mapping_list(payload, "sources")]
        self._session.add_all(
            EntitySource(entity_id=entity.id, source_id=source.id) for source in sources
        )
        await self._apply_entity_patch(entity, _mapping(payload, "entity_patch"))
        if entity.status is not PublicationStatus.PUBLISHED:
            if not sources and not await self._entity_has_verified_source(entity.id):
                raise SourceRequiredError
            entity.status = PublicationStatus.PUBLISHED
        entity.version += 1
        await self._session.flush()
        return CatalogPublicationResult(
            entity_ids=(entity.id,), source_ids=tuple(item.id for item in sources)
        )

    async def _create_relation(self, payload: Mapping[str, object]) -> CatalogPublicationResult:
        source_values = _mapping_list(payload, "sources")
        if not source_values:
            raise SourceRequiredError
        relation = await self._new_relation(_mapping(payload, "relation"))
        sources = [await self._new_source(item) for item in source_values]
        self._session.add_all(
            RelationSource(relation_id=relation.id, source_id=source.id) for source in sources
        )
        await self._session.flush()
        return CatalogPublicationResult(
            relation_ids=(relation.id,), source_ids=tuple(item.id for item in sources)
        )

    async def _add_source(self, payload: Mapping[str, object]) -> CatalogPublicationResult:
        source = await self._new_source(_mapping(payload, "source"))
        target_id = _uuid(payload, "target_id")
        if payload.get("target_type") == "entity":
            await self._require_entity(target_id)
            self._session.add(EntitySource(entity_id=target_id, source_id=source.id))
            result = CatalogPublicationResult(entity_ids=(target_id,), source_ids=(source.id,))
        else:
            await self._require_relation(target_id)
            self._session.add(RelationSource(relation_id=target_id, source_id=source.id))
            result = CatalogPublicationResult(relation_ids=(target_id,), source_ids=(source.id,))
        await self._session.flush()
        return result

    async def _resolve_report(
        self, submission: PublicationSubmission, payload: Mapping[str, object]
    ) -> CatalogPublicationResult:
        archive_id = payload.get("archive_entity_id")
        patch = payload.get("entity_patch")
        if archive_id is not None:
            entity = await self._require_entity(UUID(str(archive_id)), lock=True)
            entity.status = PublicationStatus.ARCHIVED
            entity.version += 1
            await self._session.flush()
            return CatalogPublicationResult(entity_ids=(entity.id,))
        if isinstance(patch, Mapping):
            if submission.related_entity_id is None:
                raise ValueError("Report entity target is required")
            entity = await self._require_entity(submission.related_entity_id, lock=True)
            await self._apply_entity_patch(entity, patch)
            entity.version += 1
            await self._session.flush()
            return CatalogPublicationResult(entity_ids=(entity.id,))
        return CatalogPublicationResult()

    async def _new_entity(self, values: Mapping[str, object]) -> Entity:
        coordinates = values.get("coordinates")
        coordinate = None
        if isinstance(coordinates, Mapping):
            coordinate = func.ST_SetSRID(
                func.ST_MakePoint(coordinates["longitude"], coordinates["latitude"]), 4326
            )
        entity = Entity(
            type=EntityType(str(values["type"])),
            slug=str(values["slug"]),
            status=PublicationStatus.PUBLISHED,
            version=1,
            coordinate=coordinate,
            period_from=values.get("period_from"),
            period_to=values.get("period_to"),
            district_id=values.get("district_id"),
        )
        self._session.add(entity)
        await self._session.flush()
        self._session.add_all(_entity_texts(entity.id, values))
        return entity

    async def _new_relation(self, values: Mapping[str, object]) -> Relation:
        source_id = UUID(str(values["source_entity_id"]))
        target_id = UUID(str(values["target_entity_id"]))
        if source_id == target_id:
            raise SelfRelationForbiddenError
        await self._require_entity(source_id)
        await self._require_entity(target_id)
        title, description = _mapping(values, "title"), _mapping(values, "description")
        relation = Relation(
            source_entity_id=source_id,
            target_entity_id=target_id,
            type=RelationType(str(values["type"])),
            title_ru=str(title["ru"]),
            title_ce=_optional_str(title.get("ce")),
            description_ru=str(description["ru"]),
            description_ce=_optional_str(description.get("ce")),
            period_from=values.get("period_from"),
            period_to=values.get("period_to"),
            status=PublicationStatus.PUBLISHED,
            version=1,
        )
        self._session.add(relation)
        await self._session.flush()
        return relation

    async def _new_source(self, values: Mapping[str, object]) -> Source:
        source = Source(
            title=str(values["title"]),
            type=SourceType(str(values["type"])),
            author=_optional_str(values.get("author")),
            publisher=_optional_str(values.get("publisher")),
            publication_year=values.get("publication_year"),
            url=_optional_str(values.get("url")),
            archive_reference=_optional_str(values.get("archive_reference")),
            description=str(values["description"]),
            is_verified=True,
            status=PublicationStatus.PUBLISHED,
            version=1,
        )
        self._session.add(source)
        await self._session.flush()
        return source

    async def _apply_entity_patch(self, entity: Entity, patch: Mapping[str, object]) -> None:
        for field in ("slug", "period_from", "period_to", "district_id"):
            if field in patch:
                setattr(entity, field, patch[field])
        coordinates = patch.get("coordinates")
        if "coordinates" in patch:
            entity.coordinate = None
            if isinstance(coordinates, Mapping):
                entity.coordinate = func.ST_SetSRID(
                    func.ST_MakePoint(coordinates["longitude"], coordinates["latitude"]), 4326
                )
        await self._update_texts(entity.id, patch)

    async def _update_texts(self, entity_id: UUID, patch: Mapping[str, object]) -> None:
        texts = (
            await self._session.scalars(
                select(EntityText).where(EntityText.entity_id == entity_id).with_for_update()
            )
        ).all()
        by_locale = {item.locale: item for item in texts}
        for payload_field, model_field in (
            ("title", "title"),
            ("short_description", "short_description"),
            ("full_description", "full_description"),
        ):
            value = patch.get(payload_field)
            if isinstance(value, Mapping):
                setattr(by_locale["ru"], model_field, str(value["ru"]))
                if "ce" in by_locale:
                    setattr(by_locale["ce"], model_field, _optional_str(value.get("ce")) or "")

    async def _require_entity(self, entity_id: UUID, *, lock: bool = False) -> Entity:
        statement = select(Entity).where(
            Entity.id == entity_id, Entity.status != PublicationStatus.ARCHIVED
        )
        if lock:
            statement = statement.with_for_update()
        entity = await self._session.scalar(statement)
        if entity is None:
            raise ValueError("Catalog entity not found")
        return entity

    async def _require_relation(self, relation_id: UUID) -> Relation:
        relation = await self._session.scalar(
            select(Relation).where(
                Relation.id == relation_id, Relation.status != PublicationStatus.ARCHIVED
            )
        )
        if relation is None:
            raise ValueError("Catalog relation not found")
        return relation

    async def _entity_has_verified_source(self, entity_id: UUID) -> bool:
        count = await self._session.scalar(
            select(func.count())
            .select_from(EntitySource)
            .join(Source, Source.id == EntitySource.source_id)
            .where(EntitySource.entity_id == entity_id, Source.is_verified.is_(True))
        )
        return bool(count)


def _entity_texts(entity_id: UUID, values: Mapping[str, object]) -> list[EntityText]:
    title = _mapping(values, "title")
    short = _mapping(values, "short_description")
    full = _mapping(values, "full_description")
    result = [
        EntityText(
            entity_id=entity_id,
            locale="ru",
            title=str(title["ru"]),
            short_description=str(short["ru"]),
            full_description=str(full["ru"]),
        )
    ]
    if title.get("ce") is not None:
        result.append(
            EntityText(
                entity_id=entity_id,
                locale="ce",
                title=str(title["ce"]),
                short_description=_optional_str(short.get("ce")) or "",
                full_description=_optional_str(full.get("ce")) or "",
            )
        )
    return result


def _mapping(values: Mapping[str, object], field: str) -> Mapping[str, object]:
    value = values.get(field)
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _mapping_list(values: Mapping[str, object], field: str) -> list[Mapping[str, object]]:
    raw = values.get(field)
    if not isinstance(raw, list) or not all(isinstance(item, Mapping) for item in raw):
        raise ValueError(f"{field} must be a list")
    return list(raw)


def _uuid(values: Mapping[str, object], field: str) -> UUID:
    return UUID(str(values[field]))


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)
