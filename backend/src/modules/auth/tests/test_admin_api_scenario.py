from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Self, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from main import create_app
from modules.auth.dependencies import get_auth_service
from modules.auth.models import ACTIVE_STATUS, Account, AuthSession
from modules.auth.repository import AuthRepository
from modules.auth.service import AuthService, AuthSessionPolicy


class InMemoryAuthRepository:
    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.sessions: dict[str, AuthSession] = {}
        self.roles: dict[UUID, frozenset[str]] = {}

    async def add_account(self, account: Account) -> None:
        if account.email in self.accounts:
            raise IntegrityError("insert account", {}, Exception("duplicate"))
        account.id = uuid4()
        account.status = ACTIVE_STATUS
        account.display_name = ""
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
        account = next(
            account for account in self.accounts.values() if account.id == session.account_id
        )
        return session, account

    async def revoke_session(self, token_hash: str, revoked_at: datetime) -> None:
        session = self.sessions.get(token_hash)
        if session is not None:
            session.revoked_at = revoked_at

    async def revoke_account_sessions(self, account_id: UUID, revoked_at: datetime) -> None:
        for session in self.sessions.values():
            if session.account_id == account_id:
                session.revoked_at = revoked_at

    async def list_account_role_names(self, account_id: UUID) -> frozenset[str]:
        return self.roles.get(account_id, frozenset())


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


def _scenario() -> tuple[TestClient, InMemoryAuthRepository, datetime]:
    repository = InMemoryAuthRepository()
    now = datetime(2026, 7, 18, tzinfo=UTC)
    service = AuthService(
        uow_factory=lambda: FakeUnitOfWork(repository),
        passwords=FakePasswords(),
        rate_limiter=AllowingRateLimiter(),
        session_policy=AuthSessionPolicy(idle_days=7, absolute_days=30),
        clock=lambda: now,
    )
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: service
    return TestClient(app, base_url="https://testserver"), repository, now


def _assert_error(response_status: int, payload: dict[str, object], code: str) -> None:
    assert response_status in {401, 403}
    assert payload["ok"] is False
    assert payload["data"] is None
    error = payload["error"]
    assert isinstance(error, dict)
    assert error["code"] == code
    assert isinstance(error["message"], str)
    assert error["details"] is None
    assert payload["meta"] == {"request_id": "admin-scenario"}


def test_admin_me_requires_an_active_session() -> None:
    client, _, _ = _scenario()

    response = client.get("/api/v1/admin/me", headers={"X-Request-ID": "admin-scenario"})

    assert response.status_code == 401
    _assert_error(response.status_code, response.json(), "unauthorized")


@pytest.mark.parametrize("role", ["moderator", "editor", "admin"])
def test_known_administrative_roles_can_read_their_identity(role: str) -> None:
    client, repository, _ = _scenario()
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": f"{role}@example.com", "password": "long museum password"},
    )
    account = repository.accounts[f"{role}@example.com"]
    repository.roles[account.id] = frozenset({role})

    response = client.get("/api/v1/admin/me", headers={"X-Request-ID": "admin-scenario"})

    assert registered.status_code == 201
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id": str(account.id),
            "email": f"{role}@example.com",
            "status": "active",
            "display_name": "",
            "roles": [role],
        },
        "error": None,
        "meta": {"request_id": "admin-scenario"},
    }


@pytest.mark.parametrize("roles", [frozenset(), frozenset({"museum_owner"})])
def test_no_role_and_unknown_role_are_denied(roles: frozenset[str]) -> None:
    client, repository, _ = _scenario()
    client.post(
        "/api/v1/auth/register",
        json={"email": "visitor@example.com", "password": "long museum password"},
    )
    account = repository.accounts["visitor@example.com"]
    repository.roles[account.id] = roles

    response = client.get("/api/v1/admin/me", headers={"X-Request-ID": "admin-scenario"})

    assert response.status_code == 403
    _assert_error(response.status_code, response.json(), "forbidden")


@pytest.mark.parametrize("session_state", ["revoked", "expired"])
def test_revoked_and_expired_sessions_are_unauthorized(session_state: str) -> None:
    client, repository, now = _scenario()
    client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "long museum password"},
    )
    account = repository.accounts["admin@example.com"]
    repository.roles[account.id] = frozenset({"admin"})
    session = next(iter(repository.sessions.values()))
    if session_state == "revoked":
        session.revoked_at = now
    else:
        session.idle_expires_at = now - timedelta(seconds=1)

    response = client.get("/api/v1/admin/me", headers={"X-Request-ID": "admin-scenario"})

    assert response.status_code == 401
    _assert_error(response.status_code, response.json(), "unauthorized")


def test_public_registration_cannot_self_assign_an_administrative_role() -> None:
    client, repository, _ = _scenario()

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "attacker@example.com",
            "password": "long museum password",
            "roles": ["admin"],
        },
    )
    response = client.get("/api/v1/admin/me", headers={"X-Request-ID": "admin-scenario"})

    account = repository.accounts["attacker@example.com"]
    assert registration.status_code == 201
    assert repository.roles.get(account.id, frozenset()) == frozenset()
    assert response.status_code == 403
    _assert_error(response.status_code, response.json(), "forbidden")
