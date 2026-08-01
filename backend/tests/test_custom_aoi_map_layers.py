from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import inspect

import pytest

from app.core.gee_datasets import (
    MAP_LAYER_CARBON_MAX_MG_C_HA,
    MAP_LAYER_CARBON_MIN_MG_C_HA,
    MAP_LAYER_ID_CARBON,
    MAP_LAYER_ID_GEDI,
    MAP_LAYER_ID_GMW,
    MAP_LAYER_ID_RH98,
)
from app.services import gee_carbon_stock_service as stock_module
from app.services.gee_carbon_stock_service import GeeCarbonStockService, _CarbonStockResult


def _polygon():
    return {
        "type": "Polygon",
        "coordinates": [[[66.5, 23.5], [68.5, 23.5], [68.5, 24.8], [66.5, 24.8], [66.5, 23.5]]],
    }


class _FakeImage:
    def select(self, _):
        return self

    def mask(self):
        return self

    def updateMask(self, _):
        return self

    def selfMask(self):
        return self

    def clip(self, _):
        return self

    def visualize(self, **_):
        return self

    def divide(self, _):
        return self


class _FakeCollection:
    def filterBounds(self, _):
        return self

    def filterDate(self, _, __):
        return self


def _connected_ctx():
    return SimpleNamespace(enabled=True, connected=True, message=None)


def test_map_layers_order_is_stable_and_geometry_preserved(monkeypatch):
    service = GeeCarbonStockService()
    polygon = _polygon()
    call_count = {"n": 0}

    monkeypatch.setattr(
        stock_module.gee_service_module,
        "gee_service",
        SimpleNamespace(get_connection_context=_connected_ctx),
    )
    monkeypatch.setattr(service, "_geojson_polygon_to_ee_geometry", lambda _: {"ok": True})
    monkeypatch.setattr(
        service,
        "_run_live_summary_parameterized",
        lambda *_: _CarbonStockResult(response={"results": {"ok": True}}, is_success=True),
    )
    monkeypatch.setattr(service, "_build_analysis_image", lambda **_: _FakeImage())
    monkeypatch.setattr(stock_module.gee_mask_service, "build_binary_mask", lambda *_: _FakeImage())
    monkeypatch.setattr(
        stock_module,
        "ee",
        SimpleNamespace(
            ImageCollection=lambda *_: _FakeCollection(),
            Image=SimpleNamespace(
                pixelArea=lambda: _FakeImage(),
                constant=lambda *_: _FakeImage(),
            ),
        ),
    )

    def fake_tile(_, layer_id):
        call_count["n"] += 1
        return f"https://earthengine.googleapis.com/v1/projects/mangroves123/maps/{layer_id}/tiles/{{z}}/{{x}}/{{y}}"

    monkeypatch.setattr(service, "_image_to_tile_url_template", fake_tile)

    response = service.run_live_map_layers_for_custom_aoi(
        "indus_delta", "Indus Delta, Pakistan", polygon, "2020-01-01", "2020-04-01"
    )
    assert response.mode == "live_earth_engine_map_layers"
    assert response.aoi_geometry == polygon
    assert [layer.id for layer in response.layers] == [
        MAP_LAYER_ID_GMW,
        MAP_LAYER_ID_GEDI,
        MAP_LAYER_ID_CARBON,
        MAP_LAYER_ID_RH98,
    ]
    carbon = next(layer for layer in response.layers if layer.id == MAP_LAYER_ID_CARBON)
    assert carbon.min == MAP_LAYER_CARBON_MIN_MG_C_HA
    assert carbon.max == MAP_LAYER_CARBON_MAX_MG_C_HA
    assert call_count["n"] == 4


def test_map_layer_cache_expiry_regenerates(monkeypatch):
    service = GeeCarbonStockService()
    polygon = _polygon()
    tile_calls = {"n": 0}
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    times = [
        t0,
        t0 + timedelta(seconds=10),
        t0 + timedelta(seconds=10),
        t0 + timedelta(seconds=1300),
        t0 + timedelta(seconds=1301),
        t0 + timedelta(seconds=1301),
        t0 + timedelta(seconds=1302),
        t0 + timedelta(seconds=1302),
    ]

    monkeypatch.setattr(service, "_utcnow", lambda: times.pop(0))
    monkeypatch.setattr(
        stock_module.gee_service_module,
        "gee_service",
        SimpleNamespace(get_connection_context=_connected_ctx),
    )
    monkeypatch.setattr(service, "_geojson_polygon_to_ee_geometry", lambda _: {"ok": True})
    monkeypatch.setattr(
        service,
        "_run_live_summary_parameterized",
        lambda *_: _CarbonStockResult(response={"results": {"ok": True}}, is_success=True),
    )
    monkeypatch.setattr(service, "_build_analysis_image", lambda **_: _FakeImage())
    monkeypatch.setattr(stock_module.gee_mask_service, "build_binary_mask", lambda *_: _FakeImage())
    monkeypatch.setattr(
        stock_module,
        "ee",
        SimpleNamespace(
            ImageCollection=lambda *_: _FakeCollection(),
            Image=SimpleNamespace(pixelArea=lambda: _FakeImage(), constant=lambda *_: _FakeImage()),
        ),
    )
    monkeypatch.setattr(
        service,
        "_image_to_tile_url_template",
        lambda *_args, **kwargs: (
            tile_calls.__setitem__("n", tile_calls["n"] + 1)
            or f"https://earthengine.googleapis.com/v1/projects/mangroves123/maps/{kwargs['layer_id']}/tiles/{{z}}/{{x}}/{{y}}"
        ),
    )

    service.run_live_map_layers_for_custom_aoi("custom", "Custom AOI", polygon, "2020-01-01", "2020-04-01")
    service.run_live_map_layers_for_custom_aoi("custom", "Custom AOI", polygon, "2020-01-01", "2020-04-01")
    service.run_live_map_layers_for_custom_aoi("custom", "Custom AOI", polygon, "2020-01-01", "2020-04-01")
    assert tile_calls["n"] == 8  # first generation 4 layers + regeneration after expiry 4 layers


def test_unsafe_tile_host_is_rejected():
    service = GeeCarbonStockService()
    with pytest.raises(ValueError, match="not in allowlist"):
        service._validate_tile_url_template(
            "https://example.com/v1/projects/x/maps/abc/tiles/{z}/{x}/{y}",
            layer_id="gmw_mangrove_extent",
        )


def test_no_data_map_layers_returns_http200_style_payload(monkeypatch):
    service = GeeCarbonStockService()
    polygon = _polygon()
    monkeypatch.setattr(
        stock_module.gee_service_module,
        "gee_service",
        SimpleNamespace(get_connection_context=_connected_ctx),
    )
    monkeypatch.setattr(service, "_geojson_polygon_to_ee_geometry", lambda _: {"ok": True})
    monkeypatch.setattr(
        service,
        "_run_live_summary_parameterized",
        lambda *_: _CarbonStockResult(
            response={"message": "AOI has no mapped mangrove area (no GMW mask coverage).", "error": True},
            is_success=False,
        ),
    )
    response = service.run_live_map_layers_for_custom_aoi(
        "abu_dhabi", "Abu Dhabi, United Arab Emirates", polygon, "2020-01-01", "2020-04-01"
    )
    assert response.mode == "live_earth_engine_map_layers"
    assert response.layers == []
    assert any("no mapped mangrove area" in warning.lower() for warning in response.warnings)


def test_gmw_layer_masks_non_mangrove_pixels_transparently():
    source = inspect.getsource(GeeCarbonStockService.run_live_map_layers_for_custom_aoi)
    assert "gmw_mask.selfMask().clip(geometry)" in source


def test_gedi_layer_uses_valid_mask_not_raw_pixel_area_values():
    source = inspect.getsource(GeeCarbonStockService.run_live_map_layers_for_custom_aoi)
    assert "ee.Image.constant(1).updateMask(valid_mask)" in source
    assert "_GEDI_COVERAGE_BAND" not in source
