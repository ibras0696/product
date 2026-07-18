from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    column,
    delete,
    func,
    insert,
    select,
    table,
    update,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from modules.moderation.domain import ModerationSubmission
from modules.moderation.models import ModerationClaimModel, ModerationDecisionAuditModel
from modules.submissions.contracts import SubmissionStatus, SubmissionType

SUBMISSIONS = table(
    "submissions_submissions",
    column("id", PostgreSQLUUID(as_uuid=True)),
    column("type", String),
    column("status", String),
    column("version", Integer),
    column("related_entity_id", PostgreSQLUUID(as_uuid=True)),
    column("settlement_id", PostgreSQLUUID(as_uuid=True)),
    column("title", String),
    column("description", String),
    column("source_description", String),
    column("author_name", String),
    column("contact", String),
    column("consent"),
    column("submitted_at", DateTime(timezone=True)),
    column("created_at", DateTime(timezone=True)),
    column("updated_at", DateTime(timezone=True)),
)
HISTORY = table(
    "submissions_status_history",
    column("id", PostgreSQLUUID(as_uuid=True)),
    column("submission_id", PostgreSQLUUID(as_uuid=True)),
    column("sequence", Integer),
    column("from_status", String),
    column("to_status", String),
    column("actor_account_id", PostgreSQLUUID(as_uuid=True)),
    column("public_comment", String),
)


@dataclass(frozen=True, slots=True)
class QueueFilters:
    status: SubmissionStatus | None = None
    type: SubmissionType | None = None
    settlement_id: UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class OptimisticWriteError(RuntimeError):
    pass


class ModerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def queue(
        self, filters: QueueFilters, limit: int, offset: int
    ) -> tuple[list[ModerationSubmission], int]:
        statement = self._queue_select(filters)
        count = select(func.count()).select_from(statement.order_by(None).subquery())
        total = int(await self._session.scalar(count) or 0)
        rows = (await self._session.execute(statement.limit(limit).offset(offset))).mappings()
        return [self._submission(row) for row in rows], total

    async def get(self, submission_id: UUID, *, lock: bool = False) -> ModerationSubmission | None:
        statement = self._base_select().where(SUBMISSIONS.c.id == submission_id)
        if lock:
            statement = statement.with_for_update(of=SUBMISSIONS)
        row = (await self._session.execute(statement)).mappings().one_or_none()
        return None if row is None else self._submission(row)

    async def transition(
        self,
        current: ModerationSubmission,
        target: SubmissionStatus,
        actor_id: UUID,
        comment: str | None,
    ) -> None:
        next_version = current.version + 1
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(SUBMISSIONS)
                .where(
                    SUBMISSIONS.c.id == current.id,
                    SUBMISSIONS.c.version == current.version,
                )
                .values(status=target.value, version=next_version, updated_at=func.now())
            ),
        )
        if result.rowcount != 1:
            raise OptimisticWriteError("optimistic version conflict")
        await self._session.execute(
            insert(HISTORY).values(
                id=func.gen_random_uuid(),
                submission_id=current.id,
                sequence=next_version,
                from_status=current.status.value,
                to_status=target.value,
                actor_account_id=actor_id,
                public_comment=comment,
            )
        )

    async def add_claim(self, submission_id: UUID, actor_id: UUID, version: int) -> None:
        self._session.add(
            ModerationClaimModel(
                submission_id=submission_id, actor_account_id=actor_id, claimed_version=version
            )
        )
        await self._session.flush()

    async def remove_claim(self, submission_id: UUID) -> None:
        await self._session.execute(
            delete(ModerationClaimModel).where(ModerationClaimModel.submission_id == submission_id)
        )

    async def add_decision_audit(
        self, current: ModerationSubmission, actor_id: UUID, action: str, comment: str
    ) -> None:
        self._session.add(
            ModerationDecisionAuditModel(
                submission_id=current.id,
                actor_account_id=actor_id,
                action=action,
                from_version=current.version,
                to_version=current.version + 1,
                public_comment=comment,
            )
        )
        await self._session.flush()

    def _queue_select(self, filters: QueueFilters) -> Any:
        statement = self._base_select()
        for criterion in (
            SUBMISSIONS.c.status == filters.status.value if filters.status else None,
            SUBMISSIONS.c.type == filters.type.value if filters.type else None,
            SUBMISSIONS.c.settlement_id == filters.settlement_id if filters.settlement_id else None,
            SUBMISSIONS.c.created_at >= filters.created_from if filters.created_from else None,
            SUBMISSIONS.c.created_at <= filters.created_to if filters.created_to else None,
        ):
            if criterion is not None:
                statement = statement.where(criterion)
        return statement.order_by(SUBMISSIONS.c.created_at.asc(), SUBMISSIONS.c.id.asc())

    @staticmethod
    def _base_select() -> Any:
        return select(
            *SUBMISSIONS.c,
            ModerationClaimModel.actor_account_id.label("claimed_by"),
        ).outerjoin(ModerationClaimModel, ModerationClaimModel.submission_id == SUBMISSIONS.c.id)

    @staticmethod
    def _submission(row: Any) -> ModerationSubmission:
        values = dict(row)
        values["type"] = SubmissionType(values["type"])
        values["status"] = SubmissionStatus(values["status"])
        return ModerationSubmission(**values)
