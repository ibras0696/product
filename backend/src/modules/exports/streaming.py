from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from typing import Protocol
from uuid import UUID


class ExportRecordLike(Protocol):
    @property
    def record_type(self) -> str: ...

    @property
    def values(self) -> dict[str, object]: ...


EXPORT_COLUMNS = (
    "record_type",
    "id",
    "entity_id",
    "relation_id",
    "source_id",
    "type",
    "slug",
    "status",
    "locale",
    "name",
    "title",
    "title_ru",
    "title_ce",
    "short_description",
    "full_description",
    "short_description_ru",
    "short_description_ce",
    "full_description_ru",
    "full_description_ce",
    "description",
    "description_ru",
    "description_ce",
    "source_entity_id",
    "target_entity_id",
    "period_from",
    "period_to",
    "district_id",
    "latitude",
    "longitude",
    "author",
    "publisher",
    "publication_year",
    "url",
    "archive_reference",
    "is_verified",
    "public_url",
    "preview_url",
    "mime_type",
    "width",
    "height",
    "caption",
    "approximate_date",
    "source_description",
)
_ALLOWED_FIELDS = frozenset(EXPORT_COLUMNS) - {"record_type"}
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def allowlisted(record: ExportRecordLike) -> dict[str, object]:
    return {
        "record_type": record.record_type,
        **{key: value for key, value in record.values.items() if key in _ALLOWED_FIELDS},
    }


def _json_default(value: object) -> str:
    if isinstance(value, (UUID, date, datetime)):
        return value.isoformat() if not isinstance(value, UUID) else str(value)
    raise TypeError(f"Unsupported export value: {type(value).__name__}")


class JsonExportEncoder:
    media_type = "application/json; charset=utf-8"

    def start(self) -> bytes:
        return b"["

    def record(self, record: ExportRecordLike, *, first: bool) -> bytes:
        prefix = b"" if first else b","
        payload = json.dumps(
            allowlisted(record), ensure_ascii=False, separators=(",", ":"), default=_json_default
        )
        return prefix + payload.encode("utf-8")

    def end(self) -> bytes:
        return b"]"


class CsvExportEncoder:
    media_type = "text/csv; charset=utf-8"

    def start(self) -> bytes:
        header: dict[str, object] = dict(zip(EXPORT_COLUMNS, EXPORT_COLUMNS, strict=True))
        return self._row(header)

    def record(self, record: ExportRecordLike, *, first: bool) -> bytes:
        del first
        values = allowlisted(record)
        return self._row({column: _csv_value(values.get(column)) for column in EXPORT_COLUMNS})

    def end(self) -> bytes:
        return b""

    @staticmethod
    def _row(values: dict[str, object]) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=EXPORT_COLUMNS, lineterminator="\r\n")
        writer.writerow(values)
        return output.getvalue().encode("utf-8")


def _csv_value(value: object) -> str:
    if value is None:
        return ""
    rendered = str(value)
    if rendered.lstrip(" ").startswith(_FORMULA_PREFIXES):
        return f"'{rendered}"
    return rendered
