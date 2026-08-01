from pydantic import BaseModel, Field


class BandStats(BaseModel):
    """Per-band summary statistics from a single Earth Engine reduceRegion call."""

    unit: str
    min: float | None = None
    mean: float | None = None
    max: float | None = None
    valid_raster_pixel_count: int | None = None


class BiomassStatistics(BaseModel):
    """Statistics for all five bands in the mangrove biomass image stack."""

    rh98: BandStats
    agb: BandStats
    bgb: BandStats
    tab: BandStats
    carbon: BandStats


class GeeBiomassSummaryResponse(BaseModel):
    """Response model for GET /api/gee/biomass/summary."""

    connected: bool
    mode: str = "live_earth_engine"
    status: str
    study_area: dict
    date_range: dict
    methodology: dict
    statistics: BiomassStatistics | None = None
    gmw_mask: dict | None = None
    processing: dict
    processing_performed: bool
    warnings: list[str] = Field(default_factory=list)
    message: str | None = None
