from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.submissions.domain import SubmissionStatus
from modules.submissions.models import SubmissionModel, SubmissionStatusHistoryModel


class SubmissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, submission: SubmissionModel) -> None:
        self._session.add(submission)
        await self._session.flush()

    async def owned(
        self, submission_id: UUID, owner_hash: str, now: datetime
    ) -> SubmissionModel | None:
        return cast(
            SubmissionModel | None,
            await self._session.scalar(
                select(SubmissionModel)
                .where(
                    SubmissionModel.id == submission_id,
                    SubmissionModel.owner_capability_hash == owner_hash,
                    SubmissionModel.owner_capability_expires_at > now,
                )
                .with_for_update()
            ),
        )

    async def tracked(self, tracking_hash: str) -> SubmissionModel | None:
        return cast(
            SubmissionModel | None,
            await self._session.scalar(
                select(SubmissionModel).where(SubmissionModel.tracking_code_hash == tracking_hash)
            ),
        )

    async def latest_public_comment(self, submission_id: UUID) -> str | None:
        return await self._session.scalar(
            select(SubmissionStatusHistoryModel.public_comment)
            .where(
                SubmissionStatusHistoryModel.submission_id == submission_id,
                SubmissionStatusHistoryModel.public_comment.is_not(None),
            )
            .order_by(SubmissionStatusHistoryModel.sequence.desc())
            .limit(1)
        )

    async def patch(
        self, submission: SubmissionModel, changes: dict[str, object], expected_version: int
    ) -> None:
        for field, value in changes.items():
            setattr(submission, field, value)
        submission.version = expected_version + 1
        submission.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def apply_transition(
        self,
        submission: SubmissionModel,
        status: SubmissionStatus,
        version: int,
        submitted_at: datetime | None,
        history: SubmissionStatusHistoryModel,
    ) -> None:
        submission.status = status
        submission.version = version
        submission.submitted_at = submitted_at
        submission.updated_at = datetime.now(UTC)
        self._session.add(history)
        await self._session.flush()
