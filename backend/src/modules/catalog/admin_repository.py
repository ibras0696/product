from dataclasses import dataclass
from typing import cast
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from modules.catalog.admin_schemas import (
    AdminEntity,
    AdminEntityCreate,
    AdminEntityPage,
    AdminRelation,
    AdminRelationCreate,
    AdminRelationPage,
    AdminSource,
    AdminSourceCreate,
    AdminSourcePage,
    Coordinates,
    LocalizedText,
    PageMeta,
)
from modules.catalog.admin_source_dependencies import (
    source_is_required_by_published_content,
)
from modules.catalog.domain import EntityType, PublicationStatus, RelationType, SourceType
from modules.catalog.models import (
    Entity,
    EntitySource,
    EntityText,
    Relation,
    RelationSource,
    Source,
)


@dataclass(slots=True)
class EditableEntity:
    entity: Entity
    texts: dict[str, EntityText]


class AdminCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_entities(
        self,
        *,
        query: str | None,
        entity_type: EntityType | None,
        status: PublicationStatus | None,
        limit: int,
        offset: int,
    ) -> AdminEntityPage:
        clauses, parameters = _filters(query, entity_type, status)
        where = " AND ".join(clauses) if clauses else "TRUE"
        parameters.update(limit=limit, offset=offset)
        total = await self._session.scalar(
            text(f"SELECT count(*) {_ENTITY_JOINS} WHERE {where}"), parameters
        )
        rows = (
            (
                await self._session.execute(
                    text(
                        f"{_ENTITY_SELECT} WHERE {where} ORDER BY e.updated_at DESC,e.id "
                        "LIMIT :limit OFFSET :offset"
                    ),
                    parameters,
                )
            )
            .mappings()
            .all()
        )
        return AdminEntityPage(
            items=[_entity_view(row) for row in rows],
            meta=PageMeta(limit=limit, offset=offset, total=int(total or 0)),
        )

    async def create_entity(self, payload: AdminEntityCreate) -> Entity:
        coordinate = None
        if payload.coordinates is not None:
            coordinate = func.ST_SetSRID(
                func.ST_MakePoint(payload.coordinates.longitude, payload.coordinates.latitude),
                4326,
            )
        entity = Entity(
            type=payload.type,
            slug=payload.slug,
            status=payload.status,
            version=1,
            coordinate=coordinate,
            period_from=payload.period_from,
            period_to=payload.period_to,
            district_id=payload.district_id,
        )
        self._session.add(entity)
        await self._session.flush()
        self._session.add_all(_new_texts(entity.id, payload))
        await self._session.flush()
        return entity

    async def get_entity(self, entity_id: UUID) -> AdminEntity | None:
        row = (
            (
                await self._session.execute(
                    text(f"{_ENTITY_SELECT} WHERE e.id=:id"), {"id": entity_id}
                )
            )
            .mappings()
            .one_or_none()
        )
        return _entity_view(row) if row is not None else None

    async def editable_entity(self, entity_id: UUID) -> EditableEntity | None:
        entity = await self._session.scalar(
            select(Entity).where(Entity.id == entity_id).with_for_update()
        )
        if entity is None:
            return None
        texts = (
            (
                await self._session.scalars(
                    select(EntityText).where(EntityText.entity_id == entity_id)
                )
            )
            .unique()
            .all()
        )
        return EditableEntity(entity, {item.locale: item for item in texts})

    async def update_entity(
        self, editable: EditableEntity, changes: dict[str, object], next_version: int
    ) -> None:
        entity = editable.entity
        for field in ("slug", "period_from", "period_to", "district_id", "status"):
            if field in changes:
                setattr(entity, field, changes[field])
        if "coordinates" in changes:
            coordinates = changes["coordinates"]
            entity.coordinate = _coordinate_expression(coordinates)
        _apply_localized_changes(editable, changes, self._session)
        entity.version = next_version
        await self._session.flush()

    async def verified_source_exists(self, entity_id: UUID) -> bool:
        result = await self._session.scalar(
            select(func.count())
            .select_from(EntitySource)
            .join(Source, Source.id == EntitySource.source_id)
            .where(
                EntitySource.entity_id == entity_id,
                Source.is_verified.is_(True),
                Source.status == PublicationStatus.PUBLISHED,
            )
        )
        return bool(result)

    async def list_relations(
        self,
        *,
        entity_id: UUID | None,
        relation_type: RelationType | None,
        limit: int,
        offset: int,
    ) -> AdminRelationPage:
        clauses = ["TRUE"]
        params: dict[str, object] = {"limit": limit, "offset": offset}
        if entity_id is not None:
            clauses.append("(source_entity_id=:entity_id OR target_entity_id=:entity_id)")
            params["entity_id"] = entity_id
        if relation_type is not None:
            clauses.append("type=:type")
            params["type"] = relation_type.value
        where = " AND ".join(clauses)
        total = await self._session.scalar(
            text(f"SELECT count(*) FROM catalog_relations WHERE {where}"), params
        )
        models = (
            await self._session.scalars(
                select(Relation)
                .where(text(where))
                .order_by(Relation.updated_at.desc(), Relation.id)
                .limit(limit)
                .offset(offset),
                params,
            )
        ).all()
        return AdminRelationPage(
            items=[_relation_view(model) for model in models],
            meta=PageMeta(limit=limit, offset=offset, total=int(total or 0)),
        )

    async def create_relation(self, payload: AdminRelationCreate) -> Relation:
        model = Relation(
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
        self._session.add(model)
        await self._session.flush()
        return model

    async def editable_relation(self, relation_id: UUID) -> Relation | None:
        return cast(
            Relation | None,
            await self._session.scalar(
                select(Relation).where(Relation.id == relation_id).with_for_update()
            ),
        )

    async def get_relation(self, relation_id: UUID) -> AdminRelation | None:
        model = await self._session.scalar(select(Relation).where(Relation.id == relation_id))
        return _relation_view(model) if model is not None else None

    async def update_relation(
        self, model: Relation, changes: dict[str, object], next_version: int
    ) -> None:
        for field in ("type", "period_from", "period_to", "status"):
            if field in changes:
                setattr(model, field, changes[field])
        title = changes.get("title")
        if isinstance(title, LocalizedText):
            model.title_ru, model.title_ce = title.ru, title.ce
        description = changes.get("description")
        if isinstance(description, LocalizedText):
            model.description_ru, model.description_ce = description.ru, description.ce
        model.version = next_version
        await self._session.flush()

    async def relation_has_verified_source(self, relation_id: UUID) -> bool:
        count = await self._session.scalar(
            select(func.count())
            .select_from(RelationSource)
            .join(Source, Source.id == RelationSource.source_id)
            .where(
                RelationSource.relation_id == relation_id,
                Source.is_verified.is_(True),
                Source.status == PublicationStatus.PUBLISHED,
            )
        )
        return bool(count)

    async def active_entities_exist(self, entity_ids: tuple[UUID, UUID]) -> bool:
        count = await self._session.scalar(
            select(func.count())
            .select_from(Entity)
            .where(Entity.id.in_(entity_ids), Entity.status != PublicationStatus.ARCHIVED)
        )
        return int(count or 0) == len(set(entity_ids))

    async def list_sources(
        self,
        *,
        query: str | None,
        source_type: SourceType | None,
        limit: int,
        offset: int,
    ) -> AdminSourcePage:
        clauses: list[ColumnElement[bool]] = []
        if query:
            clauses.append(Source.title.ilike(f"%{query}%"))
        if source_type is not None:
            clauses.append(Source.type == source_type)
        total = await self._session.scalar(select(func.count()).select_from(Source).where(*clauses))
        models = (
            await self._session.scalars(
                select(Source)
                .where(*clauses)
                .order_by(Source.updated_at.desc(), Source.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return AdminSourcePage(
            items=[_source_view(model) for model in models],
            meta=PageMeta(limit=limit, offset=offset, total=int(total or 0)),
        )

    async def create_source(self, payload: AdminSourceCreate) -> Source:
        values = payload.model_dump(exclude={"expected_version"})
        model = Source(**values, version=1)
        self._session.add(model)
        await self._session.flush()
        return model

    async def editable_source(self, source_id: UUID) -> Source | None:
        return cast(
            Source | None,
            await self._session.scalar(
                select(Source).where(Source.id == source_id).with_for_update()
            ),
        )

    async def get_source(self, source_id: UUID) -> AdminSource | None:
        model = await self._session.scalar(select(Source).where(Source.id == source_id))
        return _source_view(model) if model is not None else None

    async def update_source(
        self, model: Source, changes: dict[str, object], next_version: int
    ) -> None:
        for field, value in changes.items():
            setattr(model, field, value)
        model.version = next_version
        await self._session.flush()

    async def source_is_required(self, source_id: UUID) -> bool:
        return await source_is_required_by_published_content(self._session, source_id)


def _coordinate_expression(value: object) -> object:
    if value is None:
        return None
    if not isinstance(value, Coordinates):
        raise TypeError("coordinates must be validated")
    return func.ST_SetSRID(func.ST_MakePoint(value.longitude, value.latitude), 4326)


def _new_texts(entity_id: UUID, payload: AdminEntityCreate) -> list[EntityText]:
    result = [
        EntityText(
            entity_id=entity_id,
            locale="ru",
            title=payload.title.ru,
            short_description=payload.short_description.ru,
            full_description=payload.full_description.ru,
        )
    ]
    if payload.title.ce is not None:
        result.append(
            EntityText(
                entity_id=entity_id,
                locale="ce",
                title=payload.title.ce,
                short_description=payload.short_description.ce or "",
                full_description=payload.full_description.ce or "",
            )
        )
    return result


def _apply_localized_changes(
    editable: EditableEntity, changes: dict[str, object], session: AsyncSession
) -> None:
    for field, model_field in (
        ("title", "title"),
        ("short_description", "short_description"),
        ("full_description", "full_description"),
    ):
        value = changes.get(field)
        if not isinstance(value, LocalizedText):
            continue
        setattr(editable.texts["ru"], model_field, value.ru)
        ce_text = editable.texts.get("ce")
        if value.ce is not None and ce_text is None:
            ce_text = EntityText(
                entity_id=editable.entity.id,
                locale="ce",
                title="",
                short_description="",
                full_description="",
            )
            editable.texts["ce"] = ce_text
            session.add(ce_text)
        if ce_text is not None:
            setattr(ce_text, model_field, value.ce or "")


def _entity_view(row: RowMapping) -> AdminEntity:
    coordinates = None
    if row["latitude"] is not None:
        coordinates = Coordinates(latitude=row["latitude"], longitude=row["longitude"])
    return AdminEntity(
        id=row["id"],
        type=row["type"],
        slug=row["slug"],
        title=LocalizedText(ru=row["title_ru"], ce=row["title_ce"]),
        short_description=LocalizedText(ru=row["short_ru"], ce=row["short_ce"]),
        full_description=LocalizedText(ru=row["full_ru"], ce=row["full_ce"]),
        coordinates=coordinates,
        period_from=row["period_from"],
        period_to=row["period_to"],
        district_id=row["district_id"],
        status=row["status"],
        version=row["version"],
        relations_count=row["relations_count"],
        sources_count=row["sources_count"],
        media_count=row["media_count"],
    )


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


def _filters(
    query: str | None, entity_type: EntityType | None, status: PublicationStatus | None
) -> tuple[list[str], dict[str, object]]:
    clauses: list[str] = []
    parameters: dict[str, object] = {}
    if query:
        clauses.append("(e.slug ILIKE :query OR ru.title ILIKE :query OR ce.title ILIKE :query)")
        parameters["query"] = f"%{query}%"
    if entity_type is not None:
        clauses.append("e.type=:type")
        parameters["type"] = entity_type.value
    if status is not None:
        clauses.append("e.status=:status")
        parameters["status"] = status.value
    return clauses, parameters


_ENTITY_JOINS = """FROM catalog_entities e
JOIN catalog_entity_texts ru ON ru.entity_id=e.id AND ru.locale='ru'
LEFT JOIN catalog_entity_texts ce ON ce.entity_id=e.id AND ce.locale='ce'"""
_ENTITY_SELECT = f"""SELECT e.id,e.type,e.slug,e.status,e.version,e.period_from,e.period_to,
e.district_id,ST_Y(e.coordinate) latitude,ST_X(e.coordinate) longitude,
ru.title title_ru,NULLIF(ce.title,'') title_ce,ru.short_description short_ru,
NULLIF(ce.short_description,'') short_ce,ru.full_description full_ru,
NULLIF(ce.full_description,'') full_ce,
(SELECT count(*) FROM catalog_relations r WHERE r.source_entity_id=e.id OR r.target_entity_id=e.id)
relations_count,(SELECT count(*) FROM catalog_entity_sources es WHERE es.entity_id=e.id)
sources_count,(SELECT count(*) FROM media_assets m WHERE m.entity_id=e.id) media_count
{_ENTITY_JOINS}"""
