from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import dotenv_values

from app.models.gee import GeeStatusResponse

try:
    import ee
except ImportError:  # pragma: no cover
    ee = None


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class GeeSettings:
    enabled: bool
    project_id: str
    service_account_email: str
    private_key_file: str
    backend_dir: Path

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
    backend_dir = Path(__file__).resolve().parents[2]
    env_path = backend_dir / ".env"
    env_values = dotenv_values(env_path) if env_path.exists() else {}

    def _get(name: str, default: str = "") -> str:
        return os.getenv(name, env_values.get(name, default)).strip()

    return GeeSettings(
        enabled=_parse_bool(_get("GEE_ENABLED", "false"), default=False),
        project_id=_get("GEE_PROJECT_ID", ""),
        service_account_email=_get("GEE_SERVICE_ACCOUNT_EMAIL", ""),
        private_key_file=_get("GEE_PRIVATE_KEY_FILE", "secrets/gee-service-account.json"),
        backend_dir=backend_dir,
    )


class GeeService:
    def __init__(self):
        self._initialized = False
        self._initialized_project_id: str | None = None

    def _ensure_initialized(self, settings: GeeSettings) -> None:
        if self._initialized and self._initialized_project_id == settings.project_id:
            return

        credentials = ee.ServiceAccountCredentials(
            settings.service_account_email,
            str(settings.resolved_key_path()),
        )
        ee.Initialize(credentials=credentials, project=settings.project_id)
        self._initialized = True
        self._initialized_project_id = settings.project_id

    def _reset_initialization(self) -> None:
        self._initialized = False
        self._initialized_project_id = None

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

        missing_fields: list[str] = []
        if not settings.project_id:
            missing_fields.append("GEE_PROJECT_ID")
        if not settings.service_account_email:
            missing_fields.append("GEE_SERVICE_ACCOUNT_EMAIL")
        if not settings.private_key_file:
            missing_fields.append("GEE_PRIVATE_KEY_FILE")

        if missing_fields:
            return GeeConnectionContext(
                enabled=True,
                connected=False,
                status="missing_configuration",
                message=f"Missing required GEE configuration: {', '.join(missing_fields)}.",
                project_id=None,
                settings=settings,
            )

        key_path = settings.resolved_key_path()
        if not key_path.is_file():
            return GeeConnectionContext(
                enabled=True,
                connected=False,
                status="key_file_missing",
                message="Configured GEE private key file was not found.",
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
                message="Google Earth Engine authentication failed. Verify configuration and credentials.",
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
