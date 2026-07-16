from types import TracebackType
from typing import Protocol, Self

from infrastructure.uow import UnitOfWork
from modules.auth.repository import AuthRepository


class AuthUnitOfWorkContract(Protocol):
    repository: AuthRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class AuthUnitOfWork(UnitOfWork):
    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self.repository = AuthRepository(self.session)
        return self
