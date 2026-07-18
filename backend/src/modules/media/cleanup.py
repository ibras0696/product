from dataclasses import dataclass
from datetime import datetime

from modules.media.repository import OrphanRepositoryPort
from modules.media.storage import MediaStoragePort, StorageError


@dataclass(frozen=True, slots=True)
class CleanupResult:
    selected: int
    deleted: int
    failed: int


class OrphanCleanupService:
    def __init__(self, repository: OrphanRepositoryPort, storage: MediaStoragePort) -> None:
        self._repository = repository
        self._storage = storage

    async def run(self, *, before: datetime, batch_size: int = 100) -> CleanupResult:
        if not 1 <= batch_size <= 500:
            raise ValueError("batch_size must be between 1 and 500")
        orphans = await self._repository.list_expired_orphans(before=before, limit=batch_size)
        deleted = 0
        failed = 0
        for orphan in orphans:
            try:
                await self._storage.delete((orphan.original_key, orphan.preview_key))
                await self._repository.delete_orphan(orphan.id)
                deleted += 1
            except StorageError:
                failed += 1
        return CleanupResult(selected=len(orphans), deleted=deleted, failed=failed)
