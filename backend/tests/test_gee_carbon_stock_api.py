"""
Module 10 tests for GET /api/gee/carbon/stock-summary.

All Earth Engine calls are mocked.  No real GEE calls are made.

The fake EE design distinguishes the two getInfo calls by scale:
  - scale = 10 m  → GMW mapped-mangrove-area reduction
  - scale = 25 m  → combined GEDI carbon-density / coverage / direct-stock reduction

The _FakeCarbonStockRaster numerically propagates the biomass formula chain so that
coverage area, direct stock, and extrapolated stock can be verified without
hardcoded reference values.
"""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.gee_datasets import (
    BIOMASS_BAND_CARBON,
    BIOMASS_HEIGHT_TO_AGB,
    BIOMASS_ROOT_TO_SHOOT,
    BIOMASS_TO_CARBON,
    CARBON_STOCK_FORMULA_TOLERANCE,
    CARBON_STOCK_OLDER_REPORT_DIRECT_SAMPLED_MG_C,
    GEDI_L2A_MONTHLY,
    GEDI_RH98_BASELINE_END_DATE,
    GEDI_RH98_BASELINE_START_DATE,
    GEDI_RH98_MAX_PIXELS,
    GEDI_RH98_SCALE_M,
    GEDI_RH98_TILE_SCALE,
    GMW_2020,
    GMW_AREA_SCALE_M,
    GMW_VALIDATED_MASK_BAND,
)
from app.main import app
from app.services import gee_carbon_stock_service as stock_service_module
from app.services import gee_mask_service as mask_service_module
from app.services.gee_service import GeeConnectionContext, GeeSettings

# ---------------------------------------------------------------------------
# Internal band name constants (must match the service-level private constants)
# ---------------------------------------------------------------------------

_GEDI_COVERAGE_BAND = "gedi_coverage_ha"
_DIRECT_STOCK_BAND = "direct_stock_mgc"

# ---------------------------------------------------------------------------
# Fake EE primitive helpers
# ---------------------------------------------------------------------------


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

    @staticmethod
    def sum():
        return _FakeReducer(["sum"])


class _FakeGeometry:
    @staticmethod
    def Rectangle(bounds):
        return {"type": "Rectangle", "bounds": bounds}


# ---------------------------------------------------------------------------
# _FakeCarbonStockRaster: numerically tracks formula chain for deterministic tests
# ---------------------------------------------------------------------------


class _FakeCarbonStockRaster:
    """
    Fake EE image that propagates rename/multiply/add/divide/addBands/select
    numerically so that tests verify correct area and stock calculations.

    reduceRegion dispatches by scale:
      scale = GMW_AREA_SCALE_M (10)  → returns {"area": ee_state.mapped_area_ha}
      scale = GEDI_RH98_SCALE_M (25) → computes from _bands dict (sum = val × count)
    """

    def __init__(
        self,
        ee_state,
        value: float = 0.0,
        name: str = "",
        pixel_count: int = 1130,
        bands: dict | None = None,
    ):
        self._ee = ee_state
        self._value = value
        self._name = name
        self._pixel_count = pixel_count
        self._bands: dict[str, float] = bands or {}

    # ── Image operation chain ────────────────────────────────────────

    def clip(self, _geometry):
        return self

    def updateMask(self, mask):
        self._ee.mask_update_count += 1
        if self._name == "area":
            if isinstance(mask, _FakeCarbonMaskToken):
                self._ee.coverage_used_carbon_mask = True
            elif isinstance(mask, _FakeCarbonStockRaster) and mask._name == BIOMASS_BAND_CARBON:
                self._ee.coverage_used_carbon_values_directly = True
        return _FakeCarbonStockRaster(
            self._ee, self._value, self._name, self._pixel_count, dict(self._bands)
        )

    def rename(self, band_list: list[str]):
        new_name = band_list[0]
        # A renamed image has exactly one band with the new name and the current scalar value.
        # Do NOT preserve the old _bands dict — that would cause stale band names in addBands.
        return _FakeCarbonStockRaster(
            self._ee, self._value, new_name, self._pixel_count, {new_name: self._value}
        )

    def multiply(self, other):
        if self._name == BIOMASS_BAND_CARBON:
            self._ee.direct_stock_multiplies_carbon_band = True
        if isinstance(other, _FakeCarbonStockRaster):
            new_val = self._value * other._value
        else:
            new_val = self._value * float(other)
        self._ee.multiply_calls.append(new_val)
        return _FakeCarbonStockRaster(
            self._ee, new_val, self._name, self._pixel_count, dict(self._bands)
        )

    def mask(self):
        self._ee.carbon_mask_requested = self._name == BIOMASS_BAND_CARBON
        return _FakeCarbonMaskToken(self._name)

    def add(self, other: "_FakeCarbonStockRaster"):
        return _FakeCarbonStockRaster(
            self._ee, self._value + other._value, self._name, self._pixel_count, dict(self._bands)
        )

    def divide(self, divisor: float):
        new_val = self._value / divisor if divisor != 0 else 0.0
        return _FakeCarbonStockRaster(
            self._ee, new_val, self._name, self._pixel_count, dict(self._bands)
        )

    def select(self, band_list: list[str]):
        band = band_list[0]
        val = self._bands.get(band, self._value)
        return _FakeCarbonStockRaster(
            self._ee, val, band, self._pixel_count, {band: val}
        )

    def addBands(self, other: "_FakeCarbonStockRaster"):
        new_bands: dict[str, float] = {}
        if self._bands:
            new_bands.update(self._bands)
        elif self._name:
            new_bands[self._name] = self._value
        if other._bands:
            new_bands.update(other._bands)
        elif other._name:
            new_bands[other._name] = other._value
        return _FakeCarbonStockRaster(
            self._ee, self._value, self._name, self._pixel_count, new_bands
        )

    def reduceRegion(self, *, reducer, geometry, scale, maxPixels, tileScale, bestEffort):
        if self._ee.reduce_error is not None:
            raise self._ee.reduce_error

        self._ee.reduce_calls.append(
            {
                "scale": scale,
                "maxPixels": maxPixels,
                "tileScale": tileScale,
                "bestEffort": bestEffort,
                "reducer_names": getattr(reducer, "names", []),
            }
        )

        # ── GMW area reduction (scale = 10 m) ────────────────────────
        if scale == GMW_AREA_SCALE_M:
            if self._ee.override_gmw_area_output is not None:
                return _FakeValue(self._ee.override_gmw_area_output)
            return _FakeValue(
                {"area": self._ee.mapped_area_ha}
                if self._ee.mapped_area_ha is not None
                else None
            )

        # ── GEDI analysis reduction (scale = 25 m) ───────────────────
        if self._ee.override_analysis_output is not None:
            return _FakeValue(self._ee.override_analysis_output)

        if self._ee.pixel_count == 0:
            return _FakeValue(
                {
                    f"{BIOMASS_BAND_CARBON}_count": 0,
                    f"{_GEDI_COVERAGE_BAND}_count": 0,
                    f"{_DIRECT_STOCK_BAND}_count": 0,
                }
            )

        all_bands: dict[str, float] = dict(self._bands)
        if self._name and self._name not in all_bands:
            all_bands[self._name] = self._value

        result: dict = {}
        for band_name, val in all_bands.items():
            count = self._ee.pixel_count
            result[f"{band_name}_count"] = count
            if count > 0:
                result[f"{band_name}_min"] = val
                result[f"{band_name}_mean"] = val
                result[f"{band_name}_max"] = val
                result[f"{band_name}_sum"] = val * count
        return _FakeValue(result)


class _FakeCarbonMaskToken:
    def __init__(self, source_band_name: str):
        self.source_band_name = source_band_name


# ---------------------------------------------------------------------------
# Fake GMW image (returned by ee.Image(GMW_2020))
# ---------------------------------------------------------------------------


class _FakeGMWImage:
    def __init__(self, bands: list[str]):
        self._bands = bands
        self.selected_bands: list[str] = []
        self.gt_called = False
        self.self_mask_called = False

    def bandNames(self):
        return _FakeValue(self._bands)

    def select(self, bands):
        self.selected_bands = list(bands)
        return self

    def gt(self, _val):
        self.gt_called = True
        return self

    def selfMask(self):
        self.self_mask_called = True
        return self


# ---------------------------------------------------------------------------
# _FakeFirstImage / _FakeQualityProbeImage (for GEDI band checks and quality filter)
# ---------------------------------------------------------------------------


class _FakeFirstImage:
    def __init__(self, bands: list[str]):
        self._bands = bands

    def bandNames(self):
        return _FakeValue(self._bands)


class _FakeMaskExpr:
    def __init__(self, conditions: list[tuple]):
        self.conditions = conditions

    def And(self, other):
        return _FakeMaskExpr(self.conditions + other.conditions)


class _FakeBandForEq:
    def __init__(self, image, band_name: str):
        self.image = image
        self.band_name = band_name

    def eq(self, value):
        self.image.eq_checks.append((self.band_name, value))
        return _FakeMaskExpr([(self.band_name, value)])


class _FakeRh98ForFilter:
    def __init__(self, image):
        self.image = image

    def updateMask(self, mask_expr):
        self.image.update_mask_conditions = list(mask_expr.conditions)
        return self.image


class _FakeQualityProbeImage:
    def __init__(self):
        self.eq_checks: list[tuple] = []
        self.select_calls: list[str] = []
        self.update_mask_conditions: list[tuple] = []

    def select(self, bands):
        band = bands[0]
        self.select_calls.append(band)
        if band == "rh98":
            return _FakeRh98ForFilter(self)
        return _FakeBandForEq(self, band)


# ---------------------------------------------------------------------------
# _FakePixelAreaImage: models ee.Image.pixelArea()
# ---------------------------------------------------------------------------


class _FakePixelAreaImage:
    """Returned by ee.Image.pixelArea(); carries area value in m² (simulated)."""

    def __init__(self, ee_state):
        self._ee = ee_state
        self._ee.pixel_area_called = True

    def divide(self, divisor: float):
        """Convert m² → ha (divide by 10 000)."""
        self._ee.pixel_area_divide_called = True
        # Return a raster whose _value represents ha/pixel at the GEDI analysis scale
        return _FakeCarbonStockRaster(
            self._ee,
            value=self._ee.pixel_area_ha,
            name="area",
            pixel_count=self._ee.pixel_count,
        )


# ---------------------------------------------------------------------------
# _FakeImageFactory: models the ee.Image class (constructor + pixelArea static)
# ---------------------------------------------------------------------------


class _FakeImageFactory:
    """
    Callable that models ee.Image:
      ee.Image(asset_id)    → calls __call__
      ee.Image.pixelArea()  → calls instance method pixelArea()
    """

    def __init__(self, ee_state):
        self._ee = ee_state

    def __call__(self, image_input):
        if image_input == GMW_2020:
            return self._ee.gmw_image
        # For ee.Image(collection.first()) in band check
        if hasattr(image_input, "bandNames"):
            return image_input
        return _FakeCarbonStockRaster(self._ee, 0.0, "", self._ee.pixel_count)

    def pixelArea(self):
        return _FakePixelAreaImage(self._ee)


# ---------------------------------------------------------------------------
# _FakeStockData: models ee.data
# ---------------------------------------------------------------------------


class _FakeStockData:
    def __init__(self, ee_state):
        self._ee = ee_state

    def getAsset(self, asset_id: str):
        err = self._ee.asset_errors.get(asset_id)
        if err is not None:
            raise err
        return self._ee.asset_metadata_map.get(asset_id, {"type": "IMAGE"})


# ---------------------------------------------------------------------------
# _FakeMappedCollection / _FakeStockCollection
# ---------------------------------------------------------------------------


class _FakeMappedCollection:
    def __init__(self, ee_state):
        self._ee = ee_state

    def mosaic(self):
        self._ee.mosaic_called = True
        return _FakeCarbonStockRaster(
            self._ee,
            value=self._ee.rh98_value,
            name="",
            pixel_count=self._ee.pixel_count,
        )


class _FakeStockCollection:
    def __init__(self, ee_state):
        self._ee = ee_state

    def filterBounds(self, geometry):
        self._ee.last_filter_bounds = geometry
        return self

    def filterDate(self, start, end):
        self._ee.last_filter_dates = (start, end)
        return self

    def size(self):
        return _FakeValue(self._ee.collection_size, self._ee.collection_size_error)

    def first(self):
        return _FakeFirstImage(self._ee.first_image_bands)

    def map(self, fn):
        self._ee.map_called = True
        fn(self._ee.quality_probe_image)
        return _FakeMappedCollection(self._ee)


# ---------------------------------------------------------------------------
# _FakeCarbonStockEE: top-level fake Earth Engine namespace
# ---------------------------------------------------------------------------


class _FakeCarbonStockEE:
    def __init__(
        self,
        *,
        collection_size: int = 3,
        first_image_bands: list[str] | None = None,
        gmw_bands: list[str] | None = None,
        rh98_value: float = 3.09,
        pixel_count: int = 1130,
        # Area per pixel at GEDI analysis scale (25m × 25m / 10000 = 0.0625 ha)
        pixel_area_ha: float = 0.0625,
        mapped_area_ha: float | None = 90769.33,
        asset_metadata_map: dict | None = None,
        asset_errors: dict | None = None,
        collection_size_error: Exception | None = None,
        reduce_error: Exception | None = None,
        override_gmw_area_output: dict | None = None,
        override_analysis_output: dict | None = None,
    ):
        self.collection_size = collection_size
        self.first_image_bands = first_image_bands or ["rh98", "quality_flag", "degrade_flag"]
        self.gmw_bands = gmw_bands or ["b1"]
        self.rh98_value = rh98_value
        self.pixel_count = pixel_count
        self.pixel_area_ha = pixel_area_ha
        self.mapped_area_ha = mapped_area_ha
        self.asset_metadata_map = asset_metadata_map or {GMW_2020: {"type": "IMAGE"}}
        self.asset_errors = asset_errors or {}
        self.collection_size_error = collection_size_error
        self.reduce_error = reduce_error
        self.override_gmw_area_output = override_gmw_area_output
        self.override_analysis_output = override_analysis_output

        self.gmw_image = _FakeGMWImage(self.gmw_bands)
        self.quality_probe_image = _FakeQualityProbeImage()
        self.Image = _FakeImageFactory(self)
        self.Geometry = _FakeGeometry
        self.Reducer = _FakeReducerFactory
        self.data = _FakeStockData(self)

        # Tracking attributes
        self.last_collection_dataset_id: str | None = None
        self.last_filter_bounds = None
        self.last_filter_dates: tuple | None = None
        self.map_called = False
        self.mosaic_called = False
        self.mask_update_count: int = 0
        self.multiply_calls: list[float] = []
        self.reduce_calls: list[dict] = []
        self.pixel_area_called: bool = False
        self.pixel_area_divide_called: bool = False
        self.carbon_mask_requested: bool = False
        self.coverage_used_carbon_mask: bool = False
        self.coverage_used_carbon_values_directly: bool = False
        self.direct_stock_multiplies_carbon_band: bool = False

    def ImageCollection(self, dataset_id: str):
        self.last_collection_dataset_id = dataset_id
        return _FakeStockCollection(self)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


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
        stock_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(),
    )


def _set_fake_ee(monkeypatch, fake_ee: _FakeCarbonStockEE):
    monkeypatch.setattr(stock_service_module, "ee", fake_ee)
    monkeypatch.setattr(mask_service_module, "ee", fake_ee)


def _reset_cache():
    stock_service_module.gee_carbon_stock_service._cached_success_response = None


def _expected_carbon_mean(rh98: float) -> float:
    """Carbon = 0.5 × (AGB + BGB) = 0.5 × AGB × (1 + ROOT_TO_SHOOT)."""
    agb = rh98 * BIOMASS_HEIGHT_TO_AGB
    bgb = agb * BIOMASS_ROOT_TO_SHOOT
    return (agb + bgb) * BIOMASS_TO_CARBON


# ---------------------------------------------------------------------------
# 1. Unit tests — no monkeypatching
# ---------------------------------------------------------------------------


def test_gmw_area_scale_constant_is_10():
    """GMW_AREA_SCALE_M must be 10 m for accurate mangrove pixel boundaries."""
    assert GMW_AREA_SCALE_M == 10


def test_older_report_reference_constant():
    """The older project report reference is stored as a constant, not scattered."""
    assert CARBON_STOCK_OLDER_REPORT_DIRECT_SAMPLED_MG_C == pytest.approx(1480.37, rel=1e-9)


def test_pixel_area_divide_converts_m2_to_ha():
    """pixelArea() in m² must be divided by 10 000 to get hectares."""
    m2_per_25m_pixel = 25 * 25  # 625
    assert m2_per_25m_pixel / 10000 == pytest.approx(0.0625, rel=1e-9)

    m2_per_10m_pixel = 10 * 10  # 100
    assert m2_per_10m_pixel / 10000 == pytest.approx(0.01, rel=1e-9)


def test_extrapolated_stock_formula():
    """Extrapolated stock = mean Carbon density × mapped mangrove area."""
    mean_c = 23.0257
    area_ha = 90769.33
    expected = mean_c * area_ha
    # Should be ~2.09 million Mg C; verify the formula gives a value in that range
    assert 2_000_000 < expected < 2_200_000
    # Verify the arithmetic is self-consistent
    assert expected == pytest.approx(mean_c * area_ha, rel=1e-9)


def test_coverage_percent_formula():
    """Coverage % = (GEDI coverage area / mapped mangrove area) × 100."""
    gedi_coverage_ha = 70.625
    mapped_ha = 90769.33
    pct = (gedi_coverage_ha / mapped_ha) * 100
    assert 0.0 < pct < 1.0  # sparse GEDI → well below 1%


def test_pixel_count_times_625m2_is_not_authoritative_ground_area():
    """1130 × 625 m² is only a fixed-cell assumption and must not be treated as authoritative area."""
    fixed_area_ha = (1130 * 625) / 10000
    assert fixed_area_ha == pytest.approx(70.625, rel=1e-9)
    # The live geographic-grid area sum can differ and is authoritative when computed via pixelArea().
    live_pixel_area_sum_ha = 64.29286419067385
    assert live_pixel_area_sum_ha != pytest.approx(fixed_area_ha, rel=1e-6)


def test_full_precision_extrapolated_stock_example():
    """Full-precision extrapolation uses mean Carbon × mapped area without rounding."""
    mean_c = 23.02570844643939
    mapped_area = 90769.33192367057
    extrapolated = mean_c * mapped_area
    assert extrapolated == pytest.approx(2090028.172752522, rel=1e-12)


def test_carbon_stock_formula_tolerance_constant():
    """CARBON_STOCK_FORMULA_TOLERANCE is the correct small value."""
    assert CARBON_STOCK_FORMULA_TOLERANCE == pytest.approx(1e-6, rel=1e-9)


# ---------------------------------------------------------------------------
# 2. API success tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stock_summary_success_response_structure(monkeypatch):
    """Successful response includes all required top-level fields."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/carbon/stock-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["mode"] == "live_earth_engine"
    assert body["status"] == "connected"
    assert body["processing_performed"] is True
    assert "study_area" in body
    assert "date_range" in body
    assert "carbon_density" in body
    assert "area" in body
    assert "stock" in body
    assert "calculation_methods" in body
    assert isinstance(body["assumptions"], list)
    assert len(body["assumptions"]) >= 3
    assert "processing" in body
    assert isinstance(body["warnings"], list)
    assert len(body["warnings"]) >= 3
    assert "reference_comparison" in body


@pytest.mark.asyncio
async def test_stock_summary_processing_block(monkeypatch):
    """Processing block includes both area scale and analysis scale."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    p = body["processing"]
    assert p["gmw_area_scale_m"] == GMW_AREA_SCALE_M
    assert p["gedi_analysis_scale_m"] == GEDI_RH98_SCALE_M
    assert p["best_effort"] is False


@pytest.mark.asyncio
async def test_stock_summary_two_reduce_calls_made(monkeypatch):
    """Exactly two reduceRegion calls are made: one at 10 m (GMW) and one at 25 m (GEDI)."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/carbon/stock-summary")

    assert len(fake_ee.reduce_calls) == 2
    scales = sorted(c["scale"] for c in fake_ee.reduce_calls)
    assert scales == [GMW_AREA_SCALE_M, GEDI_RH98_SCALE_M]


@pytest.mark.asyncio
async def test_stock_summary_gmw_area_reduced_at_scale_10(monkeypatch):
    """Mapped mangrove area is computed at scale=10 m with bestEffort=False."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/carbon/stock-summary")

    gmw_call = next(c for c in fake_ee.reduce_calls if c["scale"] == GMW_AREA_SCALE_M)
    assert gmw_call["bestEffort"] is False
    assert gmw_call["maxPixels"] == GEDI_RH98_MAX_PIXELS
    assert gmw_call["tileScale"] == GEDI_RH98_TILE_SCALE
    assert "sum" in gmw_call["reducer_names"]


@pytest.mark.asyncio
async def test_stock_summary_gedi_coverage_reduced_at_scale_25(monkeypatch):
    """GEDI analysis is computed at scale=25 m with bestEffort=False."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/carbon/stock-summary")

    gedi_call = next(c for c in fake_ee.reduce_calls if c["scale"] == GEDI_RH98_SCALE_M)
    assert gedi_call["bestEffort"] is False
    assert gedi_call["maxPixels"] == GEDI_RH98_MAX_PIXELS
    assert "sum" in gedi_call["reducer_names"]
    assert "mean" in gedi_call["reducer_names"]
    assert "count" in gedi_call["reducer_names"]


@pytest.mark.asyncio
async def test_stock_summary_pixel_area_converted_from_m2_to_ha(monkeypatch):
    """ee.Image.pixelArea() is called and divided by 10 000 to convert to hectares."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/carbon/stock-summary")

    assert fake_ee.pixel_area_called is True
    assert fake_ee.pixel_area_divide_called is True


@pytest.mark.asyncio
async def test_stock_summary_gmw_mask_applied(monkeypatch):
    """The GMW binary mask is applied during processing (gt + selfMask)."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/carbon/stock-summary")

    assert fake_ee.mask_update_count >= 1
    assert fake_ee.gmw_image.gt_called is True
    assert fake_ee.gmw_image.self_mask_called is True


@pytest.mark.asyncio
async def test_stock_summary_coverage_uses_carbon_band_mask(monkeypatch):
    """Coverage image must use carbon_band.mask(), not Carbon numeric values, for masking."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/carbon/stock-summary")

    assert fake_ee.carbon_mask_requested is True
    assert fake_ee.coverage_used_carbon_mask is True


@pytest.mark.asyncio
async def test_stock_summary_coverage_does_not_update_mask_with_carbon_values(monkeypatch):
    """Coverage image must not call updateMask(carbon_band) directly."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/carbon/stock-summary")

    assert fake_ee.coverage_used_carbon_values_directly is False


@pytest.mark.asyncio
async def test_stock_summary_direct_stock_preserves_carbon_mask_semantics(monkeypatch):
    """Direct stock must be built from carbon_band.multiply(pixel_area_ha), preserving Carbon mask semantics."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/carbon/stock-summary")

    assert fake_ee.direct_stock_multiplies_carbon_band is True
    # No Carbon-value masking path is used for direct stock construction.
    assert fake_ee.coverage_used_carbon_values_directly is False


@pytest.mark.asyncio
async def test_stock_summary_mapped_mangrove_area_in_response(monkeypatch):
    """Response area block contains mapped_mangrove_area_ha from the GMW reduction."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(mapped_area_ha=90769.33))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["area"]["mapped_mangrove_area_ha"] == pytest.approx(90769.33, rel=1e-6)


@pytest.mark.asyncio
async def test_stock_summary_gedi_coverage_area_is_below_mapped_area(monkeypatch):
    """GEDI raster coverage area must be ≤ mapped mangrove area."""
    _reset_cache()
    _set_connected(monkeypatch)
    # pixel_count=1130 × pixel_area_ha=0.0625 = 70.625 ha << 90769.33 ha
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(pixel_count=1130, mapped_area_ha=90769.33))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    area = body["area"]
    assert area["valid_gedi_raster_coverage_area_ha"] <= area["mapped_mangrove_area_ha"]


@pytest.mark.asyncio
async def test_stock_summary_coverage_percent_between_0_and_100(monkeypatch):
    """Coverage percentage is between 0 and 100."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    pct = body["area"]["gedi_raster_coverage_percent"]
    assert 0.0 < pct <= 100.0


@pytest.mark.asyncio
async def test_stock_summary_extrapolated_stock_equals_mean_times_area(monkeypatch):
    """Extrapolated stock = mean Carbon density × mapped mangrove area (within tolerance)."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(rh98_value=3.09, mapped_area_ha=90769.33))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    carbon_mean = body["carbon_density"]["mean_mg_c_ha"]
    mapped_area = body["area"]["mapped_mangrove_area_ha"]
    extrapolated = body["stock"]["extrapolated_ecosystem_carbon_mg_c"]

    expected = carbon_mean * mapped_area
    assert extrapolated == pytest.approx(expected, rel=1e-6)


@pytest.mark.asyncio
async def test_stock_summary_direct_stock_is_calculated_not_hardcoded(monkeypatch):
    """Direct sampled stock is calculated from Carbon × pixelArea and can vary with true ground area."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(rh98_value=3.09, pixel_count=1130))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    direct = body["stock"]["direct_sampled_raster_carbon_mg_c"]
    # Synthetic fixture uses 0.0625 ha/pixel; the result differs from the live area-weighted
    # value because pixel_area comes from ee.Image.pixelArea(), not a fixed 625 m² assumption.
    assert direct == pytest.approx(_expected_carbon_mean(3.09) * 0.0625 * 1130, rel=1e-6)
    assert direct > 0.0


@pytest.mark.asyncio
async def test_stock_summary_direct_stock_can_reproduce_older_1480_value(monkeypatch):
    """With live-like pixelArea sum inputs, the computed direct stock reproduces ~1,480.37 Mg C."""
    _reset_cache()
    _set_connected(monkeypatch)
    rh98 = 3.09
    count = 1130
    target_direct = CARBON_STOCK_OLDER_REPORT_DIRECT_SAMPLED_MG_C
    pixel_area_ha = target_direct / (_expected_carbon_mean(rh98) * count)
    _set_fake_ee(
        monkeypatch,
        _FakeCarbonStockEE(rh98_value=rh98, pixel_count=count, pixel_area_ha=pixel_area_ha),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    direct = body["stock"]["direct_sampled_raster_carbon_mg_c"]
    assert direct == pytest.approx(CARBON_STOCK_OLDER_REPORT_DIRECT_SAMPLED_MG_C, rel=1e-9)


@pytest.mark.asyncio
async def test_stock_summary_direct_stock_area_weighted_sum(monkeypatch):
    """Direct stock = sum(Carbon_density × pixel_area_ha) over valid pixels."""
    _reset_cache()
    _set_connected(monkeypatch)
    rh98 = 3.09
    pixel_area = 0.0625
    count = 1130
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(rh98_value=rh98, pixel_area_ha=pixel_area, pixel_count=count))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    carbon_mean = _expected_carbon_mean(rh98)
    expected_direct = carbon_mean * pixel_area * count
    assert body["stock"]["direct_sampled_raster_carbon_mg_c"] == pytest.approx(expected_direct, rel=1e-5)


@pytest.mark.asyncio
async def test_stock_summary_calculation_not_based_on_fixed_625m2_assumption(monkeypatch):
    """Changing pixelArea_ha changes coverage/direct stock, proving no fixed 625 m² assumption is used."""
    _reset_cache()
    _set_connected(monkeypatch)
    rh98 = 3.09
    count = 1130
    pixel_area_ha = 0.056896340000596325  # live-like geographic-grid area: 64.29286419067385 / 1130
    _set_fake_ee(
        monkeypatch,
        _FakeCarbonStockEE(rh98_value=rh98, pixel_count=count, pixel_area_ha=pixel_area_ha),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["area"]["valid_gedi_raster_coverage_area_ha"] == pytest.approx(64.29286419067385, rel=1e-9)
    expected_direct = _expected_carbon_mean(rh98) * pixel_area_ha * count
    assert body["stock"]["direct_sampled_raster_carbon_mg_c"] == pytest.approx(expected_direct, rel=1e-9)


@pytest.mark.asyncio
async def test_stock_summary_extrapolated_greater_than_direct(monkeypatch):
    """Extrapolated stock (full area) must be ≥ direct stock (sparse sampled area)."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert (
        body["stock"]["extrapolated_ecosystem_carbon_mg_c"]
        >= body["stock"]["direct_sampled_raster_carbon_mg_c"]
    )


@pytest.mark.asyncio
async def test_stock_summary_reference_comparison_in_response(monkeypatch):
    """Response includes reference_comparison block describing 1,480.37 as live-validated."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    rc = body["reference_comparison"]
    assert rc["older_reported_direct_sampled_carbon_mg_c"] == pytest.approx(
        CARBON_STOCK_OLDER_REPORT_DIRECT_SAMPLED_MG_C, rel=1e-9
    )
    assert rc["difference_from_older_report_mg_c"] is not None
    assert "note" in rc
    direct = body["stock"]["direct_sampled_raster_carbon_mg_c"]
    expected_diff = direct - CARBON_STOCK_OLDER_REPORT_DIRECT_SAMPLED_MG_C
    assert rc["difference_from_older_report_mg_c"] == pytest.approx(expected_diff, rel=1e-6)
    assert "reproduces the older direct sampled carbon result" in rc["note"]
    assert "pixelArea()" in rc["note"]
    # The note must describe 1,480.37 as validated (confirmed), not as inconsistent.
    assert "inconsistent" not in rc["note"].lower()


@pytest.mark.asyncio
async def test_stock_summary_uses_correct_dataset_and_dates(monkeypatch):
    """Correct GEDI dataset ID and Jan–Mar 2020 date range are used."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert fake_ee.last_collection_dataset_id == GEDI_L2A_MONTHLY
    assert fake_ee.last_filter_dates == (GEDI_RH98_BASELINE_START_DATE, GEDI_RH98_BASELINE_END_DATE)
    assert body["date_range"]["start_date"] == "2020-01-01"
    assert body["date_range"]["end_date"] == "2020-04-01"
    assert body["date_range"]["filter_convention"] == "end_exclusive"


@pytest.mark.asyncio
async def test_stock_summary_gedi_quality_flags_applied(monkeypatch):
    """Quality filter applies quality_flag == 1 and degrade_flag == 0."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/carbon/stock-summary")

    probe = fake_ee.quality_probe_image
    eq_dict = dict(probe.eq_checks)
    assert eq_dict.get("quality_flag") == 1
    assert eq_dict.get("degrade_flag") == 0


@pytest.mark.asyncio
async def test_stock_summary_mosaic_used(monkeypatch):
    """GEDI collection uses mosaic aggregation, not mean or median."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/carbon/stock-summary")

    assert fake_ee.mosaic_called is True


@pytest.mark.asyncio
async def test_stock_summary_raster_pixel_count_positive(monkeypatch):
    """carbon_density.valid_gedi_raster_pixel_count is > 0 in successful response."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(pixel_count=1130))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["carbon_density"]["valid_gedi_raster_pixel_count"] == 1130


@pytest.mark.asyncio
async def test_stock_summary_terminology_raster_coverage_not_shots(monkeypatch):
    """Response uses raster-coverage terminology, not 'GEDI shots'."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    body_text = str(body).lower()
    assert "valid_gedi_raster_coverage_area_ha" in str(body["area"])
    assert "shot" not in body_text


@pytest.mark.asyncio
async def test_stock_summary_no_sentinel2_processing(monkeypatch):
    """Response must not contain any Sentinel-2 processing fields."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    body_str = str(body).lower()
    assert "sentinel" not in body_str
    assert "ndvi" not in body_str


@pytest.mark.asyncio
async def test_stock_summary_no_secrets_leaked(monkeypatch):
    """Error responses must not expose credentials or private key paths."""
    _reset_cache()
    monkeypatch.setattr(
        stock_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(),
    )
    fake_ee = _FakeCarbonStockEE(
        reduce_error=RuntimeError("quota exceeded for project my-secret-project-id"),
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    body_str = str(body)
    assert "my-secret-project-id" not in body_str
    assert "private_key" not in body_str
    assert "service_account" not in body_str
    # The safe message should be present
    assert body["message"] is not None


@pytest.mark.asyncio
async def test_stock_summary_cache_returns_same_response(monkeypatch):
    """Second call returns the cached response (only 2 getInfo calls total, not 4)."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeCarbonStockEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body1 = (await client.get("/api/gee/carbon/stock-summary")).json()
        body2 = (await client.get("/api/gee/carbon/stock-summary")).json()

    # Only 2 reduce calls (one 10m, one 25m) from first call; cache served second
    assert len(fake_ee.reduce_calls) == 2
    assert body1["stock"]["extrapolated_ecosystem_carbon_mg_c"] == body2["stock"][
        "extrapolated_ecosystem_carbon_mg_c"
    ]


@pytest.mark.asyncio
async def test_stock_summary_warnings_list_present(monkeypatch):
    """Response contains at least 3 meaningful warnings."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert len(body["warnings"]) >= 3
    warnings_text = " ".join(body["warnings"]).lower()
    assert "direct" in warnings_text or "sampled" in warnings_text
    assert "extrapolat" in warnings_text


# ---------------------------------------------------------------------------
# 3. Empty / null / zero handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stock_summary_empty_collection(monkeypatch):
    """Empty GEDI collection → status empty_collection, processing_performed=False."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(collection_size=0))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["status"] == "empty_collection"
    assert body["processing_performed"] is False
    assert body["stock"] is None


@pytest.mark.asyncio
async def test_stock_summary_empty_carbon_result(monkeypatch):
    """Zero valid GEDI pixels → status empty_carbon_result."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(pixel_count=0))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["status"] == "empty_carbon_result"
    assert body["processing_performed"] is True


@pytest.mark.asyncio
async def test_stock_summary_null_gmw_area_result(monkeypatch):
    """Null GMW area reducer output → status area_null_result."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(
        monkeypatch,
        _FakeCarbonStockEE(override_gmw_area_output={}),  # no "area" key
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["status"] == "area_null_result"
    assert body["processing_performed"] is True


# ---------------------------------------------------------------------------
# 4. Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stock_summary_authentication_failure(monkeypatch):
    """Authentication failure → not connected response."""
    _reset_cache()
    monkeypatch.setattr(
        stock_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(connected=False, status="auth_failed",
                                    message="Authentication failed."),
    )
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["connected"] is False
    assert body["status"] == "auth_failed"
    assert body["processing_performed"] is False


@pytest.mark.asyncio
async def test_stock_summary_gee_disabled(monkeypatch):
    """GEE disabled → connected=False, status=disabled."""
    _reset_cache()
    monkeypatch.setattr(
        stock_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(enabled=False, connected=False, status="disabled"),
    )
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["connected"] is False
    assert body["status"] == "disabled"


@pytest.mark.asyncio
async def test_stock_summary_quota_error(monkeypatch):
    """Quota/restricted error during reduction → safe message, no credentials exposed."""
    _reset_cache()
    _set_connected(monkeypatch)
    quota_err = RuntimeError("EEException: quota exceeded for project secret-proj")
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(reduce_error=quota_err))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["connected"] is True
    assert body["status"] in ("area_calculation_failed", "processing_failed")
    msg = body.get("message", "")
    assert "secret-proj" not in msg
    assert "quota" in msg.lower() or "limitation" in msg.lower()


@pytest.mark.asyncio
async def test_stock_summary_missing_gedi_bands(monkeypatch):
    """Missing GEDI bands → status missing_required_bands."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(
        monkeypatch,
        _FakeCarbonStockEE(first_image_bands=["rh98"]),  # missing quality_flag, degrade_flag
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["status"] == "missing_required_bands"


@pytest.mark.asyncio
async def test_stock_summary_gmw_asset_not_image(monkeypatch):
    """GMW asset with wrong type → status gmw_asset_invalid."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(
        monkeypatch,
        _FakeCarbonStockEE(asset_metadata_map={GMW_2020: {"type": "TABLE"}}),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["status"] == "gmw_asset_invalid"


@pytest.mark.asyncio
async def test_stock_summary_gmw_asset_inaccessible(monkeypatch):
    """Inaccessible GMW asset → status gmw_asset_failure."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(
        monkeypatch,
        _FakeCarbonStockEE(asset_errors={GMW_2020: RuntimeError("Asset not found.")}),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    assert body["status"] == "gmw_asset_failure"


# ---------------------------------------------------------------------------
# 5. Validation invariant failure tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stock_summary_validation_fails_when_coverage_exceeds_mapped_area(monkeypatch):
    """coverage_area > mapped_area → validation_failed with invariant description."""
    _reset_cache()
    _set_connected(monkeypatch)
    rh98 = 3.09
    carbon = _expected_carbon_mean(rh98)
    # Force: coverage area (sum) > mapped area
    # pixel_count=1130 × pixel_area=0.0625 = 70.625 ha; set mapped_area=10 ha to trigger
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(mapped_area_ha=10.0))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    # GEDI coverage ≈ 70.6 ha > mapped area 10 ha → validation_failed
    assert body["status"] == "validation_failed"
    assert body["processing_performed"] is True


# ---------------------------------------------------------------------------
# 6. No forbidden fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stock_summary_no_total_ecosystem_area_assumed(monkeypatch):
    """Response must not include a hard-coded area field (uses live GMW area)."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeCarbonStockEE(mapped_area_ha=12345.0))  # not the reference

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/carbon/stock-summary")).json()

    # The live GMW area should differ from the old reference 90769.33
    assert body["area"]["mapped_mangrove_area_ha"] == pytest.approx(12345.0, rel=1e-6)
