from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuditEntry(StrictSchema):
    id: UUID
    actor_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    resource_version: int
    created_at: datetime


class AuditPage(StrictSchema):
    items: list[AuditEntry]
    limit: int
    offset: int
    total: int = Field(ge=0)


class AuditListRequest(StrictSchema):
    actor_id: UUID | None = None
    action: str | None = Field(default=None, max_length=120)
    created_from: datetime | None = None
    created_to: datetime | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
