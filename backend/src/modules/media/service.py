import asyncio
import hashlib
import json
from collections.abc import AsyncIterable
from dataclasses import asdict, dataclass
from uuid import UUID, uuid4

from modules.media.repository import (
    ClaimKind,
    IdempotencyConflictError,
    MediaRecord,
    MediaRepositoryPort,
    SubmissionMediaRepositoryPort,
)
from modules.media.storage import MediaStoragePort, StoredObjects
from modules.media.validation import ImageValidator


@dataclass(frozen=True, slots=True)
class UploadMetadata:
    submission_id: UUID
    original_name: str
    caption: str
    author: str
    approximate_date: str | None
    source_description: str
    related_entity_id: UUID | None


class MediaUploadService:
    def __init__(
        self,
        repository: MediaRepositoryPort,
        storage: MediaStoragePort,
        validator: ImageValidator,
        *,
        max_bytes: int = 10 * 1024 * 1024,
        timeout_seconds: float = 30,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._validator = validator
        self._max_bytes = max_bytes
        self._timeout_seconds = timeout_seconds

    async def upload(
        self,
        *,
        idempotency_key: UUID,
        chunks: AsyncIterable[bytes],
        metadata: UploadMetadata,
    ) -> MediaRecord:
        staged = await self._storage.stage(
            chunks, max_bytes=self._max_bytes, timeout_seconds=self._timeout_seconds
        )
        fingerprint = self._fingerprint(staged.checksum, metadata)
        try:
            claim = await self._repository.claim(idempotency_key, fingerprint)
        except BaseException:
            await self._storage.discard_stage(staged.path)
            raise
        if claim.kind is ClaimKind.REPLAY:
            await self._storage.discard_stage(staged.path)
            if claim.record is None:
                raise IdempotencyConflictError("Upload with this key is still in progress")
            return claim.record
        stored: StoredObjects | None = None
        try:
            validated = await asyncio.to_thread(self._validator.validate, staged.path)
            stored = await self._storage.persist(
                staged,
                original=validated.original,
                preview=validated.preview,
                extension=validated.extension,
            )
            record = MediaRecord(
                id=uuid4(),
                submission_id=metadata.submission_id,
                original_name=metadata.original_name,
                checksum=staged.checksum,
                original_key=stored.original_key,
                preview_key=stored.preview_key,
                mime_type=validated.mime_type,
                size_bytes=staged.size_bytes,
                width=validated.width,
                height=validated.height,
                caption=metadata.caption,
                author=metadata.author,
                approximate_date=metadata.approximate_date,
                source_description=metadata.source_description,
                related_entity_id=metadata.related_entity_id,
            )
            await self._repository.complete(idempotency_key, fingerprint, record)
            return record
        except BaseException:
            if stored is not None:
                await self._storage.delete((stored.original_key, stored.preview_key))
            await self._storage.discard_stage(staged.path)
            await self._repository.abort(idempotency_key, fingerprint)
            raise

    @staticmethod
    def _fingerprint(checksum: str, metadata: UploadMetadata) -> str:
        payload = asdict(metadata)
        payload["submission_id"] = str(metadata.submission_id)
        payload["related_entity_id"] = str(metadata.related_entity_id or "")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(checksum.encode() + b":" + encoded).hexdigest()


class SubmissionMediaService:
    def __init__(
        self, repository: SubmissionMediaRepositoryPort, storage: MediaStoragePort
    ) -> None:
        self._repository = repository
        self._storage = storage

    async def list(self, submission_id: UUID) -> tuple[MediaRecord, ...]:
        return await self._repository.list_for_submission(submission_id)

    async def update(
        self, submission_id: UUID, media_id: UUID, changes: dict[str, object]
    ) -> MediaRecord | None:
        return await self._repository.update_metadata(submission_id, media_id, changes)

    async def delete(self, submission_id: UUID, media_id: UUID) -> bool:
        keys = await self._repository.get_keys(submission_id, media_id)
        if keys is None:
            return False
        await self._storage.delete((keys.original_key, keys.preview_key))
        await self._repository.delete(submission_id, media_id)
        return True
