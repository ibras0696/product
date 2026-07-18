from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from modules.catalog.domain import EntityType, PublicationStatus, RelationType, SourceType


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalizedText(StrictSchema):
    ru: str = Field(min_length=1, max_length=300)
    ce: str | None = Field(max_length=300)


class Coordinates(StrictSchema):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class AdminEntityCreate(StrictSchema):
    expected_version: int = Field(default=0, ge=0, le=0)
    type: EntityType
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: LocalizedText
    short_description: LocalizedText
    full_description: LocalizedText
    coordinates: Coordinates | None
    period_from: int | None
    period_to: int | None
    district_id: UUID | None
    status: PublicationStatus = PublicationStatus.DRAFT

    @model_validator(mode="after")
    def period_is_ordered(self) -> Self:
        _validate_period(self.period_from, self.period_to)
        return self


class AdminEntityPatch(StrictSchema):
    expected_version: int = Field(ge=1)
    slug: str | None = Field(
        default=None, min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    title: LocalizedText | None = None
    short_description: LocalizedText | None = None
    full_description: LocalizedText | None = None
    coordinates: Coordinates | None = None
    period_from: int | None = None
    period_to: int | None = None
    district_id: UUID | None = None
    status: PublicationStatus | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> Self:
        required = {"slug", "title", "short_description", "full_description", "status"}
        if any(getattr(self, field) is None for field in required & self.model_fields_set):
            raise ValueError("field cannot be null")
        return self

    def changes(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.model_fields_set
            if field != "expected_version"
        }


class ArchiveRequest(StrictSchema):
    expected_version: int = Field(ge=1)


class AdminEntity(StrictSchema):
    id: UUID
    type: EntityType
    slug: str
    title: LocalizedText
    short_description: LocalizedText
    full_description: LocalizedText
    coordinates: Coordinates | None
    period_from: int | None
    period_to: int | None
    district_id: UUID | None
    status: PublicationStatus
    version: int
    relations_count: int = Field(ge=0)
    sources_count: int = Field(ge=0)
    media_count: int = Field(ge=0)


class PageMeta(StrictSchema):
    limit: int
    offset: int
    total: int = Field(ge=0)


class AdminEntityPage(StrictSchema):
    items: list[AdminEntity]
    meta: PageMeta


class AdminEntityListRequest(StrictSchema):
    query: str | None = Field(default=None, max_length=100)
    type: EntityType | None = None
    status: PublicationStatus | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1000)


class AdminRelationCreate(StrictSchema):
    expected_version: int = Field(default=0, ge=0, le=0)
    source_entity_id: UUID
    target_entity_id: UUID
    type: RelationType
    title: LocalizedText
    description: LocalizedText
    period_from: int | None
    period_to: int | None
    status: PublicationStatus = PublicationStatus.DRAFT

    @model_validator(mode="after")
    def valid_relation(self) -> Self:
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("self relation is forbidden")
        _validate_period(self.period_from, self.period_to)
        return self


class AdminRelationPatch(StrictSchema):
    expected_version: int = Field(ge=1)
    type: RelationType | None = None
    title: LocalizedText | None = None
    description: LocalizedText | None = None
    period_from: int | None = None
    period_to: int | None = None
    status: PublicationStatus | None = None

    @model_validator(mode="after")
    def reject_required_null(self) -> Self:
        required = {"type", "title", "description", "status"}
        if any(getattr(self, field) is None for field in required & self.model_fields_set):
            raise ValueError("field cannot be null")
        return self

    def changes(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.model_fields_set
            if field != "expected_version"
        }


class AdminRelation(StrictSchema):
    id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    type: RelationType
    title: LocalizedText
    description: LocalizedText
    period_from: int | None
    period_to: int | None
    status: PublicationStatus
    version: int


class AdminRelationPage(StrictSchema):
    items: list[AdminRelation]
    meta: PageMeta


class AdminRelationListRequest(StrictSchema):
    entity_id: UUID | None = None
    type: RelationType | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1000)


class AdminSourceCreate(StrictSchema):
    expected_version: int = Field(default=0, ge=0, le=0)
    title: str = Field(min_length=1, max_length=500)
    type: SourceType
    author: str | None = Field(max_length=300)
    publisher: str | None = Field(max_length=300)
    publication_year: int | None
    url: str | None = Field(max_length=2048)
    archive_reference: str | None = Field(max_length=500)
    description: str = Field(max_length=10_000)
    is_verified: bool = False
    status: PublicationStatus = PublicationStatus.DRAFT


class AdminSourcePatch(StrictSchema):
    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    type: SourceType | None = None
    author: str | None = Field(default=None, max_length=300)
    publisher: str | None = Field(default=None, max_length=300)
    publication_year: int | None = None
    url: str | None = Field(default=None, max_length=2048)
    archive_reference: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=10_000)
    is_verified: bool | None = None
    status: PublicationStatus | None = None

    @model_validator(mode="after")
    def reject_required_null(self) -> Self:
        required = {"title", "type", "description", "is_verified", "status"}
        if any(getattr(self, field) is None for field in required & self.model_fields_set):
            raise ValueError("field cannot be null")
        return self

    def changes(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.model_fields_set
            if field != "expected_version"
        }


class AdminSource(StrictSchema):
    id: UUID
    title: str
    type: SourceType
    author: str | None
    publisher: str | None
    publication_year: int | None
    url: str | None
    archive_reference: str | None
    description: str
    is_verified: bool
    status: PublicationStatus
    version: int


class AdminSourcePage(StrictSchema):
    items: list[AdminSource]
    meta: PageMeta


class AdminSourceListRequest(StrictSchema):
    query: str | None = Field(default=None, max_length=100)
    type: SourceType | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1000)


def _validate_period(period_from: int | None, period_to: int | None) -> None:
    if period_from is not None and period_to is not None and period_from > period_to:
        raise ValueError("period_from must not exceed period_to")
