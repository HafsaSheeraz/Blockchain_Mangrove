"""
Module 10: Mangrove carbon stock summary service.

Calculates live mangrove area, GEDI raster coverage, direct sampled raster carbon stock,
and extrapolated ecosystem carbon stock for the Indus Delta.

Processing uses two Earth Engine getInfo calls:
  Call 1 (scale=10 m): mapped mangrove area from the project-owned GMW binary mask.
  Call 2 (scale=25 m): carbon density stats + GEDI raster coverage area + direct stock
                       from the 3-band analysis image.

All biomass formulas and GEDI filtering reuse the validated Module 9 pipeline.

IMPORTANT DISTINCTIONS
  - mapped_mangrove_area_ha: total pixel area of positive GMW-mask pixels at 10 m.
  - valid_gedi_raster_coverage_area_ha: total pixel area where the Carbon raster has
    valid data (i.e., the GEDI/GMW intersection).  This is NOT unique GEDI-shot area.
  - direct_sampled_raster_carbon_mg_c: sum(Carbon_density × pixel_area_ha) over valid
    GEDI/GMW cells — covers the sampled area only, not all mapped mangroves.
  - extrapolated_ecosystem_carbon_mg_c: mean Carbon density × full mapped mangrove area.
    This is an extrapolated estimate; it assumes sparse GEDI coverage is representative.
"""

from dataclasses import dataclass
from typing import Any
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from app.core.config import settings
from app.core.gee_datasets import (
    BIOMASS_BAND_CARBON,
    BIOMASS_BAND_RH98,
    BIOMASS_BAND_AGB,
    BIOMASS_BAND_BGB,
    CARBON_STOCK_FORMULA_TOLERANCE,
    CARBON_STOCK_OLDER_REPORT_DIRECT_SAMPLED_MG_C,
    DATE_FILTER_CONVENTION,
    GEDI_L2A_MONTHLY,
    GEDI_REQUIRED_BANDS,
    GEDI_RH98_BASELINE_END_DATE,
    GEDI_RH98_BASELINE_START_DATE,
    GEDI_RH98_MAX_PIXELS,
    GEDI_RH98_SCALE_M,
    GEDI_RH98_TILE_SCALE,
    GMW_2020,
    GMW_2020_INDUS,
    GMW_AREA_SCALE_M,
    GMW_ASSET_COVERAGE_NOTE,
    GMW_ASSET_TYPE_IMAGE,
    GMW_VALIDATED_MASK_BAND,
    INDUS_DELTA_STUDY_AREA,
    MAP_LAYER_CARBON_MAX_MG_C_HA,
    MAP_LAYER_CARBON_MIN_MG_C_HA,
    MAP_LAYER_CARBON_PALETTE,
    MAP_LAYER_GEDI_PALETTE,
    MAP_LAYER_GMW_PALETTE,
    MAP_LAYER_ID_CARBON,
    MAP_LAYER_ID_GEDI,
    MAP_LAYER_ID_GMW,
    MAP_LAYER_ID_RH98,
    MAP_LAYER_RH98_MAX_M,
    MAP_LAYER_RH98_MIN_M,
    MAP_LAYER_RH98_PALETTE,
    MAP_LAYER_VISUALIZATION_VERSION,
    REGION_CATALOG,
)
from app.models.gee_carbon_stock import (
    AreaStats,
    CarbonDensityStats,
    GeeCarbonStockSummaryResponse,
    ReferenceComparison,
    StockStats,
)
from app.models.analysis import DateRangeInfo, MapLayerDescriptor, MapLayersResponse, StudyAreaInfo
from app.services import gee_service as gee_service_module
from app.services.gee_biomass_service import build_biomass_image_stack
from app.services.gee_mask_service import gee_mask_service
from app.services.gee_rh98_summary_service import apply_gedi_quality_filters

ee = gee_service_module.ee
logger = logging.getLogger(__name__)

# Intermediate band names for the combined 25-m analysis image
_GEDI_COVERAGE_BAND = "gedi_coverage_ha"
_DIRECT_STOCK_BAND = "direct_stock_mgc"


@dataclass(frozen=True)
class _CarbonStockResult:
    response: GeeCarbonStockSummaryResponse
    is_success: bool


class GeeCarbonStockService:
    """Live mangrove area and carbon stock service for the Indus Delta and custom AOIs."""

    def __init__(self) -> None:
        self._cached_success_response: GeeCarbonStockSummaryResponse | None = None
        # Separate cache for custom AOI results, keyed by geometry+dates hash
        self._custom_aoi_cache: dict[str, dict[str, Any]] = {}
        self._map_layer_descriptor_cache: dict[str, dict[str, Any]] = {}

    def _processing_version_fingerprint(self) -> str:
        """
        Hash of methodology-level pipeline parameters: formulas, scales, dataset IDs,
        quality filter settings, aggregation method, and bestEffort flag.

        Intentionally excludes region-specific GMW asset IDs — those are captured
        separately as ``gmw_asset_id`` in every cache key so that different regions
        (indus_delta / abu_dhabi / custom) never share a cache entry.
        """
        payload = {
            "dataset": GEDI_L2A_MONTHLY,
            "gedi_band": "rh98",
            "gmw_band": GMW_VALIDATED_MASK_BAND,
            "gmw_scale_m": GMW_AREA_SCALE_M,
            "gedi_scale_m": GEDI_RH98_SCALE_M,
            "height_to_agb_formula": "AGB = 10 × RH98",
            "bgb_formula": "BGB = 0.49 × AGB",
            "carbon_formula": "Carbon = 0.5 × (AGB + BGB)",
            "quality_mask": "quality_flag=1 and degrade_flag=0",
            "aggregation_method": "mosaic",
            "best_effort": False,
            "pixel_area": "ee.Image.pixelArea()/10000",
        }
        as_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(as_json.encode("utf-8")).hexdigest()

    def _visualization_version_fingerprint(self) -> str:
        payload = {
            "version": MAP_LAYER_VISUALIZATION_VERSION,
            "gmw": {"min": 0, "max": 1, "palette": MAP_LAYER_GMW_PALETTE},
            "gedi": {"min": 0, "max": 1, "palette": MAP_LAYER_GEDI_PALETTE},
            "carbon": {
                "min": MAP_LAYER_CARBON_MIN_MG_C_HA,
                "max": MAP_LAYER_CARBON_MAX_MG_C_HA,
                "palette": MAP_LAYER_CARBON_PALETTE,
            },
            "rh98": {
                "min": MAP_LAYER_RH98_MIN_M,
                "max": MAP_LAYER_RH98_MAX_M,
                "palette": MAP_LAYER_RH98_PALETTE,
            },
        }
        as_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(as_json.encode("utf-8")).hexdigest()

    def get_processing_version_fingerprint(self) -> str:
        return self._processing_version_fingerprint()

    def get_visualization_version_fingerprint(self) -> str:
        return self._visualization_version_fingerprint()

    # ------------------------------------------------------------------
    # Shared payload helpers
    # ------------------------------------------------------------------

    def _geometry(self):
        return ee.Geometry.Rectangle(INDUS_DELTA_STUDY_AREA.bounds)

    def _processing(self) -> dict[str, Any]:
        return {
            "gedi_dataset": GEDI_L2A_MONTHLY,
            "quality_flag": 1,
            "degrade_flag": 0,
            "aggregation_method": "mosaic",
            "gmw_area_scale_m": GMW_AREA_SCALE_M,
            "gedi_analysis_scale_m": GEDI_RH98_SCALE_M,
            "best_effort": False,
        }

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
            "processing": self._processing(),
        }

    def _calculation_methods(self) -> dict[str, str]:
        return {
            "mapped_mangrove_area": "sum(pixelArea_ha over positive GMW-mask pixels)",
            "gedi_raster_coverage": "sum(pixelArea_ha over valid Carbon raster cells)",
            "direct_sampled_stock": "sum(Carbon_Mg_C_ha × pixelArea_ha)",
            "extrapolated_stock": "mean_Carbon_Mg_C_ha × mapped_mangrove_area_ha",
        }

    def _safe_error_message(self, error: Exception) -> str:
        text = str(error).lower()
        if "quota" in text or "noncommercial" in text or "restricted" in text:
            return "Earth Engine quota or restricted-mode limitation was encountered."
        if "timed out" in text or "deadline" in text or "timeout" in text:
            return "Earth Engine request timed out during carbon stock processing."
        if "not initialized" in text or "authentication" in text:
            return "Earth Engine authentication or initialization failed."
        return "Earth Engine carbon stock processing failed."

    def _not_connected_response(self, status: str, message: str) -> GeeCarbonStockSummaryResponse:
        base = self._base_payload()
        return GeeCarbonStockSummaryResponse(
            connected=False,
            status=status,
            study_area=base["study_area"],
            date_range=base["date_range"],
            processing=base["processing"],
            processing_performed=False,
            message=message,
        )

    def _failure_response(
        self,
        status: str,
        message: str,
        *,
        connected: bool = True,
        processing_performed: bool = False,
        carbon_density: CarbonDensityStats | None = None,
        area: AreaStats | None = None,
        stock: StockStats | None = None,
    ) -> GeeCarbonStockSummaryResponse:
        base = self._base_payload()
        return GeeCarbonStockSummaryResponse(
            connected=connected,
            status=status,
            study_area=base["study_area"],
            date_range=base["date_range"],
            processing=base["processing"],
            carbon_density=carbon_density,
            area=area,
            stock=stock,
            processing_performed=processing_performed,
            message=message,
        )

    # ------------------------------------------------------------------
    # Reducers
    # ------------------------------------------------------------------

    def _sum_reducer(self):
        return ee.Reducer.sum()

    def _combined_reducer(self):
        """min + mean + max + count + sum applied to all bands."""
        return (
            ee.Reducer.min()
            .combine(reducer2=ee.Reducer.mean(), sharedInputs=True)
            .combine(reducer2=ee.Reducer.max(), sharedInputs=True)
            .combine(reducer2=ee.Reducer.count(), sharedInputs=True)
            .combine(reducer2=ee.Reducer.sum(), sharedInputs=True)
        )

    # ------------------------------------------------------------------
    # Validation invariants
    # ------------------------------------------------------------------

    def _validate_stock_invariants(
        self,
        mapped_area: float | None,
        coverage_area: float | None,
        coverage_pct: float | None,
        direct_stock: float | None,
        extrapolated_stock: float | None,
        carbon_mean: float | None,
        carbon_count: int | None,
    ) -> list[str]:
        """Return a list of failure descriptions; empty means all invariants pass."""
        failures: list[str] = []

        if mapped_area is None or mapped_area <= 0:
            failures.append(
                f"Mapped mangrove area must be > 0; got {mapped_area!r}."
            )

        if coverage_area is None or coverage_area <= 0:
            failures.append(
                f"Valid GEDI raster coverage area must be > 0; got {coverage_area!r}."
            )

        if (
            mapped_area is not None
            and mapped_area > 0
            and coverage_area is not None
            and coverage_area > mapped_area
        ):
            failures.append(
                f"GEDI raster coverage area ({coverage_area:.4f} ha) "
                f"exceeds mapped mangrove area ({mapped_area:.4f} ha)."
            )

        if coverage_pct is not None and not (0.0 <= coverage_pct <= 100.0):
            failures.append(
                f"Coverage percentage ({coverage_pct:.4f}%) is outside [0, 100]."
            )

        if direct_stock is not None and direct_stock < 0:
            failures.append(
                f"Direct sampled carbon stock ({direct_stock:.4f} Mg C) is negative."
            )

        if (
            direct_stock is not None
            and extrapolated_stock is not None
            and extrapolated_stock < direct_stock
        ):
            failures.append(
                f"Extrapolated stock ({extrapolated_stock:.4f} Mg C) is less than "
                f"direct sampled stock ({direct_stock:.4f} Mg C)."
            )

        if carbon_mean is not None and mapped_area is not None and extrapolated_stock is not None:
            expected = carbon_mean * mapped_area
            rel_diff = abs(extrapolated_stock - expected) / max(abs(expected), 1.0)
            if rel_diff > CARBON_STOCK_FORMULA_TOLERANCE:
                failures.append(
                    f"Extrapolated stock ({extrapolated_stock:.4f}) does not equal "
                    f"mean Carbon × mapped area ({expected:.4f})."
                )

        if carbon_count is None or carbon_count <= 0:
            failures.append(
                f"Valid GEDI raster pixel count must be > 0; got {carbon_count!r}."
            )

        return failures

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def _run_live_summary(self) -> _CarbonStockResult:
        connection = gee_service_module.gee_service.get_connection_context()

        if not connection.enabled:
            return _CarbonStockResult(
                response=self._not_connected_response(
                    status="disabled",
                    message="Google Earth Engine carbon stock summary is disabled by configuration.",
                ),
                is_success=False,
            )

        if not connection.connected:
            return _CarbonStockResult(
                response=self._not_connected_response(
                    status=connection.status,
                    message=connection.message or "Google Earth Engine is not connected.",
                ),
                is_success=False,
            )

        geometry = self._geometry()

        # ── 1. Filter GEDI collection ─────────────────────────────────
        try:
            collection = (
                ee.ImageCollection(GEDI_L2A_MONTHLY)
                .filterBounds(geometry)
                .filterDate(GEDI_RH98_BASELINE_START_DATE, GEDI_RH98_BASELINE_END_DATE)
            )
            image_count = int(collection.size().getInfo())
        except Exception as error:
            logger.exception("Custom AOI/fixed pipeline failed during GEDI collection filtering")
            return _CarbonStockResult(
                response=self._failure_response(
                    status="dataset_inaccessible",
                    message=self._safe_error_message(error),
                ),
                is_success=False,
            )

        if image_count == 0:
            return _CarbonStockResult(
                response=self._failure_response(
                    status="empty_collection",
                    message="GEDI collection is empty for the configured bounds and date range.",
                ),
                is_success=False,
            )

        # ── 2. Verify required GEDI bands ─────────────────────────────
        try:
            first_bands = {
                str(b)
                for b in (ee.Image(collection.first()).bandNames().getInfo() or [])
            }
        except Exception as error:
            logger.exception("Custom AOI/fixed pipeline failed during GEDI required-band validation")
            return _CarbonStockResult(
                response=self._failure_response(
                    status="band_check_failed",
                    message=self._safe_error_message(error),
                ),
                is_success=False,
            )

        missing = [b for b in GEDI_REQUIRED_BANDS if b not in first_bands]
        if missing:
            return _CarbonStockResult(
                response=self._failure_response(
                    status="missing_required_bands",
                    message=f"Required GEDI bands are missing: {', '.join(missing)}.",
                ),
                is_success=False,
            )

        # ── 3. Verify and build GMW binary mask ───────────────────────
        try:
            gmw_meta = ee.data.getAsset(GMW_2020)
            if str(gmw_meta.get("type", "")).upper() != "IMAGE":
                return _CarbonStockResult(
                    response=self._failure_response(
                        status="gmw_asset_invalid",
                        message="Configured GMW asset must be an IMAGE.",
                    ),
                    is_success=False,
                )
            gmw_band_names = [
                str(b) for b in (ee.Image(GMW_2020).bandNames().getInfo() or [])
            ]
            if GMW_VALIDATED_MASK_BAND not in gmw_band_names:
                return _CarbonStockResult(
                    response=self._failure_response(
                        status="gmw_band_missing",
                        message=(
                            f"Validated GMW mask band '{GMW_VALIDATED_MASK_BAND}' not available."
                        ),
                    ),
                    is_success=False,
                )
        except Exception as error:
            logger.exception("Custom AOI/fixed pipeline failed during GMW asset validation")
            return _CarbonStockResult(
                response=self._failure_response(
                    status="gmw_asset_failure",
                    message=self._safe_error_message(error),
                ),
                is_success=False,
            )

        # ── 4. Compute mapped mangrove area (scale = 10 m) ────────────
        try:
            gmw_mask = gee_mask_service.build_binary_mask(GMW_2020, GMW_VALIDATED_MASK_BAND)
            # ee.Image.pixelArea() returns pixel area in m²; divide by 10 000 → hectares
            pixel_area_ha = ee.Image.pixelArea().divide(10000)
            gmw_area_image = pixel_area_ha.updateMask(gmw_mask)
            gmw_area_raw = gmw_area_image.reduceRegion(
                reducer=self._sum_reducer(),
                geometry=geometry,
                scale=GMW_AREA_SCALE_M,
                maxPixels=GEDI_RH98_MAX_PIXELS,
                tileScale=GEDI_RH98_TILE_SCALE,
                bestEffort=False,
            ).getInfo()
        except Exception as error:
            logger.exception("Custom AOI/fixed pipeline failed during mapped mangrove area calculation")
            return _CarbonStockResult(
                response=self._failure_response(
                    status="area_calculation_failed",
                    message=self._safe_error_message(error),
                    processing_performed=True,
                ),
                is_success=False,
            )

        gmw_area_raw = gmw_area_raw or {}
        mapped_mangrove_area_ha_raw = gmw_area_raw.get("area")
        mapped_mangrove_area_ha = (
            float(mapped_mangrove_area_ha_raw)
            if mapped_mangrove_area_ha_raw is not None
            else None
        )

        if mapped_mangrove_area_ha is None:
            return _CarbonStockResult(
                response=self._failure_response(
                    status="area_null_result",
                    message="GMW area reducer returned null; GMW mask may be empty.",
                    processing_performed=True,
                ),
                is_success=False,
            )

        # ── 5. Build GEDI mosaic → GMW mask → biomass image stack ─────
        try:
            analysis_image = self._build_analysis_image(
                collection=collection,
                geometry=geometry,
                gmw_mask=gmw_mask,
                pixel_area_ha=pixel_area_ha,
            )

            analysis_raw = analysis_image.reduceRegion(
                reducer=self._combined_reducer(),
                geometry=geometry,
                scale=GEDI_RH98_SCALE_M,
                maxPixels=GEDI_RH98_MAX_PIXELS,
                tileScale=GEDI_RH98_TILE_SCALE,
                bestEffort=False,
            ).getInfo()
        except Exception as error:
            logger.exception("Custom AOI/fixed pipeline failed during biomass/analysis image reduction")
            return _CarbonStockResult(
                response=self._failure_response(
                    status="processing_failed",
                    message=self._safe_error_message(error),
                    processing_performed=True,
                ),
                is_success=False,
            )

        analysis_raw = analysis_raw or {}

        # ── 6. Parse analysis results ─────────────────────────────────
        def _opt_float(key: str) -> float | None:
            v = analysis_raw.get(key)
            return float(v) if v is not None else None

        def _opt_int(key: str) -> int | None:
            v = analysis_raw.get(key)
            return int(v) if v is not None else None

        carbon_mean = _opt_float(f"{BIOMASS_BAND_CARBON}_mean")
        carbon_min = _opt_float(f"{BIOMASS_BAND_CARBON}_min")
        carbon_max = _opt_float(f"{BIOMASS_BAND_CARBON}_max")
        carbon_count = _opt_int(f"{BIOMASS_BAND_CARBON}_count")

        gedi_coverage_ha = _opt_float(f"{_GEDI_COVERAGE_BAND}_sum")
        direct_stock_mg_c = _opt_float(f"{_DIRECT_STOCK_BAND}_sum")

        # ── 7. Check for empty result ─────────────────────────────────
        if carbon_count == 0:
            return _CarbonStockResult(
                response=self._failure_response(
                    status="empty_carbon_result",
                    message="No valid mangrove-masked GEDI pixels after quality filtering.",
                    processing_performed=True,
                    carbon_density=CarbonDensityStats(valid_gedi_raster_pixel_count=0),
                ),
                is_success=False,
            )

        # ── 8. Derive coverage % and extrapolated stock ───────────────
        coverage_percent: float | None = None
        if gedi_coverage_ha is not None and mapped_mangrove_area_ha > 0:
            coverage_percent = (gedi_coverage_ha / mapped_mangrove_area_ha) * 100.0

        extrapolated_stock: float | None = None
        if carbon_mean is not None:
            extrapolated_stock = carbon_mean * mapped_mangrove_area_ha

        # ── 9. Validate invariants ────────────────────────────────────
        invariant_failures = self._validate_stock_invariants(
            mapped_area=mapped_mangrove_area_ha,
            coverage_area=gedi_coverage_ha,
            coverage_pct=coverage_percent,
            direct_stock=direct_stock_mg_c,
            extrapolated_stock=extrapolated_stock,
            carbon_mean=carbon_mean,
            carbon_count=carbon_count,
        )
        if invariant_failures:
            return _CarbonStockResult(
                response=self._failure_response(
                    status="validation_failed",
                    message="Stock invariants failed: " + "; ".join(invariant_failures),
                    processing_performed=True,
                    carbon_density=CarbonDensityStats(
                        mean_mg_c_ha=carbon_mean,
                        min_mg_c_ha=carbon_min,
                        max_mg_c_ha=carbon_max,
                        valid_gedi_raster_pixel_count=carbon_count,
                    ),
                    area=AreaStats(
                        mapped_mangrove_area_ha=mapped_mangrove_area_ha,
                        valid_gedi_raster_coverage_area_ha=gedi_coverage_ha,
                        gedi_raster_coverage_percent=coverage_percent,
                    ),
                    stock=StockStats(
                        direct_sampled_raster_carbon_mg_c=direct_stock_mg_c,
                        extrapolated_ecosystem_carbon_mg_c=extrapolated_stock,
                    ),
                ),
                is_success=False,
            )

        # ── 10. Reference comparison ──────────────────────────────────
        diff_from_older = (
            (direct_stock_mg_c - CARBON_STOCK_OLDER_REPORT_DIRECT_SAMPLED_MG_C)
            if direct_stock_mg_c is not None
            else None
        )
        reference_comparison = ReferenceComparison(
            older_reported_direct_sampled_carbon_mg_c=CARBON_STOCK_OLDER_REPORT_DIRECT_SAMPLED_MG_C,
            difference_from_older_report_mg_c=diff_from_older,
            note=(
                "The live Earth Engine area-weighted calculation reproduces the older "
                "direct sampled carbon result of approximately 1,480.37 Mg C. "
                "The earlier 70.6 ha coverage estimate assumed each raster cell occupied "
                "an exact 25 m × 25 m ground area, whereas ee.Image.pixelArea() "
                "calculates the ground area of the geographic raster grid."
            ),
        )

        # ── 11. Build successful response ─────────────────────────────
        base = self._base_payload()
        response = GeeCarbonStockSummaryResponse(
            connected=True,
            status="connected",
            study_area=base["study_area"],
            date_range=base["date_range"],
            carbon_density=CarbonDensityStats(
                mean_mg_c_ha=carbon_mean,
                min_mg_c_ha=carbon_min,
                max_mg_c_ha=carbon_max,
                valid_gedi_raster_pixel_count=carbon_count,
            ),
            area=AreaStats(
                mapped_mangrove_area_ha=mapped_mangrove_area_ha,
                valid_gedi_raster_coverage_area_ha=gedi_coverage_ha,
                gedi_raster_coverage_percent=coverage_percent,
            ),
            stock=StockStats(
                direct_sampled_raster_carbon_mg_c=direct_stock_mg_c,
                extrapolated_ecosystem_carbon_mg_c=extrapolated_stock,
            ),
            calculation_methods=self._calculation_methods(),
            assumptions=[
                "GEDI raster samples are spatially representative of the full mapped mangrove extent.",
                "The height-to-AGB relationship is a stand-level approximation and is not locally calibrated.",
                "The processing rectangle is not an exact administrative boundary.",
            ],
            processing=base["processing"],
            processing_performed=True,
            warnings=[
                "Direct sampled stock covers only valid GEDI/GMW raster cells.",
                "Extrapolated stock assumes sparse GEDI coverage represents all mapped mangroves.",
                "GEDI raster coverage is not the same as unique physical GEDI footprint area.",
            ],
            reference_comparison=reference_comparison,
        )
        return _CarbonStockResult(response=response, is_success=True)

    # ------------------------------------------------------------------
    # Public API with in-process success cache
    # ------------------------------------------------------------------

    def _make_custom_aoi_cache_key(
        self, aoi_geometry: dict, start_date: str, end_date: str, gmw_asset_id: str = ""
    ) -> str:
        """
        Create a normalized cache key for custom AOI results.

        Includes the GMW asset ID so that different regions (which use different
        GMW assets) never share a cache entry even when geometry and dates match.
        """
        normalized = {
            "geometry": aoi_geometry,
            "start_date": start_date,
            "end_date": end_date,
            "processing_version": self._processing_version_fingerprint(),
            "gmw_asset_id": gmw_asset_id,
        }
        key_str = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _utcnow(self) -> datetime:
        return datetime.now(timezone.utc)

    def _make_map_layer_cache_key(
        self, aoi_geometry: dict, start_date: str, end_date: str, gmw_asset_id: str = ""
    ) -> str:
        normalized = {
            "geometry": aoi_geometry,
            "start_date": start_date,
            "end_date": end_date,
            "processing_version": self._processing_version_fingerprint(),
            "visualization_version": self._visualization_version_fingerprint(),
            "gmw_asset_id": gmw_asset_id,
        }
        key_str = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _validate_tile_url_template(self, tile_url_template: str, *, layer_id: str) -> str:
        parsed = urlparse(tile_url_template)
        if parsed.scheme.lower() != "https":
            raise ValueError(f"Layer '{layer_id}' returned non-HTTPS tile URL.")
        if parsed.hostname not in settings.map_tile_allowed_hosts:
            raise ValueError(
                f"Layer '{layer_id}' returned tile URL host '{parsed.hostname}' not in allowlist."
            )
        return tile_url_template

    def _image_to_tile_url_template(self, image: Any, *, layer_id: str) -> str:
        map_id_response = image.getMapId()
        tile_fetcher = map_id_response.get("tile_fetcher")
        tile_url_template = getattr(tile_fetcher, "url_format", None)
        if not tile_url_template:
            raise ValueError(f"Layer '{layer_id}' map descriptor did not provide tile_fetcher.url_format.")
        return self._validate_tile_url_template(tile_url_template, layer_id=layer_id)

    def run_live_map_layers_for_custom_aoi(
        self,
        study_area_id: str,
        study_area_name: str,
        aoi_geometry: dict,
        start_date: str,
        end_date: str,
    ) -> MapLayersResponse:
        # Resolve region-specific GMW asset
        region_config = REGION_CATALOG.get(study_area_id) or REGION_CATALOG["custom"]
        gmw_asset_id = region_config.gmw_asset_id
        gmw_asset_type = region_config.gmw_asset_type

        study_area = StudyAreaInfo(id=study_area_id, name=study_area_name)
        date_range = DateRangeInfo(
            start_date=datetime.fromisoformat(start_date).date(),
            end_date=datetime.fromisoformat(end_date).date(),
        )
        processing_version = self._processing_version_fingerprint()
        visualization_version = self._visualization_version_fingerprint()
        generated_at = self._utcnow()
        expires_at = generated_at + timedelta(seconds=settings.map_layer_cache_ttl_seconds)
        cache_key = self._make_map_layer_cache_key(aoi_geometry, start_date, end_date, gmw_asset_id)

        cached = self._map_layer_descriptor_cache.get(cache_key)
        if cached:
            cached_expires_at = datetime.fromisoformat(cached["expires_at"])
            if cached_expires_at > self._utcnow():
                return MapLayersResponse(
                    study_area=study_area,
                    date_range=date_range,
                    aoi_geometry=aoi_geometry,
                    processing_version=processing_version,
                    visualization_version=visualization_version,
                    generated_at=cached["generated_at"],
                    expires_at=cached["expires_at"],
                    layers=[MapLayerDescriptor(**layer) for layer in cached["layers"]],
                    warnings=cached.get("warnings", []),
                    message=cached.get("message"),
                )

        connection = gee_service_module.gee_service.get_connection_context()
        if not connection.enabled:
            return MapLayersResponse(
                study_area=study_area,
                date_range=date_range,
                aoi_geometry=aoi_geometry,
                processing_version=processing_version,
                visualization_version=visualization_version,
                generated_at=generated_at.isoformat(),
                expires_at=expires_at.isoformat(),
                layers=[],
                warnings=["Google Earth Engine is disabled by configuration."],
                message="Map layers are unavailable while Earth Engine is disabled.",
            )
        if not connection.connected:
            return MapLayersResponse(
                study_area=study_area,
                date_range=date_range,
                aoi_geometry=aoi_geometry,
                processing_version=processing_version,
                visualization_version=visualization_version,
                generated_at=generated_at.isoformat(),
                expires_at=expires_at.isoformat(),
                layers=[],
                warnings=[connection.message or "Google Earth Engine is not connected."],
                message="Map layers are unavailable because Earth Engine is not connected.",
            )

        try:
            geometry = self._geojson_polygon_to_ee_geometry(aoi_geometry)
        except (ValueError, TypeError) as error:
            logger.exception("Map-layer AOI geometry conversion failed")
            return MapLayersResponse(
                study_area=study_area,
                date_range=date_range,
                aoi_geometry=aoi_geometry,
                processing_version=processing_version,
                visualization_version=visualization_version,
                generated_at=generated_at.isoformat(),
                expires_at=expires_at.isoformat(),
                layers=[],
                warnings=[f"Geometry validation failed: {str(error)}"],
                message="Map layers could not be generated.",
            )

        summary_key = self._make_custom_aoi_cache_key(aoi_geometry, start_date, end_date, gmw_asset_id)
        has_data = summary_key in self._custom_aoi_cache
        if not has_data:
            summary_probe = self._run_live_summary_parameterized(
                geometry, start_date, end_date, gmw_asset_id, gmw_asset_type
            )
            if not summary_probe.is_success:
                warning = summary_probe.response.get("message", "No raster layers available for this AOI.")
                no_data_markers = (
                    "no gedi data available",
                    "no mapped mangrove area",
                    "no valid gedi raster coverage",
                )
                if any(marker in warning.lower() for marker in no_data_markers):
                    return MapLayersResponse(
                        study_area=study_area,
                        date_range=date_range,
                        aoi_geometry=aoi_geometry,
                        processing_version=processing_version,
                        visualization_version=visualization_version,
                        generated_at=generated_at.isoformat(),
                        expires_at=expires_at.isoformat(),
                        layers=[],
                        warnings=[warning],
                        message="No raster map layers were generated for the selected AOI.",
                    )

        try:
            collection = (
                ee.ImageCollection(GEDI_L2A_MONTHLY)
                .filterBounds(geometry)
                .filterDate(start_date, end_date)
            )
            gmw_mask = gee_mask_service.build_binary_mask(gmw_asset_id, GMW_VALIDATED_MASK_BAND, gmw_asset_type)
            pixel_area_ha = ee.Image.pixelArea().divide(10000)
            analysis_image = self._build_analysis_image(
                collection=collection,
                geometry=geometry,
                gmw_mask=gmw_mask,
                pixel_area_ha=pixel_area_ha,
            )
            carbon_band = analysis_image.select([BIOMASS_BAND_CARBON])
            valid_mask = carbon_band.mask()
            rh98_band = analysis_image.select([BIOMASS_BAND_RH98]).updateMask(valid_mask)
            gedi_valid_mask = ee.Image.constant(1).updateMask(valid_mask)
            gmw_extent = gmw_mask.selfMask().clip(geometry)
            gedi_extent = gedi_valid_mask.selfMask().clip(geometry)
            carbon_density = carbon_band.updateMask(valid_mask).clip(geometry)

            layers = [
                MapLayerDescriptor(
                    id=MAP_LAYER_ID_GMW,
                    name="GMW Mangrove Extent",
                    tile_url_template=self._image_to_tile_url_template(
                        gmw_extent.visualize(min=0, max=1, palette=MAP_LAYER_GMW_PALETTE),
                        layer_id=MAP_LAYER_ID_GMW,
                    ),
                    default_visible=True,
                    default_opacity=0.65,
                    min=0,
                    max=1,
                    palette=MAP_LAYER_GMW_PALETTE,
                    units="Mapped mangrove",
                    legend_type="categorical",
                    description="Mapped mangrove extent (positive GMW mask pixels only). Non-mangrove pixels are transparent.",
                ),
                MapLayerDescriptor(
                    id=MAP_LAYER_ID_GEDI,
                    name="Valid GEDI Raster Coverage",
                    tile_url_template=self._image_to_tile_url_template(
                        gedi_extent.visualize(min=0, max=1, palette=MAP_LAYER_GEDI_PALETTE),
                        layer_id=MAP_LAYER_ID_GEDI,
                    ),
                    default_visible=True,
                    default_opacity=0.7,
                    min=0,
                    max=1,
                    palette=MAP_LAYER_GEDI_PALETTE,
                    units="Valid raster coverage",
                    legend_type="categorical",
                    description="Binary mask of valid GEDI/GMW raster cells. This is raster coverage, not unique physical GEDI footprints.",
                ),
                MapLayerDescriptor(
                    id=MAP_LAYER_ID_CARBON,
                    name="Carbon Density",
                    tile_url_template=self._image_to_tile_url_template(
                        carbon_density.visualize(
                            min=MAP_LAYER_CARBON_MIN_MG_C_HA,
                            max=MAP_LAYER_CARBON_MAX_MG_C_HA,
                            palette=MAP_LAYER_CARBON_PALETTE,
                        ),
                        layer_id=MAP_LAYER_ID_CARBON,
                    ),
                    default_visible=True,
                    default_opacity=0.8,
                    min=MAP_LAYER_CARBON_MIN_MG_C_HA,
                    max=MAP_LAYER_CARBON_MAX_MG_C_HA,
                    palette=MAP_LAYER_CARBON_PALETTE,
                    units="Mg C/ha",
                    legend_type="continuous",
                    description="Carbon density from the shared validated analysis stack. Display clipping is visualization-only and does not alter numerical results.",
                ),
                MapLayerDescriptor(
                    id=MAP_LAYER_ID_RH98,
                    name="RH98 Canopy Height",
                    tile_url_template=self._image_to_tile_url_template(
                        rh98_band.visualize(
                            min=MAP_LAYER_RH98_MIN_M,
                            max=MAP_LAYER_RH98_MAX_M,
                            palette=MAP_LAYER_RH98_PALETTE,
                        ),
                        layer_id=MAP_LAYER_ID_RH98,
                    ),
                    default_visible=False,
                    default_opacity=0.75,
                    min=MAP_LAYER_RH98_MIN_M,
                    max=MAP_LAYER_RH98_MAX_M,
                    palette=MAP_LAYER_RH98_PALETTE,
                    units="m",
                    legend_type="continuous",
                    description="RH98 canopy height at valid GEDI/GMW raster cells only; not wall-to-wall canopy coverage.",
                ),
            ]
        except Exception as error:
            logger.exception("Map-layer descriptor generation failed")
            return MapLayersResponse(
                study_area=study_area,
                date_range=date_range,
                aoi_geometry=aoi_geometry,
                processing_version=processing_version,
                visualization_version=visualization_version,
                generated_at=generated_at.isoformat(),
                expires_at=expires_at.isoformat(),
                layers=[],
                warnings=[self._safe_error_message(error)],
                message="Layer generation failed after successful AOI analysis.",
            )

        response = MapLayersResponse(
            study_area=study_area,
            date_range=date_range,
            aoi_geometry=aoi_geometry,
            processing_version=processing_version,
            visualization_version=visualization_version,
            generated_at=generated_at.isoformat(),
            expires_at=expires_at.isoformat(),
            layers=layers,
            warnings=[],
            message=None,
        )
        self._map_layer_descriptor_cache[cache_key] = {
            "generated_at": response.generated_at,
            "expires_at": response.expires_at,
            "layers": [layer.model_dump() for layer in response.layers],
            "warnings": response.warnings,
            "message": response.message,
        }
        return response

    def _geojson_polygon_to_ee_geometry(self, geojson_polygon: dict) -> Any:
        """
        Convert a validated GeoJSON Polygon to an ee.Geometry.

        Args:
            geojson_polygon: dict with type='Polygon' and coordinates in [lon, lat] order

        Returns:
            ee.Geometry object in EPSG:4326

        Raises:
            ValueError: If geometry is invalid
        """
        coordinates = geojson_polygon.get("coordinates")
        if not coordinates or len(coordinates) == 0:
            raise ValueError("GeoJSON Polygon must have coordinates")
        # Earth Engine EPSG:4326 uses x=longitude, y=latitude.
        # GeoJSON coordinates are already [longitude, latitude], so preserve order.
        return ee.Geometry(geojson_polygon)

    def _build_analysis_image(
        self,
        collection: Any,
        geometry: Any,
        gmw_mask: Any,
        pixel_area_ha: Any,
    ) -> Any:
        filtered = collection.map(apply_gedi_quality_filters)
        rh98_mosaic = filtered.mosaic().clip(geometry)
        mangrove_rh98 = rh98_mosaic.updateMask(gmw_mask).clip(geometry)
        biomass_stack = build_biomass_image_stack(mangrove_rh98)
        carbon_band = biomass_stack.select([BIOMASS_BAND_CARBON])
        gedi_coverage = (
            pixel_area_ha.updateMask(carbon_band.mask()).rename([_GEDI_COVERAGE_BAND])
        )
        direct_stock_image = carbon_band.multiply(pixel_area_ha).rename([_DIRECT_STOCK_BAND])
        return biomass_stack.addBands(gedi_coverage).addBands(direct_stock_image)

    def run_live_summary_for_custom_aoi(
        self,
        study_area_id: str,
        study_area_name: str,
        aoi_geometry: dict,
        start_date: str,
        end_date: str,
    ) -> "CustomAoiAnalyzeResponse":  # noqa: F821
        """
        Run live Earth Engine carbon stock analysis for a custom AOI polygon.

        Looks up the region-specific GMW asset from REGION_CATALOG using study_area_id.
        Asset selection is entirely server-side; clients never supply an asset ID.

        Args:
            study_area_id: Catalog key ("indus_delta", "abu_dhabi", or "custom")
            study_area_name: Human-readable study area name for the response
            aoi_geometry: Validated GeoJSON Polygon dict ([lon, lat] order)
            start_date: ISO date string (YYYY-MM-DD)
            end_date: ISO date string (YYYY-MM-DD), end-exclusive

        Returns:
            CustomAoiAnalyzeResponse with live results or error status
        """
        from datetime import datetime as dt

        from app.models.analysis import CustomAoiAnalyzeResponse, DateRangeInfo, StudyAreaInfo

        # Look up region-specific GMW configuration; fall back to custom (global) if unknown
        region_config = REGION_CATALOG.get(study_area_id) or REGION_CATALOG["custom"]
        gmw_asset_id = region_config.gmw_asset_id
        gmw_asset_type = region_config.gmw_asset_type

        study_area = StudyAreaInfo(id=study_area_id, name=study_area_name)
        date_range = DateRangeInfo(
            start_date=dt.fromisoformat(start_date).date(),
            end_date=dt.fromisoformat(end_date).date(),
        )

        cache_key = self._make_custom_aoi_cache_key(aoi_geometry, start_date, end_date, gmw_asset_id)

        if cache_key in self._custom_aoi_cache:
            cached = self._custom_aoi_cache[cache_key]
            if cached.get("is_success"):
                logger.warning("Custom AOI cache hit for key %s", cache_key)
                return CustomAoiAnalyzeResponse(
                    mode="live_earth_engine_custom_aoi",
                    study_area=study_area,
                    date_range=date_range,
                    datasets=cached["datasets"],
                    results=cached["results"],
                    methodology=cached["methodology"],
                    warning=cached["warning"],
                    assumptions=cached.get("assumptions"),
                    aoi_geometry=aoi_geometry,
                )

        connection = gee_service_module.gee_service.get_connection_context()

        if not connection.enabled:
            response = CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area=study_area,
                date_range=date_range,
                datasets=[],
                results=None,  # type: ignore
                methodology=None,  # type: ignore
                warning="Google Earth Engine is disabled by configuration.",
                assumptions=None,
                aoi_geometry=aoi_geometry,
            )
            return response

        if not connection.connected:
            response = CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area=study_area,
                date_range=date_range,
                datasets=[],
                results=None,  # type: ignore
                methodology=None,  # type: ignore
                warning=connection.message or "Google Earth Engine is not connected.",
                assumptions=None,
                aoi_geometry=aoi_geometry,
            )
            return response

        try:
            geometry = self._geojson_polygon_to_ee_geometry(aoi_geometry)
        except (ValueError, TypeError) as error:
            logger.exception("Custom AOI geometry conversion failed")
            return CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area=study_area,
                date_range=date_range,
                datasets=[],
                results=None,  # type: ignore
                methodology=None,  # type: ignore
                warning=f"Geometry validation failed: {str(error)}",
                assumptions=None,
                aoi_geometry=aoi_geometry,
            )

        try:
            result = self._run_live_summary_parameterized(
                geometry, start_date, end_date, gmw_asset_id, gmw_asset_type
            )
        except Exception as error:
            logger.exception("Custom AOI summary execution failed")
            response = CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area=study_area,
                date_range=date_range,
                datasets=[],
                results=None,  # type: ignore
                methodology=None,  # type: ignore
                warning=self._safe_error_message(error),
                assumptions=None,
                aoi_geometry=aoi_geometry,
            )
            return response

        if not result.is_success:
            response = CustomAoiAnalyzeResponse(
                mode="live_earth_engine_custom_aoi",
                study_area=study_area,
                date_range=date_range,
                datasets=["GEDI L2A RH98", "GMW 2020"],
                results=None,  # type: ignore
                methodology=self._get_methodology(),
                warning=result.response.get("message", "Analysis failed"),
                assumptions=None,
                aoi_geometry=aoi_geometry,
            )
            return response

        response = CustomAoiAnalyzeResponse(
            mode="live_earth_engine_custom_aoi",
            study_area=study_area,
            date_range=date_range,
            datasets=["GEDI L2A RH98", "GMW 2020"],
            results=result.response.get("results"),  # type: ignore
            methodology=self._get_methodology(),
            warning=result.response.get("warning", ""),
            assumptions=[
                "GEDI raster samples are spatially representative of the full mapped mangrove extent.",
                "The height-to-AGB relationship is a stand-level approximation and is not locally calibrated.",
                "The submitted polygon is treated as a study extent, not an official administrative boundary.",
            ],
            aoi_geometry=aoi_geometry,
        )

        self._custom_aoi_cache[cache_key] = {
            "is_success": True,
            "datasets": response.datasets,
            "results": response.results,
            "methodology": response.methodology,
            "warning": response.warning,
            "assumptions": response.assumptions,
        }
        logger.warning("Custom AOI cache store for key %s", cache_key)
        return response

    def _get_methodology(self) -> "MethodologyInfo":  # noqa: F821
        """Return biomass and carbon formulas."""
        from app.models.analysis import MethodologyInfo

        return MethodologyInfo(
            agb_formula="AGB = 10 × RH98",
            bgb_formula="BGB = 0.49 × AGB",
            tab_formula="TAB = AGB + BGB",
            carbon_formula="Carbon = 0.5 × TAB",
        )

    def _run_live_summary_parameterized(
        self,
        geometry: Any,
        start_date: str,
        end_date: str,
        gmw_asset_id: str = GMW_2020_INDUS,
        gmw_asset_type: str = GMW_ASSET_TYPE_IMAGE,
    ) -> _CarbonStockResult:
        """
        Parameterized version of _run_live_summary for custom AOI.

        Performs full Earth Engine analysis with custom geometry, date range and
        the region-specific GMW asset. The asset type determines whether the GMW
        source is loaded as an Image (project regional assets) or an ImageCollection
        mosaiced into a single image (public global GMW).

        Args:
            geometry: ee.Geometry object
            start_date: ISO date string
            end_date: ISO date string
            gmw_asset_id: Earth Engine asset ID for the GMW mask; defaults to the
                Indus IndusDelta asset for backward compatibility.
            gmw_asset_type: "IMAGE" or "IMAGE_COLLECTION".

        Returns:
            _CarbonStockResult with results dict or error info
        """
        connection = gee_service_module.gee_service.get_connection_context()

        if not connection.enabled or not connection.connected:
            return _CarbonStockResult(
                response={"message": "Earth Engine not connected", "error": True},
                is_success=False,
            )

        try:
            collection = (
                ee.ImageCollection(GEDI_L2A_MONTHLY)
                .filterBounds(geometry)
                .filterDate(start_date, end_date)
            )
            image_count = int(collection.size().getInfo())
        except Exception as error:
            logger.exception("Custom AOI pipeline failed during GEDI collection filtering")
            return _CarbonStockResult(
                response={"message": self._safe_error_message(error), "error": True},
                is_success=False,
            )

        if image_count == 0:
            return _CarbonStockResult(
                response={"message": "No GEDI data available for the AOI and date range.", "error": True},
                is_success=False,
            )

        try:
            first_bands = {str(b) for b in (ee.Image(collection.first()).bandNames().getInfo() or [])}
        except Exception as error:
            logger.exception("Custom AOI pipeline failed during GEDI required-band validation")
            return _CarbonStockResult(
                response={"message": self._safe_error_message(error), "error": True},
                is_success=False,
            )

        missing = [b for b in GEDI_REQUIRED_BANDS if b not in first_bands]
        if missing:
            return _CarbonStockResult(
                response={"message": f"Required GEDI bands missing: {', '.join(missing)}.", "error": True},
                is_success=False,
            )

        # Validate GMW asset — for IMAGE_COLLECTION we check the collection itself
        try:
            gmw_meta = ee.data.getAsset(gmw_asset_id)
            actual_type = str(gmw_meta.get("type", "")).upper()
            expected_types = {"IMAGE", "IMAGE_COLLECTION"}
            if actual_type not in expected_types:
                return _CarbonStockResult(
                    response={"message": f"GMW asset '{gmw_asset_id}' has unexpected type '{actual_type}'.", "error": True},
                    is_success=False,
                )
            # Validate mask band exists
            if gmw_asset_type == "IMAGE_COLLECTION":
                first_gmw = ee.ImageCollection(gmw_asset_id).first()
                gmw_band_names = [str(b) for b in (first_gmw.bandNames().getInfo() or [])]
            else:
                gmw_band_names = [str(b) for b in (ee.Image(gmw_asset_id).bandNames().getInfo() or [])]
            if GMW_VALIDATED_MASK_BAND not in gmw_band_names:
                return _CarbonStockResult(
                    response={"message": f"GMW mask band '{GMW_VALIDATED_MASK_BAND}' not found in '{gmw_asset_id}'.", "error": True},
                    is_success=False,
                )
        except Exception as error:
            logger.exception("Custom AOI pipeline failed during GMW asset validation")
            return _CarbonStockResult(
                response={"message": self._safe_error_message(error), "error": True},
                is_success=False,
            )

        try:
            gmw_mask = gee_mask_service.build_binary_mask(gmw_asset_id, GMW_VALIDATED_MASK_BAND, gmw_asset_type)
            pixel_area_ha = ee.Image.pixelArea().divide(10000)
            gmw_area_image = pixel_area_ha.updateMask(gmw_mask)
            gmw_area_raw = gmw_area_image.reduceRegion(
                reducer=self._sum_reducer(),
                geometry=geometry,
                scale=GMW_AREA_SCALE_M,
                maxPixels=GEDI_RH98_MAX_PIXELS,
                tileScale=GEDI_RH98_TILE_SCALE,
                bestEffort=False,
            ).getInfo()
        except Exception as error:
            logger.exception("Custom AOI pipeline failed during mapped mangrove area calculation")
            return _CarbonStockResult(
                response={"message": self._safe_error_message(error), "error": True},
                is_success=False,
            )

        gmw_area_raw = gmw_area_raw or {}
        mapped_mangrove_area_ha = float(gmw_area_raw.get("area")) if gmw_area_raw.get("area") else None

        if mapped_mangrove_area_ha is None or mapped_mangrove_area_ha <= 0:
            return _CarbonStockResult(
                response={"message": "AOI has no mapped mangrove area (no GMW mask coverage).", "error": True},
                is_success=False,
            )

        try:
            analysis_img = self._build_analysis_image(
                collection=collection,
                geometry=geometry,
                gmw_mask=gmw_mask,
                pixel_area_ha=pixel_area_ha,
            )

            stats_raw = analysis_img.reduceRegion(
                reducer=self._combined_reducer(),
                geometry=geometry,
                scale=GEDI_RH98_SCALE_M,
                maxPixels=GEDI_RH98_MAX_PIXELS,
                tileScale=GEDI_RH98_TILE_SCALE,
                bestEffort=False,
            ).getInfo()
        except Exception as error:
            logger.exception("Custom AOI pipeline failed during biomass/analysis image reduction")
            return _CarbonStockResult(
                response={"message": self._safe_error_message(error), "error": True},
                is_success=False,
            )

        stats_raw = stats_raw or {}
        gedi_coverage_ha = stats_raw.get(f"{_GEDI_COVERAGE_BAND}_sum")
        direct_stock_mg_c = stats_raw.get(f"{_DIRECT_STOCK_BAND}_sum")
        carbon_min = stats_raw.get(f"{BIOMASS_BAND_CARBON}_min")
        carbon_mean = stats_raw.get(f"{BIOMASS_BAND_CARBON}_mean")
        carbon_max = stats_raw.get(f"{BIOMASS_BAND_CARBON}_max")
        carbon_count = stats_raw.get(f"{BIOMASS_BAND_CARBON}_count")

        gedi_coverage_ha = float(gedi_coverage_ha) if gedi_coverage_ha else None
        direct_stock_mg_c = float(direct_stock_mg_c) if direct_stock_mg_c else None
        carbon_min = float(carbon_min) if carbon_min else None
        carbon_mean = float(carbon_mean) if carbon_mean else None
        carbon_max = float(carbon_max) if carbon_max else None
        carbon_count = int(carbon_count) if carbon_count else None

        if gedi_coverage_ha is None or gedi_coverage_ha <= 0:
            return _CarbonStockResult(
                response={"message": "AOI has no valid GEDI raster coverage.", "error": True},
                is_success=False,
            )

        coverage_percent = (gedi_coverage_ha / mapped_mangrove_area_ha * 100) if mapped_mangrove_area_ha > 0 else 0
        extrapolated_stock = carbon_mean * mapped_mangrove_area_ha if carbon_mean else None

        invariant_failures = self._validate_stock_invariants(
            mapped_mangrove_area_ha,
            gedi_coverage_ha,
            coverage_percent,
            direct_stock_mg_c,
            extrapolated_stock,
            carbon_mean,
            carbon_count,
        )

        if invariant_failures:
            return _CarbonStockResult(
                response={
                    "message": "Validation failed; returning raw values for debugging.",
                    "error": True,
                    "results": {
                        "valid_gedi_samples": carbon_count or 0,
                        "mean_rh98_m": stats_raw.get(f"{BIOMASS_BAND_RH98}_mean", 0),
                        "min_rh98_m": stats_raw.get(f"{BIOMASS_BAND_RH98}_min", 0),
                        "max_rh98_m": stats_raw.get(f"{BIOMASS_BAND_RH98}_max", 0),
                        "mean_agb_mg_ha": stats_raw.get(f"{BIOMASS_BAND_AGB}_mean", 0),
                        "mean_bgb_mg_ha": stats_raw.get(f"{BIOMASS_BAND_BGB}_mean", 0),
                        "mean_carbon_mg_c_ha": carbon_mean or 0,
                        "min_carbon_mg_c_ha": carbon_min or 0,
                        "max_carbon_mg_c_ha": carbon_max or 0,
                        "mangrove_area_ha": mapped_mangrove_area_ha or 0,
                        "gedi_sampled_coverage_percent": coverage_percent or 0,
                        "direct_sampled_carbon_mg_c": direct_stock_mg_c or 0,
                        "extrapolated_total_carbon_mg_c": extrapolated_stock or 0,
                    },
                },
                is_success=False,
            )

        result_dict = {
            "results": {
                "valid_gedi_samples": carbon_count or 0,
                "mean_rh98_m": stats_raw.get(f"{BIOMASS_BAND_RH98}_mean", 0),
                "min_rh98_m": stats_raw.get(f"{BIOMASS_BAND_RH98}_min", 0),
                "max_rh98_m": stats_raw.get(f"{BIOMASS_BAND_RH98}_max", 0),
                "mean_agb_mg_ha": stats_raw.get(f"{BIOMASS_BAND_AGB}_mean", 0),
                "mean_bgb_mg_ha": stats_raw.get(f"{BIOMASS_BAND_BGB}_mean", 0),
                "mean_carbon_mg_c_ha": carbon_mean or 0,
                "min_carbon_mg_c_ha": carbon_min or 0,
                "max_carbon_mg_c_ha": carbon_max or 0,
                "mangrove_area_ha": mapped_mangrove_area_ha or 0,
                "gedi_sampled_coverage_percent": coverage_percent or 0,
                "direct_sampled_carbon_mg_c": direct_stock_mg_c or 0,
                "extrapolated_total_carbon_mg_c": extrapolated_stock or 0,
            },
            "warning": "Custom AOI analysis complete.",
        }

        return _CarbonStockResult(response=result_dict, is_success=True)

    def get_carbon_stock_summary(self) -> GeeCarbonStockSummaryResponse:
        if self._cached_success_response is not None:
            return self._cached_success_response

        result = self._run_live_summary()
        if result.is_success:
            self._cached_success_response = result.response
        return result.response


gee_carbon_stock_service = GeeCarbonStockService()
