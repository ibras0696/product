from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from modules.catalog.timeline import TimelineEvent, TimelineQuery, TimelineResult


class TimelineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def district_exists(self, district_id: UUID) -> bool:
        result = await self._session.scalar(
            text("SELECT EXISTS (SELECT 1 FROM catalog_districts WHERE id=:id)"),
            {"id": district_id},
        )
        return bool(result)

    async def list_events(self, query: TimelineQuery) -> TimelineResult:
        rows = (
            (
                await self._session.execute(
                    text(_TIMELINE_SQL),
                    {
                        "q": query.text,
                        "district_id": query.district_id,
                        "period_from": query.period_from,
                        "period_to": query.period_to,
                        "limit": query.limit,
                        "offset": query.offset,
                    },
                )
            )
            .mappings()
            .all()
        )
        total = int(rows[0]["total_count"]) if rows else 0
        return TimelineResult(
            items=tuple(self._event(row) for row in rows if row["id"] is not None),
            total=total,
        )

    @staticmethod
    def _event(row: RowMapping) -> TimelineEvent:
        return TimelineEvent(
            id=row["id"],
            title_ru=row["title_ru"],
            title_ce=row["title_ce"],
            short_description_ru=row["short_description_ru"],
            short_description_ce=row["short_description_ce"],
            period_from=row["period_from"],
            period_to=row["period_to"],
            latitude=row["latitude"],
            longitude=row["longitude"],
        )


_TIMELINE_SQL = """WITH filtered AS (
  SELECT e.id,e.period_from,e.period_to,e.coordinate
  FROM catalog_entities e
  WHERE e.status='published' AND e.type='event'
    AND (CAST(:district_id AS uuid) IS NULL OR e.district_id=CAST(:district_id AS uuid))
    AND (CAST(:q AS text) IS NULL OR EXISTS (
      SELECT 1 FROM catalog_entity_texts search_text
      WHERE search_text.entity_id=e.id
        AND (lower(search_text.title) LIKE '%%'||CAST(:q AS text)||'%%'
             OR lower(search_text.short_description) LIKE '%%'||CAST(:q AS text)||'%%')
    ))
    AND (CAST(:period_from AS integer) IS NULL OR e.period_to IS NULL
         OR e.period_to>=CAST(:period_from AS integer))
    AND (CAST(:period_to AS integer) IS NULL OR e.period_from IS NULL
         OR e.period_from<=CAST(:period_to AS integer))
), summary AS (
  SELECT count(*) total_count FROM filtered
), page AS (
  SELECT * FROM filtered
  ORDER BY period_from NULLS LAST,period_to NULLS LAST,id
  LIMIT :limit OFFSET :offset
)
SELECT p.id,p.period_from,p.period_to,
  ru.title title_ru,ce.title title_ce,
  ru.short_description short_description_ru,
  ce.short_description short_description_ce,
  ST_Y(p.coordinate) latitude,ST_X(p.coordinate) longitude,s.total_count
FROM summary s LEFT JOIN page p ON true
LEFT JOIN catalog_entity_texts ru ON ru.entity_id=p.id AND ru.locale='ru'
LEFT JOIN catalog_entity_texts ce ON ce.entity_id=p.id AND ce.locale='ce'
ORDER BY p.period_from NULLS LAST,p.period_to NULLS LAST,p.id"""
