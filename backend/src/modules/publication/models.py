from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from common.base_model import BaseDBModel


class PublicationIdempotencyModel(BaseDBModel):
    __tablename__ = "publication_idempotency_records"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_publication_idempotency_key"),
        Index(
            "ix_publication_idempotency_submission_created",
            "submission_id",
            "created_at",
            "id",
        ),
    )

    idempotency_key: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    submission_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "submissions_submissions.id",
            name="fk_publication_idempotency_submission",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    actor_account_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "auth_accounts.id",
            name="fk_publication_idempotency_actor",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
