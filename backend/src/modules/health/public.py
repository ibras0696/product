"""Public transport contract owned by the health module."""

from modules.health.routes import router as health_router

__all__ = ["health_router"]
