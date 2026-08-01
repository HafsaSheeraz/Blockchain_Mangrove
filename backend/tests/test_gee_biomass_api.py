"""
Module 9 tests for GET /api/gee/biomass/summary.

All Earth Engine calls are mocked.  No real GEE calls are made.

The _FakeBiomassRaster class computes formula values numerically,
so tests can verify that build_biomass_image_stack uses the correct
centralized coefficients and produces consistent band values.
"""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.gee_datasets import (
    BIOMASS_BAND_AGB,
    BIOMASS_BAND_BGB,
    BIOMASS_BAND_CARBON,
    BIOMASS_BAND_RH98,
    BIOMASS_BAND_TAB,
    BIOMASS_FORMULA_TOLERANCE,
    BIOMASS_HEIGHT_TO_AGB,
    BIOMASS_ROOT_TO_SHOOT,
    BIOMASS_TO_CARBON,
    GEDI_L2A_MONTHLY,
    GEDI_RH98_BASELINE_END_DATE,
    GEDI_RH98_BASELINE_START_DATE,
    GEDI_RH98_SCALE_M,
    GEDI_RH98_TILE_SCALE,
    GMW_2020,
    GMW_VALIDATED_MASK_BAND,
)
from app.main import app
from app.models.gee_biomass import BandStats, BiomassStatistics
from app.services import gee_biomass_service as biomass_service_module
from app.services import gee_mask_service as mask_service_module
from app.services.gee_biomass_service import _validate_formula_invariants, build_biomass_image_stack
from app.services.gee_service import GeeConnectionContext, GeeSettings


# ---------------------------------------------------------------------------
# Fake EE primitives (shared by all API tests in this file)
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


class _FakeGeometry:
    @staticmethod
    def Rectangle(bounds):
        return {"type": "Rectangle", "bounds": bounds}


class _FakeValue:  # noqa: F811  (intentional redefinition for clarity)
    def __init__(self, value=None, error: Exception | None = None):
        self._value = value
        self._error = error

    def getInfo(self):
        if self._error is not None:
            raise self._error
        return self._value


class _FakeGMWImage:
    """Minimal fake for ee.Image(GMW_2020) used in band-name and mask-building calls."""

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


class _FakeFirstImage:
    def __init__(self, bands: list[str]):
        self._bands = bands

    def bandNames(self):
        return _FakeValue(self._bands)


class _FakeQualityProbeImage:
    """Tracks quality-filter function calls (passed to collection.map)."""

    def __init__(self):
        self.eq_checks: list[tuple[str, int]] = []
        self.select_calls: list[str] = []
        self.update_mask_conditions: list[tuple[str, int]] = []

    def select(self, bands):
        band = bands[0]
        self.select_calls.append(band)
        if band == "rh98":
            return _FakeRh98ForFilter(self)
        return _FakeBandForEq(self, band)


class _FakeBandForEq:
    def __init__(self, image, band_name: str):
        self.image = image
        self.band_name = band_name

    def eq(self, value):
        self.image.eq_checks.append((self.band_name, value))
        return _FakeMaskExpr([(self.band_name, value)])


class _FakeMaskExpr:
    def __init__(self, conditions: list[tuple[str, int]]):
        self.conditions = conditions

    def And(self, other):
        return _FakeMaskExpr(self.conditions + other.conditions)


class _FakeRh98ForFilter:
    def __init__(self, image):
        self.image = image

    def updateMask(self, mask_expr):
        self.image.update_mask_conditions = list(mask_expr.conditions)
        return self.image


# ---------------------------------------------------------------------------
# _FakeBiomassRaster: computes formula chain numerically for deterministic tests
# ---------------------------------------------------------------------------


class _FakeBiomassRaster:
    """
    Fake EE image that tracks rename/multiply/add/addBands operations and
    computes values numerically so tests can verify formula correctness.
    """

    def __init__(self, ee_state, value: float = 3.09, name: str = "", pixel_count: int = 1130, bands: dict | None = None):
        self._ee = ee_state
        self._value = value
        self._name = name
        self._pixel_count = pixel_count
        self._bands: dict[str, float] = bands or {}

    # ── Image operations tracked by the fake ──────────────────────────

    def clip(self, _geometry):
        return self

    def updateMask(self, _mask):
        self._ee.mask_update_called = True
        return _FakeBiomassRaster(self._ee, self._value, self._name, self._pixel_count, dict(self._bands))

    def rename(self, band_list: list[str]):
        r = _FakeBiomassRaster(self._ee, self._value, band_list[0], self._pixel_count, dict(self._bands))
        return r

    def multiply(self, factor: float):
        self._ee.multiply_factors.append(factor)
        return _FakeBiomassRaster(self._ee, self._value * factor, self._name, self._pixel_count, dict(self._bands))

    def add(self, other: "_FakeBiomassRaster"):
        return _FakeBiomassRaster(
            self._ee, self._value + other._value, self._name, self._pixel_count, dict(self._bands)
        )

    def addBands(self, other: "_FakeBiomassRaster"):
        new_bands: dict[str, float] = {}
        if self._bands:
            new_bands.update(self._bands)
        elif self._name:
            new_bands[self._name] = self._value
        if other._bands:
            new_bands.update(other._bands)
        elif other._name:
            new_bands[other._name] = other._value
        return _FakeBiomassRaster(self._ee, self._value, self._name, self._pixel_count, new_bands)

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
        # If override is set, return it verbatim (used for error-injection tests).
        if self._ee.override_reduce_outputs is not None:
            return _FakeValue(self._ee.override_reduce_outputs)

        # Compute numerically from accumulated bands.
        all_bands: dict[str, float] = dict(self._bands)
        if self._name and self._name not in all_bands:
            all_bands[self._name] = self._value

        stats: dict = {}
        for band_name, val in all_bands.items():
            stats[f"{band_name}_count"] = self._pixel_count
            if self._pixel_count > 0:
                stats[f"{band_name}_min"] = val
                stats[f"{band_name}_mean"] = val
                stats[f"{band_name}_max"] = val
        return _FakeValue(stats)


# ---------------------------------------------------------------------------
# _FakeBiomassCollection / _FakeMappedBiomassCollection
# ---------------------------------------------------------------------------


class _FakeMappedBiomassCollection:
    def __init__(self, ee_state):
        self._ee = ee_state

    def mosaic(self):
        self._ee.mosaic_called = True
        return _FakeBiomassRaster(self._ee, self._ee.rh98_value, "", self._ee.pixel_count)


class _FakeBiomassCollection:
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
        return _FakeMappedBiomassCollection(self._ee)


# ---------------------------------------------------------------------------
# _FakeBiomassData (ee.data)
# ---------------------------------------------------------------------------


class _FakeBiomassData:
    def __init__(self, ee_state):
        self._ee = ee_state

    def getAsset(self, asset_id: str):
        err = self._ee.asset_errors.get(asset_id)
        if err is not None:
            raise err
        return self._ee.asset_metadata_map.get(asset_id, {"type": "IMAGE"})


# ---------------------------------------------------------------------------
# _FakeBiomassEE: top-level Earth Engine namespace fake
# ---------------------------------------------------------------------------


class _FakeBiomassEE:
    def __init__(
        self,
        *,
        collection_size: int = 3,
        first_image_bands: list[str] | None = None,
        gmw_bands: list[str] | None = None,
        rh98_value: float = 3.09,
        pixel_count: int = 1130,
        asset_metadata_map: dict | None = None,
        asset_errors: dict | None = None,
        collection_size_error: Exception | None = None,
        reduce_error: Exception | None = None,
        override_reduce_outputs: dict | None = None,
    ):
        self.collection_size = collection_size
        self.first_image_bands = first_image_bands or ["rh98", "quality_flag", "degrade_flag"]
        self.gmw_bands = gmw_bands or ["b1"]
        self.rh98_value = rh98_value
        self.pixel_count = pixel_count
        self.asset_metadata_map = asset_metadata_map or {GMW_2020: {"type": "IMAGE"}}
        self.asset_errors = asset_errors or {}
        self.collection_size_error = collection_size_error
        self.reduce_error = reduce_error
        self.override_reduce_outputs = override_reduce_outputs

        self.gmw_image = _FakeGMWImage(self.gmw_bands)
        self.quality_probe_image = _FakeQualityProbeImage()
        self.Geometry = _FakeGeometry
        self.Reducer = _FakeReducerFactory
        self.data = _FakeBiomassData(self)

        # Tracking attributes
        self.last_collection_dataset_id: str | None = None
        self.last_filter_bounds = None
        self.last_filter_dates: tuple | None = None
        self.map_called = False
        self.mosaic_called = False
        self.mask_update_called = False
        self.multiply_factors: list[float] = []
        self.reduce_calls: list[dict] = []

    def ImageCollection(self, dataset_id: str):
        self.last_collection_dataset_id = dataset_id
        return _FakeBiomassCollection(self)

    def Image(self, image_input):
        if image_input == GMW_2020:
            return self.gmw_image
        return image_input


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
        biomass_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(),
    )


def _set_fake_ee(monkeypatch, fake_ee: _FakeBiomassEE):
    monkeypatch.setattr(biomass_service_module, "ee", fake_ee)
    monkeypatch.setattr(mask_service_module, "ee", fake_ee)


def _reset_cache():
    biomass_service_module.gee_biomass_service._cached_success_response = None


# ---------------------------------------------------------------------------
# 1. Coefficient and formula-chain unit tests (no network, no monkeypatching)
# ---------------------------------------------------------------------------


def test_biomass_coefficients_are_centralized():
    """All formula coefficients come from gee_datasets config, not inline literals."""
    assert BIOMASS_HEIGHT_TO_AGB == 10.0
    assert BIOMASS_ROOT_TO_SHOOT == 0.49
    assert BIOMASS_TO_CARBON == 0.5


def test_build_biomass_image_stack_formula_operations():
    """build_biomass_image_stack applies correct coefficients in the right order."""
    recorded_multiply: list[float] = []

    class _Track:
        def __init__(self, val: float = 0.0, name: str = ""):
            self.val = val
            self.name = name
            self.bands: dict[str, float] = {}

        def rename(self, bnames):
            r = _Track(self.val, bnames[0])
            r.bands = dict(self.bands)
            return r

        def multiply(self, f):
            recorded_multiply.append(f)
            r = _Track(self.val * f, self.name)
            r.bands = dict(self.bands)
            return r

        def add(self, other):
            r = _Track(self.val + other.val, self.name)
            r.bands = dict(self.bands)
            return r

        def addBands(self, other):
            nb: dict[str, float] = {}
            if self.bands:
                nb.update(self.bands)
            elif self.name:
                nb[self.name] = self.val
            if other.bands:
                nb.update(other.bands)
            elif other.name:
                nb[other.name] = other.val
            r = _Track(self.val, self.name)
            r.bands = nb
            return r

    result = build_biomass_image_stack(_Track(3.09))

    assert BIOMASS_HEIGHT_TO_AGB in recorded_multiply, "HEIGHT_TO_AGB must be used"
    assert BIOMASS_ROOT_TO_SHOOT in recorded_multiply, "ROOT_TO_SHOOT must be used"
    assert BIOMASS_TO_CARBON in recorded_multiply, "BIOMASS_TO_CARBON must be used"

    expected_agb = 3.09 * BIOMASS_HEIGHT_TO_AGB
    expected_bgb = expected_agb * BIOMASS_ROOT_TO_SHOOT
    expected_tab = expected_agb + expected_bgb
    expected_carbon = expected_tab * BIOMASS_TO_CARBON

    assert result.bands[BIOMASS_BAND_AGB] == pytest.approx(expected_agb, rel=1e-9)
    assert result.bands[BIOMASS_BAND_BGB] == pytest.approx(expected_bgb, rel=1e-9)
    assert result.bands[BIOMASS_BAND_TAB] == pytest.approx(expected_tab, rel=1e-9)
    assert result.bands[BIOMASS_BAND_CARBON] == pytest.approx(expected_carbon, rel=1e-9)


def test_build_biomass_image_stack_band_names():
    """The five expected band names are present in the returned image stack."""

    class _MinimalImage:
        def __init__(self, val=1.0, name=""):
            self.val, self.name, self.bands = val, name, {}

        def rename(self, bn):
            r = _MinimalImage(self.val, bn[0])
            r.bands = dict(self.bands)
            return r

        def multiply(self, f):
            r = _MinimalImage(self.val * f, self.name)
            r.bands = dict(self.bands)
            return r

        def add(self, other):
            r = _MinimalImage(self.val + other.val, self.name)
            r.bands = dict(self.bands)
            return r

        def addBands(self, other):
            nb = {}
            if self.bands:
                nb.update(self.bands)
            elif self.name:
                nb[self.name] = self.val
            if other.bands:
                nb.update(other.bands)
            elif other.name:
                nb[other.name] = other.val
            r = _MinimalImage(self.val, self.name)
            r.bands = nb
            return r

    result = build_biomass_image_stack(_MinimalImage(2.0))
    assert BIOMASS_BAND_RH98 in result.bands
    assert BIOMASS_BAND_AGB in result.bands
    assert BIOMASS_BAND_BGB in result.bands
    assert BIOMASS_BAND_TAB in result.bands
    assert BIOMASS_BAND_CARBON in result.bands


def test_biomass_formula_validation_passes_within_tolerance():
    """_validate_formula_invariants returns empty list when values satisfy formulas."""
    rh98_mean = 3.09
    agb_mean = BIOMASS_HEIGHT_TO_AGB * rh98_mean * (1 + BIOMASS_FORMULA_TOLERANCE * 0.5)
    bgb_mean = BIOMASS_ROOT_TO_SHOOT * agb_mean
    tab_mean = agb_mean + bgb_mean
    carbon_mean = BIOMASS_TO_CARBON * tab_mean

    stats = BiomassStatistics(
        rh98=BandStats(unit="m", mean=rh98_mean, valid_raster_pixel_count=1130),
        agb=BandStats(unit="Mg/ha", mean=agb_mean, valid_raster_pixel_count=1130),
        bgb=BandStats(unit="Mg/ha", mean=bgb_mean, valid_raster_pixel_count=1130),
        tab=BandStats(unit="Mg/ha", mean=tab_mean, valid_raster_pixel_count=1130),
        carbon=BandStats(unit="Mg C/ha", mean=carbon_mean, valid_raster_pixel_count=1130),
    )
    assert _validate_formula_invariants(stats) == []


def test_biomass_formula_validation_fails_when_agb_inconsistent():
    """_validate_formula_invariants reports failure when AGB ≠ 10 × RH98."""
    stats = BiomassStatistics(
        rh98=BandStats(unit="m", mean=3.09, valid_raster_pixel_count=1130),
        agb=BandStats(unit="Mg/ha", mean=999.0, valid_raster_pixel_count=1130),  # wrong
        bgb=BandStats(unit="Mg/ha", mean=15.14, valid_raster_pixel_count=1130),
        tab=BandStats(unit="Mg/ha", mean=46.04, valid_raster_pixel_count=1130),
        carbon=BandStats(unit="Mg C/ha", mean=23.02, valid_raster_pixel_count=1130),
    )
    failures = _validate_formula_invariants(stats)
    assert len(failures) > 0
    assert any("AGB" in f for f in failures)


# ---------------------------------------------------------------------------
# 2. API-level tests (use the fake EE via monkeypatching)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_biomass_summary_success_response_structure(monkeypatch):
    """Successful response includes required top-level fields."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/biomass/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["mode"] == "live_earth_engine"
    assert body["status"] == "connected"
    assert body["processing_performed"] is True
    assert "study_area" in body
    assert "date_range" in body
    assert "methodology" in body
    assert "processing" in body
    assert "statistics" in body
    assert "gmw_mask" in body
    assert isinstance(body["warnings"], list)
    assert len(body["warnings"]) >= 4


@pytest.mark.asyncio
async def test_biomass_summary_numeric_values_for_reference_rh98(monkeypatch):
    """With rh98_mean=3.09 m, derived band means match the formula exactly."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE(rh98_value=3.09, pixel_count=1130))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    s = body["statistics"]
    assert s["rh98"]["mean"] == pytest.approx(3.09, rel=1e-6)

    expected_agb = 3.09 * BIOMASS_HEIGHT_TO_AGB
    assert s["agb"]["mean"] == pytest.approx(expected_agb, rel=1e-6)

    expected_bgb = expected_agb * BIOMASS_ROOT_TO_SHOOT
    assert s["bgb"]["mean"] == pytest.approx(expected_bgb, rel=1e-6)

    expected_tab = expected_agb + expected_bgb
    assert s["tab"]["mean"] == pytest.approx(expected_tab, rel=1e-6)

    expected_carbon = expected_tab * BIOMASS_TO_CARBON
    assert s["carbon"]["mean"] == pytest.approx(expected_carbon, rel=1e-6)


@pytest.mark.asyncio
async def test_biomass_summary_response_units(monkeypatch):
    """Each band block carries the correct physical unit string."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    s = body["statistics"]
    assert s["rh98"]["unit"] == "m"
    assert s["agb"]["unit"] == "Mg/ha"
    assert s["bgb"]["unit"] == "Mg/ha"
    assert s["tab"]["unit"] == "Mg/ha"
    assert s["carbon"]["unit"] == "Mg C/ha"


@pytest.mark.asyncio
async def test_biomass_summary_shared_mask_applied(monkeypatch):
    """The GMW binary mask is applied to the RH98 mosaic before stack building."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeBiomassEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/biomass/summary")

    assert fake_ee.mask_update_called is True
    assert fake_ee.gmw_image.gt_called is True
    assert fake_ee.gmw_image.self_mask_called is True


@pytest.mark.asyncio
async def test_biomass_summary_combined_reducer_settings(monkeypatch):
    """reduceRegion is called with scale=25 m, tileScale=4 and bestEffort=False."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeBiomassEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/biomass/summary")

    assert len(fake_ee.reduce_calls) == 1
    call = fake_ee.reduce_calls[0]
    assert call["scale"] == GEDI_RH98_SCALE_M
    assert call["tileScale"] == GEDI_RH98_TILE_SCALE
    assert call["bestEffort"] is False
    assert "min" in call["reducer_names"]
    assert "mean" in call["reducer_names"]
    assert "max" in call["reducer_names"]
    assert "count" in call["reducer_names"]


@pytest.mark.asyncio
async def test_biomass_summary_all_band_counts_equal_reference(monkeypatch):
    """All five band pixel counts equal the reference value (1130)."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE(pixel_count=1130))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    s = body["statistics"]
    for band in ("rh98", "agb", "bgb", "tab", "carbon"):
        assert s[band]["valid_raster_pixel_count"] == 1130, f"{band} count should be 1130"


@pytest.mark.asyncio
async def test_biomass_summary_methodology_block(monkeypatch):
    """Response methodology block contains the centralized formula coefficients."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    m = body["methodology"]
    assert m["height_to_agb_factor"] == BIOMASS_HEIGHT_TO_AGB
    assert m["root_to_shoot_ratio"] == BIOMASS_ROOT_TO_SHOOT
    assert m["biomass_to_carbon_fraction"] == BIOMASS_TO_CARBON
    assert "AGB" in m["agb_formula"]
    assert "RH98" in m["agb_formula"]


@pytest.mark.asyncio
async def test_biomass_summary_uses_correct_dataset_and_dates(monkeypatch):
    """Correct GEDI dataset ID and Jan–Mar 2020 date range are used."""
    _reset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeBiomassEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    assert fake_ee.last_collection_dataset_id == GEDI_L2A_MONTHLY
    assert fake_ee.last_filter_dates == (GEDI_RH98_BASELINE_START_DATE, GEDI_RH98_BASELINE_END_DATE)
    assert body["date_range"]["start_date"] == "2020-01-01"
    assert body["date_range"]["end_date"] == "2020-04-01"
    assert body["date_range"]["filter_convention"] == "end_exclusive"


@pytest.mark.asyncio
async def test_biomass_summary_gmw_mask_block(monkeypatch):
    """Response gmw_mask block identifies the asset, band and positive-pixels constraint."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    gm = body["gmw_mask"]
    assert gm["asset_id"] == GMW_2020
    assert gm["band"] == GMW_VALIDATED_MASK_BAND
    assert gm["positive_pixels_only"] is True


@pytest.mark.asyncio
async def test_biomass_summary_zero_values_preserved(monkeypatch):
    """Genuine zero statistics (e.g., rh98=0 m) are returned as 0.0, not null."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE(rh98_value=0.0, pixel_count=50))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    # rh98=0 → agb=0, bgb=0, tab=0, carbon=0; all must be 0.0, not null
    s = body["statistics"]
    assert s["rh98"]["mean"] == 0.0
    assert s["agb"]["mean"] == 0.0
    assert s["bgb"]["mean"] == 0.0
    assert s["tab"]["mean"] == 0.0
    assert s["carbon"]["mean"] == 0.0


@pytest.mark.asyncio
async def test_biomass_summary_missing_values_return_null(monkeypatch):
    """When reducer returns None for a stat, the response contains JSON null."""
    _reset_cache()
    _set_connected(monkeypatch)
    override = {f"{b}_{r}": None for b in [BIOMASS_BAND_RH98, BIOMASS_BAND_AGB, BIOMASS_BAND_BGB,
                                            BIOMASS_BAND_TAB, BIOMASS_BAND_CARBON]
                for r in ("min", "mean", "max", "count")}
    _set_fake_ee(monkeypatch, _FakeBiomassEE(override_reduce_outputs=override))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    s = body["statistics"]
    assert s["rh98"]["mean"] is None
    assert s["agb"]["mean"] is None
    assert s["carbon"]["mean"] is None
    assert s["rh98"]["valid_raster_pixel_count"] is None


@pytest.mark.asyncio
async def test_biomass_summary_empty_collection(monkeypatch):
    """Empty GEDI collection returns status empty_collection, processing_performed=False."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE(collection_size=0))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    assert body["status"] == "empty_collection"
    assert body["processing_performed"] is False
    assert body["statistics"] is None


@pytest.mark.asyncio
async def test_biomass_summary_empty_masked_result(monkeypatch):
    """Zero valid pixels after masking returns status masked_result_empty."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE(pixel_count=0))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    assert body["status"] == "masked_result_empty"
    assert body["processing_performed"] is True
    s = body["statistics"]
    # All stats should be null when count=0
    assert s["rh98"]["min"] is None
    assert s["rh98"]["valid_raster_pixel_count"] == 0


@pytest.mark.asyncio
async def test_biomass_summary_count_mismatch_returns_validation_failed(monkeypatch):
    """Inconsistent pixel counts across bands trigger formula_validation_failed."""
    _reset_cache()
    _set_connected(monkeypatch)
    rh98_v = 3.09
    agb_v = rh98_v * BIOMASS_HEIGHT_TO_AGB
    bgb_v = agb_v * BIOMASS_ROOT_TO_SHOOT
    tab_v = agb_v + bgb_v
    carbon_v = tab_v * BIOMASS_TO_CARBON
    override = {
        f"{BIOMASS_BAND_RH98}_min": rh98_v, f"{BIOMASS_BAND_RH98}_mean": rh98_v,
        f"{BIOMASS_BAND_RH98}_max": rh98_v, f"{BIOMASS_BAND_RH98}_count": 1130,
        f"{BIOMASS_BAND_AGB}_min": agb_v, f"{BIOMASS_BAND_AGB}_mean": agb_v,
        f"{BIOMASS_BAND_AGB}_max": agb_v, f"{BIOMASS_BAND_AGB}_count": 1131,  # mismatch
        f"{BIOMASS_BAND_BGB}_min": bgb_v, f"{BIOMASS_BAND_BGB}_mean": bgb_v,
        f"{BIOMASS_BAND_BGB}_max": bgb_v, f"{BIOMASS_BAND_BGB}_count": 1130,
        f"{BIOMASS_BAND_TAB}_min": tab_v, f"{BIOMASS_BAND_TAB}_mean": tab_v,
        f"{BIOMASS_BAND_TAB}_max": tab_v, f"{BIOMASS_BAND_TAB}_count": 1130,
        f"{BIOMASS_BAND_CARBON}_min": carbon_v, f"{BIOMASS_BAND_CARBON}_mean": carbon_v,
        f"{BIOMASS_BAND_CARBON}_max": carbon_v, f"{BIOMASS_BAND_CARBON}_count": 1130,
    }
    _set_fake_ee(monkeypatch, _FakeBiomassEE(override_reduce_outputs=override))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    assert body["status"] == "formula_validation_failed"
    assert body["processing_performed"] is True
    assert "inconsistent" in body["message"].lower()
    # statistics are included so callers can inspect the raw values
    assert body["statistics"] is not None


@pytest.mark.asyncio
async def test_biomass_summary_formula_invariant_failure(monkeypatch):
    """AGB mean that doesn't satisfy AGB = 10 × RH98 returns formula_validation_failed."""
    _reset_cache()
    _set_connected(monkeypatch)
    override = {
        f"{BIOMASS_BAND_RH98}_min": 3.09, f"{BIOMASS_BAND_RH98}_mean": 3.09,
        f"{BIOMASS_BAND_RH98}_max": 3.09, f"{BIOMASS_BAND_RH98}_count": 1130,
        f"{BIOMASS_BAND_AGB}_min": 999.0, f"{BIOMASS_BAND_AGB}_mean": 999.0,  # wrong: should be 30.9
        f"{BIOMASS_BAND_AGB}_max": 999.0, f"{BIOMASS_BAND_AGB}_count": 1130,
        f"{BIOMASS_BAND_BGB}_min": 15.14, f"{BIOMASS_BAND_BGB}_mean": 15.14,
        f"{BIOMASS_BAND_BGB}_max": 15.14, f"{BIOMASS_BAND_BGB}_count": 1130,
        f"{BIOMASS_BAND_TAB}_min": 46.04, f"{BIOMASS_BAND_TAB}_mean": 46.04,
        f"{BIOMASS_BAND_TAB}_max": 46.04, f"{BIOMASS_BAND_TAB}_count": 1130,
        f"{BIOMASS_BAND_CARBON}_min": 23.02, f"{BIOMASS_BAND_CARBON}_mean": 23.02,
        f"{BIOMASS_BAND_CARBON}_max": 23.02, f"{BIOMASS_BAND_CARBON}_count": 1130,
    }
    _set_fake_ee(monkeypatch, _FakeBiomassEE(override_reduce_outputs=override))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    assert body["status"] == "formula_validation_failed"
    assert "AGB" in body["message"]


@pytest.mark.asyncio
async def test_biomass_summary_missing_required_band(monkeypatch):
    """Missing degrade_flag band returns missing_required_bands status."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE(first_image_bands=["rh98", "quality_flag"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    assert body["status"] == "missing_required_bands"
    assert "degrade_flag" in body["message"]


@pytest.mark.asyncio
async def test_biomass_summary_quota_error(monkeypatch):
    """Quota error during reduceRegion returns status processing_failed."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE(reduce_error=RuntimeError("Noncommercial quota restricted.")))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    assert body["status"] == "processing_failed"
    assert body["connected"] is True
    msg = body["message"].lower()
    assert "quota" in msg or "restricted" in msg


@pytest.mark.asyncio
async def test_biomass_summary_authentication_failure(monkeypatch):
    """Authentication failure returns connected=False without making EE calls."""
    _reset_cache()
    monkeypatch.setattr(
        biomass_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(
            enabled=True,
            connected=False,
            status="authentication_failed",
            message="Service account authentication failed.",
        ),
    )
    fake_ee = _FakeBiomassEE()
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/gee/biomass/summary")).json()

    assert body["connected"] is False
    assert body["status"] == "authentication_failed"
    assert body["processing_performed"] is False
    assert len(fake_ee.reduce_calls) == 0


@pytest.mark.asyncio
async def test_biomass_summary_no_secret_or_path_leakage(monkeypatch):
    """Internal file paths in exception messages must not appear in the API response."""
    _reset_cache()
    _set_connected(monkeypatch)
    secret_path = "/home/user/secrets/gee-service-account.json"
    _set_fake_ee(monkeypatch, _FakeBiomassEE(reduce_error=RuntimeError(f"Error opening {secret_path}")))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body_text = (await client.get("/api/gee/biomass/summary")).text

    assert secret_path not in body_text
    assert "/home/user" not in body_text
    assert "gee-service-account" not in body_text


@pytest.mark.asyncio
async def test_biomass_summary_has_no_area_or_total_stock_fields(monkeypatch):
    """Response must not contain mangrove area or total ecosystem carbon stock fields."""
    _reset_cache()
    _set_connected(monkeypatch)
    _set_fake_ee(monkeypatch, _FakeBiomassEE())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body_text = (await client.get("/api/gee/biomass/summary")).text.lower()

    assert "total_carbon" not in body_text
    assert "mangrove_area" not in body_text
    assert "ecosystem_carbon" not in body_text
    assert "carbon_stock" not in body_text


@pytest.mark.asyncio
async def test_biomass_summary_cache_only_persists_success(monkeypatch):
    """Failed responses are not cached; a subsequent success is returned fresh."""
    _reset_cache()
    _set_connected(monkeypatch)
    failing_ee = _FakeBiomassEE(reduce_error=RuntimeError("timeout"))
    _set_fake_ee(monkeypatch, failing_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = (await client.get("/api/gee/biomass/summary")).json()
    assert first["status"] == "processing_failed"

    success_ee = _FakeBiomassEE()
    _set_fake_ee(monkeypatch, success_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        second = (await client.get("/api/gee/biomass/summary")).json()
        third = (await client.get("/api/gee/biomass/summary")).json()

    assert second["status"] == "connected"
    assert third["status"] == "connected"
    # Second and third calls should share the cached result (only one reduce call)
    assert len(success_ee.reduce_calls) == 1


@pytest.mark.asyncio
async def test_existing_health_rh98_datasets_and_analysis_still_work(monkeypatch):
    """Adding the biomass endpoint does not break any existing endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/health")
        assert health.json() == {"status": "ok"}

        analysis = await client.post(
            "/api/analyze",
            json={"study_area": "indus_delta", "start_date": "2020-01-01", "end_date": "2020-04-01"},
        )
        assert analysis.status_code == 200
        assert analysis.json()["mode"] == "demonstration"
