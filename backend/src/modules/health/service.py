import asyncio
from collections.abc import Awaitable, Callable

from modules.health.domain import ComponentStatus, evaluate_readiness
from modules.health.repository import HealthRepository
from modules.health.schemas import ComponentHealth, HealthStatus

Probe = Callable[[], Awaitable[None]]


class HealthService:
    def __init__(
        self,
        repository: HealthRepository,
        redis_probe: Probe,
        broker_probe: Probe,
    ) -> None:
        self._repository = repository
        self._redis_probe = redis_probe
        self._broker_probe = broker_probe

    async def readiness(self) -> HealthStatus:
        components = await asyncio.gather(
            self._check("postgres", self._repository.ping),
            self._check("redis", self._redis_probe),
            self._check("rabbitmq", self._broker_probe),
        )
        status = evaluate_readiness(components)
        return HealthStatus(
            status=status.value,
            components=[
                ComponentHealth(name=component.name, healthy=component.healthy)
                for component in components
            ],
        )

    @staticmethod
    async def _check(name: str, probe: Probe) -> ComponentStatus:
        try:
            await asyncio.wait_for(probe(), timeout=3)
        except Exception:
            return ComponentStatus(name=name, healthy=False)
        return ComponentStatus(name=name, healthy=True)
