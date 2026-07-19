from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from modules.catalog.domain import EntityType, ResearchStatus
from modules.catalog.public_text import public_description
from modules.catalog.schemas import (
    CatalogOptions,
    Coordinates,
    DistrictOption,
    EntityDetails,
    LocalizedText,
    MapEntity,
    MapEntityCollection,
    MapRelation,
    Page,
    PageMeta,
    PeriodOption,
    PublishedMedia,
    SourceView,
)
from modules.catalog.service import MapQuery

_MAP_RELATIONS_LIMIT = 5000


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def district_exists(self, district_id: UUID) -> bool:
        result = await self._session.scalar(
            text("SELECT EXISTS (SELECT 1 FROM catalog_districts WHERE id=:id)"),
            {"id": district_id},
        )
        return bool(result)

    async def map_entities(self, query: MapQuery) -> MapEntityCollection:
        clauses, parameters = self._map_filters(query)
        sql = self._map_sql(" AND ".join(clauses))
        rows = (await self._session.execute(text(sql), parameters)).mappings().all()
        truncated = len(rows) > query.limit
        entity_rows = rows[: query.limit]
        relations, relations_truncated = await self._map_relations(query)
        return MapEntityCollection(
            items=[self._map_entity(row) for row in entity_rows],
            relations=relations,
            truncated=truncated,
            relations_truncated=relations_truncated,
        )

    async def _map_relations(self, query: MapQuery) -> tuple[list[MapRelation], bool]:
        rows = (
            (
                await self._session.execute(
                    text(_MAP_RELATIONS_SQL),
                    {
                        "limit": _MAP_RELATIONS_LIMIT + 1,
                        "types": [value.value for value in query.types],
                        "filter_types": bool(query.types),
                    },
                )
            )
            .mappings()
            .all()
        )
        return (
            [MapRelation(**row) for row in rows[:_MAP_RELATIONS_LIMIT]],
            len(rows) > _MAP_RELATIONS_LIMIT,
        )

    async def get_entity(self, entity_id: UUID) -> EntityDetails | None:
        row = (
            (await self._session.execute(text(_ENTITY_DETAILS_SQL), {"id": entity_id}))
            .mappings()
            .one_or_none()
        )
        return self._entity_details(row) if row else None

    async def list_entity_sources(
        self, entity_id: UUID, limit: int, offset: int
    ) -> Page[SourceView] | None:
        return await self._source_page(
            "catalog_entity_sources", "entity_id", entity_id, limit, offset
        )

    async def list_relation_sources(
        self, relation_id: UUID, limit: int, offset: int
    ) -> Page[SourceView] | None:
        return await self._source_page(
            "catalog_relation_sources", "relation_id", relation_id, limit, offset
        )

    async def list_entity_media(
        self, entity_id: UUID, limit: int, offset: int
    ) -> Page[PublishedMedia] | None:
        summary = (
            (await self._session.execute(text(_MEDIA_SUMMARY_SQL), {"entity_id": entity_id}))
            .mappings()
            .one()
        )
        if not summary["visible"]:
            return None
        rows = (
            (
                await self._session.execute(
                    text(_MEDIA_PAGE_SQL),
                    {"entity_id": entity_id, "limit": limit, "offset": offset},
                )
            )
            .mappings()
            .all()
        )
        return Page[PublishedMedia](
            items=[
                PublishedMedia(**{field: row[field] for field in _MEDIA_FIELDS}) for row in rows
            ],
            meta=PageMeta(limit=limit, offset=offset, total=int(summary["total"])),
        )

    async def get_options(self) -> CatalogOptions:
        rows = (
            (
                await self._session.execute(
                    text("SELECT id,title_ru,title_ce FROM catalog_districts ORDER BY title_ru,id")
                )
            )
            .mappings()
            .all()
        )
        districts = [
            DistrictOption(
                id=row["id"], title=LocalizedText(ru=row["title_ru"], ce=row["title_ce"])
            )
            for row in rows
        ]
        period_rows = (
            (
                await self._session.execute(
                    text(
                        """SELECT key,title_ru,title_ce,period_from,period_to
                    FROM catalog_periods ORDER BY period_from,period_to,key"""
                    )
                )
            )
            .mappings()
            .all()
        )
        periods = [
            PeriodOption(
                id=row["key"],
                title=LocalizedText(ru=row["title_ru"], ce=row["title_ce"]),
                period_from=row["period_from"],
                period_to=row["period_to"],
            )
            for row in period_rows
        ]
        return CatalogOptions(
            districts=districts,
            periods=periods,
            entity_types=list(EntityType),
            research_statuses=list(ResearchStatus),
        )

    @staticmethod
    def _map_filters(query: MapQuery) -> tuple[list[str], dict[str, object]]:
        clauses = ["e.status='published'", "e.coordinate && ST_MakeEnvelope(:a,:b,:c,:d,4326)"]
        parameters: dict[str, object] = {
            "a": query.bbox[0],
            "b": query.bbox[1],
            "c": query.bbox[2],
            "d": query.bbox[3],
            "limit": query.limit + 1,
        }
        if query.types:
            clauses.append("e.type = ANY(:types)")
            parameters["types"] = [value.value for value in query.types]
        if query.research_statuses:
            clauses.append(f"{_RESEARCH_STATUS_SQL} = ANY(:research_statuses)")
            parameters["research_statuses"] = [value.value for value in query.research_statuses]
        if query.district_id:
            clauses.append("e.district_id=:district_id")
            parameters["district_id"] = query.district_id
        if query.period_from is not None:
            clauses.append("(e.period_to IS NULL OR e.period_to >= :period_from)")
            parameters["period_from"] = query.period_from
        if query.period_to is not None:
            clauses.append("(e.period_from IS NULL OR e.period_from <= :period_to)")
            parameters["period_to"] = query.period_to
        return clauses, parameters

    @staticmethod
    def _map_sql(filters: str) -> str:
        return f"""SELECT e.id,e.type,e.district_id,ru.title AS title_ru,ce.title AS title_ce,
        ST_Y(e.coordinate) latitude,ST_X(e.coordinate) longitude,
        {_RESEARCH_STATUS_SQL} research_status,
        COALESCE((SELECT media.preview_url FROM media_assets media
          WHERE media.entity_id=e.id AND media.status='published'
          ORDER BY media.created_at,media.id LIMIT 1),
        (SELECT source.archive_reference FROM catalog_entity_sources link
          JOIN catalog_sources source ON source.id=link.source_id
          WHERE link.entity_id=e.id AND source.type='photo'
            AND source.status='published' AND source.is_verified
            AND source.archive_reference LIKE 'https://%'
          ORDER BY source.created_at,source.id LIMIT 1)) cover_url,
        (SELECT count(*) FROM catalog_relations r WHERE r.status='published'
          AND (r.source_entity_id=e.id OR r.target_entity_id=e.id)
          AND EXISTS (SELECT 1 FROM catalog_entities peer
            WHERE peer.id=CASE WHEN r.source_entity_id=e.id
              THEN r.target_entity_id ELSE r.source_entity_id END
            AND peer.status='published')) relations_count
        FROM catalog_entities e
        JOIN catalog_entity_texts ru ON ru.entity_id=e.id AND ru.locale='ru'
        LEFT JOIN catalog_entity_texts ce ON ce.entity_id=e.id AND ce.locale='ce'
        WHERE {filters} ORDER BY e.id LIMIT :limit"""

    @staticmethod
    def _map_entity(row: RowMapping) -> MapEntity:
        values = row
        return MapEntity(
            id=values["id"],
            type=values["type"],
            title=LocalizedText(ru=values["title_ru"], ce=values["title_ce"]),
            coordinates=Coordinates(latitude=values["latitude"], longitude=values["longitude"]),
            relations_count=values["relations_count"],
            cover_url=values["cover_url"],
            district_id=values["district_id"],
            research_status=values["research_status"],
        )

    async def _source_page(
        self, link_table: str, parent_column: str, parent_id: UUID, limit: int, offset: int
    ) -> Page[SourceView] | None:
        parent_table = "catalog_entities" if parent_column == "entity_id" else "catalog_relations"
        visible = await self._session.scalar(
            text(
                f"SELECT EXISTS (SELECT 1 FROM {parent_table} WHERE id=:id AND status='published')"
            ),
            {"id": parent_id},
        )
        if not visible:
            return None
        total = await self._session.scalar(
            text(
                f"""SELECT count(*) FROM {link_table} link
                JOIN catalog_sources s ON s.id=link.source_id
                WHERE link.{parent_column}=:id
                AND s.status='published' AND s.is_verified"""
            ),
            {"id": parent_id},
        )
        sql = _SOURCE_PAGE_SQL.format(link_table=link_table, parent_column=parent_column)
        rows = (
            (
                await self._session.execute(
                    text(sql), {"id": parent_id, "limit": limit, "offset": offset}
                )
            )
            .mappings()
            .all()
        )
        return Page[SourceView](
            items=[SourceView(**{key: row[key] for key in _SOURCE_FIELDS}) for row in rows],
            meta=PageMeta(limit=limit, offset=offset, total=int(total or 0)),
        )

    @staticmethod
    def _entity_details(row: RowMapping) -> EntityDetails:
        values = row
        coordinates = None
        if values["latitude"] is not None:
            coordinates = Coordinates(latitude=values["latitude"], longitude=values["longitude"])
        return EntityDetails(
            **{key: values[key] for key in _ENTITY_FIELDS},
            title=LocalizedText(ru=values["title_ru"], ce=values["title_ce"]),
            short_description=LocalizedText(ru=values["short_ru"], ce=values["short_ce"]),
            full_description=LocalizedText(
                ru=public_description(values["full_ru"]),
                ce=(public_description(values["full_ce"]) if values["full_ce"] else None),
            ),
            coordinates=coordinates,
            cover_url=values["cover_url"],
            status="published",
            research_status=values["research_status"],
        )


_SOURCE_FIELDS = (
    "id",
    "title",
    "type",
    "author",
    "publisher",
    "publication_year",
    "url",
    "archive_reference",
    "description",
    "is_verified",
)
_ENTITY_FIELDS = (
    "id",
    "type",
    "slug",
    "period_from",
    "period_to",
    "relations_count",
    "sources_count",
    "media_count",
)

_ENTITY_DETAILS_SQL = """SELECT e.id,e.type,e.slug,e.period_from,e.period_to,
ST_Y(e.coordinate) latitude,ST_X(e.coordinate) longitude,ru.title title_ru,ce.title title_ce,
ru.short_description short_ru,ce.short_description short_ce,
ru.full_description full_ru,ce.full_description full_ce,
CASE WHEN ru.full_description LIKE '%Статус исследования: needs_review.%'
 THEN 'needs_review' ELSE 'verified' END research_status,
COALESCE((SELECT media.preview_url FROM media_assets media
 WHERE media.entity_id=e.id AND media.status='published'
 ORDER BY media.created_at,media.id LIMIT 1),
(SELECT source.archive_reference FROM catalog_entity_sources link
 JOIN catalog_sources source ON source.id=link.source_id
 WHERE link.entity_id=e.id AND source.type='photo'
   AND source.status='published' AND source.is_verified
   AND source.archive_reference LIKE 'https://%'
 ORDER BY source.created_at,source.id LIMIT 1)) cover_url,
(SELECT count(*) FROM catalog_relations r WHERE r.status='published'
 AND (r.source_entity_id=e.id OR r.target_entity_id=e.id)
 AND EXISTS (SELECT 1 FROM catalog_entities peer
   WHERE peer.id=CASE WHEN r.source_entity_id=e.id
     THEN r.target_entity_id ELSE r.source_entity_id END
   AND peer.status='published')) relations_count,
(SELECT count(*) FROM catalog_entity_sources es
 JOIN catalog_sources s ON s.id=es.source_id
 WHERE es.entity_id=e.id AND s.status='published' AND s.is_verified) sources_count
,(SELECT count(*) FROM media_assets m
  WHERE m.entity_id=e.id AND m.status='published') media_count
FROM catalog_entities e JOIN catalog_entity_texts ru ON ru.entity_id=e.id AND ru.locale='ru'
LEFT JOIN catalog_entity_texts ce ON ce.entity_id=e.id AND ce.locale='ce'
WHERE e.id=:id AND e.status='published'"""

_RESEARCH_STATUS_SQL = """CASE
WHEN ru.full_description LIKE '%Статус исследования: needs_review.%'
THEN 'needs_review' ELSE 'verified' END"""

_SOURCE_PAGE_SQL = """SELECT s.id,s.title,s.type,s.author,s.publisher,s.publication_year,s.url,
s.archive_reference,s.description,s.is_verified FROM {link_table} link
JOIN catalog_sources s ON s.id=link.source_id WHERE link.{parent_column}=:id
AND s.status='published' AND s.is_verified ORDER BY s.created_at,s.id LIMIT :limit OFFSET :offset"""

_MEDIA_FIELDS = (
    "id",
    "public_url",
    "preview_url",
    "mime_type",
    "width",
    "height",
    "caption",
    "author",
    "approximate_date",
    "source_description",
)
_MEDIA_SUMMARY_SQL = """SELECT
EXISTS(SELECT 1 FROM catalog_entities WHERE id=:entity_id AND status='published') visible,
(SELECT count(*) FROM media_assets WHERE entity_id=:entity_id AND status='published') total"""
_MEDIA_PAGE_SQL = """SELECT id,public_url,preview_url,mime_type,width,height,caption,author,
approximate_date,source_description FROM media_assets
WHERE entity_id=:entity_id AND status='published' ORDER BY created_at,id
LIMIT :limit OFFSET :offset"""

_MAP_RELATIONS_SQL = """SELECT relation.id,
relation.source_entity_id source_id,relation.target_entity_id target_id,relation.type,
source.type source_type,source_text.title source_title,
target.type target_type,target_text.title target_title
FROM catalog_relations relation
JOIN catalog_entities source ON source.id=relation.source_entity_id
JOIN catalog_entities target ON target.id=relation.target_entity_id
JOIN catalog_entity_texts source_text
  ON source_text.entity_id=source.id AND source_text.locale='ru'
JOIN catalog_entity_texts target_text
  ON target_text.entity_id=target.id AND target_text.locale='ru'
WHERE relation.status='published' AND source.status='published' AND target.status='published'
AND (NOT :filter_types OR source.type=ANY(:types) OR target.type=ANY(:types))
ORDER BY relation.id LIMIT :limit"""
