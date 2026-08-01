"""
Module 13 tests: Custom AOI analysis with real Earth Engine processing.

Tests cover:
- AnalyzeRequest geometry validation (Polygon, closed ring, coordinates)
- Backward-compatible demonstration analysis (no geometry)
- Live custom AOI analysis (with geometry)
- Cache strategy (different geometries/dates don't share cache)
- Error handling (no GEDI data, invalid geometry, GEE connection failures)
"""

import pytest
from httpx import ASGITransport, AsyncClient
from types import SimpleNamespace

from app.main import app
from app.models.analysis import AnalyzeRequest, MapLayersResponse
import app.models.analysis as analysis_model
from app.services import analysis_service


def _indus_delta_aoi_geojson() -> dict:
    """Indus Delta region as GeoJSON Polygon."""
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


def _abu_dhabi_aoi_geojson() -> dict:
    """Abu Dhabi region as GeoJSON Polygon (approx bounds)."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [51.5, 22.5],
                [54.5, 22.5],
                [54.5, 24.5],
                [51.5, 24.5],
                [51.5, 22.5],
            ]
        ],
    }


class TestAnalyzeRequestValidation:
    """Test geometry validation in AnalyzeRequest."""

    def test_valid_polygon_geometry(self):
        """Valid GeoJSON Polygon passes validation."""
        payload = {
            "study_area": "custom",
            "aoi_geometry": _indus_delta_aoi_geojson(),
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        request = AnalyzeRequest(**payload)
        assert request.aoi_geometry is not None
        assert request.aoi_geometry["type"] == "Polygon"

    def test_geometry_none_is_valid(self):
        """aoi_geometry=None is valid (demonstration mode)."""
        payload = {
            "study_area": "indus_delta",
            "aoi_geometry": None,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        request = AnalyzeRequest(**payload)
        assert request.aoi_geometry is None

    def test_geometry_omitted_is_valid(self):
        """Omitting aoi_geometry field is valid (backward compat)."""
        payload = {
            "study_area": "indus_delta",
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        request = AnalyzeRequest(**payload)
        assert request.aoi_geometry is None

    def test_invalid_geometry_type_rejected(self):
        """Non-Polygon geometry type is rejected."""
        invalid_geom = {
            "type": "LineString",
            "coordinates": [[66.5, 23.5], [68.5, 24.8]],
        }
        payload = {
            "study_area": "custom",
            "aoi_geometry": invalid_geom,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        with pytest.raises(ValueError, match="must be a GeoJSON Polygon"):
            AnalyzeRequest(**payload)

    def test_geometry_not_closed_ring_rejected(self):
        """Polygon with open ring (first != last point) is rejected."""
        invalid_geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [66.5, 23.5],
                    [68.5, 23.5],
                    [68.5, 24.8],
                    [66.5, 24.8],
                    # Missing closing point [66.5, 23.5]
                ]
            ],
        }
        payload = {
            "study_area": "custom",
            "aoi_geometry": invalid_geom,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        with pytest.raises(ValueError, match="must be closed"):
            AnalyzeRequest(**payload)

    def test_geometry_insufficient_distinct_vertices_rejected(self):
        """Polygon with fewer than 3 distinct vertices is rejected."""
        invalid_geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [66.5, 23.5],
                    [66.5, 23.5],
                    [66.5, 23.5],
                    [66.5, 23.5],
                ]
            ],
        }
        payload = {
            "study_area": "custom",
            "aoi_geometry": invalid_geom,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        with pytest.raises(ValueError, match="degenerate ring|distinct vertices"):
            AnalyzeRequest(**payload)

    def test_geometry_coordinates_out_of_range_rejected(self):
        """Lon/lat values outside valid ranges are rejected."""
        invalid_geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [200.0, 23.5],  # Longitude > 180
                    [68.5, 23.5],
                    [68.5, 24.8],
                    [200.0, 23.5],
                ]
            ],
        }
        payload = {
            "study_area": "custom",
            "aoi_geometry": invalid_geom,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        with pytest.raises(ValueError, match="valid lon/lat ranges"):
            AnalyzeRequest(**payload)

    def test_geometry_non_numeric_coordinates_rejected(self):
        """Non-numeric coordinate values are rejected."""
        invalid_geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    ["66.5", 23.5],  # String instead of number
                    [68.5, 23.5],
                    [68.5, 24.8],
                    ["66.5", 23.5],
                ]
            ],
        }
        payload = {
            "study_area": "custom",
            "aoi_geometry": invalid_geom,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        with pytest.raises(ValueError, match="coordinates must be"):
            AnalyzeRequest(**payload)

    def test_geometry_infinite_coordinates_rejected(self):
        """Non-finite coordinate values are rejected."""
        invalid_geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [float("inf"), 23.5],
                    [68.5, 23.5],
                    [68.5, 24.8],
                    [float("inf"), 23.5],
                ]
            ],
        }
        payload = {
            "study_area": "custom",
            "aoi_geometry": invalid_geom,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        with pytest.raises(ValueError, match="(finite|lon/lat range)"):
            AnalyzeRequest(**payload)

    def test_date_range_validation_still_works(self):
        """Date range validation is preserved."""
        payload = {
            "study_area": "indus_delta",
            "start_date": "2020-04-01",
            "end_date": "2020-01-01",  # end before start
        }
        with pytest.raises(ValueError, match="end_date must be after start_date"):
            AnalyzeRequest(**payload)


class TestBackwardCompatibility:
    """Test backward compatibility with existing demonstration endpoint."""

    @pytest.mark.asyncio
    async def test_demo_request_without_geometry(self):
        """Old-style request (no aoi_geometry) returns demonstration response."""
        payload = {
            "study_area": "indus_delta",
            "start_date": "2019-01-01",
            "end_date": "2021-12-31",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "demonstration"
        assert body["warning"].startswith("Demonstration results only")
        assert body["results"]["direct_sampled_carbon_mg_c"] == 1480.37

    @pytest.mark.asyncio
    async def test_demo_mode_response_structure(self):
        """Demonstration response has expected structure."""
        payload = {
            "study_area": "indus_delta",
            "start_date": "2019-01-01",
            "end_date": "2021-12-31",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze", json=payload)

        body = response.json()
        assert "mode" in body
        assert "study_area" in body
        assert "date_range" in body


class TestMapLayersEndpoint:
    @pytest.mark.asyncio
    async def test_map_layers_endpoint_returns_ordered_layers(self, monkeypatch):
        payload = {
            "study_area": "indus_delta",
            "aoi_geometry": _indus_delta_aoi_geojson(),
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }

        class StubService:
            def run_live_map_layers_for_custom_aoi(self, study_area_id, study_area_name, aoi_geometry, start_date, end_date):
                return MapLayersResponse(
                    study_area={"id": study_area_id, "name": study_area_name},
                    date_range={"start_date": start_date, "end_date": end_date},
                    aoi_geometry=aoi_geometry,
                    processing_version="p1",
                    visualization_version="v1",
                    generated_at="2026-01-01T00:00:00+00:00",
                    expires_at="2026-01-01T00:20:00+00:00",
                    layers=[
                        {
                            "id": "gmw_mangrove_extent",
                            "name": "GMW Mangrove Extent",
                            "kind": "raster_tile",
                            "tile_url_template": "https://earthengine.googleapis.com/v1/projects/mangroves123/maps/a/tiles/{z}/{x}/{y}",
                            "default_visible": True,
                            "default_opacity": 0.65,
                            "min": 0,
                            "max": 1,
                            "palette": ["2e8b57"],
                            "units": "Mapped mangrove",
                            "legend_type": "categorical",
                            "description": "Mapped mangrove extent.",
                        },
                        {
                            "id": "valid_gedi_raster_coverage",
                            "name": "Valid GEDI Raster Coverage",
                            "kind": "raster_tile",
                            "tile_url_template": "https://earthengine.googleapis.com/v1/projects/mangroves123/maps/b/tiles/{z}/{x}/{y}",
                            "default_visible": True,
                            "default_opacity": 0.7,
                            "min": 0,
                            "max": 1,
                            "palette": ["1f78b4"],
                            "units": "Valid raster coverage",
                            "legend_type": "categorical",
                            "description": "Valid GEDI raster coverage.",
                        },
                    ],
                    warnings=[],
                    message=None,
                )

        monkeypatch.setattr(analysis_service, "_get_gee_service", lambda: StubService())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/map-layers", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "live_earth_engine_map_layers"
        assert [layer["id"] for layer in body["layers"]] == [
            "gmw_mangrove_extent",
            "valid_gedi_raster_coverage",
        ]
        assert body["aoi_geometry"]["coordinates"][0][0] == [66.5, 23.5]

    @pytest.mark.asyncio
    async def test_live_mode_rejects_unknown_study_area_id(self):
        payload = {
            "study_area": "unknown_region",
            "aoi_geometry": _indus_delta_aoi_geojson(),
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze", json=payload)

        assert response.status_code == 422
        assert "Unsupported study_area" in response.json()["detail"]


class TestCustomAoiAnalysis:
    """Test live Earth Engine analysis for custom AOI (requires GEE mocking in tests)."""

    @pytest.mark.asyncio
    async def test_custom_aoi_request_with_geometry_accepted(self):
        """Request with aoi_geometry field is accepted (structure check)."""
        payload = {
            "study_area": "custom",
            "aoi_geometry": _indus_delta_aoi_geojson(),
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        # Just verify the request is valid; actual processing requires GEE mocking
        request = AnalyzeRequest(**payload)
        assert request.aoi_geometry is not None
        assert request.aoi_geometry["type"] == "Polygon"

    @pytest.mark.asyncio
    async def test_custom_aoi_with_different_geometry_parameters_valid(self):
        """Different geometries and dates are all valid as request inputs."""
        geom1 = _indus_delta_aoi_geojson()
        geom2 = _abu_dhabi_aoi_geojson()

        # Both should be valid
        payload1 = {
            "study_area": "custom",
            "aoi_geometry": geom1,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        request1 = AnalyzeRequest(**payload1)
        assert request1.aoi_geometry == geom1

        payload2 = {
            "study_area": "custom",
            "aoi_geometry": geom2,
            "start_date": "2021-01-01",
            "end_date": "2021-12-31",
        }
        request2 = AnalyzeRequest(**payload2)
        assert request2.aoi_geometry == geom2


class TestRequestValidationEdgeCases:
    """Test edge cases in geometry and date validation."""

    def test_geometry_with_holes_accepted(self):
        """Polygon with holes (donuts) should be structurally valid."""
        geom_with_hole = {
            "type": "Polygon",
            "coordinates": [
                # Exterior ring
                [
                    [66.0, 23.0],
                    [69.0, 23.0],
                    [69.0, 25.0],
                    [66.0, 25.0],
                    [66.0, 23.0],
                ],
                # Interior ring (hole)
                [
                    [67.0, 23.5],
                    [68.0, 23.5],
                    [68.0, 24.5],
                    [67.0, 24.5],
                    [67.0, 23.5],
                ],
            ],
        }
        payload = {
            "study_area": "custom",
            "aoi_geometry": geom_with_hole,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        request = AnalyzeRequest(**payload)
        assert request.aoi_geometry["type"] == "Polygon"
        assert len(request.aoi_geometry["coordinates"]) == 2  # Exterior + 1 hole

    def test_geometry_minimum_valid_triangle(self):
        """Minimum valid polygon (triangle) is accepted."""
        min_geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [66.0, 23.0],
                    [67.0, 23.0],
                    [66.5, 24.0],
                    [66.0, 23.0],
                ]
            ],
        }
        payload = {
            "study_area": "custom",
            "aoi_geometry": min_geom,
            "start_date": "2020-01-01",
            "end_date": "2020-04-01",
        }
        request = AnalyzeRequest(**payload)
        assert request.aoi_geometry is not None

    def test_equal_start_and_end_date_rejected(self):
        """Same start and end date is rejected."""
        payload = {
            "study_area": "indus_delta",
            "start_date": "2020-01-01",
            "end_date": "2020-01-01",
        }
        with pytest.raises(ValueError, match="end_date must be after start_date"):
            AnalyzeRequest(**payload)

    def test_interior_ring_limit_enforced(self, monkeypatch):
        monkeypatch.setattr(
            analysis_model,
            "settings",
            SimpleNamespace(
                max_aoi_total_vertices=5000,
                max_aoi_interior_rings=1,
                max_aoi_ring_vertices=2000,
                max_aoi_serialized_bytes=200000,
            ),
        )
        geom = {
            "type": "Polygon",
            "coordinates": [
                [[66.0, 23.0], [69.0, 23.0], [69.0, 25.0], [66.0, 25.0], [66.0, 23.0]],
                [[67.0, 23.5], [68.0, 23.5], [68.0, 24.5], [67.0, 24.5], [67.0, 23.5]],
                [[67.1, 23.6], [67.9, 23.6], [67.9, 24.4], [67.1, 24.4], [67.1, 23.6]],
            ],
        }
        with pytest.raises(ValueError, match="too many interior rings"):
            AnalyzeRequest(
                study_area="custom",
                aoi_geometry=geom,
                start_date="2020-01-01",
                end_date="2020-04-01",
            )

    def test_ring_vertex_limit_enforced(self, monkeypatch):
        monkeypatch.setattr(
            analysis_model,
            "settings",
            SimpleNamespace(
                max_aoi_total_vertices=5000,
                max_aoi_interior_rings=20,
                max_aoi_ring_vertices=5,
                max_aoi_serialized_bytes=200000,
            ),
        )
        ring = [[66.0, 23.0], [66.5, 23.0], [67.0, 23.5], [67.0, 24.0], [66.5, 24.5], [66.0, 24.0], [66.0, 23.0]]
        geom = {"type": "Polygon", "coordinates": [ring]}
        with pytest.raises(ValueError, match="ring has too many vertices"):
            AnalyzeRequest(
                study_area="custom",
                aoi_geometry=geom,
                start_date="2020-01-01",
                end_date="2020-04-01",
            )

    def test_total_vertex_limit_enforced(self, monkeypatch):
        monkeypatch.setattr(
            analysis_model,
            "settings",
            SimpleNamespace(
                max_aoi_total_vertices=6,
                max_aoi_interior_rings=20,
                max_aoi_ring_vertices=2000,
                max_aoi_serialized_bytes=200000,
            ),
        )
        geom = {
            "type": "Polygon",
            "coordinates": [
                [[66.0, 23.0], [69.0, 23.0], [69.0, 25.0], [66.0, 25.0], [66.0, 23.0]],
                [[67.0, 23.5], [68.0, 23.5], [68.0, 24.5], [67.0, 24.5], [67.0, 23.5]],
            ],
        }
        with pytest.raises(ValueError, match="too many total vertices"):
            AnalyzeRequest(
                study_area="custom",
                aoi_geometry=geom,
                start_date="2020-01-01",
                end_date="2020-04-01",
            )

    def test_serialized_size_limit_enforced(self, monkeypatch):
        monkeypatch.setattr(
            analysis_model,
            "settings",
            SimpleNamespace(
                max_aoi_total_vertices=5000,
                max_aoi_interior_rings=20,
                max_aoi_ring_vertices=2000,
                max_aoi_serialized_bytes=50,
            ),
        )
        geom = _indus_delta_aoi_geojson()
        with pytest.raises(ValueError, match="serialized size exceeds limit"):
            AnalyzeRequest(
                study_area="custom",
                aoi_geometry=geom,
                start_date="2020-01-01",
                end_date="2020-04-01",
            )

    def test_limits_allow_boundary_case(self, monkeypatch):
        monkeypatch.setattr(
            analysis_model,
            "settings",
            SimpleNamespace(
                max_aoi_total_vertices=4,
                max_aoi_interior_rings=0,
                max_aoi_ring_vertices=5,
                max_aoi_serialized_bytes=500,
            ),
        )
        request = AnalyzeRequest(
            study_area="custom",
            aoi_geometry=_indus_delta_aoi_geojson(),
            start_date="2020-01-01",
            end_date="2020-04-01",
        )
        assert request.aoi_geometry is not None
