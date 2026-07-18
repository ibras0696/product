from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from common.exceptions import BadRequestError, NotFoundError
from modules.catalog.domain import EntityType, RelationType


@dataclass(frozen=True, slots=True)
class GraphQuery:
    center_id: UUID
    depth: int = 1
    types: tuple[EntityType, ...] = ()
    period_from: int | None = None
    period_to: int | None = None
    limit: int = 20

    def __post_init__(self) -> None:
        if self.depth not in (1, 2):
            raise ValueError("Graph depth must be 1 or 2")
        if not 1 <= self.limit <= 40:
            raise ValueError("Graph limit must be between 1 and 40")


@dataclass(frozen=True, slots=True)
class GraphEntity:
    id: UUID
    type: EntityType
    title_ru: str
    title_ce: str | None


@dataclass(frozen=True, slots=True)
class GraphNodeRecord(GraphEntity):
    depth: int
    period_from: int | None
    period_to: int | None
    relations_count: int


@dataclass(frozen=True, slots=True)
class GraphEdgeRecord:
    id: UUID
    source_id: UUID
    target_id: UUID
    type: RelationType
    title_ru: str
    title_ce: str | None
    description_ru: str
    description_ce: str | None
    period_from: int | None
    period_to: int | None
    sources_count: int


@dataclass(frozen=True, slots=True)
class GraphNode(GraphEntity):
    relations_count: int


@dataclass(frozen=True, slots=True)
class GraphEdge:
    id: UUID
    source_id: UUID
    target_id: UUID
    type: RelationType
    title_ru: str
    title_ce: str | None
    description_ru: str
    description_ce: str | None
    sources_count: int


@dataclass(frozen=True, slots=True)
class GraphResult:
    center: GraphEntity
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    hidden_nodes_count: int


@dataclass(frozen=True, slots=True)
class GraphRecords:
    center: GraphEntity | None
    nodes: tuple[GraphNodeRecord, ...] = ()
    edges: tuple[GraphEdgeRecord, ...] = ()
    hidden_nodes_count: int = 0


class GraphQueryRepository(Protocol):
    async def graph_records(self, query: GraphQuery) -> GraphRecords: ...


class GraphService:
    def __init__(self, repository: GraphQueryRepository) -> None:
        self._repository = repository

    async def graph(self, query: GraphQuery) -> GraphResult:
        if (
            query.period_from is not None
            and query.period_to is not None
            and query.period_from > query.period_to
        ):
            raise BadRequestError("Invalid period")
        records = await self._repository.graph_records(query)
        if records.center is None:
            raise NotFoundError("Catalog entity not found")
        return assemble_graph(query, records)


def assemble_graph(query: GraphQuery, records: GraphRecords) -> GraphResult:
    if records.center is None:
        raise ValueError("Graph center is required")
    candidates = _eligible_nodes(query, records.nodes)
    selected = candidates[: query.limit]
    selected_ids = {node.id for node in selected}
    allowed_ids = selected_ids | {records.center.id}
    edges = _eligible_edges(query, records.edges, allowed_ids)
    hidden_count = records.hidden_nodes_count + max(0, len(candidates) - len(selected))
    return GraphResult(
        center=records.center,
        nodes=tuple(_to_node(node) for node in selected),
        edges=tuple(_to_edge(edge) for edge in edges),
        hidden_nodes_count=hidden_count,
    )


def _eligible_nodes(
    query: GraphQuery, records: tuple[GraphNodeRecord, ...]
) -> list[GraphNodeRecord]:
    unique: dict[UUID, GraphNodeRecord] = {}
    for node in records:
        if node.depth > query.depth or not _matches_filters(
            node.type, node.period_from, node.period_to, query
        ):
            continue
        previous = unique.get(node.id)
        if previous is None or node.depth < previous.depth:
            unique[node.id] = node
    return sorted(unique.values(), key=lambda node: (node.depth, node.id))


def _eligible_edges(
    query: GraphQuery, records: tuple[GraphEdgeRecord, ...], allowed_ids: set[UUID]
) -> list[GraphEdgeRecord]:
    unique = {
        edge.id: edge
        for edge in records
        if edge.source_id in allowed_ids
        and edge.target_id in allowed_ids
        and _period_overlaps(edge.period_from, edge.period_to, query.period_from, query.period_to)
    }
    return sorted(unique.values(), key=lambda edge: edge.id)


def _matches_filters(
    entity_type: EntityType,
    item_from: int | None,
    item_to: int | None,
    query: GraphQuery,
) -> bool:
    return (not query.types or entity_type in query.types) and _period_overlaps(
        item_from, item_to, query.period_from, query.period_to
    )


def _period_overlaps(
    item_from: int | None,
    item_to: int | None,
    query_from: int | None,
    query_to: int | None,
) -> bool:
    return (query_from is None or item_to is None or item_to >= query_from) and (
        query_to is None or item_from is None or item_from <= query_to
    )


def _to_node(record: GraphNodeRecord) -> GraphNode:
    return GraphNode(
        id=record.id,
        type=record.type,
        title_ru=record.title_ru,
        title_ce=record.title_ce,
        relations_count=record.relations_count,
    )


def _to_edge(record: GraphEdgeRecord) -> GraphEdge:
    return GraphEdge(
        id=record.id,
        source_id=record.source_id,
        target_id=record.target_id,
        type=record.type,
        title_ru=record.title_ru,
        title_ce=record.title_ce,
        description_ru=record.description_ru,
        description_ce=record.description_ce,
        sources_count=record.sources_count,
    )
