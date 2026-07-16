import asyncio

from celery import Celery

from infrastructure.celery_app import celery


class BrokerHealthProbe:
    def __init__(self, app: Celery = celery) -> None:
        self._app = app

    async def ping(self) -> None:
        await asyncio.to_thread(self._ping_sync)

    def _ping_sync(self) -> None:
        connection = self._app.connection_for_read()
        try:
            connection.ensure_connection(max_retries=1, timeout=2)
        finally:
            connection.release()
