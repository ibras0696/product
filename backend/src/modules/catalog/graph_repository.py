from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from modules.catalog.domain import EntityType, RelationType
from modules.catalog.graph import (
    GraphEdgeRecord,
    GraphEntity,
    GraphNodeRecord,
    GraphQuery,
    GraphRecords,
)
from modules.catalog.public_text import public_description


class GraphRepository:
    """Read-only graph queries; traversal and returned rows are bounded in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def graph_records(self, query: GraphQuery) -> GraphRecords:
        parameters = _parameters(query)
        center_row = (
            (await self._session.execute(text(_CENTER_SQL), parameters)).mappings().one_or_none()
        )
        if center_row is None:
            return GraphRecords(center=None)
        node_rows = (await self._session.execute(text(_NODES_SQL), parameters)).mappings().all()
        nodes = tuple(_node(row) for row in node_rows if row["id"] is not None)
        total = int(node_rows[0]["total_count"]) if node_rows else 0
        edge_rows = (await self._session.execute(text(_EDGES_SQL), parameters)).mappings().all()
        return GraphRecords(
            center=_center(center_row),
            nodes=nodes,
            edges=tuple(_edge(row) for row in edge_rows),
            hidden_nodes_count=max(0, total - len(nodes)),
        )


def _parameters(query: GraphQuery) -> dict[str, object]:
    return {
        "center_id": query.center_id,
        "depth": query.depth,
        "types": [item.value for item in query.types],
        "has_types": bool(query.types),
        "period_from": query.period_from,
        "period_to": query.period_to,
        "limit": query.limit,
        "edge_limit": 1600,
    }


def _center(row: RowMapping) -> GraphEntity:
    return GraphEntity(
        id=row["id"],
        type=EntityType(row["type"]),
        title_ru=row["title_ru"],
        title_ce=row["title_ce"],
    )


def _node(row: RowMapping) -> GraphNodeRecord:
    return GraphNodeRecord(
        id=row["id"],
        type=EntityType(row["type"]),
        title_ru=row["title_ru"],
        title_ce=row["title_ce"],
        depth=row["depth"],
        period_from=row["period_from"],
        period_to=row["period_to"],
        relations_count=row["relations_count"],
    )


def _edge(row: RowMapping) -> GraphEdgeRecord:
    return GraphEdgeRecord(
        id=row["id"],
        source_id=row["source_id"],
        target_id=row["target_id"],
        type=RelationType(row["type"]),
        title_ru=row["title_ru"],
        title_ce=row["title_ce"],
        description_ru=public_description(
            row["description_ru"], fallback="Связь подтверждена источником."
        ),
        description_ce=(
            public_description(row["description_ce"]) if row["description_ce"] else None
        ),
        period_from=row["period_from"],
        period_to=row["period_to"],
        sources_count=row["sources_count"],
    )


_PERIOD_FILTER = """(CAST(:period_from AS integer) IS NULL OR item.period_to IS NULL
OR item.period_to >= CAST(:period_from AS integer))
AND (CAST(:period_to AS integer) IS NULL OR item.period_from IS NULL
OR item.period_from <= CAST(:period_to AS integer))"""

_FIRST_NODES = f"""SELECT DISTINCT
CASE WHEN r.source_entity_id=:center_id THEN r.target_entity_id ELSE r.source_entity_id END node_id,
1 depth FROM catalog_relations r
JOIN catalog_entities item ON item.id=CASE WHEN r.source_entity_id=:center_id
THEN r.target_entity_id ELSE r.source_entity_id END
WHERE (r.source_entity_id=:center_id OR r.target_entity_id=:center_id)
AND r.status='published' AND item.status='published'
AND (NOT CAST(:has_types AS boolean) OR item.type=ANY(CAST(:types AS text[])))
AND {_PERIOD_FILTER}
AND (CAST(:period_from AS integer) IS NULL OR r.period_to IS NULL
 OR r.period_to >= CAST(:period_from AS integer))
AND (CAST(:period_to AS integer) IS NULL OR r.period_from IS NULL
 OR r.period_from <= CAST(:period_to AS integer))"""

_CANDIDATES_CTE = f"""first_nodes AS ({_FIRST_NODES}),
second_nodes AS (SELECT DISTINCT
CASE WHEN r.source_entity_id=f.node_id THEN r.target_entity_id ELSE r.source_entity_id END node_id,
2 depth FROM first_nodes f JOIN catalog_relations r
ON r.source_entity_id=f.node_id OR r.target_entity_id=f.node_id
JOIN catalog_entities item ON item.id=CASE WHEN r.source_entity_id=f.node_id
THEN r.target_entity_id ELSE r.source_entity_id END
WHERE CAST(:depth AS integer)=2 AND r.status='published'
AND item.status='published' AND item.id<>:center_id
AND (NOT CAST(:has_types AS boolean) OR item.type=ANY(CAST(:types AS text[])))
AND {_PERIOD_FILTER}
AND (CAST(:period_from AS integer) IS NULL OR r.period_to IS NULL
 OR r.period_to >= CAST(:period_from AS integer))
AND (CAST(:period_to AS integer) IS NULL OR r.period_from IS NULL
 OR r.period_from <= CAST(:period_to AS integer))),
candidates AS (SELECT node_id,min(depth) depth FROM
(SELECT * FROM first_nodes UNION ALL SELECT * FROM second_nodes) found GROUP BY node_id),
ranked AS (SELECT node_id,depth,row_number() OVER (ORDER BY depth,node_id) rank
FROM candidates)"""

_CENTER_SQL = """SELECT e.id,e.type,ru.title title_ru,ce.title title_ce
FROM catalog_entities e JOIN catalog_entity_texts ru ON ru.entity_id=e.id AND ru.locale='ru'
LEFT JOIN catalog_entity_texts ce ON ce.entity_id=e.id AND ce.locale='ce'
WHERE e.id=:center_id AND e.status='published'"""

_NODES_SQL = f"""WITH {_CANDIDATES_CTE},
selected AS (SELECT * FROM ranked WHERE rank<=CAST(:limit AS integer)),
summary AS (SELECT count(*) total_count FROM candidates)
SELECT summary.total_count,e.id,e.type,e.period_from,e.period_to,s.depth,
ru.title title_ru,ce.title title_ce,
(SELECT count(*) FROM catalog_relations visible
 JOIN catalog_entities peer ON peer.id=CASE WHEN visible.source_entity_id=e.id
 THEN visible.target_entity_id ELSE visible.source_entity_id END
 WHERE visible.status='published' AND peer.status='published'
 AND (visible.source_entity_id=e.id OR visible.target_entity_id=e.id)) relations_count
FROM summary LEFT JOIN selected s ON true LEFT JOIN catalog_entities e ON e.id=s.node_id
LEFT JOIN catalog_entity_texts ru ON ru.entity_id=e.id AND ru.locale='ru'
LEFT JOIN catalog_entity_texts ce ON ce.entity_id=e.id AND ce.locale='ce'
ORDER BY s.depth,e.id"""

_EDGES_SQL = f"""WITH {_CANDIDATES_CTE}, selected AS
(SELECT node_id FROM ranked WHERE rank<=CAST(:limit AS integer)), allowed AS
(SELECT CAST(:center_id AS uuid) node_id UNION ALL SELECT node_id FROM selected)
SELECT r.id,r.source_entity_id source_id,r.target_entity_id target_id,r.type,
r.title_ru,r.title_ce,r.description_ru,r.description_ce,r.period_from,r.period_to,
(SELECT count(*) FROM catalog_relation_sources link JOIN catalog_sources source
 ON source.id=link.source_id WHERE link.relation_id=r.id
 AND source.status='published' AND source.is_verified) sources_count
FROM catalog_relations r WHERE r.status='published'
AND EXISTS (SELECT 1 FROM allowed WHERE node_id=r.source_entity_id)
AND EXISTS (SELECT 1 FROM allowed WHERE node_id=r.target_entity_id)
AND (CAST(:period_from AS integer) IS NULL OR r.period_to IS NULL
 OR r.period_to >= CAST(:period_from AS integer))
AND (CAST(:period_to AS integer) IS NULL OR r.period_from IS NULL
 OR r.period_from <= CAST(:period_to AS integer))
ORDER BY r.id LIMIT CAST(:edge_limit AS integer)"""
