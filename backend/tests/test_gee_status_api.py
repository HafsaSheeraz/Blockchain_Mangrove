import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import gee_service as gee_service_module


def _reset_gee_singleton():
    gee_service_module.gee_service._initialized = False
    gee_service_module.gee_service._initialized_project_id = None


class _FakeNumber:
    def __init__(self, value):
        self.value = value

    def getInfo(self):
        return self.value


class _FakeEESuccess:
    def __init__(self):
        self.initialize_calls = 0
        self.credentials_calls = []

    def ServiceAccountCredentials(self, email, key_path):
        self.credentials_calls.append((email, key_path))
        return ("creds", email, key_path)

    def Initialize(self, credentials=None, project=None):
        self.initialize_calls += 1
        self.last_init = (credentials, project)

    def Number(self, value):
        return _FakeNumber(value)


class _FakeEEAuthFailure(_FakeEESuccess):
    def Initialize(self, credentials=None, project=None):
        raise RuntimeError("Authentication failed for service account.")


class _FakeGoogleAuthSuccess:
    def __init__(self, credentials="adc-creds", detected_project="detected-project"):
        self.credentials = credentials
        self.detected_project = detected_project
        self.calls = 0

    def default(self):
        self.calls += 1
        return self.credentials, self.detected_project


class _FakeGoogleAuthFailure:
    def __init__(self):
        self.calls = 0

    def default(self):
        self.calls += 1
        raise RuntimeError("ADC failed with secret-value")


@pytest.mark.asyncio
async def test_gee_status_when_disabled(monkeypatch):
    _reset_gee_singleton()
    monkeypatch.setenv("GEE_ENABLED", "false")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    assert response.status_code == 200
    assert response.json() == {"enabled": False, "connected": False, "status": "disabled"}


@pytest.mark.asyncio
async def test_gee_status_missing_project_id(monkeypatch):
    _reset_gee_singleton()
    monkeypatch.setenv("GEE_ENABLED", "true")
    monkeypatch.setenv("GEE_PROJECT_ID", "")
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_EMAIL", "svc@example.iam.gserviceaccount.com")
    monkeypatch.setenv("GEE_PRIVATE_KEY_FILE", "secrets/gee-service-account.json")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["connected"] is False
    assert body["status"] == "missing_configuration"
    assert "GEE_PROJECT_ID" in body["message"]


@pytest.mark.asyncio
async def test_gee_status_missing_service_account_email(monkeypatch):
    _reset_gee_singleton()
    monkeypatch.setenv("GEE_ENABLED", "true")
    monkeypatch.setenv("GEE_PROJECT_ID", "demo-project")
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_EMAIL", "")
    monkeypatch.setenv("GEE_PRIVATE_KEY_FILE", "secrets/gee-service-account.json")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    body = response.json()
    assert body["status"] == "missing_configuration"
    assert "GEE_SERVICE_ACCOUNT_EMAIL" in body["message"]


@pytest.mark.asyncio
async def test_gee_status_missing_key_file(monkeypatch):
    _reset_gee_singleton()
    monkeypatch.setenv("GEE_ENABLED", "true")
    monkeypatch.setenv("GEE_PROJECT_ID", "demo-project")
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_EMAIL", "svc@example.iam.gserviceaccount.com")
    monkeypatch.setenv("GEE_PRIVATE_KEY_FILE", "secrets/not-found.key")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    body = response.json()
    assert body["status"] == "key_file_missing"
    assert body["connected"] is False


@pytest.mark.asyncio
async def test_gee_status_successful_initialization(monkeypatch, tmp_path):
    _reset_gee_singleton()
    fake_ee = _FakeEESuccess()
    monkeypatch.setattr(gee_service_module, "ee", fake_ee)

    key_file = tmp_path / "gee-test.key"
    key_file.write_text("dummy", encoding="utf-8")

    monkeypatch.setenv("GEE_ENABLED", "true")
    monkeypatch.setenv("GEE_PROJECT_ID", "demo-project")
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_EMAIL", "svc@example.iam.gserviceaccount.com")
    monkeypatch.setenv("GEE_PRIVATE_KEY_FILE", str(key_file))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    body = response.json()
    assert body == {"enabled": True, "connected": True, "status": "connected", "project_id": "demo-project"}
    assert fake_ee.initialize_calls == 1
    assert fake_ee.credentials_calls == [("svc@example.iam.gserviceaccount.com", str(key_file))]


@pytest.mark.asyncio
async def test_gee_status_adc_initialization(monkeypatch):
    _reset_gee_singleton()
    fake_ee = _FakeEESuccess()
    fake_google_auth = _FakeGoogleAuthSuccess()
    monkeypatch.setattr(gee_service_module, "ee", fake_ee)
    monkeypatch.setattr(gee_service_module, "google_auth", fake_google_auth)

    monkeypatch.setenv("GEE_ENABLED", "true")
    monkeypatch.setenv("GEE_AUTH_MODE", "adc")
    monkeypatch.setenv("GEE_PROJECT_ID", "mangroves123")
    monkeypatch.delenv("GEE_SERVICE_ACCOUNT_EMAIL", raising=False)
    monkeypatch.delenv("GEE_PRIVATE_KEY_FILE", raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    body = response.json()
    assert body == {"enabled": True, "connected": True, "status": "connected", "project_id": "mangroves123"}
    assert fake_google_auth.calls == 1
    assert fake_ee.initialize_calls == 1
    assert fake_ee.last_init == ("adc-creds", "mangroves123")
    assert fake_ee.credentials_calls == []


@pytest.mark.asyncio
async def test_gee_status_adc_missing_project_id(monkeypatch):
    _reset_gee_singleton()
    fake_google_auth = _FakeGoogleAuthSuccess()
    monkeypatch.setattr(gee_service_module, "google_auth", fake_google_auth)

    monkeypatch.setenv("GEE_ENABLED", "true")
    monkeypatch.setenv("GEE_AUTH_MODE", "adc")
    monkeypatch.setenv("GEE_PROJECT_ID", "")
    monkeypatch.delenv("GEE_SERVICE_ACCOUNT_EMAIL", raising=False)
    monkeypatch.delenv("GEE_PRIVATE_KEY_FILE", raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    body = response.json()
    assert body["status"] == "missing_configuration"
    assert "GEE_PROJECT_ID" in body["message"]
    assert fake_google_auth.calls == 0


@pytest.mark.asyncio
async def test_gee_status_authentication_failure(monkeypatch, tmp_path):
    _reset_gee_singleton()
    fake_ee = _FakeEEAuthFailure()
    monkeypatch.setattr(gee_service_module, "ee", fake_ee)

    key_file = tmp_path / "gee-auth-fail.key"
    key_file.write_text("dummy", encoding="utf-8")

    monkeypatch.setenv("GEE_ENABLED", "true")
    monkeypatch.setenv("GEE_PROJECT_ID", "demo-project")
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_EMAIL", "svc@example.iam.gserviceaccount.com")
    monkeypatch.setenv("GEE_PRIVATE_KEY_FILE", str(key_file))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    body = response.json()
    assert body["enabled"] is True
    assert body["connected"] is False
    assert body["status"] == "authentication_failed"
    assert "authentication failed" in body["message"].lower()


@pytest.mark.asyncio
async def test_gee_status_adc_authentication_failure_is_sanitized(monkeypatch, caplog):
    _reset_gee_singleton()
    fake_ee = _FakeEESuccess()
    fake_google_auth = _FakeGoogleAuthFailure()
    monkeypatch.setattr(gee_service_module, "ee", fake_ee)
    monkeypatch.setattr(gee_service_module, "google_auth", fake_google_auth)

    monkeypatch.setenv("GEE_ENABLED", "true")
    monkeypatch.setenv("GEE_AUTH_MODE", "adc")
    monkeypatch.setenv("GEE_PROJECT_ID", "mangroves123")
    monkeypatch.delenv("GEE_SERVICE_ACCOUNT_EMAIL", raising=False)
    monkeypatch.delenv("GEE_PRIVATE_KEY_FILE", raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    body = response.json()
    assert body["enabled"] is True
    assert body["connected"] is False
    assert body["status"] == "authentication_failed"
    assert body["message"] == "Google Earth Engine authentication failed. Verify ADC configuration and runtime identity."
    assert "secret-value" not in str(body)
    assert "secret-value" not in caplog.text


@pytest.mark.asyncio
async def test_gee_status_does_not_expose_private_paths_or_secrets(monkeypatch, tmp_path):
    _reset_gee_singleton()
    fake_ee = _FakeEEAuthFailure()
    monkeypatch.setattr(gee_service_module, "ee", fake_ee)

    private_folder = tmp_path / "super-private-folder"
    private_folder.mkdir()
    key_file = private_folder / "my-secret.key"
    key_file.write_text("dummy", encoding="utf-8")

    monkeypatch.setenv("GEE_ENABLED", "true")
    monkeypatch.setenv("GEE_PROJECT_ID", "demo-project")
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_EMAIL", "svc@example.iam.gserviceaccount.com")
    monkeypatch.setenv("GEE_PRIVATE_KEY_FILE", str(key_file))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/gee/status")

    body_text = str(response.json())
    assert str(private_folder) not in body_text
    assert str(key_file) not in body_text
    assert "secrets/" not in body_text
    assert "my-secret.key" not in body_text


@pytest.mark.asyncio
async def test_existing_health_and_mock_analysis_still_work(monkeypatch):
    _reset_gee_singleton()
    monkeypatch.setenv("GEE_ENABLED", "true")
    monkeypatch.setenv("GEE_PROJECT_ID", "")
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_EMAIL", "")
    monkeypatch.setenv("GEE_PRIVATE_KEY_FILE", "secrets/missing.key")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/health")
        analysis = await client.post(
            "/api/analyze",
            json={
                "study_area": "indus_delta",
                "start_date": "2019-01-01",
                "end_date": "2021-12-31",
            },
        )

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert analysis.status_code == 200
    assert analysis.json()["mode"] == "demonstration"
