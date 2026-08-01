from pydantic import BaseModel, Field


class CarbonDensityStats(BaseModel):
    """Carbon density statistics from the quality-filtered GMW-masked GEDI raster."""

    mean_mg_c_ha: float | None = None
    min_mg_c_ha: float | None = None
    max_mg_c_ha: float | None = None
    valid_gedi_raster_pixel_count: int | None = None


class AreaStats(BaseModel):
    """Area statistics: mapped mangrove extent vs. valid GEDI raster coverage."""

    mapped_mangrove_area_ha: float | None = None
    valid_gedi_raster_coverage_area_ha: float | None = None
    gedi_raster_coverage_percent: float | None = None


class StockStats(BaseModel):
    """
    Carbon stock totals.

    direct_sampled_raster_carbon_mg_c: sum of (Carbon_Mg_C_ha × pixel_area_ha) over
        valid GEDI/GMW raster cells only.  Covers the sampled area, not all mangroves.

    extrapolated_ecosystem_carbon_mg_c: mean Carbon density × full mapped mangrove area.
        Assumes sparse GEDI samples are spatially representative.
        Labelled as an extrapolated estimate; not a field-validated total.
    """

    direct_sampled_raster_carbon_mg_c: float | None = None
    extrapolated_ecosystem_carbon_mg_c: float | None = None


class ReferenceComparison(BaseModel):
    """
    Comparison against an older project report value for the direct sampled stock.

    The live Earth Engine area-weighted calculation reproduces the older direct sampled
    carbon result of approximately 1,480.37 Mg C, confirming that value.  The earlier
    70.6 ha coverage estimate assumed each raster cell occupied an exact 25 m × 25 m
    ground area, whereas ee.Image.pixelArea() calculates the actual ground area of each
    cell in the geographic raster grid (64.29 ha for the Jan–Mar 2020 GEDI raster).
    """

    older_reported_direct_sampled_carbon_mg_c: float
    difference_from_older_report_mg_c: float | None = None
    note: str


class GeeCarbonStockSummaryResponse(BaseModel):
    """Response model for GET /api/gee/carbon/stock-summary."""

    connected: bool
    mode: str = "live_earth_engine"
    status: str
    study_area: dict
    date_range: dict
    carbon_density: CarbonDensityStats | None = None
    area: AreaStats | None = None
    stock: StockStats | None = None
    calculation_methods: dict | None = None
    assumptions: list[str] = Field(default_factory=list)
    processing: dict
    processing_performed: bool
    warnings: list[str] = Field(default_factory=list)
    reference_comparison: ReferenceComparison | None = None
    message: str | None = None
