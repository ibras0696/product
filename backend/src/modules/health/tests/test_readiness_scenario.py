from modules.health.domain import ComponentStatus, ReadinessStatus, evaluate_readiness


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
