import hashlib
import math
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from common.exceptions import BadRequestError, NotFoundError
from modules.catalog.domain import EntityType, ResearchStatus
from modules.catalog.schemas import (
    CatalogOptions,
    EntityDetails,
    MapEntityCollection,
    MapRequest,
    Page,
    PublishedMedia,
    SourceView,
)


@dataclass(frozen=True, slots=True)
class MapQuery:
    bbox: tuple[float, float, float, float]
    zoom: int
    types: tuple[EntityType, ...]
    district_id: UUID | None
    period_from: int | None
    period_to: int | None
    limit: int
    research_statuses: tuple[ResearchStatus, ...] = ()


class CatalogQueryRepository(Protocol):
    async def district_exists(self, district_id: UUID) -> bool: ...

    async def map_entities(self, query: MapQuery) -> MapEntityCollection: ...

    async def get_entity(self, entity_id: UUID) -> EntityDetails | None: ...

    async def list_entity_sources(
        self, entity_id: UUID, limit: int, offset: int
    ) -> Page[SourceView] | None: ...

    async def list_relation_sources(
        self, relation_id: UUID, limit: int, offset: int
    ) -> Page[SourceView] | None: ...

    async def list_entity_media(
        self, entity_id: UUID, limit: int, offset: int
    ) -> Page[PublishedMedia] | None: ...

    async def get_options(self) -> CatalogOptions: ...


class CatalogService:
    def __init__(self, repository: CatalogQueryRepository) -> None:
        self._repository = repository

    async def map_entities(self, request: MapRequest) -> MapEntityCollection:
        coordinates = self._parse_bbox(request.bbox)
        self._validate_period(request.period_from, request.period_to)
        await self._require_known_district(request.district_id)
        query = MapQuery(
            bbox=coordinates,
            zoom=request.zoom,
            types=tuple(request.types),
            research_statuses=tuple(request.research_statuses),
            district_id=request.district_id,
            period_from=request.period_from,
            period_to=request.period_to,
            limit=request.limit,
        )
        return await self._repository.map_entities(query)

    async def entity_details(self, entity_id: UUID) -> EntityDetails:
        return self._require_result(await self._repository.get_entity(entity_id))

    async def entity_sources(self, entity_id: UUID, limit: int, offset: int) -> Page[SourceView]:
        result = await self._repository.list_entity_sources(entity_id, limit, offset)
        return self._require_result(result)

    async def relation_sources(
        self, relation_id: UUID, limit: int, offset: int
    ) -> Page[SourceView]:
        result = await self._repository.list_relation_sources(relation_id, limit, offset)
        return self._require_result(result)

    async def entity_media(self, entity_id: UUID, limit: int, offset: int) -> Page[PublishedMedia]:
        result = await self._repository.list_entity_media(entity_id, limit, offset)
        return self._require_result(result)

    async def options(self) -> tuple[CatalogOptions, str]:
        options = await self._repository.get_options()
        digest = hashlib.sha256(options.model_dump_json().encode()).hexdigest()
        return options, f'"{digest}"'

    async def _require_known_district(self, district_id: UUID | None) -> None:
        if district_id is not None and not await self._repository.district_exists(district_id):
            raise BadRequestError("Unknown district")

    @staticmethod
    def _parse_bbox(raw_bbox: str) -> tuple[float, float, float, float]:
        try:
            values = tuple(float(value.strip()) for value in raw_bbox.split(","))
        except ValueError as exc:
            raise BadRequestError("Invalid bbox") from exc
        if len(values) != 4 or not all(math.isfinite(value) for value in values):
            raise BadRequestError("Invalid bbox")
        min_lon, min_lat, max_lon, max_lat = values
        valid_range = -180 <= min_lon <= max_lon <= 180 and -90 <= min_lat <= max_lat <= 90
        if not valid_range:
            raise BadRequestError("Invalid bbox")
        return min_lon, min_lat, max_lon, max_lat

    @staticmethod
    def _validate_period(period_from: int | None, period_to: int | None) -> None:
        if period_from is not None and period_to is not None and period_from > period_to:
            raise BadRequestError("Invalid period")

    @staticmethod
    def _require_result[T](result: T | None) -> T:
        if result is None:
            raise NotFoundError("Catalog resource not found")
        return result
