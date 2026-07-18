import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from modules.catalog.domain import EntityType
from modules.catalog.repository import CatalogRepository
from modules.catalog.service import MapQuery

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is required for PostgreSQL repository integration tests",
)


@pytest_asyncio.fixture
async def repository() -> AsyncIterator[CatalogRepository]:
    assert DATABASE_URL is not None
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield CatalogRepository(session)
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


async def _district(repository: CatalogRepository) -> UUID:
    district_id = uuid4()
    await repository._session.execute(
        text(
            """INSERT INTO catalog_districts (id,slug,title_ru,title_ce)
            VALUES (:id,:slug,'Тестовый район','Тестан район')"""
        ),
        {"id": district_id, "slug": f"test-{district_id}"},
    )
    return district_id


async def _entity(
    repository: CatalogRepository,
    *,
    district_id: UUID,
    coordinate: tuple[float, float],
    status: str = "published",
    title: str = "Тестовый объект",
) -> UUID:
    entity_id = uuid4()
    await repository._session.execute(
        text(
            """INSERT INTO catalog_entities
            (id,type,slug,status,version,coordinate,district_id)
            VALUES (:id,'settlement',:slug,:status,1,
                    ST_SetSRID(ST_MakePoint(:longitude,:latitude),4326),:district_id)"""
        ),
        {
            "id": entity_id,
            "slug": f"test-{entity_id}",
            "status": status,
            "longitude": coordinate[0],
            "latitude": coordinate[1],
            "district_id": district_id,
        },
    )
    await repository._session.execute(
        text(
            """INSERT INTO catalog_entity_texts
            (id,entity_id,locale,title,short_description,full_description)
            VALUES (:id,:entity_id,'ru',:title,'Кратко','Полное описание')"""
        ),
        {"id": uuid4(), "entity_id": entity_id, "title": title},
    )
    return entity_id


async def _source(
    repository: CatalogRepository,
    *,
    entity_id: UUID,
    title: str,
    status: str = "published",
    verified: bool = True,
) -> UUID:
    source_id = uuid4()
    await repository._session.execute(
        text(
            """INSERT INTO catalog_sources
            (id,title,type,description,is_verified,status,version)
            VALUES (:id,:title,'archive_document','Описание',:verified,:status,1)"""
        ),
        {"id": source_id, "title": title, "verified": verified, "status": status},
    )
    await repository._session.execute(
        text(
            """INSERT INTO catalog_entity_sources (id,entity_id,source_id)
            VALUES (:id,:entity_id,:source_id)"""
        ),
        {"id": uuid4(), "entity_id": entity_id, "source_id": source_id},
    )
    return source_id


def _map_query(*, limit: int) -> MapQuery:
    return MapQuery(
        bbox=(45.0, 43.0, 46.0, 44.0),
        zoom=8,
        types=(),
        district_id=None,
        period_from=None,
        period_to=None,
        limit=limit,
    )


async def test_map_applies_bbox_and_published_scope_and_reports_truncation(
    repository: CatalogRepository,
) -> None:
    district_id = await _district(repository)
    first_id = await _entity(
        repository, district_id=district_id, coordinate=(45.5, 43.5), title="Первый"
    )
    second_id = await _entity(
        repository, district_id=district_id, coordinate=(45.6, 43.6), title="Второй"
    )
    await _entity(
        repository,
        district_id=district_id,
        coordinate=(45.7, 43.7),
        status="draft",
    )
    await _entity(repository, district_id=district_id, coordinate=(47.0, 43.5))

    page = await repository.map_entities(_map_query(limit=1))
    full = await repository.map_entities(_map_query(limit=10))

    assert page.truncated is True
    assert len(page.items) == 1
    assert {item.id for item in full.items} == {first_id, second_id}
    assert full.truncated is False


async def test_details_hide_drafts_and_count_only_public_evidence(
    repository: CatalogRepository,
) -> None:
    district_id = await _district(repository)
    entity_id = await _entity(repository, district_id=district_id, coordinate=(45.5, 43.5))
    draft_id = await _entity(
        repository,
        district_id=district_id,
        coordinate=(45.6, 43.6),
        status="draft",
    )
    await _source(repository, entity_id=entity_id, title="Открытый")
    await _source(repository, entity_id=entity_id, title="Черновик", status="draft")
    await _source(repository, entity_id=entity_id, title="unverified", verified=False)

    details = await repository.get_entity(entity_id)

    assert details is not None
    assert details.sources_count == 1
    assert details.coordinates is not None
    assert details.coordinates.longitude == pytest.approx(45.5)
    assert await repository.get_entity(draft_id) is None


async def test_sources_total_survives_offset_beyond_last_page(
    repository: CatalogRepository,
) -> None:
    district_id = await _district(repository)
    entity_id = await _entity(repository, district_id=district_id, coordinate=(45.5, 43.5))
    await _source(repository, entity_id=entity_id, title="Источник 1")
    await _source(repository, entity_id=entity_id, title="Источник 2")
    await _source(repository, entity_id=entity_id, title="Скрытый", verified=False)

    page = await repository.list_entity_sources(entity_id, limit=1, offset=20)

    assert page is not None
    assert page.items == []
    assert page.meta.total == 2
    assert page.meta.limit == 1
    assert page.meta.offset == 20


async def test_options_return_districts_in_stable_order(
    repository: CatalogRepository,
) -> None:
    later_id = await _district(repository)
    await repository._session.execute(
        text("UPDATE catalog_districts SET title_ru='Z district' WHERE id=:id"),
        {"id": later_id},
    )
    earlier_id = await _district(repository)
    await repository._session.execute(
        text("UPDATE catalog_districts SET title_ru='A district' WHERE id=:id"),
        {"id": earlier_id},
    )

    options = await repository.get_options()
    selected = [item for item in options.districts if item.id in {earlier_id, later_id}]

    assert [item.id for item in selected] == [earlier_id, later_id]
    assert options.periods == []
    assert options.entity_types == list(EntityType)
