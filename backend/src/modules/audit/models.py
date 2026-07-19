from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from common.base_model import BaseDBModel


class AuditEntryModel(BaseDBModel):
    __tablename__ = "audit_entries"
    __table_args__ = (
        CheckConstraint("resource_version > 0", name="ck_audit_entry_resource_version"),
        Index("ix_audit_entries_created", "created_at", "id"),
        Index("ix_audit_entries_actor_created", "actor_account_id", "created_at", "id"),
        Index("ix_audit_entries_action_created", "action", "created_at", "id"),
    )

    actor_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(nullable=False)
    resource_version: Mapped[int] = mapped_column(Integer, nullable=False)
