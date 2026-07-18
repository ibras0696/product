from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from common.base_model import BaseDBModel


class MediaAsset(BaseDBModel):
    """Persisted media metadata; storage_key is never part of a public response."""

    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("width > 0", name="ck_media_asset_width_positive"),
        CheckConstraint("height > 0", name="ck_media_asset_height_positive"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_media_asset_status",
        ),
        Index("ix_media_assets_entity_public", "entity_id", "status", "created_at", "id"),
    )

    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_entities.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    public_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    preview_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(300), nullable=False)
    approximate_date: Mapped[str | None] = mapped_column(String(120))
    source_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)


class SubmissionMediaModel(BaseDBModel):
    __tablename__ = "media_submission_assets"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_media_submission_asset_size_positive"),
        CheckConstraint("size_bytes <= 10485760", name="ck_media_submission_asset_size_limit"),
        CheckConstraint("width > 0", name="ck_media_submission_asset_width_positive"),
        CheckConstraint("height > 0", name="ck_media_submission_asset_height_positive"),
        CheckConstraint(
            "width::bigint * height <= 40000000",
            name="ck_media_submission_asset_pixel_limit",
        ),
        CheckConstraint(
            "mime_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_media_submission_asset_mime_type",
        ),
        CheckConstraint("status = 'pending'", name="ck_media_submission_asset_status"),
        UniqueConstraint(
            "original_storage_key", name="uq_media_submission_asset_original_storage_key"
        ),
        UniqueConstraint(
            "preview_storage_key", name="uq_media_submission_asset_preview_storage_key"
        ),
        Index(
            "ix_media_submission_asset_submission_created",
            "submission_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_media_submission_asset_orphan_expiry",
            "expires_at",
            "submission_id",
            "id",
        ),
    )

    submission_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "submissions_submissions.id",
            name="fk_media_submission_asset_submission_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    original_storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    preview_storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(300), nullable=False)
    approximate_date: Mapped[str | None] = mapped_column(String(120))
    source_description: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "catalog_entities.id",
            name="fk_media_submission_asset_related_entity_id",
            ondelete="RESTRICT",
        )
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MediaUploadClaimModel(BaseDBModel):
    __tablename__ = "media_upload_claims"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_media_upload_claim_idempotency_key"),
        UniqueConstraint("media_id", name="uq_media_upload_claim_media_id"),
        CheckConstraint(
            "(state = 'processing' AND media_id IS NULL) OR "
            "(state = 'completed' AND media_id IS NOT NULL)",
            name="ck_media_upload_claim_state_media",
        ),
        Index("ix_media_upload_claim_created", "created_at", "id"),
    )

    idempotency_key: Mapped[UUID] = mapped_column(nullable=False)
    submission_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "submissions_submissions.id",
            name="fk_media_upload_claim_submission_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    media_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "media_submission_assets.id",
            name="fk_media_upload_claim_media_id",
            ondelete="CASCADE",
        )
    )
