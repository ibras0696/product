from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import aclosing
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from modules.exports.streaming import CsvExportEncoder, JsonExportEncoder

MAX_EXPORT_ROWS = 10_000
MAX_EXPORT_BYTES = 100 * 1024 * 1024
EXPORT_PERMISSION = "catalog:export"


class ExportFormat(StrEnum):
    JSON = "json"
    CSV = "csv"


class ExportStatus(StrEnum):
    PUBLISHED = "published"
    ALL = "all"


class ExportForbiddenError(PermissionError):
    """Raised when the caller has not proved catalog:export permission."""


class ExportTooLargeError(ValueError):
    """Raised before or during streaming when a hard export limit is exceeded."""


@dataclass(frozen=True, slots=True)
class ExportRecord:
    record_type: str
    values: dict[str, object]


class ExportRepository(Protocol):
    async def count_records(self, status: ExportStatus) -> int: ...

    def iter_records(self, status: ExportStatus) -> AsyncGenerator[ExportRecord]: ...


@dataclass(frozen=True, slots=True)
class ExportStream:
    body: AsyncIterator[bytes]
    media_type: str
    filename: str


DisconnectProbe = Callable[[], Awaitable[bool]]


class CatalogExportService:
    def __init__(self, repository: ExportRepository) -> None:
        self._repository = repository

    async def export(
        self,
        *,
        format: ExportFormat,
        status: ExportStatus,
        permission_granted: bool,
        is_disconnected: DisconnectProbe | None = None,
    ) -> ExportStream:
        if not permission_granted:
            raise ExportForbiddenError(f"{EXPORT_PERMISSION} permission is required")
        if await self._repository.count_records(status) > MAX_EXPORT_ROWS:
            raise ExportTooLargeError(f"Export exceeds {MAX_EXPORT_ROWS} records")
        encoder = JsonExportEncoder() if format is ExportFormat.JSON else CsvExportEncoder()
        body = self._bounded_stream(
            encoder=encoder,
            records=self._repository.iter_records(status),
            is_disconnected=is_disconnected,
        )
        return ExportStream(
            body=body,
            media_type=encoder.media_type,
            filename=f"catalog-export-{status.value}.{format.value}",
        )

    async def _bounded_stream(
        self,
        *,
        encoder: JsonExportEncoder | CsvExportEncoder,
        records: AsyncGenerator[ExportRecord],
        is_disconnected: DisconnectProbe | None,
    ) -> AsyncIterator[bytes]:
        emitted = 0
        count = 0
        async with aclosing(records):
            first = encoder.start()
            emitted += len(first)
            yield first
            async for record in records:
                if is_disconnected is not None and await is_disconnected():
                    return
                count += 1
                if count > MAX_EXPORT_ROWS:
                    raise ExportTooLargeError(f"Export exceeds {MAX_EXPORT_ROWS} records")
                chunk = encoder.record(record, first=count == 1)
                emitted += len(chunk)
                if emitted > MAX_EXPORT_BYTES:
                    raise ExportTooLargeError(f"Export exceeds {MAX_EXPORT_BYTES} bytes")
                yield chunk
            end = encoder.end()
            if emitted + len(end) > MAX_EXPORT_BYTES:
                raise ExportTooLargeError(f"Export exceeds {MAX_EXPORT_BYTES} bytes")
            yield end
