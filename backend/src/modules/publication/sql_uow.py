from collections.abc import Awaitable, Callable
from typing import cast
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.uow import UnitOfWork
from modules.audit.contracts import SqlAuditRepository
from modules.catalog.contracts import CatalogPublicationAdapter
from modules.moderation.contracts import PublishAction
from modules.publication.domain import (
    CatalogPublicationResult,
    PublicationAuditInput,
    PublicationSubmission,
)
from modules.publication.exceptions import InvalidPublicationTransitionError
from modules.publication.repository import SqlPublicationRepository
from modules.submissions.contracts import SubmissionStatus, SubmissionType


class SqlSubmissionPublicationAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock(self, submission_id: UUID) -> PublicationSubmission | None:
        row = (
            (
                await self._session.execute(
                    text(
                        """SELECT s.id,s.type,s.status,s.version,s.related_entity_id,
                    c.actor_account_id claimed_by
                    FROM submissions_submissions s
                    LEFT JOIN moderation_claims c ON c.submission_id=s.id
                    WHERE s.id=:id FOR UPDATE OF s"""
                    ),
                    {"id": submission_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return PublicationSubmission(
            id=row["id"],
            type=SubmissionType(row["type"]),
            status=SubmissionStatus(row["status"]),
            version=row["version"],
            claimed_by=row["claimed_by"],
            related_entity_id=row["related_entity_id"],
        )

    async def mark_published(
        self, submission: PublicationSubmission, actor_id: UUID, comment: str
    ) -> None:
        next_version = submission.version + 1
        updated_id = await self._session.scalar(
            text(
                """UPDATE submissions_submissions
                SET status='published',version=:next_version,updated_at=now()
                WHERE id=:id AND version=:version AND status='in_review'
                RETURNING id"""
            ),
            {
                "id": submission.id,
                "version": submission.version,
                "next_version": next_version,
            },
        )
        if updated_id is None:
            raise InvalidPublicationTransitionError("Submission changed during publication")
        await self._session.execute(
            text(
                """INSERT INTO submissions_status_history
                (id,submission_id,sequence,from_status,to_status,actor_account_id,public_comment)
                VALUES (:history_id,:submission_id,:sequence,'in_review','published',
                        :actor,:comment)"""
            ),
            {
                "history_id": uuid4(),
                "submission_id": submission.id,
                "sequence": next_version,
                "actor": actor_id,
                "comment": comment,
            },
        )
        await self._session.execute(
            text("DELETE FROM moderation_claims WHERE submission_id=:id"),
            {"id": submission.id},
        )


class SqlMediaPublicationAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def publish(
        self,
        submission_id: UUID,
        action: PublishAction,
        payload: BaseModel,
        catalog: CatalogPublicationResult,
    ) -> tuple[UUID, ...]:
        values = payload.model_dump()
        approved = tuple(cast(list[UUID], values.get("approved_media_ids", [])))
        if not approved:
            return ()
        entity_id = _target_entity(action, values, catalog)
        rows = (
            (
                await self._session.execute(
                    text(
                        """SELECT id,original_storage_key,preview_storage_key,mime_type,
                    width,height,
                    caption,author,approximate_date,source_description
                    FROM media_submission_assets
                    WHERE submission_id=:submission_id AND id=ANY(:ids) AND status='pending'
                    ORDER BY id FOR UPDATE"""
                    ),
                    {"submission_id": submission_id, "ids": list(approved)},
                )
            )
            .mappings()
            .all()
        )
        if len(rows) != len(set(approved)):
            raise InvalidPublicationTransitionError("Approved media does not belong to submission")
        for row in rows:
            await self._publish_row(row, entity_id)
        await self._session.execute(
            text(
                "DELETE FROM media_submission_assets "
                "WHERE submission_id=:submission_id AND id=ANY(:ids)"
            ),
            {"submission_id": submission_id, "ids": list(approved)},
        )
        return tuple(row["id"] for row in rows)

    async def _publish_row(self, row: object, entity_id: UUID) -> None:
        values = cast(dict[str, object], row)
        media_id = cast(UUID, values["id"])
        await self._session.execute(
            text(
                """INSERT INTO media_assets
                (id,entity_id,storage_key,public_url,preview_url,mime_type,width,height,
                 caption,author,approximate_date,source_description,status)
                VALUES (:id,:entity_id,:storage_key,:public_url,:preview_url,:mime_type,
                        :width,:height,
                        :caption,:author,:approximate_date,:source_description,'published')"""
            ),
            {
                **values,
                "entity_id": entity_id,
                "storage_key": values["original_storage_key"],
                "public_url": f"/api/v1/media/{media_id}/original",
                "preview_url": f"/api/v1/media/{media_id}/preview",
            },
        )


class SqlPublicationAuditAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = SqlAuditRepository(session)

    async def record_publication(self, audit: PublicationAuditInput) -> UUID:
        return await self._repository.create(
            actor_id=audit.actor_id,
            action=f"submission.publish.{audit.action.value}",
            resource_type="submission",
            resource_id=audit.submission_id,
            version=audit.from_version + 1,
        )


class SqlPublicationUnitOfWork(UnitOfWork):
    async def __aenter__(self) -> "SqlPublicationUnitOfWork":
        await super().__aenter__()
        self.publications = SqlPublicationRepository(self.session)
        self.submissions = SqlSubmissionPublicationAdapter(self.session)
        self.catalog = CatalogPublicationAdapter(self.session)
        self.media = SqlMediaPublicationAdapter(self.session)
        self.audit = SqlPublicationAuditAdapter(self.session)
        return self

    def after_commit(self, hook: Callable[[], Awaitable[None]]) -> None:
        super().after_commit(hook)


def _target_entity(
    action: PublishAction,
    values: dict[str, object],
    catalog: CatalogPublicationResult,
) -> UUID:
    if action is PublishAction.CREATE_ENTITY and catalog.entity_ids:
        return catalog.entity_ids[0]
    candidate = values.get("entity_id") or values.get("target_entity_id")
    if isinstance(candidate, UUID):
        return candidate
    raise InvalidPublicationTransitionError("Published media requires a target entity")
