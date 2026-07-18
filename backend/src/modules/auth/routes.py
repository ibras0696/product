from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from common.schemas import ApiResponse
from config import get_settings
from modules.auth.dependencies import (
    SESSION_COOKIE_NAME,
    AuthRequestContext,
    get_auth_context,
    require_same_origin,
)
from modules.auth.schemas import CredentialsRequest, CurrentAccount

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={
        401: {"model": ApiResponse[None]},
        403: {"model": ApiResponse[None]},
        409: {"model": ApiResponse[None]},
        422: {"model": ApiResponse[None]},
        429: {"model": ApiResponse[None]},
    },
)
ContextDependency = Annotated[AuthRequestContext, Depends(get_auth_context)]
OriginDependency = Annotated[None, Depends(require_same_origin)]


@router.post(
    "/register",
    response_model=ApiResponse[CurrentAccount],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: CredentialsRequest,
    request: Request,
    response: Response,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[CurrentAccount]:
    result = await context.service.register(
        payload.email, payload.password, context.source, current_token=context.token
    )
    _set_session_cookie(response, result.session_token)
    return ApiResponse[CurrentAccount].success(result.account, request.state.request_id)


@router.post("/login", response_model=ApiResponse[CurrentAccount])
async def login(
    payload: CredentialsRequest,
    request: Request,
    response: Response,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[CurrentAccount]:
    result = await context.service.login(
        payload.email, payload.password, context.source, current_token=context.token
    )
    _set_session_cookie(response, result.session_token)
    return ApiResponse[CurrentAccount].success(result.account, request.state.request_id)


@router.get("/me", response_model=ApiResponse[CurrentAccount])
async def me(
    request: Request,
    context: ContextDependency,
) -> ApiResponse[CurrentAccount]:
    account = await context.service.current_account(context.token)
    return ApiResponse[CurrentAccount].success(account, request.state.request_id)


@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    request: Request,
    response: Response,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[None]:
    await context.service.logout(context.token)
    _clear_session_cookie(response)
    return ApiResponse[None].success(None, request.state.request_id)


@router.post("/logout-all", response_model=ApiResponse[None])
async def logout_all(
    request: Request,
    response: Response,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[None]:
    await context.service.logout_all(context.token)
    _clear_session_cookie(response)
    return ApiResponse[None].success(None, request.state.request_id)


def _set_session_cookie(response: Response, token: str) -> None:
    max_age = get_settings().auth_session_absolute_days * 24 * 60 * 60
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
