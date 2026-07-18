import asyncio
import io
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from PIL import Image
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from modules.media.models import MediaUploadClaimModel, SubmissionMediaModel
from modules.media.repository import IdempotencyConflictError, MediaRecord
from modules.media.service import MediaUploadService, UploadMetadata
from modules.media.sql_repository import SqlMediaRepository
from modules.media.storage import LocalMediaStorage
from modules.media.validation import ImageValidator
from modules.submissions.contracts import SubmissionStatus, SubmissionType

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL is required for PostgreSQL media scenarios"
)


@dataclass(frozen=True, slots=True)
class MediaDatabase:
    factory: async_sessionmaker[AsyncSession]
    submission_id: UUID


@pytest_asyncio.fixture
async def media_database() -> AsyncIterator[MediaDatabase]:
    assert DATABASE_URL is not None
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    submission_id = uuid4()
    async with factory.begin() as session:
        await session.execute(
            text(
                """INSERT INTO submissions_submissions
                (id,type,status,version,title,description,source_description,author_name,
                 contact,consent,owner_capability_hash,owner_capability_expires_at,
                 tracking_code_hash)
                VALUES (:id,:type,:status,1,'Media integration','Description','Source',
                        'Author','contact@example.test',true,:owner_hash,:expires_at,:tracking_hash)"""
            ),
            {
                "id": submission_id,
                "type": SubmissionType.NEW_MEDIA.value,
                "status": SubmissionStatus.DRAFT.value,
                "owner_hash": uuid4().hex,
                "expires_at": datetime(2099, 1, 1, tzinfo=UTC),
                "tracking_hash": uuid4().hex,
            },
        )
    try:
        yield MediaDatabase(factory, submission_id)
    finally:
        async with factory.begin() as session:
            await session.execute(
                delete(MediaUploadClaimModel).where(
                    MediaUploadClaimModel.submission_id == submission_id
                )
            )
            await session.execute(
                delete(SubmissionMediaModel).where(
                    SubmissionMediaModel.submission_id == submission_id
                )
            )
            await session.execute(
                text("DELETE FROM submissions_submissions WHERE id=:id"),
                {"id": submission_id},
            )
        await engine.dispose()


async def _chunks(payload: bytes) -> AsyncIterator[bytes]:
    yield payload[: len(payload) // 2]
    yield payload[len(payload) // 2 :]


def _image() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 24), (20, 80, 120)).save(output, format="PNG")
    return output.getvalue()


def _metadata(submission_id: UUID, caption: str = "caption") -> UploadMetadata:
    return UploadMetadata(
        submission_id,
        "family-photo.jpg",
        caption,
        "author",
        None,
        "archive",
        None,
    )


async def test_postgres_lost_response_and_concurrent_retry_create_one_media(
    media_database: MediaDatabase, tmp_path: Path
) -> None:
    repository = SqlMediaRepository(media_database.factory, media_database.submission_id)
    service = MediaUploadService(repository, LocalMediaStorage(tmp_path), ImageValidator())
    key = uuid4()
    metadata = _metadata(media_database.submission_id)

    first = await service.upload(idempotency_key=key, chunks=_chunks(_image()), metadata=metadata)
    replay = await service.upload(idempotency_key=key, chunks=_chunks(_image()), metadata=metadata)
    concurrent_key = uuid4()
    outcomes = await asyncio.gather(
        service.upload(idempotency_key=concurrent_key, chunks=_chunks(_image()), metadata=metadata),
        service.upload(idempotency_key=concurrent_key, chunks=_chunks(_image()), metadata=metadata),
        return_exceptions=True,
    )

    assert replay.id == first.id
    successful = [outcome for outcome in outcomes if isinstance(outcome, MediaRecord)]
    assert successful
    assert len({record.id for record in successful}) == 1
    assert all(isinstance(outcome, (MediaRecord, IdempotencyConflictError)) for outcome in outcomes)
    async with media_database.factory() as session:
        media_count = await session.scalar(
            select(func.count())
            .select_from(SubmissionMediaModel)
            .where(SubmissionMediaModel.submission_id == media_database.submission_id)
        )
        claim_count = await session.scalar(
            select(func.count())
            .select_from(MediaUploadClaimModel)
            .where(MediaUploadClaimModel.submission_id == media_database.submission_id)
        )
    assert media_count == 2
    assert claim_count == 2
    originals = await asyncio.to_thread(lambda: list(tmp_path.rglob("original.*")))
    assert len(originals) == 2


async def test_postgres_same_key_changed_metadata_conflicts_without_duplicate(
    media_database: MediaDatabase, tmp_path: Path
) -> None:
    service = MediaUploadService(
        SqlMediaRepository(media_database.factory, media_database.submission_id),
        LocalMediaStorage(tmp_path),
        ImageValidator(),
    )
    key = uuid4()
    await service.upload(
        idempotency_key=key,
        chunks=_chunks(_image()),
        metadata=_metadata(media_database.submission_id),
    )

    with pytest.raises(IdempotencyConflictError):
        await service.upload(
            idempotency_key=key,
            chunks=_chunks(_image()),
            metadata=_metadata(media_database.submission_id, "changed"),
        )

    async with media_database.factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(SubmissionMediaModel)
            .where(SubmissionMediaModel.submission_id == media_database.submission_id)
        )
    assert count == 1
    originals = await asyncio.to_thread(lambda: list(tmp_path.rglob("original.*")))
    assert len(originals) == 1
