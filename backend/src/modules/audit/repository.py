from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.audit.models import AuditEntryModel
from modules.audit.schemas import AuditEntry, AuditListRequest, AuditPage


class SqlAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        actor_id: UUID,
        action: str,
        resource_type: str,
        resource_id: UUID,
        version: int,
    ) -> None:
        await self.create(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            version=version,
        )

    async def create(
        self,
        *,
        actor_id: UUID,
        action: str,
        resource_type: str,
        resource_id: UUID,
        version: int,
    ) -> UUID:
        model = AuditEntryModel(
            actor_account_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_version=version,
        )
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def list(self, filters: AuditListRequest) -> AuditPage:
        conditions = []
        if filters.actor_id is not None:
            conditions.append(AuditEntryModel.actor_account_id == filters.actor_id)
        if filters.action is not None:
            conditions.append(AuditEntryModel.action == filters.action)
        if filters.created_from is not None:
            conditions.append(AuditEntryModel.created_at >= filters.created_from)
        if filters.created_to is not None:
            conditions.append(AuditEntryModel.created_at <= filters.created_to)
        total = await self._session.scalar(
            select(func.count()).select_from(AuditEntryModel).where(*conditions)
        )
        rows = (
            await self._session.scalars(
                select(AuditEntryModel)
                .where(*conditions)
                .order_by(AuditEntryModel.created_at.desc(), AuditEntryModel.id.desc())
                .limit(filters.limit)
                .offset(filters.offset)
            )
        ).all()
        return AuditPage(
            items=[_view(row) for row in rows],
            limit=filters.limit,
            offset=filters.offset,
            total=int(total or 0),
        )


def _view(model: AuditEntryModel) -> AuditEntry:
    return AuditEntry(
        id=model.id,
        actor_id=model.actor_account_id,
        action=model.action,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        resource_version=model.resource_version,
        created_at=model.created_at,
    )
