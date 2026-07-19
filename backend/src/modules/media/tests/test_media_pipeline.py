import asyncio
import io
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from PIL import Image

from modules.media.cleanup import OrphanCleanupService
from modules.media.repository import (
    ClaimKind,
    IdempotencyClaim,
    IdempotencyConflictError,
    MediaRecord,
    OrphanMedia,
)
from modules.media.service import MediaUploadService, UploadMetadata
from modules.media.storage import (
    LocalMediaStorage,
    StorageError,
    UploadTimeoutError,
    UploadTooLargeError,
)
from modules.media.validation import ImageValidator, MediaValidationError


class FakeMediaRepository:
    def __init__(self) -> None:
        self.claims: dict[UUID, tuple[str, MediaRecord | None]] = {}
        self.completed = 0

    async def claim(self, key: UUID, fingerprint: str) -> IdempotencyClaim:
        previous = self.claims.get(key)
        if previous is None:
            self.claims[key] = (fingerprint, None)
            return IdempotencyClaim(ClaimKind.NEW)
        if previous[0] != fingerprint:
            raise IdempotencyConflictError("Idempotency key was used for another payload")
        return IdempotencyClaim(ClaimKind.REPLAY, previous[1])

    async def complete(self, key: UUID, fingerprint: str, record: MediaRecord) -> None:
        self.claims[key] = (fingerprint, record)
        self.completed += 1

    async def abort(self, key: UUID, fingerprint: str) -> None:
        if self.claims.get(key) == (fingerprint, None):
            del self.claims[key]


class FakeOrphanRepository:
    def __init__(self, orphans: tuple[OrphanMedia, ...]) -> None:
        self.orphans = orphans
        self.requested_limit = 0
        self.deleted: list[UUID] = []

    async def list_expired_orphans(
        self, *, before: datetime, limit: int
    ) -> tuple[OrphanMedia, ...]:
        self.requested_limit = limit
        return self.orphans[:limit]

    async def delete_orphan(self, media_id: UUID) -> None:
        self.deleted.append(media_id)


class FailingCompleteRepository(FakeMediaRepository):
    async def complete(self, key: UUID, fingerprint: str, record: MediaRecord) -> None:
        raise RuntimeError("database unavailable")


class PartiallyFailingStorage(LocalMediaStorage):
    def __init__(self, root: Path, failing_key: str) -> None:
        super().__init__(root)
        self._failing_key = failing_key

    async def delete(self, keys: tuple[str, ...]) -> None:
        if self._failing_key in keys:
            raise StorageError("unavailable")
        await super().delete(keys)


async def chunks(payload: bytes) -> AsyncIterator[bytes]:
    midpoint = len(payload) // 2
    yield payload[:midpoint]
    yield payload[midpoint:]


def image_bytes(
    image_format: str, *, size: tuple[int, int] = (24, 16), with_exif: bool = False
) -> bytes:
    image = Image.new("RGB", size, (120, 30, 10))
    output = io.BytesIO()
    kwargs: dict[str, object] = {}
    if with_exif:
        exif = Image.Exif()
        exif[0x010E] = "private description"
        kwargs["exif"] = exif
    image.save(output, format=image_format, **kwargs)
    return output.getvalue()


def metadata(caption: str = "caption") -> UploadMetadata:
    return UploadMetadata(uuid4(), "photo.png", caption, "author", None, "source", None)


@pytest.mark.parametrize(
    ("image_format", "mime_type"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")],
)
async def test_valid_upload_is_sanitized_previewed_and_retry_is_idempotent(
    tmp_path: Path, image_format: str, mime_type: str
) -> None:
    payload = image_bytes(image_format, with_exif=image_format == "JPEG")
    repository = FakeMediaRepository()
    storage = LocalMediaStorage(tmp_path)
    service = MediaUploadService(repository, storage, ImageValidator())
    key = uuid4()
    upload_metadata = metadata()

    first = await service.upload(
        idempotency_key=key, chunks=chunks(payload), metadata=upload_metadata
    )
    replay = await service.upload(
        idempotency_key=key, chunks=chunks(payload), metadata=upload_metadata
    )

    assert replay == first
    assert repository.completed == 1
    assert first.mime_type == mime_type
    assert first.checksum
    original = tmp_path / first.original_key
    preview = tmp_path / first.preview_key
    with Image.open(original) as sanitized:
        assert sanitized.getexif() == {}
        assert sanitized.size == (24, 16)
    with Image.open(preview) as preview_image:
        assert preview_image.format == "WEBP"
    assert not any((tmp_path / ".temporary").iterdir())


async def test_same_key_with_changed_metadata_conflicts_without_duplicate(
    tmp_path: Path,
) -> None:
    payload = image_bytes("PNG")
    repository = FakeMediaRepository()
    service = MediaUploadService(repository, LocalMediaStorage(tmp_path), ImageValidator())
    key = uuid4()
    first = await service.upload(
        idempotency_key=key, chunks=chunks(payload), metadata=metadata("first")
    )

    with pytest.raises(IdempotencyConflictError):
        await service.upload(
            idempotency_key=key, chunks=chunks(payload), metadata=metadata("changed")
        )

    assert repository.completed == 1
    assert len(list((tmp_path / "draft").rglob("original.*"))) == 1
    assert (tmp_path / first.original_key).exists()
    assert not any((tmp_path / ".temporary").iterdir())


async def test_concurrent_same_key_and_repository_failure_leave_no_duplicates(
    tmp_path: Path,
) -> None:
    payload = image_bytes("PNG")
    repository = FakeMediaRepository()
    service = MediaUploadService(repository, LocalMediaStorage(tmp_path), ImageValidator())
    key = uuid4()
    upload_metadata = metadata()
    outcomes = await asyncio.gather(
        service.upload(idempotency_key=key, chunks=chunks(payload), metadata=upload_metadata),
        service.upload(idempotency_key=key, chunks=chunks(payload), metadata=upload_metadata),
        return_exceptions=True,
    )
    assert sum(isinstance(outcome, MediaRecord) for outcome in outcomes) == 1
    assert sum(isinstance(outcome, IdempotencyConflictError) for outcome in outcomes) == 1
    assert repository.completed == 1
    assert len(list((tmp_path / "draft").rglob("original.*"))) == 1

    failed_root = tmp_path / "failed"
    failing_service = MediaUploadService(
        FailingCompleteRepository(), LocalMediaStorage(failed_root), ImageValidator()
    )
    with pytest.raises(RuntimeError, match="database unavailable"):
        await failing_service.upload(
            idempotency_key=uuid4(), chunks=chunks(payload), metadata=metadata()
        )
    assert not list(failed_root.rglob("original.*"))
    assert not list(failed_root.rglob("*.upload"))


async def test_corrupt_oversized_and_dimension_bomb_leave_no_files(tmp_path: Path) -> None:
    cases = [
        (b"not an image", 100, ImageValidator(), MediaValidationError),
        (image_bytes("PNG"), 5, ImageValidator(), UploadTooLargeError),
        (
            image_bytes("PNG", size=(20, 20)),
            10_000,
            ImageValidator(max_pixels=399),
            MediaValidationError,
        ),
    ]
    for payload, max_bytes, validator, expected in cases:
        root = tmp_path / uuid4().hex
        service = MediaUploadService(
            FakeMediaRepository(), LocalMediaStorage(root), validator, max_bytes=max_bytes
        )
        with pytest.raises(expected):
            await service.upload(
                idempotency_key=uuid4(), chunks=chunks(payload), metadata=metadata()
            )
        assert not list(root.rglob("*.upload"))
        assert not list(root.rglob("original.*"))


async def test_timeout_and_disconnected_stream_clean_temporary_file(tmp_path: Path) -> None:
    async def slow() -> AsyncIterator[bytes]:
        yield b"start"
        await asyncio.sleep(0.05)
        yield b"end"

    storage = LocalMediaStorage(tmp_path)
    with pytest.raises(UploadTimeoutError):
        await storage.stage(slow(), max_bytes=100, timeout_seconds=0.001)

    async def disconnected() -> AsyncIterator[bytes]:
        yield b"start"
        raise ConnectionError("client disconnected")

    with pytest.raises(StorageError):
        await storage.stage(disconnected(), max_bytes=100, timeout_seconds=1)
    assert not any((tmp_path / ".temporary").iterdir())


async def test_orphan_cleanup_is_bounded_repeatable_and_isolates_file_failure(
    tmp_path: Path,
) -> None:
    first = OrphanMedia(uuid4(), "draft/a/original.png", "draft/a/preview.webp")
    second = OrphanMedia(uuid4(), "draft/b/original.png", "draft/b/preview.webp")
    for orphan in (first, second):
        for key in (orphan.original_key, orphan.preview_key):
            path = tmp_path / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"data")
    repository = FakeOrphanRepository((first, second))
    service = OrphanCleanupService(
        repository, PartiallyFailingStorage(tmp_path, first.original_key)
    )

    result = await service.run(before=datetime.now(UTC), batch_size=2)

    assert result.selected == 2
    assert result.deleted == 1
    assert result.failed == 1
    assert repository.requested_limit == 2
    assert repository.deleted == [second.id]
    assert (tmp_path / first.original_key).exists()
    assert not (tmp_path / second.original_key).exists()
