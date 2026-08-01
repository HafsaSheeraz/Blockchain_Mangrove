from datetime import date
from typing import Any, Optional, Literal
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.core.config import settings


class AnalyzeRequest(BaseModel):
    study_area: str = Field(
        ...,
        description="Study area identifier. 'indus_delta' for backward-compatible demo; or any identifier for custom AOI mode.",
    )
    start_date: date = Field(..., description="Start date in ISO format (YYYY-MM-DD).")
    end_date: date = Field(..., description="End date in ISO format (YYYY-MM-DD).")
    aoi_geometry: Optional[dict[str, Any]] = Field(
        None,
        description="GeoJSON Polygon for custom AOI (Module 13). If provided, triggers live Earth Engine processing. Coordinates in [lon, lat] order.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "study_area": "indus_delta",
                "start_date": "2019-01-01",
                "end_date": "2021-12-31",
            }
        }
    )

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        max_date_range_days = getattr(settings, "max_aoi_date_range_days", None)
        if max_date_range_days is not None and (self.end_date - self.start_date).days > max_date_range_days:
            raise ValueError(
                f"Date range exceeds the maximum allowed length of {max_date_range_days} days"
            )
        return self

    @model_validator(mode="after")
    def validate_aoi_geometry(self):
        if self.aoi_geometry is None:
            return self

        if not isinstance(self.aoi_geometry, dict):
            raise ValueError("aoi_geometry must be a GeoJSON object")

        geometry_type = self.aoi_geometry.get("type")
        if geometry_type != "Polygon":
            raise ValueError("aoi_geometry must be a GeoJSON Polygon")

        coordinates = self.aoi_geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) == 0:
            raise ValueError("aoi_geometry coordinates must be a non-empty array")
        if len(coordinates) - 1 > settings.max_aoi_interior_rings:
            raise ValueError(
                f"aoi_geometry has too many interior rings; maximum allowed is {settings.max_aoi_interior_rings}"
            )

        serialized_size = len(json.dumps(self.aoi_geometry, separators=(",", ":")).encode("utf-8"))
        if serialized_size > settings.max_aoi_serialized_bytes:
            raise ValueError(
                f"aoi_geometry serialized size exceeds limit of {settings.max_aoi_serialized_bytes} bytes"
            )

        exterior_ring = coordinates[0]
        if not isinstance(exterior_ring, list) or len(exterior_ring) < 4:
            raise ValueError("aoi_geometry exterior ring must have at least 4 points (closed ring)")

        first = exterior_ring[0]
        last = exterior_ring[-1]
        if first != last:
            raise ValueError("aoi_geometry exterior ring must be closed (first and last points identical)")

        total_vertices = 0

        for ring in coordinates:
            if not isinstance(ring, list):
                raise ValueError("aoi_geometry rings must be arrays of coordinate pairs")
            if len(ring) < 4:
                raise ValueError("aoi_geometry rings must have at least 4 points (closed ring)")
            if ring[0] != ring[-1]:
                raise ValueError("aoi_geometry rings must be closed (first and last points identical)")
            if len(ring) > settings.max_aoi_ring_vertices:
                raise ValueError(
                    f"aoi_geometry ring has too many vertices; maximum allowed is {settings.max_aoi_ring_vertices}"
                )
            distinct_points = len(set(tuple(p) for p in ring[:-1]))
            if distinct_points < 3:
                raise ValueError("aoi_geometry contains a degenerate ring with fewer than 3 distinct vertices")
            total_vertices += len(ring) - 1
            for point in ring:
                if not isinstance(point, (list, tuple)) or len(point) < 2:
                    raise ValueError("aoi_geometry coordinates must be [lon, lat] pairs")
                lon, lat = point[0], point[1]
                if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                    raise ValueError("aoi_geometry coordinates must be numbers")
                if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                    raise ValueError("aoi_geometry coordinates must be valid lon/lat ranges")
                if not (isinstance(lon, float) and isinstance(lat, float)):
                    if not (isinstance(lon, int) and isinstance(lat, int)):
                        raise ValueError("aoi_geometry coordinates must be numeric")
                import math
                if not math.isfinite(lon) or not math.isfinite(lat):
                    raise ValueError("aoi_geometry coordinates must be finite numbers")

        if total_vertices > settings.max_aoi_total_vertices:
            raise ValueError(
                f"aoi_geometry has too many total vertices; maximum allowed is {settings.max_aoi_total_vertices}"
            )

        area_bounds = self._compute_bounds(exterior_ring)
        if area_bounds["width"] <= 0 or area_bounds["height"] <= 0:
            raise ValueError("aoi_geometry must have non-zero area")

        return self

    @staticmethod
    def _compute_bounds(ring: list) -> dict:
        lons = [p[0] for p in ring]
        lats = [p[1] for p in ring]
        return {
            "min_lon": min(lons),
            "max_lon": max(lons),
            "min_lat": min(lats),
            "max_lat": max(lats),
            "width": max(lons) - min(lons),
            "height": max(lats) - min(lats),
        }


class StudyAreaInfo(BaseModel):
    id: str
    name: str


class DateRangeInfo(BaseModel):
    start_date: date
    end_date: date


class AnalysisResults(BaseModel):
    valid_gedi_samples: int
    mean_rh98_m: float
    min_rh98_m: float
    max_rh98_m: float
    mean_agb_mg_ha: float
    mean_bgb_mg_ha: float
    mean_carbon_mg_c_ha: float
    min_carbon_mg_c_ha: float
    max_carbon_mg_c_ha: float
    mangrove_area_ha: float
    gedi_sampled_coverage_percent: float
    direct_sampled_carbon_mg_c: float
    extrapolated_total_carbon_mg_c: float


class MethodologyInfo(BaseModel):
    agb_formula: str
    bgb_formula: str
    tab_formula: str
    carbon_formula: str


class AnalyzeResponse(BaseModel):
    mode: str
    study_area: StudyAreaInfo
    date_range: DateRangeInfo
    datasets: list[str]
    results: AnalysisResults
    methodology: MethodologyInfo
    warning: str


class CustomAoiAnalyzeResponse(BaseModel):
    """Response for live Earth Engine custom AOI analysis (Module 13)."""
    mode: str = Field(..., description="Should be 'live_earth_engine_custom_aoi'")
    study_area: StudyAreaInfo
    date_range: DateRangeInfo
    datasets: list[str]
    results: Optional[AnalysisResults] = Field(None, description="Analysis results (None if processing failed)")
    methodology: Optional[MethodologyInfo] = Field(None, description="Methodology info (None if processing failed)")
    warning: str
    assumptions: Optional[list[str]] = Field(None, description="Scientific assumptions for interpretation")
    aoi_geometry: Optional[dict[str, Any]] = Field(None, description="The submitted GeoJSON Polygon AOI")


class MapLayerDescriptor(BaseModel):
    id: str
    name: str
    kind: Literal["raster_tile"] = "raster_tile"
    tile_url_template: str
    default_visible: bool
    default_opacity: float = Field(..., ge=0.0, le=1.0)
    min: float | int
    max: float | int
    palette: list[str]
    units: str
    legend_type: Literal["categorical", "continuous"] = "continuous"
    description: str


class MapLayersResponse(BaseModel):
    mode: Literal["live_earth_engine_map_layers"] = "live_earth_engine_map_layers"
    study_area: StudyAreaInfo
    date_range: DateRangeInfo
    aoi_geometry: dict[str, Any]
    processing_version: str
    visualization_version: str
    generated_at: str
    expires_at: str
    layers: list[MapLayerDescriptor] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    message: str | None = None


class ExportMetric(BaseModel):
    value: float | int | None
    unit: str


class ExportScientificResults(BaseModel):
    valid_gedi_samples: ExportMetric
    mean_rh98_m: ExportMetric
    min_rh98_m: ExportMetric
    max_rh98_m: ExportMetric
    mean_agb_mg_ha: ExportMetric
    mean_bgb_mg_ha: ExportMetric
    mean_carbon_mg_c_ha: ExportMetric
    min_carbon_mg_c_ha: ExportMetric
    max_carbon_mg_c_ha: ExportMetric
    mangrove_area_ha: ExportMetric
    gedi_sampled_coverage_percent: ExportMetric
    direct_sampled_carbon_mg_c: ExportMetric
    extrapolated_total_carbon_mg_c: ExportMetric


class ExportDateRangeInfo(BaseModel):
    start_date: date
    end_date: date
    convention: Literal["end_exclusive"] = "end_exclusive"


class ExportAoiBounds(BaseModel):
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


class ExportDocument(BaseModel):
    report_schema_version: Literal["module15_v1"] = "module15_v1"
    generated_at_utc: str
    processing_mode: str
    processing_version: str
    study_area: StudyAreaInfo
    date_range: ExportDateRangeInfo
    coordinate_order: Literal["longitude_latitude"] = "longitude_latitude"
    aoi_geometry: dict[str, Any]
    aoi_bounds: ExportAoiBounds
    vertex_count: int
    datasets: list[str]
    results: Optional[ExportScientificResults] = None
    methodology: Optional[MethodologyInfo] = None
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    no_data: bool = False
