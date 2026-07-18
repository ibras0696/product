"""submission media and upload idempotency

Revision ID: 0009_07_2026_submission_media
Revises: 0008_07_2026_submissions
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_07_2026_submission_media"
down_revision: str | Sequence[str] | None = "0008_07_2026_submissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_submission_assets",
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_name", sa.String(length=500), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("original_storage_key", sa.String(length=1024), nullable=False),
        sa.Column("preview_storage_key", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=300), nullable=False),
        sa.Column("approximate_date", sa.String(length=120), nullable=True),
        sa.Column("source_description", sa.Text(), nullable=False),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint("size_bytes > 0", name="ck_media_submission_asset_size_positive"),
        sa.CheckConstraint("size_bytes <= 10485760", name="ck_media_submission_asset_size_limit"),
        sa.CheckConstraint("width > 0", name="ck_media_submission_asset_width_positive"),
        sa.CheckConstraint("height > 0", name="ck_media_submission_asset_height_positive"),
        sa.CheckConstraint(
            "width::bigint * height <= 40000000", name="ck_media_submission_asset_pixel_limit"
        ),
        sa.CheckConstraint(
            "mime_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_media_submission_asset_mime_type",
        ),
        sa.CheckConstraint("status = 'pending'", name="ck_media_submission_asset_status"),
        sa.ForeignKeyConstraint(
            ["related_entity_id"],
            ["catalog_entities.id"],
            name="fk_media_submission_asset_related_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions_submissions.id"],
            name="fk_media_submission_asset_submission_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_submission_assets"),
        sa.UniqueConstraint(
            "original_storage_key", name="uq_media_submission_asset_original_storage_key"
        ),
        sa.UniqueConstraint(
            "preview_storage_key", name="uq_media_submission_asset_preview_storage_key"
        ),
    )
    op.create_index(
        "ix_media_submission_asset_submission_created",
        "media_submission_assets",
        ["submission_id", "created_at", "id"],
    )
    op.create_index(
        "ix_media_submission_asset_orphan_expiry",
        "media_submission_assets",
        ["expires_at", "submission_id", "id"],
    )
    op.create_table(
        "media_upload_claims",
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=20), server_default="processing", nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            "(state = 'processing' AND media_id IS NULL) OR "
            "(state = 'completed' AND media_id IS NOT NULL)",
            name="ck_media_upload_claim_state_media",
        ),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_submission_assets.id"],
            name="fk_media_upload_claim_media_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions_submissions.id"],
            name="fk_media_upload_claim_submission_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_upload_claims"),
        sa.UniqueConstraint("idempotency_key", name="uq_media_upload_claim_idempotency_key"),
        sa.UniqueConstraint("media_id", name="uq_media_upload_claim_media_id"),
    )
    op.create_index("ix_media_upload_claim_created", "media_upload_claims", ["created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_media_upload_claim_created", table_name="media_upload_claims")
    op.drop_table("media_upload_claims")
    op.drop_index("ix_media_submission_asset_orphan_expiry", table_name="media_submission_assets")
    op.drop_index(
        "ix_media_submission_asset_submission_created", table_name="media_submission_assets"
    )
    op.drop_table("media_submission_assets")
