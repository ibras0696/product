from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import ApiResponse
from infrastructure.database import get_session
from modules.audit.repository import SqlAuditRepository
from modules.audit.schemas import AuditListRequest, AuditPage
from modules.auth.public import AuthRequestContext, Permission, get_auth_context

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])
Context = Annotated[AuthRequestContext, Depends(get_auth_context)]
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=ApiResponse[AuditPage])
async def list_audit(
    request: Request,
    context: Context,
    session: Session,
    filters: Annotated[AuditListRequest, Query()],
) -> ApiResponse[AuditPage]:
    await context.service.require_permission(context.token, Permission.AUDIT_READ)
    page = await SqlAuditRepository(session).list(filters)
    return ApiResponse[AuditPage].success(page, request.state.request_id)
