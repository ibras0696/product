from redis.asyncio import Redis

from config import get_settings


def create_redis_client() -> Redis:
    return Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )


class RedisHealthProbe:
    async def ping(self) -> None:
        client = create_redis_client()
        try:
            await client.ping()
        finally:
            await client.aclose()
