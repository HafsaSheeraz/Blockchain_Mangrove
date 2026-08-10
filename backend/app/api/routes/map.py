from typing import Literal

from fastapi import APIRouter, HTTPException

from app.core.request_timeout import run_with_request_timeout
from app.models.map_layers import (
    GmwCoverageCheckRequest,
    GmwCoverageCheckResponse,
    GmwLayerResponse,
)
from app.services.gee_map_layer_service import gee_map_layer_service

router = APIRouter(prefix="/api/map", tags=["Map Layers"])


@router.get(
    "/gmw-layer",
    response_model=GmwLayerResponse,
    summary="Get Earth Engine tile descriptor for the configured GMW mangrove mask",
)
def get_gmw_layer(
    study_area: Literal["indus_delta", "abu_dhabi", "custom"] = "custom",
) -> GmwLayerResponse:
    try:
        payload = run_with_request_timeout(
            "GMW overlay tile descriptor generation",
            lambda: gee_map_layer_service.get_gmw_layer_descriptor(study_area),
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return GmwLayerResponse(**payload)


@router.post(
    "/gmw-coverage-check",
    response_model=GmwCoverageCheckResponse,
    summary="Check whether an AOI polygon intersects mapped mangroves in the configured GMW source",
)
def check_gmw_coverage(payload: GmwCoverageCheckRequest) -> GmwCoverageCheckResponse:
    try:
        response_payload = run_with_request_timeout(
            "GMW coverage check",
            lambda: gee_map_layer_service.check_polygon_mangrove_coverage(
                payload.study_area, payload.aoi_geometry
            ),
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return GmwCoverageCheckResponse(**response_payload)
