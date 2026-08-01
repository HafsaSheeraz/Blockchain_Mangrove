from typing import Union

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import Response

from app.models.analysis import (
    AnalyzeRequest,
    AnalyzeResponse,
    CustomAoiAnalyzeResponse,
    MapLayersResponse,
)
from app.services.analysis_service import run_analysis, run_custom_aoi_analysis, run_map_layers_analysis
from app.services import export_service
from app.services.analysis_service import _get_gee_service

router = APIRouter(prefix="/api", tags=["Analysis"])


@router.post(
    "/analyze",
    response_model=Union[AnalyzeResponse, CustomAoiAnalyzeResponse],
    summary="Run biomass analysis (demonstration or live custom AOI)",
)
def analyze(payload: AnalyzeRequest) -> Union[AnalyzeResponse, CustomAoiAnalyzeResponse]:
    """
    Analyze mangrove biomass and carbon stock.

    Backward-compatible endpoint that supports both:
    - **Demonstration mode** (old-style): send study_area without aoi_geometry
    - **Live custom AOI** (Module 13): send aoi_geometry (GeoJSON Polygon)

    Returns mode='demonstration' or mode='live_earth_engine_custom_aoi' accordingly.
    """
    return run_analysis(payload)


@router.post(
    "/analyze/map-layers",
    response_model=MapLayersResponse,
    summary="Build Earth Engine AOI map-layer descriptors",
)
def analyze_map_layers(payload: AnalyzeRequest) -> MapLayersResponse:
    return run_map_layers_analysis(payload)


@router.post(
    "/analyze/export/{export_format}",
    summary="Export authoritative AOI analysis results (JSON, CSV or PDF)",
    responses={
        200: {"description": "File download"},
        400: {"description": "aoi_geometry required or unsupported format"},
        422: {"description": "Validation error"},
    },
)
def export_analysis(
    payload: AnalyzeRequest,
    export_format: str = Path(
        ...,
        pattern="^(json|csv|pdf)$",
        description="Export format: json, csv, or pdf",
    ),
) -> Response:
    """
    Export the authoritative AOI analysis result as a downloadable file.

    Reuses the cached live Earth Engine result when available — no new
    Earth Engine calculation is triggered if an equivalent result is cached.

    Requires aoi_geometry (GeoJSON Polygon) in the request body.
    """
    if not payload.aoi_geometry:
        raise HTTPException(
            status_code=400,
            detail="Export requires aoi_geometry (GeoJSON Polygon) in the request body.",
        )

    result: CustomAoiAnalyzeResponse = run_custom_aoi_analysis(payload)
    processing_version = _get_gee_service().get_processing_version_fingerprint()
    document = export_service.build_export_document(
        result,
        processing_version=processing_version,
    )

    filename = export_service.build_filename(document, export_format)
    content_type = export_service.CONTENT_TYPES[export_format]

    if export_format == "json":
        body = export_service.generate_json(document)
    elif export_format == "csv":
        body = export_service.generate_csv(document)
    else:  # pdf
        body = export_service.generate_pdf(document)

    return Response(
        content=body,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
