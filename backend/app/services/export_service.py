"""
Module 15 export service.

Builds a shared, versioned export document for JSON, CSV and PDF output.
The document is normalized from CustomAoiAnalyzeResponse and never
recomputes scientific values.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import unicodedata
import textwrap
from datetime import datetime, timezone
from typing import Any

from app.models.analysis import (
    CustomAoiAnalyzeResponse,
    ExportAoiBounds,
    ExportDateRangeInfo,
    ExportDocument,
    ExportMetric,
    ExportScientificResults,
)

REPORT_SCHEMA_VERSION = "module15_v1"
MAX_SAFE_FILENAME_LENGTH = 96
ALLOWED_EXPORT_FORMATS = ("json", "csv", "pdf")
CONTENT_TYPES: dict[str, str] = {
    "json": "application/json; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "pdf": "application/pdf",
}

CSV_COLUMNS = [
    "report_schema_version",
    "generated_at_utc",
    "processing_mode",
    "processing_version",
    "study_area_id",
    "study_area_name",
    "start_date",
    "end_date",
    "date_convention",
    "coordinate_order",
    "aoi_type",
    "aoi_geometry_json",
    "aoi_bounds_min_lon",
    "aoi_bounds_min_lat",
    "aoi_bounds_max_lon",
    "aoi_bounds_max_lat",
    "vertex_count",
    "datasets_json",
    "no_data",
    "warnings_json",
    "assumptions_json",
    "methodology_json",
    "valid_gedi_samples_value",
    "valid_gedi_samples_unit",
    "mean_rh98_m_value",
    "mean_rh98_m_unit",
    "min_rh98_m_value",
    "min_rh98_m_unit",
    "max_rh98_m_value",
    "max_rh98_m_unit",
    "mean_agb_mg_ha_value",
    "mean_agb_mg_ha_unit",
    "mean_bgb_mg_ha_value",
    "mean_bgb_mg_ha_unit",
    "mean_carbon_mg_c_ha_value",
    "mean_carbon_mg_c_ha_unit",
    "min_carbon_mg_c_ha_value",
    "min_carbon_mg_c_ha_unit",
    "max_carbon_mg_c_ha_value",
    "max_carbon_mg_c_ha_unit",
    "mangrove_area_ha_value",
    "mangrove_area_ha_unit",
    "gedi_sampled_coverage_percent_value",
    "gedi_sampled_coverage_percent_unit",
    "direct_sampled_carbon_mg_c_value",
    "direct_sampled_carbon_mg_c_unit",
    "extrapolated_total_carbon_mg_c_value",
    "extrapolated_total_carbon_mg_c_unit",
]

METRIC_UNITS: dict[str, str] = {
    "valid_gedi_samples": "count",
    "mean_rh98_m": "m",
    "min_rh98_m": "m",
    "max_rh98_m": "m",
    "mean_agb_mg_ha": "Mg/ha",
    "mean_bgb_mg_ha": "Mg/ha",
    "mean_carbon_mg_c_ha": "Mg C/ha",
    "min_carbon_mg_c_ha": "Mg C/ha",
    "max_carbon_mg_c_ha": "Mg C/ha",
    "mangrove_area_ha": "ha",
    "gedi_sampled_coverage_percent": "%",
    "direct_sampled_carbon_mg_c": "Mg C",
    "extrapolated_total_carbon_mg_c": "Mg C",
}

METRIC_LABELS = {
    "valid_gedi_samples": "Valid GEDI raster sample count",
    "mean_rh98_m": "Mean RH98 canopy height",
    "min_rh98_m": "Min RH98 canopy height",
    "max_rh98_m": "Max RH98 canopy height",
    "mean_agb_mg_ha": "Mean AGB",
    "mean_bgb_mg_ha": "Mean BGB",
    "mean_carbon_mg_c_ha": "Mean carbon density",
    "min_carbon_mg_c_ha": "Min carbon density",
    "max_carbon_mg_c_ha": "Max carbon density",
    "mangrove_area_ha": "Mapped mangrove area",
    "gedi_sampled_coverage_percent": "GEDI coverage percentage",
    "direct_sampled_carbon_mg_c": "Direct sampled carbon stock",
    "extrapolated_total_carbon_mg_c": "Extrapolated ecosystem carbon stock",
}

SAFE_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Export document contains non-finite numeric value.")
        return format(value, ".15g")
    return str(value)


def _safe_csv_text(value: Any) -> str:
    text = _safe_str(value)
    if not text:
        return text
    if text.startswith(SAFE_CSV_FORMULA_PREFIXES) or text.lstrip().startswith(SAFE_CSV_FORMULA_PREFIXES):
        return "'" + text
    return text


def _json_text(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sanitize_filename_part(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = re.sub(r"_{2,}", "_", text).strip("._-")
    return text


def _safe_filename_base(value: str, fallback: str) -> str:
    text = _sanitize_filename_part(value)
    if not text:
        return fallback
    return text[:MAX_SAFE_FILENAME_LENGTH]


def build_filename(document: ExportDocument, ext: str) -> str:
    base = "_".join(
        [
            "mangrove_carbon",
            _safe_filename_base(document.study_area.id, "study_area"),
            document.date_range.start_date.strftime("%Y%m%d"),
            document.date_range.end_date.strftime("%Y%m%d"),
        ]
    )
    base = _sanitize_filename_part(base)
    if not base:
        base = "mangrove_carbon_export"
    base = base[:MAX_SAFE_FILENAME_LENGTH]
    return f"{base}.{ext}"


def _geometry_lons_lats(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError("AOI geometry must contain coordinates.")

    points: list[tuple[float, float]] = []
    for ring in coordinates:
        if not isinstance(ring, list) or len(ring) < 4:
            raise ValueError("AOI geometry rings must contain closed coordinate arrays.")
        for point in ring:
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                raise ValueError("AOI geometry must contain [lon, lat] coordinate pairs.")
            lon, lat = point[0], point[1]
            if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                raise ValueError("AOI geometry coordinates must be numeric.")
            if not math.isfinite(lon) or not math.isfinite(lat):
                raise ValueError("AOI geometry coordinates must be finite.")
            points.append((float(lon), float(lat)))
    return points


def _geometry_bounds(geometry: dict[str, Any]) -> ExportAoiBounds:
    points = _geometry_lons_lats(geometry)
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    return ExportAoiBounds(
        min_lon=min(lons),
        min_lat=min(lats),
        max_lon=max(lons),
        max_lat=max(lats),
    )


def _geometry_vertex_count(geometry: dict[str, Any]) -> int:
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list):
        raise ValueError("AOI geometry must contain coordinates.")
    total = 0
    for ring in coordinates:
        if not isinstance(ring, list) or len(ring) < 4:
            raise ValueError("AOI geometry rings must contain closed coordinate arrays.")
        total += max(0, len(ring) - 1)
    return total


def _metric(value: float | int | None, unit: str) -> ExportMetric:
    if value is None:
        return ExportMetric(value=None, unit=unit)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Export document contains non-finite numeric value.")
    return ExportMetric(value=value, unit=unit)


def _build_results(result: Any) -> ExportScientificResults | None:
    if result is None:
        return None
    return ExportScientificResults(
        valid_gedi_samples=_metric(result.valid_gedi_samples, METRIC_UNITS["valid_gedi_samples"]),
        mean_rh98_m=_metric(result.mean_rh98_m, METRIC_UNITS["mean_rh98_m"]),
        min_rh98_m=_metric(result.min_rh98_m, METRIC_UNITS["min_rh98_m"]),
        max_rh98_m=_metric(result.max_rh98_m, METRIC_UNITS["max_rh98_m"]),
        mean_agb_mg_ha=_metric(result.mean_agb_mg_ha, METRIC_UNITS["mean_agb_mg_ha"]),
        mean_bgb_mg_ha=_metric(result.mean_bgb_mg_ha, METRIC_UNITS["mean_bgb_mg_ha"]),
        mean_carbon_mg_c_ha=_metric(result.mean_carbon_mg_c_ha, METRIC_UNITS["mean_carbon_mg_c_ha"]),
        min_carbon_mg_c_ha=_metric(result.min_carbon_mg_c_ha, METRIC_UNITS["min_carbon_mg_c_ha"]),
        max_carbon_mg_c_ha=_metric(result.max_carbon_mg_c_ha, METRIC_UNITS["max_carbon_mg_c_ha"]),
        mangrove_area_ha=_metric(result.mangrove_area_ha, METRIC_UNITS["mangrove_area_ha"]),
        gedi_sampled_coverage_percent=_metric(
            result.gedi_sampled_coverage_percent, METRIC_UNITS["gedi_sampled_coverage_percent"]
        ),
        direct_sampled_carbon_mg_c=_metric(result.direct_sampled_carbon_mg_c, METRIC_UNITS["direct_sampled_carbon_mg_c"]),
        extrapolated_total_carbon_mg_c=_metric(
            result.extrapolated_total_carbon_mg_c, METRIC_UNITS["extrapolated_total_carbon_mg_c"]
        ),
    )


def build_export_document(
    result: CustomAoiAnalyzeResponse,
    *,
    processing_version: str,
    generated_at_utc: str | None = None,
) -> ExportDocument:
    if not result.aoi_geometry:
        raise ValueError("Export requires aoi_geometry.")
    geometry = result.aoi_geometry
    bounds = _geometry_bounds(geometry)
    vertex_count = _geometry_vertex_count(geometry)
    warnings = [result.warning] if result.warning else []
    assumptions = list(result.assumptions or [])
    no_data = result.results is None
    return ExportDocument(
        generated_at_utc=generated_at_utc or _now_utc(),
        processing_mode=result.mode,
        processing_version=processing_version,
        study_area=result.study_area,
        date_range=ExportDateRangeInfo(
            start_date=result.date_range.start_date,
            end_date=result.date_range.end_date,
        ),
        aoi_geometry=geometry,
        aoi_bounds=bounds,
        vertex_count=vertex_count,
        datasets=list(result.datasets),
        results=_build_results(result.results),
        methodology=result.methodology,
        assumptions=assumptions,
        warnings=warnings,
        no_data=no_data,
    )


def generate_json(document: ExportDocument) -> bytes:
    payload = document.model_dump(mode="json")
    return json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8")


def _serialize_list(value: list[Any]) -> str:
    return _json_text(value)


def _csv_result_values(document: ExportDocument) -> dict[str, str]:
    results = document.results
    values: dict[str, str] = {}
    for key in METRIC_UNITS:
        metric = getattr(results, key) if results else None
        values[f"{key}_value"] = _safe_csv_text(metric.value if metric else "")
        values[f"{key}_unit"] = _safe_csv_text(metric.unit if metric else METRIC_UNITS[key])
    return values


def build_csv_row(document: ExportDocument) -> list[str]:
    data: dict[str, Any] = {
        "report_schema_version": document.report_schema_version,
        "generated_at_utc": document.generated_at_utc,
        "processing_mode": document.processing_mode,
        "processing_version": document.processing_version,
        "study_area_id": document.study_area.id,
        "study_area_name": document.study_area.name,
        "start_date": document.date_range.start_date.isoformat(),
        "end_date": document.date_range.end_date.isoformat(),
        "date_convention": document.date_range.convention,
        "coordinate_order": document.coordinate_order,
        "aoi_type": document.aoi_geometry.get("type", ""),
        "aoi_geometry_json": _json_text(document.aoi_geometry) if document.aoi_geometry else "",
        "aoi_bounds_min_lon": document.aoi_bounds.min_lon,
        "aoi_bounds_min_lat": document.aoi_bounds.min_lat,
        "aoi_bounds_max_lon": document.aoi_bounds.max_lon,
        "aoi_bounds_max_lat": document.aoi_bounds.max_lat,
        "vertex_count": document.vertex_count,
        "datasets_json": _serialize_list(document.datasets),
        "no_data": document.no_data,
        "warnings_json": _serialize_list(document.warnings),
        "assumptions_json": _serialize_list(document.assumptions),
        "methodology_json": _json_text(document.methodology.model_dump(mode="json")) if document.methodology else "",
    }
    data.update(_csv_result_values(document))

    row: list[str] = []
    for column in CSV_COLUMNS:
        value = data.get(column, "")
        row.append(_safe_csv_text(value))
    return row


def generate_csv(document: ExportDocument) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    writer.writerow(build_csv_row(document))
    return buf.getvalue().encode("utf-8")


def _pdf_text(value: Any) -> str:
    text = _safe_str(value)
    replacements = {
        "×": "x",
        "–": "-",
        "—": "-",
        "•": "-",
        "\u2022": "-",
        "\u2212": "-",
    }
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _pdf_wrapped_text(value: Any, width: int = 76) -> str:
    text = _pdf_text(value)
    if not text:
        return ""
    lines = text.splitlines() or [text]
    wrapped_lines: list[str] = []
    for line in lines:
        if not line:
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(
            textwrap.wrap(
                line,
                width=width,
                break_long_words=True,
                break_on_hyphens=False,
            )
            or [""]
        )
    return "\n".join(wrapped_lines)


def _pdf_value(value: Any) -> str:
    if value is None:
        return "No data"
    return _pdf_text(value)


def _write_section_title(pdf: Any, title: str) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _pdf_text(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _write_kv_lines(pdf: Any, rows: list[tuple[str, Any]]) -> None:
    usable_width = pdf.w - pdf.l_margin - pdf.r_margin
    for label, value in rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(usable_width, 6, _pdf_text(f"{label}:"))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(usable_width, 6, _pdf_wrapped_text(value))
        pdf.ln(1)


def _write_table(pdf: Any, headers: list[str], rows: list[list[str]], widths: list[float], *, title: str) -> None:
    _write_section_title(pdf, title)
    pdf.set_font("Helvetica", "B", 9)
    header_height = 7
    row_height = 7

    def draw_header() -> None:
        for index, header in enumerate(headers):
            pdf.cell(widths[index], header_height, _pdf_text(header), border=1)
        pdf.ln(header_height)

    draw_header()
    pdf.set_font("Helvetica", "", 9)
    for row in rows:
        if pdf.get_y() + row_height > pdf.page_break_trigger:
            pdf.add_page()
            draw_header()
        for index, cell in enumerate(row):
            pdf.cell(widths[index], row_height, _pdf_text(cell), border=1)
        pdf.ln(row_height)


class _ExportPdf:
    """Small PDF renderer for Module 15 exports."""

    def __init__(self) -> None:
        from fpdf import FPDF

        class _Pdf(FPDF):
            def footer(self) -> None:  # type: ignore[override]
                self.set_y(-14)
                self.set_font("Helvetica", "I", 8)
                self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="C")

        self.pdf = _Pdf()
        self.pdf.alias_nb_pages()
        self.pdf.set_compression(False)
        self.pdf.set_margins(16, 16, 16)
        self.pdf.set_auto_page_break(auto=True, margin=16)
        self.pdf.add_page()

    def output(self) -> bytes:
        return bytes(self.pdf.output())


def generate_pdf(document: ExportDocument) -> bytes:
    pdf = _ExportPdf().pdf

    # Title and executive summary
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _pdf_text("Mangrove Carbon Analysis Export"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    summary_text = (
        "No scientific result was available for this AOI." if document.no_data else
        "Authoritative backend analysis results exported without recalculation."
    )
    pdf.multi_cell(0, 6, _pdf_text(summary_text))
    pdf.ln(2)

    _write_section_title(pdf, "Study area and analysis metadata")
    _write_kv_lines(
        pdf,
        [
            ("Report schema version", document.report_schema_version),
            ("Generated at UTC", document.generated_at_utc),
            ("Processing mode", document.processing_mode),
            ("Processing version", document.processing_version),
            ("Study area", f"{document.study_area.name} ({document.study_area.id})"),
            (
                "Date range",
                f"{document.date_range.start_date.isoformat()} to {document.date_range.end_date.isoformat()} (end exclusive)",
            ),
            ("Coordinate order", document.coordinate_order.replace("_", " ")),
            ("No data", "yes" if document.no_data else "no"),
        ],
    )

    _write_section_title(pdf, "AOI geometry")
    _write_kv_lines(
        pdf,
        [
            ("AOI type", document.aoi_geometry.get("type", "")),
            (
                "AOI bounds",
                f"[{document.aoi_bounds.min_lon:.6f}, {document.aoi_bounds.min_lat:.6f}] to "
                f"[{document.aoi_bounds.max_lon:.6f}, {document.aoi_bounds.max_lat:.6f}]",
            ),
            ("Vertex count", str(document.vertex_count)),
        ],
    )

    _write_kv_lines(
        pdf,
        [
            ("Datasets", ", ".join(_pdf_text(item) for item in document.datasets) if document.datasets else "None"),
        ],
    )

    if document.results:
        rows: list[list[str]] = []
        for key in METRIC_UNITS:
            metric = getattr(document.results, key)
            rows.append(
                [
                    METRIC_LABELS[key],
                    _pdf_value(metric.value),
                    metric.unit,
                ]
            )
        _write_table(
            pdf,
            ["Metric", "Value", "Unit"],
            rows,
            [90, 44, 24],
            title="Scientific results",
        )
    else:
        _write_section_title(pdf, "Scientific results")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _pdf_text("No scientific result was available for this AOI and date range."))

    _write_section_title(pdf, "Processing details")
    pdf.set_font("Helvetica", "", 10)
    if document.methodology:
        usable_width = pdf.w - pdf.l_margin - pdf.r_margin
        for key, value in document.methodology.model_dump(mode="json").items():
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(usable_width, 6, _pdf_wrapped_text(f"{key}: {value}"))
    else:
        usable_width = pdf.w - pdf.l_margin - pdf.r_margin
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(usable_width, 6, _pdf_wrapped_text("Methodology: not available for no-data export."))

    _write_section_title(pdf, "Assumptions and warnings")
    assumptions = document.assumptions or ["None"]
    warnings = document.warnings or ["None"]
    _write_kv_lines(
        pdf,
        [
            ("Assumptions", "; ".join(_pdf_text(item) for item in assumptions)),
            ("Warnings", "; ".join(_pdf_text(item) for item in warnings)),
        ],
    )

    _write_section_title(pdf, "Reproducibility metadata")
    _write_kv_lines(
        pdf,
        [
            ("Export format", "PDF"),
            ("Schema version", document.report_schema_version),
            ("Processing version", document.processing_version),
            ("Generated at UTC", document.generated_at_utc),
        ],
    )

    return bytes(pdf.output())
