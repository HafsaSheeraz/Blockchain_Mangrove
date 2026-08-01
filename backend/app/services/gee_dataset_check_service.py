from dataclasses import dataclass
from typing import Any

from app.core.gee_datasets import (
    DATASET_CHECK_END_DATE,
    DATASET_CHECK_START_DATE,
    DATE_FILTER_CONVENTION,
    GEDI_L2A_MONTHLY,
    GEDI_REQUIRED_BANDS,
    GMW_2020,
    INDUS_DELTA_STUDY_AREA,
    S2_REQUIRED_BANDS,
    SENTINEL2_L2A,
)
from app.models.gee_datasets import DatasetBandStatus, DatasetMaskStatus, GeeDatasetsStatusResponse
from app.services.gee_mask_service import gee_mask_service
from app.services import gee_service as gee_service_module

ee = gee_service_module.ee


@dataclass(frozen=True)
class DatasetCheckResult:
    response: GeeDatasetsStatusResponse
    is_success: bool


class GeeDatasetCheckService:
    def __init__(self):
        self._cached_success_response: GeeDatasetsStatusResponse | None = None

    def _rectangle_geometry(self):
        return ee.Geometry.Rectangle(INDUS_DELTA_STUDY_AREA.bounds)

    def _safe_dataset_error_message(self, error: Exception) -> str:
        text = str(error).lower()
        if "quota" in text or "noncommercial" in text or "restricted" in text:
            return "Earth Engine quota or restricted-mode limitation was encountered."
        if "timed out" in text or "deadline" in text or "timeout" in text:
            return "Earth Engine request timed out while checking dataset metadata."
        return "Dataset metadata access failed."

    def _check_collection_bands(
        self,
        dataset_id: str,
        geometry: Any,
        required_bands: list[str],
    ) -> DatasetBandStatus:
        try:
            collection = (
                ee.ImageCollection(dataset_id)
                .filterBounds(geometry)
                .filterDate(DATASET_CHECK_START_DATE, DATASET_CHECK_END_DATE)
            )
            image_count = int(collection.size().getInfo())
        except Exception as error:
            return DatasetBandStatus(
                dataset_id=dataset_id,
                accessible=False,
                image_count=None,
                required_bands_available=False,
                message=self._safe_dataset_error_message(error),
            )

        if image_count == 0:
            return DatasetBandStatus(
                dataset_id=dataset_id,
                accessible=True,
                image_count=0,
                required_bands_available=False,
                message="Dataset is accessible but the filtered collection is empty for this AOI and date range.",
            )

        try:
            first_bands = ee.Image(collection.first()).bandNames().getInfo()
        except Exception as error:
            return DatasetBandStatus(
                dataset_id=dataset_id,
                accessible=False,
                image_count=image_count,
                required_bands_available=False,
                message=self._safe_dataset_error_message(error),
            )

        band_set = set(first_bands or [])
        missing_bands = [band for band in required_bands if band not in band_set]

        if missing_bands:
            return DatasetBandStatus(
                dataset_id=dataset_id,
                accessible=True,
                image_count=image_count,
                required_bands_available=False,
                message=f"Required bands are missing: {', '.join(missing_bands)}.",
            )

        return DatasetBandStatus(
            dataset_id=dataset_id,
            accessible=True,
            image_count=image_count,
            required_bands_available=True,
        )

    def _check_gmw_mask(self) -> DatasetMaskStatus:
        dataset_id = GMW_2020
        try:
            asset = ee.data.getAsset(dataset_id)
            asset_type = str(asset.get("type", "")).upper()
            if asset_type != "IMAGE":
                return DatasetMaskStatus(
                    dataset_id=dataset_id,
                    source="project_asset",
                    accessible=False,
                    asset_type=asset_type or None,
                    band_names=[],
                    usable_as_mask=False,
                    message="Configured GMW project asset must be an IMAGE.",
                )

            band_names = ee.Image(dataset_id).bandNames().getInfo() or []
            normalized_band_names = [str(name) for name in band_names]
            if not normalized_band_names:
                return DatasetMaskStatus(
                    dataset_id=dataset_id,
                    source="project_asset",
                    accessible=True,
                    asset_type=asset_type,
                    band_names=[],
                    usable_as_mask=False,
                    message="Configured GMW project asset has no bands and cannot be used as a mask.",
                )

            validated_band_name = gee_mask_service.select_validated_mask_band(normalized_band_names)
            gee_mask_service.build_binary_mask(dataset_id, validated_band_name)
            return DatasetMaskStatus(
                dataset_id=dataset_id,
                source="project_asset",
                accessible=True,
                asset_type=asset_type,
                band_names=normalized_band_names,
                usable_as_mask=True,
            )
        except Exception as error:
            return DatasetMaskStatus(
                dataset_id=dataset_id,
                source="project_asset",
                accessible=False,
                usable_as_mask=False,
                message=self._safe_dataset_error_message(error),
            )

    def _build_not_connected_response(self, status: str, message: str) -> GeeDatasetsStatusResponse:
        return GeeDatasetsStatusResponse(
            connected=False,
            status=status,
            study_area={
                "id": INDUS_DELTA_STUDY_AREA.id,
                "name": INDUS_DELTA_STUDY_AREA.name,
                "geometry_type": INDUS_DELTA_STUDY_AREA.geometry_type,
                "description": INDUS_DELTA_STUDY_AREA.description,
                "processing_boundary_note": INDUS_DELTA_STUDY_AREA.processing_boundary_note,
                "mask_note": INDUS_DELTA_STUDY_AREA.mask_note,
            },
            date_range={
                "start_date": DATASET_CHECK_START_DATE,
                "end_date": DATASET_CHECK_END_DATE,
                "filter_convention": DATE_FILTER_CONVENTION,
            },
            datasets={
                "gedi_l2a": {"dataset_id": GEDI_L2A_MONTHLY, "accessible": False},
                "sentinel2_l2a": {"dataset_id": SENTINEL2_L2A, "accessible": False},
                "gmw_2020": {"dataset_id": GMW_2020, "accessible": False},
            },
            processing_performed=False,
            message=message,
        )

    def _run_live_checks(self) -> DatasetCheckResult:
        connection = gee_service_module.gee_service.get_connection_context()
        if not connection.enabled:
            return DatasetCheckResult(
                response=self._build_not_connected_response(
                    status="disabled",
                    message="Google Earth Engine access checks are disabled by configuration.",
                ),
                is_success=False,
            )

        if not connection.connected:
            return DatasetCheckResult(
                response=self._build_not_connected_response(
                    status=connection.status,
                    message=connection.message or "Google Earth Engine is not connected.",
                ),
                is_success=False,
            )

        geometry = self._rectangle_geometry()
        gedi = self._check_collection_bands(GEDI_L2A_MONTHLY, geometry, GEDI_REQUIRED_BANDS)
        sentinel = self._check_collection_bands(SENTINEL2_L2A, geometry, S2_REQUIRED_BANDS)
        gmw = self._check_gmw_mask()

        all_ok = (
            gedi.accessible
            and sentinel.accessible
            and gmw.accessible
            and bool(gedi.required_bands_available)
            and bool(sentinel.required_bands_available)
            and bool(gmw.usable_as_mask)
        )

        status = "connected" if all_ok else "connected_with_dataset_issues"
        message = (
            "Metadata access check only. No biomass calculation was run."
            if all_ok
            else "Metadata access check completed with one or more dataset issues. No biomass calculation was run."
        )

        response = GeeDatasetsStatusResponse(
            connected=True,
            status=status,
            study_area={
                "id": INDUS_DELTA_STUDY_AREA.id,
                "name": INDUS_DELTA_STUDY_AREA.name,
                "geometry_type": INDUS_DELTA_STUDY_AREA.geometry_type,
                "description": INDUS_DELTA_STUDY_AREA.description,
                "bounds": INDUS_DELTA_STUDY_AREA.bounds,
                "processing_boundary_note": INDUS_DELTA_STUDY_AREA.processing_boundary_note,
                "mask_note": INDUS_DELTA_STUDY_AREA.mask_note,
            },
            date_range={
                "start_date": DATASET_CHECK_START_DATE,
                "end_date": DATASET_CHECK_END_DATE,
                "filter_convention": DATE_FILTER_CONVENTION,
            },
            datasets={
                "gedi_l2a": gedi.model_dump(exclude_none=True),
                "sentinel2_l2a": sentinel.model_dump(exclude_none=True),
                "gmw_2020": gmw.model_dump(exclude_none=True),
            },
            processing_performed=False,
            message=message,
        )
        return DatasetCheckResult(response=response, is_success=all_ok)

    def get_datasets_status(self) -> GeeDatasetsStatusResponse:
        if self._cached_success_response is not None:
            return self._cached_success_response

        live_result = self._run_live_checks()
        if live_result.is_success:
            self._cached_success_response = live_result.response
        return live_result.response


gee_dataset_check_service = GeeDatasetCheckService()
