import hashlib
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.exceptions import RateLimitedError, ServiceUnavailableError
from infrastructure.redis_client import create_redis_client

DRAFT_COOKIE_PREFIX = "__Host-submission_draft_"
_TOKEN_BYTES = 32


@dataclass(frozen=True, slots=True)
class SubmissionCapabilities:
    owner_secret: str
    tracking_code: str

    @property
    def cookie_value(self) -> str:
        return f"{self.owner_secret}.{self.tracking_code}"


class CapabilityIssuer:
    """Issues independent 256-bit secrets and stores only domain-separated hashes."""

    @staticmethod
    def issue() -> SubmissionCapabilities:
        return SubmissionCapabilities(
            owner_secret=secrets.token_urlsafe(_TOKEN_BYTES),
            tracking_code=secrets.token_urlsafe(_TOKEN_BYTES),
        )

    @staticmethod
    def parse_cookie(value: str | None) -> SubmissionCapabilities | None:
        if value is None:
            return None
        parts = value.split(".")
        if len(parts) != 2 or not all(len(part) >= 40 for part in parts):
            return None
        return SubmissionCapabilities(owner_secret=parts[0], tracking_code=parts[1])

    @staticmethod
    def owner_hash(secret: str) -> str:
        return _secret_hash("owner", secret)

    @staticmethod
    def tracking_hash(secret: str) -> str:
        return _secret_hash("tracking", secret)


def draft_cookie_name(submission_id: object) -> str:
    return f"{DRAFT_COOKIE_PREFIX}{submission_id}"


def secrets_match(candidate_hash: str, stored_hash: str) -> bool:
    return secrets.compare_digest(candidate_hash, stored_hash)


def _secret_hash(purpose: str, secret: str) -> str:
    return hashlib.sha256(f"submission:v1:{purpose}:{secret}".encode()).hexdigest()


class SubmissionRateLimiter(Protocol):
    async def consume_create(self, source: str) -> None: ...

    async def consume_status(self, source: str) -> None: ...


RedisFactory = Callable[[], Redis]


class RedisSubmissionRateLimiter:
    def __init__(
        self,
        attempts: int = 20,
        window_seconds: int = 900,
        redis_factory: RedisFactory = create_redis_client,
    ) -> None:
        self._attempts = attempts
        self._window_seconds = window_seconds
        self._redis_factory = redis_factory

    async def consume_create(self, source: str) -> None:
        await self._consume("create", source)

    async def consume_status(self, source: str) -> None:
        await self._consume("status", source)

    async def _consume(self, scope: str, source: str) -> None:
        source_hash = hashlib.sha256(source.encode()).hexdigest()
        key = f"product:submission:v1:{scope}:{source_hash}"
        await self._with_client(lambda client: self._increment(client, key))

    async def _increment(self, client: Redis, key: str) -> None:
        pipeline = client.pipeline(transaction=True)
        pipeline.incr(key)
        pipeline.expire(key, self._window_seconds, nx=True)
        results = cast(list[int | bool], await pipeline.execute())
        if int(results[0]) <= self._attempts:
            return
        retry_after = await client.ttl(key)
        raise RateLimitedError(
            "Too many submission requests. Try again later.",
            headers={"Retry-After": str(max(retry_after, 1))},
        )

    async def _with_client(self, action: Callable[[Redis], Awaitable[None]]) -> None:
        client = self._redis_factory()
        try:
            await action(client)
        except RedisError as exc:
            raise ServiceUnavailableError("Submission service is temporarily unavailable") from exc
        finally:
            await client.aclose()
