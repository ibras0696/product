from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.exceptions import register_exception_handlers
from middleware.request_context import request_context
from modules.catalog.domain import EntityType, RelationType, ResearchStatus, SourceType
from modules.catalog.routes import get_catalog_service, router
from modules.catalog.schemas import (
    CatalogOptions,
    Coordinates,
    DistrictOption,
    EntityDetails,
    LocalizedText,
    MapEntity,
    MapEntityCollection,
    MapRelation,
    Page,
    PageMeta,
    PublishedMedia,
    SourceView,
)
from modules.catalog.service import CatalogService, MapQuery


class FakeCatalogRepository:
    def __init__(self) -> None:
        self.entity_id = uuid4()
        self.peer_entity_id = uuid4()
        self.relation_id = uuid4()
        self.district_id = uuid4()
        self.map_query: MapQuery | None = None
        self.entity_visible = True

    async def district_exists(self, district_id: UUID) -> bool:
        return district_id == self.district_id

    async def map_entities(self, query: MapQuery) -> MapEntityCollection:
        self.map_query = query
        return MapEntityCollection(
            items=[
                MapEntity(
                    id=self.entity_id,
                    type=EntityType.SETTLEMENT,
                    title=LocalizedText(ru="Грозный", ce=None),
                    coordinates=Coordinates(latitude=43.32, longitude=45.69),
                    relations_count=2,
                    cover_url=None,
                    district_id=self.district_id,
                    research_status=ResearchStatus.VERIFIED,
                ),
                MapEntity(
                    id=self.peer_entity_id,
                    type=EntityType.EVENT,
                    title=LocalizedText(ru="Событие", ce=None),
                    coordinates=Coordinates(latitude=43.33, longitude=45.70),
                    relations_count=1,
                    cover_url=None,
                    district_id=self.district_id,
                    research_status=ResearchStatus.VERIFIED,
                ),
            ],
            relations=[
                MapRelation(
                    id=self.relation_id,
                    source_id=self.entity_id,
                    target_id=self.peer_entity_id,
                    type=RelationType.CONNECTED_WITH,
                    source_type=EntityType.SETTLEMENT,
                    source_title="Грозный",
                    target_type=EntityType.EVENT,
                    target_title="Событие",
                )
            ],
            truncated=True,
            relations_truncated=False,
        )

    async def get_entity(self, entity_id: UUID) -> EntityDetails | None:
        if entity_id != self.entity_id or not self.entity_visible:
            return None
        return EntityDetails(
            id=entity_id,
            type=EntityType.SETTLEMENT,
            slug="grozny",
            title=LocalizedText(ru="Грозный", ce=None),
            short_description=LocalizedText(ru="Столица", ce=None),
            full_description=LocalizedText(ru="Столица Чечни", ce=None),
            coordinates=Coordinates(latitude=43.32, longitude=45.69),
            period_from=None,
            period_to=None,
            cover_url=None,
            relations_count=2,
            sources_count=1,
            media_count=0,
            status="published",
            research_status=ResearchStatus.VERIFIED,
        )

    async def list_entity_sources(
        self, entity_id: UUID, limit: int, offset: int
    ) -> Page[SourceView] | None:
        if entity_id != self.entity_id:
            return None
        return Page[SourceView](
            items=[
                SourceView(
                    id=uuid4(),
                    title="Архивный документ",
                    type=SourceType.ARCHIVE_DOCUMENT,
                    author=None,
                    publisher=None,
                    publication_year=None,
                    url=None,
                    archive_reference="A-1",
                    description="Описание",
                    is_verified=True,
                )
            ],
            meta=PageMeta(limit=limit, offset=offset, total=1),
        )

    async def list_relation_sources(
        self, relation_id: UUID, limit: int, offset: int
    ) -> Page[SourceView] | None:
        return None

    async def list_entity_media(
        self, entity_id: UUID, limit: int, offset: int
    ) -> Page[PublishedMedia] | None:
        if entity_id != self.entity_id:
            return None
        return Page[PublishedMedia](items=[], meta=PageMeta(limit=limit, offset=offset, total=0))

    async def get_options(self) -> CatalogOptions:
        return CatalogOptions(
            districts=[
                DistrictOption(
                    id=self.district_id,
                    title=LocalizedText(ru="Грозненский", ce=None),
                )
            ],
            periods=[],
            entity_types=list(EntityType),
            research_statuses=list(ResearchStatus),
        )


def _client() -> tuple[TestClient, FakeCatalogRepository]:
    repository = FakeCatalogRepository()
    app = FastAPI()
    app.middleware("http")(request_context)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_catalog_service] = lambda: CatalogService(repository)
    register_exception_handlers(app)
    return TestClient(app), repository


def test_map_validates_filters_and_returns_bounded_transport_shape() -> None:
    client, repository = _client()
    response = client.get(
        "/api/v1/map/entities",
        params=[
            ("bbox", "45,43,46,44"),
            ("zoom", "8"),
            ("types", "settlement"),
            ("district_id", str(repository.district_id)),
            ("limit", "2"),
        ],
        headers={"X-Request-ID": "catalog-map"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["truncated"] is True
    assert response.json()["data"]["relations"] == [
        {
            "id": str(repository.relation_id),
            "source_id": str(repository.entity_id),
            "target_id": str(repository.peer_entity_id),
            "type": "connected_with",
            "source_type": "settlement",
            "source_title": "Грозный",
            "target_type": "event",
            "target_title": "Событие",
        }
    ]
    assert response.json()["data"]["relations_truncated"] is False
    assert response.json()["meta"] == {"request_id": "catalog-map"}
    assert repository.map_query == MapQuery(
        bbox=(45.0, 43.0, 46.0, 44.0),
        zoom=8,
        types=(EntityType.SETTLEMENT,),
        district_id=repository.district_id,
        period_from=None,
        period_to=None,
        limit=2,
    )


def test_semantic_map_errors_have_stable_bad_request_envelope() -> None:
    client, repository = _client()
    cases = [
        {"bbox": "46,43,45,44", "zoom": 8},
        {"bbox": "45,43,46,44", "zoom": 8, "period_from": 2000, "period_to": 1900},
        {"bbox": "45,43,46,44", "zoom": 8, "district_id": uuid4()},
    ]

    for params in cases:
        response = client.get(
            "/api/v1/map/entities",
            params=params,
            headers={"X-Request-ID": "catalog-invalid"},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "bad_request"
        assert response.json()["meta"] == {"request_id": "catalog-invalid"}
    assert repository.map_query is None


def test_map_rejects_payloads_above_the_bounded_research_limit() -> None:
    client, repository = _client()

    response = client.get(
        "/api/v1/map/entities",
        params={"bbox": "45,43,46,44", "zoom": 8, "limit": 1001},
    )

    assert response.status_code == 422
    assert repository.map_query is None


def test_details_and_child_pages_hide_missing_or_nonpublic_parents() -> None:
    client, repository = _client()
    details = client.get(f"/api/v1/entities/{repository.entity_id}")
    sources = client.get(
        f"/api/v1/entities/{repository.entity_id}/sources", params={"limit": 10, "offset": 1}
    )
    media = client.get(f"/api/v1/entities/{repository.entity_id}/media")
    repository.entity_visible = False
    hidden = client.get(f"/api/v1/entities/{repository.entity_id}")

    assert details.status_code == 200
    assert details.json()["data"]["status"] == "published"
    assert sources.json()["data"]["meta"] == {"limit": 10, "offset": 1, "total": 1}
    assert sources.json()["data"]["items"][0]["is_verified"] is True
    assert media.json()["data"]["items"] == []
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "not_found"


def test_child_pagination_is_strictly_bounded() -> None:
    client, repository = _client()

    too_large = client.get(
        f"/api/v1/entities/{repository.entity_id}/sources", params={"limit": 101}
    )
    negative = client.get(f"/api/v1/entities/{repository.entity_id}/media", params={"offset": -1})

    assert too_large.status_code == 422
    assert too_large.json()["error"]["code"] == "validation_error"
    assert negative.status_code == 422


def test_options_etag_supports_conditional_reads() -> None:
    client, _ = _client()
    first = client.get("/api/v1/catalog/options", headers={"X-Request-ID": "options"})
    etag = first.headers["etag"]
    cached = client.get("/api/v1/catalog/options", headers={"If-None-Match": etag})

    assert first.status_code == 200
    assert first.json()["data"]["entity_types"] == [item.value for item in EntityType]
    assert first.json()["meta"] == {"request_id": "options"}
    assert cached.status_code == 304
    assert cached.content == b""
    assert cached.headers["etag"] == etag


def test_options_openapi_declares_conditional_response() -> None:
    client, _ = _client()

    schema = client.get("/openapi.json").json()
    responses = schema["paths"]["/api/v1/catalog/options"]["get"]["responses"]

    assert "200" in responses
    assert responses["304"]["description"] == "Not Modified"
