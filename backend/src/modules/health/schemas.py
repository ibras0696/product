from typing import Literal

from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    name: str
    healthy: bool


class HealthStatus(BaseModel):
    status: Literal["alive", "ready", "not_ready"]
    components: list[ComponentHealth] = Field(default_factory=list)
