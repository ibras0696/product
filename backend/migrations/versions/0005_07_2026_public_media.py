"""published media persistence

Revision ID: 0005_07_2026_public_media
Revises: 0004_07_2026_catalog_foundation
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_07_2026_public_media"
down_revision: str | Sequence[str] | None = "0004_07_2026_catalog_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("public_url", sa.String(length=2048), nullable=False),
        sa.Column("preview_url", sa.String(length=2048), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=300), nullable=False),
        sa.Column("approximate_date", sa.String(length=120), nullable=True),
        sa.Column("source_description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("width > 0", name="ck_media_asset_width_positive"),
        sa.CheckConstraint("height > 0", name="ck_media_asset_height_positive"),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')", name="ck_media_asset_status"
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["catalog_entities.id"],
            name="fk_media_assets_entity_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_assets"),
        sa.UniqueConstraint("storage_key", name="uq_media_assets_storage_key"),
    )
    op.create_index(
        "ix_media_assets_entity_public",
        "media_assets",
        ["entity_id", "status", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_media_assets_entity_public", table_name="media_assets")
    op.drop_table("media_assets")
