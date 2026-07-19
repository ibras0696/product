import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from modules.catalog.timeline import TimelineQuery
from modules.catalog.timeline_repository import TimelineRepository

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is required for PostgreSQL timeline scenarios",
)


@pytest_asyncio.fixture
async def repository() -> AsyncIterator[TimelineRepository]:
    assert DATABASE_URL is not None
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield TimelineRepository(session)
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


async def add_district(repository: TimelineRepository, title: str) -> UUID:
    district_id = uuid4()
    await repository._session.execute(
        text(
            """INSERT INTO catalog_districts (id,slug,title_ru)
            VALUES (:id,:slug,:title)"""
        ),
        {"id": district_id, "slug": f"timeline-{district_id}", "title": title},
    )
    return district_id


@dataclass(frozen=True)
class EventSeed:
    district_id: UUID
    title: str
    period_from: int
    period_to: int
    status: str = "published"
    coordinates: tuple[float, float] | None = None


async def add_event(
    repository: TimelineRepository,
    seed: EventSeed,
) -> UUID:
    event_id = uuid4()
    insert_with_coordinate = text(
        """INSERT INTO catalog_entities
        (id,type,slug,status,version,district_id,period_from,period_to,coordinate)
        VALUES (:id,'event',:slug,:status,1,:district_id,:period_from,:period_to,
                ST_SetSRID(ST_MakePoint(:longitude,:latitude),4326))"""
    )
    insert_without_coordinate = text(
        """INSERT INTO catalog_entities
        (id,type,slug,status,version,district_id,period_from,period_to,coordinate)
        VALUES (:id,'event',:slug,:status,1,:district_id,:period_from,:period_to,NULL)"""
    )
    await repository._session.execute(
        insert_with_coordinate if seed.coordinates else insert_without_coordinate,
        {
            "id": event_id,
            "slug": f"timeline-event-{event_id}",
            "status": seed.status,
            "district_id": seed.district_id,
            "period_from": seed.period_from,
            "period_to": seed.period_to,
            "longitude": seed.coordinates[0] if seed.coordinates else None,
            "latitude": seed.coordinates[1] if seed.coordinates else None,
        },
    )
    await repository._session.execute(
        text(
            """INSERT INTO catalog_entity_texts
            (id,entity_id,locale,title,short_description,full_description)
            VALUES (:id,:entity_id,'ru',:title,:description,:description)"""
        ),
        {
            "id": uuid4(),
            "entity_id": event_id,
            "title": seed.title,
            "description": f"Подтверждённое событие {seed.title}",
        },
    )
    return event_id


async def test_timeline_sql_filters_orders_and_keeps_total(
    repository: TimelineRepository,
) -> None:
    district_id = await add_district(repository, "Основной район")
    other_district_id = await add_district(repository, "Другой район")
    first_id = await add_event(
        repository,
        EventSeed(
            district_id,
            "Искомое раннее событие",
            1900,
            1910,
            coordinates=(45.5, 43.5),
        ),
    )
    second_id = await add_event(
        repository,
        EventSeed(district_id, "Искомое позднее событие", 1905, 1920),
    )
    await add_event(
        repository,
        EventSeed(
            district_id,
            "Искомое скрытое событие",
            1900,
            1920,
            status="draft",
        ),
    )
    await add_event(
        repository,
        EventSeed(
            other_district_id,
            "Искомое событие другого района",
            1900,
            1920,
        ),
    )

    result = await repository.list_events(TimelineQuery("искомое", district_id, 1908, 1912, 1, 1))

    assert result.total == 2
    assert [item.id for item in result.items] == [second_id]
    full = await repository.list_events(TimelineQuery("искомое", district_id, 1908, 1912, 10, 0))
    assert [item.id for item in full.items] == [first_id, second_id]
    assert full.items[0].latitude == pytest.approx(43.5)
    assert full.items[1].latitude is None
