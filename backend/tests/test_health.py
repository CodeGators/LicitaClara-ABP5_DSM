import json
from uuid import UUID

from fastapi.testclient import TestClient
from licita_backend.main import create_app


def test_health_is_independent_of_database_and_ready_reports_failure(settings, capsys):
    with TestClient(create_app(settings)) as client:
        health = client.get("/api/v1/health")
        ready = client.get("/api/v1/ready")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert ready.status_code == 503
        assert ready.json()["database"] == "unavailable"
        assert UUID(ready.headers["X-Request-ID"])
    logs = capsys.readouterr().err
    assert "test_password_do_not_leak" not in logs
    entries = [json.loads(line) for line in logs.splitlines()]
    assert any(e["event"] == "database_unavailable" for e in entries)
    assert any(e.get("request_id") == ready.headers["X-Request-ID"] for e in entries)


def test_cors_allows_only_configured_origin(settings):
    with TestClient(create_app(settings)) as client:
        allowed = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
        denied = client.get("/api/v1/health", headers={"Origin": "https://unknown.example"})
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "access-control-allow-origin" not in denied.headers


def test_openapi_declares_readiness_failure(settings):
    with TestClient(create_app(settings)) as client:
        schema = client.get("/openapi.json").json()
        assert "503" in schema["paths"]["/api/v1/ready"]["get"]["responses"]
