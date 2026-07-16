from infrastructure.celery_app import celery


def worker_ping() -> str:
    return "pong"


celery.task(name="health.worker_ping")(worker_ping)
