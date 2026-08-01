import json
import time
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from api.index import app as vercel_app
from app.api.routes import gee as gee_routes
from app.core.request_timeout import run_with_request_timeout
from app.main import app as main_app


def test_vercel_entrypoint_reuses_main_app():
    assert vercel_app is main_app


def _route_paths(app):
    return sorted(
        route.path
        for route in app.routes
        if hasattr(route, "path")
    )


def test_main_and_vercel_apps_have_same_route_registry():
    assert _route_paths(vercel_app) == _route_paths(main_app)


def test_vercel_entrypoint_contains_expected_public_routes():
    paths = set(_route_paths(vercel_app))
    assert "/" in paths
    assert "/health" in paths
    assert "/ready" in paths
    assert "/docs" in paths
    assert "/openapi.json" in paths
    assert "/api/gee/status" in paths
    assert "/api/analyze" in paths
    assert "/api/index/health" not in paths
    assert "/api/index/ready" not in paths
    assert "/api/index/api/gee/status" not in paths


def test_backend_vercel_config_routes_all_requests_to_fastapi_entrypoint():
    vercel_config_path = Path(__file__).resolve().parents[1] / "vercel.json"
    config = json.loads(vercel_config_path.read_text(encoding="utf-8"))

    assert config["version"] == 2
    assert config["functions"]["api/index.py"]["maxDuration"] == 300
    assert config["routes"] == [{"src": "/(.*)", "dest": "api/index.py"}]


def test_vercel_testclient_health_docs_and_gee_status_are_mapped():
    client = TestClient(vercel_app)
    health = client.get("/health")
    docs = client.get("/docs")
    gee_status = client.get("/api/gee/status")

    assert health.status_code == 200
    assert docs.status_code == 200
    assert gee_status.status_code != 404


def test_root_endpoint_returns_service_metadata():
    client = TestClient(vercel_app)
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "Mangrove Carbon API",
        "status": "running",
        "health": "/health",
        "docs": "/docs",
    }


def test_run_with_request_timeout_returns_result():
    assert run_with_request_timeout("quick operation", lambda: "ok", timeout_seconds=1) == "ok"


def test_run_with_request_timeout_raises_504_for_slow_operation():
    with pytest.raises(HTTPException) as exc_info:
        run_with_request_timeout("slow operation", lambda: time.sleep(0.05), timeout_seconds=0.001)

    assert exc_info.value.status_code == 504
    assert "slow operation exceeded the configured request timeout" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_gee_status_route_returns_504_on_timeout(monkeypatch):
    monkeypatch.setattr(
        gee_routes,
        "run_with_request_timeout",
        lambda operation_name, func: (_ for _ in ()).throw(HTTPException(status_code=504, detail="timed out")),
    )

    async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    assert response.status_code == 504
    assert response.json()["detail"] == "timed out"
