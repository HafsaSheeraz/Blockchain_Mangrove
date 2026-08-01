from fastapi import APIRouter

from app.core.request_timeout import run_with_request_timeout
from app.models.gee_datasets import GeeDatasetsStatusResponse
from app.models.gee_rh98 import GeeRh98SummaryResponse
from app.models.gee_biomass import GeeBiomassSummaryResponse
from app.models.gee_carbon_stock import GeeCarbonStockSummaryResponse
from app.services.gee_dataset_check_service import gee_dataset_check_service
from app.services.gee_rh98_summary_service import gee_rh98_summary_service
from app.services.gee_biomass_service import gee_biomass_service
from app.services.gee_carbon_stock_service import gee_carbon_stock_service
from app.models.gee import GeeStatusResponse
from app.services.gee_service import gee_service

router = APIRouter(prefix="/api/gee", tags=["Google Earth Engine"])


@router.get(
    "/status",
    response_model=GeeStatusResponse,
    response_model_exclude_none=True,
    summary="Get Google Earth Engine authentication status",
)
def gee_status() -> GeeStatusResponse:
    return run_with_request_timeout("Google Earth Engine status check", gee_service.get_status)


@router.get(
    "/datasets/status",
    response_model=GeeDatasetsStatusResponse,
    response_model_exclude_none=True,
    summary="Get metadata-only Earth Engine dataset accessibility status",
)
def gee_datasets_status() -> GeeDatasetsStatusResponse:
    return run_with_request_timeout(
        "Earth Engine dataset status check",
        gee_dataset_check_service.get_datasets_status,
    )


@router.get(
    "/rh98/summary",
    response_model=GeeRh98SummaryResponse,
    summary="Get live quality-filtered GEDI RH98 summary for whole AOI and mangrove mask",
)
def gee_rh98_summary() -> GeeRh98SummaryResponse:
    return run_with_request_timeout("Earth Engine RH98 summary", gee_rh98_summary_service.get_rh98_summary)


@router.get(
    "/biomass/summary",
    response_model=GeeBiomassSummaryResponse,
    summary="Get live mangrove biomass and carbon-density statistics for the Indus Delta",
)
def gee_biomass_summary() -> GeeBiomassSummaryResponse:
    return run_with_request_timeout("Earth Engine biomass summary", gee_biomass_service.get_biomass_summary)


@router.get(
    "/carbon/stock-summary",
    response_model=GeeCarbonStockSummaryResponse,
    summary="Get live mangrove area, GEDI raster coverage and carbon stock totals",
)
def gee_carbon_stock_summary() -> GeeCarbonStockSummaryResponse:
    return run_with_request_timeout(
        "Earth Engine carbon stock summary",
        gee_carbon_stock_service.get_carbon_stock_summary,
    )
