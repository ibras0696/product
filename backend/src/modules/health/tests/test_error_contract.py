import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.exceptions import (
    ApplicationError,
    ConflictError,
    ForbiddenError,
    RateLimitedError,
    ServiceUnavailableError,
    UnauthorizedError,
    register_exception_handlers,
)
from middleware.request_context import request_context


def _error_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(request_context)
    register_exception_handlers(app)

    @app.get("/validated")
    async def validated(limit: int) -> dict[str, int]:
        return {"limit": limit}

    return app


@pytest.mark.parametrize(
    "case",
    [
        ("/unauthorized", UnauthorizedError("Login required"), 401, "unauthorized", None),
        ("/forbidden", ForbiddenError("Denied"), 403, "forbidden", None),
        ("/conflict", ConflictError("Version conflict"), 409, "conflict", None),
        (
            "/limited",
            RateLimitedError("Try later", headers={"Retry-After": "60"}),
            429,
            "rate_limited",
            {"retry-after": "60"},
        ),
        (
            "/unavailable",
            ServiceUnavailableError("Dependency unavailable"),
            503,
            "service_unavailable",
            None,
        ),
    ],
)
def test_typed_errors_keep_status_code_headers_and_correlation(
    case: tuple[str, ApplicationError, int, str, dict[str, str] | None],
) -> None:
    path, error, status, code, headers = case
    app = _error_app()

    async def fail() -> None:
        raise error

    app.add_api_route(path, fail, methods=["GET"])
    response = TestClient(app).get(path, headers={"X-Request-ID": "museum-request-42"})

    assert response.status_code == status
    assert response.headers["x-request-id"] == "museum-request-42"
    if headers:
        assert all(response.headers[name] == value for name, value in headers.items())
    assert response.json() == {
        "ok": False,
        "data": None,
        "error": {"code": code, "message": error.message, "details": None},
        "meta": {"request_id": "museum-request-42"},
    }


def test_framework_errors_use_the_safe_envelope() -> None:
    client = TestClient(_error_app())

    missing = client.get("/missing")
    invalid = client.get("/validated", params={"limit": "many"})

    assert missing.status_code == 404
    assert missing.json()["error"] == {
        "code": "not_found",
        "message": "Resource not found",
        "details": None,
    }
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    fields = invalid.json()["error"]["details"]["fields"]
    assert len(fields) == 1
    assert fields[0]["path"] == "query.limit"
    assert fields[0]["message"]


def test_unexpected_errors_do_not_expose_internal_details() -> None:
    app = _error_app()

    async def crash() -> None:
        raise RuntimeError("database password is secret")

    app.add_api_route("/crash", crash, methods=["GET"])
    response = TestClient(app, raise_server_exceptions=False).get("/crash")

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "internal_error",
        "message": "An unexpected error occurred",
        "details": None,
    }
    assert "secret" not in response.text
    assert response.json()["meta"]["request_id"] == response.headers["x-request-id"]
