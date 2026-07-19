from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.exports.service import ExportRecord, ExportStatus


class SqlCatalogExportRepository:
    """Read-only adapter whose SQL selects are the export security allowlist."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_records(self, status: ExportStatus) -> int:
        result = await self._session.scalar(text(_COUNT_SQL), _parameters(status))
        return int(result or 0)

    async def iter_records(self, status: ExportStatus) -> AsyncGenerator[ExportRecord]:
        parameters = _parameters(status)
        for record_type, query in _EXPORT_QUERIES:
            result = await self._session.stream(text(query), parameters)
            try:
                async for row in result.mappings():
                    yield ExportRecord(record_type=record_type, values=dict(row))
            finally:
                await result.close()


def _parameters(status: ExportStatus) -> dict[str, object]:
    return {"published_only": status is ExportStatus.PUBLISHED}


_ENTITY_FILTER = "(NOT CAST(:published_only AS boolean) OR e.status='published')"
_RELATION_FILTER = "(NOT CAST(:published_only AS boolean) OR r.status='published')"
_SOURCE_FILTER = "(NOT CAST(:published_only AS boolean) OR s.status='published')"
_MEDIA_FILTER = "(NOT CAST(:published_only AS boolean) OR m.status='published')"

_COUNT_SQL = f"""SELECT
 (SELECT count(*) FROM catalog_entities e WHERE {_ENTITY_FILTER}) +
 (SELECT count(*) FROM catalog_entity_texts t JOIN catalog_entities e ON e.id=t.entity_id
   WHERE {_ENTITY_FILTER}) +
 (SELECT count(*) FROM catalog_entity_names n JOIN catalog_entities e ON e.id=n.entity_id
   WHERE {_ENTITY_FILTER}) +
 (SELECT count(*) FROM catalog_relations r WHERE {_RELATION_FILTER}) +
 (SELECT count(*) FROM catalog_sources s WHERE {_SOURCE_FILTER}) +
 (SELECT count(*) FROM catalog_entity_sources link
   JOIN catalog_entities e ON e.id=link.entity_id JOIN catalog_sources s ON s.id=link.source_id
   WHERE {_ENTITY_FILTER} AND {_SOURCE_FILTER}) +
 (SELECT count(*) FROM catalog_relation_sources link
   JOIN catalog_relations r ON r.id=link.relation_id JOIN catalog_sources s ON s.id=link.source_id
   WHERE {_RELATION_FILTER} AND {_SOURCE_FILTER}) +
 (SELECT count(*) FROM media_assets m WHERE {_MEDIA_FILTER})"""

_EXPORT_QUERIES = (
    (
        "entity",
        f"""SELECT e.id,e.type,e.slug,e.status,e.period_from,e.period_to,e.district_id,
        ST_Y(e.coordinate) latitude,ST_X(e.coordinate) longitude
        FROM catalog_entities e WHERE {_ENTITY_FILTER} ORDER BY e.id""",
    ),
    (
        "entity_text",
        f"""SELECT t.id,t.entity_id,t.locale,t.title,
        t.short_description,t.full_description
        FROM catalog_entity_texts t JOIN catalog_entities e ON e.id=t.entity_id
        WHERE {_ENTITY_FILTER} ORDER BY t.entity_id,t.locale,t.id""",
    ),
    (
        "entity_name",
        f"""SELECT n.id,n.entity_id,n.locale,n.name FROM catalog_entity_names n
        JOIN catalog_entities e ON e.id=n.entity_id WHERE {_ENTITY_FILTER}
        ORDER BY n.entity_id,n.locale,n.name,n.id""",
    ),
    (
        "relation",
        f"""SELECT r.id,r.source_entity_id,r.target_entity_id,r.type,r.status,
        r.title_ru,r.title_ce,r.description_ru,r.description_ce,r.period_from,r.period_to
        FROM catalog_relations r WHERE {_RELATION_FILTER} ORDER BY r.id""",
    ),
    (
        "source",
        f"""SELECT s.id,s.title,s.type,s.status,s.author,s.publisher,s.publication_year,s.url,
        s.archive_reference,s.description,s.is_verified FROM catalog_sources s
        WHERE {_SOURCE_FILTER} ORDER BY s.id""",
    ),
    (
        "entity_source",
        f"""SELECT link.id,link.entity_id,link.source_id FROM catalog_entity_sources link
        JOIN catalog_entities e ON e.id=link.entity_id JOIN catalog_sources s ON s.id=link.source_id
        WHERE {_ENTITY_FILTER} AND {_SOURCE_FILTER}
        ORDER BY link.entity_id,link.source_id,link.id""",
    ),
    (
        "relation_source",
        f"""SELECT link.id,link.relation_id,link.source_id FROM catalog_relation_sources link
        JOIN catalog_relations r ON r.id=link.relation_id
        JOIN catalog_sources s ON s.id=link.source_id
        WHERE {_RELATION_FILTER} AND {_SOURCE_FILTER}
        ORDER BY link.relation_id,link.source_id,link.id""",
    ),
    (
        "media",
        f"""SELECT m.id,m.entity_id,m.status,m.public_url,m.preview_url,m.mime_type,
        m.width,m.height,
        m.caption,m.author,m.approximate_date,m.source_description
        FROM media_assets m WHERE {_MEDIA_FILTER} ORDER BY m.entity_id,m.id""",
    ),
)
