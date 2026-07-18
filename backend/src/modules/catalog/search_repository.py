from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from modules.catalog.domain import EntityType
from modules.catalog.search import SearchQuery, SearchRecord, SearchResult


class CatalogSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def district_exists(self, district_id: UUID) -> bool:
        result = await self._session.scalar(
            text("SELECT EXISTS (SELECT 1 FROM catalog_districts WHERE id=:id)"),
            {"id": district_id},
        )
        return bool(result)

    async def search(self, query: SearchQuery) -> SearchResult:
        parameters: dict[str, object] = {
            "q": query.text,
            "types": [item.value for item in query.types] or None,
            "district_id": query.district_id,
            "period_from": query.period_from,
            "period_to": query.period_to,
            "limit": query.limit,
            "offset": query.offset,
        }
        rows = (await self._session.execute(text(_SEARCH_SQL), parameters)).mappings().all()
        total = int(rows[0]["total_count"]) if rows else 0
        return SearchResult(
            items=tuple(self._record(row) for row in rows if row["id"] is not None),
            total=total,
        )

    @staticmethod
    def _record(row: RowMapping) -> SearchRecord:
        return SearchRecord(
            id=row["id"],
            type=EntityType(row["type"]),
            title_ru=row["title_ru"],
            title_ce=row["title_ce"],
            subtitle_ru=row["subtitle_ru"],
            subtitle_ce=row["subtitle_ce"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            cover_url=None,
            relations_count=int(row["relations_count"]),
            district_id=row["district_id"],
            rank=float(row["rank"]),
        )


_SEARCH_SQL = """WITH name_matches AS (
    SELECT t.entity_id,
      CASE WHEN lower(t.title)=:q THEN 1 ELSE 0 END exact_match,
      similarity(lower(t.title),:q) trigram_rank,0.0 fts_rank
    FROM catalog_entity_texts t
    WHERE t.locale='ru' AND lower(t.title) % :q
    UNION ALL
    SELECT t.entity_id,0,0.0,
      ts_rank(to_tsvector('russian',t.title),plainto_tsquery('russian',:q))
    FROM catalog_entity_texts t
    WHERE t.locale='ru'
      AND to_tsvector('russian',t.title) @@ plainto_tsquery('russian',:q)
    UNION ALL
    SELECT t.entity_id,CASE WHEN lower(t.title)=:q THEN 1 ELSE 0 END,
      similarity(lower(t.title),:q),0.0
    FROM catalog_entity_texts t
    WHERE t.locale='ce' AND lower(t.title) % :q
    UNION ALL
    SELECT t.entity_id,0,0.0,
      ts_rank(to_tsvector('simple',t.title),plainto_tsquery('simple',:q))
    FROM catalog_entity_texts t
    WHERE t.locale='ce'
      AND to_tsvector('simple',t.title) @@ plainto_tsquery('simple',:q)
    UNION ALL
    SELECT n.entity_id,
      CASE WHEN lower(n.name)=:q THEN 1 ELSE 0 END,
      similarity(lower(n.name),:q),0.0
    FROM catalog_entity_names n
    WHERE n.locale='ru' AND lower(n.name) % :q
    UNION ALL
    SELECT n.entity_id,0,0.0,
      ts_rank(to_tsvector('russian',n.name),plainto_tsquery('russian',:q))
    FROM catalog_entity_names n
    WHERE n.locale='ru'
      AND to_tsvector('russian',n.name) @@ plainto_tsquery('russian',:q)
    UNION ALL
    SELECT n.entity_id,CASE WHEN lower(n.name)=:q THEN 1 ELSE 0 END,
      similarity(lower(n.name),:q),0.0
    FROM catalog_entity_names n
    WHERE n.locale='ce' AND lower(n.name) % :q
    UNION ALL
    SELECT n.entity_id,0,0.0,
      ts_rank(to_tsvector('simple',n.name),plainto_tsquery('simple',:q))
    FROM catalog_entity_names n
    WHERE n.locale='ce'
      AND to_tsvector('simple',n.name) @@ plainto_tsquery('simple',:q)
), ranked AS (
    SELECT e.id,
      max(m.exact_match)*100.0 + max(m.trigram_rank)*10.0 + max(m.fts_rank) rank
    FROM name_matches m JOIN catalog_entities e ON e.id=m.entity_id
    WHERE e.status='published'
      AND (CAST(:types AS text[]) IS NULL OR e.type=ANY(CAST(:types AS text[])))
      AND (CAST(:district_id AS uuid) IS NULL OR e.district_id=CAST(:district_id AS uuid))
      AND (CAST(:period_from AS integer) IS NULL OR e.period_to IS NULL
           OR e.period_to>=CAST(:period_from AS integer))
      AND (CAST(:period_to AS integer) IS NULL OR e.period_from IS NULL
           OR e.period_from<=CAST(:period_to AS integer))
    GROUP BY e.id
), summary AS (
    SELECT count(*) total_count FROM ranked
), page AS (
    SELECT id,rank FROM ranked
    ORDER BY rank DESC,id LIMIT :limit OFFSET :offset
), relation_counts AS (
    SELECT p.id,count(peer.id) relations_count FROM page p
    LEFT JOIN catalog_relations r ON r.status='published'
      AND (r.source_entity_id=p.id OR r.target_entity_id=p.id)
    LEFT JOIN catalog_entities peer ON peer.id=CASE WHEN r.source_entity_id=p.id
      THEN r.target_entity_id ELSE r.source_entity_id END AND peer.status='published'
    GROUP BY p.id
)
SELECT e.id,e.type,e.district_id,ru.title title_ru,ce.title title_ce,
  ru.short_description subtitle_ru,ce.short_description subtitle_ce,
  ST_Y(e.coordinate) latitude,ST_X(e.coordinate) longitude,
  rc.relations_count,p.rank,s.total_count
FROM summary s LEFT JOIN page p ON true
LEFT JOIN catalog_entities e ON e.id=p.id
LEFT JOIN catalog_entity_texts ru ON ru.entity_id=e.id AND ru.locale='ru'
LEFT JOIN catalog_entity_texts ce ON ce.entity_id=e.id AND ce.locale='ce'
LEFT JOIN relation_counts rc ON rc.id=e.id
ORDER BY p.rank DESC,e.id"""
