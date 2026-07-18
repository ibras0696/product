from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class IdempotencyConflictError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class MediaRecord:
    id: UUID
    submission_id: UUID
    original_name: str
    checksum: str
    original_key: str
    preview_key: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    caption: str
    author: str
    approximate_date: str | None
    source_description: str
    related_entity_id: UUID | None


class ClaimKind(StrEnum):
    NEW = "new"
    REPLAY = "replay"


@dataclass(frozen=True, slots=True)
class IdempotencyClaim:
    kind: ClaimKind
    record: MediaRecord | None = None


class MediaRepositoryPort(Protocol):
    async def claim(self, key: UUID, fingerprint: str) -> IdempotencyClaim: ...

    async def complete(self, key: UUID, fingerprint: str, record: MediaRecord) -> None: ...

    async def abort(self, key: UUID, fingerprint: str) -> None: ...


@dataclass(frozen=True, slots=True)
class OrphanMedia:
    id: UUID
    original_key: str
    preview_key: str


class OrphanRepositoryPort(Protocol):
    async def list_expired_orphans(
        self, *, before: datetime, limit: int
    ) -> tuple[OrphanMedia, ...]: ...

    async def delete_orphan(self, media_id: UUID) -> None: ...


class SubmissionMediaRepositoryPort(Protocol):
    async def list_for_submission(self, submission_id: UUID) -> tuple[MediaRecord, ...]: ...

    async def update_metadata(
        self, submission_id: UUID, media_id: UUID, changes: dict[str, object]
    ) -> MediaRecord | None: ...

    async def get_keys(self, submission_id: UUID, media_id: UUID) -> OrphanMedia | None: ...

    async def delete(self, submission_id: UUID, media_id: UUID) -> None: ...
