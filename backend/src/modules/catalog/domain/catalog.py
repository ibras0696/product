from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import UUID

from modules.catalog.domain.exceptions import SelfRelationForbiddenError
from modules.catalog.domain.publication import ensure_publishable
from modules.catalog.domain.sources import Source


class PublicationStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ResearchStatus(StrEnum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"


class EntityType(StrEnum):
    SETTLEMENT = "settlement"
    PERSON = "person"
    EVENT = "event"
    LANDMARK = "landmark"
    NATURAL_OBJECT = "natural_object"
    CULTURAL_OBJECT = "cultural_object"
    ORGANIZATION = "organization"
    UNIVERSITY_OBJECT = "university_object"
    ARTIFACT = "artifact"


class RelationType(StrEnum):
    BORN_IN = "born_in"
    LIVED_IN = "lived_in"
    WORKED_IN = "worked_in"
    STUDIED_IN = "studied_in"
    TAUGHT_AT = "taught_at"
    PARTICIPATED_IN = "participated_in"
    LOCATED_IN = "located_in"
    PART_OF = "part_of"
    CREATED_BY = "created_by"
    DESCRIBED_IN = "described_in"
    CONNECTED_WITH = "connected_with"
    CONNECTED_WITH_CHGU = "connected_with_chgu"


@dataclass(frozen=True, slots=True)
class CatalogEntity:
    id: UUID
    sources: tuple[Source, ...] = ()
    status: PublicationStatus = PublicationStatus.DRAFT

    def publish(self) -> "CatalogEntity":
        ensure_publishable(self.sources)
        return replace(self, status=PublicationStatus.PUBLISHED)


@dataclass(frozen=True, slots=True)
class CatalogRelation:
    id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    sources: tuple[Source, ...] = ()
    status: PublicationStatus = PublicationStatus.DRAFT

    def __post_init__(self) -> None:
        if self.source_entity_id == self.target_entity_id:
            raise SelfRelationForbiddenError

    def publish(self) -> "CatalogRelation":
        ensure_publishable(self.sources)
        return replace(self, status=PublicationStatus.PUBLISHED)
