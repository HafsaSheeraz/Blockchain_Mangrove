from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.gee_datasets import (
    GEDI_L2A_MONTHLY,
    GEDI_RH98_BASELINE_END_DATE,
    GEDI_RH98_BASELINE_START_DATE,
    GEDI_RH98_COMPARISON_ASSET_ID,
    GMW_2020,
    GMW_VALIDATED_MASK_BAND,
)
from app.main import app
from app.services import gee_mask_service as mask_service_module
from app.services import gee_rh98_summary_service as summary_service_module
from app.services.gee_service import GeeConnectionContext, GeeSettings


class _FakeValue:
    def __init__(self, value=None, error: Exception | None = None):
        self._value = value
        self._error = error

    def getInfo(self):
        if self._error is not None:
            raise self._error
        return self._value


class _FakeReducer:
    def __init__(self, names: list[str]):
        self.names = names

    def combine(self, reducer2, sharedInputs=True):
        return _FakeReducer(self.names + reducer2.names)


class _FakeReducerFactory:
    @staticmethod
    def min():
        return _FakeReducer(["min"])

    @staticmethod
    def mean():
        return _FakeReducer(["mean"])

    @staticmethod
    def max():
        return _FakeReducer(["max"])

    @staticmethod
    def count():
        return _FakeReducer(["count"])


class _FakeMaskExpression:
    def __init__(self, conditions: list[tuple[str, int]]):
        self.conditions = conditions

    def And(self, other):
        return _FakeMaskExpression(self.conditions + other.conditions)


class _FakeBandForEq:
    def __init__(self, image, band_name: str):
        self.image = image
        self.band_name = band_name

    def eq(self, value):
        self.image.eq_checks.append((self.band_name, value))
        return _FakeMaskExpression([(self.band_name, value)])


class _FakeRh98Band:
    def __init__(self, image):
        self.image = image

    def updateMask(self, mask_expression):
        self.image.update_mask_conditions = list(mask_expression.conditions)
        return self.image


class _FakeQualityProbeImage:
    def __init__(self):
        self.eq_checks: list[tuple[str, int]] = []
        self.select_calls: list[str] = []
        self.update_mask_conditions: list[tuple[str, int]] = []

    def select(self, bands):
        band = bands[0]
        self.select_calls.append(band)
        if band == "rh98":
            return _FakeRh98Band(self)
        return _FakeBandForEq(self, band)


class _FakeImageWithMetadata:
    def __init__(self, bands: list[str], projection=None):
        self._bands = bands
        self._projection = projection or {"crs": "EPSG:4326", "transform": [1, 0, 0, 0, -1, 0]}
        self.selected_bands: list[str] = []
        self.gt_called = False
        self.self_mask_called = False

    def bandNames(self):
        return _FakeValue(self._bands)

    def projection(self):
        return _FakeValue(self._projection)

    def select(self, bands):
        self.selected_bands = list(bands)
        return self

    def gt(self, _value):
        self.gt_called = True
        return self

    def selfMask(self):
        self.self_mask_called = True
        return self


class _FakeFirstImage:
    def __init__(self, bands: list[str]):
        self._bands = bands

    def bandNames(self):
        return _FakeValue(self._bands)


class _FakeRaster:
    def __init__(self, ee, label: str):
        self.ee = ee
        self.label = label

    def clip(self, _geometry):
        return self

    def updateMask(self, _mask):
        self.ee.mask_update_called = True
        return _FakeRaster(self.ee, "mangrove_masked")

    def reduceRegion(self, *, reducer, geometry, scale, maxPixels, tileScale, bestEffort):
        self.ee.reduce_calls.append(
            {
                "label": self.label,
                "reducer_names": getattr(reducer, "names", []),
                "geometry": geometry,
                "scale": scale,
                "maxPixels": maxPixels,
                "tileScale": tileScale,
                "bestEffort": bestEffort,
            }
        )
        if self.ee.reduce_error is not None:
            raise self.ee.reduce_error
        return _FakeValue(self.ee.reduce_outputs[self.label])


class _FakeMappedCollection:
    def __init__(self, ee):
        self.ee = ee

    def mosaic(self):
        self.ee.mosaic_called = True
        return _FakeRaster(self.ee, "whole_aoi")


class _FakeCollection:
    def __init__(self, ee):
        self.ee = ee

    def filterBounds(self, geometry):
        self.ee.last_filter_bounds = geometry
        return self

    def filterDate(self, start_date, end_date):
        self.ee.last_filter_dates = (start_date, end_date)
        return self

    def size(self):
        return _FakeValue(self.ee.collection_size, self.ee.collection_size_error)

    def first(self):
        return _FakeFirstImage(self.ee.first_image_bands)

    def map(self, fn):
        self.ee.map_called = True
        fn(self.ee.quality_probe_image)
        return _FakeMappedCollection(self.ee)


class _FakeGeometry:
    @staticmethod
    def Rectangle(bounds):
        return {"type": "Rectangle", "bounds": bounds}


class _FakeData:
    def __init__(self, ee):
        self.ee = ee
        self.calls: list[str] = []

    def getAsset(self, asset_id):
        self.calls.append(asset_id)
        error = self.ee.asset_errors.get(asset_id)
        if error is not None:
            raise error
        return self.ee.asset_metadata_map.get(asset_id, {"type": "IMAGE"})


class _FakeEE:
    def __init__(
        self,
        *,
        collection_size=3,
        first_image_bands=None,
        gmw_bands=None,
        comparison_bands=None,
        comparison_projection=None,
        reduce_outputs=None,
        asset_metadata_map=None,
        asset_errors=None,
        collection_size_error=None,
        reduce_error=None,
    ):
        self.collection_size = collection_size
        self.first_image_bands = first_image_bands or ["rh98", "quality_flag", "degrade_flag"]
        self.reduce_outputs = reduce_outputs or {
            "whole_aoi": {"rh98_min": 1.27, "rh98_mean": 2.466, "rh98_max": 98.04, "rh98_count": 905850},
            "mangrove_masked": {"rh98_min": 1.64, "rh98_mean": 3.369, "rh98_max": 16.77, "rh98_count": 30008},
        }
        self.asset_metadata_map = asset_metadata_map or {
            GMW_2020: {"type": "IMAGE"},
            GEDI_RH98_COMPARISON_ASSET_ID: {"type": "IMAGE"},
        }
        self.asset_errors = asset_errors or {}
        self.collection_size_error = collection_size_error
        self.reduce_error = reduce_error

        self.quality_probe_image = _FakeQualityProbeImage()
        self.gmw_image = _FakeImageWithMetadata(gmw_bands or ["b1"])
        self.comparison_image = _FakeImageWithMetadata(
            comparison_bands or ["rh98"],
            projection=comparison_projection,
        )
        self.Geometry = _FakeGeometry
        self.Reducer = _FakeReducerFactory
        self.data = _FakeData(self)

        self.last_collection_dataset_id = None
        self.last_filter_bounds = None
        self.last_filter_dates = None
        self.map_called = False
        self.mosaic_called = False
        self.mask_update_called = False
        self.reduce_calls: list[dict] = []

    def ImageCollection(self, dataset_id):
        self.last_collection_dataset_id = dataset_id
        return _FakeCollection(self)

    def Image(self, image_input):
        if isinstance(image_input, str):
            if image_input == GMW_2020:
                return self.gmw_image
            if image_input == GEDI_RH98_COMPARISON_ASSET_ID:
                return self.comparison_image
        return image_input


def _connection_context(*, enabled=True, connected=True, status="connected", message=None):
    return GeeConnectionContext(
        enabled=enabled,
        connected=connected,
        status=status,
        message=message,
        project_id="demo-gee-project" if connected else None,
        settings=GeeSettings(
            enabled=enabled,
            project_id="demo-gee-project",
            service_account_email="svc@example.iam.gserviceaccount.com",
            private_key_file="secrets/gee-service-account.json",
            backend_dir=Path("D:/MangroveCarbonApp/backend"),
        ),
    )


def _set_connected(monkeypatch):
    monkeypatch.setattr(
        summary_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(),
    )


def _set_fake_ee(monkeypatch, fake_ee: _FakeEE):
    monkeypatch.setattr(summary_service_module, "ee", fake_ee)
    monkeypatch.setattr(mask_service_module, "ee", fake_ee)


def _reset_summary_cache():
    summary_service_module.gee_rh98_summary_service._cached_success_response = None


def test_quality_filter_function_is_reusable_and_correct():
    image = _FakeQualityProbeImage()
    output = summary_service_module.apply_gedi_quality_filters(image)
    assert output is image
    assert image.select_calls == ["quality_flag", "degrade_flag", "rh98"]
    assert image.update_mask_conditions == [("quality_flag", 1), ("degrade_flag", 0)]


@pytest.mark.asyncio
async def test_rh98_summary_uses_jan_mar_2020_end_exclusive_dates(monkeypatch):
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body = response.json()
    assert fake_ee.last_filter_dates == (GEDI_RH98_BASELINE_START_DATE, GEDI_RH98_BASELINE_END_DATE)
    assert body["date_range"]["start_date"] == "2020-01-01"
    assert body["date_range"]["end_date"] == "2020-04-01"
    assert body["date_range"]["filter_convention"] == "end_exclusive"
    assert body["filtered_monthly_image_count"] == 3


@pytest.mark.asyncio
async def test_rh98_summary_preserves_quality_mask_mosaic_and_scale(monkeypatch):
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/rh98/summary")

    assert fake_ee.map_called is True
    assert fake_ee.mosaic_called is True
    assert fake_ee.mask_update_called is True
    assert fake_ee.quality_probe_image.update_mask_conditions == [("quality_flag", 1), ("degrade_flag", 0)]
    assert all(call["scale"] == 25 for call in fake_ee.reduce_calls)
    assert all(call["bestEffort"] is False for call in fake_ee.reduce_calls)


@pytest.mark.asyncio
async def test_reference_values_are_reported_but_do_not_replace_live_values(monkeypatch):
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        reduce_outputs={
            "whole_aoi": {"rh98_min": 10.0, "rh98_mean": 11.0, "rh98_max": 12.0, "rh98_count": 50000},
            "mangrove_masked": {"rh98_min": 20.0, "rh98_mean": 21.0, "rh98_max": 22.0, "rh98_count": 2000},
        }
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body = response.json()
    assert body["baseline_purpose"] == "reproduce_jan_mar_2020_reference"
    assert body["whole_aoi"]["rh98_mean_m"] == 11.0
    assert body["reference_results"]["whole_aoi"]["rh98_mean_m"] == 2.57
    assert body["reference_results"]["mangrove_masked"]["valid_gedi_raster_pixel_count"] == 1130


@pytest.mark.asyncio
async def test_difference_from_reference_is_calculated_per_stat(monkeypatch):
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        reduce_outputs={
            "whole_aoi": {"rh98_min": 1.52, "rh98_mean": 2.67, "rh98_max": 15.75, "rh98_count": 42298},
            "mangrove_masked": {"rh98_min": 2.49, "rh98_mean": 3.19, "rh98_max": 5.96, "rh98_count": 1140},
        }
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    diff = response.json()["difference_from_reference"]
    assert round(diff["whole_aoi"]["rh98_mean_m"], 2) == 0.10
    assert diff["whole_aoi"]["valid_gedi_raster_pixel_count"] == 100
    assert round(diff["mangrove_masked"]["rh98_max_m"], 2) == 0.20
    assert diff["mangrove_masked"]["valid_gedi_raster_pixel_count"] == 10


@pytest.mark.asyncio
async def test_outlier_and_substantial_count_difference_warnings(monkeypatch):
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    warnings = response.json()["warnings"]
    assert any("Whole-AOI RH98 max exceeds 50 m" in warning for warning in warnings)
    assert any("Mangrove-masked RH98 max exceeds 15 m" in warning for warning in warnings)
    assert any("Whole-AOI valid GEDI raster pixel count differs substantially" in warning for warning in warnings)
    assert any("Mangrove-masked valid GEDI raster pixel count differs substantially" in warning for warning in warnings)


@pytest.mark.asyncio
async def test_comparison_asset_metadata_accessible(monkeypatch):
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        comparison_bands=["rh98"],
        comparison_projection={"crs": "EPSG:4326", "transform": [0.00025, 0, 0, 0, -0.00025, 0]},
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    comparison_asset = response.json()["comparison_asset"]
    assert comparison_asset["asset_id"] == GEDI_RH98_COMPARISON_ASSET_ID
    assert comparison_asset["accessible"] is True
    assert comparison_asset["asset_type"] == "IMAGE"
    assert comparison_asset["band_names"] == ["rh98"]
    assert comparison_asset["projection"]["crs"] == "EPSG:4326"


@pytest.mark.asyncio
async def test_comparison_asset_metadata_inaccessible(monkeypatch):
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(asset_errors={GEDI_RH98_COMPARISON_ASSET_ID: RuntimeError("asset not found")})
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    comparison_asset = response.json()["comparison_asset"]
    assert comparison_asset["asset_id"] == GEDI_RH98_COMPARISON_ASSET_ID
    assert comparison_asset["accessible"] is False
    assert "message" in comparison_asset


@pytest.mark.asyncio
async def test_rh98_summary_has_no_biomass_or_carbon_fields(monkeypatch):
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/rh98/summary")).json()

    body_text = str(body).lower()
    assert "agb" not in body_text
    assert "bgb" not in body_text
    assert "carbon" not in body_text


@pytest.mark.asyncio
async def test_rh98_summary_cache_still_only_persists_success(monkeypatch):
    _reset_summary_cache()
    _set_connected(monkeypatch)
    failing_ee = _FakeEE(reduce_error=RuntimeError("timeout"))
    _set_fake_ee(monkeypatch, failing_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/api/gee/rh98/summary")
    assert first.json()["status"] == "processing_failed"

    success_ee = _FakeEE()
    _set_fake_ee(monkeypatch, success_ee)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        second = await client.get("/api/gee/rh98/summary")
        third = await client.get("/api/gee/rh98/summary")

    assert second.json()["status"] in {"connected", "masked_result_empty", "no_valid_rh98_pixels"}
    assert third.json()["status"] == second.json()["status"]
    assert len(success_ee.reduce_calls) == 2


# ---------------------------------------------------------------------------
# Restored Module 8 coverage tests (adapted for Module 8.1 _FakeEE interface)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rh98_summary_success_response_structure(monkeypatch):
    """Success path includes mode, gmw_mask dict, processing_performed and warnings."""
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        reduce_outputs={
            "whole_aoi": {"rh98_min": 1.42, "rh98_mean": 2.57, "rh98_max": 15.55, "rh98_count": 42198},
            "mangrove_masked": {"rh98_min": 2.39, "rh98_mean": 3.09, "rh98_max": 5.76, "rh98_count": 1130},
        }
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["mode"] == "live_earth_engine"
    assert body["processing_performed"] is True
    assert body["gmw_mask"]["asset_id"] == GMW_2020
    assert body["gmw_mask"]["band"] == GMW_VALIDATED_MASK_BAND
    assert body["gmw_mask"]["positive_pixels_only"] is True
    assert isinstance(body["warnings"], list)
    assert len(body["warnings"]) >= 3


@pytest.mark.asyncio
async def test_rh98_summary_correct_dataset_id_and_bounds(monkeypatch):
    """Collection is built from GEDI_L2A_MONTHLY and filtered by the configured AOI geometry."""
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        reduce_outputs={
            "whole_aoi": {"rh98_min": 1.42, "rh98_mean": 2.57, "rh98_max": 15.55, "rh98_count": 42198},
            "mangrove_masked": {"rh98_min": 2.39, "rh98_mean": 3.09, "rh98_max": 5.76, "rh98_count": 1130},
        }
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/rh98/summary")

    assert fake_ee.last_collection_dataset_id == GEDI_L2A_MONTHLY
    assert fake_ee.last_filter_bounds is not None
    assert GMW_2020 in fake_ee.data.calls


@pytest.mark.asyncio
async def test_rh98_summary_combined_reducer_stats_values(monkeypatch):
    """Stats values are read from reduce outputs; combined reducer uses min/mean/max/count at tileScale 4."""
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        reduce_outputs={
            "whole_aoi": {"rh98_min": 1.42, "rh98_mean": 2.57, "rh98_max": 15.55, "rh98_count": 42198},
            "mangrove_masked": {"rh98_min": 2.39, "rh98_mean": 3.09, "rh98_max": 5.76, "rh98_count": 1130},
        }
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body = response.json()
    assert body["whole_aoi"]["rh98_min_m"] == 1.42
    assert body["whole_aoi"]["rh98_mean_m"] == 2.57
    assert body["whole_aoi"]["rh98_max_m"] == 15.55
    assert body["whole_aoi"]["valid_gedi_raster_pixel_count"] == 42198
    assert body["mangrove_masked"]["rh98_mean_m"] == 3.09
    assert body["mangrove_masked"]["valid_gedi_raster_pixel_count"] == 1130

    assert len(fake_ee.reduce_calls) == 2
    reducer_names = fake_ee.reduce_calls[0]["reducer_names"]
    assert "min" in reducer_names
    assert "mean" in reducer_names
    assert "max" in reducer_names
    assert "count" in reducer_names
    assert fake_ee.reduce_calls[0]["tileScale"] == 4


@pytest.mark.asyncio
async def test_rh98_summary_zero_values_preserved(monkeypatch):
    """Numeric zero values in reducer output are preserved as 0.0, not coerced to null."""
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        reduce_outputs={
            "whole_aoi": {"rh98_min": 0.0, "rh98_mean": 0.0, "rh98_max": 0.0, "rh98_count": 500},
            "mangrove_masked": {"rh98_min": 0.0, "rh98_mean": 0.0, "rh98_max": 0.0, "rh98_count": 50},
        }
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body = response.json()
    assert body["whole_aoi"]["rh98_min_m"] == 0.0
    assert body["whole_aoi"]["rh98_mean_m"] == 0.0
    assert body["whole_aoi"]["rh98_max_m"] == 0.0
    assert body["whole_aoi"]["valid_gedi_raster_pixel_count"] == 500
    assert body["mangrove_masked"]["rh98_min_m"] == 0.0


@pytest.mark.asyncio
async def test_rh98_summary_missing_values_return_null(monkeypatch):
    """Reducer output with None values serializes as JSON null (response_model_exclude_none is not set)."""
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        reduce_outputs={
            "whole_aoi": {"rh98_min": None, "rh98_mean": None, "rh98_max": None, "rh98_count": None},
            "mangrove_masked": {"rh98_min": None, "rh98_mean": None, "rh98_max": None, "rh98_count": None},
        }
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body = response.json()
    assert body["whole_aoi"]["rh98_min_m"] is None
    assert body["whole_aoi"]["rh98_mean_m"] is None
    assert body["whole_aoi"]["rh98_max_m"] is None
    assert body["whole_aoi"]["valid_gedi_raster_pixel_count"] is None
    assert body["mangrove_masked"]["rh98_mean_m"] is None


@pytest.mark.asyncio
async def test_rh98_summary_empty_collection(monkeypatch):
    """Empty GEDI collection returns status empty_collection with processing_performed=False."""
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(collection_size=0)
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body = response.json()
    assert body["status"] == "empty_collection"
    assert body["processing_performed"] is False
    assert body["filtered_monthly_image_count"] == 0


@pytest.mark.asyncio
async def test_rh98_summary_empty_masked_result(monkeypatch):
    """Zero mangrove-masked pixel count returns status masked_result_empty; whole-AOI stats are intact."""
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        reduce_outputs={
            "whole_aoi": {"rh98_min": 1.5, "rh98_mean": 2.5, "rh98_max": 10.0, "rh98_count": 100},
            "mangrove_masked": {"rh98_min": None, "rh98_mean": None, "rh98_max": None, "rh98_count": 0},
        }
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body = response.json()
    assert body["status"] == "masked_result_empty"
    assert body["mangrove_masked"]["rh98_min_m"] is None
    assert body["mangrove_masked"]["valid_gedi_raster_pixel_count"] == 0
    assert body["whole_aoi"]["rh98_mean_m"] == 2.5


@pytest.mark.asyncio
async def test_rh98_summary_missing_required_band(monkeypatch):
    """Missing degrade_flag band returns status missing_required_bands with an informative message."""
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(first_image_bands=["rh98", "quality_flag"])  # degrade_flag absent
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body = response.json()
    assert body["status"] == "missing_required_bands"
    assert body["processing_performed"] is False
    assert "degrade_flag" in body["message"]


@pytest.mark.asyncio
async def test_rh98_summary_quota_error(monkeypatch):
    """Quota or restricted-mode error during reduceRegion returns status processing_failed."""
    _reset_summary_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(reduce_error=RuntimeError("Noncommercial quota restricted for this project."))
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body = response.json()
    assert body["status"] == "processing_failed"
    assert body["connected"] is True
    assert "quota" in body["message"].lower() or "restricted" in body["message"].lower()


@pytest.mark.asyncio
async def test_rh98_summary_authentication_failure(monkeypatch):
    """Authentication failure returns connected=False without making Earth Engine calls."""
    _reset_summary_cache()
    monkeypatch.setattr(
        summary_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(
            enabled=True,
            connected=False,
            status="authentication_failed",
            message="Service account authentication failed.",
        ),
    )
    fake_ee = _FakeEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body = response.json()
    assert body["connected"] is False
    assert body["status"] == "authentication_failed"
    assert body["processing_performed"] is False


@pytest.mark.asyncio
async def test_rh98_summary_no_secret_or_path_leakage(monkeypatch):
    """Internal file paths in exception messages must not appear in the API response."""
    _reset_summary_cache()
    _set_connected(monkeypatch)
    secret_path = "/home/user/secrets/gee-service-account.json"
    fake_ee = _FakeEE(reduce_error=RuntimeError(f"Error opening file {secret_path}: permission denied"))
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/rh98/summary")

    body_text = response.text
    assert secret_path not in body_text
    assert "/home/user" not in body_text
    assert "gee-service-account" not in body_text
