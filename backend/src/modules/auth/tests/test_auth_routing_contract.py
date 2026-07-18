from fastapi.testclient import TestClient

from main import create_app


def test_versioned_auth_contract_keeps_legacy_runtime_transition() -> None:
    app = create_app()
    paths = app.openapi()["paths"]

    assert "/api/v1/auth/login" in paths
    assert "/api/v1/admin/me" in paths
    assert "/api/auth/login" not in paths
    assert TestClient(app).post("/api/auth/login", json={}).status_code == 422
    admin_responses = paths["/api/v1/admin/me"]["get"]["responses"]
    assert admin_responses["401"]["content"]["application/json"]["schema"]
    assert admin_responses["403"]["content"]["application/json"]["schema"]
    assert admin_responses["422"]["content"]["application/json"]["schema"]
