"""catalog period options

Revision ID: 0006_07_2026_catalog_periods
Revises: 0005_07_2026_public_media
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_07_2026_catalog_periods"
down_revision: str | Sequence[str] | None = "0005_07_2026_public_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_periods",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("title_ru", sa.String(length=240), nullable=False),
        sa.Column("title_ce", sa.String(length=240), nullable=True),
        sa.Column("period_from", sa.Integer(), nullable=True),
        sa.Column("period_to", sa.Integer(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(
            "period_from IS NULL OR period_to IS NULL OR period_from <= period_to",
            name="ck_catalog_period_order",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_periods"),
        sa.UniqueConstraint("key", name="uq_catalog_period_key"),
    )
    op.create_index(
        "ix_catalog_periods_order",
        "catalog_periods",
        ["display_order", "key"],
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_periods_order", table_name="catalog_periods")
    op.drop_table("catalog_periods")
