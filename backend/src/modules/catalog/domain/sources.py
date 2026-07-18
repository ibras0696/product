from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class SourceType(StrEnum):
    ARCHIVE_DOCUMENT = "archive_document"
    BOOK = "book"
    SCIENTIFIC_ARTICLE = "scientific_article"
    MUSEUM_MATERIAL = "museum_material"
    OFFICIAL_PUBLICATION = "official_publication"
    PHOTO = "photo"
    AUDIO = "audio"
    VIDEO = "video"
    ORAL_TESTIMONY = "oral_testimony"
    WEB_RESOURCE = "web_resource"


class EvidenceClassification(StrEnum):
    DOCUMENTARY = "documentary"
    ORAL_TESTIMONY = "oral_testimony"


@dataclass(frozen=True, slots=True)
class Source:
    id: UUID
    type: SourceType
    is_verified: bool

    @property
    def evidence_classification(self) -> EvidenceClassification:
        if self.type is SourceType.ORAL_TESTIMONY:
            return EvidenceClassification.ORAL_TESTIMONY
        return EvidenceClassification.DOCUMENTARY
