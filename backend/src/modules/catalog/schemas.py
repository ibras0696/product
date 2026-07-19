from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from modules.catalog.domain import EntityType, RelationType, ResearchStatus, SourceType


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalizedText(StrictSchema):
    ru: str = Field(min_length=1)
    ce: str | None


class Coordinates(StrictSchema):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class PageMeta(StrictSchema):
    limit: int
    offset: int
    total: int = Field(ge=0)


class Page[T](StrictSchema):
    items: list[T]
    meta: PageMeta


class MapEntity(StrictSchema):
    id: UUID
    type: EntityType
    title: LocalizedText
    coordinates: Coordinates
    relations_count: int = Field(ge=0)
    cover_url: str | None
    district_id: UUID | None
    research_status: ResearchStatus


class MapRelation(StrictSchema):
    id: UUID
    source_id: UUID
    target_id: UUID
    type: RelationType
    source_type: EntityType
    source_title: str
    target_type: EntityType
    target_title: str


class MapEntityCollection(StrictSchema):
    items: list[MapEntity]
    relations: list[MapRelation]
    truncated: bool
    relations_truncated: bool


class MapRequest(StrictSchema):
    bbox: str
    zoom: int = Field(ge=5, le=18)
    types: list[EntityType] = Field(default_factory=list)
    research_statuses: list[ResearchStatus] = Field(default_factory=list)
    district_id: UUID | None = None
    period_from: int | None = None
    period_to: int | None = None
    limit: int = Field(default=200, ge=1, le=1000)


class EntityDetails(StrictSchema):
    id: UUID
    type: EntityType
    slug: str = Field(min_length=1)
    title: LocalizedText
    short_description: LocalizedText
    full_description: LocalizedText
    coordinates: Coordinates | None
    period_from: int | None
    period_to: int | None
    cover_url: str | None
    relations_count: int = Field(ge=0)
    sources_count: int = Field(ge=0)
    media_count: int = Field(ge=0)
    status: Literal["published"]
    research_status: ResearchStatus


class SourceView(StrictSchema):
    id: UUID
    title: str = Field(min_length=1)
    type: SourceType
    author: str | None
    publisher: str | None
    publication_year: int | None
    url: str | None
    archive_reference: str | None
    description: str
    is_verified: Literal[True]


class PublishedMedia(StrictSchema):
    id: UUID
    public_url: str
    preview_url: str
    mime_type: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    caption: str
    author: str
    approximate_date: str | None
    source_description: str


class DistrictOption(StrictSchema):
    id: UUID
    title: LocalizedText


class PeriodOption(StrictSchema):
    id: str = Field(min_length=1)
    title: LocalizedText
    period_from: int | None
    period_to: int | None


class CatalogOptions(StrictSchema):
    districts: list[DistrictOption]
    periods: list[PeriodOption]
    entity_types: list[EntityType]
    research_statuses: list[ResearchStatus]
