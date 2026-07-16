import hashlib
from collections.abc import Awaitable, Callable
from typing import Protocol, cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.exceptions import RateLimitedError, ServiceUnavailableError
from infrastructure.redis_client import create_redis_client

RedisFactory = Callable[[], Redis]


class AuthRateLimiterContract(Protocol):
    async def consume_login_attempt(self, source: str, account_key: str) -> None: ...

    async def clear_login_attempts(self, source: str, account_key: str) -> None: ...

    async def record_registration(self, source: str, account_key: str) -> None: ...


class RedisAuthRateLimiter:
    def __init__(
        self,
        attempts: int,
        window_seconds: int,
        redis_factory: RedisFactory = create_redis_client,
    ) -> None:
        self._attempts = attempts
        self._window_seconds = window_seconds
        self._redis_factory = redis_factory

    async def consume_login_attempt(self, source: str, account_key: str) -> None:
        await self._with_client(
            lambda client: self._increment_keys(client, self._login_keys(source, account_key))
        )

    async def clear_login_attempts(self, source: str, account_key: str) -> None:
        await self._with_client(
            lambda client: self._clear_keys(client, self._login_keys(source, account_key))
        )

    async def record_registration(self, source: str, account_key: str) -> None:
        keys = self._keys("register", source, account_key)
        await self._with_client(lambda client: self._increment_keys(client, keys))

    async def _increment_keys(self, client: Redis, keys: tuple[str, str]) -> None:
        pipeline = client.pipeline(transaction=True)
        for key in keys:
            pipeline.incr(key)
            pipeline.expire(key, self._window_seconds, nx=True)
        results = cast(list[int | bool], await pipeline.execute())
        counts = [int(results[index]) for index in range(0, len(results), 2)]
        if any(count > self._attempts for count in counts):
            await self._raise_limited(client, keys)

    @staticmethod
    async def _clear_keys(client: Redis, keys: tuple[str, str]) -> None:
        await client.delete(*keys)

    async def _raise_limited(self, client: Redis, keys: tuple[str, str]) -> None:
        retry_after = await client.ttl(keys[0])
        if retry_after <= 0:
            retry_after = self._window_seconds
        raise RateLimitedError(
            "Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    async def _with_client(self, action: Callable[[Redis], Awaitable[None]]) -> None:
        client = self._redis_factory()
        try:
            await action(client)
        except RedisError as exc:
            raise ServiceUnavailableError("Authentication is temporarily unavailable") from exc
        finally:
            await client.aclose()

    def _login_keys(self, source: str, account_key: str) -> tuple[str, str]:
        return self._keys("login", source, account_key)

    @staticmethod
    def _keys(scope: str, source: str, account_key: str) -> tuple[str, str]:
        source_hash = hashlib.sha256(f"{source}|{account_key}".encode()).hexdigest()
        account_hash = hashlib.sha256(account_key.encode()).hexdigest()
        prefix = "product:auth:v1"
        return (
            f"{prefix}:{scope}:source:{source_hash}",
            f"{prefix}:{scope}:account:{account_hash}",
        )
