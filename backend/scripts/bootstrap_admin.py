"""Idempotent release command for the first administrative account."""

import asyncio
import os

from modules.auth.bootstrap import AdminBootstrapService
from modules.auth.bootstrap_inputs import read_password, required_environment
from modules.auth.passwords import Argon2idPasswordManager
from modules.auth.uow import AuthUnitOfWork


async def _run() -> None:
    email = required_environment(os.environ, "ADMIN_BOOTSTRAP_EMAIL")
    password_file = required_environment(os.environ, "ADMIN_BOOTSTRAP_PASSWORD_FILE")
    password = read_password(password_file)
    service = AdminBootstrapService(AuthUnitOfWork, Argon2idPasswordManager())
    outcome = await service.bootstrap(email, password)
    print(f"Admin bootstrap: {outcome.value}")


if __name__ == "__main__":
    asyncio.run(_run())
