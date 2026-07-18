from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.models import Account, AccountRole, AuthSession, Role


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_account(self, account: Account) -> None:
        self._session.add(account)
        await self._session.flush()

    async def find_account_by_email(self, email: str) -> Account | None:
        result = await self._session.execute(select(Account).where(Account.email == email))
        return result.scalar_one_or_none()

    async def find_role_by_name(self, name: str) -> Role | None:
        result = await self._session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def add_role(self, role: Role) -> None:
        self._session.add(role)
        await self._session.flush()

    async def add_account_role(self, account_role: AccountRole) -> None:
        self._session.add(account_role)
        await self._session.flush()

    async def list_account_role_names(self, account_id: UUID) -> frozenset[str]:
        statement = (
            select(Role.name)
            .join(AccountRole, AccountRole.role_id == Role.id)
            .where(AccountRole.account_id == account_id)
            .order_by(Role.name)
        )
        result = await self._session.execute(statement)
        return frozenset(result.scalars().all())

    async def add_session(self, session: AuthSession) -> None:
        self._session.add(session)
        await self._session.flush()

    async def find_session_with_account(
        self, token_hash: str
    ) -> tuple[AuthSession, Account] | None:
        statement = (
            select(AuthSession, Account)
            .join(Account, Account.id == AuthSession.account_id)
            .where(AuthSession.token_hash == token_hash)
        )
        result = await self._session.execute(statement)
        row = result.one_or_none()
        return (row[0], row[1]) if row is not None else None

    async def revoke_session(self, token_hash: str, revoked_at: datetime) -> None:
        statement = (
            update(AuthSession)
            .where(AuthSession.token_hash == token_hash, AuthSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        await self._session.execute(statement)

    async def revoke_account_sessions(self, account_id: UUID, revoked_at: datetime) -> None:
        statement = (
            update(AuthSession)
            .where(AuthSession.account_id == account_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        await self._session.execute(statement)
