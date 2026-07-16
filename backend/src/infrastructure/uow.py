from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.database import session_factory


class UnitOfWork:
    """Owns exactly one transaction for one application use-case."""

    def __init__(self, factory: async_sessionmaker[AsyncSession] = session_factory) -> None:
        self._factory = factory
        self.session: AsyncSession

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
