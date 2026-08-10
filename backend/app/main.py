import hashlib
import json
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.api.routes.analysis import router as analysis_router
from app.api.routes.gee import router as gee_router
from app.api.routes.map import router as map_router
from app.core.config import settings

logger = logging.getLogger(__name__)


def _security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    return response


def _request_metadata(payload: dict) -> dict[str, str | None]:
    aoi_geometry = payload.get("aoi_geometry")
    geometry_hash = None
    if isinstance(aoi_geometry, dict):
        geometry_json = json.dumps(aoi_geometry, sort_keys=True, separators=(",", ":"))
        geometry_hash = hashlib.sha256(geometry_json.encode("utf-8")).hexdigest()

    return {
        "study_area": payload.get("study_area") if isinstance(payload.get("study_area"), str) else None,
        "start_date": payload.get("start_date") if isinstance(payload.get("start_date"), str) else None,
        "end_date": payload.get("end_date") if isinstance(payload.get("end_date"), str) else None,
        "geometry_hash": geometry_hash,
    }


def create_app() -> FastAPI:
    app = FastAPI(
        title="Mangrove Carbon Explorer API",
        version=settings.api_version,
        description="API for demonstration and future mangrove biomass/carbon analysis workflows.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Request-ID"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def add_request_id_and_security_headers(request: Request, call_next):
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        started_at = time.perf_counter()

        if request.method in {"POST", "PUT", "PATCH"} and request.url.path.startswith("/api/"):
            content_length = request.headers.get("content-length")
            if content_length and content_length.isdigit() and int(content_length) > settings.max_request_body_bytes:
                response = PlainTextResponse("Request body too large.", status_code=413)
                response.headers["X-Request-ID"] = request_id
                return _security_headers(response)

            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                body = await request.body()
                if body:
                    try:
                        payload = json.loads(body)
                    except json.JSONDecodeError:
                        payload = None
                    if isinstance(payload, dict):
                        metadata = _request_metadata(payload)
                        logger.info(
                            "request_id=%s route=%s method=%s study_area=%s start_date=%s end_date=%s geometry_hash=%s",
                            request_id,
                            request.url.path,
                            request.method,
                            metadata["study_area"],
                            metadata["start_date"],
                            metadata["end_date"],
                            metadata["geometry_hash"],
                        )

        response = await call_next(request)
        duration_ms = (time.perf_counter() - started_at) * 1000.0
        logger.info(
            "request_id=%s route=%s method=%s status=%s duration_ms=%.1f",
            request_id,
            request.url.path,
            request.method,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return _security_headers(response)

    @app.get("/health", tags=["System"])
    def health_check():
        return {"status": "ok"}

    @app.get("/", tags=["System"])
    def root():
        return {
            "service": "Mangrove Carbon API",
            "status": "running",
            "health": "/health",
            "docs": "/docs",
        }

    @app.get("/ready", tags=["System"])
    def readiness_check():
        issues = settings.readiness_issues()
        return {
            "status": "ready" if not issues else "not_ready",
            "ready": not issues,
            "app_env": settings.app_env,
            "gee_enabled": settings.gee_enabled,
            "cors_origins_configured": bool(settings.cors_origins),
            "issues": issues,
        }

    app.include_router(analysis_router)
    app.include_router(gee_router)
    app.include_router(map_router)
    return app


app = create_app()
