from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from modules.submissions.domain import SubmissionStatus, SubmissionType


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SubmissionCreate(StrictSchema):
    type: SubmissionType
    related_entity_id: UUID | None
    settlement_id: UUID | None
    title: str = Field(max_length=300)
    description: str = Field(max_length=20_000)
    source_description: str = Field(max_length=5_000)
    author_name: str = Field(max_length=300)
    contact: str = Field(max_length=500)
    consent: bool


class SubmissionPatch(StrictSchema):
    expected_version: int = Field(ge=1)
    related_entity_id: UUID | None = None
    settlement_id: UUID | None = None
    title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=20_000)
    source_description: str | None = Field(default=None, max_length=5_000)
    author_name: str | None = Field(default=None, max_length=300)
    contact: str | None = Field(default=None, max_length=500)
    consent: bool | None = None

    @model_validator(mode="after")
    def reject_null_for_non_nullable_fields(self) -> Self:
        non_nullable = {
            "title",
            "description",
            "source_description",
            "author_name",
            "contact",
            "consent",
        }
        if any(getattr(self, name) is None for name in non_nullable & self.model_fields_set):
            raise ValueError("field cannot be null")
        return self

    def changes(self) -> dict[str, object]:
        mutable = self.model_fields_set - {"expected_version"}
        return {name: getattr(self, name) for name in mutable}


class SubmissionSubmit(StrictSchema):
    expected_version: int = Field(ge=1)


class SubmissionStatusRequest(StrictSchema):
    tracking_code: str = Field(min_length=40, max_length=128)


class SubmissionDraft(StrictSchema):
    id: UUID
    type: SubmissionType
    related_entity_id: UUID | None
    settlement_id: UUID | None
    title: str
    description: str
    source_description: str
    author_name: str
    contact: str
    consent: bool
    status: SubmissionStatus
    version: int
    tracking_code: str
    created_at: datetime
    updated_at: datetime


class SubmissionStatusView(StrictSchema):
    id: UUID
    tracking_code: str
    type: SubmissionType
    title: str
    status: SubmissionStatus
    public_comment: str | None
    submitted_at: datetime | None
    updated_at: datetime
