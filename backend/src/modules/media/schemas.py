from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from modules.media.repository import MediaRecord


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SubmissionMediaMetadata(StrictSchema):
    caption: str = Field(max_length=2_000)
    author: str = Field(max_length=300)
    approximate_date: str | None = Field(default=None, max_length=120)
    source_description: str = Field(max_length=5_000)
    related_entity_id: UUID | None = None


class SubmissionMediaPatch(StrictSchema):
    caption: str | None = Field(default=None, max_length=2_000)
    author: str | None = Field(default=None, max_length=300)
    approximate_date: str | None = Field(default=None, max_length=120)
    source_description: str | None = Field(default=None, max_length=5_000)
    related_entity_id: UUID | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> Self:
        required = {"caption", "author", "source_description"}
        if any(getattr(self, field) is None for field in required & self.model_fields_set):
            raise ValueError("field cannot be null")
        return self

    def changes(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in self.model_fields_set}


class SubmissionMedia(StrictSchema):
    id: UUID
    submission_id: UUID
    original_name: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    preview_url: str
    caption: str
    author: str
    approximate_date: str | None
    source_description: str
    related_entity_id: UUID | None
    status: str = "pending"

    @classmethod
    def from_record(cls, record: MediaRecord) -> "SubmissionMedia":
        return cls(
            id=record.id,
            submission_id=record.submission_id,
            original_name=record.original_name,
            mime_type=record.mime_type,
            size_bytes=record.size_bytes,
            width=record.width,
            height=record.height,
            preview_url=(f"/api/v1/submissions/{record.submission_id}/media/{record.id}/preview"),
            caption=record.caption,
            author=record.author,
            approximate_date=record.approximate_date,
            source_description=record.source_description,
            related_entity_id=record.related_entity_id,
        )
