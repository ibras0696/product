from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from modules.submissions.contracts import SubmissionStatus, SubmissionType


class PublishAction(StrEnum):
    CREATE_ENTITY = "create_entity"
    UPDATE_ENTITY = "update_entity"
    CREATE_RELATION = "create_relation"
    ADD_SOURCE = "add_source"
    PUBLISH_MEDIA = "publish_media"
    RESOLVE_REPORT = "resolve_report"


ACTION_BY_SUBMISSION_TYPE = {
    SubmissionType.NEW_ENTITY: PublishAction.CREATE_ENTITY,
    SubmissionType.UPDATE_ENTITY: PublishAction.UPDATE_ENTITY,
    SubmissionType.NEW_RELATION: PublishAction.CREATE_RELATION,
    SubmissionType.NEW_SOURCE: PublishAction.ADD_SOURCE,
    SubmissionType.NEW_MEDIA: PublishAction.PUBLISH_MEDIA,
    SubmissionType.REPORT_ERROR: PublishAction.RESOLVE_REPORT,
}


@dataclass(frozen=True, slots=True)
class ModerationSubmission:
    id: UUID
    type: SubmissionType
    status: SubmissionStatus
    version: int
    title: str
    description: str
    source_description: str
    author_name: str
    contact: str
    consent: bool
    related_entity_id: UUID | None
    settlement_id: UUID | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    claimed_by: UUID | None = None


def validate_action(submission_type: SubmissionType, action: PublishAction) -> None:
    if ACTION_BY_SUBMISSION_TYPE[submission_type] is not action:
        raise ValueError("publish action does not match submission type")
