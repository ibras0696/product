from dataclasses import dataclass
from uuid import UUID

from modules.moderation.contracts import PublishAction
from modules.submissions.contracts import SubmissionStatus, SubmissionType


@dataclass(frozen=True, slots=True)
class PublicationSubmission:
    id: UUID
    type: SubmissionType
    status: SubmissionStatus
    version: int
    claimed_by: UUID | None
    related_entity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CatalogPublicationResult:
    entity_ids: tuple[UUID, ...] = ()
    relation_ids: tuple[UUID, ...] = ()
    source_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class StoredPublication:
    submission_id: UUID
    actor_id: UUID
    request_hash: str
    result: dict[str, object]


@dataclass(frozen=True, slots=True)
class PublicationAuditInput:
    submission_id: UUID
    actor_id: UUID
    action: PublishAction
    from_version: int
    request_hash: str
    comment: str
    catalog: CatalogPublicationResult
    media_ids: tuple[UUID, ...]
