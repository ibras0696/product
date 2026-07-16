from dataclasses import dataclass
from enum import StrEnum


class ReadinessStatus(StrEnum):
    READY = "ready"
    NOT_READY = "not_ready"


@dataclass(frozen=True, slots=True)
class ComponentStatus:
    name: str
    healthy: bool


def evaluate_readiness(components: tuple[ComponentStatus, ...]) -> ReadinessStatus:
    return (
        ReadinessStatus.READY
        if components and all(component.healthy for component in components)
        else ReadinessStatus.NOT_READY
    )
