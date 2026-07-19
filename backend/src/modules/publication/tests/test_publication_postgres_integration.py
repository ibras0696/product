import asyncio
import os
from collections.abc import AsyncIterator
from typing import cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from modules.publication.exceptions import IdempotencyConflictError
from modules.publication.service import PublicationService
from modules.publication.sql_uow import SqlPublicationUnitOfWork
from modules.publication.tests.postgres_support import (
    DatabaseInvalidationProbe,
    FailingSqlPublicationUnitOfWork,
    PublicationDatabase,
    command,
    scalar,
    seed_publication,
    truncate_publication_data,
)

DATABASE_URL = os.getenv("DATABASE_URL")
IS_TEST_DATABASE = bool(
    DATABASE_URL
    and DATABASE_URL.rsplit("/", maxsplit=1)[-1].split("?", maxsplit=1)[0].endswith("_test")
)
pytestmark = pytest.mark.skipif(
    not IS_TEST_DATABASE,
    reason="DATABASE_URL for PostgreSQL publication scenarios must use a *_test database",
)


@pytest_asyncio.fixture
async def publication_database() -> AsyncIterator[PublicationDatabase]:
    assert DATABASE_URL is not None
    commits: list[None] = []

    class CountingSession(AsyncSession):
        async def commit(self) -> None:
            commits.append(None)
            await super().commit()

    engine = create_async_engine(DATABASE_URL)
    factory = cast(
        async_sessionmaker[AsyncSession],
        async_sessionmaker(engine, class_=CountingSession, expire_on_commit=False),
    )
    await truncate_publication_data(factory)
    database = await seed_publication(factory)
    database.commits = commits
    commits.clear()
    try:
        yield database
    finally:
        await truncate_publication_data(factory)
        await engine.dispose()


async def test_real_postgres_publish_commits_complete_slice_then_invalidates(
    publication_database: PublicationDatabase,
) -> None:
    database = publication_database
    probe = DatabaseInvalidationProbe(database.factory, database.submission_id)

    result = await PublicationService(
        lambda: SqlPublicationUnitOfWork(database.factory), probe
    ).publish(database.submission_id, database.actor_id, command(database, key=uuid4()))

    assert result.status == "published"
    assert len(result.published_entity_ids) == 1
    assert len(result.published_source_ids) == 1
    assert result.published_media_ids == [database.pending_media_id]
    assert len(database.commits) == 1
    assert probe.committed_statuses == ["published"]
    await _assert_published_state(database, result.published_entity_ids[0])


async def test_failure_after_final_flush_rolls_back_entire_publication(
    publication_database: PublicationDatabase,
) -> None:
    database = publication_database
    probe = DatabaseInvalidationProbe(database.factory, database.submission_id)

    with pytest.raises(RuntimeError, match="after idempotency flush"):
        await PublicationService(
            lambda: FailingSqlPublicationUnitOfWork(database.factory), probe
        ).publish(database.submission_id, database.actor_id, command(database, key=uuid4()))

    assert len(database.commits) == 0
    assert probe.committed_statuses == []
    assert (
        await scalar(
            database.factory,
            "SELECT status FROM submissions_submissions WHERE id=:id",
            id=database.submission_id,
        )
        == "in_review"
    )
    assert await scalar(database.factory, "SELECT count(*) FROM moderation_claims") == 1
    assert await scalar(database.factory, "SELECT count(*) FROM media_submission_assets") == 1
    for table in (
        "catalog_entities",
        "catalog_sources",
        "media_assets",
        "audit_entries",
        "publication_idempotency_records",
        "submissions_status_history",
    ):
        assert await scalar(database.factory, f"SELECT count(*) FROM {table}") == 0


async def test_same_key_concurrent_retry_replays_without_duplicate_database_writes(
    publication_database: PublicationDatabase,
) -> None:
    database = publication_database
    key = uuid4()
    probe = DatabaseInvalidationProbe(database.factory, database.submission_id)
    service = PublicationService(lambda: SqlPublicationUnitOfWork(database.factory), probe)

    first, replay = await asyncio.gather(
        service.publish(database.submission_id, database.actor_id, command(database, key=key)),
        service.publish(database.submission_id, database.actor_id, command(database, key=key)),
    )

    assert replay == first
    assert await scalar(database.factory, "SELECT count(*) FROM catalog_entities") == 1
    assert await scalar(database.factory, "SELECT count(*) FROM catalog_sources") == 1
    assert await scalar(database.factory, "SELECT count(*) FROM media_assets") == 1
    assert await scalar(database.factory, "SELECT count(*) FROM audit_entries") == 1
    assert (
        await scalar(database.factory, "SELECT count(*) FROM publication_idempotency_records") == 1
    )


async def test_same_key_with_changed_request_conflicts_without_mutation(
    publication_database: PublicationDatabase,
) -> None:
    database = publication_database
    key = uuid4()
    service = PublicationService(
        lambda: SqlPublicationUnitOfWork(database.factory),
        DatabaseInvalidationProbe(database.factory, database.submission_id),
    )
    await service.publish(database.submission_id, database.actor_id, command(database, key=key))

    with pytest.raises(IdempotencyConflictError):
        await service.publish(
            database.submission_id,
            database.actor_id,
            command(database, key=key, comment="Измененный запрос"),
        )

    assert await scalar(database.factory, "SELECT count(*) FROM catalog_entities") == 1
    assert (
        await scalar(database.factory, "SELECT count(*) FROM publication_idempotency_records") == 1
    )


async def _assert_published_state(database: PublicationDatabase, entity_id: UUID) -> None:
    assert (
        await scalar(
            database.factory,
            "SELECT status FROM submissions_submissions WHERE id=:id",
            id=database.submission_id,
        )
        == "published"
    )
    assert await scalar(database.factory, "SELECT count(*) FROM moderation_claims") == 0
    assert await scalar(database.factory, "SELECT count(*) FROM submissions_status_history") == 1
    assert await scalar(database.factory, "SELECT count(*) FROM audit_entries") == 1
    assert (
        await scalar(database.factory, "SELECT count(*) FROM publication_idempotency_records") == 1
    )
    assert await scalar(database.factory, "SELECT count(*) FROM media_submission_assets") == 0
    assert await scalar(database.factory, "SELECT count(*) FROM media_assets") == 1
    assert (
        await scalar(
            database.factory,
            "SELECT count(*) FROM media_assets WHERE entity_id=:entity_id AND status='published'",
            entity_id=entity_id,
        )
        == 1
    )
