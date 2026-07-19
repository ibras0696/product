from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from common.exceptions import register_exception_handlers
from infrastructure.database import get_session
from middleware.request_context import request_context
from modules.catalog import exploration_routes
from modules.catalog.domain import EntityType
from modules.catalog.graph import GraphEntity, GraphRecords
from modules.catalog.search import SearchQuery, SearchResult
from modules.catalog.timeline import TimelineEvent, TimelineQuery, TimelineResult


class FakeGraphRepository:
    def __init__(self, _: object, *, visible: bool = True) -> None:
        self.visible = visible

    async def graph_records(self, query: object) -> GraphRecords:
        center = None
        if self.visible:
            center = GraphEntity(uuid4(), EntityType.SETTLEMENT, "Центр", None)
        return GraphRecords(center=center)


class FakeSearchRepository:
    received: SearchQuery | None = None

    def __init__(self, _: object) -> None: ...

    async def district_exists(self, district_id: UUID) -> bool:
        return True

    async def search(self, query: SearchQuery) -> SearchResult:
        type(self).received = query
        return SearchResult(items=(), total=0)


class FakeTimelineRepository:
    received: TimelineQuery | None = None

    def __init__(self, _: object) -> None: ...

    async def district_exists(self, district_id: UUID) -> bool:
        return True

    async def list_events(self, query: TimelineQuery) -> TimelineResult:
        type(self).received = query
        return TimelineResult(
            items=(
                TimelineEvent(
                    id=UUID("8d605a68-7eb8-4f21-bd9c-c0d9886a692f"),
                    title_ru="Историческое событие",
                    title_ce=None,
                    short_description_ru="Подтверждённое описание",
                    short_description_ce=None,
                    period_from=1944,
                    period_to=1957,
                    latitude=None,
                    longitude=None,
                ),
            ),
            total=1,
        )


def fake_session() -> object:
    return object()


def client(monkeypatch: MonkeyPatch, *, graph_visible: bool = True) -> TestClient:
    monkeypatch.setattr(
        exploration_routes,
        "GraphRepository",
        lambda session: FakeGraphRepository(session, visible=graph_visible),
    )
    monkeypatch.setattr(exploration_routes, "CatalogSearchRepository", FakeSearchRepository)
    monkeypatch.setattr(exploration_routes, "TimelineRepository", FakeTimelineRepository)
    app = FastAPI()
    app.middleware("http")(request_context)
    app.include_router(exploration_routes.router, prefix="/api/v1")
    app.dependency_overrides[get_session] = fake_session
    register_exception_handlers(app)
    return TestClient(app)


def test_graph_repeated_types_and_transport_shape(monkeypatch: MonkeyPatch) -> None:
    response = client(monkeypatch).get(
        f"/api/v1/entities/{uuid4()}/graph",
        params=[("types", "person"), ("types", "event"), ("depth", "2")],
    )

    assert response.status_code == 200
    assert response.json()["data"]["nodes"] == []
    assert response.json()["data"]["edges"] == []


def test_graph_missing_center_uses_not_found_envelope(monkeypatch: MonkeyPatch) -> None:
    response = client(monkeypatch, graph_visible=False).get(f"/api/v1/entities/{uuid4()}/graph")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_search_strips_before_length_validation(monkeypatch: MonkeyPatch) -> None:
    response = client(monkeypatch).get("/api/v1/search", params={"q": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert FakeSearchRepository.received is None


def test_openapi_declares_semantic_graph_and_search_failures(monkeypatch: MonkeyPatch) -> None:
    schema = client(monkeypatch).get("/openapi.json").json()

    graph_responses = schema["paths"]["/api/v1/entities/{entity_id}/graph"]["get"]["responses"]
    search_responses = schema["paths"]["/api/v1/search"]["get"]["responses"]

    assert {"400", "404"} <= set(graph_responses)
    assert "400" in search_responses


def test_timeline_returns_published_event_shape(monkeypatch: MonkeyPatch) -> None:
    response = client(monkeypatch).get(
        "/api/v1/timeline/events",
        params={"period_from": 1900, "period_to": 2000},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "items": [
            {
                "id": "8d605a68-7eb8-4f21-bd9c-c0d9886a692f",
                "title": {"ru": "Историческое событие", "ce": None},
                "short_description": {
                    "ru": "Подтверждённое описание",
                    "ce": None,
                },
                "period_from": 1944,
                "period_to": 1957,
                "coordinates": None,
            }
        ],
        "meta": {"limit": 100, "offset": 0, "total": 1},
    }
    assert FakeTimelineRepository.received == TimelineQuery(None, None, 1900, 2000, 100, 0)


def test_timeline_rejects_reversed_period(monkeypatch: MonkeyPatch) -> None:
    response = client(monkeypatch).get(
        "/api/v1/timeline/events",
        params={"period_from": 2000, "period_to": 1900},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
