import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import gee_map_layer_service as gee_map_layer_service_module


@pytest.mark.asyncio
async def test_get_gmw_layer_returns_tile_descriptor(monkeypatch):
    monkeypatch.setattr(
        gee_map_layer_service_module.gee_map_layer_service,
        "get_gmw_layer_descriptor",
        lambda study_area_id: {
            "study_area": study_area_id,
            "gmw_asset_id": "projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020",
            "tile_url_template": "https://earthengine.googleapis.com/v1/projects/mangroves123/maps/test/tiles/{z}/{x}/{y}",
            "default_visible": True,
            "default_opacity": 0.5,
            "palette": ["2e8b57"],
            "label": "Mangrove Area (Global Mangrove Watch)",
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/map/gmw-layer?study_area=custom")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "live_earth_engine_gmw_layer"
    assert body["study_area"] == "custom"
    assert body["default_visible"] is True
    assert body["default_opacity"] == pytest.approx(0.5, rel=1e-9)
    assert body["label"] == "Mangrove Area (Global Mangrove Watch)"
    assert body["tile_url_template"].startswith("https://earthengine.googleapis.com/")


@pytest.mark.asyncio
async def test_get_gmw_layer_returns_503_on_service_failure(monkeypatch):
    monkeypatch.setattr(
        gee_map_layer_service_module.gee_map_layer_service,
        "get_gmw_layer_descriptor",
        lambda study_area_id: (_ for _ in ()).throw(RuntimeError("Google Earth Engine is not connected.")),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/map/gmw-layer?study_area=custom")

    assert response.status_code == 503
    assert response.json()["detail"] == "Google Earth Engine is not connected."


@pytest.mark.asyncio
async def test_check_gmw_coverage_returns_no_mangrove_warning(monkeypatch):
    monkeypatch.setattr(
        gee_map_layer_service_module.gee_map_layer_service,
        "check_polygon_mangrove_coverage",
        lambda study_area_id, geometry: {
            "study_area": study_area_id,
            "has_mangroves": False,
            "mapped_mangrove_area_ha": 0.0,
            "message": "No mapped mangroves were found inside this polygon. Please draw inside the highlighted green areas.",
        },
    )

    payload = {
        "study_area": "custom",
        "aoi_geometry": {
            "type": "Polygon",
            "coordinates": [[[67.0, 24.0], [67.4, 24.0], [67.4, 24.4], [67.0, 24.4], [67.0, 24.0]]],
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/map/gmw-coverage-check", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "live_earth_engine_gmw_coverage_check"
    assert body["has_mangroves"] is False
    assert body["message"] == "No mapped mangroves were found inside this polygon. Please draw inside the highlighted green areas."


@pytest.mark.asyncio
async def test_check_gmw_coverage_rejects_invalid_geometry():
    payload = {
        "study_area": "custom",
        "aoi_geometry": {
            "type": "Point",
            "coordinates": [67.0, 24.0],
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/map/gmw-coverage-check", json=payload)

    assert response.status_code == 422
