from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from common.exceptions import BadRequestError
from modules.catalog.domain import EntityType


@dataclass(frozen=True, slots=True)
class SearchQuery:
    text: str
    types: tuple[EntityType, ...]
    district_id: UUID | None
    period_from: int | None
    period_to: int | None
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class SearchRecord:
    id: UUID
    type: EntityType
    title_ru: str
    title_ce: str | None
    subtitle_ru: str
    subtitle_ce: str | None
    latitude: float | None
    longitude: float | None
    cover_url: str | None
    relations_count: int
    district_id: UUID | None
    rank: float


@dataclass(frozen=True, slots=True)
class SearchResult:
    items: tuple[SearchRecord, ...]
    total: int


class SearchRepositoryPort(Protocol):
    async def district_exists(self, district_id: UUID) -> bool: ...

    async def search(self, query: SearchQuery) -> SearchResult: ...


class CatalogSearchService:
    def __init__(self, repository: SearchRepositoryPort) -> None:
        self._repository = repository

    async def search(self, query: SearchQuery) -> SearchResult:
        normalized = " ".join(query.text.split()).casefold()
        self._validate_period(query.period_from, query.period_to)
        await self._require_known_district(query.district_id)
        return await self._repository.search(
            SearchQuery(
                text=normalized,
                types=query.types,
                district_id=query.district_id,
                period_from=query.period_from,
                period_to=query.period_to,
                limit=query.limit,
                offset=query.offset,
            )
        )

    async def _require_known_district(self, district_id: UUID | None) -> None:
        if district_id is not None and not await self._repository.district_exists(district_id):
            raise BadRequestError("Unknown district")

    @staticmethod
    def _validate_period(period_from: int | None, period_to: int | None) -> None:
        if period_from is not None and period_to is not None and period_from > period_to:
            raise BadRequestError("Invalid period")
