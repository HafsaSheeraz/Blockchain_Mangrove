from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core import config as config_module
from app.main import create_app
from app.models.analysis import AnalyzeRequest
import app.main as main_module
import app.models.analysis as analysis_model
import app.services.gee_service as gee_service_module


def _settings(**overrides):
    backend_dir = Path(__file__).resolve().parents[1]
    base = {
        "app_env": "production",
        "api_version": "0.4.1",
        "host": "127.0.0.1",
        "port": 8001,
        "cors_origins": ["https://app.example"],
        "request_timeout_seconds": 120,
        "map_layer_cache_ttl_seconds": 1200,
        "log_level": "info",
        "max_aoi_total_vertices": 5000,
        "max_aoi_interior_rings": 20,
        "max_aoi_ring_vertices": 2000,
        "max_aoi_serialized_bytes": 200000,
        "max_aoi_date_range_days": 1461,
        "max_request_body_bytes": 1000000,
        "map_tile_allowed_hosts": ["earthengine.googleapis.com"],
        "gee_enabled": True,
        "gee_project_id": "mangroves123",
        "gee_service_account_email": "mangrove-carbon-backend@mangroves123.iam.gserviceaccount.com",
        "gee_private_key_file": "gee-service-account.json",
        "backend_dir": backend_dir,
    }
    base.update(overrides)
    return config_module.Settings(**base)


def _create_app(settings):
    main_module.settings = settings
    return create_app()


def _ready_client(settings):
    return AsyncClient(transport=ASGITransport(app=_create_app(settings)), base_url="http://test")


def test_build_settings_normalizes_origin_lists(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", " https://app.example/ , https://api.example ")
    monkeypatch.setenv("MAP_TILE_ALLOWED_HOSTS", "earthengine.googleapis.com, earthengine-alt.googleapis.com")

    settings = config_module.build_settings()

    assert settings.cors_origins == ["https://app.example", "https://api.example"]
    assert settings.map_tile_allowed_hosts == ["earthengine.googleapis.com", "earthengine-alt.googleapis.com"]


def test_build_settings_uses_empty_cors_allowlist_in_production_when_unset(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    settings = config_module.build_settings()

    assert settings.cors_origins == []


@pytest.mark.asyncio
async def test_ready_endpoint_reports_ready_without_earth_engine_check(monkeypatch, tmp_path):
    key_file = tmp_path / "gee-service-account.json"
    key_file.write_text("fake-key")
    settings = _settings(gee_private_key_file=str(key_file))
    monkeypatch.setattr(gee_service_module.gee_service, "get_connection_context", lambda: (_ for _ in ()).throw(AssertionError("Earth Engine should not be checked")))

    async with _ready_client(settings) as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "ready": True,
        "app_env": "production",
        "gee_enabled": True,
        "cors_origins_configured": True,
        "issues": [],
    }


@pytest.mark.asyncio
async def test_ready_endpoint_reports_missing_production_cors_allowlist():
    settings = _settings(cors_origins=[], gee_enabled=False)

    async with _ready_client(settings) as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert any("CORS_ORIGINS" in issue for issue in body["issues"])


@pytest.mark.asyncio
async def test_security_headers_are_added_to_api_responses():
    settings = _settings(cors_origins=["https://app.example"], gee_enabled=False)

    async with _ready_client(settings) as client:
        response = await client.get("/health", headers={"Origin": "https://app.example"})

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["permissions-policy"] == "geolocation=(), camera=(), microphone=()"
    assert response.headers["x-request-id"]
    assert response.headers["access-control-allow-origin"] == "https://app.example"


@pytest.mark.asyncio
async def test_request_body_limit_rejects_oversized_api_requests():
    settings = _settings(max_request_body_bytes=20, gee_enabled=False)

    async with _ready_client(settings) as client:
        response = await client.post(
            "/api/analyze",
            json={
                "study_area": "indus_delta",
                "start_date": "2020-01-01",
                "end_date": "2020-04-01",
                "padding": "this request is intentionally larger than the configured limit",
            },
        )

    assert response.status_code == 413
    assert response.text == "Request body too large."
    assert response.headers["x-request-id"]


def test_date_range_limit_rejects_excessive_spans(monkeypatch):
    monkeypatch.setattr(analysis_model, "settings", _settings(max_aoi_date_range_days=30, gee_enabled=False))

    with pytest.raises(ValueError, match="maximum allowed length of 30 days"):
        AnalyzeRequest(
            study_area="indus_delta",
            start_date="2020-01-01",
            end_date="2020-03-01",
        )
