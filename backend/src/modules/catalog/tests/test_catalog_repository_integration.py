import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from modules.catalog.admin_repository import AdminCatalogRepository
from modules.catalog.domain import EntityType
from modules.catalog.publication import CatalogPublicationAdapter
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


async def _media(
    repository: CatalogRepository, *, entity_id: UUID, status: str = "published"
) -> UUID:
    media_id = uuid4()
    await repository._session.execute(
        text(
            """INSERT INTO media_assets
            (id,entity_id,storage_key,public_url,preview_url,mime_type,width,height,
             caption,author,source_description,status)
            VALUES (:id,:entity_id,:storage_key,:public_url,:preview_url,'image/webp',640,480,
                    'Подпись','Автор','Архив',:status)"""
        ),
        {
            "id": media_id,
            "entity_id": entity_id,
            "storage_key": f"catalog-test/{media_id}",
            "public_url": f"/api/v1/media/{media_id}/original",
            "preview_url": f"/api/v1/media/{media_id}/preview",
            "status": status,
        },
    )
    return media_id


async def _relation(
    repository: CatalogRepository,
    *,
    source_id: UUID,
    target_id: UUID,
    status: str = "published",
) -> UUID:
    relation_id = uuid4()
    await repository._session.execute(
        text(
            """INSERT INTO catalog_relations
            (id,source_entity_id,target_entity_id,type,title_ru,description_ru,status,version)
            VALUES (:id,:source_id,:target_id,'connected_with','Связь','Описание',:status,1)"""
        ),
        {
            "id": relation_id,
            "source_id": source_id,
            "target_id": target_id,
            "status": status,
        },
    )
    return relation_id


def _map_query(*, limit: int, district_id: UUID | None = None) -> MapQuery:
    return MapQuery(
        bbox=(45.0, 43.0, 46.0, 44.0),
        zoom=8,
        types=(),
        district_id=district_id,
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

    page = await repository.map_entities(_map_query(limit=1, district_id=district_id))
    full = await repository.map_entities(_map_query(limit=10, district_id=district_id))

    assert page.truncated is True
    assert len(page.items) == 1
    assert {item.id for item in full.items} == {first_id, second_id}
    assert full.truncated is False


async def test_map_returns_only_published_relations_between_returned_entities(
    repository: CatalogRepository,
) -> None:
    district_id = await _district(repository)
    first_id = await _entity(repository, district_id=district_id, coordinate=(45.5, 43.5))
    second_id = await _entity(repository, district_id=district_id, coordinate=(45.6, 43.6))
    outside_id = await _entity(repository, district_id=district_id, coordinate=(47.0, 43.5))
    published_id = await _relation(
        repository, source_id=first_id, target_id=second_id
    )
    await _relation(repository, source_id=first_id, target_id=second_id, status="draft")
    await _relation(repository, source_id=first_id, target_id=outside_id)

    result = await repository.map_entities(_map_query(limit=10, district_id=district_id))

    assert [(edge.id, edge.source_id, edge.target_id) for edge in result.relations] == [
        (published_id, first_id, second_id)
    ]
    assert result.relations_truncated is False


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
    media_id = await _media(repository, entity_id=entity_id)
    await _media(repository, entity_id=entity_id, status="archived")

    details = await repository.get_entity(entity_id)
    media = await repository.list_entity_media(entity_id, limit=20, offset=0)

    assert details is not None
    assert details.sources_count == 1
    assert details.media_count == 1
    assert details.cover_url == f"/api/v1/media/{media_id}/preview"
    assert details.coordinates is not None
    assert details.coordinates.longitude == pytest.approx(45.5)
    assert media is not None
    assert [item.id for item in media.items] == [media_id]
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


async def test_only_published_verified_sources_satisfy_publication_invariant(
    repository: CatalogRepository,
) -> None:
    district_id = await _district(repository)
    source_entity_id = await _entity(
        repository, district_id=district_id, coordinate=(45.5, 43.5), status="draft"
    )
    target_entity_id = await _entity(
        repository, district_id=district_id, coordinate=(45.6, 43.6), status="draft"
    )
    source_id = await _source(
        repository,
        entity_id=source_entity_id,
        title="Черновой проверенный источник",
        status="draft",
    )
    relation_id = uuid4()
    await repository._session.execute(
        text(
            """INSERT INTO catalog_relations
            (id,source_entity_id,target_entity_id,type,title_ru,description_ru,status,version)
            VALUES (:id,:source_id,:target_id,'connected_with','Связь','Описание','draft',1)"""
        ),
        {"id": relation_id, "source_id": source_entity_id, "target_id": target_entity_id},
    )
    await repository._session.execute(
        text(
            """INSERT INTO catalog_relation_sources (id,relation_id,source_id)
            VALUES (:id,:relation_id,:source_id)"""
        ),
        {"id": uuid4(), "relation_id": relation_id, "source_id": source_id},
    )
    admin = AdminCatalogRepository(repository._session)
    publication = CatalogPublicationAdapter(repository._session)

    assert await admin.verified_source_exists(source_entity_id) is False
    assert await admin.relation_has_verified_source(relation_id) is False
    assert await publication._entity_has_verified_source(source_entity_id) is False

    await repository._session.execute(
        text("UPDATE catalog_sources SET status='published' WHERE id=:id"), {"id": source_id}
    )
    assert await admin.verified_source_exists(source_entity_id) is True
    assert await admin.relation_has_verified_source(relation_id) is True
    assert await publication._entity_has_verified_source(source_entity_id) is True

    await repository._session.execute(
        text("UPDATE catalog_sources SET status='archived' WHERE id=:id"), {"id": source_id}
    )
    assert await admin.verified_source_exists(source_entity_id) is False
    assert await admin.relation_has_verified_source(relation_id) is False
    assert await publication._entity_has_verified_source(source_entity_id) is False


async def test_source_dependency_check_covers_published_entities_and_relations(
    repository: CatalogRepository,
) -> None:
    district_id = await _district(repository)
    source_entity_id = await _entity(repository, district_id=district_id, coordinate=(45.5, 43.5))
    target_entity_id = await _entity(repository, district_id=district_id, coordinate=(45.6, 43.6))
    required_source_id = await _source(
        repository, entity_id=source_entity_id, title="Обязательный источник"
    )
    relation_id = uuid4()
    await repository._session.execute(
        text(
            """INSERT INTO catalog_relations
            (id,source_entity_id,target_entity_id,type,title_ru,description_ru,status,version)
            VALUES (:id,:source_id,:target_id,'connected_with','Связь','Описание','published',1)"""
        ),
        {"id": relation_id, "source_id": source_entity_id, "target_id": target_entity_id},
    )
    await repository._session.execute(
        text(
            """INSERT INTO catalog_relation_sources (id,relation_id,source_id)
            VALUES (:id,:relation_id,:source_id)"""
        ),
        {"id": uuid4(), "relation_id": relation_id, "source_id": required_source_id},
    )
    admin = AdminCatalogRepository(repository._session)
    assert await admin.source_is_required(required_source_id) is True

    alternate_source_id = await _source(
        repository, entity_id=source_entity_id, title="Альтернативный источник"
    )
    assert await admin.source_is_required(required_source_id) is True
    await repository._session.execute(
        text(
            """INSERT INTO catalog_relation_sources (id,relation_id,source_id)
            VALUES (:id,:relation_id,:source_id)"""
        ),
        {"id": uuid4(), "relation_id": relation_id, "source_id": alternate_source_id},
    )
    assert await admin.source_is_required(required_source_id) is False


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

    period_ids = [uuid4(), uuid4(), uuid4()]
    await repository._session.execute(
        text(
            """INSERT INTO catalog_periods
            (id,key,title_ru,period_from,period_to,display_order) VALUES
            (:late,'late','Поздний',1900,2000,1),
            (:early_b,'early-b','Ранний Б',1800,1850,30),
            (:early_a,'early-a','Ранний Первый',1800,1850,20)"""
        ),
        {"late": period_ids[0], "early_b": period_ids[1], "early_a": period_ids[2]},
    )

    options = await repository.get_options()
    selected = [item for item in options.districts if item.id in {earlier_id, later_id}]
    selected_periods = [
        item.id for item in options.periods if item.id in {"late", "early-a", "early-b"}
    ]

    assert [item.id for item in selected] == [earlier_id, later_id]
    assert selected_periods == ["early-a", "early-b", "late"]
    assert options.entity_types == list(EntityType)
