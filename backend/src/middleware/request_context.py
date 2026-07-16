from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint


async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["x-frame-options"] = "DENY"
    response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
    return response
