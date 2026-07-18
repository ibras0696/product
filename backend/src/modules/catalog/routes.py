from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import ApiResponse
from infrastructure.database import get_session
from modules.catalog.repository import CatalogRepository
from modules.catalog.schemas import (
    CatalogOptions,
    EntityDetails,
    MapEntityCollection,
    MapRequest,
    Page,
    PublishedMedia,
    SourceView,
)
from modules.catalog.service import CatalogService

router = APIRouter(
    tags=["catalog"],
    responses={
        400: {"model": ApiResponse[None]},
        404: {"model": ApiResponse[None]},
        422: {"model": ApiResponse[None]},
    },
)


def get_catalog_service(session: Annotated[AsyncSession, Depends(get_session)]) -> CatalogService:
    return CatalogService(CatalogRepository(session))


CatalogServiceDependency = Annotated[CatalogService, Depends(get_catalog_service)]


@router.get("/map/entities", response_model=ApiResponse[MapEntityCollection])
async def map_entities(
    request: Request,
    service: CatalogServiceDependency,
    query: Annotated[MapRequest, Query()],
) -> ApiResponse[MapEntityCollection]:
    result = await service.map_entities(query)
    return ApiResponse[MapEntityCollection].success(result, request.state.request_id)


@router.get("/entities/{entity_id}", response_model=ApiResponse[EntityDetails])
async def entity_details(
    request: Request, entity_id: UUID, service: CatalogServiceDependency
) -> ApiResponse[EntityDetails]:
    result = await service.entity_details(entity_id)
    return ApiResponse[EntityDetails].success(result, request.state.request_id)


@router.get("/entities/{entity_id}/sources", response_model=ApiResponse[Page[SourceView]])
async def entity_sources(
    request: Request,
    entity_id: UUID,
    service: CatalogServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> ApiResponse[Page[SourceView]]:
    result = await service.entity_sources(entity_id, limit, offset)
    return ApiResponse[Page[SourceView]].success(result, request.state.request_id)


@router.get("/relations/{relation_id}/sources", response_model=ApiResponse[Page[SourceView]])
async def relation_sources(
    request: Request,
    relation_id: UUID,
    service: CatalogServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> ApiResponse[Page[SourceView]]:
    result = await service.relation_sources(relation_id, limit, offset)
    return ApiResponse[Page[SourceView]].success(result, request.state.request_id)


@router.get("/entities/{entity_id}/media", response_model=ApiResponse[Page[PublishedMedia]])
async def entity_media(
    request: Request,
    entity_id: UUID,
    service: CatalogServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> ApiResponse[Page[PublishedMedia]]:
    result = await service.entity_media(entity_id, limit, offset)
    return ApiResponse[Page[PublishedMedia]].success(result, request.state.request_id)


@router.get("/catalog/options", response_model=ApiResponse[CatalogOptions])
async def catalog_options(
    request: Request,
    service: CatalogServiceDependency,
    if_none_match: Annotated[str | None, Header()] = None,
) -> Response:
    options, etag = await service.options()
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    payload = ApiResponse[CatalogOptions].success(options, request.state.request_id)
    return JSONResponse(content=payload.model_dump(mode="json"), headers={"ETag": etag})
