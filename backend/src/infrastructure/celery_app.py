from celery import Celery

from config import get_settings

settings = get_settings()
celery = Celery(
    "product_hackathon",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["modules.health.tasks"],
)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
)
