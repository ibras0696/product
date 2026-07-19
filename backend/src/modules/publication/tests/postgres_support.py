from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from modules.auth.public import admin_router
from modules.moderation.contracts import PublishCommand
from modules.publication.domain import StoredPublication
from modules.publication.repository import SqlPublicationRepository
from modules.publication.sql_uow import SqlPublicationUnitOfWork
from modules.submissions.public import submissions_router


@dataclass(slots=True)
class PublicationDatabase:
    factory: async_sessionmaker[AsyncSession]
    commits: list[None]
    actor_id: UUID
    submission_id: UUID
    pending_media_id: UUID
    slug: str


class DatabaseInvalidationProbe:
    def __init__(self, factory: async_sessionmaker[AsyncSession], submission_id: UUID) -> None:
        self._factory = factory
        self._submission_id = submission_id
        self.committed_statuses: list[str] = []

    async def invalidate_public_catalog(self) -> None:
        async with self._factory() as session:
            status = await session.scalar(
                text("SELECT status FROM submissions_submissions WHERE id=:id"),
                {"id": self._submission_id},
            )
        self.committed_statuses.append(str(status))


class FailingPublicationRepository(SqlPublicationRepository):
    """Injects a failure after every publication mutation has been flushed."""

    def __init__(self, delegate: SqlPublicationRepository) -> None:
        self._delegate = delegate

    async def find(self, idempotency_key: UUID) -> StoredPublication | None:
        return await self._delegate.find(idempotency_key)

    async def add(self, idempotency_key: UUID, publication: StoredPublication) -> None:
        await self._delegate.add(idempotency_key, publication)
        raise RuntimeError("injected failure after idempotency flush")


class FailingSqlPublicationUnitOfWork(SqlPublicationUnitOfWork):
    async def __aenter__(self) -> "FailingSqlPublicationUnitOfWork":
        await super().__aenter__()
        self.publications = FailingPublicationRepository(self.publications)
        return self


def command(
    database: PublicationDatabase, *, key: UUID, comment: str = "Проверено"
) -> PublishCommand:
    return TypeAdapter(PublishCommand).validate_python(
        {
            "expected_version": 3,
            "idempotency_key": str(key),
            "action": "create_entity",
            "payload": {
                "entity": {
                    "type": "person",
                    "slug": database.slug,
                    "title": {"ru": "Проверенная личность", "ce": None},
                    "short_description": {"ru": "Кратко", "ce": None},
                    "full_description": {"ru": "Подтвержденная история", "ce": None},
                    "coordinates": None,
                    "period_from": None,
                    "period_to": None,
                },
                "relations": [],
                "sources": [
                    {
                        "title": "Архивная книга",
                        "type": "book",
                        "author": None,
                        "publisher": None,
                        "publication_year": None,
                        "url": None,
                        "archive_reference": None,
                        "description": "Проверенный источник",
                    }
                ],
                "approved_media_ids": [str(database.pending_media_id)],
            },
            "comment": comment,
        }
    )


async def seed_publication(factory: async_sessionmaker[AsyncSession]) -> PublicationDatabase:
    _register_cross_context_tables()
    actor_id, submission_id, media_id = uuid4(), uuid4(), uuid4()
    slug = f"publication-{uuid4()}"
    async with factory.begin() as session:
        await _insert_actor(session, actor_id)
        await _insert_submission(session, submission_id)
        await _insert_claim(session, submission_id, actor_id)
        await _insert_media(session, submission_id, media_id)
    return PublicationDatabase(factory, [], actor_id, submission_id, media_id, slug)


def _register_cross_context_tables() -> None:
    """Load FK targets needed by SQLAlchemy's shared application metadata."""
    assert admin_router is not None
    assert submissions_router is not None


async def _insert_actor(session: AsyncSession, actor_id: UUID) -> None:
    await session.execute(
        text(
            """INSERT INTO auth_accounts (id,email,password_hash,status,display_name)
            VALUES (:id,:email,'test-hash','active','Moderator')"""
        ),
        {"id": actor_id, "email": f"publication-{actor_id}@example.test"},
    )


async def _insert_submission(session: AsyncSession, submission_id: UUID) -> None:
    await session.execute(
        text(
            """INSERT INTO submissions_submissions
            (id,type,status,version,title,description,source_description,author_name,
             contact,consent,owner_capability_hash,owner_capability_expires_at,tracking_code_hash)
            VALUES (:id,'new_entity','in_review',3,'Publication','Description','Source',
                    'Author','contact@example.test',true,:owner_hash,:expires_at,:tracking_hash)"""
        ),
        {
            "id": submission_id,
            "owner_hash": uuid4().hex,
            "expires_at": datetime(2099, 1, 1, tzinfo=UTC),
            "tracking_hash": uuid4().hex,
        },
    )


async def _insert_claim(session: AsyncSession, submission_id: UUID, actor_id: UUID) -> None:
    await session.execute(
        text(
            """INSERT INTO moderation_claims
            (id,submission_id,actor_account_id,claimed_version)
            VALUES (:id,:submission_id,:actor_id,3)"""
        ),
        {"id": uuid4(), "submission_id": submission_id, "actor_id": actor_id},
    )


async def _insert_media(session: AsyncSession, submission_id: UUID, media_id: UUID) -> None:
    await session.execute(
        text(
            """INSERT INTO media_submission_assets
            (id,submission_id,original_name,checksum,original_storage_key,preview_storage_key,
             mime_type,size_bytes,width,height,caption,author,source_description,status,expires_at)
            VALUES (:id,:submission_id,'archive.png',:checksum,:original_key,:preview_key,
                    'image/png',1024,32,24,'Архив','Автор','Фонд','pending',:expires_at)"""
        ),
        {
            "id": media_id,
            "submission_id": submission_id,
            "checksum": uuid4().hex + uuid4().hex,
            "original_key": f"pending/{media_id}/original.png",
            "preview_key": f"pending/{media_id}/preview.webp",
            "expires_at": datetime(2099, 1, 1, tzinfo=UTC),
        },
    )


async def scalar(factory: async_sessionmaker[AsyncSession], query: str, **params: Any) -> Any:
    async with factory() as session:
        return await session.scalar(text(query), params)


async def truncate_publication_data(factory: async_sessionmaker[AsyncSession]) -> None:
    bind = factory.kw.get("bind")
    database_name = make_url(str(bind.url)).database if bind is not None else None
    if not database_name or not database_name.endswith("_test"):
        raise RuntimeError("publication integration cleanup requires a *_test database")
    async with factory.begin() as session:
        await session.execute(
            text(
                "TRUNCATE auth_accounts, submissions_submissions, catalog_entities, "
                "catalog_sources CASCADE"
            )
        )
