from dataclasses import dataclass
from typing import Any

from app.core.gee_datasets import (
    DATE_FILTER_CONVENTION,
    GEDI_L2A_MONTHLY,
    GEDI_REQUIRED_BANDS,
    GEDI_RH98_BAND,
    GEDI_RH98_BASELINE_END_DATE,
    GEDI_RH98_BASELINE_PURPOSE,
    GEDI_RH98_BASELINE_START_DATE,
    GEDI_RH98_COMPARISON_ASSET_ID,
    GEDI_RH98_COUNT_SUBSTANTIAL_DIFFERENCE_FRACTION,
    GEDI_RH98_MASKED_MAX_WARNING_THRESHOLD_M,
    GEDI_RH98_MAX_PIXELS,
    GEDI_RH98_REFERENCE_MANGROVE_MASKED,
    GEDI_RH98_REFERENCE_WHOLE_AOI,
    GEDI_RH98_SCALE_M,
    GEDI_RH98_TILE_SCALE,
    GEDI_RH98_WHOLE_AOI_MAX_WARNING_THRESHOLD_M,
    GMW_2020,
    GMW_VALIDATED_MASK_BAND,
    INDUS_DELTA_STUDY_AREA,
)
from app.models.gee_rh98 import (
    GeeRh98SummaryResponse,
    Rh98ReferenceDifferences,
    Rh98ReferenceResults,
    Rh98Stats,
)
from app.services import gee_service as gee_service_module
from app.services.gee_mask_service import gee_mask_service

ee = gee_service_module.ee


def apply_gedi_quality_filters(image):
    quality_mask = image.select(["quality_flag"]).eq(1)
    degrade_mask = image.select(["degrade_flag"]).eq(0)
    return image.select([GEDI_RH98_BAND]).updateMask(quality_mask.And(degrade_mask))


@dataclass(frozen=True)
class Rh98SummaryResult:
    response: GeeRh98SummaryResponse
    is_success: bool


class GeeRh98SummaryService:
    def __init__(self):
        self._cached_success_response: GeeRh98SummaryResponse | None = None

    def _rectangle_geometry(self):
        return ee.Geometry.Rectangle(INDUS_DELTA_STUDY_AREA.bounds)

    def _safe_ee_error_message(self, error: Exception) -> str:
        text = str(error).lower()
        if "quota" in text or "noncommercial" in text or "restricted" in text:
            return "Earth Engine quota or restricted-mode limitation was encountered."
        if "timed out" in text or "deadline" in text or "timeout" in text:
            return "Earth Engine request timed out while processing RH98 summary."
        return "Earth Engine processing failed for RH98 summary."

    def _reference_results(self) -> Rh98ReferenceResults:
        return Rh98ReferenceResults(
            whole_aoi=Rh98Stats(**GEDI_RH98_REFERENCE_WHOLE_AOI),
            mangrove_masked=Rh98Stats(**GEDI_RH98_REFERENCE_MANGROVE_MASKED),
        )

    def _base_payload(self) -> dict[str, Any]:
        return {
            "study_area": {
                "id": INDUS_DELTA_STUDY_AREA.id,
                "name": INDUS_DELTA_STUDY_AREA.name,
                "geometry_type": INDUS_DELTA_STUDY_AREA.geometry_type,
                "bounds": INDUS_DELTA_STUDY_AREA.bounds,
            },
            "date_range": {
                "start_date": GEDI_RH98_BASELINE_START_DATE,
                "end_date": GEDI_RH98_BASELINE_END_DATE,
                "filter_convention": DATE_FILTER_CONVENTION,
            },
            "dataset": {
                "id": GEDI_L2A_MONTHLY,
                "product": "GEDI L2A monthly raster",
                "band": GEDI_RH98_BAND,
            },
            "filters": {
                "quality_flag": 1,
                "degrade_flag": 0,
                "aggregation_method": "mosaic",
                "scale_m": GEDI_RH98_SCALE_M,
            },
            "baseline_purpose": GEDI_RH98_BASELINE_PURPOSE,
            "reference_results": self._reference_results(),
            "warnings": [
                "GEDI coverage is sparse.",
                "Pixel counts represent valid mosaic raster cells, not unique GEDI shots.",
                "The processing rectangle is not an exact administrative boundary.",
            ],
        }

    def _build_not_connected_response(self, status: str, message: str) -> GeeRh98SummaryResponse:
        base = self._base_payload()
        return GeeRh98SummaryResponse(
            connected=False,
            status=status,
            study_area=base["study_area"],
            date_range=base["date_range"],
            dataset=base["dataset"],
            filters=base["filters"],
            baseline_purpose=base["baseline_purpose"],
            reference_results=base["reference_results"],
            processing_performed=False,
            warnings=base["warnings"],
            message=message,
        )

    def _build_failure_response(
        self,
        status: str,
        message: str,
        *,
        connected: bool,
        processing_performed: bool,
        filtered_monthly_image_count: int | None = None,
        comparison_asset: dict[str, Any] | None = None,
    ) -> GeeRh98SummaryResponse:
        base = self._base_payload()
        return GeeRh98SummaryResponse(
            connected=connected,
            status=status,
            study_area=base["study_area"],
            date_range=base["date_range"],
            dataset=base["dataset"],
            filters=base["filters"],
            baseline_purpose=base["baseline_purpose"],
            reference_results=base["reference_results"],
            filtered_monthly_image_count=filtered_monthly_image_count,
            comparison_asset=comparison_asset,
            processing_performed=processing_performed,
            warnings=base["warnings"],
            message=message,
        )

    def _build_combined_stats_reducer(self):
        return (
            ee.Reducer.min()
            .combine(reducer2=ee.Reducer.mean(), sharedInputs=True)
            .combine(reducer2=ee.Reducer.max(), sharedInputs=True)
            .combine(reducer2=ee.Reducer.count(), sharedInputs=True)
        )

    def _reduce_rh98_stats(self, image, geometry) -> Rh98Stats:
        stats = image.reduceRegion(
            reducer=self._build_combined_stats_reducer(),
            geometry=geometry,
            scale=GEDI_RH98_SCALE_M,
            maxPixels=GEDI_RH98_MAX_PIXELS,
            tileScale=GEDI_RH98_TILE_SCALE,
            bestEffort=False,
        ).getInfo()
        stats = stats or {}

        count_value = stats.get(f"{GEDI_RH98_BAND}_count")
        pixel_count = int(count_value) if count_value is not None else None
        if pixel_count == 0:
            return Rh98Stats(
                rh98_min_m=None,
                rh98_mean_m=None,
                rh98_max_m=None,
                valid_gedi_raster_pixel_count=0,
            )

        return Rh98Stats(
            rh98_min_m=float(stats[f"{GEDI_RH98_BAND}_min"])
            if f"{GEDI_RH98_BAND}_min" in stats and stats[f"{GEDI_RH98_BAND}_min"] is not None
            else None,
            rh98_mean_m=float(stats[f"{GEDI_RH98_BAND}_mean"])
            if f"{GEDI_RH98_BAND}_mean" in stats and stats[f"{GEDI_RH98_BAND}_mean"] is not None
            else None,
            rh98_max_m=float(stats[f"{GEDI_RH98_BAND}_max"])
            if f"{GEDI_RH98_BAND}_max" in stats and stats[f"{GEDI_RH98_BAND}_max"] is not None
            else None,
            valid_gedi_raster_pixel_count=pixel_count,
        )

    def _difference_value(self, calculated: float | int | None, reference: float | int | None):
        if calculated is None or reference is None:
            return None
        if isinstance(calculated, int) and isinstance(reference, int):
            return calculated - reference
        return float(calculated) - float(reference)

    def _calculate_difference_from_reference(self, calculated: Rh98Stats, reference: Rh98Stats) -> Rh98Stats:
        return Rh98Stats(
            rh98_min_m=self._difference_value(calculated.rh98_min_m, reference.rh98_min_m),
            rh98_mean_m=self._difference_value(calculated.rh98_mean_m, reference.rh98_mean_m),
            rh98_max_m=self._difference_value(calculated.rh98_max_m, reference.rh98_max_m),
            valid_gedi_raster_pixel_count=self._difference_value(
                calculated.valid_gedi_raster_pixel_count,
                reference.valid_gedi_raster_pixel_count,
            ),
        )

    def _count_difference_is_substantial(self, calculated: int | None, reference: int | None) -> bool:
        if calculated is None or reference in (None, 0):
            return False
        return abs(calculated - reference) / reference >= GEDI_RH98_COUNT_SUBSTANTIAL_DIFFERENCE_FRACTION

    def _check_comparison_asset_metadata(self) -> dict[str, Any]:
        try:
            asset = ee.data.getAsset(GEDI_RH98_COMPARISON_ASSET_ID)
            asset_type = str(asset.get("type", "")).upper()
            if asset_type != "IMAGE":
                return {
                    "asset_id": GEDI_RH98_COMPARISON_ASSET_ID,
                    "accessible": False,
                    "asset_type": asset_type or None,
                    "message": "Comparison asset is accessible but is not an IMAGE.",
                }

            image = ee.Image(GEDI_RH98_COMPARISON_ASSET_ID)
            return {
                "asset_id": GEDI_RH98_COMPARISON_ASSET_ID,
                "accessible": True,
                "asset_type": "IMAGE",
                "band_names": [str(name) for name in (image.bandNames().getInfo() or [])],
                "projection": image.projection().getInfo(),
            }
        except Exception as error:
            return {
                "asset_id": GEDI_RH98_COMPARISON_ASSET_ID,
                "accessible": False,
                "message": self._safe_ee_error_message(error),
            }

    def _run_live_summary(self) -> Rh98SummaryResult:
        connection = gee_service_module.gee_service.get_connection_context()
        if not connection.enabled:
            return Rh98SummaryResult(
                response=self._build_not_connected_response(
                    status="disabled",
                    message="Google Earth Engine RH98 summary is disabled by configuration.",
                ),
                is_success=False,
            )
        if not connection.connected:
            return Rh98SummaryResult(
                response=self._build_not_connected_response(
                    status=connection.status,
                    message=connection.message or "Google Earth Engine is not connected.",
                ),
                is_success=False,
            )

        geometry = self._rectangle_geometry()
        comparison_asset = self._check_comparison_asset_metadata()

        try:
            collection = (
                ee.ImageCollection(GEDI_L2A_MONTHLY)
                .filterBounds(geometry)
                .filterDate(GEDI_RH98_BASELINE_START_DATE, GEDI_RH98_BASELINE_END_DATE)
            )
            image_count = int(collection.size().getInfo())
        except Exception as error:
            return Rh98SummaryResult(
                response=self._build_failure_response(
                    status="dataset_inaccessible",
                    message=self._safe_ee_error_message(error),
                    connected=True,
                    processing_performed=False,
                    comparison_asset=comparison_asset,
                ),
                is_success=False,
            )

        if image_count == 0:
            return Rh98SummaryResult(
                response=self._build_failure_response(
                    status="empty_collection",
                    message="GEDI collection is accessible but empty for the configured bounds and date range.",
                    connected=True,
                    processing_performed=False,
                    filtered_monthly_image_count=0,
                    comparison_asset=comparison_asset,
                ),
                is_success=False,
            )

        try:
            first_band_names = ee.Image(collection.first()).bandNames().getInfo() or []
            band_set = {str(name) for name in first_band_names}
        except Exception as error:
            return Rh98SummaryResult(
                response=self._build_failure_response(
                    status="band_check_failed",
                    message=self._safe_ee_error_message(error),
                    connected=True,
                    processing_performed=False,
                    filtered_monthly_image_count=image_count,
                    comparison_asset=comparison_asset,
                ),
                is_success=False,
            )

        missing_bands = [band for band in GEDI_REQUIRED_BANDS if band not in band_set]
        if missing_bands:
            return Rh98SummaryResult(
                response=self._build_failure_response(
                    status="missing_required_bands",
                    message=f"Required GEDI bands are missing: {', '.join(missing_bands)}.",
                    connected=True,
                    processing_performed=False,
                    filtered_monthly_image_count=image_count,
                    comparison_asset=comparison_asset,
                ),
                is_success=False,
            )

        try:
            gmw_asset = ee.data.getAsset(GMW_2020)
            asset_type = str(gmw_asset.get("type", "")).upper()
            if asset_type != "IMAGE":
                return Rh98SummaryResult(
                    response=self._build_failure_response(
                        status="gmw_asset_invalid",
                        message="Configured GMW asset must be an IMAGE.",
                        connected=True,
                        processing_performed=False,
                        filtered_monthly_image_count=image_count,
                        comparison_asset=comparison_asset,
                    ),
                    is_success=False,
                )

            gmw_band_names = [str(name) for name in (ee.Image(GMW_2020).bandNames().getInfo() or [])]
            if GMW_VALIDATED_MASK_BAND not in gmw_band_names:
                return Rh98SummaryResult(
                    response=self._build_failure_response(
                        status="gmw_band_missing",
                        message=f"Validated GMW mask band '{GMW_VALIDATED_MASK_BAND}' is not available.",
                        connected=True,
                        processing_performed=False,
                        filtered_monthly_image_count=image_count,
                        comparison_asset=comparison_asset,
                    ),
                    is_success=False,
                )
        except Exception as error:
            return Rh98SummaryResult(
                response=self._build_failure_response(
                    status="gmw_asset_failure",
                    message=self._safe_ee_error_message(error),
                    connected=True,
                    processing_performed=False,
                    filtered_monthly_image_count=image_count,
                    comparison_asset=comparison_asset,
                ),
                is_success=False,
            )

        try:
            filtered_collection = collection.map(apply_gedi_quality_filters)
            whole_aoi_mosaic = filtered_collection.mosaic().clip(geometry)
            gmw_binary_mask = gee_mask_service.build_binary_mask(GMW_2020, GMW_VALIDATED_MASK_BAND)
            mangrove_mosaic = whole_aoi_mosaic.updateMask(gmw_binary_mask).clip(geometry)

            whole_aoi_stats = self._reduce_rh98_stats(whole_aoi_mosaic, geometry)
            mangrove_stats = self._reduce_rh98_stats(mangrove_mosaic, geometry)
        except Exception as error:
            return Rh98SummaryResult(
                response=self._build_failure_response(
                    status="processing_failed",
                    message=self._safe_ee_error_message(error),
                    connected=True,
                    processing_performed=True,
                    filtered_monthly_image_count=image_count,
                    comparison_asset=comparison_asset,
                ),
                is_success=False,
            )

        base = self._base_payload()
        warnings = list(base["warnings"])
        reference_results = base["reference_results"]
        difference_from_reference = Rh98ReferenceDifferences(
            whole_aoi=self._calculate_difference_from_reference(whole_aoi_stats, reference_results.whole_aoi),
            mangrove_masked=self._calculate_difference_from_reference(mangrove_stats, reference_results.mangrove_masked),
        )

        if whole_aoi_stats.rh98_max_m is not None and whole_aoi_stats.rh98_max_m > GEDI_RH98_WHOLE_AOI_MAX_WARNING_THRESHOLD_M:
            warnings.append(
                f"Whole-AOI RH98 max exceeds {GEDI_RH98_WHOLE_AOI_MAX_WARNING_THRESHOLD_M:.0f} m; review potential outliers."
            )
        if (
            mangrove_stats.rh98_max_m is not None
            and mangrove_stats.rh98_max_m > GEDI_RH98_MASKED_MAX_WARNING_THRESHOLD_M
        ):
            warnings.append(
                f"Mangrove-masked RH98 max exceeds {GEDI_RH98_MASKED_MAX_WARNING_THRESHOLD_M:.0f} m; review potential outliers."
            )
        if self._count_difference_is_substantial(
            whole_aoi_stats.valid_gedi_raster_pixel_count,
            reference_results.whole_aoi.valid_gedi_raster_pixel_count,
        ):
            warnings.append("Whole-AOI valid GEDI raster pixel count differs substantially from the Jan-Mar 2020 reference.")
        if self._count_difference_is_substantial(
            mangrove_stats.valid_gedi_raster_pixel_count,
            reference_results.mangrove_masked.valid_gedi_raster_pixel_count,
        ):
            warnings.append(
                "Mangrove-masked valid GEDI raster pixel count differs substantially from the Jan-Mar 2020 reference."
            )

        status = "connected"
        message = None
        if whole_aoi_stats.valid_gedi_raster_pixel_count == 0:
            status = "no_valid_rh98_pixels"
            message = "No valid GEDI RH98 pixels remained after quality filtering."
        elif mangrove_stats.valid_gedi_raster_pixel_count == 0:
            status = "masked_result_empty"
            message = "No valid mangrove-masked GEDI RH98 pixels were available in the configured period."

        response = GeeRh98SummaryResponse(
            connected=True,
            status=status,
            study_area=base["study_area"],
            date_range=base["date_range"],
            dataset=base["dataset"],
            filters=base["filters"],
            whole_aoi=whole_aoi_stats,
            mangrove_masked=mangrove_stats,
            gmw_mask={
                "asset_id": GMW_2020,
                "band": GMW_VALIDATED_MASK_BAND,
                "positive_pixels_only": True,
            },
            filtered_monthly_image_count=image_count,
            baseline_purpose=base["baseline_purpose"],
            reference_results=reference_results,
            difference_from_reference=difference_from_reference,
            comparison_asset=comparison_asset,
            processing_performed=True,
            warnings=warnings,
            message=message,
        )
        return Rh98SummaryResult(response=response, is_success=True)

    def get_rh98_summary(self) -> GeeRh98SummaryResponse:
        if self._cached_success_response is not None:
            return self._cached_success_response

        result = self._run_live_summary()
        if result.is_success:
            self._cached_success_response = result.response
        return result.response


gee_rh98_summary_service = GeeRh98SummaryService()
