from pathlib import Path
from types import TracebackType
from typing import Self, cast
from uuid import uuid4

import pytest

from modules.auth.bootstrap import AdminBootstrapService, BootstrapOutcome
from modules.auth.bootstrap_inputs import read_password, required_environment
from modules.auth.exceptions import BootstrapConflictError
from modules.auth.models import Account, AccountRole, Role
from modules.auth.repository import AuthRepository


class BootstrapRepository:
    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.roles: dict[str, Role] = {}
        self.account_roles: dict[object, set[str]] = {}

    async def find_account_by_email(self, email: str) -> Account | None:
        return self.accounts.get(email)

    async def list_account_role_names(self, account_id: object) -> frozenset[str]:
        return frozenset(self.account_roles.get(account_id, set()))

    async def find_role_by_name(self, name: str) -> Role | None:
        return self.roles.get(name)

    async def add_role(self, role: Role) -> None:
        role.id = uuid4()
        self.roles[role.name] = role

    async def add_account(self, account: Account) -> None:
        account.id = uuid4()
        self.accounts[account.email] = account

    async def add_account_role(self, link: AccountRole) -> None:
        role_name = next(role.name for role in self.roles.values() if role.id == link.role_id)
        self.account_roles.setdefault(link.account_id, set()).add(role_name)


class CountingUnitOfWork:
    def __init__(self, repository: BootstrapRepository, commits: list[bool]) -> None:
        self.repository = cast(AuthRepository, repository)
        self._commits = commits

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._commits.append(exc_type is None)


class RecordingPasswords:
    def __init__(self) -> None:
        self.hashed: list[str] = []

    async def hash(self, password: str) -> str:
        self.hashed.append(password)
        return "argon2id-hash"

    async def verify(self, password: str, password_hash: str | None) -> bool:
        return False


@pytest.mark.asyncio
async def test_bootstrap_creates_admin_once_without_rotating_password() -> None:
    repository = BootstrapRepository()
    commits: list[bool] = []
    passwords = RecordingPasswords()
    service = AdminBootstrapService(lambda: CountingUnitOfWork(repository, commits), passwords)

    first = await service.bootstrap(" Admin@Example.com ", "very long admin password")
    second = await service.bootstrap("admin@example.com", "different admin password")

    assert first is BootstrapOutcome.CREATED
    assert second is BootstrapOutcome.ALREADY_BOOTSTRAPPED
    assert passwords.hashed == ["very long admin password"]
    assert repository.account_roles[next(iter(repository.account_roles))] == {"admin"}
    assert commits == [True, True]


@pytest.mark.asyncio
async def test_bootstrap_rejects_existing_non_admin_account() -> None:
    repository = BootstrapRepository()
    existing = Account(email="person@example.com", password_hash="existing", display_name="Person")
    existing.id = uuid4()
    repository.accounts[existing.email] = existing
    commits: list[bool] = []
    service = AdminBootstrapService(
        lambda: CountingUnitOfWork(repository, commits), RecordingPasswords()
    )

    with pytest.raises(BootstrapConflictError):
        await service.bootstrap(existing.email, "very long admin password")

    assert existing.password_hash == "existing"
    assert commits == [False]


def test_bootstrap_inputs_reject_missing_and_empty_secret(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ADMIN_BOOTSTRAP_EMAIL"):
        required_environment({}, "ADMIN_BOOTSTRAP_EMAIL")
    secret = tmp_path / "secret"
    secret.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        read_password(str(secret))
    with pytest.raises(ValueError, match="missing"):
        read_password(str(secret) + "-missing")
