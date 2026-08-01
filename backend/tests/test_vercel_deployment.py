import json
import time
from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from api.index import app as vercel_app
from app.api.routes import gee as gee_routes
from app.core.request_timeout import run_with_request_timeout
from app.main import app as main_app


def test_vercel_entrypoint_reuses_main_app():
    assert vercel_app is main_app


def test_backend_vercel_config_rewrites_all_requests_to_fastapi_entrypoint():
    vercel_config_path = Path(__file__).resolve().parents[1] / "vercel.json"
    config = json.loads(vercel_config_path.read_text(encoding="utf-8"))

    assert config["functions"]["api/index.py"]["maxDuration"] == 300
    assert config["rewrites"] == [{"source": "/(.*)", "destination": "/api/index"}]


def test_run_with_request_timeout_returns_result():
    assert run_with_request_timeout("quick operation", lambda: "ok", timeout_seconds=1) == "ok"


def test_run_with_request_timeout_raises_504_for_slow_operation():
    with pytest.raises(HTTPException) as exc_info:
        run_with_request_timeout("slow operation", lambda: time.sleep(0.05), timeout_seconds=0.001)

    assert exc_info.value.status_code == 504
    assert "slow operation exceeded the configured request timeout" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_gee_status_route_returns_504_on_timeout(monkeypatch):
    monkeypatch.setattr(
        gee_routes,
        "run_with_request_timeout",
        lambda operation_name, func: (_ for _ in ()).throw(HTTPException(status_code=504, detail="timed out")),
    )

    async with AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    assert response.status_code == 504
    assert response.json()["detail"] == "timed out"
