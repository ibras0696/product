from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self, cast
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import ForbiddenError, register_exception_handlers
from middleware.request_context import request_context
from modules.auth.public import AdminAccount, Permission, RoleName, get_auth_context
from modules.moderation.domain import ModerationDetails, ModerationMedia, ModerationSubmission
from modules.moderation.repository import MAX_MEDIA_PER_SUBMISSION, ModerationRepository
from modules.moderation.routes import get_moderation_service, router
from modules.moderation.service import ModerationPreview
from modules.submissions.contracts import SubmissionStatus, SubmissionType


def _submission() -> ModerationSubmission:
    now = datetime(2026, 7, 18, tzinfo=UTC)
    return ModerationSubmission(
        id=uuid4(),
        type=SubmissionType.NEW_MEDIA,
        status=SubmissionStatus.PENDING,
        version=2,
        title="Archive photo",
        description="A family archive photograph",
        source_description="Original print",
        author_name="Contributor",
        contact="contributor@example.com",
        consent=True,
        related_entity_id=uuid4(),
        settlement_id=None,
        submitted_at=now,
        created_at=now,
        updated_at=now,
    )


def _media() -> ModerationMedia:
    return ModerationMedia(
        id=uuid4(),
        original_name="archive.jpg",
        mime_type="image/jpeg",
        size_bytes=2048,
        width=1200,
        height=800,
        caption="Family gathering",
        author="Family archive",
        approximate_date="circa 1950",
        source_description="Scanned original print",
        related_entity_id=uuid4(),
        status="pending",
    )


class _MappingsResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> Self:
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows


class _RecordingSession:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self.statements: list[object] = []

    async def execute(self, statement: object) -> _MappingsResult:
        self.statements.append(statement)
        return _MappingsResult(self._rows)


def _row(submission: ModerationSubmission, media: ModerationMedia | None) -> dict[str, object]:
    row = {
        **asdict(submission),
        "type": submission.type.value,
        "status": submission.status.value,
    }
    if media is None:
        return {
            **row,
            **{f"media_{field}": None for field in _MEDIA_FIELDS},
        }
    return {
        **row,
        **{f"media_{field}": getattr(media, field) for field in _MEDIA_FIELDS},
    }


_MEDIA_FIELDS = (
    "id",
    "original_name",
    "mime_type",
    "size_bytes",
    "width",
    "height",
    "caption",
    "author",
    "approximate_date",
    "source_description",
    "related_entity_id",
    "status",
)


async def test_repository_maps_bounded_media_in_one_query_without_private_keys() -> None:
    submission = _submission()
    first, second = _media(), _media()
    session = _RecordingSession([_row(submission, first), _row(submission, second)])
    repository = ModerationRepository(cast(AsyncSession, session))

    details = await repository.get_details(submission.id)

    assert details == ModerationDetails(submission, (first, second))
    assert len(session.statements) == 1
    statement = cast(Any, session.statements[0])
    compiled = statement.compile()
    assert MAX_MEDIA_PER_SUBMISSION in compiled.params.values()
    assert "preview_storage_key" not in str(statement)


class _RouteService:
    def __init__(self, details: ModerationDetails, preview_path: Path) -> None:
        self._details = details
        self._preview_path = preview_path
        self.preview_calls: list[tuple[UUID, UUID]] = []

    async def details(self, submission_id: UUID) -> ModerationDetails:
        assert submission_id == self._details.submission.id
        return self._details

    async def preview(self, submission_id: UUID, media_id: UUID) -> ModerationPreview:
        self.preview_calls.append((submission_id, media_id))
        return ModerationPreview(self._preview_path)


class _RouteAuth:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.permissions: list[str] = []

    async def require_permission(self, token: str | None, permission: str) -> AdminAccount:
        del token
        self.permissions.append(permission)
        if not self.allowed:
            raise ForbiddenError("Permission is required")
        return AdminAccount(
            id=uuid4(),
            email="moderator@example.com",
            status="active",
            display_name="Moderator",
            roles=[RoleName.MODERATOR],
        )


def _client(service: _RouteService, auth: _RouteAuth) -> TestClient:
    app = FastAPI()
    app.middleware("http")(request_context)
    app.include_router(router, prefix="/api/v1")
    register_exception_handlers(app)
    app.dependency_overrides[get_moderation_service] = lambda: service
    app.dependency_overrides[get_auth_context] = lambda: SimpleNamespace(
        service=auth,
        token="session",
        source="test",
    )
    return TestClient(app)


def test_details_returns_safe_media_and_empty_media_list(tmp_path: Path) -> None:
    submission = _submission()
    media = _media()
    service = _RouteService(ModerationDetails(submission, (media,)), tmp_path / "preview.webp")
    client = _client(service, _RouteAuth())

    response = client.get(f"/api/v1/admin/submissions/{submission.id}")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["media"] == [
        {
            "id": str(media.id),
            "original_name": "archive.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 2048,
            "width": 1200,
            "height": 800,
            "preview_url": (f"/api/v1/admin/submissions/{submission.id}/media/{media.id}/preview"),
            "caption": "Family gathering",
            "author": "Family archive",
            "approximate_date": "circa 1950",
            "source_description": "Scanned original print",
            "related_entity_id": str(media.related_entity_id),
            "status": "pending",
        }
    ]
    assert all(
        private not in response.text
        for private in ("checksum", "expires_at", "storage_key", "preview_storage_key")
    )
    openapi = cast(FastAPI, client.app).openapi()
    media_schema = openapi["components"]["schemas"]["SubmissionDetails"]["properties"]["media"]
    assert media_schema == {
        "items": {"$ref": "#/components/schemas/ModerationMedia"},
        "type": "array",
        "maxItems": 10,
        "title": "Media",
    }

    service._details = ModerationDetails(submission, ())
    assert client.get(f"/api/v1/admin/submissions/{submission.id}").json()["data"]["media"] == []


def test_preview_is_available_only_after_moderation_authorization(tmp_path: Path) -> None:
    submission, media = _submission(), _media()
    preview = tmp_path / "preview.webp"
    preview.write_bytes(b"safe-preview")
    service = _RouteService(ModerationDetails(submission, (media,)), preview)
    auth = _RouteAuth(allowed=False)
    client = _client(service, auth)
    path = f"/api/v1/admin/submissions/{submission.id}/media/{media.id}/preview"

    denied = client.get(path)
    assert denied.status_code == 403
    assert service.preview_calls == []

    auth.allowed = True
    allowed = client.get(path)
    assert allowed.status_code == 200
    assert allowed.content == b"safe-preview"
    assert allowed.headers["content-type"] == "image/webp"
    assert allowed.headers["cache-control"] == "private, no-store"
    assert auth.permissions == [Permission.MODERATION_READ, Permission.MODERATION_READ]
