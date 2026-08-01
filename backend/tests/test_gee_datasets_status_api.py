from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import gee_dataset_check_service as dataset_service_module
from app.services import gee_mask_service as mask_service_module
from app.services.gee_service import GeeConnectionContext, GeeSettings


class _FakeValue:
    def __init__(self, value=None, error: Exception | None = None):
        self._value = value
        self._error = error

    def getInfo(self):
        if self._error is not None:
            raise self._error
        return self._value


class _FakeImage:
    def __init__(self, bands: list[str] | None = None, bands_error: Exception | None = None):
        self._bands = bands if bands is not None else []
        self._bands_error = bands_error
        self.selected_bands: list[str] = []
        self.gt_called = False
        self.self_mask_called = False
        self.reduce_region_called = False
        self.sample_called = False
        self.mosaic_called = False

    def bandNames(self):
        return _FakeValue(self._bands, self._bands_error)

    def select(self, bands):
        self.selected_bands = list(bands)
        return self

    def gt(self, _value):
        self.gt_called = True
        return self

    def selfMask(self):
        self.self_mask_called = True
        return self

    # These are intentionally present to verify they are never called.
    def reduceRegion(self, *args, **kwargs):  # pragma: no cover
        self.reduce_region_called = True
        raise AssertionError("reduceRegion must not be called in metadata/mask checks.")

    def sample(self, *args, **kwargs):  # pragma: no cover
        self.sample_called = True
        raise AssertionError("sample must not be called in metadata/mask checks.")

    def mosaic(self, *args, **kwargs):  # pragma: no cover
        self.mosaic_called = True
        raise AssertionError("mosaic must not be called in metadata/mask checks.")


class _FakeCollection:
    def __init__(self, count: int, bands: list[str], size_error: Exception | None = None, bands_error: Exception | None = None):
        self._count = count
        self._bands = bands
        self._size_error = size_error
        self._bands_error = bands_error

    def filterBounds(self, _geometry):
        return self

    def filterDate(self, _start, _end):
        return self

    def size(self):
        return _FakeValue(self._count, self._size_error)

    def first(self):
        return _FakeImage(self._bands, self._bands_error)


class _FakeGeometry:
    @staticmethod
    def Rectangle(bounds):
        return {"type": "Rectangle", "bounds": bounds}


class _FakeData:
    def __init__(self, gmw_asset: dict | None = None, gmw_error: Exception | None = None):
        self._gmw_asset = gmw_asset if gmw_asset is not None else {"type": "IMAGE"}
        self._gmw_error = gmw_error
        self.last_asset_id = None

    def getAsset(self, asset_id):
        self.last_asset_id = asset_id
        if self._gmw_error is not None:
            raise self._gmw_error
        return self._gmw_asset


class _FakeEE:
    def __init__(
        self,
        collections: dict[str, _FakeCollection],
        gmw_asset: dict | None = None,
        gmw_error: Exception | None = None,
        gmw_image_bands: list[str] | None = None,
    ):
        self._collections = collections
        self.Geometry = _FakeGeometry
        self.data = _FakeData(gmw_asset=gmw_asset, gmw_error=gmw_error)
        self.gmw_image = _FakeImage(gmw_image_bands if gmw_image_bands is not None else ["mask"])

    def ImageCollection(self, dataset_id):
        if dataset_id not in self._collections:
            raise RuntimeError("Dataset inaccessible")
        return self._collections[dataset_id]

    def Image(self, image_input):
        if isinstance(image_input, str):
            return self.gmw_image
        return image_input


def _connection_context(*, enabled=True, connected=True, status="connected", message=None):
    return GeeConnectionContext(
        enabled=enabled,
        connected=connected,
        status=status,
        message=message,
        project_id="demo-gee-project" if connected else None,
        settings=GeeSettings(
            enabled=enabled,
            project_id="demo-gee-project",
            service_account_email="svc@example.iam.gserviceaccount.com",
            private_key_file="secrets/gee-service-account.json",
            backend_dir=Path("D:/MangroveCarbonApp/backend"),
        ),
    )


def _set_connected(monkeypatch):
    monkeypatch.setattr(
        dataset_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(),
    )


def _reset_dataset_cache():
    dataset_service_module.gee_dataset_check_service._cached_success_response = None


def _set_fake_ee(monkeypatch, fake_ee: _FakeEE):
    monkeypatch.setattr(dataset_service_module, "ee", fake_ee)
    monkeypatch.setattr(mask_service_module, "ee", fake_ee)


@pytest.mark.asyncio
async def test_datasets_status_successful_response_with_project_mask(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(5, ["rh98", "quality_flag", "degrade_flag", "x"]),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(8, ["B2", "B3", "B4", "B8", "B11"]),
        },
        gmw_asset={"type": "IMAGE"},
        gmw_image_bands=["mask_band"],
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["status"] == "connected"
    assert body["processing_performed"] is False
    assert body["datasets"]["gedi_l2a"]["image_count"] == 5
    assert body["datasets"]["gedi_l2a"]["required_bands_available"] is True
    assert body["datasets"]["sentinel2_l2a"]["required_bands_available"] is True
    assert body["datasets"]["gmw_2020"]["dataset_id"] == "projects/mangroves123/assets/GMW_2020_IndusDelta"
    assert body["datasets"]["gmw_2020"]["source"] == "project_asset"
    assert body["datasets"]["gmw_2020"]["accessible"] is True
    assert body["datasets"]["gmw_2020"]["asset_type"] == "IMAGE"
    assert body["datasets"]["gmw_2020"]["band_names"] == ["mask_band"]
    assert body["datasets"]["gmw_2020"]["usable_as_mask"] is True


@pytest.mark.asyncio
async def test_datasets_status_uses_project_owned_asset_id(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(1, ["rh98", "quality_flag", "degrade_flag"]),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(1, ["B2", "B3", "B4", "B8"]),
        },
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/gee/datasets/status")

    assert fake_ee.data.last_asset_id == "projects/mangroves123/assets/GMW_2020_IndusDelta"


@pytest.mark.asyncio
async def test_datasets_status_gmw_image_with_multiple_bands(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(3, ["rh98", "quality_flag", "degrade_flag"]),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(2, ["B2", "B3", "B4", "B8"]),
        },
        gmw_asset={"type": "IMAGE"},
        gmw_image_bands=["band_a", "band_b"],
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body = response.json()
    assert body["datasets"]["gmw_2020"]["band_names"] == ["band_a", "band_b"]
    assert body["datasets"]["gmw_2020"]["usable_as_mask"] is True


@pytest.mark.asyncio
async def test_datasets_status_gmw_empty_band_image(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(4, ["rh98", "quality_flag", "degrade_flag"]),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(7, ["B2", "B3", "B4", "B8"]),
        },
        gmw_asset={"type": "IMAGE"},
        gmw_image_bands=[],
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body = response.json()
    assert body["status"] == "connected_with_dataset_issues"
    assert body["datasets"]["gmw_2020"]["accessible"] is True
    assert body["datasets"]["gmw_2020"]["asset_type"] == "IMAGE"
    assert body["datasets"]["gmw_2020"]["band_names"] == []
    assert body["datasets"]["gmw_2020"]["usable_as_mask"] is False


@pytest.mark.asyncio
async def test_datasets_status_gmw_wrong_asset_type(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(4, ["rh98", "quality_flag", "degrade_flag"]),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(7, ["B2", "B3", "B4", "B8"]),
        },
        gmw_asset={"type": "IMAGE_COLLECTION"},
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body = response.json()
    assert body["datasets"]["gmw_2020"]["accessible"] is False
    assert body["datasets"]["gmw_2020"]["asset_type"] == "IMAGE_COLLECTION"
    assert body["datasets"]["gmw_2020"]["usable_as_mask"] is False


@pytest.mark.asyncio
async def test_datasets_status_gmw_inaccessible(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(4, ["rh98", "quality_flag", "degrade_flag"]),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(7, ["B2", "B3", "B4", "B8"]),
        },
        gmw_error=RuntimeError("Asset not found"),
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body = response.json()
    assert body["datasets"]["gmw_2020"]["accessible"] is False
    assert body["datasets"]["gmw_2020"]["usable_as_mask"] is False
    assert body["status"] == "connected_with_dataset_issues"


@pytest.mark.asyncio
async def test_datasets_status_gedi_collection_empty(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(0, []),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(2, ["B2", "B3", "B4", "B8"]),
        },
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body = response.json()
    assert body["status"] == "connected_with_dataset_issues"
    assert body["datasets"]["gedi_l2a"]["image_count"] == 0
    assert body["datasets"]["gedi_l2a"]["required_bands_available"] is False


@pytest.mark.asyncio
async def test_datasets_status_gedi_required_band_missing(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(4, ["rh98", "quality_flag"]),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(2, ["B2", "B3", "B4", "B8"]),
        },
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body = response.json()
    assert body["datasets"]["gedi_l2a"]["required_bands_available"] is False
    assert "degrade_flag" in body["datasets"]["gedi_l2a"]["message"]


@pytest.mark.asyncio
async def test_datasets_status_sentinel_band_missing(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(4, ["rh98", "quality_flag", "degrade_flag"]),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(7, ["B2", "B3", "B4"]),
        },
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body = response.json()
    assert body["datasets"]["sentinel2_l2a"]["required_bands_available"] is False
    assert "B8" in body["datasets"]["sentinel2_l2a"]["message"]


@pytest.mark.asyncio
async def test_datasets_status_when_gee_disabled(monkeypatch):
    _reset_dataset_cache()
    monkeypatch.setattr(
        dataset_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(enabled=False, connected=False, status="disabled"),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body = response.json()
    assert body["connected"] is False
    assert body["status"] == "disabled"


@pytest.mark.asyncio
async def test_datasets_status_when_authentication_failed(monkeypatch):
    _reset_dataset_cache()
    monkeypatch.setattr(
        dataset_service_module.gee_service_module.gee_service,
        "get_connection_context",
        lambda: _connection_context(
            enabled=True,
            connected=False,
            status="authentication_failed",
            message="Google Earth Engine authentication failed. Verify configuration and credentials.",
        ),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body = response.json()
    assert body["connected"] is False
    assert body["status"] == "authentication_failed"


@pytest.mark.asyncio
async def test_datasets_status_quota_or_restricted_failure(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(
                0,
                [],
                size_error=RuntimeError("Noncommercial quota restricted."),
            ),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(7, ["B2", "B3", "B4", "B8"]),
        },
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body = response.json()
    assert body["datasets"]["gedi_l2a"]["accessible"] is False
    assert "quota or restricted-mode" in body["datasets"]["gedi_l2a"]["message"].lower()


@pytest.mark.asyncio
async def test_datasets_status_does_not_expose_credentials_or_private_paths(monkeypatch):
    _reset_dataset_cache()
    _set_connected(monkeypatch)
    fake_ee = _FakeEE(
        collections={
            "LARSE/GEDI/GEDI02_A_002_MONTHLY": _FakeCollection(
                1,
                ["rh98", "quality_flag", "degrade_flag"],
                bands_error=RuntimeError("Failure at C:\\private\\secrets\\gee-service-account.json"),
            ),
            "COPERNICUS/S2_SR_HARMONIZED": _FakeCollection(7, ["B2", "B3", "B4", "B8"]),
        },
    )
    _set_fake_ee(monkeypatch, fake_ee)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/datasets/status")

    body_text = str(response.json())
    assert "gee-service-account.json" not in body_text
    assert "C:\\private" not in body_text
    assert "svc@example.iam.gserviceaccount.com" not in body_text


def test_binary_mask_helper_selects_validated_band_and_stays_metadata_safe(monkeypatch):
    fake_ee = _FakeEE(collections={})
    monkeypatch.setattr(mask_service_module, "ee", fake_ee)

    mask = dataset_service_module.gee_mask_service.build_binary_mask(
        "projects/mangroves123/assets/GMW_2020_IndusDelta",
        "mangrove_band",
    )

    assert mask is fake_ee.gmw_image
    assert fake_ee.gmw_image.selected_bands == ["mangrove_band"]
    assert fake_ee.gmw_image.gt_called is True
    assert fake_ee.gmw_image.self_mask_called is True
    assert fake_ee.gmw_image.reduce_region_called is False
    assert fake_ee.gmw_image.sample_called is False
    assert fake_ee.gmw_image.mosaic_called is False


@pytest.mark.asyncio
async def test_existing_health_gee_status_and_analysis_still_work(monkeypatch):
    _reset_dataset_cache()
    monkeypatch.setenv("GEE_ENABLED", "false")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/health")
        gee_status = await client.get("/api/gee/status")
        analysis = await client.post(
            "/api/analyze",
            json={
                "study_area": "indus_delta",
                "start_date": "2019-01-01",
                "end_date": "2021-12-31",
            },
        )

    assert health.status_code == 200
    assert gee_status.status_code == 200
    assert analysis.status_code == 200
    assert analysis.json()["mode"] == "demonstration"
