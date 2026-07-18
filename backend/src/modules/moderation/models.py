from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from common.base_model import BaseDBModel


class ModerationClaimModel(BaseDBModel):
    __tablename__ = "moderation_claims"
    __table_args__ = (
        UniqueConstraint("submission_id", name="uq_moderation_claim_submission_id"),
        CheckConstraint("claimed_version > 1", name="ck_moderation_claim_version_positive"),
        Index("ix_moderation_claim_actor_created", "actor_account_id", "created_at", "id"),
    )

    submission_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "submissions_submissions.id",
            name="fk_moderation_claim_submission",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    actor_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_accounts.id", name="fk_moderation_claim_actor", ondelete="RESTRICT"),
        nullable=False,
    )
    claimed_version: Mapped[int] = mapped_column(Integer, nullable=False)


class ModerationDecisionAuditModel(BaseDBModel):
    __tablename__ = "moderation_decision_audits"
    __table_args__ = (
        CheckConstraint("to_version = from_version + 1", name="ck_moderation_audit_version_step"),
        CheckConstraint(
            "length(trim(public_comment)) > 0", name="ck_moderation_audit_comment_nonempty"
        ),
        CheckConstraint(
            "action IN ('rejected', 'needs_revision')", name="ck_moderation_audit_action"
        ),
        Index("ix_moderation_audit_submission_created", "submission_id", "created_at", "id"),
    )

    submission_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "submissions_submissions.id",
            name="fk_moderation_audit_submission",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    actor_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_accounts.id", name="fk_moderation_audit_actor", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    from_version: Mapped[int] = mapped_column(Integer, nullable=False)
    to_version: Mapped[int] = mapped_column(Integer, nullable=False)
    public_comment: Mapped[str] = mapped_column(Text, nullable=False)
