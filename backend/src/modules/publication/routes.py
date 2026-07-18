from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from common.schemas import ApiResponse
from modules.auth.public import (
    AuthRequestContext,
    Permission,
    get_auth_context,
    require_same_origin,
)
from modules.moderation.contracts import PublishCommand
from modules.publication.invalidation import RedisCatalogInvalidation
from modules.publication.schemas import PublishResult
from modules.publication.service import PublicationService
from modules.publication.sql_uow import SqlPublicationUnitOfWork

router = APIRouter(prefix="/admin/submissions", tags=["moderation-publication"])
Context = Annotated[AuthRequestContext, Depends(get_auth_context)]


def get_publication_service() -> PublicationService:
    return PublicationService(SqlPublicationUnitOfWork, RedisCatalogInvalidation())


Service = Annotated[PublicationService, Depends(get_publication_service)]


@router.post(
    "/{submission_id}/publish",
    response_model=ApiResponse[PublishResult],
    dependencies=[Depends(require_same_origin)],
)
async def publish_submission(
    submission_id: UUID,
    payload: PublishCommand,
    request: Request,
    context: Context,
    service: Service,
) -> ApiResponse[PublishResult]:
    actor = await context.service.require_permission(context.token, Permission.MODERATION_PUBLISH)
    result = await service.publish(submission_id, actor.id, payload)
    return ApiResponse[PublishResult].success(result, request.state.request_id)
