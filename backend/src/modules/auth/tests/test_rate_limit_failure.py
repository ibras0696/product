from typing import NoReturn, cast

import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.exceptions import ServiceUnavailableError
from modules.auth.rate_limit import RedisAuthRateLimiter


class FailingRedis:
    def __init__(self) -> None:
        self.closed = False

    def pipeline(self, transaction: bool = True) -> NoReturn:
        raise RedisError("redis unavailable")

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_redis_failure_closes_the_client_and_fails_authentication_safely() -> None:
    client = FailingRedis()
    limiter = RedisAuthRateLimiter(
        attempts=5,
        window_seconds=900,
        redis_factory=lambda: cast(Redis, client),
    )

    with pytest.raises(ServiceUnavailableError):
        await limiter.consume_login_attempt("source", "person@example.com")
    assert client.closed
