"""catalog search indexes

Revision ID: 0007_07_2026_catalog_search
Revises: 0006_07_2026_catalog_periods
Create Date: 2026-07-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_07_2026_catalog_search"
down_revision: str | Sequence[str] | None = "0006_07_2026_catalog_periods"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """CREATE INDEX ix_catalog_entity_texts_title_trgm
        ON catalog_entity_texts USING gin (lower(title) gin_trgm_ops)"""
    )
    op.execute(
        """CREATE INDEX ix_catalog_entity_texts_title_fts_ru
        ON catalog_entity_texts USING gin (to_tsvector('russian',title))
        WHERE locale='ru'"""
    )
    op.execute(
        """CREATE INDEX ix_catalog_entity_texts_title_fts_ce
        ON catalog_entity_texts USING gin (to_tsvector('simple',title))
        WHERE locale='ce'"""
    )
    op.execute(
        """CREATE INDEX ix_catalog_entity_names_name_trgm
        ON catalog_entity_names USING gin (lower(name) gin_trgm_ops)"""
    )
    op.execute(
        """CREATE INDEX ix_catalog_entity_names_name_fts_ru
        ON catalog_entity_names USING gin (to_tsvector('russian',name))
        WHERE locale='ru'"""
    )
    op.execute(
        """CREATE INDEX ix_catalog_entity_names_name_fts_ce
        ON catalog_entity_names USING gin (to_tsvector('simple',name))
        WHERE locale='ce'"""
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_entity_names_name_fts_ce", table_name="catalog_entity_names")
    op.drop_index("ix_catalog_entity_names_name_fts_ru", table_name="catalog_entity_names")
    op.drop_index("ix_catalog_entity_names_name_trgm", table_name="catalog_entity_names")
    op.drop_index("ix_catalog_entity_texts_title_fts_ce", table_name="catalog_entity_texts")
    op.drop_index("ix_catalog_entity_texts_title_fts_ru", table_name="catalog_entity_texts")
    op.drop_index("ix_catalog_entity_texts_title_trgm", table_name="catalog_entity_texts")
    # pg_trgm can be shared by other schemas, so downgrade intentionally retains it.
