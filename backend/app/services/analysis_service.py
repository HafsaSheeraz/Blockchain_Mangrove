from datetime import date
from typing import Optional
from fastapi import HTTPException

from app.models.analysis import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisResults,
    CustomAoiAnalyzeResponse,
    DateRangeInfo,
    MapLayersResponse,
    MethodologyInfo,
    StudyAreaInfo,
)
from app.services.gee_carbon_stock_service import GeeCarbonStockService

SUPPORTED_STUDY_AREA = "indus_delta"

STUDY_AREA_CATALOG: dict[str, StudyAreaInfo] = {
    "indus_delta": StudyAreaInfo(id="indus_delta", name="Indus Delta, Pakistan"),
    "abu_dhabi": StudyAreaInfo(id="abu_dhabi", name="Abu Dhabi, United Arab Emirates"),
    "custom": StudyAreaInfo(id="custom", name="Custom AOI"),
}

DEMO_DATASETS = ["GEDI L2A RH98", "GMW 2020", "Sentinel-2"]

DEMO_RESULTS = AnalysisResults(
    valid_gedi_samples=1130,
    mean_rh98_m=3.09,
    min_rh98_m=2.39,
    max_rh98_m=5.76,
    mean_agb_mg_ha=30.91,
    mean_bgb_mg_ha=15.15,
    mean_carbon_mg_c_ha=23.03,
    min_carbon_mg_c_ha=17.81,
    max_carbon_mg_c_ha=42.91,
    mangrove_area_ha=90769.33,
    gedi_sampled_coverage_percent=0.08,
    direct_sampled_carbon_mg_c=1480.37,
    extrapolated_total_carbon_mg_c=2090417.67,
)

DEMO_METHOD = MethodologyInfo(
    agb_formula="AGB = 10 × RH98",
    bgb_formula="BGB = 0.49 × AGB",
    tab_formula="TAB = AGB + BGB",
    carbon_formula="Carbon = 0.5 × TAB",
)

_gee_service_instance: Optional[GeeCarbonStockService] = None


def _get_gee_service() -> GeeCarbonStockService:
    global _gee_service_instance
    if _gee_service_instance is None:
        _gee_service_instance = GeeCarbonStockService()
    return _gee_service_instance


def run_demonstration_analysis(request: AnalyzeRequest) -> AnalyzeResponse:
    if request.study_area != SUPPORTED_STUDY_AREA:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported study_area '{request.study_area}'. "
                f"Currently supported: '{SUPPORTED_STUDY_AREA}'."
            ),
        )

    return AnalyzeResponse(
        mode="demonstration",
        study_area=STUDY_AREA_CATALOG[request.study_area],
        date_range=DateRangeInfo(start_date=request.start_date, end_date=request.end_date),
        datasets=DEMO_DATASETS,
        results=DEMO_RESULTS,
        methodology=DEMO_METHOD,
        warning="Demonstration results only. No live Earth Engine processing was performed.",
    )


def run_custom_aoi_analysis(request: AnalyzeRequest) -> CustomAoiAnalyzeResponse:
    """
    Run live Earth Engine analysis for a custom AOI polygon.

    Args:
        request: AnalyzeRequest with aoi_geometry (GeoJSON Polygon) and date range.

    Returns:
        CustomAoiAnalyzeResponse with live Earth Engine results.

    Raises:
        HTTPException: If geometry is invalid or Earth Engine processing fails.
    """
    if not request.aoi_geometry:
        raise HTTPException(
            status_code=400,
            detail="Custom AOI analysis requires aoi_geometry (GeoJSON Polygon).",
        )

    gee_service = _get_gee_service()
    if request.study_area not in STUDY_AREA_CATALOG:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported study_area '{request.study_area}' for live AOI analysis. "
                "Supported values: 'indus_delta', 'abu_dhabi', 'custom'."
            ),
        )
    study_area_info = STUDY_AREA_CATALOG[request.study_area]

    response = gee_service.run_live_summary_for_custom_aoi(
        study_area_id=study_area_info.id,
        study_area_name=study_area_info.name,
        aoi_geometry=request.aoi_geometry,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
    )

    if response.results is None:
        warning_text = (response.warning or "").lower()
        no_data_markers = (
            "no gedi data available",
            "no mapped mangrove area",
            "no valid gedi raster coverage",
        )
        if any(marker in warning_text for marker in no_data_markers):
            return response

        if "geometry validation failed" in warning_text:
            raise HTTPException(status_code=422, detail=response.warning)

        service_unavailable_markers = (
            "disabled by configuration",
            "not connected",
            "authentication or initialization failed",
            "quota",
            "timed out",
            "timeout",
        )
        if any(marker in warning_text for marker in service_unavailable_markers):
            raise HTTPException(status_code=503, detail=response.warning)

        raise HTTPException(status_code=500, detail="Earth Engine carbon stock processing failed.")

    return response


def run_analysis(request: AnalyzeRequest) -> AnalyzeResponse | CustomAoiAnalyzeResponse:
    """
    Route incoming request to either demonstration or custom AOI analysis.

    Backward compatibility:
    - If aoi_geometry is None: run demonstration analysis (old-style request)
    - If aoi_geometry is provided: run live custom AOI analysis (Module 13)

    Args:
        request: AnalyzeRequest with optional aoi_geometry.

    Returns:
        AnalyzeResponse (demonstration) or CustomAoiAnalyzeResponse (live custom AOI).
    """
    if request.aoi_geometry is not None:
        return run_custom_aoi_analysis(request)
    else:
        return run_demonstration_analysis(request)


def run_map_layers_analysis(request: AnalyzeRequest) -> MapLayersResponse:
    if not request.aoi_geometry:
        raise HTTPException(
            status_code=400,
            detail="Map-layer analysis requires aoi_geometry (GeoJSON Polygon).",
        )
    if request.study_area not in STUDY_AREA_CATALOG:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported study_area '{request.study_area}' for live map-layer analysis. "
                "Supported values: 'indus_delta', 'abu_dhabi', 'custom'."
            ),
        )

    gee_service = _get_gee_service()
    study_area_info = STUDY_AREA_CATALOG[request.study_area]
    response = gee_service.run_live_map_layers_for_custom_aoi(
        study_area_id=study_area_info.id,
        study_area_name=study_area_info.name,
        aoi_geometry=request.aoi_geometry,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
    )
    return response
