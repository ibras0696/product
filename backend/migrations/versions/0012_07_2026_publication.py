"""publication idempotency records

Revision ID: 0012_07_2026_publication
Revises: 0011_07_2026_audit
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_07_2026_publication"
down_revision: str | Sequence[str] | None = "0011_07_2026_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "publication_idempotency_records",
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["actor_account_id"],
            ["auth_accounts.id"],
            name="fk_publication_idempotency_actor",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions_submissions.id"],
            name="fk_publication_idempotency_submission",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_publication_idempotency_records"),
        sa.UniqueConstraint("idempotency_key", name="uq_publication_idempotency_key"),
    )
    op.create_index(
        "ix_publication_idempotency_submission_created",
        "publication_idempotency_records",
        ["submission_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_publication_idempotency_submission_created",
        table_name="publication_idempotency_records",
    )
    op.drop_table("publication_idempotency_records")
