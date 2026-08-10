import csv
import io
import json
import re
import base64
from datetime import date
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.analysis import (
    AnalysisResults,
    CustomAoiAnalyzeResponse,
    DateRangeInfo,
    MethodologyInfo,
    StudyAreaInfo,
)
from app.services.export_service import (
    ALLOWED_EXPORT_FORMATS,
    CSV_COLUMNS,
    build_export_document,
    build_filename,
    generate_csv,
    generate_json,
    generate_pdf,
)
from app.services.analysis_service import _get_gee_service


def _indus_aoi_geojson() -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [[66.5, 23.5], [68.5, 23.5], [68.5, 24.8], [66.5, 24.8], [66.5, 23.5]]
        ],
    }


def _make_success_result(
    *,
    study_area_id: str = "indus_delta",
    study_area_name: str = "Indus Delta, Pakistan",
    warning: str = "Custom AOI analysis complete.",
    assumptions: list[str] | None = None,
) -> CustomAoiAnalyzeResponse:
    return CustomAoiAnalyzeResponse(
        mode="live_earth_engine_custom_aoi",
        study_area=StudyAreaInfo(id=study_area_id, name=study_area_name),
        date_range=DateRangeInfo(start_date=date(2020, 1, 1), end_date=date(2020, 4, 1)),
        datasets=["GEDI L2A RH98", "GMW 2020"],
        results=AnalysisResults(
            valid_gedi_samples=1130,
            mean_rh98_m=3.0907,
            min_rh98_m=2.39,
            max_rh98_m=5.76,
            mean_agb_mg_ha=30.9070,
            mean_bgb_mg_ha=15.1444,
            mean_carbon_mg_c_ha=23.02570844643939,
            min_carbon_mg_c_ha=17.81,
            max_carbon_mg_c_ha=42.91,
            mangrove_area_ha=90769.33192367057,
            gedi_sampled_coverage_percent=0.07083104263093926,
            direct_sampled_carbon_mg_c=1480.3693760410526,
            extrapolated_total_carbon_mg_c=2090028.172752522,
        ),
        methodology=MethodologyInfo(
            agb_formula="AGB = 10 x RH98",
            bgb_formula="BGB = 0.49 x AGB",
            tab_formula="TAB = AGB + BGB",
            carbon_formula="Carbon = 0.5 x TAB",
        ),
        warning=warning,
        assumptions=assumptions
        if assumptions is not None
        else ["GEDI raster samples are spatially representative of the full mapped mangrove extent."],
        aoi_geometry=_indus_aoi_geojson(),
    )


def _make_no_data_result() -> CustomAoiAnalyzeResponse:
    return CustomAoiAnalyzeResponse(
        mode="live_earth_engine_custom_aoi",
        study_area=StudyAreaInfo(id="abu_dhabi", name="Abu Dhabi, United Arab Emirates"),
        date_range=DateRangeInfo(start_date=date(2020, 1, 1), end_date=date(2020, 4, 1)),
        datasets=["GEDI L2A RH98", "GMW 2020"],
        results=None,
        methodology=None,
        warning="AOI has no mapped mangrove area (no GMW mask coverage).",
        assumptions=None,
        aoi_geometry={
            "type": "Polygon",
            "coordinates": [
                [[51.5, 22.5], [54.5, 22.5], [54.5, 24.5], [51.5, 24.5], [51.5, 22.5]]
            ],
        },
    )


def _export_payload() -> dict:
    return {
        "study_area": "indus_delta",
        "aoi_geometry": _indus_aoi_geojson(),
        "start_date": "2020-01-01",
        "end_date": "2020-04-01",
    }


def _no_data_payload() -> dict:
    return {
        "study_area": "abu_dhabi",
        "aoi_geometry": {
            "type": "Polygon",
            "coordinates": [
                [[51.5, 22.5], [54.5, 22.5], [54.5, 24.5], [51.5, 24.5], [51.5, 22.5]]
            ],
        },
        "start_date": "2020-01-01",
        "end_date": "2020-04-01",
    }


def _patch_run_custom(return_value: CustomAoiAnalyzeResponse):
    return patch("app.api.routes.analysis.run_custom_aoi_analysis", return_value=return_value)


def _custom_success_result() -> CustomAoiAnalyzeResponse:
    return _make_success_result(study_area_id="custom", study_area_name="Custom AOI")


def _custom_success_payload() -> dict:
    return {
        "study_area": "custom",
        "aoi_geometry": _indus_aoi_geojson(),
        "start_date": "2020-01-01",
        "end_date": "2020-04-01",
    }


def _assert_no_secret_leakage(text: str) -> None:
    assert "tile_fetcher" not in text
    assert "token" not in text
    assert "mapid" not in text
    assert "C:\\" not in text


@pytest.mark.asyncio
@pytest.mark.parametrize("export_format", ["json", "csv", "pdf"])
async def test_no_data_exports_across_formats(export_format):
    result = _make_no_data_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/analyze/export/{export_format}", json=_no_data_payload())

    assert response.status_code == 200
    if export_format == "json":
        data = response.json()
        assert data["no_data"] is True
        assert data["results"] is None
    elif export_format == "csv":
        rows = list(csv.reader(io.StringIO(response.text)))
        row = dict(zip(rows[0], rows[1]))
        assert row["no_data"] == "true"
        assert row["valid_gedi_samples_value"] == ""
        assert row["direct_sampled_carbon_mg_c_value"] == ""
    else:
        pdf_text = response.content.decode("latin-1", errors="ignore")
        assert "No scientific result was available for this AOI and date range." in pdf_text
        assert "Abu Dhabi, United Arab Emirates" in pdf_text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("export_format", "content_type"),
    [
        ("json", "application/json"),
        ("csv", "text/csv"),
        ("pdf", "application/pdf"),
    ],
)
async def test_export_responses_expose_security_headers_and_safe_filenames(export_format, content_type):
    result = _make_success_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/analyze/export/{export_format}", json=_export_payload())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="mangrove_carbon_indus_delta_20200101_20200401.{export_format}"'
    )
    assert "\r" not in response.headers["content-disposition"]
    assert "\n" not in response.headers["content-disposition"]


@pytest.mark.asyncio
@pytest.mark.parametrize("export_format", ["json", "csv", "pdf"])
async def test_export_responses_do_not_leak_secrets_or_local_paths(export_format):
    result = _make_success_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/analyze/export/{export_format}", json=_export_payload())

    body = response.text if export_format != "pdf" else response.content.decode("latin-1", errors="ignore")
    _assert_no_secret_leakage(body)


@pytest.mark.asyncio
@pytest.mark.parametrize("export_format", ["json", "csv", "pdf"])
async def test_custom_aoi_export_succeeds_for_each_format(export_format):
    result = _custom_success_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/analyze/export/{export_format}", json=_custom_success_payload())

    assert response.status_code == 200
    if export_format == "json":
        data = response.json()
        assert data["study_area"]["id"] == "custom"
        assert data["no_data"] is False
    elif export_format == "csv":
        rows = list(csv.reader(io.StringIO(response.text)))
        row = dict(zip(rows[0], rows[1]))
        assert row["study_area_id"] == "custom"
        assert row["study_area_name"] == "Custom AOI"
        assert row["no_data"] == "false"
    else:
        pdf_text = response.content.decode("latin-1", errors="ignore")
        assert "Custom AOI" in pdf_text
        assert "Indus Delta, Pakistan" not in pdf_text


@pytest.mark.asyncio
@pytest.mark.parametrize("export_format", ["json", "csv", "pdf"])
async def test_export_rejects_invalid_geometry_for_each_format(export_format):
    payload = {
        "study_area": "custom",
        "aoi_geometry": {"type": "Polygon", "coordinates": [[[66.5, 23.5], [68.5, 23.5]]]},
        "start_date": "2020-01-01",
        "end_date": "2020-04-01",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/analyze/export/{export_format}", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
async def test_csv_export_protects_against_all_formula_prefixes(prefix):
    malicious = _make_success_result(
        study_area_id="custom",
        study_area_name=f"{prefix}Spreadsheet",
        warning=f"{prefix}Alert",
    )
    with _patch_run_custom(malicious):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/export/csv", json=_export_payload())

    rows = list(csv.reader(io.StringIO(response.text)))
    row = dict(zip(rows[0], rows[1]))
    assert row["study_area_name"].startswith("'")
    assert row["warnings_json"].startswith('["')


@pytest.mark.asyncio
async def test_csv_export_quotes_text_cells_and_preserves_commas():
    malicious = _make_success_result(
        study_area_id="custom",
        study_area_name='Indus, Delta "Special"',
        warning='Warning, with comma',
    )
    with _patch_run_custom(malicious):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/export/csv", json=_export_payload())

    rows = list(csv.reader(io.StringIO(response.text)))
    row = dict(zip(rows[0], rows[1]))
    assert row["study_area_name"] == 'Indus, Delta "Special"'
    assert row["warnings_json"] == '["Warning, with comma"]'


@pytest.mark.asyncio
async def test_pdf_export_contains_signature_metadata_and_page_numbers():
    result = _make_success_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/export/pdf", json=_export_payload())

    assert response.content[:4] == b"%PDF"
    assert b"/Count " in response.content
    assert b"Page 1/" in response.content
    assert b"Page 2/" in response.content
    pdf_text = response.content.decode("latin-1", errors="ignore")
    assert "Mangrove Carbon Analysis Export" in pdf_text
    assert "Report schema version:" in pdf_text
    assert "Processing version:" in pdf_text


@pytest.mark.asyncio
async def test_json_export_uses_normalized_document_and_security_headers():
    result = _make_success_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/export/json", json=_export_payload())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert "\r" not in response.headers["content-disposition"]
    assert "\n" not in response.headers["content-disposition"]

    data = response.json()
    assert data["report_schema_version"] == "module15_v1"
    assert data["processing_mode"] == "live_earth_engine_custom_aoi"
    assert data["processing_version"] == _get_gee_service().get_processing_version_fingerprint()
    assert data["coordinate_order"] == "longitude_latitude"
    assert data["date_range"]["convention"] == "end_exclusive"
    assert data["aoi_geometry"]["type"] == "Polygon"
    assert data["aoi_geometry"]["coordinates"][0][0] == [66.5, 23.5]
    assert data["aoi_bounds"] == {
        "min_lon": 66.5,
        "min_lat": 23.5,
        "max_lon": 68.5,
        "max_lat": 24.8,
    }
    assert data["vertex_count"] == 4
    assert data["datasets"] == ["GEDI L2A RH98", "GMW 2020"]
    assert data["no_data"] is False
    assert data["warnings"] == ["Custom AOI analysis complete."]
    assert data["assumptions"]
    assert data["results"]["mean_carbon_mg_c_ha"]["unit"] == "Mg C/ha"
    assert data["results"]["direct_sampled_carbon_mg_c"]["value"] == pytest.approx(1480.3693760410526)
    assert "tile_fetcher" not in response.text
    assert "token" not in response.text
    assert "mapid" not in response.text
    assert "23.02570844643939" in response.text


@pytest.mark.asyncio
async def test_json_export_no_data_preserves_null_results():
    result = _make_no_data_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/export/json", json=_no_data_payload())

    data = response.json()
    assert data["no_data"] is True
    assert data["results"] is None
    assert data["warnings"] == ["AOI has no mapped mangrove area (no GMW mask coverage)."]


@pytest.mark.asyncio
async def test_csv_export_has_fixed_header_and_one_data_row():
    result = _make_success_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/export/csv", json=_export_payload())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["x-content-type-options"] == "nosniff"

    rows = list(csv.reader(io.StringIO(response.text)))
    assert len(rows) == 2
    assert rows[0] == CSV_COLUMNS
    assert len(rows[1]) == len(CSV_COLUMNS)

    row = dict(zip(rows[0], rows[1]))
    assert row["report_schema_version"] == "module15_v1"
    assert row["processing_mode"] == "live_earth_engine_custom_aoi"
    assert row["date_convention"] == "end_exclusive"
    assert row["coordinate_order"] == "longitude_latitude"
    assert row["aoi_type"] == "Polygon"
    assert row["aoi_geometry_json"].startswith("{")
    assert row["datasets_json"] == '["GEDI L2A RH98","GMW 2020"]'
    assert row["no_data"] == "false"
    assert row["valid_gedi_samples_value"] == "1130"
    assert row["valid_gedi_samples_unit"] == "count"
    assert row["mean_carbon_mg_c_ha_value"].startswith("23.025708446")
    assert row["mean_carbon_mg_c_ha_unit"] == "Mg C/ha"
    assert row["direct_sampled_carbon_mg_c_value"].startswith("1480.369376041")


@pytest.mark.asyncio
async def test_csv_export_no_data_leaves_missing_numeric_fields_blank():
    result = _make_no_data_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/export/csv", json=_no_data_payload())

    rows = list(csv.reader(io.StringIO(response.text)))
    row = dict(zip(rows[0], rows[1]))
    assert row["no_data"] == "true"
    assert row["valid_gedi_samples_value"] == ""
    assert row["mean_carbon_mg_c_ha_value"] == ""
    assert row["direct_sampled_carbon_mg_c_value"] == ""
    assert row["warnings_json"] == '["AOI has no mapped mangrove area (no GMW mask coverage)."]'


@pytest.mark.asyncio
async def test_csv_export_protects_against_formula_injection():
    malicious = _make_success_result(
        study_area_id="custom",
        study_area_name='=HYPERLINK("http://evil")',
        warning="@SUM(1,1)",
    )
    with _patch_run_custom(malicious):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/export/csv", json=_export_payload())

    rows = list(csv.reader(io.StringIO(response.text)))
    row = dict(zip(rows[0], rows[1]))
    assert row["study_area_name"].startswith("'=")
    assert "@SUM(1,1)" in row["warnings_json"]


@pytest.mark.asyncio
async def test_pdf_export_contains_expected_text_and_page_number():
    result = _make_success_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/export/pdf", json=_export_payload())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content[:4] == b"%PDF"
    assert response.headers["content-disposition"].endswith('.pdf"')

    pdf_text = response.content.decode("latin-1", errors="ignore")
    assert "Mangrove Carbon Analysis Export" in pdf_text
    assert "Indus Delta, Pakistan" in pdf_text
    assert "2020-01-01" in pdf_text
    assert "2020-04-01" in pdf_text
    assert "Mapped mangrove area" in pdf_text
    assert "Extrapolated ecosystem carbon stock" in pdf_text
    assert "Page 1/" in pdf_text


@pytest.mark.asyncio
async def test_pdf_export_no_data_shows_no_scientific_results():
    result = _make_no_data_result()
    with _patch_run_custom(result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/analyze/export/pdf", json=_no_data_payload())

    pdf_text = response.content.decode("latin-1", errors="ignore")
    assert "No scientific result was available for this AOI and date range." in pdf_text
    assert "Abu Dhabi, United Arab Emirates" in pdf_text
    assert "Indus Delta, Pakistan" not in pdf_text


@pytest.mark.asyncio
async def test_unsupported_export_format_is_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analyze/export/xlsx", json=_export_payload())

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_missing_aoi_geometry_is_rejected():
    payload = {"study_area": "indus_delta", "start_date": "2020-01-01", "end_date": "2020-04-01"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analyze/export/json", json=payload)

    assert response.status_code == 400
    assert "aoi_geometry" in response.json()["detail"].lower()


def test_shared_export_document_contains_bounds_and_units():
    result = _make_success_result()
    document = build_export_document(result, processing_version="fingerprint-123")

    assert document.report_schema_version == "module15_v1"
    assert document.coordinate_order == "longitude_latitude"
    assert document.no_data is False
    assert document.results is not None
    assert document.results.mean_carbon_mg_c_ha.unit == "Mg C/ha"
    assert document.aoi_bounds.min_lon == 66.5
    assert document.vertex_count == 4


def test_build_filename_is_safe_and_bounded():
    result = build_export_document(_make_success_result(), processing_version="fingerprint-123")
    filename = build_filename(result, "json")
    assert filename == "mangrove_carbon_indus_delta_20200101_20200401.json"
    assert len(filename) <= 120
    assert "\r" not in filename
    assert "\n" not in filename
    assert "/" not in filename
    assert "\\" not in filename


def test_generate_json_rejects_non_finite_numbers():
    result = build_export_document(_make_success_result(), processing_version="fingerprint-123")
    result = result.model_copy(
        update={
            "results": result.results.model_copy(
                update={
                    "mean_carbon_mg_c_ha": result.results.mean_carbon_mg_c_ha.model_copy(
                        update={"value": float("inf")}
                    )
                }
            )
        }
    )
    with pytest.raises(ValueError):
        generate_json(result)


def test_generate_csv_header_order_matches_documentation():
    result = build_export_document(_make_success_result(), processing_version="fingerprint-123")
    csv_text = generate_csv(result).decode("utf-8")
    rows = list(csv.reader(io.StringIO(csv_text)))
    assert rows[0] == CSV_COLUMNS


def test_generate_pdf_contains_page_number_marker():
    result = build_export_document(_make_success_result(), processing_version="fingerprint-123")
    with patch(
        "app.services.export_service.render_study_area_map_png",
        return_value=base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5M6tcAAAAASUVORK5CYII="
        ),
    ):
        pdf_bytes = generate_pdf(result)
    assert pdf_bytes[:4] == b"%PDF"
    assert b"Page 1/" in pdf_bytes
    assert b"Figure 1." in pdf_bytes
    assert b"Selected Area of Interest" in pdf_bytes


def test_generate_pdf_includes_map_fallback_message_when_map_fails():
    result = build_export_document(_make_success_result(), processing_version="fingerprint-123")
    with patch(
        "app.services.export_service.render_study_area_map_png",
        side_effect=RuntimeError("map failure"),
    ):
        pdf_bytes = generate_pdf(result)
    assert b"Study area map could not be generated." in pdf_bytes
