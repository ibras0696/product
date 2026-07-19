from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

import pytest

from modules.moderation.domain import (
    ModerationDetails,
    ModerationMedia,
    ModerationSubmission,
    PublishAction,
)
from modules.moderation.exceptions import (
    InvalidModerationTransitionError,
    ModerationConflictError,
)
from modules.moderation.repository import MediaPreviewRecord, QueueFilters
from modules.moderation.service import ModerationService
from modules.submissions.contracts import SubmissionStatus, SubmissionType


def submission(
    *,
    status: SubmissionStatus = SubmissionStatus.PENDING,
    version: int = 2,
    claimed_by: UUID | None = None,
    type: SubmissionType = SubmissionType.NEW_ENTITY,
) -> ModerationSubmission:
    now = datetime(2026, 7, 18, tzinfo=UTC)
    return ModerationSubmission(
        id=uuid4(),
        type=type,
        status=status,
        version=version,
        title="Title",
        description="Description",
        source_description="Source",
        author_name="Author",
        contact="contact",
        consent=True,
        related_entity_id=None,
        settlement_id=None,
        submitted_at=now,
        created_at=now,
        updated_at=now,
        claimed_by=claimed_by,
    )


def media() -> ModerationMedia:
    return ModerationMedia(
        id=uuid4(),
        original_name="archive.jpg",
        mime_type="image/jpeg",
        size_bytes=1024,
        width=800,
        height=600,
        caption="Archive photo",
        author="Family archive",
        approximate_date="1950",
        source_description="Original print",
        related_entity_id=None,
        status="pending",
    )


class FakeRepository:
    def __init__(
        self,
        records: list[ModerationSubmission],
        media_by_submission: dict[UUID, tuple[ModerationMedia, ...]] | None = None,
    ) -> None:
        self.records = records
        self.media_by_submission = media_by_submission or {}
        self.transitions: list[tuple[SubmissionStatus, UUID, str | None]] = []
        self.claims: dict[UUID, UUID] = {}
        self.audits: list[tuple[str, str]] = []

    async def queue(
        self, filters: QueueFilters, limit: int, offset: int
    ) -> tuple[list[ModerationSubmission], int]:
        selected = [item for item in self.records if filters.status in {None, item.status}]
        selected.sort(key=lambda item: (item.created_at, item.id))
        return selected[offset : offset + limit], len(selected)

    async def get_details(
        self, submission_id: UUID, *, lock: bool = False
    ) -> ModerationDetails | None:
        del lock
        item = next((item for item in self.records if item.id == submission_id), None)
        if item is None:
            return None
        return ModerationDetails(item, self.media_by_submission.get(submission_id, ()))

    async def get_media_preview(
        self, submission_id: UUID, media_id: UUID
    ) -> MediaPreviewRecord | None:
        del submission_id, media_id
        return None

    async def transition(
        self,
        current: ModerationSubmission,
        target: SubmissionStatus,
        actor_id: UUID,
        comment: str | None,
    ) -> None:
        self.transitions.append((target, actor_id, comment))

    async def add_claim(self, submission_id: UUID, actor_id: UUID, version: int) -> None:
        del version
        if submission_id in self.claims:
            raise AssertionError("duplicate claim")
        self.claims[submission_id] = actor_id

    async def remove_claim(self, submission_id: UUID) -> None:
        self.claims.pop(submission_id, None)

    async def add_decision_audit(
        self, current: ModerationSubmission, actor_id: UUID, action: str, comment: str
    ) -> None:
        del current, actor_id
        self.audits.append((action, comment))


class FakeUoW:
    def __init__(self, repository: FakeRepository) -> None:
        self._repository = repository

    @property
    def repository(self) -> FakeRepository:
        return self._repository

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback


def service(repository: FakeRepository) -> ModerationService:
    return ModerationService(lambda: FakeUoW(repository))


async def test_queue_is_bounded_filtered_and_deterministic() -> None:
    pending = [submission() for _ in range(4)]
    rejected = submission(status=SubmissionStatus.REJECTED)
    repository = FakeRepository([rejected, *reversed(pending)])

    page, total = await service(repository).queue(
        QueueFilters(status=SubmissionStatus.PENDING), limit=2, offset=1
    )

    expected = sorted(pending, key=lambda item: (item.created_at, item.id))[1:3]
    assert page == expected
    assert total == 4


async def test_claim_changes_pending_once_and_reject_requires_owner() -> None:
    moderator = uuid4()
    current = submission()
    repository = FakeRepository([current])
    attached = media()
    repository.media_by_submission[current.id] = (attached,)
    claimed = await service(repository).claim(current.id, moderator, expected_version=2)

    assert (
        claimed.submission.status,
        claimed.submission.version,
        claimed.submission.claimed_by,
    ) == (
        SubmissionStatus.IN_REVIEW,
        3,
        moderator,
    )
    assert claimed.media == (attached,)
    assert repository.transitions == [(SubmissionStatus.IN_REVIEW, moderator, None)]

    other_claim = submission(status=SubmissionStatus.IN_REVIEW, version=3, claimed_by=uuid4())
    with pytest.raises(ModerationConflictError, match="another moderator"):
        await service(FakeRepository([other_claim])).reject(other_claim.id, moderator, 3, "Checked")


async def test_stale_and_final_decisions_never_overwrite() -> None:
    moderator = uuid4()
    in_review = submission(status=SubmissionStatus.IN_REVIEW, version=3, claimed_by=moderator)
    moderation = service(FakeRepository([in_review]))

    with pytest.raises(ModerationConflictError, match="version"):
        await moderation.reject(in_review.id, moderator, 2, "Checked")

    final = submission(status=SubmissionStatus.REJECTED, version=4, claimed_by=None)
    with pytest.raises(InvalidModerationTransitionError, match="transition"):
        await service(FakeRepository([final])).request_revision(
            final.id, moderator, 4, "Please revise"
        )


async def test_revision_records_trimmed_comment_and_releases_claim() -> None:
    moderator = uuid4()
    current = submission(status=SubmissionStatus.IN_REVIEW, version=3, claimed_by=moderator)
    repository = FakeRepository([current])
    repository.claims[current.id] = moderator

    revised = await service(repository).request_revision(
        current.id, moderator, 3, "  Add source details  "
    )

    assert revised.submission.status is SubmissionStatus.NEEDS_REVISION
    assert repository.audits == [("needs_revision", "Add source details")]
    assert current.id not in repository.claims
    with pytest.raises(InvalidModerationTransitionError, match="required"):
        await service(repository).reject(current.id, moderator, 3, "   ")


@pytest.mark.parametrize(
    ("submission_type", "action"),
    list(
        zip(
            SubmissionType,
            (
                PublishAction.CREATE_ENTITY,
                PublishAction.UPDATE_ENTITY,
                PublishAction.CREATE_RELATION,
                PublishAction.ADD_SOURCE,
                PublishAction.PUBLISH_MEDIA,
                PublishAction.RESOLVE_REPORT,
            ),
            strict=True,
        )
    ),
)
def test_all_six_submission_types_accept_only_their_action(
    submission_type: SubmissionType, action: PublishAction
) -> None:
    ModerationService.validate_publish_action(submission_type, action)
    wrong = (
        PublishAction.UPDATE_ENTITY
        if action is not PublishAction.UPDATE_ENTITY
        else PublishAction.ADD_SOURCE
    )
    with pytest.raises(InvalidModerationTransitionError) as error:
        ModerationService.validate_publish_action(submission_type, wrong)
    assert error.value.code == "invalid_transition"
