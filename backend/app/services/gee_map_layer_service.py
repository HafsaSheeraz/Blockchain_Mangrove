from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.core.config import settings
from app.core.gee_datasets import GEDI_RH98_MAX_PIXELS, GMW_AREA_SCALE_M, REGION_CATALOG
from app.services import gee_service as gee_service_module
from app.services.gee_mask_service import gee_mask_service

ee = gee_service_module.ee
logger = logging.getLogger(__name__)


class GeeMapLayerService:
    def _validate_tile_url_template(self, tile_url_template: str) -> str:
        parsed = urlparse(tile_url_template)
        if parsed.scheme.lower() != "https":
            raise RuntimeError("Earth Engine returned a non-HTTPS map tile URL.")
        if parsed.hostname not in settings.map_tile_allowed_hosts:
            raise RuntimeError(
                f"Earth Engine returned map tiles from an unapproved host: '{parsed.hostname}'."
            )
        return tile_url_template

    def _safe_error_message(self, error: Exception) -> str:
        text = str(error).lower()
        if "not connected" in text or "authentication" in text:
            return "Google Earth Engine is not connected."
        if "quota" in text or "restricted" in text:
            return "Earth Engine quota or restricted-mode limitation was encountered."
        if "timeout" in text or "timed out" in text:
            return "Earth Engine request timed out."
        return "Earth Engine map-layer operation failed."

    def _resolve_region_config(self, study_area_id: str):
        region_config = REGION_CATALOG.get(study_area_id)
        if region_config is None:
            raise ValueError(
                f"Unsupported study_area '{study_area_id}'. Supported values: 'indus_delta', 'abu_dhabi', 'custom'."
            )
        return region_config

    def _require_connection(self) -> None:
        connection = gee_service_module.gee_service.get_connection_context()
        if not connection.enabled:
            raise RuntimeError("Google Earth Engine is disabled by configuration.")
        if not connection.connected:
            raise RuntimeError(connection.message or "Google Earth Engine is not connected.")

    def get_gmw_layer_descriptor(self, study_area_id: str) -> dict:
        self._require_connection()
        region_config = self._resolve_region_config(study_area_id)

        try:
            gmw_mask = gee_mask_service.build_binary_mask(
                region_config.gmw_asset_id,
                region_config.gmw_mask_band,
                region_config.gmw_asset_type,
            )
            map_id_response = gmw_mask.selfMask().visualize(min=0, max=1, palette=["2e8b57"]).getMapId()
            tile_fetcher = map_id_response.get("tile_fetcher")
            tile_url_template = getattr(tile_fetcher, "url_format", None)
            if not tile_url_template:
                raise RuntimeError("Earth Engine map descriptor did not provide a tile URL.")
            tile_url_template = self._validate_tile_url_template(tile_url_template)
        except Exception as error:
            logger.exception("Failed to generate GMW overlay tile descriptor")
            raise RuntimeError(self._safe_error_message(error)) from error

        return {
            "study_area": study_area_id,
            "gmw_asset_id": region_config.gmw_asset_id,
            "tile_url_template": tile_url_template,
            "default_visible": True,
            "default_opacity": 0.5,
            "palette": ["2e8b57"],
            "label": "Mangrove Area (Global Mangrove Watch)",
        }

    def check_polygon_mangrove_coverage(self, study_area_id: str, aoi_geometry: dict) -> dict:
        self._require_connection()
        region_config = self._resolve_region_config(study_area_id)

        try:
            geometry = ee.Geometry(aoi_geometry)
            gmw_mask = gee_mask_service.build_binary_mask(
                region_config.gmw_asset_id,
                region_config.gmw_mask_band,
                region_config.gmw_asset_type,
            )
            area_result = (
                ee.Image.pixelArea()
                .divide(10000)
                .updateMask(gmw_mask)
                .reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=geometry,
                    scale=GMW_AREA_SCALE_M,
                    maxPixels=GEDI_RH98_MAX_PIXELS,
                    bestEffort=False,
                )
                .getInfo()
            )
            area_result = area_result or {}
            mapped_area_ha_raw = area_result.get("area")
            mapped_area_ha = float(mapped_area_ha_raw) if mapped_area_ha_raw is not None else 0.0
            has_mangroves = mapped_area_ha > 0
        except Exception as error:
            logger.exception("Failed to check custom AOI mangrove coverage")
            raise RuntimeError(self._safe_error_message(error)) from error

        return {
            "study_area": study_area_id,
            "has_mangroves": has_mangroves,
            "mapped_mangrove_area_ha": mapped_area_ha if has_mangroves else 0.0,
            "message": None
            if has_mangroves
            else "No mapped mangroves were found inside this polygon. Please draw inside the highlighted green areas.",
        }


gee_map_layer_service = GeeMapLayerService()
