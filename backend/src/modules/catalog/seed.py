"""Bounded, idempotent catalog seed application use case."""

import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.base_model import BaseDBModel
from infrastructure.uow import UnitOfWork
from modules.catalog.domain import EntityType, PublicationStatus, RelationType, SourceType
from modules.catalog.models import (
    District,
    Entity,
    EntityName,
    EntitySource,
    EntityText,
    Relation,
    RelationSource,
    Source,
)

MAX_SEED_BYTES = 2_000_000
MAX_SEED_RECORDS = 1_000
Record = Mapping[str, object]


class SeedValidationError(ValueError):
    """The seed is malformed or violates a catalog invariant."""


@dataclass(frozen=True, slots=True)
class SeedPayload:
    groups: Mapping[str, tuple[Record, ...]]

    @property
    def record_count(self) -> int:
        return sum(len(records) for records in self.groups.values())


@dataclass(frozen=True, slots=True)
class SeedResult:
    created: int
    unchanged: int


class SeedRepositoryContract(Protocol):
    async def existing(
        self, model: type[BaseDBModel], record_ids: set[UUID]
    ) -> Mapping[UUID, BaseDBModel]: ...

    def add(self, instance: BaseDBModel) -> None: ...


class SeedUnitOfWorkContract(Protocol):
    @property
    def repository(self) -> SeedRepositoryContract: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class CatalogSeedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def existing(
        self, model: type[BaseDBModel], record_ids: set[UUID]
    ) -> Mapping[UUID, BaseDBModel]:
        if not record_ids:
            return {}
        statement = select(model).where(model.id.in_(record_ids))
        records = (await self._session.scalars(statement)).all()
        return {record.id: record for record in records}

    def add(self, instance: BaseDBModel) -> None:
        self._session.add(instance)


class CatalogSeedUnitOfWork(UnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.repository = CatalogSeedRepository(self.session)
        return self


SeedUnitOfWorkFactory = Callable[[], SeedUnitOfWorkContract]


def load_seed(path: Path) -> SeedPayload:
    if path.stat().st_size > MAX_SEED_BYTES:
        raise SeedValidationError("seed file exceeds the byte limit")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SeedValidationError("seed root must be an object")
    groups = {name: _records(value, name) for name in GROUP_ORDER}
    payload = SeedPayload(groups)
    if payload.record_count > MAX_SEED_RECORDS:
        raise SeedValidationError("seed exceeds the record limit")
    return payload


def _records(root: Mapping[object, object], name: str) -> tuple[Record, ...]:
    value = root.get(name, [])
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise SeedValidationError(f"{name} must be an array of objects")
    return tuple(value)


def _required[ValueT](record: Record, name: str, expected: type[ValueT]) -> ValueT:
    value = record.get(name)
    if not isinstance(value, expected):
        raise SeedValidationError(f"{name} is required and must be {expected.__name__}")
    return value


def _optional[ValueT](record: Record, name: str, expected: type[ValueT]) -> ValueT | None:
    value = record.get(name)
    if value is not None and not isinstance(value, expected):
        raise SeedValidationError(f"{name} must be {expected.__name__} or null")
    return value


def _uuid(record: Record, name: str = "id") -> UUID:
    try:
        return UUID(str(_required(record, name, str)))
    except ValueError as exc:
        raise SeedValidationError(f"{name} must be a UUID") from exc


def _text(record: Record, name: str) -> str:
    value = _required(record, name, str).strip()
    if not value:
        raise SeedValidationError(f"{name} must not be blank")
    return value


def _optional_text(record: Record, name: str) -> str | None:
    value = _optional(record, name, str)
    if value is not None and not value.strip():
        raise SeedValidationError(f"{name} must not be blank")
    return value.strip() if value is not None else None


def _integer(record: Record, name: str) -> int | None:
    return _optional(record, name, int)


def _number(record: Record, name: str) -> int | float | None:
    value = record.get(name)
    if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        raise SeedValidationError(f"{name} must be a number or null")
    return value


def _model_district(record: Record) -> District:
    return District(
        id=_uuid(record),
        slug=_text(record, "slug"),
        title_ru=_text(record, "title_ru"),
        title_ce=_optional_text(record, "title_ce"),
    )


def _model_source(record: Record) -> Source:
    return Source(
        id=_uuid(record),
        title=_text(record, "title"),
        type=SourceType(_text(record, "type")),
        author=_optional_text(record, "author"),
        publisher=_optional_text(record, "publisher"),
        publication_year=_integer(record, "publication_year"),
        url=_optional_text(record, "url"),
        archive_reference=_optional_text(record, "archive_reference"),
        description=_text(record, "description"),
        is_verified=_required(record, "is_verified", bool),
        status=PublicationStatus(_text(record, "status")),
        version=1,
    )


def _model_entity(record: Record) -> Entity:
    coordinate = _coordinate(record)
    return Entity(
        id=_uuid(record),
        type=EntityType(_text(record, "type")),
        slug=_text(record, "slug"),
        status=PublicationStatus(_text(record, "status")),
        version=1,
        coordinate=coordinate,
        period_from=_integer(record, "period_from"),
        period_to=_integer(record, "period_to"),
        district_id=_uuid(record, "district_id") if record.get("district_id") else None,
    )


def _coordinate(record: Record) -> str | None:
    longitude = _number(record, "longitude")
    latitude = _number(record, "latitude")
    if (longitude is None) != (latitude is None):
        raise SeedValidationError("longitude and latitude must be provided together")
    if longitude is None or latitude is None:
        return None
    _validate_coordinate_value(longitude, "longitude", -180, 180)
    _validate_coordinate_value(latitude, "latitude", -90, 90)
    return f"SRID=4326;POINT({longitude} {latitude})"


def _validate_coordinate_value(value: int | float, name: str, minimum: int, maximum: int) -> None:
    if not math.isfinite(value):
        raise SeedValidationError(f"{name} must be finite")
    if not minimum <= value <= maximum:
        raise SeedValidationError(f"{name} must be between {minimum} and {maximum}")


def _model_entity_text(record: Record) -> EntityText:
    return EntityText(
        id=_uuid(record),
        entity_id=_uuid(record, "entity_id"),
        locale=_text(record, "locale"),
        title=_text(record, "title"),
        short_description=_text(record, "short_description"),
        full_description=_text(record, "full_description"),
    )


def _model_entity_name(record: Record) -> EntityName:
    return EntityName(
        id=_uuid(record),
        entity_id=_uuid(record, "entity_id"),
        locale=_text(record, "locale"),
        name=_text(record, "name"),
    )


def _model_relation(record: Record) -> Relation:
    return Relation(
        id=_uuid(record),
        source_entity_id=_uuid(record, "source_entity_id"),
        target_entity_id=_uuid(record, "target_entity_id"),
        type=RelationType(_text(record, "type")),
        title_ru=_text(record, "title_ru"),
        title_ce=_optional_text(record, "title_ce"),
        description_ru=_text(record, "description_ru"),
        description_ce=_optional_text(record, "description_ce"),
        period_from=_integer(record, "period_from"),
        period_to=_integer(record, "period_to"),
        status=PublicationStatus(_text(record, "status")),
        version=1,
    )


def _model_entity_source(record: Record) -> EntitySource:
    return EntitySource(
        id=_uuid(record),
        entity_id=_uuid(record, "entity_id"),
        source_id=_uuid(record, "source_id"),
    )


def _model_relation_source(record: Record) -> RelationSource:
    return RelationSource(
        id=_uuid(record),
        relation_id=_uuid(record, "relation_id"),
        source_id=_uuid(record, "source_id"),
    )


ModelFactory = Callable[[Record], BaseDBModel]
GROUP_MODELS: Mapping[str, tuple[type[BaseDBModel], ModelFactory]] = {
    "districts": (District, _model_district),
    "sources": (Source, _model_source),
    "entities": (Entity, _model_entity),
    "entity_texts": (EntityText, _model_entity_text),
    "entity_names": (EntityName, _model_entity_name),
    "relations": (Relation, _model_relation),
    "entity_sources": (EntitySource, _model_entity_source),
    "relation_sources": (RelationSource, _model_relation_source),
}
GROUP_ORDER: Sequence[str] = tuple(GROUP_MODELS)


def validate_invariants(payload: SeedPayload) -> None:
    sources = {_uuid(item): item for item in payload.groups["sources"]}
    entity_links = _verified_links(payload.groups["entity_sources"], "entity_id", sources)
    relation_links = _verified_links(payload.groups["relation_sources"], "relation_id", sources)
    _validate_published(payload.groups["entities"], entity_links, "entity")
    _validate_published(payload.groups["relations"], relation_links, "relation")
    for relation in payload.groups["relations"]:
        if _uuid(relation, "source_entity_id") == _uuid(relation, "target_entity_id"):
            raise SeedValidationError("relation cannot connect an entity to itself")


def _verified_links(
    links: tuple[Record, ...], owner_key: str, sources: Mapping[UUID, Record]
) -> set[UUID]:
    return {
        _uuid(link, owner_key)
        for link in links
        if (source := sources.get(_uuid(link, "source_id"))) is not None
        and source.get("is_verified") is True
        and source.get("status") == PublicationStatus.PUBLISHED.value
    }


def _validate_published(records: tuple[Record, ...], linked: set[UUID], label: str) -> None:
    for record in records:
        is_published = record.get("status") == PublicationStatus.PUBLISHED.value
        if is_published and _uuid(record) not in linked:
            raise SeedValidationError(
                f"published {label} requires a linked verified and published source"
            )


MODEL_FIELDS: Mapping[str, tuple[str, ...]] = {
    "districts": ("slug", "title_ru", "title_ce"),
    "sources": (
        "title",
        "type",
        "author",
        "publisher",
        "publication_year",
        "url",
        "archive_reference",
        "description",
        "is_verified",
        "status",
        "version",
    ),
    "entities": (
        "type",
        "slug",
        "status",
        "version",
        "coordinate",
        "period_from",
        "period_to",
        "district_id",
    ),
    "entity_texts": (
        "entity_id",
        "locale",
        "title",
        "short_description",
        "full_description",
    ),
    "entity_names": ("entity_id", "locale", "name"),
    "relations": (
        "source_entity_id",
        "target_entity_id",
        "type",
        "title_ru",
        "title_ce",
        "description_ru",
        "description_ce",
        "period_from",
        "period_to",
        "status",
        "version",
    ),
    "entity_sources": ("entity_id", "source_id"),
    "relation_sources": ("relation_id", "source_id"),
}


def _has_content_drift(group: str, existing: BaseDBModel, expected: BaseDBModel) -> bool:
    return any(
        getattr(existing, field) != getattr(expected, field) for field in MODEL_FIELDS[group]
    )


class CatalogSeedService:
    def __init__(self, uow_factory: SeedUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def seed(self, payload: SeedPayload) -> SeedResult:
        created = 0
        unchanged = 0
        async with self._uow_factory() as uow:
            validate_invariants(payload)
            for group in GROUP_ORDER:
                model, factory = GROUP_MODELS[group]
                records = payload.groups[group]
                existing = await uow.repository.existing(
                    model, {_uuid(record) for record in records}
                )
                for record in records:
                    record_id = _uuid(record)
                    instance = factory(record)
                    if current := existing.get(record_id):
                        if _has_content_drift(group, current, instance):
                            raise SeedValidationError(
                                f"{group} record {record_id} conflicts with existing content"
                            )
                        unchanged += 1
                    else:
                        uow.repository.add(instance)
                        created += 1
        return SeedResult(created=created, unchanged=unchanged)
