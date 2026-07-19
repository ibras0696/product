from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas import ApiResponse
from infrastructure.database import get_session
from modules.catalog.exploration_schemas import (
    GraphCenterView,
    GraphEdgeView,
    GraphNodeView,
    GraphRequest,
    GraphView,
    SearchItemView,
    SearchPage,
    SearchRequest,
    TimelineEventPage,
    TimelineEventView,
    TimelineRequest,
)
from modules.catalog.graph import GraphQuery, GraphResult, GraphService
from modules.catalog.graph_repository import GraphRepository
from modules.catalog.schemas import Coordinates, LocalizedText, PageMeta
from modules.catalog.search import CatalogSearchService, SearchQuery, SearchRecord
from modules.catalog.search_repository import CatalogSearchRepository
from modules.catalog.timeline import TimelineEvent, TimelineQuery, TimelineService
from modules.catalog.timeline_repository import TimelineRepository

router = APIRouter(tags=["catalog"])


@router.get(
    "/entities/{entity_id}/graph",
    response_model=ApiResponse[GraphView],
    responses={400: {"model": ApiResponse[None]}, 404: {"model": ApiResponse[None]}},
)
async def entity_graph(
    request: Request,
    entity_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    query: Annotated[GraphRequest, Query()],
) -> ApiResponse[GraphView]:
    result = await GraphService(GraphRepository(session)).graph(
        GraphQuery(
            center_id=entity_id,
            depth=query.depth,
            types=tuple(query.types),
            period_from=query.period_from,
            period_to=query.period_to,
            limit=query.limit,
        )
    )
    return ApiResponse[GraphView].success(_graph_view(result), request.state.request_id)


@router.get(
    "/search",
    response_model=ApiResponse[SearchPage],
    responses={400: {"model": ApiResponse[None]}},
)
async def search_catalog(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    query: Annotated[SearchRequest, Query()],
) -> ApiResponse[SearchPage]:
    result = await CatalogSearchService(CatalogSearchRepository(session)).search(
        SearchQuery(
            text=query.q,
            types=tuple(query.types),
            district_id=query.district_id,
            period_from=query.period_from,
            period_to=query.period_to,
            limit=query.limit,
            offset=query.offset,
        )
    )
    page = SearchPage(
        items=[_search_item(item) for item in result.items],
        meta=PageMeta(limit=query.limit, offset=query.offset, total=result.total),
    )
    return ApiResponse[SearchPage].success(page, request.state.request_id)


@router.get(
    "/timeline/events",
    response_model=ApiResponse[TimelineEventPage],
    responses={400: {"model": ApiResponse[None]}},
)
async def timeline_events(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    query: Annotated[TimelineRequest, Query()],
) -> ApiResponse[TimelineEventPage]:
    result = await TimelineService(TimelineRepository(session)).list_events(
        TimelineQuery(
            text=query.q,
            district_id=query.district_id,
            period_from=query.period_from,
            period_to=query.period_to,
            limit=query.limit,
            offset=query.offset,
        )
    )
    page = TimelineEventPage(
        items=[_timeline_event(item) for item in result.items],
        meta=PageMeta(limit=query.limit, offset=query.offset, total=result.total),
    )
    return ApiResponse[TimelineEventPage].success(page, request.state.request_id)


def _graph_view(result: GraphResult) -> GraphView:
    return GraphView(
        center=GraphCenterView(
            id=result.center.id,
            type=result.center.type,
            title=LocalizedText(ru=result.center.title_ru, ce=result.center.title_ce),
        ),
        nodes=[
            GraphNodeView(
                id=node.id,
                type=node.type,
                title=LocalizedText(ru=node.title_ru, ce=node.title_ce),
                relations_count=node.relations_count,
            )
            for node in result.nodes
        ],
        edges=[
            GraphEdgeView(
                id=edge.id,
                source_id=edge.source_id,
                target_id=edge.target_id,
                type=edge.type,
                title=LocalizedText(ru=edge.title_ru, ce=edge.title_ce),
                description=LocalizedText(ru=edge.description_ru, ce=edge.description_ce),
                sources_count=edge.sources_count,
            )
            for edge in result.edges
        ],
        hidden_nodes_count=result.hidden_nodes_count,
    )


def _search_item(item: SearchRecord) -> SearchItemView:
    coordinates = None
    if item.latitude is not None and item.longitude is not None:
        coordinates = Coordinates(latitude=item.latitude, longitude=item.longitude)
    return SearchItemView(
        id=item.id,
        type=item.type,
        title=LocalizedText(ru=item.title_ru, ce=item.title_ce),
        subtitle=LocalizedText(ru=item.subtitle_ru, ce=item.subtitle_ce),
        cover_url=item.cover_url,
        coordinates=coordinates,
        relations_count=item.relations_count,
    )


def _timeline_event(item: TimelineEvent) -> TimelineEventView:
    coordinates = None
    if item.latitude is not None and item.longitude is not None:
        coordinates = Coordinates(latitude=item.latitude, longitude=item.longitude)
    return TimelineEventView(
        id=item.id,
        title=LocalizedText(ru=item.title_ru, ce=item.title_ce),
        short_description=LocalizedText(
            ru=item.short_description_ru,
            ce=item.short_description_ce,
        ),
        period_from=item.period_from,
        period_to=item.period_to,
        coordinates=coordinates,
    )
