from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from modules.moderation.contracts import PublishAction


class PublishResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: UUID
    status: Literal["published"] = "published"
    action: PublishAction
    published_entity_ids: list[UUID]
    published_relation_ids: list[UUID]
    published_source_ids: list[UUID]
    published_media_ids: list[UUID]
    audit_id: UUID
