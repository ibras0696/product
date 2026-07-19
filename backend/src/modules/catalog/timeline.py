from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from common.exceptions import BadRequestError


@dataclass(frozen=True, slots=True)
class TimelineQuery:
    text: str | None
    district_id: UUID | None
    period_from: int | None
    period_to: int | None
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    id: UUID
    title_ru: str
    title_ce: str | None
    short_description_ru: str
    short_description_ce: str | None
    period_from: int | None
    period_to: int | None
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True, slots=True)
class TimelineResult:
    items: tuple[TimelineEvent, ...]
    total: int


class TimelineRepositoryPort(Protocol):
    async def district_exists(self, district_id: UUID) -> bool: ...

    async def list_events(self, query: TimelineQuery) -> TimelineResult: ...


class TimelineService:
    def __init__(self, repository: TimelineRepositoryPort) -> None:
        self._repository = repository

    async def list_events(self, query: TimelineQuery) -> TimelineResult:
        if (
            query.period_from is not None
            and query.period_to is not None
            and query.period_from > query.period_to
        ):
            raise BadRequestError("Invalid period")
        if query.district_id is not None and not await self._repository.district_exists(
            query.district_id
        ):
            raise BadRequestError("Unknown district")
        return await self._repository.list_events(
            TimelineQuery(
                text=" ".join(query.text.split()).casefold() if query.text else None,
                district_id=query.district_id,
                period_from=query.period_from,
                period_to=query.period_to,
                limit=query.limit,
                offset=query.offset,
            )
        )
