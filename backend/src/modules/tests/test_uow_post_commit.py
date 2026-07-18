import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.uow import UnitOfWork


class FakeSession(AsyncSession):
    def __init__(self, *, fail_commit: bool = False) -> None:
        self.fail_commit = fail_commit
        self.committed = False
        self.rolled_back = False
        self.closed = False

    async def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("commit failed")
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def close(self) -> None:
        self.closed = True


class FakeFactory:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    def __call__(self) -> FakeSession:
        return self.session


async def test_hook_runs_only_after_successful_commit() -> None:
    session = FakeSession()
    events: list[str] = []
    uow = UnitOfWork(FakeFactory(session))

    async with uow:
        uow.after_commit(lambda: _record(events, "invalidated"))
        assert events == []

    assert session.committed is True
    assert events == ["invalidated"]
    assert session.closed is True


async def test_commit_failure_emits_nothing() -> None:
    session = FakeSession(fail_commit=True)
    events: list[str] = []
    uow = UnitOfWork(FakeFactory(session))

    with pytest.raises(RuntimeError, match="commit failed"):
        async with uow:
            uow.after_commit(lambda: _record(events, "invalidated"))

    assert events == []
    assert session.closed is True


async def test_hook_failure_does_not_undo_committed_truth() -> None:
    session = FakeSession()
    uow = UnitOfWork(FakeFactory(session))

    with pytest.raises(RuntimeError, match="cache unavailable"):
        async with uow:
            uow.after_commit(_failing_hook)

    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True


async def _record(events: list[str], value: str) -> None:
    events.append(value)


async def _failing_hook() -> None:
    raise RuntimeError("cache unavailable")
