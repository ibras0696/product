from uuid import UUID

from pydantic import Field, field_validator

from modules.catalog.domain import EntityType, RelationType
from modules.catalog.schemas import Coordinates, LocalizedText, Page, StrictSchema


class GraphCenterView(StrictSchema):
    id: UUID
    type: EntityType
    title: LocalizedText


class GraphNodeView(GraphCenterView):
    relations_count: int = Field(ge=0)


class GraphEdgeView(StrictSchema):
    id: UUID
    source_id: UUID
    target_id: UUID
    type: RelationType
    title: LocalizedText
    description: LocalizedText
    sources_count: int = Field(ge=0)


class GraphView(StrictSchema):
    center: GraphCenterView
    nodes: list[GraphNodeView]
    edges: list[GraphEdgeView]
    hidden_nodes_count: int = Field(ge=0)


class GraphRequest(StrictSchema):
    depth: int = Field(default=1, ge=1, le=2)
    types: list[EntityType] = Field(default_factory=list)
    period_from: int | None = None
    period_to: int | None = None
    limit: int = Field(default=20, ge=1, le=40)


class SearchItemView(StrictSchema):
    id: UUID
    type: EntityType
    title: LocalizedText
    subtitle: LocalizedText
    cover_url: str | None
    coordinates: Coordinates | None
    relations_count: int = Field(ge=0)


SearchPage = Page[SearchItemView]


class SearchRequest(StrictSchema):
    q: str = Field(min_length=2, max_length=100)
    types: list[EntityType] = Field(default_factory=list)
    district_id: UUID | None = None
    period_from: int | None = None
    period_to: int | None = None
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=1000)

    @field_validator("q", mode="before")
    @classmethod
    def strip_query(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value
