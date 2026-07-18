from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from modules.media.models import MediaUploadClaimModel, SubmissionMediaModel
from modules.media.repository import (
    ClaimKind,
    IdempotencyClaim,
    IdempotencyConflictError,
    MediaRecord,
    OrphanMedia,
)


class SubmissionMediaLimitError(Exception):
    pass


class SqlMediaRepository:
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        submission_id: UUID,
        *,
        max_files: int = 10,
    ) -> None:
        self._factory = factory
        self._submission_id = submission_id
        self._max_files = max_files

    async def claim(self, key: UUID, fingerprint: str) -> IdempotencyClaim:
        async with self._factory.begin() as session:
            inserted = await session.scalar(
                insert(MediaUploadClaimModel)
                .values(
                    id=uuid4(),
                    idempotency_key=key,
                    submission_id=self._submission_id,
                    fingerprint=fingerprint,
                    state="processing",
                )
                .on_conflict_do_nothing(index_elements=["idempotency_key"])
                .returning(MediaUploadClaimModel.id)
            )
            if inserted is not None:
                return IdempotencyClaim(ClaimKind.NEW)
            claim = await self._claim(session, key)
            if claim is None or claim.fingerprint != fingerprint:
                raise IdempotencyConflictError("Idempotency key was used for another payload")
            if claim.submission_id != self._submission_id:
                raise IdempotencyConflictError("Idempotency key was used for another submission")
            if claim.media_id is None:
                return IdempotencyClaim(ClaimKind.REPLAY)
            model = await session.get(SubmissionMediaModel, claim.media_id)
            return IdempotencyClaim(ClaimKind.REPLAY, _record(model) if model else None)

    async def complete(self, key: UUID, fingerprint: str, record: MediaRecord) -> None:
        async with self._factory.begin() as session:
            claim = await self._claim(session, key, lock=True)
            if claim is None or claim.fingerprint != fingerprint or claim.media_id is not None:
                raise IdempotencyConflictError("Upload claim is no longer available")
            await session.execute(
                text("SELECT id FROM submissions_submissions WHERE id=:id FOR UPDATE"),
                {"id": self._submission_id},
            )
            count = await session.scalar(
                select(func.count())
                .select_from(SubmissionMediaModel)
                .where(SubmissionMediaModel.submission_id == self._submission_id)
            )
            if int(count or 0) >= self._max_files:
                raise SubmissionMediaLimitError("Submission media limit reached")
            session.add(_model(record))
            claim.media_id = record.id
            claim.state = "completed"
            await session.flush()

    async def abort(self, key: UUID, fingerprint: str) -> None:
        async with self._factory.begin() as session:
            await session.execute(
                delete(MediaUploadClaimModel).where(
                    MediaUploadClaimModel.idempotency_key == key,
                    MediaUploadClaimModel.submission_id == self._submission_id,
                    MediaUploadClaimModel.fingerprint == fingerprint,
                    MediaUploadClaimModel.media_id.is_(None),
                )
            )

    async def list_for_submission(self, submission_id: UUID) -> tuple[MediaRecord, ...]:
        async with self._factory() as session:
            models = (
                await session.scalars(
                    select(SubmissionMediaModel)
                    .where(SubmissionMediaModel.submission_id == submission_id)
                    .order_by(SubmissionMediaModel.created_at, SubmissionMediaModel.id)
                    .limit(self._max_files)
                )
            ).all()
            return tuple(_record(model) for model in models)

    async def update_metadata(
        self, submission_id: UUID, media_id: UUID, changes: dict[str, object]
    ) -> MediaRecord | None:
        async with self._factory.begin() as session:
            model = await session.scalar(
                select(SubmissionMediaModel)
                .where(
                    SubmissionMediaModel.id == media_id,
                    SubmissionMediaModel.submission_id == submission_id,
                )
                .with_for_update()
            )
            if model is None:
                return None
            for field, value in changes.items():
                setattr(model, field, value)
            await session.flush()
            return _record(model)

    async def get_keys(self, submission_id: UUID, media_id: UUID) -> OrphanMedia | None:
        async with self._factory() as session:
            model = await session.scalar(
                select(SubmissionMediaModel).where(
                    SubmissionMediaModel.id == media_id,
                    SubmissionMediaModel.submission_id == submission_id,
                )
            )
            if model is None:
                return None
            return OrphanMedia(model.id, model.original_storage_key, model.preview_storage_key)

    async def delete(self, submission_id: UUID, media_id: UUID) -> None:
        async with self._factory.begin() as session:
            await session.execute(
                delete(SubmissionMediaModel).where(
                    SubmissionMediaModel.id == media_id,
                    SubmissionMediaModel.submission_id == submission_id,
                )
            )

    async def list_expired_orphans(
        self, *, before: datetime, limit: int
    ) -> tuple[OrphanMedia, ...]:
        async with self._factory() as session:
            rows = (
                await session.execute(
                    select(
                        SubmissionMediaModel.id,
                        SubmissionMediaModel.original_storage_key,
                        SubmissionMediaModel.preview_storage_key,
                    )
                    .where(
                        SubmissionMediaModel.expires_at < before,
                        SubmissionMediaModel.status == "pending",
                    )
                    .order_by(SubmissionMediaModel.expires_at, SubmissionMediaModel.id)
                    .limit(limit)
                )
            ).all()
            return tuple(OrphanMedia(row[0], row[1], row[2]) for row in rows)

    async def delete_orphan(self, media_id: UUID) -> None:
        async with self._factory.begin() as session:
            await session.execute(
                delete(SubmissionMediaModel).where(SubmissionMediaModel.id == media_id)
            )

    async def _claim(
        self, session: AsyncSession, key: UUID, *, lock: bool = False
    ) -> MediaUploadClaimModel | None:
        statement = select(MediaUploadClaimModel).where(
            MediaUploadClaimModel.idempotency_key == key
        )
        if lock:
            statement = statement.with_for_update()
        return cast(MediaUploadClaimModel | None, await session.scalar(statement))


def _model(record: MediaRecord) -> SubmissionMediaModel:
    return SubmissionMediaModel(
        id=record.id,
        submission_id=record.submission_id,
        original_name=record.original_name,
        checksum=record.checksum,
        original_storage_key=record.original_key,
        preview_storage_key=record.preview_key,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        width=record.width,
        height=record.height,
        caption=record.caption,
        author=record.author,
        approximate_date=record.approximate_date,
        source_description=record.source_description,
        related_entity_id=record.related_entity_id,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )


def _record(model: SubmissionMediaModel) -> MediaRecord:
    return MediaRecord(
        id=model.id,
        submission_id=model.submission_id,
        original_name=model.original_name,
        checksum=model.checksum,
        original_key=model.original_storage_key,
        preview_key=model.preview_storage_key,
        mime_type=model.mime_type,
        size_bytes=model.size_bytes,
        width=model.width,
        height=model.height,
        caption=model.caption,
        author=model.author,
        approximate_date=model.approximate_date,
        source_description=model.source_description,
        related_entity_id=model.related_entity_id,
    )
