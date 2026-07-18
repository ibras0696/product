from collections.abc import AsyncIterable
from typing import ClassVar
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from common.exceptions import NotFoundError
from main import create_app
from modules.media.repository import MediaRecord, OrphanMedia
from modules.media.storage import UploadTooLargeError
from modules.media.validation import MediaValidationError
from modules.submissions.public import draft_cookie_name, get_submission_service, media_routes


class FakeOwnerService:
    def __init__(self, submission_id: UUID) -> None:
        self._submission_id = submission_id

    async def authorize_owner(
        self, submission_id: UUID, cookie: str | None, *, editable: bool
    ) -> None:
        if submission_id != self._submission_id or cookie != "owner-secret":
            raise NotFoundError("Submission not found")


class FakeMediaRepository:
    def __init__(self, record: MediaRecord) -> None:
        self.records: dict[UUID, MediaRecord] = {record.id: record}

    async def list_for_submission(self, submission_id: UUID) -> tuple[MediaRecord, ...]:
        return tuple(item for item in self.records.values() if item.submission_id == submission_id)

    async def update_metadata(
        self, submission_id: UUID, media_id: UUID, changes: dict[str, object]
    ) -> MediaRecord | None:
        record = self.records.get(media_id)
        if record is None or record.submission_id != submission_id:
            return None
        caption = changes.get("caption", record.caption)
        author = changes.get("author", record.author)
        source = changes.get("source_description", record.source_description)
        approximate_date = changes.get("approximate_date", record.approximate_date)
        related_entity_id = changes.get("related_entity_id", record.related_entity_id)
        assert isinstance(caption, str)
        assert isinstance(author, str)
        assert isinstance(source, str)
        assert approximate_date is None or isinstance(approximate_date, str)
        assert related_entity_id is None or isinstance(related_entity_id, UUID)
        updated = MediaRecord(
            id=record.id,
            submission_id=record.submission_id,
            original_name=record.original_name,
            checksum=record.checksum,
            original_key=record.original_key,
            preview_key=record.preview_key,
            mime_type=record.mime_type,
            size_bytes=record.size_bytes,
            width=record.width,
            height=record.height,
            caption=caption,
            author=author,
            approximate_date=approximate_date,
            source_description=source,
            related_entity_id=related_entity_id,
        )
        self.records[media_id] = updated
        return updated

    async def get_keys(self, submission_id: UUID, media_id: UUID) -> OrphanMedia | None:
        record = self.records.get(media_id)
        if record is None or record.submission_id != submission_id:
            return None
        return OrphanMedia(record.id, record.original_key, record.preview_key)

    async def delete(self, submission_id: UUID, media_id: UUID) -> None:
        self.records.pop(media_id, None)


class FakeStorage:
    def __init__(self) -> None:
        self.deleted: list[tuple[str, ...]] = []

    async def delete(self, keys: tuple[str, ...]) -> None:
        self.deleted.append(keys)


class FakeUploadService:
    outcome: ClassVar[MediaRecord | Exception]

    def __init__(self, *_: object, **__: object) -> None:
        pass

    async def upload(
        self,
        *,
        idempotency_key: UUID,
        chunks: AsyncIterable[bytes],
        metadata: object,
    ) -> MediaRecord:
        async for _ in chunks:
            pass
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def scenario(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, UUID, MediaRecord, FakeStorage]:
    submission_id = uuid4()
    record = MediaRecord(
        id=uuid4(),
        submission_id=submission_id,
        original_name="museum.png",
        checksum="private-checksum",
        original_key="draft/private/original.png",
        preview_key="draft/private/preview.webp",
        mime_type="image/png",
        size_bytes=128,
        width=20,
        height=10,
        caption="Экспонат",
        author="Автор",
        approximate_date=None,
        source_description="Архив",
        related_entity_id=None,
    )
    repository = FakeMediaRepository(record)
    storage = FakeStorage()
    FakeUploadService.outcome = record
    monkeypatch.setattr(media_routes, "_repository", lambda _: repository)
    monkeypatch.setattr(media_routes, "_storage", lambda: storage)
    monkeypatch.setattr(media_routes, "MediaUploadService", FakeUploadService)
    app = create_app()
    app.dependency_overrides[get_submission_service] = lambda: FakeOwnerService(submission_id)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(draft_cookie_name(submission_id), "owner-secret")
    return client, submission_id, record, storage


def _multipart() -> dict[str, str]:
    return {
        "caption": "Экспонат",
        "author": "Автор",
        "source_description": "Архив",
    }


def _assert_no_private_fields(payload: object) -> None:
    serialized = str(payload)
    assert "original_key" not in serialized
    assert "preview_key" not in serialized
    assert "checksum" not in serialized


def test_owner_uploads_lists_updates_and_deletes_media(
    scenario: tuple[TestClient, UUID, MediaRecord, FakeStorage],
) -> None:
    client, submission_id, record, storage = scenario
    base = f"/api/v1/submissions/{submission_id}/media"
    origin = {"Origin": "https://testserver"}
    uploaded = client.post(
        base,
        headers={**origin, "Idempotency-Key": str(uuid4())},
        data=_multipart(),
        files={"file": ("museum.png", b"png", "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["data"]["id"] == str(record.id)
    _assert_no_private_fields(uploaded.json())

    listed = client.get(base)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["data"]] == [str(record.id)]
    _assert_no_private_fields(listed.json())

    patched = client.patch(f"{base}/{record.id}", json={"caption": "Новая подпись"}, headers=origin)
    assert patched.status_code == 200
    assert patched.json()["data"]["caption"] == "Новая подпись"

    deleted = client.delete(f"{base}/{record.id}", headers=origin)
    assert deleted.status_code == 200
    assert deleted.json()["data"] is None
    assert storage.deleted == [(record.original_key, record.preview_key)]


def test_attacker_and_guessed_submission_uuid_receive_same_404(
    scenario: tuple[TestClient, UUID, MediaRecord, FakeStorage],
) -> None:
    client, submission_id, _, _ = scenario
    base = f"/api/v1/submissions/{submission_id}/media"
    client.cookies.set(draft_cookie_name(submission_id), "attacker-secret")
    attacker = client.get(base)
    guessed = client.get(f"/api/v1/submissions/{uuid4()}/media")
    assert attacker.status_code == guessed.status_code == 404
    assert attacker.json()["error"]["code"] == guessed.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    ("outcome", "status_code", "error_code"),
    [
        (UploadTooLargeError("too large"), 413, "payload_too_large"),
        (MediaValidationError("invalid image"), 415, "unsupported_media_type"),
    ],
)
def test_upload_failures_use_safe_error_envelope(
    scenario: tuple[TestClient, UUID, MediaRecord, FakeStorage],
    outcome: Exception,
    status_code: int,
    error_code: str,
) -> None:
    client, submission_id, _, _ = scenario
    FakeUploadService.outcome = outcome
    response = client.post(
        f"/api/v1/submissions/{submission_id}/media",
        headers={"Origin": "https://testserver", "Idempotency-Key": str(uuid4())},
        data=_multipart(),
        files={"file": ("bad.bin", b"bad", "application/octet-stream")},
    )
    assert response.status_code == status_code, response.text
    assert response.json()["ok"] is False
    assert response.json()["data"] is None
    assert response.json()["error"]["code"] == error_code
    _assert_no_private_fields(response.json())


def test_invalid_idempotency_key_is_validation_error(
    scenario: tuple[TestClient, UUID, MediaRecord, FakeStorage],
) -> None:
    client, submission_id, _, _ = scenario
    response = client.post(
        f"/api/v1/submissions/{submission_id}/media",
        headers={"Origin": "https://testserver", "Idempotency-Key": "not-a-uuid"},
        data=_multipart(),
        files={"file": ("museum.png", b"png", "image/png")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
