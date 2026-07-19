"""moderation claims and decision audit

Revision ID: 0010_07_2026_moderation
Revises: 0009_07_2026_submission_media
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_07_2026_moderation"
down_revision: str | Sequence[str] | None = "0009_07_2026_submission_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "moderation_claims",
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claimed_version", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("claimed_version > 1", name="ck_moderation_claim_version_positive"),
        sa.ForeignKeyConstraint(
            ["actor_account_id"],
            ["auth_accounts.id"],
            name="fk_moderation_claim_actor",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions_submissions.id"],
            name="fk_moderation_claim_submission",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_moderation_claims"),
        sa.UniqueConstraint("submission_id", name="uq_moderation_claim_submission_id"),
    )
    op.create_index(
        "ix_moderation_claim_actor_created",
        "moderation_claims",
        ["actor_account_id", "created_at", "id"],
    )
    op.create_table(
        "moderation_decision_audits",
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("from_version", sa.Integer(), nullable=False),
        sa.Column("to_version", sa.Integer(), nullable=False),
        sa.Column("public_comment", sa.Text(), nullable=False),
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
            "to_version = from_version + 1", name="ck_moderation_audit_version_step"
        ),
        sa.CheckConstraint(
            "length(trim(public_comment)) > 0",
            name="ck_moderation_audit_comment_nonempty",
        ),
        sa.CheckConstraint(
            "action IN ('rejected', 'needs_revision')",
            name="ck_moderation_audit_action",
        ),
        sa.ForeignKeyConstraint(
            ["actor_account_id"],
            ["auth_accounts.id"],
            name="fk_moderation_audit_actor",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions_submissions.id"],
            name="fk_moderation_audit_submission",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_moderation_decision_audits"),
    )
    op.create_index(
        "ix_moderation_audit_submission_created",
        "moderation_decision_audits",
        ["submission_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_moderation_audit_submission_created",
        table_name="moderation_decision_audits",
    )
    op.drop_table("moderation_decision_audits")
    op.drop_index("ix_moderation_claim_actor_created", table_name="moderation_claims")
    op.drop_table("moderation_claims")
