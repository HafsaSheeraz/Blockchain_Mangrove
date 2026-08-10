from __future__ import annotations

import io
import math
from dataclasses import dataclass

import httpx
from PIL import Image, ImageDraw

from app.models.analysis import ExportDocument
from app.services.gee_map_layer_service import gee_map_layer_service

TILE_SIZE = 256
OSM_TILE_URL_TEMPLATE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
MAP_WIDTH_PX = 1200
MAP_HEIGHT_PX = 700
MAX_ZOOM = 18
MIN_ZOOM = 1


@dataclass(frozen=True)
class _MapBounds:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


def _clamp_lat(lat: float) -> float:
    return max(-85.05112878, min(85.05112878, lat))


def _wrap_lon(lon: float) -> float:
    wrapped = ((lon + 180.0) % 360.0) - 180.0
    if wrapped == -180.0:
        return 180.0
    return wrapped


def _lonlat_to_world_px(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    lat = _clamp_lat(lat)
    lon = _wrap_lon(lon)
    scale = TILE_SIZE * (2**zoom)
    x = (lon + 180.0) / 360.0 * scale
    lat_rad = math.radians(lat)
    merc = math.log(math.tan(math.pi / 4.0 + lat_rad / 2.0))
    y = (1.0 - merc / math.pi) / 2.0 * scale
    return x, y


def _fit_zoom(bounds: _MapBounds, width_px: int, height_px: int) -> int:
    for zoom in range(MAX_ZOOM, MIN_ZOOM - 1, -1):
        x0, y1 = _lonlat_to_world_px(bounds.min_lon, bounds.min_lat, zoom)
        x1, y0 = _lonlat_to_world_px(bounds.max_lon, bounds.max_lat, zoom)
        span_x = abs(x1 - x0)
        span_y = abs(y1 - y0)
        if span_x <= width_px * 0.86 and span_y <= height_px * 0.78:
            return zoom
    return MIN_ZOOM


def _padded_bounds(document: ExportDocument) -> _MapBounds:
    min_lon = float(document.aoi_bounds.min_lon)
    min_lat = float(document.aoi_bounds.min_lat)
    max_lon = float(document.aoi_bounds.max_lon)
    max_lat = float(document.aoi_bounds.max_lat)
    lon_span = max(max_lon - min_lon, 1e-6)
    lat_span = max(max_lat - min_lat, 1e-6)
    lon_pad = lon_span * 0.22
    lat_pad = lat_span * 0.22
    return _MapBounds(
        min_lon=max(-180.0, min_lon - lon_pad),
        min_lat=max(-85.05112878, min_lat - lat_pad),
        max_lon=min(180.0, max_lon + lon_pad),
        max_lat=min(85.05112878, max_lat + lat_pad),
    )


def _fetch_png_tile(client: httpx.Client, url: str) -> Image.Image:
    response = client.get(url)
    response.raise_for_status()
    with Image.open(io.BytesIO(response.content)) as image:
        return image.convert("RGBA")


def _draw_north_marker(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    x = image.width - 34
    y = 18
    draw.polygon([(x, y + 20), (x + 8, y), (x + 16, y + 20)], fill=(0, 0, 0, 200))
    draw.text((x + 4, y + 22), "N", fill=(0, 0, 0, 230))


def render_study_area_map_png(document: ExportDocument) -> bytes:
    bounds = _padded_bounds(document)
    zoom = _fit_zoom(bounds, MAP_WIDTH_PX, MAP_HEIGHT_PX)
    x0, y1 = _lonlat_to_world_px(bounds.min_lon, bounds.min_lat, zoom)
    x1, y0 = _lonlat_to_world_px(bounds.max_lon, bounds.max_lat, zoom)

    left_world = min(x0, x1)
    right_world = max(x0, x1)
    top_world = min(y0, y1)
    bottom_world = max(y0, y1)

    min_tile_x = int(math.floor(left_world / TILE_SIZE))
    max_tile_x = int(math.floor((right_world - 1) / TILE_SIZE))
    min_tile_y = int(math.floor(top_world / TILE_SIZE))
    max_tile_y = int(math.floor((bottom_world - 1) / TILE_SIZE))

    tile_count_x = max_tile_x - min_tile_x + 1
    tile_count_y = max_tile_y - min_tile_y + 1

    if tile_count_x <= 0 or tile_count_y <= 0:
        raise RuntimeError("Map tile range could not be derived for the AOI.")

    canvas = Image.new("RGBA", (tile_count_x * TILE_SIZE, tile_count_y * TILE_SIZE), (255, 255, 255, 255))
    study_area_id = document.study_area.id if document.study_area.id in {"indus_delta", "abu_dhabi", "custom"} else "custom"
    gmw_tile_template = gee_map_layer_service.get_gmw_layer_descriptor(study_area_id)["tile_url_template"]

    zoom_world_tile_count = 2**zoom
    with httpx.Client(timeout=20.0) as client:
        for tile_y in range(min_tile_y, max_tile_y + 1):
            if tile_y < 0 or tile_y >= zoom_world_tile_count:
                continue
            for tile_x in range(min_tile_x, max_tile_x + 1):
                wrapped_tile_x = tile_x % zoom_world_tile_count
                px = (tile_x - min_tile_x) * TILE_SIZE
                py = (tile_y - min_tile_y) * TILE_SIZE

                base_url = OSM_TILE_URL_TEMPLATE.format(z=zoom, x=wrapped_tile_x, y=tile_y)
                base_tile = _fetch_png_tile(client, base_url)
                canvas.paste(base_tile, (px, py))

                gmw_url = gmw_tile_template.format(z=zoom, x=wrapped_tile_x, y=tile_y)
                gmw_tile = _fetch_png_tile(client, gmw_url)
                canvas.alpha_composite(gmw_tile, (px, py))

    crop_left = int(round(left_world - min_tile_x * TILE_SIZE))
    crop_top = int(round(top_world - min_tile_y * TILE_SIZE))
    crop_right = int(round(right_world - min_tile_x * TILE_SIZE))
    crop_bottom = int(round(bottom_world - min_tile_y * TILE_SIZE))

    cropped = canvas.crop((crop_left, crop_top, crop_right, crop_bottom))
    resample_method = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
    cropped = cropped.resize((MAP_WIDTH_PX, MAP_HEIGHT_PX), resample=resample_method)

    scale_x = MAP_WIDTH_PX / max(1.0, right_world - left_world)
    scale_y = MAP_HEIGHT_PX / max(1.0, bottom_world - top_world)

    def scaled_world_to_resized(px_world: float, py_world: float) -> tuple[float, float]:
        return ((px_world - left_world) * scale_x, (py_world - top_world) * scale_y)

    coordinates = document.aoi_geometry.get("coordinates")
    if isinstance(coordinates, list):
        draw = ImageDraw.Draw(cropped)
        for ring in coordinates:
            if not isinstance(ring, list) or len(ring) < 4:
                continue
            points: list[tuple[float, float]] = []
            for point in ring:
                if not isinstance(point, (list, tuple)) or len(point) < 2:
                    continue
                lon = float(point[0])
                lat = float(point[1])
                wx, wy = _lonlat_to_world_px(lon, lat, zoom)
                points.append(scaled_world_to_resized(wx, wy))
            if len(points) < 2:
                continue
            draw.line(points, fill=(255, 255, 255, 230), width=8, joint="curve")
            draw.line(points, fill=(198, 40, 40, 255), width=4, joint="curve")

    _draw_north_marker(cropped)

    output = io.BytesIO()
    cropped.save(output, format="PNG")
    return output.getvalue()
