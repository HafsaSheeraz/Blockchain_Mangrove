from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import dotenv_values


LOCAL_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
DEFAULT_TILE_HOSTS = ["earthengine.googleapis.com"]
DEFAULT_GEE_PRIVATE_KEY_FILE = "secrets/gee-service-account.json"
SUPPORTED_GEE_AUTH_MODES = {"service_account_key", "service_account_json", "adc"}


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(raw_value: str | None, default: int) -> int:
    if raw_value is None or not raw_value.strip():
        return default
    return int(raw_value)


def _normalize_origin(value: str) -> str:
    return value.rstrip("/")


def _parse_csv(value: str | None, fallback: list[str], *, normalize=None) -> list[str]:
    if value is None or not value.strip():
        return list(fallback)

    items: list[str] = []
    for item in value.split(","):
        trimmed = item.strip()
        if not trimmed:
            continue
        normalized = normalize(trimmed) if normalize else trimmed
        if normalized not in items:
            items.append(normalized)

    return items or list(fallback)


def _get_env(name: str, env_values: dict[str, str], default: str = "") -> str:
    raw_value = os.getenv(name)
    if raw_value is not None:
        return raw_value
    file_value = env_values.get(name)
    if file_value is None:
        return default
    return str(file_value)


def _default_gee_auth_mode(app_env: str) -> str:
    return "adc" if app_env.strip().lower() == "production" else "service_account_key"


@dataclass(frozen=True)
class Settings:
    app_env: str
    api_version: str
    host: str
    port: int
    cors_origins: list[str]
    request_timeout_seconds: int
    map_layer_cache_ttl_seconds: int
    log_level: str
    max_aoi_total_vertices: int
    max_aoi_interior_rings: int
    max_aoi_ring_vertices: int
    max_aoi_serialized_bytes: int
    max_aoi_date_range_days: int
    max_request_body_bytes: int
    map_tile_allowed_hosts: list[str]
    gee_enabled: bool
    gee_auth_mode: str
    gee_project_id: str
    gee_service_account_email: str
    gee_private_key_file: str
    gee_service_account_json: str
    backend_dir: Path

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    def resolved_key_path(self) -> Path:
        key_path = Path(self.gee_private_key_file)
        if key_path.is_absolute():
            return key_path
        return self.backend_dir / key_path

    def readiness_issues(self) -> list[str]:
        issues: list[str] = []
        if self.is_production:
            if not self.cors_origins:
                issues.append("CORS_ORIGINS must define an explicit allowlist in production.")
            elif "*" in self.cors_origins:
                issues.append("Wildcard CORS origins are not allowed in production.")
            elif any(origin in LOCAL_CORS_ORIGINS for origin in self.cors_origins):
                issues.append("Localhost CORS origins are not allowed in production.")

        if self.gee_enabled:
            if self.gee_auth_mode not in SUPPORTED_GEE_AUTH_MODES:
                issues.append(
                    "GEE_AUTH_MODE must be one of: service_account_key, service_account_json, adc."
                )
                return issues

            missing = []
            if not self.gee_project_id:
                missing.append("GEE_PROJECT_ID")

            if self.gee_auth_mode == "service_account_key":
                if not self.gee_service_account_email:
                    missing.append("GEE_SERVICE_ACCOUNT_EMAIL")
                if not self.gee_private_key_file:
                    missing.append("GEE_PRIVATE_KEY_FILE")

                if missing:
                    issues.append(f"Missing required GEE configuration: {', '.join(missing)}.")
                else:
                    if (
                        self.is_production
                        and self.gee_private_key_file == DEFAULT_GEE_PRIVATE_KEY_FILE
                    ):
                        issues.append(
                            "Production service_account_key mode requires an explicit non-default GEE_PRIVATE_KEY_FILE path."
                        )
                    elif not self.resolved_key_path().is_file():
                        issues.append("Configured GEE private key file was not found.")
            elif self.gee_auth_mode == "service_account_json":
                if not self.gee_service_account_email:
                    missing.append("GEE_SERVICE_ACCOUNT_EMAIL")
                if not self.gee_service_account_json:
                    missing.append("GEE_SERVICE_ACCOUNT_JSON")

                if missing:
                    issues.append(f"Missing required GEE configuration: {', '.join(missing)}.")
                else:
                    try:
                        import json

                        parsed = json.loads(self.gee_service_account_json)
                    except Exception:
                        issues.append("GEE_SERVICE_ACCOUNT_JSON must contain valid service-account JSON.")
                    else:
                        if not isinstance(parsed, dict):
                            issues.append("GEE_SERVICE_ACCOUNT_JSON must contain valid service-account JSON.")
            elif missing:
                issues.append(f"Missing required GEE configuration: {', '.join(missing)}.")

        return issues


def build_settings() -> Settings:
    backend_dir = Path(__file__).resolve().parents[2]
    env_path = backend_dir / ".env"
    env_values = dotenv_values(env_path) if env_path.exists() else {}

    app_env = _get_env("APP_ENV", env_values, "development").strip() or "development"
    cors_raw = _get_env("CORS_ORIGINS", env_values, "")
    if cors_raw is None or not cors_raw.strip():
        cors_defaults = LOCAL_CORS_ORIGINS if app_env.lower() != "production" else []
        cors_origins = list(cors_defaults)
    else:
        cors_origins = _parse_csv(cors_raw, [], normalize=_normalize_origin)

    gee_auth_mode = _get_env("GEE_AUTH_MODE", env_values, "").strip().lower()
    if not gee_auth_mode:
        gee_auth_mode = _default_gee_auth_mode(app_env)

    return Settings(
        app_env=app_env,
        api_version=_get_env("API_VERSION", env_values, "0.4.1"),
        host=_get_env("HOST", env_values, "127.0.0.1").strip() or "127.0.0.1",
        port=_parse_int(_get_env("PORT", env_values, ""), 8001),
        cors_origins=cors_origins,
        request_timeout_seconds=_parse_int(_get_env("REQUEST_TIMEOUT_SECONDS", env_values, ""), 120),
        map_layer_cache_ttl_seconds=_parse_int(_get_env("MAP_LAYER_CACHE_TTL_SECONDS", env_values, ""), 1200),
        log_level=_get_env("LOG_LEVEL", env_values, "info").strip() or "info",
        max_aoi_total_vertices=_parse_int(_get_env("MAX_AOI_TOTAL_VERTICES", env_values, ""), 5000),
        max_aoi_interior_rings=_parse_int(_get_env("MAX_AOI_INTERIOR_RINGS", env_values, ""), 20),
        max_aoi_ring_vertices=_parse_int(_get_env("MAX_AOI_RING_VERTICES", env_values, ""), 2000),
        max_aoi_serialized_bytes=_parse_int(_get_env("MAX_AOI_SERIALIZED_BYTES", env_values, ""), 200000),
        max_aoi_date_range_days=_parse_int(_get_env("MAX_AOI_DATE_RANGE_DAYS", env_values, ""), 1461),
        max_request_body_bytes=_parse_int(_get_env("MAX_REQUEST_BODY_BYTES", env_values, ""), 1_000_000),
        map_tile_allowed_hosts=_parse_csv(
            _get_env("MAP_TILE_ALLOWED_HOSTS", env_values, ""),
            DEFAULT_TILE_HOSTS,
        ),
        gee_enabled=_parse_bool(_get_env("GEE_ENABLED", env_values, None), default=False),
        gee_auth_mode=gee_auth_mode,
        gee_project_id=_get_env("GEE_PROJECT_ID", env_values, "").strip(),
        gee_service_account_email=_get_env("GEE_SERVICE_ACCOUNT_EMAIL", env_values, "").strip(),
        gee_private_key_file=_get_env("GEE_PRIVATE_KEY_FILE", env_values, DEFAULT_GEE_PRIVATE_KEY_FILE).strip(),
        gee_service_account_json=_get_env("GEE_SERVICE_ACCOUNT_JSON", env_values, "").strip(),
        backend_dir=backend_dir,
    )


settings = build_settings()
