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


def fake_session() -> object:
    return object()


def client(monkeypatch: MonkeyPatch, *, graph_visible: bool = True) -> TestClient:
    monkeypatch.setattr(
        exploration_routes,
        "GraphRepository",
        lambda session: FakeGraphRepository(session, visible=graph_visible),
    )
    monkeypatch.setattr(exploration_routes, "CatalogSearchRepository", FakeSearchRepository)
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
