from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class GmwLayerResponse(BaseModel):
    mode: Literal["live_earth_engine_gmw_layer"] = "live_earth_engine_gmw_layer"
    study_area: str
    gmw_asset_id: str
    tile_url_template: str
    default_visible: bool = True
    default_opacity: float = Field(0.5, ge=0.0, le=1.0)
    palette: list[str] = Field(default_factory=lambda: ["2e8b57"])
    label: str = "Mangrove Area (Global Mangrove Watch)"


class GmwCoverageCheckRequest(BaseModel):
    study_area: Literal["indus_delta", "abu_dhabi", "custom"] = "custom"
    aoi_geometry: dict[str, Any]

    @model_validator(mode="after")
    def validate_polygon_geometry(self):
        geometry = self.aoi_geometry
        if not isinstance(geometry, dict):
            raise ValueError("aoi_geometry must be a GeoJSON object")

        if geometry.get("type") != "Polygon":
            raise ValueError("aoi_geometry must be a GeoJSON Polygon")

        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) == 0:
            raise ValueError("aoi_geometry coordinates must be a non-empty array")

        exterior_ring = coordinates[0]
        if not isinstance(exterior_ring, list) or len(exterior_ring) < 4:
            raise ValueError("aoi_geometry exterior ring must have at least 4 points (closed ring)")

        if exterior_ring[0] != exterior_ring[-1]:
            raise ValueError("aoi_geometry exterior ring must be closed (first and last points identical)")

        return self


class GmwCoverageCheckResponse(BaseModel):
    mode: Literal["live_earth_engine_gmw_coverage_check"] = "live_earth_engine_gmw_coverage_check"
    study_area: str
    has_mangroves: bool
    mapped_mangrove_area_ha: float | None = None
    message: str | None = None
