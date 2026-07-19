from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.exc import IntegrityError

from modules.auth.domain import RoleName, normalize_email, validate_password
from modules.auth.exceptions import BootstrapConflictError
from modules.auth.models import Account, AccountRole, Role
from modules.auth.service import PasswordManagerContract, UoWFactory


class BootstrapOutcome(StrEnum):
    CREATED = "created"
    ALREADY_BOOTSTRAPPED = "already_bootstrapped"


@dataclass(frozen=True, slots=True)
class AdminBootstrapService:
    uow_factory: UoWFactory
    passwords: PasswordManagerContract

    async def bootstrap(self, email: str, password: str) -> BootstrapOutcome:
        normalized_email = normalize_email(email)
        validate_password(password)
        try:
            async with self.uow_factory() as uow:
                account = await uow.repository.find_account_by_email(normalized_email)
                if account is not None:
                    roles = await uow.repository.list_account_role_names(account.id)
                    if RoleName.ADMIN in roles:
                        return BootstrapOutcome.ALREADY_BOOTSTRAPPED
                    raise BootstrapConflictError(
                        "An account with the bootstrap email already exists"
                    )
                password_hash = await self.passwords.hash(password)
                role = await uow.repository.find_role_by_name(RoleName.ADMIN)
                if role is None:
                    role = Role(name=RoleName.ADMIN)
                    await uow.repository.add_role(role)
                account = Account(
                    email=normalized_email,
                    password_hash=password_hash,
                    display_name="Администратор",
                )
                await uow.repository.add_account(account)
                await uow.repository.add_account_role(
                    AccountRole(account_id=account.id, role_id=role.id)
                )
        except IntegrityError as exc:
            raise BootstrapConflictError("Admin bootstrap conflicted with existing data") from exc
        return BootstrapOutcome.CREATED
