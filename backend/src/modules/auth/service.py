from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy.exc import IntegrityError

from common.exceptions import ForbiddenError, UnauthorizedError
from modules.auth.domain import (
    RoleName,
    SessionState,
    evaluate_session,
    has_admin_role,
    has_permission,
    normalize_email,
    validate_password,
)
from modules.auth.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from modules.auth.models import ACTIVE_STATUS, Account, AuthSession
from modules.auth.rate_limit import AuthRateLimiterContract
from modules.auth.schemas import AdminAccount, AuthenticatedAccount, CurrentAccount
from modules.auth.tokens import SessionTokenManager
from modules.auth.uow import AuthUnitOfWorkContract


class PasswordManagerContract(Protocol):
    async def hash(self, password: str) -> str: ...

    async def verify(self, password: str, password_hash: str | None) -> bool: ...


UoWFactory = Callable[[], AuthUnitOfWorkContract]
Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class AuthSessionPolicy:
    idle_days: int
    absolute_days: int


class AuthService:
    def __init__(
        self,
        uow_factory: UoWFactory,
        passwords: PasswordManagerContract,
        rate_limiter: AuthRateLimiterContract,
        session_policy: AuthSessionPolicy,
        clock: Clock = lambda: datetime.now(UTC),
    ) -> None:
        self._uow_factory = uow_factory
        self._passwords = passwords
        self._rate_limiter = rate_limiter
        self._idle_duration = timedelta(days=session_policy.idle_days)
        self._absolute_duration = timedelta(days=session_policy.absolute_days)
        self._clock = clock
        self._tokens = SessionTokenManager()

    async def register(
        self, email: str, password: str, source: str, current_token: str | None = None
    ) -> AuthenticatedAccount:
        normalized_email = normalize_email(email)
        validate_password(password)
        await self._rate_limiter.record_registration(source, normalized_email)
        password_hash = await self._passwords.hash(password)
        account = Account(email=normalized_email, password_hash=password_hash)
        token = self._tokens.create()
        now = self._clock()
        try:
            async with self._uow_factory() as uow:
                await uow.repository.add_account(account)
                await self._revoke_presented_session(uow, current_token, now)
                await uow.repository.add_session(self._new_session(account, token, now))
        except IntegrityError as exc:
            raise EmailAlreadyRegisteredError("An account with this email already exists") from exc
        return AuthenticatedAccount(account=self._public_account(account), session_token=token)

    async def login(
        self, email: str, password: str, source: str, current_token: str | None = None
    ) -> AuthenticatedAccount:
        normalized_email = normalize_email(email)
        await self._rate_limiter.consume_login_attempt(source, normalized_email)
        async with self._uow_factory() as uow:
            account = await uow.repository.find_account_by_email(normalized_email)
            password_valid = await self._passwords.verify(
                password, account.password_hash if account else None
            )
            if account is None or not password_valid or account.status != ACTIVE_STATUS:
                raise InvalidCredentialsError("Invalid email or password")
            await self._rate_limiter.clear_login_attempts(source, normalized_email)
            token = self._tokens.create()
            now = self._clock()
            await self._revoke_presented_session(uow, current_token, now)
            await uow.repository.add_session(self._new_session(account, token, now))
        return AuthenticatedAccount(account=self._public_account(account), session_token=token)

    async def current_account(self, token: str | None) -> CurrentAccount:
        now = self._clock()
        async with self._uow_factory() as uow:
            session, account = await self._require_session(uow, token, now)
            session.last_seen_at = now
            session.idle_expires_at = min(now + self._idle_duration, session.absolute_expires_at)
        return self._public_account(account)

    async def logout(self, token: str | None) -> None:
        if token is None:
            return
        async with self._uow_factory() as uow:
            await uow.repository.revoke_session(self._tokens.digest(token), self._clock())

    async def logout_all(self, token: str | None) -> None:
        now = self._clock()
        async with self._uow_factory() as uow:
            _, account = await self._require_session(uow, token, now)
            await uow.repository.revoke_account_sessions(account.id, now)

    async def admin_account(self, token: str | None) -> AdminAccount:
        async with self._uow_factory() as uow:
            _, account = await self._require_session(uow, token, self._clock())
            role_names = await uow.repository.list_account_role_names(account.id)
            if not has_admin_role(role_names):
                raise ForbiddenError("Administrative role is required")
        return self._admin_account(account, role_names)

    async def require_permission(self, token: str | None, permission: str) -> AdminAccount:
        async with self._uow_factory() as uow:
            _, account = await self._require_session(uow, token, self._clock())
            role_names = await uow.repository.list_account_role_names(account.id)
            if not has_permission(role_names, permission):
                raise ForbiddenError("Permission is required")
        return self._admin_account(account, role_names)

    async def _require_session(
        self, uow: AuthUnitOfWorkContract, token: str | None, now: datetime
    ) -> tuple[AuthSession, Account]:
        if token is None:
            raise UnauthorizedError("Authentication is required")
        record = await uow.repository.find_session_with_account(self._tokens.digest(token))
        if record is None:
            raise UnauthorizedError("Authentication is required")
        session, account = record
        state = SessionState(
            idle_expires_at=session.idle_expires_at,
            absolute_expires_at=session.absolute_expires_at,
            revoked_at=session.revoked_at,
            account_active=account.status == ACTIVE_STATUS,
        )
        if not evaluate_session(state, now):
            raise UnauthorizedError("Authentication is required")
        return session, account

    async def _revoke_presented_session(
        self, uow: AuthUnitOfWorkContract, token: str | None, now: datetime
    ) -> None:
        if token is not None:
            await uow.repository.revoke_session(self._tokens.digest(token), now)

    def _new_session(self, account: Account, token: str, now: datetime) -> AuthSession:
        return AuthSession(
            account=account,
            account_id=account.id,
            token_hash=self._tokens.digest(token),
            idle_expires_at=min(now + self._idle_duration, now + self._absolute_duration),
            absolute_expires_at=now + self._absolute_duration,
            last_seen_at=now,
        )

    @staticmethod
    def _public_account(account: Account) -> CurrentAccount:
        return CurrentAccount(id=account.id, email=account.email, status="active")

    @staticmethod
    def _admin_account(account: Account, role_names: frozenset[str]) -> AdminAccount:
        known_roles = sorted(
            RoleName(role) for role in role_names if role in RoleName._value2member_map_
        )
        return AdminAccount(
            id=account.id,
            email=account.email,
            status="active",
            display_name=account.display_name,
            roles=known_roles,
        )
