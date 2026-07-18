from collections.abc import Callable
from uuid import UUID

import pytest

from common.exceptions import BadRequestError, NotFoundError
from modules.catalog.domain import EntityType, RelationType
from modules.catalog.graph import (
    GraphEdgeRecord,
    GraphEntity,
    GraphNodeRecord,
    GraphQuery,
    GraphRecords,
    GraphService,
    assemble_graph,
)


def _id(value: int) -> UUID:
    return UUID(int=value)


CENTER = GraphEntity(_id(100), EntityType.SETTLEMENT, "Центр", None)


def _node(
    value: int,
    *,
    depth: int = 1,
    entity_type: EntityType = EntityType.PERSON,
    period_from: int | None = 1900,
    period_to: int | None = 2000,
) -> GraphNodeRecord:
    return GraphNodeRecord(
        id=_id(value),
        type=entity_type,
        title_ru=f"Узел {value}",
        title_ce=None,
        depth=depth,
        period_from=period_from,
        period_to=period_to,
        relations_count=value,
    )


def _edge(value: int, source: int, target: int) -> GraphEdgeRecord:
    return GraphEdgeRecord(
        id=_id(value),
        source_id=_id(source),
        target_id=_id(target),
        type=RelationType.CONNECTED_WITH,
        title_ru="Связан",
        title_ce=None,
        description_ru="Связь",
        description_ce=None,
        period_from=1900,
        period_to=2000,
        sources_count=1,
    )


def test_graph_assembles_stable_nodes_edges_and_empty_graph() -> None:
    query = GraphQuery(center_id=CENTER.id, depth=2)
    records = GraphRecords(
        center=CENTER,
        nodes=(_node(2, depth=2), _node(1), _node(1, depth=2)),
        edges=(
            _edge(12, 1, 2),
            _edge(10, 100, 1),
            _edge(12, 1, 2),
            _edge(11, 2, 100),
        ),
    )

    result = assemble_graph(query, records)
    empty = assemble_graph(query, GraphRecords(center=CENTER))

    assert [node.id for node in result.nodes] == [_id(1), _id(2)]
    assert [edge.id for edge in result.edges] == [_id(10), _id(11), _id(12)]
    assert result.hidden_nodes_count == 0
    assert empty.nodes == ()
    assert empty.edges == ()


def test_graph_handles_cycles_and_removes_edges_to_hidden_nodes() -> None:
    records = GraphRecords(
        center=CENTER,
        nodes=(_node(1), _node(2, depth=2), _node(3, depth=2)),
        edges=(
            _edge(1, 100, 1),
            _edge(2, 1, 2),
            _edge(3, 2, 100),
            _edge(4, 2, 3),
        ),
    )

    result = assemble_graph(GraphQuery(CENTER.id, depth=2, limit=2), records)

    assert [edge.id for edge in result.edges] == [_id(1), _id(2), _id(3)]
    assert result.hidden_nodes_count == 1
    allowed = {CENTER.id, *(node.id for node in result.nodes)}
    assert all({edge.source_id, edge.target_id} <= allowed for edge in result.edges)


def test_graph_applies_depth_type_and_period_filters_before_limit() -> None:
    records = GraphRecords(
        center=CENTER,
        nodes=(
            _node(1, entity_type=EntityType.PERSON),
            _node(2, entity_type=EntityType.EVENT),
            _node(3, depth=2),
            _node(4, period_from=1700, period_to=1800),
        ),
        edges=(_edge(1, 100, 1), _edge(2, 100, 2), _edge(3, 100, 3)),
        hidden_nodes_count=4,
    )
    query = GraphQuery(
        CENTER.id,
        depth=1,
        types=(EntityType.PERSON,),
        period_from=1850,
        period_to=1950,
        limit=1,
    )

    result = assemble_graph(query, records)

    assert [node.id for node in result.nodes] == [_id(1)]
    assert [edge.id for edge in result.edges] == [_id(1)]
    assert result.hidden_nodes_count == 4


def test_graph_hard_limit_counts_unique_hidden_nodes() -> None:
    records = GraphRecords(
        center=CENTER,
        nodes=(*(_node(value) for value in range(45)), _node(0, depth=2)),
    )

    result = assemble_graph(GraphQuery(CENTER.id, limit=40), records)

    assert len(result.nodes) == 40
    assert result.hidden_nodes_count == 5
    assert len({node.id for node in result.nodes}) == 40


@pytest.mark.parametrize(
    "factory",
    [
        lambda: GraphQuery(CENTER.id, depth=0),
        lambda: GraphQuery(CENTER.id, depth=3),
        lambda: GraphQuery(CENTER.id, limit=0),
        lambda: GraphQuery(CENTER.id, limit=41),
    ],
)
def test_graph_query_rejects_unbounded_or_invalid_inputs(
    factory: Callable[[], GraphQuery],
) -> None:
    with pytest.raises(ValueError):
        factory()


class _FakeRepository:
    def __init__(self, records: GraphRecords) -> None:
        self._records = records

    async def graph_records(self, query: GraphQuery) -> GraphRecords:
        return self._records


async def test_graph_service_signals_missing_or_unpublished_center_as_not_found() -> None:
    service = GraphService(_FakeRepository(GraphRecords(center=None)))

    with pytest.raises(NotFoundError):
        await service.graph(GraphQuery(CENTER.id))


async def test_graph_service_rejects_inverted_period_without_querying() -> None:
    service = GraphService(_FakeRepository(GraphRecords(center=CENTER)))

    with pytest.raises(BadRequestError):
        await service.graph(GraphQuery(CENTER.id, period_from=2000, period_to=1900))
