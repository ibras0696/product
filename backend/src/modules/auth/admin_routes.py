from typing import Annotated

from fastapi import APIRouter, Depends, Request

from common.schemas import ApiResponse
from modules.auth.dependencies import AuthRequestContext, get_auth_context
from modules.auth.schemas import AdminAccount

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={
        401: {"model": ApiResponse[None]},
        403: {"model": ApiResponse[None]},
        422: {"model": ApiResponse[None]},
    },
)
ContextDependency = Annotated[AuthRequestContext, Depends(get_auth_context)]


@router.get("/me", response_model=ApiResponse[AdminAccount])
async def me(request: Request, context: ContextDependency) -> ApiResponse[AdminAccount]:
    account = await context.service.admin_account(context.token)
    return ApiResponse[AdminAccount].success(account, request.state.request_id)
