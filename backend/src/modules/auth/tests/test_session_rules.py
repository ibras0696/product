from dataclasses import replace
from datetime import UTC, datetime, timedelta

from modules.auth.domain import SessionState, evaluate_session, normalize_email, validate_password
from modules.auth.domain.credentials import PasswordPolicyViolation


def test_credentials_and_session_invariants_form_one_domain_scenario() -> None:
    now = datetime(2026, 7, 17, tzinfo=UTC)
    active = SessionState(
        idle_expires_at=now + timedelta(days=1),
        absolute_expires_at=now + timedelta(days=10),
        revoked_at=None,
        account_active=True,
    )

    assert normalize_email("  Person@Example.COM ") == "person@example.com"
    validate_password("длинный пароль пользователя")
    assert evaluate_session(active, now)
    assert not evaluate_session(active, active.idle_expires_at)
    assert not evaluate_session(replace(active, revoked_at=now), now)

    try:
        validate_password("short")
    except PasswordPolicyViolation:
        pass
    else:
        raise AssertionError("Short passwords must be rejected")
