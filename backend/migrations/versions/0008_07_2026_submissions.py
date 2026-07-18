"""submission drafts and status history

Revision ID: 0008_07_2026_submissions
Revises: 0007_07_2026_catalog_search
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_07_2026_submissions"
down_revision: str | Sequence[str] | None = "0007_07_2026_catalog_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SUBMISSION_TYPES = (
    "new_entity",
    "update_entity",
    "new_relation",
    "new_source",
    "new_media",
    "report_error",
)
SUBMISSION_STATUSES = (
    "draft",
    "pending",
    "in_review",
    "needs_revision",
    "rejected",
    "published",
)


def submission_type() -> sa.Enum:
    return sa.Enum(
        *SUBMISSION_TYPES,
        name="submissions_submission_type",
        native_enum=False,
        create_constraint=True,
    )


def submission_status(name: str) -> sa.Enum:
    return sa.Enum(
        *SUBMISSION_STATUSES,
        name=name,
        native_enum=False,
        create_constraint=True,
    )


def upgrade() -> None:
    op.create_table(
        "submissions_submissions",
        sa.Column("type", submission_type(), nullable=False),
        sa.Column("status", submission_status("submissions_submission_status"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_description", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(length=300), nullable=False),
        sa.Column("contact", sa.String(length=500), nullable=False),
        sa.Column("consent", sa.Boolean(), nullable=False),
        sa.Column("owner_capability_hash", sa.String(length=128), nullable=False),
        sa.Column("owner_capability_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tracking_code_hash", sa.String(length=128), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("version > 0", name="ck_submissions_submission_version_positive"),
        sa.ForeignKeyConstraint(
            ["related_entity_id"],
            ["catalog_entities.id"],
            name="fk_submissions_submission_related_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["settlement_id"],
            ["catalog_entities.id"],
            name="fk_submissions_submission_settlement_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_submissions_submissions"),
        sa.UniqueConstraint(
            "owner_capability_hash", name="uq_submissions_submission_owner_capability_hash"
        ),
        sa.UniqueConstraint(
            "tracking_code_hash", name="uq_submissions_submission_tracking_code_hash"
        ),
    )
    op.create_index(
        "ix_submissions_submission_status_created",
        "submissions_submissions",
        ["status", "created_at", "id"],
    )
    op.create_index(
        "ix_submissions_submission_capability_expiry",
        "submissions_submissions",
        ["owner_capability_expires_at", "id"],
    )

    op.create_table(
        "submissions_status_history",
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "from_status",
            submission_status("submissions_status_history_from"),
            nullable=False,
        ),
        sa.Column(
            "to_status",
            submission_status("submissions_status_history_to"),
            nullable=False,
        ),
        sa.Column("actor_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("public_comment", sa.Text(), nullable=True),
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
        sa.CheckConstraint("sequence > 1", name="ck_submissions_status_history_sequence"),
        sa.ForeignKeyConstraint(
            ["actor_account_id"],
            ["auth_accounts.id"],
            name="fk_submissions_status_history_actor_account_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions_submissions.id"],
            name="fk_submissions_status_history_submission_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_submissions_status_history"),
        sa.UniqueConstraint(
            "submission_id",
            "sequence",
            name="uq_submissions_status_history_submission_sequence",
        ),
    )
    op.create_index(
        "ix_submissions_status_history_order",
        "submissions_status_history",
        ["submission_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_index("ix_submissions_status_history_order", table_name="submissions_status_history")
    op.drop_table("submissions_status_history")
    op.drop_index(
        "ix_submissions_submission_capability_expiry",
        table_name="submissions_submissions",
    )
    op.drop_index(
        "ix_submissions_submission_status_created",
        table_name="submissions_submissions",
    )
    op.drop_table("submissions_submissions")
