import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from modules.catalog.domain import EntityType
from modules.catalog.graph import GraphQuery, GraphService
from modules.catalog.graph_repository import GraphRepository

DATABASE_URL = os.getenv("DATABASE_URL")


@pytest_asyncio.fixture
async def graph_repository() -> AsyncIterator[GraphRepository]:
    if DATABASE_URL is None:
        pytest.skip("DATABASE_URL is required for PostgreSQL graph scenarios")
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield GraphRepository(session)
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


async def test_postgres_graph_handles_cycle_depth_and_published_scope(
    graph_repository: GraphRepository,
) -> None:
    center_id, first_id, second_id, hidden_id = (uuid4() for _ in range(4))
    await graph_repository._session.execute(
        text(
            """INSERT INTO catalog_entities (id,type,slug,status,version) VALUES
            (:center,'settlement',:center_slug,'published',1),
            (:first,'person',:first_slug,'published',1),
            (:second,'event',:second_slug,'published',1),
            (:hidden,'person',:hidden_slug,'archived',1)"""
        ),
        {
            "center": center_id,
            "first": first_id,
            "second": second_id,
            "hidden": hidden_id,
            "center_slug": f"graph-{center_id}",
            "first_slug": f"graph-{first_id}",
            "second_slug": f"graph-{second_id}",
            "hidden_slug": f"graph-{hidden_id}",
        },
    )
    for entity_id in (center_id, first_id, second_id, hidden_id):
        await graph_repository._session.execute(
            text(
                """INSERT INTO catalog_entity_texts
                (id,entity_id,locale,title,short_description,full_description)
                VALUES (:id,:entity_id,'ru','Узел','Кратко','Полно')"""
            ),
            {"id": uuid4(), "entity_id": entity_id},
        )
    for source_id, target_id in (
        (center_id, first_id),
        (first_id, second_id),
        (second_id, center_id),
        (center_id, hidden_id),
    ):
        await graph_repository._session.execute(
            text(
                """INSERT INTO catalog_relations
                (id,source_entity_id,target_entity_id,type,title_ru,description_ru,status,version)
                VALUES (:id,:source,:target,'connected_with','Связь','Описание','published',1)"""
            ),
            {"id": uuid4(), "source": source_id, "target": target_id},
        )

    result = await GraphService(graph_repository).graph(GraphQuery(center_id, depth=2, limit=40))

    assert {node.id for node in result.nodes} == {first_id, second_id}
    assert len(result.edges) == 3
    assert result.hidden_nodes_count == 0
    allowed = {center_id, first_id, second_id}
    assert all({edge.source_id, edge.target_id} <= allowed for edge in result.edges)


async def test_postgres_graph_filters_before_hard_limit_and_counts_hidden(
    graph_repository: GraphRepository,
) -> None:
    center_id = uuid4()
    node_ids = [uuid4() for _ in range(43)]
    await graph_repository._session.execute(
        text(
            """INSERT INTO catalog_entities (id,type,slug,status,version)
            VALUES (:id,'settlement',:slug,'published',1)"""
        ),
        {"id": center_id, "slug": f"graph-{center_id}"},
    )
    entity_rows = [
        {
            "id": node_id,
            "type": "event" if index == 42 else "person",
            "slug": f"graph-{node_id}",
            "period_from": 1700 if index == 41 else 1900,
            "period_to": 1750 if index == 41 else 1950,
        }
        for index, node_id in enumerate(node_ids)
    ]
    await graph_repository._session.execute(
        text(
            """INSERT INTO catalog_entities
            (id,type,slug,status,version,period_from,period_to)
            VALUES (:id,:type,:slug,'published',1,:period_from,:period_to)"""
        ),
        entity_rows,
    )
    text_rows = [
        {
            "id": uuid4(),
            "entity_id": entity_id,
            "title": f"Узел {index}",
        }
        for index, entity_id in enumerate([center_id, *node_ids])
    ]
    await graph_repository._session.execute(
        text(
            """INSERT INTO catalog_entity_texts
            (id,entity_id,locale,title,short_description,full_description)
            VALUES (:id,:entity_id,'ru',:title,'Кратко','Полно')"""
        ),
        text_rows,
    )
    relation_rows = [
        {"id": uuid4(), "source": center_id, "target": node_id} for node_id in node_ids
    ]
    await graph_repository._session.execute(
        text(
            """INSERT INTO catalog_relations
            (id,source_entity_id,target_entity_id,type,title_ru,description_ru,
             period_from,period_to,status,version)
            VALUES (:id,:source,:target,'connected_with','Связь','Описание',
                    1900,1950,'published',1)"""
        ),
        relation_rows,
    )

    result = await GraphService(graph_repository).graph(
        GraphQuery(
            center_id,
            depth=1,
            types=(EntityType.PERSON,),
            period_from=1850,
            period_to=2000,
            limit=40,
        )
    )

    assert len(result.nodes) == 40
    assert result.hidden_nodes_count == 1
    assert all(node.type is EntityType.PERSON for node in result.nodes)
    assert node_ids[41] not in {node.id for node in result.nodes}
    assert node_ids[42] not in {node.id for node in result.nodes}
