from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.base_model import BaseDBModel

ACTIVE_STATUS: Final = "active"


class Account(BaseDBModel):
    __tablename__ = "auth_accounts"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ACTIVE_STATUS, nullable=False)
    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class AuthSession(BaseDBModel):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_account_active", "account_id", "revoked_at"),
        Index("ix_auth_sessions_idle_expiry", "idle_expires_at"),
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth_accounts.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    account: Mapped[Account] = relationship(back_populates="sessions")
