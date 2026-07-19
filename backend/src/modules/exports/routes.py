from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import ApplicationError
from infrastructure.database import get_session
from modules.auth.public import AuthRequestContext, Permission, get_auth_context
from modules.exports.repository import SqlCatalogExportRepository
from modules.exports.service import (
    CatalogExportService,
    ExportFormat,
    ExportStatus,
    ExportTooLargeError,
)

router = APIRouter(prefix="/admin/catalog", tags=["admin-catalog-export"])

AuthContext = Annotated[AuthRequestContext, Depends(get_auth_context)]
Session = Annotated[AsyncSession, Depends(get_session)]


class ExportTooLargeApplicationError(ApplicationError):
    code = "export_too_large"
    status_code = 413


@router.get("/export", response_class=StreamingResponse)
async def export_catalog(
    format: ExportFormat,
    status: ExportStatus,
    request: Request,
    context: AuthContext,
    session: Session,
) -> StreamingResponse:
    await context.service.require_permission(context.token, Permission.CATALOG_EXPORT)
    service = CatalogExportService(SqlCatalogExportRepository(session))
    try:
        export = await service.export(
            format=format,
            status=status,
            permission_granted=True,
            is_disconnected=request.is_disconnected,
        )
    except ExportTooLargeError as exc:
        raise ExportTooLargeApplicationError("Export exceeds the configured limit") from exc
    return StreamingResponse(
        export.body,
        media_type=export.media_type,
        headers={"Content-Disposition": f'attachment; filename="{export.filename}"'},
    )
