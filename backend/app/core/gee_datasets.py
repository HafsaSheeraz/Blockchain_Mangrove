from dataclasses import dataclass
from typing import Optional


GEDI_L2A_MONTHLY = "LARSE/GEDI/GEDI02_A_002_MONTHLY"
SENTINEL2_L2A = "COPERNICUS/S2_SR_HARMONIZED"

# ── GMW asset identifiers ─────────────────────────────────────────────────────
# Project-owned regional assets (IMAGE type, EPSG:4326, 25 m nominal scale)
GMW_2020_INDUS = "projects/mangroves123/assets/GMW_2020_IndusDelta"
GMW_2020_ABU_DHABI = "projects/mangroves123/assets/GMW_2020_AbuDhabi_v2"

# Public global GMW 2020 (IMAGE_COLLECTION, 1 646 tiles, band b1)
# Confirmed accessible; must be loaded as ImageCollection and mosaiced.
GMW_GLOBAL_2020_COLLECTION = "projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020"

# Backward-compatibility alias used by the fixed Indus baseline path in
# gee_carbon_stock_service._run_live_summary() and related fixed-path tests.
# Do not change this alias; it must remain pointing to the IndusDelta asset.
GMW_2020 = GMW_2020_INDUS

# GMW asset type tokens
GMW_ASSET_TYPE_IMAGE = "IMAGE"
GMW_ASSET_TYPE_IMAGE_COLLECTION = "IMAGE_COLLECTION"

# Approximate spatial footprint of the Indus-only project asset
# (confirmed via ee.Image.geometry().bounds().getInfo()).
GMW_ASSET_APPROX_LON_MIN: float = 66.49
GMW_ASSET_APPROX_LON_MAX: float = 68.50
GMW_ASSET_APPROX_LAT_MIN: float = 23.49
GMW_ASSET_APPROX_LAT_MAX: float = 24.80
GMW_ASSET_COVERAGE_NOTE: str = (
    "The configured GMW asset (IndusDelta) covers only the Indus Delta geographic region "
    "(approx. lon 66.5–68.5°E, lat 23.5–24.8°N). "
    "AOIs outside this spatial extent will return no mapped mangrove area. "
    "Abu Dhabi and other regions use their own region-specific GMW assets."
)

DATASET_CHECK_START_DATE = "2019-04-01"
DATASET_CHECK_END_DATE = "2021-12-31"
DATE_FILTER_CONVENTION = "end_exclusive"
GEDI_REQUIRED_BANDS = ["rh98", "quality_flag", "degrade_flag"]
S2_REQUIRED_BANDS = ["B2", "B3", "B4", "B8"]
GMW_VALIDATED_MASK_BAND = "b1"
GEDI_RH98_BAND = "rh98"
GEDI_RH98_SCALE_M = 25
GEDI_RH98_TILE_SCALE = 4
GEDI_RH98_MAX_PIXELS = 1_000_000_000
GEDI_RH98_BASELINE_START_DATE = "2020-01-01"
GEDI_RH98_BASELINE_END_DATE = "2020-04-01"
GEDI_RH98_BASELINE_PURPOSE = "reproduce_jan_mar_2020_reference"
GEDI_RH98_REFERENCE_WHOLE_AOI = {
    "rh98_min_m": 1.42,
    "rh98_mean_m": 2.57,
    "rh98_max_m": 15.55,
    "valid_gedi_raster_pixel_count": 42198,
}
GEDI_RH98_REFERENCE_MANGROVE_MASKED = {
    "rh98_min_m": 2.39,
    "rh98_mean_m": 3.09,
    "rh98_max_m": 5.76,
    "valid_gedi_raster_pixel_count": 1130,
}
GEDI_RH98_WHOLE_AOI_MAX_WARNING_THRESHOLD_M = 50.0
GEDI_RH98_MASKED_MAX_WARNING_THRESHOLD_M = 15.0
GEDI_RH98_COUNT_SUBSTANTIAL_DIFFERENCE_FRACTION = 0.5
GEDI_RH98_COMPARISON_ASSET_ID = "projects/mangroves123/assets/GEDI_L2A_RH98_JanMar2020_IndusDelta"

# Module 9: Biomass and carbon-density formula coefficients
# AGB (Mg/ha) = BIOMASS_HEIGHT_TO_AGB × RH98 (m)
BIOMASS_HEIGHT_TO_AGB: float = 10.0
# BGB (Mg/ha) = BIOMASS_ROOT_TO_SHOOT × AGB (Mg/ha)
BIOMASS_ROOT_TO_SHOOT: float = 0.49
# Carbon (Mg C/ha) = BIOMASS_TO_CARBON × TAB (Mg/ha)
BIOMASS_TO_CARBON: float = 0.5

# Named output bands for the biomass image stack
BIOMASS_BAND_RH98 = "RH98"
BIOMASS_BAND_AGB = "AGB"
BIOMASS_BAND_BGB = "BGB"
BIOMASS_BAND_TAB = "TAB"
BIOMASS_BAND_CARBON = "Carbon"
BIOMASS_BANDS = [
    BIOMASS_BAND_RH98,
    BIOMASS_BAND_AGB,
    BIOMASS_BAND_BGB,
    BIOMASS_BAND_TAB,
    BIOMASS_BAND_CARBON,
]

# Relative tolerance for formula-invariant validation (post-reduction sanity check)
BIOMASS_FORMULA_TOLERANCE: float = 1e-6

# Module 10: Carbon stock calculation constants
# Scale for mapped mangrove area calculation (10 m captures fine GMW pixel boundaries)
GMW_AREA_SCALE_M: int = 10
# Older project report value for direct sampled carbon stock (Mg C) — used only for
# diagnostic comparison, not as a calculated output
CARBON_STOCK_OLDER_REPORT_DIRECT_SAMPLED_MG_C: float = 1480.37
# Relative tolerance for stock calculation validation invariants
CARBON_STOCK_FORMULA_TOLERANCE: float = 1e-6

# Module 14 map visualization defaults (style-only; does not affect scientific calculations)
MAP_LAYER_VISUALIZATION_VERSION = "module14_v1"
MAP_LAYER_ID_GMW = "gmw_mangrove_extent"
MAP_LAYER_ID_GEDI = "valid_gedi_raster_coverage"
MAP_LAYER_ID_CARBON = "carbon_density"
MAP_LAYER_ID_RH98 = "rh98_canopy_height"
MAP_LAYER_CARBON_MIN_MG_C_HA = 0.0
MAP_LAYER_CARBON_MAX_MG_C_HA = 50.0
MAP_LAYER_RH98_MIN_M = 0.0
MAP_LAYER_RH98_MAX_M = 20.0
MAP_LAYER_GMW_PALETTE = ["2e8b57"]
MAP_LAYER_GEDI_PALETTE = ["1f78b4"]
MAP_LAYER_CARBON_PALETTE = ["0d0887", "6a00a8", "b12a90", "e16462", "fca636", "f0f921"]
MAP_LAYER_RH98_PALETTE = ["081d58", "225ea8", "1d91c0", "41b6c4", "7fcdbb", "c7e9b4", "edf8b1"]


@dataclass(frozen=True)
class StudyAreaConfig:
    id: str
    name: str
    geometry_type: str
    bounds: list
    description: str
    processing_boundary_note: str
    mask_note: str


@dataclass(frozen=True)
class RegionConfig:
    """Per-region Earth Engine configuration for the analysis pipeline.

    Stores the GMW asset to use, its type, the verified study geometry, and
    recommended date defaults. The backend uses this catalog exclusively to
    determine which GMW asset a request should query — clients never supply
    an asset ID.
    """
    id: str
    name: str
    # [lon_min, lat_min, lon_max, lat_max] bounding box; None for custom AOI
    bounds: Optional[list]
    gmw_asset_id: str
    # "IMAGE" or "IMAGE_COLLECTION" — determines loading strategy in gee_mask_service
    gmw_asset_type: str
    gmw_mask_band: str
    default_start_date: str
    default_end_date: str
    geometry_status: str


REGION_CATALOG: dict = {
    "indus_delta": RegionConfig(
        id="indus_delta",
        name="Indus Delta, Pakistan",
        bounds=[66.5, 23.5, 68.5, 24.8],
        gmw_asset_id=GMW_2020_INDUS,
        gmw_asset_type=GMW_ASSET_TYPE_IMAGE,
        gmw_mask_band=GMW_VALIDATED_MASK_BAND,
        default_start_date="2020-01-01",
        default_end_date="2020-04-01",
        geometry_status="temporary_bounding_rectangle",
    ),
    "abu_dhabi": RegionConfig(
        id="abu_dhabi",
        name="Abu Dhabi, United Arab Emirates",
        # Verified project study extent (confirmed by live EE diagnostic):
        # asset footprint [54.319°E to 54.520°E, 24.399°N to 24.550°N]
        bounds=[54.32, 24.40, 54.52, 24.55],
        gmw_asset_id=GMW_2020_ABU_DHABI,
        gmw_asset_type=GMW_ASSET_TYPE_IMAGE,
        gmw_mask_band=GMW_VALIDATED_MASK_BAND,
        default_start_date="2019-01-01",
        default_end_date="2021-12-31",
        geometry_status="verified_project_study_extent",
    ),
    "custom": RegionConfig(
        id="custom",
        name="Custom AOI",
        bounds=None,
        gmw_asset_id=GMW_GLOBAL_2020_COLLECTION,
        gmw_asset_type=GMW_ASSET_TYPE_IMAGE_COLLECTION,
        gmw_mask_band=GMW_VALIDATED_MASK_BAND,
        default_start_date="2020-01-01",
        default_end_date="2020-04-01",
        geometry_status="user_supplied",
    ),
}


INDUS_DELTA_STUDY_AREA = StudyAreaConfig(
    id="indus_delta",
    name="Indus Delta, Pakistan",
    geometry_type="temporary_rectangle",
    bounds=[66.5, 23.5, 68.5, 24.8],
    description=(
        "Temporary bounding box for access checks only; "
        "not necessarily the final scientific boundary."
    ),
    processing_boundary_note=(
        "This rectangle is the processing boundary and is not an exact administrative boundary."
    ),
    mask_note=(
        "Calculations must be restricted to valid positive pixels of the project-owned GMW mask."
    ),
)
