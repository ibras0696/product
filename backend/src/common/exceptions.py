from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from common.schemas import ApiError, ApiResponse, ResponseMeta


class ApplicationError(Exception):
    code = "application_error"
    status_code = 500

    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


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


async def application_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ApplicationError):
        raise exc
    payload = ApiResponse[object](
        ok=False,
        error=ApiError(code=exc.code, message=exc.message, details=exc.details),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error_handler)
