from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.exceptions import register_exception_handlers
from common.metrics import create_metrics_app
from infrastructure.database import engine
from middleware.request_context import request_context
from router import api_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Product Hackathon API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    application.middleware("http")(request_context)
    application.include_router(api_router)
    application.mount("/metrics", create_metrics_app())
    register_exception_handlers(application)
    return application


app = create_app()
