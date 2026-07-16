from prometheus_client import make_asgi_app
from starlette.types import ASGIApp


def create_metrics_app() -> ASGIApp:
    return make_asgi_app()
