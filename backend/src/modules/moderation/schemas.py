from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from modules.catalog.public import EntityType, RelationType, SourceType
from modules.moderation.domain import PublishAction
from modules.submissions.contracts import SubmissionStatus, SubmissionType


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalizedText(StrictSchema):
    ru: str = Field(min_length=1, max_length=500)
    ce: str | None


class Coordinates(StrictSchema):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class EntityInput(StrictSchema):
    type: EntityType
    slug: str = Field(min_length=1, max_length=200)
    title: LocalizedText
    short_description: LocalizedText
    full_description: LocalizedText
    coordinates: Coordinates | None
    period_from: int | None
    period_to: int | None
    district_id: UUID | None = None


class EntityPatch(StrictSchema):
    slug: str | None = Field(default=None, min_length=1, max_length=200)
    title: LocalizedText | None = None
    short_description: LocalizedText | None = None
    full_description: LocalizedText | None = None
    coordinates: Coordinates | None = None
    period_from: int | None = None
    period_to: int | None = None
    district_id: UUID | None = None


class RelationInput(StrictSchema):
    source_entity_id: UUID
    target_entity_id: UUID
    type: RelationType
    title: LocalizedText
    description: LocalizedText
    period_from: int | None
    period_to: int | None


class SourceInput(StrictSchema):
    title: str = Field(min_length=1, max_length=500)
    type: SourceType
    author: str | None
    publisher: str | None
    publication_year: int | None
    url: str | None
    archive_reference: str | None
    description: str = Field(max_length=5000)


class CreateEntityPayload(StrictSchema):
    entity: EntityInput
    relations: list[RelationInput] = Field(max_length=100)
    sources: list[SourceInput] = Field(max_length=100)
    approved_media_ids: list[UUID] = Field(max_length=100)


class UpdateEntityPayload(StrictSchema):
    entity_id: UUID
    entity_patch: EntityPatch
    sources: list[SourceInput] = Field(max_length=100)
    approved_media_ids: list[UUID] = Field(max_length=100)


class CreateRelationPayload(StrictSchema):
    relation: RelationInput
    sources: list[SourceInput] = Field(min_length=1, max_length=100)


class AddSourcePayload(StrictSchema):
    target_type: Literal["entity", "relation"]
    target_id: UUID
    source: SourceInput


class PublishMediaPayload(StrictSchema):
    target_entity_id: UUID
    approved_media_ids: list[UUID] = Field(min_length=1, max_length=100)


class ResolveReportPayload(StrictSchema):
    resolution: str = Field(min_length=1, max_length=5000)
    entity_patch: EntityPatch | None = None
    archive_entity_id: UUID | None = None

    @model_validator(mode="after")
    def one_optional_resolution_action(self) -> Self:
        if self.entity_patch is not None and self.archive_entity_id is not None:
            raise ValueError("entity_patch and archive_entity_id are mutually exclusive")
        return self


class PublishBase(StrictSchema):
    action: PublishAction
    expected_version: int = Field(ge=1)
    idempotency_key: UUID
    comment: str = Field(min_length=1, max_length=5000)


class CreateEntityCommand(PublishBase):
    action: Literal[PublishAction.CREATE_ENTITY]
    payload: CreateEntityPayload


class UpdateEntityCommand(PublishBase):
    action: Literal[PublishAction.UPDATE_ENTITY]
    payload: UpdateEntityPayload


class CreateRelationCommand(PublishBase):
    action: Literal[PublishAction.CREATE_RELATION]
    payload: CreateRelationPayload


class AddSourceCommand(PublishBase):
    action: Literal[PublishAction.ADD_SOURCE]
    payload: AddSourcePayload


class PublishMediaCommand(PublishBase):
    action: Literal[PublishAction.PUBLISH_MEDIA]
    payload: PublishMediaPayload


class ResolveReportCommand(PublishBase):
    action: Literal[PublishAction.RESOLVE_REPORT]
    payload: ResolveReportPayload


PublishCommand = Annotated[
    CreateEntityCommand
    | UpdateEntityCommand
    | CreateRelationCommand
    | AddSourceCommand
    | PublishMediaCommand
    | ResolveReportCommand,
    Field(discriminator="action"),
]


class DecisionCommand(StrictSchema):
    expected_version: int = Field(ge=1)
    comment: str = Field(min_length=1, max_length=5000)


class ClaimCommand(StrictSchema):
    expected_version: int = Field(ge=1)


class QueueItem(StrictSchema):
    id: UUID
    type: SubmissionType
    status: SubmissionStatus
    version: int
    title: str
    settlement_id: UUID | None
    submitted_at: datetime | None
    created_at: datetime
    claimed_by: UUID | None


class QueueQuery(StrictSchema):
    status: SubmissionStatus | None = None
    type: SubmissionType | None = None
    settlement_id: UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=100_000)

    @model_validator(mode="after")
    def ordered_date_range(self) -> Self:
        if (
            self.created_from is not None
            and self.created_to is not None
            and self.created_from > self.created_to
        ):
            raise ValueError("created_from must not exceed created_to")
        return self


class QueuePage(StrictSchema):
    items: list[QueueItem]
    limit: int
    offset: int
    total: int


class ModerationMedia(StrictSchema):
    id: UUID
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
    status: Literal["pending"]


class SubmissionDetails(QueueItem):
    related_entity_id: UUID | None
    description: str
    source_description: str
    author_name: str
    contact: str
    consent: bool
    updated_at: datetime
    media: list[ModerationMedia] = Field(max_length=10)
