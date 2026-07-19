from __future__ import annotations

import csv
import io
import json
from collections.abc import AsyncGenerator, AsyncIterator

import pytest

from modules.exports import service as service_module
from modules.exports.service import (
    CatalogExportService,
    ExportForbiddenError,
    ExportFormat,
    ExportRecord,
    ExportStatus,
    ExportTooLargeError,
)


class FakeExportRepository:
    def __init__(self, records: list[ExportRecord], *, reported_count: int | None = None) -> None:
        self.records = records
        self.reported_count = len(records) if reported_count is None else reported_count
        self.requested_statuses: list[ExportStatus] = []
        self.closed = False

    async def count_records(self, status: ExportStatus) -> int:
        self.requested_statuses.append(status)
        return self.reported_count

    async def iter_records(self, status: ExportStatus) -> AsyncGenerator[ExportRecord]:
        self.requested_statuses.append(status)
        try:
            for record in self.records:
                yield record
        finally:
            self.closed = True


async def collect(body: AsyncIterator[bytes]) -> bytes:
    return b"".join([chunk async for chunk in body])


@pytest.mark.parametrize("format", [ExportFormat.JSON, ExportFormat.CSV])
async def test_export_is_bounded_by_permission_and_uses_safe_metadata(format: ExportFormat) -> None:
    repository = FakeExportRepository([])
    service = CatalogExportService(repository)

    with pytest.raises(ExportForbiddenError):
        await service.export(
            format=format,
            status=ExportStatus.ALL,
            permission_granted=False,
        )

    stream = await service.export(
        format=format,
        status=ExportStatus.PUBLISHED,
        permission_granted=True,
    )
    payload = await collect(stream.body)

    assert repository.requested_statuses == [ExportStatus.PUBLISHED, ExportStatus.PUBLISHED]
    assert stream.filename == f"catalog-export-published.{format.value}"
    assert "/" not in stream.filename and "\\" not in stream.filename
    if format is ExportFormat.JSON:
        assert payload == b"[]"
    else:
        assert payload.startswith(b"record_type,id,")


async def test_json_stream_is_deterministic_utf8_and_drops_non_allowlisted_data() -> None:
    repository = FakeExportRepository(
        [
            ExportRecord(
                "entity",
                {
                    "id": "0001",
                    "title_ru": "Грозный",
                    "password_hash": "must-not-leak",
                    "storage_key": "private/original.jpg",
                    "contact": "private@example.test",
                },
            ),
            ExportRecord("source", {"id": "0002", "title": "Архив"}),
        ]
    )
    stream = await CatalogExportService(repository).export(
        format=ExportFormat.JSON,
        status=ExportStatus.PUBLISHED,
        permission_granted=True,
    )

    raw = await collect(stream.body)
    decoded = json.loads(raw)

    assert decoded == [
        {"record_type": "entity", "id": "0001", "title_ru": "Грозный"},
        {"record_type": "source", "id": "0002", "title": "Архив"},
    ]
    assert b"password" not in raw and b"storage_key" not in raw and b"contact" not in raw


async def test_csv_escapes_formula_injection_and_keeps_valid_rows() -> None:
    repository = FakeExportRepository(
        [ExportRecord("source", {"id": "1", "title": '  =HYPERLINK("bad")'})]
    )
    stream = await CatalogExportService(repository).export(
        format=ExportFormat.CSV,
        status=ExportStatus.ALL,
        permission_granted=True,
    )

    rows = list(csv.DictReader(io.StringIO((await collect(stream.body)).decode())))

    assert rows[0]["record_type"] == "source"
    assert rows[0]["title"] == '\'  =HYPERLINK("bad")'


async def test_row_and_byte_limits_fail_without_unbounded_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_byte_limit = service_module.MAX_EXPORT_BYTES
    service = CatalogExportService(FakeExportRepository([], reported_count=10_001))
    with pytest.raises(ExportTooLargeError, match="10000 records"):
        await service.export(
            format=ExportFormat.JSON,
            status=ExportStatus.ALL,
            permission_granted=True,
        )

    monkeypatch.setattr(service_module, "MAX_EXPORT_BYTES", 12)
    stream = await CatalogExportService(
        FakeExportRepository([ExportRecord("source", {"title": "too large"})])
    ).export(
        format=ExportFormat.JSON,
        status=ExportStatus.PUBLISHED,
        permission_granted=True,
    )
    with pytest.raises(ExportTooLargeError, match="bytes"):
        await collect(stream.body)

    monkeypatch.setattr(service_module, "MAX_EXPORT_BYTES", original_byte_limit)
    monkeypatch.setattr(service_module, "MAX_EXPORT_ROWS", 1)
    stream = await CatalogExportService(
        FakeExportRepository(
            [ExportRecord("entity", {"id": "1"}), ExportRecord("entity", {"id": "2"})],
            reported_count=1,
        )
    ).export(
        format=ExportFormat.JSON,
        status=ExportStatus.PUBLISHED,
        permission_granted=True,
    )
    with pytest.raises(ExportTooLargeError, match="1 records"):
        await collect(stream.body)


async def test_disconnect_stops_query_iterator_and_releases_it() -> None:
    repository = FakeExportRepository(
        [ExportRecord("entity", {"id": str(index)}) for index in range(3)]
    )
    probes = 0

    async def disconnected() -> bool:
        nonlocal probes
        probes += 1
        return probes == 2

    stream = await CatalogExportService(repository).export(
        format=ExportFormat.JSON,
        status=ExportStatus.PUBLISHED,
        permission_granted=True,
        is_disconnected=disconnected,
    )
    payload = await collect(stream.body)

    assert repository.closed
    assert payload.startswith(b"[")
    assert b'"id":"0"' in payload
    assert b'"id":"1"' not in payload
