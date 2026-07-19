"""generic mutation audit

Revision ID: 0011_07_2026_audit
Revises: 0010_07_2026_moderation
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_07_2026_audit"
down_revision: str | Sequence[str] | None = "0010_07_2026_moderation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_entries",
        sa.Column("actor_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_version", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("resource_version > 0", name="ck_audit_entry_resource_version"),
        sa.ForeignKeyConstraint(["actor_account_id"], ["auth_accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_entries"),
    )
    op.create_index("ix_audit_entries_created", "audit_entries", ["created_at", "id"])
    op.create_index(
        "ix_audit_entries_actor_created", "audit_entries", ["actor_account_id", "created_at", "id"]
    )
    op.create_index(
        "ix_audit_entries_action_created", "audit_entries", ["action", "created_at", "id"]
    )


def downgrade() -> None:
    op.drop_index("ix_audit_entries_action_created", table_name="audit_entries")
    op.drop_index("ix_audit_entries_actor_created", table_name="audit_entries")
    op.drop_index("ix_audit_entries_created", table_name="audit_entries")
    op.drop_table("audit_entries")
