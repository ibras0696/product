from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def source_is_required_by_published_content(session: AsyncSession, source_id: UUID) -> bool:
    query = text(
        """SELECT EXISTS (
            SELECT 1
            FROM catalog_entity_sources current_link
            JOIN catalog_entities entity ON entity.id=current_link.entity_id
            WHERE current_link.source_id=:source_id AND entity.status='published'
              AND NOT EXISTS (
                SELECT 1 FROM catalog_entity_sources other_link
                JOIN catalog_sources other_source ON other_source.id=other_link.source_id
                WHERE other_link.entity_id=entity.id
                  AND other_link.source_id<>:source_id
                  AND other_source.status='published' AND other_source.is_verified IS TRUE
              )
        ) OR EXISTS (
            SELECT 1
            FROM catalog_relation_sources current_link
            JOIN catalog_relations relation ON relation.id=current_link.relation_id
            WHERE current_link.source_id=:source_id AND relation.status='published'
              AND NOT EXISTS (
                SELECT 1 FROM catalog_relation_sources other_link
                JOIN catalog_sources other_source ON other_source.id=other_link.source_id
                WHERE other_link.relation_id=relation.id
                  AND other_link.source_id<>:source_id
                  AND other_source.status='published' AND other_source.is_verified IS TRUE
              )
        )"""
    )
    return bool(await session.scalar(query, {"source_id": source_id}))
