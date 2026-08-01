from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from app.core import config as config_module

from app.models.gee import GeeStatusResponse

try:
    import ee
except ImportError:  # pragma: no cover
    ee = None

try:
    import google.auth as google_auth
except ImportError:  # pragma: no cover
    google_auth = None


@dataclass(frozen=True)
class GeeSettings:
    enabled: bool
    project_id: str
    service_account_email: str
    private_key_file: str
    backend_dir: Path
    service_account_json: str = ""
    auth_mode: str = "service_account_key"

    def resolved_key_path(self) -> Path:
        key_path = Path(self.private_key_file)
        if key_path.is_absolute():
            return key_path
        return self.backend_dir / key_path


@dataclass(frozen=True)
class GeeConnectionContext:
    enabled: bool
    connected: bool
    status: str
    message: str | None
    project_id: str | None
    settings: GeeSettings


def load_gee_settings() -> GeeSettings:
    app_settings = config_module.build_settings()

    return GeeSettings(
        enabled=app_settings.gee_enabled,
        auth_mode=app_settings.gee_auth_mode,
        project_id=app_settings.gee_project_id,
        service_account_email=app_settings.gee_service_account_email,
        private_key_file=app_settings.gee_private_key_file,
        backend_dir=app_settings.backend_dir,
        service_account_json=app_settings.gee_service_account_json,
    )


class GeeService:
    def __init__(self):
        self._initialized = False
        self._initialized_project_id: str | None = None
        self._initialized_auth_fingerprint: str | None = None

    def _settings_fingerprint(self, settings: GeeSettings) -> str:
        if settings.auth_mode == "adc":
            return f"adc:{settings.project_id}"
        if settings.auth_mode == "service_account_json":
            secret_hash = hashlib.sha256(settings.service_account_json.encode("utf-8")).hexdigest()
            return (
                f"service_account_json:{settings.project_id}:{settings.service_account_email}:"
                f"{secret_hash}"
            )
        return (
            f"service_account_key:{settings.project_id}:{settings.service_account_email}:"
            f"{settings.resolved_key_path()}"
        )

    def _validated_service_account_json(self, settings: GeeSettings) -> str:
        try:
            parsed = json.loads(settings.service_account_json)
        except Exception as error:
            raise ValueError("Configured GEE service-account JSON is invalid.") from error
        if not isinstance(parsed, dict):
            raise ValueError("Configured GEE service-account JSON is invalid.")
        return settings.service_account_json

    def _ensure_initialized(self, settings: GeeSettings) -> None:
        fingerprint = self._settings_fingerprint(settings)
        if (
            self._initialized
            and self._initialized_project_id == settings.project_id
            and self._initialized_auth_fingerprint == fingerprint
        ):
            return

        if settings.auth_mode == "adc":
            credentials, _detected_project = google_auth.default()
        elif settings.auth_mode == "service_account_json":
            credentials = ee.ServiceAccountCredentials(
                settings.service_account_email,
                key_data=self._validated_service_account_json(settings),
            )
        elif settings.auth_mode == "service_account_key":
            credentials = ee.ServiceAccountCredentials(
                settings.service_account_email,
                str(settings.resolved_key_path()),
            )
        else:
            raise ValueError("Unsupported GEE_AUTH_MODE.")

        ee.Initialize(credentials=credentials, project=settings.project_id)
        self._initialized = True
        self._initialized_project_id = settings.project_id
        self._initialized_auth_fingerprint = fingerprint

    def _reset_initialization(self) -> None:
        self._initialized = False
        self._initialized_project_id = None
        self._initialized_auth_fingerprint = None

    def _authentication_failure_message(self, settings: GeeSettings) -> str:
        if settings.auth_mode == "adc":
            return "Google Earth Engine authentication failed. Verify ADC configuration and runtime identity."
        if settings.auth_mode == "service_account_json":
            return "Google Earth Engine authentication failed. Verify service-account JSON configuration and credentials."
        return "Google Earth Engine authentication failed. Verify configuration and credentials."

    def get_connection_context(self) -> GeeConnectionContext:
        settings = load_gee_settings()

        if not settings.enabled:
            return GeeConnectionContext(
                enabled=False,
                connected=False,
                status="disabled",
                message=None,
                project_id=None,
                settings=settings,
            )

        if settings.auth_mode not in config_module.SUPPORTED_GEE_AUTH_MODES:
            return GeeConnectionContext(
                enabled=True,
                connected=False,
                status="invalid_configuration",
                message="GEE_AUTH_MODE must be one of: service_account_key, service_account_json, adc.",
                project_id=None,
                settings=settings,
            )

        missing_fields: list[str] = []
        if not settings.project_id:
            missing_fields.append("GEE_PROJECT_ID")

        if settings.auth_mode == "service_account_key":
            if not settings.service_account_email:
                missing_fields.append("GEE_SERVICE_ACCOUNT_EMAIL")
            if not settings.private_key_file:
                missing_fields.append("GEE_PRIVATE_KEY_FILE")
        elif settings.auth_mode == "service_account_json":
            if not settings.service_account_email:
                missing_fields.append("GEE_SERVICE_ACCOUNT_EMAIL")
            if not settings.service_account_json:
                missing_fields.append("GEE_SERVICE_ACCOUNT_JSON")

        if missing_fields:
            return GeeConnectionContext(
                enabled=True,
                connected=False,
                status="missing_configuration",
                message=f"Missing required GEE configuration: {', '.join(missing_fields)}.",
                project_id=None,
                settings=settings,
            )

        if settings.auth_mode == "service_account_key" and not settings.resolved_key_path().is_file():
            return GeeConnectionContext(
                enabled=True,
                connected=False,
                status="key_file_missing",
                message="Configured GEE private key file was not found.",
                project_id=None,
                settings=settings,
            )

        if settings.auth_mode == "service_account_json":
            try:
                self._validated_service_account_json(settings)
            except ValueError:
                return GeeConnectionContext(
                    enabled=True,
                    connected=False,
                    status="invalid_configuration",
                    message="Configured GEE service-account JSON is invalid.",
                    project_id=None,
                    settings=settings,
                )

        if settings.auth_mode == "adc" and google_auth is None:
            return GeeConnectionContext(
                enabled=True,
                connected=False,
                status="dependency_unavailable",
                message="google-auth dependency is not available in the backend environment.",
                project_id=None,
                settings=settings,
            )

        if ee is None:
            return GeeConnectionContext(
                enabled=True,
                connected=False,
                status="dependency_unavailable",
                message="earthengine-api dependency is not available in the backend environment.",
                project_id=None,
                settings=settings,
            )

        try:
            self._ensure_initialized(settings)
            ee.Number(1).getInfo()
            return GeeConnectionContext(
                enabled=True,
                connected=True,
                status="connected",
                message=None,
                project_id=settings.project_id,
                settings=settings,
            )
        except Exception:
            self._reset_initialization()
            return GeeConnectionContext(
                enabled=True,
                connected=False,
                status="authentication_failed",
                message=self._authentication_failure_message(settings),
                project_id=None,
                settings=settings,
            )

    def get_status(self) -> GeeStatusResponse:
        context = self.get_connection_context()
        return GeeStatusResponse(
            enabled=context.enabled,
            connected=context.connected,
            status=context.status,
            project_id=context.project_id,
            message=context.message,
        )


gee_service = GeeService()
