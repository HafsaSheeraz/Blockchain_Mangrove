from copy import deepcopy
from types import SimpleNamespace
import inspect

import pytest
from fastapi import HTTPException

from app.models.analysis import AnalyzeRequest, CustomAoiAnalyzeResponse
from app.services import analysis_service
from app.services import gee_carbon_stock_service as stock_module
from app.services.gee_carbon_stock_service import GeeCarbonStockService, _CarbonStockResult


def _indus_polygon():
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [66.5, 23.5],
                [68.5, 23.5],
                [68.5, 24.8],
                [66.5, 24.8],
                [66.5, 23.5],
            ]
        ],
    }


def _abu_dhabi_polygon():
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [53.6, 23.7],
                [55.9, 23.7],
                [55.9, 25.6],
                [53.6, 25.6],
                [53.6, 23.7],
            ]
        ],
    }


def _polygon_with_hole():
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [66.0, 23.0],
                [69.0, 23.0],
                [69.0, 25.0],
                [66.0, 25.0],
                [66.0, 23.0],
            ],
            [
                [67.0, 23.5],
                [68.0, 23.5],
                [68.0, 24.5],
                [67.0, 24.5],
                [67.0, 23.5],
            ],
        ],
    }


def _valid_results_dict():
    return {
        "results": {
            "valid_gedi_samples": 10,
            "mean_rh98_m": 3.0,
            "min_rh98_m": 2.0,
            "max_rh98_m": 4.0,
            "mean_agb_mg_ha": 30.0,
            "mean_bgb_mg_ha": 14.7,
            "mean_carbon_mg_c_ha": 22.35,
            "min_carbon_mg_c_ha": 15.0,
            "max_carbon_mg_c_ha": 31.0,
            "mangrove_area_ha": 100.0,
            "gedi_sampled_coverage_percent": 2.5,
            "direct_sampled_carbon_mg_c": 55.0,
            "extrapolated_total_carbon_mg_c": 2235.0,
        },
        "warning": "Custom AOI analysis complete.",
    }


def _bounds(coords):
    ring = coords[0]
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return min(lons), max(lons), min(lats), max(lats)


def test_geojson_conversion_preserves_lon_lat_order(monkeypatch):
    service = GeeCarbonStockService()
    captured = {}

    def fake_geometry(geojson):
        captured["geojson"] = geojson
        return {"ok": True}

    monkeypatch.setattr(stock_module, "ee", SimpleNamespace(Geometry=fake_geometry))
    polygon = _indus_polygon()
    service._geojson_polygon_to_ee_geometry(polygon)

    assert captured["geojson"]["coordinates"][0][0] == [66.5, 23.5]
    assert captured["geojson"] == polygon


def test_indus_bounds_preserved_in_geometry_constructor(monkeypatch):
    service = GeeCarbonStockService()
    captured = {}

    def fake_geometry(geojson):
        captured["geojson"] = geojson
        return {"ok": True}

    monkeypatch.setattr(stock_module, "ee", SimpleNamespace(Geometry=fake_geometry))
    polygon = _indus_polygon()
    service._geojson_polygon_to_ee_geometry(polygon)

    min_lon, max_lon, min_lat, max_lat = _bounds(captured["geojson"]["coordinates"])
    assert min_lon == pytest.approx(66.5)
    assert max_lon == pytest.approx(68.5)
    assert min_lat == pytest.approx(23.5)
    assert max_lat == pytest.approx(24.8)


def test_abu_dhabi_longitude_latitude_not_swapped(monkeypatch):
    service = GeeCarbonStockService()
    captured = {}

    def fake_geometry(geojson):
        captured["geojson"] = geojson
        return {"ok": True}

    monkeypatch.setattr(stock_module, "ee", SimpleNamespace(Geometry=fake_geometry))
    polygon = _abu_dhabi_polygon()
    service._geojson_polygon_to_ee_geometry(polygon)

    min_lon, max_lon, min_lat, max_lat = _bounds(captured["geojson"]["coordinates"])
    assert 53 <= min_lon <= 54
    assert 55 <= max_lon <= 56
    assert 23 <= min_lat <= 24
    assert 25 <= max_lat <= 26


def test_outer_ring_and_holes_preserve_coordinate_order(monkeypatch):
    service = GeeCarbonStockService()
    captured = {}

    def fake_geometry(geojson):
        captured["geojson"] = geojson
        return {"ok": True}

    monkeypatch.setattr(stock_module, "ee", SimpleNamespace(Geometry=fake_geometry))
    polygon = _polygon_with_hole()
    service._geojson_polygon_to_ee_geometry(polygon)

    assert captured["geojson"]["coordinates"][0][0] == [66.0, 23.0]
    assert captured["geojson"]["coordinates"][1][0] == [67.0, 23.5]
    assert captured["geojson"] == polygon


def test_cache_key_is_deterministic_for_canonical_json():
    service = GeeCarbonStockService()

    one = {"type": "Polygon", "coordinates": _indus_polygon()["coordinates"]}
    two = {"coordinates": _indus_polygon()["coordinates"], "type": "Polygon"}

    key_one = service._make_custom_aoi_cache_key(one, "2020-01-01", "2020-04-01")
    key_two = service._make_custom_aoi_cache_key(two, "2020-01-01", "2020-04-01")
    assert key_one == key_two


def test_cache_key_changes_for_geometry_date_and_holes():
    service = GeeCarbonStockService()
    indus = _indus_polygon()
    abu = _abu_dhabi_polygon()
    with_hole = _polygon_with_hole()

    base = service._make_custom_aoi_cache_key(indus, "2020-01-01", "2020-04-01")
    different_geometry = service._make_custom_aoi_cache_key(abu, "2020-01-01", "2020-04-01")
    different_dates = service._make_custom_aoi_cache_key(indus, "2020-02-01", "2020-04-01")
    different_holes = service._make_custom_aoi_cache_key(with_hole, "2020-01-01", "2020-04-01")

    assert base != different_geometry
    assert base != different_dates
    assert base != different_holes


def test_same_request_reuses_custom_cache_and_never_returns_baseline_cache(monkeypatch):
    service = GeeCarbonStockService()
    service._cached_success_response = object()
    polygon = _indus_polygon()
    calls = {"count": 0}

    monkeypatch.setattr(
        stock_module.gee_service_module,
        "gee_service",
        SimpleNamespace(get_connection_context=lambda: SimpleNamespace(enabled=True, connected=True)),
    )
    monkeypatch.setattr(service, "_geojson_polygon_to_ee_geometry", lambda _: {"geometry": "ok"})

    def fake_run(*args, **kwargs):
        calls["count"] += 1
        return _CarbonStockResult(response=_valid_results_dict(), is_success=True)

    monkeypatch.setattr(service, "_run_live_summary_parameterized", fake_run)

    first = service.run_live_summary_for_custom_aoi(
        "custom", "Custom AOI", polygon, "2020-01-01", "2020-04-01"
    )
    second = service.run_live_summary_for_custom_aoi(
        "custom", "Custom AOI", deepcopy(polygon), "2020-01-01", "2020-04-01"
    )

    assert isinstance(first, CustomAoiAnalyzeResponse)
    assert first.mode == "live_earth_engine_custom_aoi"
    assert first.study_area.name == "Custom AOI"
    assert first.results is not None
    assert first.results.direct_sampled_carbon_mg_c == pytest.approx(55.0)
    assert second.results is not None
    assert second.results.direct_sampled_carbon_mg_c == pytest.approx(55.0)
    assert calls["count"] == 1


def test_serverless_cache_miss_still_returns_correct_result(monkeypatch):
    service = GeeCarbonStockService()
    polygon = _indus_polygon()
    calls = {"count": 0}

    monkeypatch.setattr(
        stock_module.gee_service_module,
        "gee_service",
        SimpleNamespace(get_connection_context=lambda: SimpleNamespace(enabled=True, connected=True)),
    )
    monkeypatch.setattr(service, "_geojson_polygon_to_ee_geometry", lambda _: {"geometry": "ok"})

    def fake_run(*args, **kwargs):
        calls["count"] += 1
        return _CarbonStockResult(response=_valid_results_dict(), is_success=True)

    monkeypatch.setattr(service, "_run_live_summary_parameterized", fake_run)

    first = service.run_live_summary_for_custom_aoi(
        "custom", "Custom AOI", polygon, "2020-01-01", "2020-04-01"
    )
    service._custom_aoi_cache.clear()
    second = service.run_live_summary_for_custom_aoi(
        "custom", "Custom AOI", deepcopy(polygon), "2020-01-01", "2020-04-01"
    )

    assert first.results is not None
    assert second.results is not None
    assert first.results.direct_sampled_carbon_mg_c == pytest.approx(55.0)
    assert second.results.direct_sampled_carbon_mg_c == pytest.approx(55.0)
    assert calls["count"] == 2


def test_same_geometry_with_different_study_area_ids_keeps_correct_labels(monkeypatch):
    service = GeeCarbonStockService()
    polygon = _indus_polygon()
    calls = {"count": 0}

    monkeypatch.setattr(
        stock_module.gee_service_module,
        "gee_service",
        SimpleNamespace(get_connection_context=lambda: SimpleNamespace(enabled=True, connected=True)),
    )
    monkeypatch.setattr(service, "_geojson_polygon_to_ee_geometry", lambda _: {"geometry": "ok"})

    def fake_run(*args, **kwargs):
        calls["count"] += 1
        return _CarbonStockResult(response=_valid_results_dict(), is_success=True)

    monkeypatch.setattr(service, "_run_live_summary_parameterized", fake_run)

    indus = service.run_live_summary_for_custom_aoi(
        "indus_delta",
        "Indus Delta, Pakistan",
        polygon,
        "2020-01-01",
        "2020-04-01",
    )
    custom = service.run_live_summary_for_custom_aoi(
        "custom",
        "Custom AOI",
        deepcopy(polygon),
        "2020-01-01",
        "2020-04-01",
    )

    assert indus.study_area.id == "indus_delta"
    assert indus.study_area.name == "Indus Delta, Pakistan"
    assert custom.study_area.id == "custom"
    assert custom.study_area.name == "Custom AOI"
    # indus_delta uses GMW_2020_INDUS; custom uses GMW_GLOBAL_2020_COLLECTION.
    # Different GMW assets → different cache keys → two separate EE calls.
    assert calls["count"] == 2


def test_failed_and_no_data_results_are_not_cached(monkeypatch):
    service = GeeCarbonStockService()
    polygon = _indus_polygon()
    calls = {"count": 0}

    monkeypatch.setattr(
        stock_module.gee_service_module,
        "gee_service",
        SimpleNamespace(get_connection_context=lambda: SimpleNamespace(enabled=True, connected=True)),
    )
    monkeypatch.setattr(service, "_geojson_polygon_to_ee_geometry", lambda _: {"geometry": "ok"})

    def fake_run(*args, **kwargs):
        calls["count"] += 1
        return _CarbonStockResult(
            response={"message": "No GEDI data available for the AOI and date range.", "error": True},
            is_success=False,
        )

    monkeypatch.setattr(service, "_run_live_summary_parameterized", fake_run)

    first = service.run_live_summary_for_custom_aoi(
        "custom", "Custom AOI", polygon, "2020-01-01", "2020-04-01"
    )
    second = service.run_live_summary_for_custom_aoi(
        "custom", "Custom AOI", polygon, "2020-01-01", "2020-04-01"
    )

    assert first.results is None
    assert second.results is None
    assert calls["count"] == 2
    assert len(service._custom_aoi_cache) == 0


def test_live_mode_maps_service_failures_to_http_errors(monkeypatch):
    request = AnalyzeRequest(
        study_area="custom",
        aoi_geometry=_indus_polygon(),
        start_date="2020-01-01",
        end_date="2020-04-01",
    )

    class StubService:
        def run_live_summary_for_custom_aoi(self, study_area_id, study_area_name, aoi_geometry, start_date, end_date):
            return CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area={"id": "custom", "name": "Custom AOI"},
                date_range={"start_date": "2020-01-01", "end_date": "2020-04-01"},
                datasets=[],
                results=None,
                methodology=None,
                warning="Google Earth Engine is not connected.",
                aoi_geometry=aoi_geometry,
            )

    monkeypatch.setattr(analysis_service, "_get_gee_service", lambda: StubService())

    with pytest.raises(HTTPException) as exc:
        analysis_service.run_custom_aoi_analysis(request)
    assert exc.value.status_code == 503


def test_live_mode_500_message_is_safe(monkeypatch):
    request = AnalyzeRequest(
        study_area="custom",
        aoi_geometry=_indus_polygon(),
        start_date="2020-01-01",
        end_date="2020-04-01",
    )

    class StubService:
        def run_live_summary_for_custom_aoi(self, study_area_id, study_area_name, aoi_geometry, start_date, end_date):
            return CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area={"id": "custom", "name": "Custom AOI"},
                date_range={"start_date": "2020-01-01", "end_date": "2020-04-01"},
                datasets=[],
                results=None,
                methodology=None,
                warning="Traceback with credential path C:\\secret\\gee.json",
                aoi_geometry=aoi_geometry,
            )

    monkeypatch.setattr(analysis_service, "_get_gee_service", lambda: StubService())

    with pytest.raises(HTTPException) as exc:
        analysis_service.run_custom_aoi_analysis(request)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Earth Engine carbon stock processing failed."


def test_live_mode_preserves_no_data_as_defined_response(monkeypatch):
    request = AnalyzeRequest(
        study_area="custom",
        aoi_geometry=_abu_dhabi_polygon(),
        start_date="2020-01-01",
        end_date="2020-04-01",
    )

    class StubService:
        def run_live_summary_for_custom_aoi(self, study_area_id, study_area_name, aoi_geometry, start_date, end_date):
            return CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area={"id": "custom", "name": "Custom AOI"},
                date_range={"start_date": "2020-01-01", "end_date": "2020-04-01"},
                datasets=["GEDI L2A RH98", "GMW 2020"],
                results=None,
                methodology=None,
                warning="No GEDI data available for the AOI and date range.",
                aoi_geometry=aoi_geometry,
            )

    monkeypatch.setattr(analysis_service, "_get_gee_service", lambda: StubService())

    response = analysis_service.run_custom_aoi_analysis(request)
    assert response.mode == "live_earth_engine_custom_aoi"
    assert response.results is None
    assert "No GEDI data available" in response.warning


def test_fixed_and_custom_paths_share_analysis_image_builder():
    source = inspect.getsource(GeeCarbonStockService)
    assert source.count("_build_analysis_image(") >= 2


def test_build_analysis_image_uses_single_masked_rh98_input(monkeypatch):
    service = GeeCarbonStockService()
    calls = {}

    class FakeImage:
        def clip(self, _):
            return self

        def updateMask(self, _):
            return self

        def select(self, _):
            return self

        def mask(self):
            return self

        def rename(self, _):
            return self

        def multiply(self, _):
            return self

        def addBands(self, _):
            return self

    class FakeCollection:
        def map(self, fn):
            calls["map_fn"] = fn
            return self

        def mosaic(self):
            return FakeImage()

    def fake_build_biomass(masked_rh98_image):
        calls["arg"] = masked_rh98_image
        return FakeImage()

    monkeypatch.setattr(stock_module, "build_biomass_image_stack", fake_build_biomass)
    analysis_image = service._build_analysis_image(
        collection=FakeCollection(),
        geometry=object(),
        gmw_mask=object(),
        pixel_area_ha=FakeImage(),
    )
    assert "arg" in calls
    assert calls["arg"] is not None
    assert analysis_image is not None


def test_custom_pipeline_logs_original_exception_and_returns_safe_message(monkeypatch):
    service = GeeCarbonStockService()
    polygon = _indus_polygon()
    log_calls = {"count": 0}

    monkeypatch.setattr(
        stock_module.gee_service_module,
        "gee_service",
        SimpleNamespace(get_connection_context=lambda: SimpleNamespace(enabled=True, connected=True)),
    )
    monkeypatch.setattr(service, "_geojson_polygon_to_ee_geometry", lambda _: {"geometry": "ok"})

    def boom(*args, **kwargs):
        raise TypeError("build_biomass_image_stack() takes 1 positional argument but 2 were given")

    monkeypatch.setattr(service, "_run_live_summary_parameterized", boom)
    monkeypatch.setattr(stock_module.logger, "exception", lambda *args, **kwargs: log_calls.__setitem__("count", log_calls["count"] + 1))

    response = service.run_live_summary_for_custom_aoi(
        "custom", "Custom AOI", polygon, "2020-01-01", "2020-04-01"
    )
    assert response.results is None
    assert "failed" in response.warning.lower()
    assert log_calls["count"] >= 1


# ---------------------------------------------------------------------------
# Custom AOI audit: fingerprint, cache isolation, no-demo-leak
# ---------------------------------------------------------------------------


def test_processing_fingerprint_is_methodology_only():
    """The fingerprint must not embed a region-specific GMW asset ID."""
    from app.core.gee_datasets import GMW_2020_INDUS, GMW_2020_ABU_DHABI, GMW_GLOBAL_2020_COLLECTION
    service = GeeCarbonStockService()
    fp = service._processing_version_fingerprint()
    # Fingerprint is a hex SHA-256 string
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)
    # Verify the underlying payload does NOT contain any region-specific asset ID by
    # constructing it fresh and checking the JSON string
    import json, hashlib
    from app.core.gee_datasets import (
        GEDI_L2A_MONTHLY, GMW_VALIDATED_MASK_BAND, GMW_AREA_SCALE_M, GEDI_RH98_SCALE_M,
    )
    payload = {
        "dataset": GEDI_L2A_MONTHLY,
        "gedi_band": "rh98",
        "gmw_band": GMW_VALIDATED_MASK_BAND,
        "gmw_scale_m": GMW_AREA_SCALE_M,
        "gedi_scale_m": GEDI_RH98_SCALE_M,
        "height_to_agb_formula": "AGB = 10 × RH98",
        "bgb_formula": "BGB = 0.49 × AGB",
        "carbon_formula": "Carbon = 0.5 × (AGB + BGB)",
        "quality_mask": "quality_flag=1 and degrade_flag=0",
        "aggregation_method": "mosaic",
        "best_effort": False,
        "pixel_area": "ee.Image.pixelArea()/10000",
    }
    as_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256(as_json.encode("utf-8")).hexdigest()
    assert fp == expected
    # None of the region asset IDs appear in the payload JSON
    assert GMW_2020_INDUS not in as_json
    assert GMW_2020_ABU_DHABI not in as_json
    assert GMW_GLOBAL_2020_COLLECTION not in as_json


def test_processing_fingerprint_includes_aggregation_and_best_effort():
    """Fingerprint must encode aggregation_method and best_effort."""
    import json, hashlib
    from app.core.gee_datasets import (
        GEDI_L2A_MONTHLY, GMW_VALIDATED_MASK_BAND, GMW_AREA_SCALE_M, GEDI_RH98_SCALE_M,
    )
    # Build a variant with best_effort=True — should produce a different fingerprint
    payload_true = {
        "dataset": GEDI_L2A_MONTHLY,
        "gedi_band": "rh98",
        "gmw_band": GMW_VALIDATED_MASK_BAND,
        "gmw_scale_m": GMW_AREA_SCALE_M,
        "gedi_scale_m": GEDI_RH98_SCALE_M,
        "height_to_agb_formula": "AGB = 10 × RH98",
        "bgb_formula": "BGB = 0.49 × AGB",
        "carbon_formula": "Carbon = 0.5 × (AGB + BGB)",
        "quality_mask": "quality_flag=1 and degrade_flag=0",
        "aggregation_method": "mosaic",
        "best_effort": True,
        "pixel_area": "ee.Image.pixelArea()/10000",
    }
    as_json_true = json.dumps(payload_true, sort_keys=True, separators=(",", ":"))
    fp_best_effort_true = hashlib.sha256(as_json_true.encode("utf-8")).hexdigest()

    service = GeeCarbonStockService()
    fp_production = service._processing_version_fingerprint()

    assert fp_production != fp_best_effort_true, (
        "Fingerprint must change when best_effort changes"
    )


def test_cache_key_changes_with_different_gmw_asset():
    """Different GMW asset IDs must produce different cache keys."""
    service = GeeCarbonStockService()
    polygon = _indus_polygon()
    key_indus = service._make_custom_aoi_cache_key(polygon, "2020-01-01", "2020-04-01", "projects/mangroves123/assets/GMW_2020_IndusDelta")
    key_global = service._make_custom_aoi_cache_key(polygon, "2020-01-01", "2020-04-01", "projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020")
    key_abu = service._make_custom_aoi_cache_key(polygon, "2020-01-01", "2020-04-01", "projects/mangroves123/assets/GMW_2020_AbuDhabi_v2")

    assert key_indus != key_global
    assert key_indus != key_abu
    assert key_global != key_abu


def test_cache_key_includes_start_and_end_date():
    """Both start_date and end_date must be captured in the cache key."""
    service = GeeCarbonStockService()
    polygon = _indus_polygon()
    base = service._make_custom_aoi_cache_key(polygon, "2020-01-01", "2020-04-01")
    diff_start = service._make_custom_aoi_cache_key(polygon, "2021-01-01", "2020-04-01")
    diff_end = service._make_custom_aoi_cache_key(polygon, "2020-01-01", "2021-04-01")

    assert base != diff_start
    assert base != diff_end
    assert diff_start != diff_end


def test_fingerprint_change_invalidates_cache_key():
    """Cache key must change when the processing fingerprint changes."""
    service = GeeCarbonStockService()
    polygon = _indus_polygon()

    key_real = service._make_custom_aoi_cache_key(polygon, "2020-01-01", "2020-04-01", "asset-x")

    # Patch the fingerprint to a different value
    service._processing_version_fingerprint = lambda: "different-fingerprint"
    key_patched = service._make_custom_aoi_cache_key(polygon, "2020-01-01", "2020-04-01", "asset-x")

    assert key_real != key_patched


def test_custom_aoi_response_cannot_carry_demo_results(monkeypatch):
    """run_custom_aoi_analysis must never return mode='demonstration'."""
    request = AnalyzeRequest(
        study_area="custom",
        aoi_geometry=_indus_polygon(),
        start_date="2020-01-01",
        end_date="2020-04-01",
    )

    class StubService:
        def run_live_summary_for_custom_aoi(self, study_area_id, study_area_name, aoi_geometry, start_date, end_date):
            return CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area={"id": "custom", "name": "Custom AOI"},
                date_range={"start_date": "2020-01-01", "end_date": "2020-04-01"},
                datasets=["GEDI L2A RH98", "GMW 2020"],
                results=None,
                methodology=None,
                warning="No GEDI data available for the AOI and date range.",
                aoi_geometry=aoi_geometry,
            )

    monkeypatch.setattr(analysis_service, "_get_gee_service", lambda: StubService())
    response = analysis_service.run_custom_aoi_analysis(request)
    assert response.mode == "live_earth_engine_custom_aoi"
    assert response.mode != "demonstration"


def test_run_analysis_routes_by_aoi_geometry_presence(monkeypatch):
    """Requests with aoi_geometry must never reach run_demonstration_analysis."""
    demo_called = {"count": 0}
    original_demo = analysis_service.run_demonstration_analysis

    def patched_demo(req):
        demo_called["count"] += 1
        return original_demo(req)

    monkeypatch.setattr(analysis_service, "run_demonstration_analysis", patched_demo)

    class StubService:
        def run_live_summary_for_custom_aoi(self, *args, **kwargs):
            return CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area={"id": "custom", "name": "Custom AOI"},
                date_range={"start_date": "2020-01-01", "end_date": "2020-04-01"},
                datasets=[],
                results=None,
                methodology=None,
                warning="No GEDI data available for the AOI and date range.",
                aoi_geometry=args[2] if len(args) > 2 else {},
            )

    monkeypatch.setattr(analysis_service, "_get_gee_service", lambda: StubService())

    request = AnalyzeRequest(
        study_area="custom",
        aoi_geometry=_indus_polygon(),
        start_date="2020-01-01",
        end_date="2020-04-01",
    )
    analysis_service.run_analysis(request)
    assert demo_called["count"] == 0, "run_demonstration_analysis must not be called when aoi_geometry is present"


def test_demo_results_not_reachable_via_custom_aoi_endpoint(monkeypatch):
    """Confirm DEMO_RESULTS values (hard-coded Indus constants) cannot appear in a live response."""
    from app.services.analysis_service import DEMO_RESULTS

    class StubService:
        def run_live_summary_for_custom_aoi(self, *args, **kwargs):
            return CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area={"id": "custom", "name": "Custom AOI"},
                date_range={"start_date": "2020-01-01", "end_date": "2020-04-01"},
                datasets=[],
                results=None,
                methodology=None,
                warning="No GEDI data available for the AOI and date range.",
                aoi_geometry=_indus_polygon(),
            )

    monkeypatch.setattr(analysis_service, "_get_gee_service", lambda: StubService())

    request = AnalyzeRequest(
        study_area="custom",
        aoi_geometry=_indus_polygon(),
        start_date="2020-01-01",
        end_date="2020-04-01",
    )
    response = analysis_service.run_analysis(request)
    assert response.mode == "live_earth_engine_custom_aoi"
    # No DEMO_RESULTS fields can appear
    assert response.results is None or response.results != DEMO_RESULTS


def test_custom_aoi_study_area_label_does_not_leak_indus_name(monkeypatch):
    """Custom AOI responses must never carry the Indus Delta study-area name."""
    service = GeeCarbonStockService()
    polygon = _indus_polygon()

    monkeypatch.setattr(
        stock_module.gee_service_module,
        "gee_service",
        SimpleNamespace(get_connection_context=lambda: SimpleNamespace(enabled=True, connected=True)),
    )
    monkeypatch.setattr(service, "_geojson_polygon_to_ee_geometry", lambda _: {"geometry": "ok"})

    def fake_run(*args, **kwargs):
        return _CarbonStockResult(response=_valid_results_dict(), is_success=True)

    monkeypatch.setattr(service, "_run_live_summary_parameterized", fake_run)

    response = service.run_live_summary_for_custom_aoi(
        "custom", "Custom AOI", polygon, "2020-01-01", "2020-04-01"
    )
    assert response.study_area.id == "custom"
    assert "Indus" not in response.study_area.name
    assert "Pakistan" not in response.study_area.name
