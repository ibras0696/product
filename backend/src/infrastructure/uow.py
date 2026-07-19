from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database import session_factory


class SessionFactory(Protocol):
    def __call__(self) -> AsyncSession: ...


class UnitOfWork:
    """Owns exactly one transaction for one application use-case."""

    def __init__(self, factory: SessionFactory = session_factory) -> None:
        self._factory = factory
        self.session: AsyncSession
        self._after_commit: list[Callable[[], Awaitable[None]]] = []

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._factory()
        self._after_commit = []
        return self

    def after_commit(self, callback: Callable[[], Awaitable[None]]) -> None:
        self._after_commit.append(callback)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                await self.session.commit()
                for callback in self._after_commit:
                    await callback()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
