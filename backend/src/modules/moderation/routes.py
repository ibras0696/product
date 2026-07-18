from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from common.schemas import ApiResponse
from modules.auth.public import (
    AuthRequestContext,
    Permission,
    get_auth_context,
    require_same_origin,
)
from modules.moderation.domain import ModerationSubmission
from modules.moderation.repository import QueueFilters
from modules.moderation.schemas import (
    ClaimCommand,
    DecisionCommand,
    QueueItem,
    QueuePage,
    QueueQuery,
    SubmissionDetails,
)
from modules.moderation.service import ModerationService

router = APIRouter(
    prefix="/admin/submissions",
    tags=["moderation"],
    responses={
        401: {"model": ApiResponse[None]},
        403: {"model": ApiResponse[None]},
        404: {"model": ApiResponse[None]},
        409: {"model": ApiResponse[None]},
        422: {"model": ApiResponse[None]},
    },
)
ContextDependency = Annotated[AuthRequestContext, Depends(get_auth_context)]


def get_moderation_service() -> ModerationService:
    return ModerationService()


ServiceDependency = Annotated[ModerationService, Depends(get_moderation_service)]


@router.get("", response_model=ApiResponse[QueuePage])
async def queue(
    request: Request,
    context: ContextDependency,
    service: ServiceDependency,
    query: Annotated[QueueQuery, Query()],
) -> ApiResponse[QueuePage]:
    await context.service.require_permission(context.token, Permission.MODERATION_READ)
    items, total = await service.queue(
        QueueFilters(
            query.status,
            query.type,
            query.settlement_id,
            query.created_from,
            query.created_to,
        ),
        query.limit,
        query.offset,
    )
    page = QueuePage(
        items=[_queue_item(item) for item in items],
        limit=query.limit,
        offset=query.offset,
        total=total,
    )
    return ApiResponse[QueuePage].success(page, request.state.request_id)


@router.get("/{submission_id}", response_model=ApiResponse[SubmissionDetails])
async def details(
    submission_id: UUID,
    request: Request,
    context: ContextDependency,
    service: ServiceDependency,
) -> ApiResponse[SubmissionDetails]:
    await context.service.require_permission(context.token, Permission.MODERATION_READ)
    result = await service.details(submission_id)
    return ApiResponse[SubmissionDetails].success(_details(result), request.state.request_id)


@router.post(
    "/{submission_id}/claim",
    response_model=ApiResponse[SubmissionDetails],
    dependencies=[Depends(require_same_origin)],
)
async def claim(
    submission_id: UUID,
    payload: ClaimCommand,
    request: Request,
    context: ContextDependency,
    service: ServiceDependency,
) -> ApiResponse[SubmissionDetails]:
    actor = await context.service.require_permission(context.token, Permission.MODERATION_CLAIM)
    result = await service.claim(submission_id, actor.id, payload.expected_version)
    return ApiResponse[SubmissionDetails].success(_details(result), request.state.request_id)


@router.post(
    "/{submission_id}/reject",
    response_model=ApiResponse[SubmissionDetails],
    dependencies=[Depends(require_same_origin)],
)
async def reject(
    submission_id: UUID,
    payload: DecisionCommand,
    request: Request,
    context: ContextDependency,
    service: ServiceDependency,
) -> ApiResponse[SubmissionDetails]:
    actor = await context.service.require_permission(context.token, Permission.MODERATION_DECIDE)
    result = await service.reject(
        submission_id, actor.id, payload.expected_version, payload.comment
    )
    return ApiResponse[SubmissionDetails].success(_details(result), request.state.request_id)


@router.post(
    "/{submission_id}/request-revision",
    response_model=ApiResponse[SubmissionDetails],
    dependencies=[Depends(require_same_origin)],
)
async def request_revision(
    submission_id: UUID,
    payload: DecisionCommand,
    request: Request,
    context: ContextDependency,
    service: ServiceDependency,
) -> ApiResponse[SubmissionDetails]:
    actor = await context.service.require_permission(context.token, Permission.MODERATION_DECIDE)
    result = await service.request_revision(
        submission_id, actor.id, payload.expected_version, payload.comment
    )
    return ApiResponse[SubmissionDetails].success(_details(result), request.state.request_id)


def _queue_item(item: ModerationSubmission) -> QueueItem:
    return QueueItem(
        id=item.id,
        type=item.type,
        status=item.status,
        version=item.version,
        title=item.title,
        settlement_id=item.settlement_id,
        submitted_at=item.submitted_at,
        created_at=item.created_at,
        claimed_by=item.claimed_by,
    )


def _details(item: ModerationSubmission) -> SubmissionDetails:
    return SubmissionDetails(
        **_queue_item(item).model_dump(),
        related_entity_id=item.related_entity_id,
        description=item.description,
        source_description=item.source_description,
        author_name=item.author_name,
        contact=item.contact,
        consent=item.consent,
        updated_at=item.updated_at,
    )
