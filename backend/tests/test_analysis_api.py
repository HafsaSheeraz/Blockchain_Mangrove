import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _valid_payload():
    return {
        "study_area": "indus_delta",
        "start_date": "2019-01-01",
        "end_date": "2021-12-31",
    }


@pytest.mark.asyncio
async def test_analysis_success_response():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analyze", json=_valid_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "demonstration"
    assert body["study_area"] == {"id": "indus_delta", "name": "Indus Delta, Pakistan"}
    assert body["date_range"] == {"start_date": "2019-01-01", "end_date": "2021-12-31"}
    assert body["datasets"] == ["GEDI L2A RH98", "GMW 2020", "Sentinel-2"]
    assert body["warning"] == "Demonstration results only. No live Earth Engine processing was performed."


@pytest.mark.asyncio
async def test_analysis_response_structure_and_numeric_values():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analyze", json=_valid_payload())

    body = response.json()
    results = body["results"]
    assert results["valid_gedi_samples"] == 1130
    assert results["mean_rh98_m"] == 3.09
    assert results["min_rh98_m"] == 2.39
    assert results["max_rh98_m"] == 5.76
    assert results["mean_agb_mg_ha"] == 30.91
    assert results["mean_bgb_mg_ha"] == 15.15
    assert results["mean_carbon_mg_c_ha"] == 23.03
    assert results["min_carbon_mg_c_ha"] == 17.81
    assert results["max_carbon_mg_c_ha"] == 42.91
    assert results["mangrove_area_ha"] == 90769.33
    assert results["gedi_sampled_coverage_percent"] == 0.08
    assert results["direct_sampled_carbon_mg_c"] == 1480.37
    assert results["extrapolated_total_carbon_mg_c"] == 2090417.67
    assert body["methodology"] == {
        "agb_formula": "AGB = 10 × RH98",
        "bgb_formula": "BGB = 0.49 × AGB",
        "tab_formula": "TAB = AGB + BGB",
        "carbon_formula": "Carbon = 0.5 × TAB",
    }


@pytest.mark.asyncio
async def test_analysis_rejects_unsupported_study_area():
    payload = _valid_payload()
    payload["study_area"] = "abu_dhabi"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analyze", json=payload)

    assert response.status_code == 400
    assert "Unsupported study_area 'abu_dhabi'" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analysis_rejects_invalid_date_format():
    payload = _valid_payload()
    payload["start_date"] = "2019-13-40"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analyze", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("start_date" in str(item.get("loc", [])) for item in detail)


@pytest.mark.asyncio
async def test_analysis_rejects_equal_dates():
    payload = _valid_payload()
    payload["end_date"] = payload["start_date"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analyze", json=payload)

    assert response.status_code == 422
    assert "end_date must be after start_date" in str(response.json()["detail"])


@pytest.mark.asyncio
async def test_analysis_rejects_end_date_before_start_date():
    payload = _valid_payload()
    payload["end_date"] = "2018-12-31"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analyze", json=payload)

    assert response.status_code == 422
    assert "end_date must be after start_date" in str(response.json()["detail"])


@pytest.mark.asyncio
async def test_analysis_requires_required_fields():
    payload = {"study_area": "indus_delta"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analyze", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(item.get("loc") == ["body", "start_date"] for item in detail)
    assert any(item.get("loc") == ["body", "end_date"] for item in detail)


@pytest.mark.asyncio
async def test_analysis_explicitly_in_demonstration_mode():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/analyze", json=_valid_payload())

    body = response.json()
    assert body["mode"] == "demonstration"
    assert body["warning"].startswith("Demonstration results only")
