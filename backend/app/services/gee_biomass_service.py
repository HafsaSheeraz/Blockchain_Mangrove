"""
Module 9: Mangrove biomass and carbon-density summary service.

Processing graph (reuses the validated Module 8.1 pipeline):
  GEDI L2A monthly raster (LARSE/GEDI/GEDI02_A_002_MONTHLY)
  → filterBounds(Indus Delta rectangle)
  → filterDate(2020-01-01, 2020-04-01)  [end-exclusive]
  → map(quality_flag == 1, degrade_flag == 0, select rh98)
  → mosaic()
  → updateMask(GMW b1 binary mask)
  → build_biomass_image_stack()  [5-band image: RH98, AGB, BGB, TAB, Carbon]
  → reduceRegion(min+mean+max+count, scale=25 m, tileScale=4, bestEffort=False)

This endpoint calculates density statistics only.
No mangrove area, no total ecosystem carbon stock is computed here.
"""

from dataclasses import dataclass
from typing import Any

from app.core.gee_datasets import (
    BIOMASS_BAND_AGB,
    BIOMASS_BAND_BGB,
    BIOMASS_BAND_CARBON,
    BIOMASS_BAND_RH98,
    BIOMASS_BAND_TAB,
    BIOMASS_FORMULA_TOLERANCE,
    BIOMASS_HEIGHT_TO_AGB,
    BIOMASS_ROOT_TO_SHOOT,
    BIOMASS_TO_CARBON,
    DATE_FILTER_CONVENTION,
    GEDI_L2A_MONTHLY,
    GEDI_REQUIRED_BANDS,
    GEDI_RH98_BASELINE_END_DATE,
    GEDI_RH98_BASELINE_START_DATE,
    GEDI_RH98_MAX_PIXELS,
    GEDI_RH98_SCALE_M,
    GEDI_RH98_TILE_SCALE,
    GMW_2020,
    GMW_VALIDATED_MASK_BAND,
    INDUS_DELTA_STUDY_AREA,
)
from app.models.gee_biomass import BandStats, BiomassStatistics, GeeBiomassSummaryResponse
from app.services import gee_service as gee_service_module
from app.services.gee_mask_service import gee_mask_service
from app.services.gee_rh98_summary_service import apply_gedi_quality_filters

ee = gee_service_module.ee

_BAND_UNITS = {
    BIOMASS_BAND_RH98: "m",
    BIOMASS_BAND_AGB: "Mg/ha",
    BIOMASS_BAND_BGB: "Mg/ha",
    BIOMASS_BAND_TAB: "Mg/ha",
    BIOMASS_BAND_CARBON: "Mg C/ha",
}


def build_biomass_image_stack(masked_rh98_image):
    """
    Build a 5-band image stack from a quality-filtered, GMW-masked RH98 image.

    All derived bands share the same valid-data mask as the input rh98 image.
    No pixels are created outside valid GEDI/GMW coverage.

    Band order: RH98 (m), AGB (Mg/ha), BGB (Mg/ha), TAB (Mg/ha), Carbon (Mg C/ha).

    Formulas (applied pixel-wise to each valid raster cell):
        AGB     = BIOMASS_HEIGHT_TO_AGB  × RH98      (10.0 × RH98)
        BGB     = BIOMASS_ROOT_TO_SHOOT  × AGB       (0.49 × AGB)
        TAB     = AGB + BGB
        Carbon  = BIOMASS_TO_CARBON      × TAB       (0.5  × TAB)
    """
    rh98 = masked_rh98_image.rename([BIOMASS_BAND_RH98])
    agb = rh98.multiply(BIOMASS_HEIGHT_TO_AGB).rename([BIOMASS_BAND_AGB])
    bgb = agb.multiply(BIOMASS_ROOT_TO_SHOOT).rename([BIOMASS_BAND_BGB])
    tab = agb.add(bgb).rename([BIOMASS_BAND_TAB])
    carbon = tab.multiply(BIOMASS_TO_CARBON).rename([BIOMASS_BAND_CARBON])
    return rh98.addBands(agb).addBands(bgb).addBands(tab).addBands(carbon)


def _parse_band_stats(stats_dict: dict, band_key: str, unit: str) -> BandStats:
    """Extract min/mean/max/count for one named band from a combined reducer output dict."""
    count_raw = stats_dict.get(f"{band_key}_count")
    pixel_count = int(count_raw) if count_raw is not None else None

    # A count of zero means the reduction found no valid pixels; stats are undefined.
    if pixel_count == 0:
        return BandStats(unit=unit, min=None, mean=None, max=None, valid_raster_pixel_count=0)

    def _as_float(key: str) -> float | None:
        v = stats_dict.get(key)
        return float(v) if v is not None else None

    return BandStats(
        unit=unit,
        min=_as_float(f"{band_key}_min"),
        mean=_as_float(f"{band_key}_mean"),
        max=_as_float(f"{band_key}_max"),
        valid_raster_pixel_count=pixel_count,
    )


def _validate_formula_invariants(stats: BiomassStatistics) -> list[str]:
    """
    Validate that derived-band statistics satisfy formula invariants.

    Returns a list of human-readable failure descriptions; empty list means all pass.
    Validation is relative (tolerance = BIOMASS_FORMULA_TOLERANCE) so floating-point
    imprecision in large-scale reductions does not cause false failures.
    """
    failures: list[str] = []

    def _rel_ok(calc: float | None, expected: float | None) -> bool:
        if calc is None or expected is None:
            return True  # skip when data is genuinely missing
        return abs(calc - expected) / max(abs(expected), 1.0) <= BIOMASS_FORMULA_TOLERANCE

    rh98_mean = stats.rh98.mean
    agb_mean = stats.agb.mean
    bgb_mean = stats.bgb.mean
    tab_mean = stats.tab.mean
    carbon_mean = stats.carbon.mean

    expected_agb = BIOMASS_HEIGHT_TO_AGB * rh98_mean if rh98_mean is not None else None
    if not _rel_ok(agb_mean, expected_agb):
        failures.append(
            f"AGB mean ({agb_mean:.6f}) does not satisfy "
            f"AGB = {BIOMASS_HEIGHT_TO_AGB} × RH98 (expected {expected_agb:.6f})"
        )

    expected_bgb = BIOMASS_ROOT_TO_SHOOT * agb_mean if agb_mean is not None else None
    if not _rel_ok(bgb_mean, expected_bgb):
        failures.append(
            f"BGB mean ({bgb_mean:.6f}) does not satisfy "
            f"BGB = {BIOMASS_ROOT_TO_SHOOT} × AGB (expected {expected_bgb:.6f})"
        )

    if agb_mean is not None and bgb_mean is not None:
        expected_tab = agb_mean + bgb_mean
        if not _rel_ok(tab_mean, expected_tab):
            failures.append(
                f"TAB mean ({tab_mean:.6f}) does not satisfy "
                f"TAB = AGB + BGB (expected {expected_tab:.6f})"
            )

    expected_carbon = BIOMASS_TO_CARBON * tab_mean if tab_mean is not None else None
    if not _rel_ok(carbon_mean, expected_carbon):
        failures.append(
            f"Carbon mean ({carbon_mean:.6f}) does not satisfy "
            f"Carbon = {BIOMASS_TO_CARBON} × TAB (expected {expected_carbon:.6f})"
        )

    # All derived bands share the same mask → their pixel counts must be equal.
    counts = [
        s.valid_raster_pixel_count
        for s in [stats.rh98, stats.agb, stats.bgb, stats.tab, stats.carbon]
        if s.valid_raster_pixel_count is not None
    ]
    unique_counts = set(counts)
    if len(unique_counts) > 1:
        failures.append(f"Band pixel counts are inconsistent: {sorted(unique_counts)}")

    return failures


@dataclass(frozen=True)
class _BiomassSummaryResult:
    response: GeeBiomassSummaryResponse
    is_success: bool


class GeeBiomassService:
    """Live biomass and carbon-density statistics service for the Indus Delta mangroves."""

    def __init__(self) -> None:
        self._cached_success_response: GeeBiomassSummaryResponse | None = None

    # ------------------------------------------------------------------
    # Shared payload helpers
    # ------------------------------------------------------------------

    def _geometry(self):
        return ee.Geometry.Rectangle(INDUS_DELTA_STUDY_AREA.bounds)

    def _methodology(self) -> dict[str, Any]:
        return {
            "height_to_agb_factor": BIOMASS_HEIGHT_TO_AGB,
            "root_to_shoot_ratio": BIOMASS_ROOT_TO_SHOOT,
            "biomass_to_carbon_fraction": BIOMASS_TO_CARBON,
            "agb_formula": f"AGB = {BIOMASS_HEIGHT_TO_AGB:.0f} \u00d7 RH98",
            "bgb_formula": f"BGB = {BIOMASS_ROOT_TO_SHOOT} \u00d7 AGB",
            "tab_formula": "TAB = AGB + BGB",
            "carbon_formula": f"Carbon = {BIOMASS_TO_CARBON} \u00d7 TAB",
        }

    def _processing(self) -> dict[str, Any]:
        return {
            "gedi_dataset": GEDI_L2A_MONTHLY,
            "quality_flag": 1,
            "degrade_flag": 0,
            "aggregation_method": "mosaic",
            "scale_m": GEDI_RH98_SCALE_M,
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
            "methodology": self._methodology(),
            "processing": self._processing(),
        }

    def _safe_error_message(self, error: Exception) -> str:
        text = str(error).lower()
        if "quota" in text or "noncommercial" in text or "restricted" in text:
            return "Earth Engine quota or restricted-mode limitation was encountered."
        if "timed out" in text or "deadline" in text or "timeout" in text:
            return "Earth Engine request timed out during biomass processing."
        return "Earth Engine biomass processing failed."

    def _not_connected_response(self, status: str, message: str) -> GeeBiomassSummaryResponse:
        base = self._base_payload()
        return GeeBiomassSummaryResponse(
            connected=False,
            status=status,
            study_area=base["study_area"],
            date_range=base["date_range"],
            methodology=base["methodology"],
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
        statistics: BiomassStatistics | None = None,
    ) -> GeeBiomassSummaryResponse:
        base = self._base_payload()
        return GeeBiomassSummaryResponse(
            connected=connected,
            status=status,
            study_area=base["study_area"],
            date_range=base["date_range"],
            methodology=base["methodology"],
            processing=base["processing"],
            statistics=statistics,
            processing_performed=processing_performed,
            message=message,
        )

    # ------------------------------------------------------------------
    # EE reducer helpers
    # ------------------------------------------------------------------

    def _combined_reducer(self):
        return (
            ee.Reducer.min()
            .combine(reducer2=ee.Reducer.mean(), sharedInputs=True)
            .combine(reducer2=ee.Reducer.max(), sharedInputs=True)
            .combine(reducer2=ee.Reducer.count(), sharedInputs=True)
        )

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def _run_live_summary(self) -> _BiomassSummaryResult:
        connection = gee_service_module.gee_service.get_connection_context()

        if not connection.enabled:
            return _BiomassSummaryResult(
                response=self._not_connected_response(
                    status="disabled",
                    message="Google Earth Engine biomass summary is disabled by configuration.",
                ),
                is_success=False,
            )

        if not connection.connected:
            return _BiomassSummaryResult(
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
            return _BiomassSummaryResult(
                response=self._failure_response(
                    status="dataset_inaccessible",
                    message=self._safe_error_message(error),
                ),
                is_success=False,
            )

        if image_count == 0:
            return _BiomassSummaryResult(
                response=self._failure_response(
                    status="empty_collection",
                    message="GEDI collection is empty for the configured bounds and date range.",
                ),
                is_success=False,
            )

        # ── 2. Verify required bands ──────────────────────────────────
        try:
            first_bands = {str(b) for b in (ee.Image(collection.first()).bandNames().getInfo() or [])}
        except Exception as error:
            return _BiomassSummaryResult(
                response=self._failure_response(
                    status="band_check_failed",
                    message=self._safe_error_message(error),
                ),
                is_success=False,
            )

        missing = [b for b in GEDI_REQUIRED_BANDS if b not in first_bands]
        if missing:
            return _BiomassSummaryResult(
                response=self._failure_response(
                    status="missing_required_bands",
                    message=f"Required GEDI bands are missing: {', '.join(missing)}.",
                ),
                is_success=False,
            )

        # ── 3. Verify GMW asset ───────────────────────────────────────
        try:
            gmw_meta = ee.data.getAsset(GMW_2020)
            if str(gmw_meta.get("type", "")).upper() != "IMAGE":
                return _BiomassSummaryResult(
                    response=self._failure_response(
                        status="gmw_asset_invalid",
                        message="Configured GMW asset must be an IMAGE.",
                    ),
                    is_success=False,
                )
            gmw_band_names = [str(b) for b in (ee.Image(GMW_2020).bandNames().getInfo() or [])]
            if GMW_VALIDATED_MASK_BAND not in gmw_band_names:
                return _BiomassSummaryResult(
                    response=self._failure_response(
                        status="gmw_band_missing",
                        message=f"Validated GMW mask band '{GMW_VALIDATED_MASK_BAND}' not available.",
                    ),
                    is_success=False,
                )
        except Exception as error:
            return _BiomassSummaryResult(
                response=self._failure_response(
                    status="gmw_asset_failure",
                    message=self._safe_error_message(error),
                ),
                is_success=False,
            )

        # ── 4. Build mosaic → apply GMW mask → build biomass stack ────
        try:
            filtered = collection.map(apply_gedi_quality_filters)
            rh98_mosaic = filtered.mosaic().clip(geometry)
            gmw_mask = gee_mask_service.build_binary_mask(GMW_2020, GMW_VALIDATED_MASK_BAND)
            mangrove_rh98 = rh98_mosaic.updateMask(gmw_mask).clip(geometry)

            biomass_stack = build_biomass_image_stack(mangrove_rh98)

            stats_raw = biomass_stack.reduceRegion(
                reducer=self._combined_reducer(),
                geometry=geometry,
                scale=GEDI_RH98_SCALE_M,
                maxPixels=GEDI_RH98_MAX_PIXELS,
                tileScale=GEDI_RH98_TILE_SCALE,
                bestEffort=False,
            ).getInfo()
        except Exception as error:
            return _BiomassSummaryResult(
                response=self._failure_response(
                    status="processing_failed",
                    message=self._safe_error_message(error),
                    processing_performed=True,
                ),
                is_success=False,
            )

        stats_raw = stats_raw or {}

        # ── 5. Parse per-band statistics ──────────────────────────────
        biomass_stats = BiomassStatistics(
            rh98=_parse_band_stats(stats_raw, BIOMASS_BAND_RH98, _BAND_UNITS[BIOMASS_BAND_RH98]),
            agb=_parse_band_stats(stats_raw, BIOMASS_BAND_AGB, _BAND_UNITS[BIOMASS_BAND_AGB]),
            bgb=_parse_band_stats(stats_raw, BIOMASS_BAND_BGB, _BAND_UNITS[BIOMASS_BAND_BGB]),
            tab=_parse_band_stats(stats_raw, BIOMASS_BAND_TAB, _BAND_UNITS[BIOMASS_BAND_TAB]),
            carbon=_parse_band_stats(stats_raw, BIOMASS_BAND_CARBON, _BAND_UNITS[BIOMASS_BAND_CARBON]),
        )

        # ── 6. Check for empty masked result ──────────────────────────
        if biomass_stats.rh98.valid_raster_pixel_count == 0:
            return _BiomassSummaryResult(
                response=self._failure_response(
                    status="masked_result_empty",
                    message="No valid mangrove-masked GEDI pixels after quality filtering.",
                    processing_performed=True,
                    statistics=biomass_stats,
                ),
                is_success=False,
            )

        # ── 7. Validate formula invariants ────────────────────────────
        formula_failures = _validate_formula_invariants(biomass_stats)
        if formula_failures:
            return _BiomassSummaryResult(
                response=self._failure_response(
                    status="formula_validation_failed",
                    message="Formula invariants failed: " + "; ".join(formula_failures),
                    processing_performed=True,
                    statistics=biomass_stats,
                ),
                is_success=False,
            )

        # ── 8. Build successful response ──────────────────────────────
        base = self._base_payload()
        response = GeeBiomassSummaryResponse(
            connected=True,
            status="connected",
            study_area=base["study_area"],
            date_range=base["date_range"],
            methodology=base["methodology"],
            statistics=biomass_stats,
            gmw_mask={
                "asset_id": GMW_2020,
                "band": GMW_VALIDATED_MASK_BAND,
                "positive_pixels_only": True,
            },
            processing=base["processing"],
            processing_performed=True,
            warnings=[
                "Results are biomass and carbon densities at valid GEDI/GMW raster pixels.",
                "Counts represent valid raster cells, not unique GEDI shots.",
                "No ecosystem-wide total carbon stock is calculated in this module.",
                "The height-to-AGB factor is a stand-level approximation and is not locally calibrated.",
            ],
        )
        return _BiomassSummaryResult(response=response, is_success=True)

    # ------------------------------------------------------------------
    # Public API with in-process success cache
    # ------------------------------------------------------------------

    def get_biomass_summary(self) -> GeeBiomassSummaryResponse:
        if self._cached_success_response is not None:
            return self._cached_success_response

        result = self._run_live_summary()
        if result.is_success:
            self._cached_success_response = result.response
        return result.response


gee_biomass_service = GeeBiomassService()
