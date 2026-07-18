import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from common.exceptions import BadRequestError
from modules.catalog.domain import EntityType
from modules.catalog.search import (
    CatalogSearchService,
    SearchQuery,
    SearchRecord,
    SearchResult,
)
from modules.catalog.search_repository import _SEARCH_SQL, CatalogSearchRepository

DATABASE_URL = os.getenv("DATABASE_URL")


class FakeSearchRepository:
    def __init__(self, *, known_district: bool = True) -> None:
        self.known_district = known_district
        self.received: SearchQuery | None = None

    async def district_exists(self, district_id: UUID) -> bool:
        return self.known_district

    async def search(self, query: SearchQuery) -> SearchResult:
        self.received = query
        item = SearchRecord(
            id=uuid4(),
            type=EntityType.SETTLEMENT,
            title_ru="Грозный",
            title_ce="Соьлжа-ГӀала",
            subtitle_ru="Столица",
            subtitle_ce=None,
            latitude=43.31,
            longitude=45.69,
            cover_url=None,
            relations_count=2,
            district_id=query.district_id,
            rank=100.0,
        )
        return SearchResult(items=(item,), total=1)


def _query() -> SearchQuery:
    return SearchQuery(
        text="  ГРОЗНЫЙ   ",
        types=(EntityType.SETTLEMENT,),
        district_id=None,
        period_from=None,
        period_to=None,
        limit=20,
        offset=0,
    )


async def test_search_normalizes_query_and_preserves_bounded_filters() -> None:
    repository = FakeSearchRepository()
    service = CatalogSearchService(repository)

    result = await service.search(replace(_query(), limit=7, offset=1000))

    assert result.total == 1
    assert repository.received == replace(_query(), text="грозный", limit=7, offset=1000)


async def test_search_rejects_invalid_period_before_querying_repository() -> None:
    repository = FakeSearchRepository()

    with pytest.raises(BadRequestError, match="Invalid period"):
        await CatalogSearchService(repository).search(
            replace(_query(), period_from=2000, period_to=1900)
        )

    assert repository.received is None


async def test_search_rejects_unknown_district() -> None:
    repository = FakeSearchRepository(known_district=False)

    with pytest.raises(BadRequestError, match="Unknown district"):
        await CatalogSearchService(repository).search(replace(_query(), district_id=uuid4()))

    assert repository.received is None


def test_search_sql_is_published_bounded_and_deterministic() -> None:
    normalized = " ".join(_SEARCH_SQL.split())

    assert "e.status='published'" in normalized
    assert "LIMIT :limit OFFSET :offset" in normalized
    assert normalized.endswith("ORDER BY p.rank DESC,e.id")
    assert "SELECT count(*) total_count FROM ranked" in normalized
    assert "catalog_entity_names" in normalized


@pytest_asyncio.fixture
async def pg_repository() -> AsyncIterator[CatalogSearchRepository]:
    if DATABASE_URL is None:
        pytest.skip("DATABASE_URL is required for PostgreSQL search scenarios")
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield CatalogSearchRepository(session)
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


@dataclass(frozen=True, slots=True)
class EntityFixture:
    district_id: UUID
    title_ru: str
    title_ce: str | None
    status: str = "published"
    entity_type: str = "settlement"
    period_from: int | None = 1800


async def _insert_entity(repository: CatalogSearchRepository, fixture: EntityFixture) -> UUID:
    entity_id = uuid4()
    await repository._session.execute(
        text(
            """INSERT INTO catalog_entities
            (id,type,slug,status,version,district_id,period_from)
            VALUES (:id,:type,:slug,:status,1,:district_id,:period_from)"""
        ),
        {
            "id": entity_id,
            "type": fixture.entity_type,
            "slug": f"search-{entity_id}",
            "status": fixture.status,
            "district_id": fixture.district_id,
            "period_from": fixture.period_from,
        },
    )
    for locale, title in (("ru", fixture.title_ru), ("ce", fixture.title_ce)):
        if title is not None:
            await repository._session.execute(
                text(
                    """INSERT INTO catalog_entity_texts
                    (id,entity_id,locale,title,short_description,full_description)
                    VALUES (:id,:entity_id,:locale,:title,'Описание','Полное описание')"""
                ),
                {"id": uuid4(), "entity_id": entity_id, "locale": locale, "title": title},
            )
    return entity_id


async def _insert_district(repository: CatalogSearchRepository) -> UUID:
    district_id = uuid4()
    await repository._session.execute(
        text(
            """INSERT INTO catalog_districts (id,slug,title_ru)
            VALUES (:id,:slug,'Поисковый район')"""
        ),
        {"id": district_id, "slug": f"search-{district_id}"},
    )
    return district_id


async def test_postgres_search_handles_exact_typo_ce_alternative_and_hidden_scope(
    pg_repository: CatalogSearchRepository,
) -> None:
    district_id = await _insert_district(pg_repository)
    entity_id = await _insert_entity(
        pg_repository,
        EntityFixture(district_id, "Грозный", "Соьлжа-ГӀала"),
    )
    await pg_repository._session.execute(
        text(
            """INSERT INTO catalog_entity_names (id,entity_id,locale,name)
            VALUES (:id,:entity_id,'ru','Джохар')"""
        ),
        {"id": uuid4(), "entity_id": entity_id},
    )
    await _insert_entity(
        pg_repository,
        EntityFixture(district_id, "Грозный архив", None, status="archived"),
    )

    service = CatalogSearchService(pg_repository)
    exact = await service.search(replace(_query(), district_id=district_id))
    typo = await service.search(replace(_query(), text="Грозни", district_id=district_id))
    ce = await service.search(replace(_query(), text="соьлжа-гӀала", district_id=district_id))
    alternative = await service.search(replace(_query(), text="джохар", district_id=district_id))

    assert [item.id for item in exact.items] == [entity_id]
    assert [item.id for item in typo.items] == [entity_id]
    assert [item.id for item in ce.items] == [entity_id]
    assert [item.id for item in alternative.items] == [entity_id]


async def test_postgres_search_combines_filters_and_preserves_total_after_offset(
    pg_repository: CatalogSearchRepository,
) -> None:
    district_id = await _insert_district(pg_repository)
    expected_id = await _insert_entity(pg_repository, EntityFixture(district_id, "Общее имя", None))
    await _insert_entity(
        pg_repository,
        EntityFixture(district_id, "Общее имя", None, entity_type="person"),
    )
    service = CatalogSearchService(pg_repository)

    page = await service.search(
        replace(
            _query(),
            text="общее имя",
            district_id=district_id,
            period_from=1700,
            offset=1000,
        )
    )

    assert page.items == ()
    assert page.total == 1
    unpaged = await service.search(replace(_query(), text="общее имя", district_id=district_id))
    assert [item.id for item in unpaged.items] == [expected_id]
