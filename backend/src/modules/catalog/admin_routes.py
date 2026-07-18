from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from common.schemas import ApiResponse
from modules.auth.public import (
    AuthRequestContext,
    Permission,
    get_auth_context,
    require_same_origin,
)
from modules.catalog.admin_schemas import (
    AdminEntity,
    AdminEntityCreate,
    AdminEntityListRequest,
    AdminEntityPage,
    AdminEntityPatch,
    AdminRelation,
    AdminRelationCreate,
    AdminRelationListRequest,
    AdminRelationPage,
    AdminRelationPatch,
    AdminSource,
    AdminSourceCreate,
    AdminSourceListRequest,
    AdminSourcePage,
    AdminSourcePatch,
    ArchiveRequest,
)
from modules.catalog.admin_service import (
    AdminCatalogService,
    AdminCatalogUoW,
)

router = APIRouter(
    prefix="/admin/catalog",
    tags=["admin-catalog"],
    responses={
        400: {"model": ApiResponse[None]},
        401: {"model": ApiResponse[None]},
        403: {"model": ApiResponse[None]},
        404: {"model": ApiResponse[None]},
        409: {"model": ApiResponse[None]},
        422: {"model": ApiResponse[None]},
        503: {"model": ApiResponse[None]},
    },
)


def get_admin_catalog_service() -> AdminCatalogService:
    return AdminCatalogService(AdminCatalogUoW)


ServiceDependency = Annotated[AdminCatalogService, Depends(get_admin_catalog_service)]
ContextDependency = Annotated[AuthRequestContext, Depends(get_auth_context)]
OriginDependency = Annotated[None, Depends(require_same_origin)]


@router.get("/entities", response_model=ApiResponse[AdminEntityPage])
async def list_entities(
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    filters: Annotated[AdminEntityListRequest, Query()],
) -> ApiResponse[AdminEntityPage]:
    await context.service.require_permission(context.token, Permission.CATALOG_READ)
    result = await service.list_entities(
        query=filters.query,
        entity_type=filters.type,
        status=filters.status,
        limit=filters.limit,
        offset=filters.offset,
    )
    return ApiResponse[AdminEntityPage].success(result, request.state.request_id)


@router.post(
    "/entities", response_model=ApiResponse[AdminEntity], status_code=status.HTTP_201_CREATED
)
async def create_entity(
    payload: AdminEntityCreate,
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[AdminEntity]:
    actor = await context.service.require_permission(context.token, Permission.CATALOG_WRITE)
    result = await service.create_entity(payload, actor.id)
    return ApiResponse[AdminEntity].success(result, request.state.request_id)


@router.patch("/entities/{entity_id}", response_model=ApiResponse[AdminEntity])
async def update_entity(
    entity_id: UUID,
    payload: AdminEntityPatch,
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[AdminEntity]:
    actor = await context.service.require_permission(context.token, Permission.CATALOG_WRITE)
    result = await service.update_entity(entity_id, payload, actor.id)
    return ApiResponse[AdminEntity].success(result, request.state.request_id)


@router.delete("/entities/{entity_id}", response_model=ApiResponse[None])
async def archive_entity(
    entity_id: UUID,
    payload: ArchiveRequest,
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[None]:
    actor = await context.service.require_permission(context.token, Permission.CATALOG_WRITE)
    await service.archive_entity(entity_id, payload.expected_version, actor.id)
    return ApiResponse[None].success(None, request.state.request_id)


@router.get("/relations", response_model=ApiResponse[AdminRelationPage])
async def list_relations(
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    filters: Annotated[AdminRelationListRequest, Query()],
) -> ApiResponse[AdminRelationPage]:
    await context.service.require_permission(context.token, Permission.CATALOG_READ)
    result = await service.list_relations(
        entity_id=filters.entity_id,
        relation_type=filters.type,
        limit=filters.limit,
        offset=filters.offset,
    )
    return ApiResponse[AdminRelationPage].success(result, request.state.request_id)


@router.post(
    "/relations", response_model=ApiResponse[AdminRelation], status_code=status.HTTP_201_CREATED
)
async def create_relation(
    payload: AdminRelationCreate,
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[AdminRelation]:
    actor = await context.service.require_permission(context.token, Permission.CATALOG_WRITE)
    result = await service.create_relation(payload, actor.id)
    return ApiResponse[AdminRelation].success(result, request.state.request_id)


@router.patch("/relations/{relation_id}", response_model=ApiResponse[AdminRelation])
async def update_relation(
    relation_id: UUID,
    payload: AdminRelationPatch,
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[AdminRelation]:
    actor = await context.service.require_permission(context.token, Permission.CATALOG_WRITE)
    result = await service.update_relation(relation_id, payload, actor.id)
    return ApiResponse[AdminRelation].success(result, request.state.request_id)


@router.delete("/relations/{relation_id}", response_model=ApiResponse[None])
async def archive_relation(
    relation_id: UUID,
    payload: ArchiveRequest,
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[None]:
    actor = await context.service.require_permission(context.token, Permission.CATALOG_WRITE)
    await service.archive_relation(relation_id, payload.expected_version, actor.id)
    return ApiResponse[None].success(None, request.state.request_id)


@router.get("/sources", response_model=ApiResponse[AdminSourcePage])
async def list_sources(
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    filters: Annotated[AdminSourceListRequest, Query()],
) -> ApiResponse[AdminSourcePage]:
    await context.service.require_permission(context.token, Permission.CATALOG_READ)
    result = await service.list_sources(
        query=filters.query,
        source_type=filters.type,
        limit=filters.limit,
        offset=filters.offset,
    )
    return ApiResponse[AdminSourcePage].success(result, request.state.request_id)


@router.post(
    "/sources", response_model=ApiResponse[AdminSource], status_code=status.HTTP_201_CREATED
)
async def create_source(
    payload: AdminSourceCreate,
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[AdminSource]:
    actor = await context.service.require_permission(context.token, Permission.CATALOG_WRITE)
    result = await service.create_source(payload, actor.id)
    return ApiResponse[AdminSource].success(result, request.state.request_id)


@router.patch("/sources/{source_id}", response_model=ApiResponse[AdminSource])
async def update_source(
    source_id: UUID,
    payload: AdminSourcePatch,
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[AdminSource]:
    actor = await context.service.require_permission(context.token, Permission.CATALOG_WRITE)
    result = await service.update_source(source_id, payload, actor.id)
    return ApiResponse[AdminSource].success(result, request.state.request_id)


@router.delete("/sources/{source_id}", response_model=ApiResponse[None])
async def archive_source(
    source_id: UUID,
    payload: ArchiveRequest,
    request: Request,
    service: ServiceDependency,
    context: ContextDependency,
    _: OriginDependency,
) -> ApiResponse[None]:
    actor = await context.service.require_permission(context.token, Permission.CATALOG_WRITE)
    await service.archive_source(source_id, payload.expected_version, actor.id)
    return ApiResponse[None].success(None, request.state.request_id)
