from redis.exceptions import RedisError

from common.exceptions import ServiceUnavailableError
from infrastructure.redis_client import create_redis_client


class RedisCatalogInvalidation:
    async def invalidate_public_catalog(self) -> None:
        client = create_redis_client()
        try:
            await client.incr("product:catalog:v1:version")
            await client.publish("product:catalog:v1:invalidated", "updated")
        except RedisError as exc:
            raise ServiceUnavailableError("Catalog cache invalidation failed") from exc
        finally:
            await client.aclose()
