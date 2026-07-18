from uuid import uuid4

import pytest

from modules.submissions.domain import (
    InvalidTransitionError,
    Submission,
    SubmissionStatus,
    SubmissionStatusChange,
    SubmissionType,
    VersionConflictError,
)


def new_submission() -> Submission:
    return Submission(id=uuid4(), type=SubmissionType.NEW_ENTITY)


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (SubmissionStatus.DRAFT, SubmissionStatus.PENDING),
        (SubmissionStatus.PENDING, SubmissionStatus.IN_REVIEW),
        (SubmissionStatus.IN_REVIEW, SubmissionStatus.NEEDS_REVISION),
        (SubmissionStatus.IN_REVIEW, SubmissionStatus.REJECTED),
        (SubmissionStatus.IN_REVIEW, SubmissionStatus.PUBLISHED),
        (SubmissionStatus.NEEDS_REVISION, SubmissionStatus.PENDING),
    ],
)
def test_every_allowed_transition_increments_version_and_records_history(
    start: SubmissionStatus,
    target: SubmissionStatus,
) -> None:
    submission = Submission(
        id=uuid4(),
        type=SubmissionType.NEW_ENTITY,
        status=start,
        version=3,
    )

    transitioned = submission.transition(target, expected_version=3)

    assert transitioned.status is target
    assert transitioned.version == 4
    assert transitioned.history == (
        SubmissionStatusChange(
            sequence=4,
            from_status=start,
            to_status=target,
        ),
    )
    assert submission.status is start
    assert submission.version == 3


@pytest.mark.parametrize("start", list(SubmissionStatus))
def test_every_forbidden_transition_is_rejected(start: SubmissionStatus) -> None:
    allowed = {
        SubmissionStatus.DRAFT: {SubmissionStatus.PENDING},
        SubmissionStatus.PENDING: {SubmissionStatus.IN_REVIEW},
        SubmissionStatus.IN_REVIEW: {
            SubmissionStatus.NEEDS_REVISION,
            SubmissionStatus.REJECTED,
            SubmissionStatus.PUBLISHED,
        },
        SubmissionStatus.NEEDS_REVISION: {SubmissionStatus.PENDING},
        SubmissionStatus.REJECTED: set(),
        SubmissionStatus.PUBLISHED: set(),
    }[start]
    submission = Submission(
        id=uuid4(),
        type=SubmissionType.REPORT_ERROR,
        status=start,
    )

    for target in set(SubmissionStatus) - allowed:
        with pytest.raises(InvalidTransitionError):
            submission.transition(target, expected_version=1)


def test_stale_version_is_rejected_before_transition() -> None:
    submission = new_submission()

    with pytest.raises(VersionConflictError):
        submission.transition(SubmissionStatus.PENDING, expected_version=2)


def test_revision_cycle_keeps_continuous_ordered_history() -> None:
    submission = new_submission()
    submission = submission.transition(SubmissionStatus.PENDING, expected_version=1)
    submission = submission.transition(SubmissionStatus.IN_REVIEW, expected_version=2)
    submission = submission.transition(SubmissionStatus.NEEDS_REVISION, expected_version=3)
    submission = submission.transition(SubmissionStatus.PENDING, expected_version=4)

    assert submission.version == 5
    assert [change.sequence for change in submission.history] == [2, 3, 4, 5]
    assert [change.to_status for change in submission.history] == [
        SubmissionStatus.PENDING,
        SubmissionStatus.IN_REVIEW,
        SubmissionStatus.NEEDS_REVISION,
        SubmissionStatus.PENDING,
    ]


@pytest.mark.parametrize(
    "history",
    [
        (
            SubmissionStatusChange(
                sequence=4,
                from_status=SubmissionStatus.DRAFT,
                to_status=SubmissionStatus.PENDING,
            ),
        ),
        (
            SubmissionStatusChange(
                sequence=2,
                from_status=SubmissionStatus.DRAFT,
                to_status=SubmissionStatus.PENDING,
            ),
            SubmissionStatusChange(
                sequence=3,
                from_status=SubmissionStatus.DRAFT,
                to_status=SubmissionStatus.IN_REVIEW,
            ),
        ),
    ],
)
def test_invalid_history_order_or_continuity_is_rejected(
    history: tuple[SubmissionStatusChange, ...],
) -> None:
    with pytest.raises(ValueError):
        Submission(
            id=uuid4(),
            type=SubmissionType.NEW_SOURCE,
            status=history[-1].to_status,
            version=3,
            history=history,
        )


def test_all_submission_types_match_approved_contract() -> None:
    assert {value.value for value in SubmissionType} == {
        "new_entity",
        "update_entity",
        "new_relation",
        "new_source",
        "new_media",
        "report_error",
    }
