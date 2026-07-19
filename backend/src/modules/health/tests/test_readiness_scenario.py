from fastapi.testclient import TestClient

from main import app
from modules.health.domain import ComponentStatus, ReadinessStatus, evaluate_readiness
from modules.health.routes import get_health_service
from modules.health.schemas import ComponentHealth, HealthStatus


def test_readiness_reflects_the_whole_dependency_scenario() -> None:
    healthy = (
        ComponentStatus("postgres", True),
        ComponentStatus("redis", True),
        ComponentStatus("rabbitmq", True),
    )
    degraded = (*healthy[:2], ComponentStatus("rabbitmq", False))

    assert evaluate_readiness(healthy) is ReadinessStatus.READY
    assert evaluate_readiness(degraded) is ReadinessStatus.NOT_READY
    assert evaluate_readiness(()) is ReadinessStatus.NOT_READY


class DegradedHealthService:
    async def readiness(self) -> HealthStatus:
        return HealthStatus(
            status="not_ready",
            components=[
                ComponentHealth(name="postgres", healthy=True),
                ComponentHealth(name="redis", healthy=False),
                ComponentHealth(name="rabbitmq", healthy=True),
            ],
        )


def test_readiness_returns_503_when_a_required_dependency_is_down() -> None:
    app.dependency_overrides[get_health_service] = DegradedHealthService
    try:
        response = TestClient(app).get("/api/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "service_unavailable",
        "message": "Required dependencies are unavailable",
        "details": {
            "components": [
                {"name": "postgres", "healthy": True},
                {"name": "redis", "healthy": False},
                {"name": "rabbitmq", "healthy": True},
            ]
        },
    }
