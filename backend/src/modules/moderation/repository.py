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

from modules.moderation.domain import ModerationDetails, ModerationMedia, ModerationSubmission
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
SUBMISSION_MEDIA = table(
    "media_submission_assets",
    column("id", PostgreSQLUUID(as_uuid=True)),
    column("submission_id", PostgreSQLUUID(as_uuid=True)),
    column("original_name", String),
    column("preview_storage_key", String),
    column("mime_type", String),
    column("size_bytes", Integer),
    column("width", Integer),
    column("height", Integer),
    column("caption", String),
    column("author", String),
    column("approximate_date", String),
    column("source_description", String),
    column("related_entity_id", PostgreSQLUUID(as_uuid=True)),
    column("status", String),
    column("created_at", DateTime(timezone=True)),
)
MAX_MEDIA_PER_SUBMISSION = 10


@dataclass(frozen=True, slots=True)
class QueueFilters:
    status: SubmissionStatus | None = None
    type: SubmissionType | None = None
    settlement_id: UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class OptimisticWriteError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaPreviewRecord:
    preview_key: str


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

    async def get_details(
        self, submission_id: UUID, *, lock: bool = False
    ) -> ModerationDetails | None:
        statement = (
            self._details_select()
            .where(SUBMISSIONS.c.id == submission_id)
            .order_by(SUBMISSION_MEDIA.c.created_at.asc(), SUBMISSION_MEDIA.c.id.asc())
            .limit(MAX_MEDIA_PER_SUBMISSION)
        )
        if lock:
            statement = statement.with_for_update(of=SUBMISSIONS)
        rows = (await self._session.execute(statement)).mappings().all()
        if not rows:
            return None
        mapped_media = (self._media(row) for row in rows)
        media = tuple(item for item in mapped_media if item is not None)
        return ModerationDetails(self._submission(rows[0]), media)

    async def get_media_preview(
        self, submission_id: UUID, media_id: UUID
    ) -> MediaPreviewRecord | None:
        key = await self._session.scalar(
            select(SUBMISSION_MEDIA.c.preview_storage_key).where(
                SUBMISSION_MEDIA.c.submission_id == submission_id,
                SUBMISSION_MEDIA.c.id == media_id,
                SUBMISSION_MEDIA.c.status == "pending",
            )
        )
        return None if key is None else MediaPreviewRecord(str(key))

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
    def _details_select() -> Any:
        return (
            ModerationRepository._base_select()
            .add_columns(
                SUBMISSION_MEDIA.c.id.label("media_id"),
                SUBMISSION_MEDIA.c.original_name.label("media_original_name"),
                SUBMISSION_MEDIA.c.mime_type.label("media_mime_type"),
                SUBMISSION_MEDIA.c.size_bytes.label("media_size_bytes"),
                SUBMISSION_MEDIA.c.width.label("media_width"),
                SUBMISSION_MEDIA.c.height.label("media_height"),
                SUBMISSION_MEDIA.c.caption.label("media_caption"),
                SUBMISSION_MEDIA.c.author.label("media_author"),
                SUBMISSION_MEDIA.c.approximate_date.label("media_approximate_date"),
                SUBMISSION_MEDIA.c.source_description.label("media_source_description"),
                SUBMISSION_MEDIA.c.related_entity_id.label("media_related_entity_id"),
                SUBMISSION_MEDIA.c.status.label("media_status"),
            )
            .outerjoin(
                SUBMISSION_MEDIA,
                SUBMISSION_MEDIA.c.submission_id == SUBMISSIONS.c.id,
            )
        )

    @staticmethod
    def _submission(row: Any) -> ModerationSubmission:
        values = {column.name: row[column.name] for column in SUBMISSIONS.c}
        values["claimed_by"] = row["claimed_by"]
        values["type"] = SubmissionType(values["type"])
        values["status"] = SubmissionStatus(values["status"])
        return ModerationSubmission(**values)

    @staticmethod
    def _media(row: Any) -> ModerationMedia | None:
        if row["media_id"] is None:
            return None
        return ModerationMedia(
            id=row["media_id"],
            original_name=row["media_original_name"],
            mime_type=row["media_mime_type"],
            size_bytes=row["media_size_bytes"],
            width=row["media_width"],
            height=row["media_height"],
            caption=row["media_caption"],
            author=row["media_author"],
            approximate_date=row["media_approximate_date"],
            source_description=row["media_source_description"],
            related_entity_id=row["media_related_entity_id"],
            status=row["media_status"],
        )
