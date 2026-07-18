from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.publication.domain import StoredPublication
from modules.publication.models import PublicationIdempotencyModel


class SqlPublicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self, idempotency_key: UUID) -> StoredPublication | None:
        model = await self._session.scalar(
            select(PublicationIdempotencyModel)
            .where(PublicationIdempotencyModel.idempotency_key == idempotency_key)
            .with_for_update()
        )
        if model is None:
            return None
        return StoredPublication(
            submission_id=model.submission_id,
            actor_id=model.actor_account_id,
            request_hash=model.request_hash,
            result=model.result,
        )

    async def add(self, idempotency_key: UUID, publication: StoredPublication) -> None:
        self._session.add(
            PublicationIdempotencyModel(
                idempotency_key=idempotency_key,
                submission_id=publication.submission_id,
                actor_account_id=publication.actor_id,
                request_hash=publication.request_hash,
                result=publication.result,
            )
        )
        await self._session.flush()
