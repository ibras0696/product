from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SessionState:
    idle_expires_at: datetime
    absolute_expires_at: datetime
    revoked_at: datetime | None
    account_active: bool


def evaluate_session(state: SessionState, now: datetime) -> bool:
    return (
        state.revoked_at is None
        and state.account_active
        and now < state.idle_expires_at
        and now < state.absolute_expires_at
    )
