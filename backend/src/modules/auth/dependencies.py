from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Cookie, Depends, Request

from common.exceptions import ForbiddenError
from config import get_settings
from modules.auth.passwords import Argon2idPasswordManager
from modules.auth.rate_limit import RedisAuthRateLimiter
from modules.auth.service import AuthService, AuthSessionPolicy
from modules.auth.uow import AuthUnitOfWork

SESSION_COOKIE_NAME = "__Host-product_session"


@lru_cache
def get_password_manager() -> Argon2idPasswordManager:
    return Argon2idPasswordManager()


def get_auth_service() -> AuthService:
    settings = get_settings()
    return AuthService(
        uow_factory=AuthUnitOfWork,
        passwords=get_password_manager(),
        rate_limiter=RedisAuthRateLimiter(
            attempts=settings.auth_rate_limit_attempts,
            window_seconds=settings.auth_rate_limit_window_seconds,
        ),
        session_policy=AuthSessionPolicy(
            idle_days=settings.auth_session_idle_days,
            absolute_days=settings.auth_session_absolute_days,
        ),
    )


def get_session_token(
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> str | None:
    return token


@dataclass(frozen=True, slots=True)
class AuthRequestContext:
    service: AuthService
    token: str | None
    source: str


def get_auth_context(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    token: Annotated[str | None, Depends(get_session_token)],
) -> AuthRequestContext:
    return AuthRequestContext(service=service, token=token, source=request_source(request))


def require_same_origin(
    request: Request,
    token: Annotated[str | None, Depends(get_session_token)],
) -> None:
    if token is None:
        return
    origin = request.headers.get("origin")
    if origin is None or _origin(origin) != _origin(str(request.base_url)):
        raise ForbiddenError("Request origin is not allowed")


def request_source(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _origin(value: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(value)
    return parsed.scheme, parsed.hostname or "", parsed.port
