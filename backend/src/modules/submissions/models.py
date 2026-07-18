from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from common.base_model import BaseDBModel
from modules.submissions.domain import SubmissionStatus, SubmissionType


def enum_column(enum_type: type[Any], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        values_callable=lambda values: [value.value for value in values],
        create_constraint=True,
        validate_strings=True,
    )


class SubmissionModel(BaseDBModel):
    __tablename__ = "submissions_submissions"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_submissions_submission_version_positive"),
        UniqueConstraint(
            "owner_capability_hash", name="uq_submissions_submission_owner_capability_hash"
        ),
        UniqueConstraint("tracking_code_hash", name="uq_submissions_submission_tracking_code_hash"),
        Index(
            "ix_submissions_submission_status_created",
            "status",
            "created_at",
            "id",
        ),
        Index(
            "ix_submissions_submission_capability_expiry",
            "owner_capability_expires_at",
            "id",
        ),
    )

    type: Mapped[SubmissionType] = mapped_column(
        enum_column(SubmissionType, "submissions_submission_type"), nullable=False
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        enum_column(SubmissionStatus, "submissions_submission_status"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    related_entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "catalog_entities.id",
            name="fk_submissions_submission_related_entity_id",
            ondelete="RESTRICT",
        )
    )
    settlement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "catalog_entities.id",
            name="fk_submissions_submission_settlement_id",
            ondelete="RESTRICT",
        )
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_description: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[str] = mapped_column(String(300), nullable=False)
    contact: Mapped[str] = mapped_column(String(500), nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    owner_capability_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_capability_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    tracking_code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SubmissionStatusHistoryModel(BaseDBModel):
    __tablename__ = "submissions_status_history"
    __table_args__ = (
        CheckConstraint("sequence > 1", name="ck_submissions_status_history_sequence"),
        UniqueConstraint(
            "submission_id",
            "sequence",
            name="uq_submissions_status_history_submission_sequence",
        ),
        Index(
            "ix_submissions_status_history_order",
            "submission_id",
            "sequence",
        ),
    )

    submission_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "submissions_submissions.id",
            name="fk_submissions_status_history_submission_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    from_status: Mapped[SubmissionStatus] = mapped_column(
        enum_column(SubmissionStatus, "submissions_status_history_from"), nullable=False
    )
    to_status: Mapped[SubmissionStatus] = mapped_column(
        enum_column(SubmissionStatus, "submissions_status_history_to"), nullable=False
    )
    actor_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "auth_accounts.id",
            name="fk_submissions_status_history_actor_account_id",
            ondelete="SET NULL",
        )
    )
    public_comment: Mapped[str | None] = mapped_column(Text)
