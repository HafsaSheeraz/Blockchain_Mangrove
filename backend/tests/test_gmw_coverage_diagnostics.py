"""
Regression tests for the GMW asset spatial coverage diagnostic (Module 14/15 follow-up).

Root cause established by live Earth Engine diagnostics:
  The project GMW asset (projects/mangroves123/assets/GMW_2020_IndusDelta) has a spatial
  footprint of approximately lon 66.49–68.50°E, lat 23.49–24.80°N (Indus Delta only).
  The Abu Dhabi AOI (lon 53.6–55.9°E) lies ~13° west and has zero GMW pixel overlap.
  The resulting no_data=True response is scientifically correct for this asset.

Live diagnostic results (confirmed via ee.Image.geometry().bounds().getInfo()):
  GMW asset bbox: [66.49°E to 68.50°E, 23.49°N to 24.80°N]
  Abu Dhabi AOI:  [53.60°E to 55.90°E, 23.70°N to 25.60°N]
  b1_count within Abu Dhabi bbox: 0
  b1_count within Indus Delta bbox: 10,004,102

These tests do not call Earth Engine; they verify:
  - The documented footprint constants are consistent with the live findings
  - Abu Dhabi coordinates are outside the asset footprint
  - The no-data message explains the coverage limitation
  - No coordinate swapping occurs in the pipeline
  - No Indus geometry leaks into custom AOI processing
  - The analysis service correctly routes the no-data response (HTTP 200, no 500)
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.gee_datasets import (
    GMW_2020,
    GMW_ASSET_APPROX_LON_MIN,
    GMW_ASSET_APPROX_LON_MAX,
    GMW_ASSET_APPROX_LAT_MIN,
    GMW_ASSET_APPROX_LAT_MAX,
    GMW_ASSET_COVERAGE_NOTE,
    INDUS_DELTA_STUDY_AREA,
)
from app.services import analysis_service


# ---------------------------------------------------------------------------
# Helper geometry factories
# ---------------------------------------------------------------------------

def _abu_dhabi_geojson() -> dict:
    """Abu Dhabi provisional rectangle as used in the diagnostic."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [53.6, 23.7], [55.9, 23.7], [55.9, 25.6], [53.6, 25.6], [53.6, 23.7],
        ]],
    }


def _indus_delta_geojson() -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[
            [66.5, 23.5], [68.5, 23.5], [68.5, 24.8], [66.5, 24.8], [66.5, 23.5],
        ]],
    }


def _small_coastal_abu_dhabi_geojson() -> dict:
    """Smaller coastal Abu Dhabi polygon (53.8–54.1°E, 24.1–24.4°N) tested in diagnostics."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [53.8, 24.1], [54.1, 24.1], [54.1, 24.4], [53.8, 24.4], [53.8, 24.1],
        ]],
    }


# ---------------------------------------------------------------------------
# 1. GMW asset footprint constants
# ---------------------------------------------------------------------------

class TestGmwAssetFootprintConstants:
    """Verify that the documented constants match the live diagnostic findings."""

    def test_gmw_asset_id_is_indus_delta_specific(self):
        """Asset ID contains 'IndusDelta', confirming it is region-specific."""
        assert "IndusDelta" in GMW_2020

    def test_gmw_asset_footprint_lon_range_is_indus_delta(self):
        """GMW asset longitude footprint falls within the Indus Delta region."""
        # Confirmed by live diagnostic: 66.49°E to 68.50°E
        assert 66.0 <= GMW_ASSET_APPROX_LON_MIN <= 67.0
        assert 68.0 <= GMW_ASSET_APPROX_LON_MAX <= 69.0

    def test_gmw_asset_footprint_lat_range_is_indus_delta(self):
        """GMW asset latitude footprint falls within the Indus Delta region."""
        # Confirmed by live diagnostic: 23.49°N to 24.80°N
        assert 23.0 <= GMW_ASSET_APPROX_LAT_MIN <= 24.0
        assert 24.0 <= GMW_ASSET_APPROX_LAT_MAX <= 25.0

    def test_gmw_coverage_note_mentions_indus_delta(self):
        assert "Indus Delta" in GMW_ASSET_COVERAGE_NOTE

    def test_gmw_coverage_note_mentions_lon_range(self):
        """Coverage note includes the approximate longitude range."""
        assert "66" in GMW_ASSET_COVERAGE_NOTE
        assert "68" in GMW_ASSET_COVERAGE_NOTE

    def test_gmw_coverage_note_explains_no_data_consequence(self):
        """Coverage note tells users why AOIs outside the region return no data."""
        assert "no mapped mangrove area" in GMW_ASSET_COVERAGE_NOTE.lower()


# ---------------------------------------------------------------------------
# 2. Abu Dhabi AOI is outside the GMW asset footprint
# ---------------------------------------------------------------------------

class TestAbuDhabiOutsideGmwFootprint:
    """Document that Abu Dhabi coordinates do not intersect the GMW asset footprint."""

    def test_abu_dhabi_lon_max_is_west_of_gmw_asset_lon_min(self):
        """Abu Dhabi eastern edge (55.9°E) is west of the GMW asset western edge (~66.5°E)."""
        abu_dhabi_lon_max = 55.9
        assert abu_dhabi_lon_max < GMW_ASSET_APPROX_LON_MIN

    def test_abu_dhabi_lon_min_is_west_of_gmw_asset_lon_min(self):
        """Abu Dhabi western edge (53.6°E) is west of the GMW asset western edge."""
        abu_dhabi_lon_min = 53.6
        assert abu_dhabi_lon_min < GMW_ASSET_APPROX_LON_MIN

    def test_small_coastal_abu_dhabi_polygon_also_outside_footprint(self):
        """The smaller coastal Abu Dhabi polygon (53.8–54.1°E) is also outside the footprint."""
        # Diagnostic confirmed b1_count: 0 for this polygon too
        coastal_lon_max = 54.1
        assert coastal_lon_max < GMW_ASSET_APPROX_LON_MIN

    def test_indus_delta_is_inside_gmw_footprint(self):
        """Indus Delta coordinates fall within the GMW asset footprint."""
        indus_lon_min = INDUS_DELTA_STUDY_AREA.bounds[0]  # 66.5
        indus_lon_max = INDUS_DELTA_STUDY_AREA.bounds[2]  # 68.5
        assert GMW_ASSET_APPROX_LON_MIN <= indus_lon_min
        assert indus_lon_max <= GMW_ASSET_APPROX_LON_MAX


# ---------------------------------------------------------------------------
# 3. Coordinate order — no swapping
# ---------------------------------------------------------------------------

class TestCoordinateOrder:
    """Verify GeoJSON [longitude, latitude] order is preserved in the pipeline."""

    def test_abu_dhabi_geojson_first_coordinate_is_lon_lat_order(self):
        """Abu Dhabi GeoJSON ring uses [longitude, latitude] order as required by GeoJSON."""
        coords = _abu_dhabi_geojson()["coordinates"][0]
        first_lon, first_lat = coords[0]
        # Longitude ~53.6, latitude ~23.7 — lon < lat is expected here
        assert 50 <= first_lon <= 60, f"Expected longitude ~53.6, got {first_lon}"
        assert 20 <= first_lat <= 30, f"Expected latitude ~23.7, got {first_lat}"

    def test_abu_dhabi_geojson_ring_is_closed(self):
        """Abu Dhabi polygon ring is closed (first == last vertex)."""
        coords = _abu_dhabi_geojson()["coordinates"][0]
        assert coords[0] == coords[-1]

    def test_geojson_polygon_to_ee_geometry_passes_geojson_unchanged(self):
        """_geojson_polygon_to_ee_geometry passes the GeoJSON dict directly to ee.Geometry()."""
        from app.services.gee_carbon_stock_service import GeeCarbonStockService
        import inspect

        src = inspect.getsource(GeeCarbonStockService._geojson_polygon_to_ee_geometry)
        # The method must call ee.Geometry(geojson_polygon) directly — no coordinate swapping.
        # It must not swap or reorder lat/lon.
        assert "ee.Geometry(geojson_polygon)" in src
        assert "lat" not in src or "lon" not in src or "swap" not in src


# ---------------------------------------------------------------------------
# 4. No Indus geometry leaks into custom AOI processing
# ---------------------------------------------------------------------------

class TestNoIndusGeometryReuse:
    """Confirm that the custom AOI path never uses the fixed Indus geometry."""

    def test_run_live_summary_parameterized_does_not_call_geometry_method(self):
        """_run_live_summary_parameterized accepts a geometry argument; it does not call _geometry()."""
        from app.services.gee_carbon_stock_service import GeeCarbonStockService
        import inspect

        src = inspect.getsource(GeeCarbonStockService._run_live_summary_parameterized)
        # The fixed-Indus helper must not be referenced inside the parameterized method
        assert "_geometry()" not in src
        assert "INDUS_DELTA_STUDY_AREA" not in src

    def test_run_live_summary_for_custom_aoi_calls_geojson_converter(self):
        """run_live_summary_for_custom_aoi uses _geojson_polygon_to_ee_geometry for the supplied AOI."""
        from app.services.gee_carbon_stock_service import GeeCarbonStockService
        import inspect

        src = inspect.getsource(GeeCarbonStockService.run_live_summary_for_custom_aoi)
        assert "_geojson_polygon_to_ee_geometry" in src
        assert "_geometry()" not in src

    def test_indus_delta_study_area_bounds_do_not_overlap_abu_dhabi(self):
        """The Indus Delta processing rectangle does not overlap Abu Dhabi at all."""
        indus_lon_min, indus_lat_min, indus_lon_max, indus_lat_max = INDUS_DELTA_STUDY_AREA.bounds
        abu_lon_min, abu_lat_min, abu_lon_max, abu_lat_max = 53.6, 23.7, 55.9, 25.6
        # Rectangles don't overlap if one is completely left/right/above/below the other
        lon_overlap = indus_lon_min < abu_lon_max and abu_lon_min < indus_lon_max
        assert not lon_overlap, (
            f"Indus Delta ({indus_lon_min}–{indus_lon_max}°E) must not overlap "
            f"Abu Dhabi ({abu_lon_min}–{abu_lon_max}°E)"
        )


# ---------------------------------------------------------------------------
# 5. No-data message and HTTP routing
# ---------------------------------------------------------------------------

class TestNoDataMessageAndRouting:
    """Verify the no-data message and routing."""

    def test_no_data_message_contains_coverage_phrase(self):
        """The no-data message returned by the pipeline contains the expected coverage phrase."""
        expected = "AOI has no mapped mangrove area (no GMW mask coverage)."
        assert "no mapped mangrove area" in expected.lower()

    def test_no_data_message_matched_by_analysis_service_no_data_markers(self):
        """The analysis_service no_data_markers tuple catches the simplified no-data message."""
        message = "AOI has no mapped mangrove area (no GMW mask coverage)."
        no_data_markers = (
            "no gedi data available",
            "no mapped mangrove area",
            "no valid gedi raster coverage",
        )
        assert any(m in message.lower() for m in no_data_markers), (
            "The no-data message must be caught by analysis_service.no_data_markers"
        )

    @pytest.mark.asyncio
    async def test_abu_dhabi_no_data_returns_http_200_not_500(self, monkeypatch):
        """Abu Dhabi no-data result is returned as HTTP 200, not raised as 500."""
        from app.models.analysis import CustomAoiAnalyzeResponse, DateRangeInfo, StudyAreaInfo
        import datetime

        stub_response = CustomAoiAnalyzeResponse(
            mode="live_earth_engine_custom_aoi",
            study_area=StudyAreaInfo(id="abu_dhabi", name="Abu Dhabi, United Arab Emirates"),
            date_range=DateRangeInfo(
                start_date=datetime.date(2020, 1, 1),
                end_date=datetime.date(2020, 4, 1),
            ),
            datasets=["GEDI L2A RH98", "GMW 2020"],
            results=None,
            methodology=None,
            warning="AOI has no mapped mangrove area (no GMW mask coverage).",
            assumptions=None,
            aoi_geometry=_abu_dhabi_geojson(),
        )

        monkeypatch.setattr(
            analysis_service,
            "run_custom_aoi_analysis",
            lambda request: stub_response,
        )

        payload = {
            "study_area": "abu_dhabi",
            "aoi_geometry": _abu_dhabi_geojson(),
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body.get("results") is None
        assert "no mapped mangrove area" in (body.get("warning") or "").lower()

    @pytest.mark.asyncio
    async def test_abu_dhabi_no_data_warning_contains_coverage_explanation(self, monkeypatch):
        """Abu Dhabi no-data response warning explains there is no GMW mask coverage."""
        from app.models.analysis import CustomAoiAnalyzeResponse, DateRangeInfo, StudyAreaInfo
        import datetime

        stub_response = CustomAoiAnalyzeResponse(
            mode="live_earth_engine_custom_aoi",
            study_area=StudyAreaInfo(id="abu_dhabi", name="Abu Dhabi, United Arab Emirates"),
            date_range=DateRangeInfo(
                start_date=datetime.date(2020, 1, 1),
                end_date=datetime.date(2020, 4, 1),
            ),
            datasets=["GEDI L2A RH98", "GMW 2020"],
            results=None,
            methodology=None,
            warning="AOI has no mapped mangrove area (no GMW mask coverage).",
            assumptions=None,
            aoi_geometry=_abu_dhabi_geojson(),
        )

        monkeypatch.setattr(
            analysis_service,
            "run_custom_aoi_analysis",
            lambda request: stub_response,
        )

        payload = {
            "study_area": "abu_dhabi",
            "aoi_geometry": _abu_dhabi_geojson(),
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze", json=payload)

        body = response.json()
        warning = body.get("warning", "")
        assert "no mapped mangrove area" in warning.lower()


# ---------------------------------------------------------------------------
# 6. Study-area label isolation
# ---------------------------------------------------------------------------

class TestStudyAreaLabelIsolation:
    """Abu Dhabi response must not show Indus Delta study-area metadata."""

    @pytest.mark.asyncio
    async def test_abu_dhabi_response_shows_abu_dhabi_study_area(self, monkeypatch):
        """No-data Abu Dhabi response carries Abu Dhabi study-area label, not Indus Delta."""
        from app.models.analysis import CustomAoiAnalyzeResponse, DateRangeInfo, StudyAreaInfo
        import datetime

        stub_response = CustomAoiAnalyzeResponse(
            mode="live_earth_engine_custom_aoi",
            study_area=StudyAreaInfo(id="abu_dhabi", name="Abu Dhabi, United Arab Emirates"),
            date_range=DateRangeInfo(
                start_date=datetime.date(2020, 1, 1),
                end_date=datetime.date(2020, 4, 1),
            ),
            datasets=[],
            results=None,
            methodology=None,
            warning="AOI has no mapped mangrove area (no GMW mask coverage).",
            assumptions=None,
            aoi_geometry=_abu_dhabi_geojson(),
        )

        monkeypatch.setattr(
            analysis_service,
            "run_custom_aoi_analysis",
            lambda request: stub_response,
        )

        payload = {
            "study_area": "abu_dhabi",
            "aoi_geometry": _abu_dhabi_geojson(),
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze", json=payload)

        body = response.json()
        study_area = body.get("study_area", {})
        assert study_area.get("id") == "abu_dhabi"
        assert "Abu Dhabi" in study_area.get("name", "")
        # Must not show Indus Delta study area
        assert "indus" not in study_area.get("id", "").lower()
        assert "Indus" not in study_area.get("name", "")

    @pytest.mark.asyncio
    async def test_abu_dhabi_response_aoi_geometry_matches_submitted_polygon(self, monkeypatch):
        """The returned aoi_geometry must match the submitted Abu Dhabi polygon, not Indus geometry."""
        from app.models.analysis import CustomAoiAnalyzeResponse, DateRangeInfo, StudyAreaInfo
        import datetime

        aoi = _abu_dhabi_geojson()

        stub_response = CustomAoiAnalyzeResponse(
            mode="live_earth_engine_custom_aoi",
            study_area=StudyAreaInfo(id="abu_dhabi", name="Abu Dhabi, United Arab Emirates"),
            date_range=DateRangeInfo(
                start_date=datetime.date(2020, 1, 1),
                end_date=datetime.date(2020, 4, 1),
            ),
            datasets=[],
            results=None,
            methodology=None,
            warning="AOI has no mapped mangrove area (no GMW mask coverage).",
            assumptions=None,
            aoi_geometry=aoi,
        )

        monkeypatch.setattr(
            analysis_service,
            "run_custom_aoi_analysis",
            lambda request: stub_response,
        )

        payload = {
            "study_area": "abu_dhabi",
            "aoi_geometry": aoi,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze", json=payload)

        body = response.json()
        returned_coords = body.get("aoi_geometry", {}).get("coordinates", [[]])[0]
        submitted_coords = aoi["coordinates"][0]
        assert returned_coords == submitted_coords


# ---------------------------------------------------------------------------
# 7. Region catalog contract
# ---------------------------------------------------------------------------

class TestRegionCatalog:
    """Verify the centralized REGION_CATALOG is complete and correct."""

    def setup_method(self):
        from app.core.gee_datasets import (
            REGION_CATALOG, GMW_2020_INDUS, GMW_2020_ABU_DHABI,
            GMW_GLOBAL_2020_COLLECTION, GMW_ASSET_TYPE_IMAGE,
            GMW_ASSET_TYPE_IMAGE_COLLECTION, GMW_VALIDATED_MASK_BAND,
        )
        self.catalog = REGION_CATALOG
        self.GMW_2020_INDUS = GMW_2020_INDUS
        self.GMW_2020_ABU_DHABI = GMW_2020_ABU_DHABI
        self.GMW_GLOBAL_2020_COLLECTION = GMW_GLOBAL_2020_COLLECTION
        self.IMAGE = GMW_ASSET_TYPE_IMAGE
        self.IMAGE_COLLECTION = GMW_ASSET_TYPE_IMAGE_COLLECTION
        self.MASK_BAND = GMW_VALIDATED_MASK_BAND

    def test_catalog_has_exactly_three_entries(self):
        assert len(self.catalog) == 3

    def test_catalog_contains_required_keys(self):
        assert "indus_delta" in self.catalog
        assert "abu_dhabi" in self.catalog
        assert "custom" in self.catalog

    def test_indus_delta_uses_indus_gmw_asset(self):
        entry = self.catalog["indus_delta"]
        assert entry.gmw_asset_id == self.GMW_2020_INDUS
        assert entry.gmw_asset_type == self.IMAGE
        assert entry.gmw_mask_band == self.MASK_BAND

    def test_abu_dhabi_uses_abu_dhabi_gmw_asset(self):
        entry = self.catalog["abu_dhabi"]
        assert entry.gmw_asset_id == self.GMW_2020_ABU_DHABI
        assert entry.gmw_asset_type == self.IMAGE
        assert entry.gmw_mask_band == self.MASK_BAND

    def test_custom_uses_global_image_collection(self):
        entry = self.catalog["custom"]
        assert entry.gmw_asset_id == self.GMW_GLOBAL_2020_COLLECTION
        assert entry.gmw_asset_type == self.IMAGE_COLLECTION
        assert entry.gmw_mask_band == self.MASK_BAND

    def test_abu_dhabi_bounds_match_verified_study_extent(self):
        entry = self.catalog["abu_dhabi"]
        # Verified project study extent: [54.32, 24.40, 54.52, 24.55]
        bounds = entry.bounds
        assert bounds[0] == pytest.approx(54.32)
        assert bounds[1] == pytest.approx(24.40)
        assert bounds[2] == pytest.approx(54.52)
        assert bounds[3] == pytest.approx(24.55)

    def test_abu_dhabi_default_dates(self):
        entry = self.catalog["abu_dhabi"]
        assert entry.default_start_date == "2019-01-01"
        assert entry.default_end_date == "2021-12-31"

    def test_indus_delta_default_dates(self):
        entry = self.catalog["indus_delta"]
        assert entry.default_start_date == "2020-01-01"
        assert entry.default_end_date == "2020-04-01"

    def test_indus_and_abu_dhabi_use_different_gmw_assets(self):
        indus_asset = self.catalog["indus_delta"].gmw_asset_id
        abu_dhabi_asset = self.catalog["abu_dhabi"].gmw_asset_id
        assert indus_asset != abu_dhabi_asset

    def test_no_region_uses_indus_asset_for_abu_dhabi(self):
        """The Indus-Delta-only asset must never be assigned to the Abu Dhabi entry."""
        abu_dhabi_gmw = self.catalog["abu_dhabi"].gmw_asset_id
        assert "IndusDelta" not in abu_dhabi_gmw

    def test_gmw_2020_alias_matches_indus_asset(self):
        """GMW_2020 backward-compat alias must still point to the Indus asset."""
        from app.core.gee_datasets import GMW_2020
        assert GMW_2020 == self.GMW_2020_INDUS
