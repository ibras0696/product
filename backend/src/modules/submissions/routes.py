from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from common.exceptions import ForbiddenError
from common.schemas import ApiResponse
from modules.submissions.capabilities import (
    CapabilityIssuer,
    RedisSubmissionRateLimiter,
    draft_cookie_name,
)
from modules.submissions.schemas import (
    SubmissionCreate,
    SubmissionDraft,
    SubmissionPatch,
    SubmissionStatusRequest,
    SubmissionStatusView,
    SubmissionSubmit,
)
from modules.submissions.service import SubmissionService, SubmissionUnitOfWork

router = APIRouter(
    prefix="/submissions",
    tags=["submissions"],
    responses={
        400: {"model": ApiResponse[None]},
        403: {"model": ApiResponse[None]},
        404: {"model": ApiResponse[None]},
        409: {"model": ApiResponse[None]},
        422: {"model": ApiResponse[None]},
        429: {"model": ApiResponse[None]},
        503: {"model": ApiResponse[None]},
    },
)


def get_submission_service() -> SubmissionService:
    return SubmissionService(SubmissionUnitOfWork, CapabilityIssuer(), RedisSubmissionRateLimiter())


ServiceDependency = Annotated[SubmissionService, Depends(get_submission_service)]


@router.post("", response_model=ApiResponse[SubmissionDraft], status_code=status.HTTP_201_CREATED)
async def create_submission(
    payload: SubmissionCreate,
    request: Request,
    response: Response,
    service: ServiceDependency,
) -> ApiResponse[SubmissionDraft]:
    result, cookie_value = await service.create(payload, _request_source(request))
    response.set_cookie(
        draft_cookie_name(result.id),
        cookie_value,
        max_age=30 * 24 * 60 * 60,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return ApiResponse[SubmissionDraft].success(result, request.state.request_id)


@router.patch("/{submission_id}", response_model=ApiResponse[SubmissionDraft])
async def patch_submission(
    submission_id: UUID,
    payload: SubmissionPatch,
    request: Request,
    service: ServiceDependency,
) -> ApiResponse[SubmissionDraft]:
    _require_same_origin(request)
    result = await service.patch(
        submission_id, payload, request.cookies.get(draft_cookie_name(submission_id))
    )
    return ApiResponse[SubmissionDraft].success(result, request.state.request_id)


@router.post("/{submission_id}/submit", response_model=ApiResponse[SubmissionStatusView])
async def submit_submission(
    submission_id: UUID,
    payload: SubmissionSubmit,
    request: Request,
    service: ServiceDependency,
) -> ApiResponse[SubmissionStatusView]:
    _require_same_origin(request)
    result = await service.submit(
        submission_id, payload, request.cookies.get(draft_cookie_name(submission_id))
    )
    return ApiResponse[SubmissionStatusView].success(result, request.state.request_id)


@router.post("/status", response_model=ApiResponse[SubmissionStatusView])
async def submission_status(
    payload: SubmissionStatusRequest,
    request: Request,
    response: Response,
    service: ServiceDependency,
) -> ApiResponse[SubmissionStatusView]:
    result = await service.status(payload.tracking_code, _request_source(request))
    response.headers["Cache-Control"] = "no-store"
    return ApiResponse[SubmissionStatusView].success(result, request.state.request_id)


def _request_source(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None or _origin(origin) != _origin(str(request.base_url)):
        raise ForbiddenError("Request origin is not allowed")


def _origin(value: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(value)
    return parsed.scheme, parsed.hostname or "", parsed.port
