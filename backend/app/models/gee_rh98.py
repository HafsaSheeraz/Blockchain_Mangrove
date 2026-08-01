from pydantic import BaseModel, Field


class Rh98Stats(BaseModel):
    rh98_min_m: float | None = None
    rh98_mean_m: float | None = None
    rh98_max_m: float | None = None
    valid_gedi_raster_pixel_count: int | None = None


class Rh98ReferenceResults(BaseModel):
    whole_aoi: Rh98Stats
    mangrove_masked: Rh98Stats


class Rh98ReferenceDifferences(BaseModel):
    whole_aoi: Rh98Stats
    mangrove_masked: Rh98Stats


class GeeRh98SummaryResponse(BaseModel):
    connected: bool
    mode: str = "live_earth_engine"
    status: str
    study_area: dict
    date_range: dict
    dataset: dict
    filters: dict
    whole_aoi: Rh98Stats | None = None
    mangrove_masked: Rh98Stats | None = None
    gmw_mask: dict | None = None
    filtered_monthly_image_count: int | None = None
    baseline_purpose: str
    reference_results: Rh98ReferenceResults
    difference_from_reference: Rh98ReferenceDifferences | None = None
    comparison_asset: dict | None = None
    processing_performed: bool
    warnings: list[str] = Field(default_factory=list)
    message: str | None = None
