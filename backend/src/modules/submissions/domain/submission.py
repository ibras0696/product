from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import UUID

from modules.submissions.domain.exceptions import (
    InvalidTransitionError,
    VersionConflictError,
)


class SubmissionType(StrEnum):
    NEW_ENTITY = "new_entity"
    UPDATE_ENTITY = "update_entity"
    NEW_RELATION = "new_relation"
    NEW_SOURCE = "new_source"
    NEW_MEDIA = "new_media"
    REPORT_ERROR = "report_error"


class SubmissionStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    IN_REVIEW = "in_review"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"
    PUBLISHED = "published"


ALLOWED_TRANSITIONS: dict[SubmissionStatus, frozenset[SubmissionStatus]] = {
    SubmissionStatus.DRAFT: frozenset({SubmissionStatus.PENDING}),
    SubmissionStatus.PENDING: frozenset({SubmissionStatus.IN_REVIEW}),
    SubmissionStatus.IN_REVIEW: frozenset(
        {
            SubmissionStatus.NEEDS_REVISION,
            SubmissionStatus.REJECTED,
            SubmissionStatus.PUBLISHED,
        }
    ),
    SubmissionStatus.NEEDS_REVISION: frozenset({SubmissionStatus.PENDING}),
    SubmissionStatus.REJECTED: frozenset(),
    SubmissionStatus.PUBLISHED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class SubmissionStatusChange:
    sequence: int
    from_status: SubmissionStatus
    to_status: SubmissionStatus
    actor_account_id: UUID | None = None
    public_comment: str | None = None


@dataclass(frozen=True, slots=True)
class Submission:
    id: UUID
    type: SubmissionType
    status: SubmissionStatus = SubmissionStatus.DRAFT
    version: int = 1
    history: tuple[SubmissionStatusChange, ...] = ()

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("submission version must be positive")
        self._validate_history()

    def transition(
        self,
        target: SubmissionStatus,
        *,
        expected_version: int,
        actor_account_id: UUID | None = None,
        public_comment: str | None = None,
    ) -> "Submission":
        if expected_version != self.version:
            raise VersionConflictError
        if target not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidTransitionError

        next_version = self.version + 1
        change = SubmissionStatusChange(
            sequence=next_version,
            from_status=self.status,
            to_status=target,
            actor_account_id=actor_account_id,
            public_comment=public_comment,
        )
        return replace(
            self,
            status=target,
            version=next_version,
            history=(*self.history, change),
        )

    def _validate_history(self) -> None:
        if not self.history:
            return
        expected_sequences = tuple(range(self.version - len(self.history) + 1, self.version + 1))
        actual_sequences = tuple(change.sequence for change in self.history)
        if actual_sequences != expected_sequences:
            raise ValueError("submission history must be ordered and end at current version")
        for previous, current in zip(self.history, self.history[1:], strict=False):
            if previous.to_status is not current.from_status:
                raise ValueError("submission history must form a continuous status chain")
        if self.history[-1].to_status is not self.status:
            raise ValueError("submission history must end at current status")
