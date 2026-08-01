from dataclasses import dataclass
from pathlib import Path
import os


LOCAL_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
DEFAULT_TILE_HOSTS = ["earthengine.googleapis.com"]


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
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
    gee_project_id: str
    gee_service_account_email: str
    gee_private_key_file: str
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
            missing = []
            if not self.gee_project_id:
                missing.append("GEE_PROJECT_ID")
            if not self.gee_service_account_email:
                missing.append("GEE_SERVICE_ACCOUNT_EMAIL")
            if not self.gee_private_key_file:
                missing.append("GEE_PRIVATE_KEY_FILE")
            if missing:
                issues.append(f"Missing required GEE configuration: {', '.join(missing)}.")
            elif not self.resolved_key_path().is_file():
                issues.append("Configured GEE private key file was not found.")

        return issues


def build_settings() -> Settings:
    backend_dir = Path(__file__).resolve().parents[2]
    app_env = os.getenv("APP_ENV", "development").strip() or "development"
    cors_raw = os.getenv("CORS_ORIGINS")
    if cors_raw is None or not cors_raw.strip():
        cors_defaults = LOCAL_CORS_ORIGINS if app_env.lower() != "production" else []
        cors_origins = list(cors_defaults)
    else:
        cors_origins = _parse_csv(cors_raw, [], normalize=_normalize_origin)

    return Settings(
        app_env=app_env,
        api_version=os.getenv("API_VERSION", "0.4.1"),
        host=os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=_parse_int("PORT", 8001),
        cors_origins=cors_origins,
        request_timeout_seconds=_parse_int("REQUEST_TIMEOUT_SECONDS", 120),
        map_layer_cache_ttl_seconds=_parse_int("MAP_LAYER_CACHE_TTL_SECONDS", 1200),
        log_level=os.getenv("LOG_LEVEL", "info").strip() or "info",
        max_aoi_total_vertices=_parse_int("MAX_AOI_TOTAL_VERTICES", 5000),
        max_aoi_interior_rings=_parse_int("MAX_AOI_INTERIOR_RINGS", 20),
        max_aoi_ring_vertices=_parse_int("MAX_AOI_RING_VERTICES", 2000),
        max_aoi_serialized_bytes=_parse_int("MAX_AOI_SERIALIZED_BYTES", 200000),
        max_aoi_date_range_days=_parse_int("MAX_AOI_DATE_RANGE_DAYS", 1461),
        max_request_body_bytes=_parse_int("MAX_REQUEST_BODY_BYTES", 1_000_000),
        map_tile_allowed_hosts=_parse_csv(
            os.getenv("MAP_TILE_ALLOWED_HOSTS"),
            DEFAULT_TILE_HOSTS,
        ),
        gee_enabled=_parse_bool(os.getenv("GEE_ENABLED"), default=False),
        gee_project_id=os.getenv("GEE_PROJECT_ID", "").strip(),
        gee_service_account_email=os.getenv("GEE_SERVICE_ACCOUNT_EMAIL", "").strip(),
        gee_private_key_file=os.getenv("GEE_PRIVATE_KEY_FILE", "secrets/gee-service-account.json").strip(),
        backend_dir=backend_dir,
    )


settings = build_settings()
