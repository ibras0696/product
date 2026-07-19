import logging
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.schemas import ApiError, ApiResponse, ResponseMeta


class ApplicationError(Exception):
    code = "application_error"
    status_code = 500

    def __init__(
        self,
        message: str,
        details: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        self.headers = headers


class BadRequestError(ApplicationError):
    code = "bad_request"
    status_code = 400


class UnauthorizedError(ApplicationError):
    code = "unauthorized"
    status_code = 401


class ForbiddenError(ApplicationError):
    code = "forbidden"
    status_code = 403


class NotFoundError(ApplicationError):
    code = "not_found"
    status_code = 404


class ConflictError(ApplicationError):
    code = "conflict"
    status_code = 409


class RateLimitedError(ApplicationError):
    code = "rate_limited"
    status_code = 429


class ServiceUnavailableError(ApplicationError):
    code = "service_unavailable"
    status_code = 503


_HTTP_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    503: "service_unavailable",
}

_HTTP_ERROR_MESSAGES = {
    401: "Authentication is required",
    403: "Permission denied",
    404: "Resource not found",
    429: "Too many requests",
    503: "Service temporarily unavailable",
}


async def application_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ApplicationError):
        raise exc
    payload = ApiResponse[object](
        ok=False,
        error=ApiError(code=exc.code, message=exc.message, details=exc.details),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(mode="json"),
        headers=_response_headers(request, exc.headers),
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    fields = [
        {"path": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
        for error in exc.errors()
    ]
    payload = _failure_payload(request, "validation_error", "Request validation failed", fields)
    return JSONResponse(
        status_code=422,
        content=payload.model_dump(mode="json"),
        headers=_response_headers(request),
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    code = _HTTP_ERROR_CODES.get(exc.status_code, "http_error")
    message = _HTTP_ERROR_MESSAGES.get(exc.status_code, "Request could not be completed")
    payload = _failure_payload(request, code, message)
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(mode="json"),
        headers=_response_headers(request, exc.headers),
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled request failure", exc_info=exc)
    payload = _failure_payload(request, "internal_error", "An unexpected error occurred")
    return JSONResponse(
        status_code=500,
        content=payload.model_dump(mode="json"),
        headers=_response_headers(request),
    )


def _response_headers(request: Request, headers: Mapping[str, str] | None = None) -> dict[str, str]:
    response_headers = dict(headers or {})
    response_headers["X-Request-ID"] = request.state.request_id
    return response_headers


def _failure_payload(
    request: Request,
    code: str,
    message: str,
    fields: list[dict[str, object]] | None = None,
) -> ApiResponse[object]:
    details: dict[str, object] | None = {"fields": fields} if fields is not None else None
    return ApiResponse[object](
        ok=False,
        error=ApiError(code=code, message=message, details=details),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
