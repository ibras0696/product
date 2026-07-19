import asyncio
import hashlib
import os
from collections.abc import AsyncIterable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4


class StorageError(Exception):
    """A safe, typed storage boundary failure."""


class UploadTooLargeError(StorageError):
    pass


class UploadTimeoutError(StorageError):
    pass


@dataclass(frozen=True, slots=True)
class StagedUpload:
    path: Path
    size_bytes: int
    checksum: str


@dataclass(frozen=True, slots=True)
class StoredObjects:
    original_key: str
    preview_key: str


class MediaStoragePort(Protocol):
    async def stage(
        self, chunks: AsyncIterable[bytes], *, max_bytes: int, timeout_seconds: float
    ) -> StagedUpload: ...

    async def persist(
        self,
        staged: StagedUpload,
        *,
        original: bytes,
        preview: bytes,
        extension: str,
    ) -> StoredObjects: ...

    async def discard_stage(self, path: Path) -> None: ...

    async def delete(self, keys: tuple[str, ...]) -> None: ...


class LocalMediaStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._temporary = self._root / ".temporary"

    async def stage(
        self,
        chunks: AsyncIterable[bytes],
        *,
        max_bytes: int,
        timeout_seconds: float,
    ) -> StagedUpload:
        await asyncio.to_thread(self._temporary.mkdir, parents=True, exist_ok=True)
        path = self._temporary / f"{uuid4().hex}.upload"
        try:
            async with asyncio.timeout(timeout_seconds):
                return await self._write_stream(path, chunks, max_bytes)
        except TimeoutError as exc:
            await self.discard_stage(path)
            raise UploadTimeoutError("Upload timed out") from exc
        except BaseException:
            await self.discard_stage(path)
            raise

    async def persist(
        self,
        staged: StagedUpload,
        *,
        original: bytes,
        preview: bytes,
        extension: str,
    ) -> StoredObjects:
        asset_id = uuid4().hex
        original_key = f"draft/{asset_id}/original.{extension}"
        preview_key = f"draft/{asset_id}/preview.webp"
        original_path = self._path_for_key(original_key)
        preview_path = self._path_for_key(preview_key)
        try:
            await asyncio.to_thread(
                self._persist_pair, original_path, original, preview_path, preview
            )
        except OSError as exc:
            await self.delete((original_key, preview_key))
            raise StorageError("Media storage is unavailable") from exc
        finally:
            await self.discard_stage(staged.path)
        return StoredObjects(original_key=original_key, preview_key=preview_key)

    async def discard_stage(self, path: Path) -> None:
        if path.parent == self._temporary:
            await asyncio.to_thread(path.unlink, missing_ok=True)

    async def delete(self, keys: tuple[str, ...]) -> None:
        for key in keys:
            try:
                await asyncio.to_thread(self._path_for_key(key).unlink, missing_ok=True)
            except OSError as exc:
                raise StorageError("Media storage is unavailable") from exc

    def resolve_key(self, key: str) -> Path:
        return self._path_for_key(key)

    async def _write_stream(
        self, path: Path, chunks: AsyncIterable[bytes], max_bytes: int
    ) -> StagedUpload:
        digest = hashlib.sha256()
        size = 0
        target = None
        try:
            target = await asyncio.to_thread(path.open, "xb")
            async for chunk in chunks:
                size += len(chunk)
                if size > max_bytes:
                    raise UploadTooLargeError("Upload exceeds the configured limit")
                digest.update(chunk)
                await self._write_chunk(target, chunk)
        except OSError as exc:
            raise StorageError("Media storage is unavailable") from exc
        finally:
            if target is not None:
                await asyncio.to_thread(target.close)
        return StagedUpload(path=path, size_bytes=size, checksum=digest.hexdigest())

    @staticmethod
    async def _write_chunk(target: BinaryIO, chunk: bytes) -> None:
        task = asyncio.create_task(asyncio.to_thread(target.write, chunk))
        try:
            await task
        except asyncio.CancelledError:
            await task
            raise

    def _path_for_key(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root):
            raise StorageError("Invalid storage key")
        return path

    @staticmethod
    def _persist_pair(
        original_path: Path, original: bytes, preview_path: Path, preview: bytes
    ) -> None:
        original_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_original = original_path.with_suffix(".pending")
        temporary_preview = preview_path.with_suffix(".pending")
        try:
            temporary_original.write_bytes(original)
            temporary_preview.write_bytes(preview)
            os.replace(temporary_original, original_path)
            os.replace(temporary_preview, preview_path)
        finally:
            temporary_original.unlink(missing_ok=True)
            temporary_preview.unlink(missing_ok=True)
