from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Self, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from common.exceptions import UnauthorizedError
from modules.auth.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from modules.auth.models import ACTIVE_STATUS, Account, AuthSession
from modules.auth.repository import AuthRepository
from modules.auth.service import AuthService, AuthSessionPolicy


class InMemoryAuthRepository:
    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.sessions: dict[str, AuthSession] = {}

    async def add_account(self, account: Account) -> None:
        if account.email in self.accounts:
            raise IntegrityError("insert account", {}, Exception("duplicate"))
        account.id = uuid4()
        account.status = ACTIVE_STATUS
        self.accounts[account.email] = account

    async def find_account_by_email(self, email: str) -> Account | None:
        return self.accounts.get(email)

    async def add_session(self, session: AuthSession) -> None:
        session.id = uuid4()
        self.sessions[session.token_hash] = session

    async def find_session_with_account(
        self, token_hash: str
    ) -> tuple[AuthSession, Account] | None:
        session = self.sessions.get(token_hash)
        if session is None:
            return None
        return session, self.accounts[session.account.email]

    async def revoke_session(self, token_hash: str, revoked_at: datetime) -> None:
        session = self.sessions.get(token_hash)
        if session is not None:
            session.revoked_at = revoked_at

    async def revoke_account_sessions(self, account_id: UUID, revoked_at: datetime) -> None:
        for session in self.sessions.values():
            if session.account_id == account_id:
                session.revoked_at = revoked_at


class FakeUnitOfWork:
    def __init__(self, repository: InMemoryAuthRepository) -> None:
        self.repository = cast(AuthRepository, repository)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakePasswords:
    async def hash(self, password: str) -> str:
        return f"hashed:{password}"

    async def verify(self, password: str, password_hash: str | None) -> bool:
        return password_hash == f"hashed:{password}"


class AllowingRateLimiter:
    async def consume_login_attempt(self, source: str, account_key: str) -> None:
        return None

    async def clear_login_attempts(self, source: str, account_key: str) -> None:
        return None

    async def record_registration(self, source: str, account_key: str) -> None:
        return None


@pytest.mark.asyncio
async def test_authentication_lifecycle_covers_core_use_cases() -> None:
    repository = InMemoryAuthRepository()
    now = datetime(2026, 7, 17, tzinfo=UTC)
    service = AuthService(
        uow_factory=lambda: FakeUnitOfWork(repository),
        passwords=FakePasswords(),
        rate_limiter=AllowingRateLimiter(),
        session_policy=AuthSessionPolicy(idle_days=7, absolute_days=30),
        clock=lambda: now,
    )

    registered = await service.register(" Person@Example.COM ", "long user password", "test-source")
    assert registered.account.email == "person@example.com"
    assert await service.current_account(registered.session_token) == registered.account

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register("person@example.com", "another long password", "test-source")
    with pytest.raises(InvalidCredentialsError):
        await service.login("person@example.com", "wrong long password", "test-source")
    with pytest.raises(InvalidCredentialsError):
        await service.login("missing@example.com", "wrong long password", "test-source")

    rotated = await service.login(
        "person@example.com",
        "long user password",
        "test-source",
        current_token=registered.session_token,
    )
    with pytest.raises(UnauthorizedError):
        await service.current_account(registered.session_token)
    parallel = await service.login("person@example.com", "long user password", "test-source")
    await service.logout(parallel.session_token)
    assert await service.current_account(rotated.session_token) == rotated.account
    with pytest.raises(UnauthorizedError):
        await service.current_account(parallel.session_token)

    await service.logout_all(rotated.session_token)
    with pytest.raises(UnauthorizedError):
        await service.current_account(rotated.session_token)

    expired = await service.login("person@example.com", "long user password", "test-source")
    for session in repository.sessions.values():
        if session.revoked_at is None:
            session.idle_expires_at = now - timedelta(seconds=1)
    with pytest.raises(UnauthorizedError):
        await service.current_account(expired.session_token)
