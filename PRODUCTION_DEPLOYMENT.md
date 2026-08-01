# Production Readiness and Deployment Guide

## Local development

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Set `frontend/.env` with:

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

## Environment variables

### Backend

- `APP_ENV`
- `HOST`
- `PORT`
- `CORS_ORIGINS`
- `REQUEST_TIMEOUT_SECONDS`
- `MAP_LAYER_CACHE_TTL_SECONDS`
- `LOG_LEVEL`
- `MAX_REQUEST_BODY_BYTES`
- `MAX_AOI_TOTAL_VERTICES`
- `MAX_AOI_INTERIOR_RINGS`
- `MAX_AOI_RING_VERTICES`
- `MAX_AOI_SERIALIZED_BYTES`
- `MAX_AOI_DATE_RANGE_DAYS`
- `MAP_TILE_ALLOWED_HOSTS`
- `GEE_ENABLED`
- `GEE_PROJECT_ID`
- `GEE_SERVICE_ACCOUNT_EMAIL`
- `GEE_PRIVATE_KEY_FILE`

### Frontend

- `VITE_API_BASE_URL`

## Health and readiness

- `GET /health` is a liveness check.
- `GET /ready` reports startup readiness without calling Earth Engine.
- `GET /api/gee/status` remains the Earth Engine diagnostic endpoint.

## Production backend command

Linux:

```bash
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8001}"
```

If you use multiple workers, remember that in-memory caches are per worker.
Only scale workers if you are comfortable with that tradeoff.

## Cloud Run backend preflight

### Current backend readiness verdict

Conditionally ready for Cloud Run after runtime configuration is supplied.

Validated backend characteristics:

- ASGI entrypoint: `app.main:app`
- Lightweight liveness endpoint: `GET /health`
- Readiness endpoint: `GET /ready`
- Production CORS allowlist support via `CORS_ORIGINS`
- Request body-size guard via `MAX_REQUEST_BODY_BYTES`
- AOI/date validation and export filename hardening already in place
- HTTPS-only Earth Engine tile URL validation with host allowlist
- JSON, CSV, and PDF exports are generated in memory and do not require
  persistent disk

Current deployment-sensitive constraints:

- Earth Engine authentication currently expects a service-account JSON key path
- `REQUEST_TIMEOUT_SECONDS` is configured but is not yet enforced as an
  application-level timeout around Earth Engine calls
- Custom AOI result caching and map-layer descriptor caching are in-memory only
  and therefore per process / per Cloud Run instance

### Safest authentication design for Cloud Run

Preferred design:

1. Attach a dedicated Cloud Run runtime service account with only the minimum
   permissions needed for:
   - reading the Earth Engine credential secret from Secret Manager
   - writing Cloud Logging entries
2. Mount the Earth Engine service-account JSON from Secret Manager as a file
   inside the container, rather than baking credentials into the image
3. Set `GEE_PRIVATE_KEY_FILE` to the mounted path and keep
   `GEE_SERVICE_ACCOUNT_EMAIL` and `GEE_PROJECT_ID` in environment variables

This avoids embedding credentials in the image and works with the current code
without changing scientific processing.

Smallest future secure adaptation (proposed, not implemented here):

- add an Application Default Credentials fallback in the Earth Engine
  initialization path so Cloud Run could use its attached runtime identity
  directly when the service account is Earth Engine-enabled
- keep the current explicit key-file path as a backward-compatible fallback

Until that adaptation is implemented, Secret Manager file mount is the safest
production fit for the current codebase.

### Backend container files

- Dockerfile: [backend/Dockerfile](/D:/MangroveCarbonApp/backend/Dockerfile)
- Docker ignore: [backend/.dockerignore](/D:/MangroveCarbonApp/backend/.dockerignore)

Container properties:

- uses `python:3.12-slim`
- installs only backend Python dependencies
- runs as a non-root user
- does not copy `.env` files or credential material
- uses Cloud Run's `PORT`
- runs `uvicorn app.main:app` without `--reload`

### Required production environment variables

- `APP_ENV=production`
- `PORT` (provided by Cloud Run)
- `CORS_ORIGINS` (explicit comma-separated frontend allowlist)
- `LOG_LEVEL`
- `REQUEST_TIMEOUT_SECONDS`
- `MAX_REQUEST_BODY_BYTES`
- `MAX_AOI_TOTAL_VERTICES`
- `MAX_AOI_INTERIOR_RINGS`
- `MAX_AOI_RING_VERTICES`
- `MAX_AOI_SERIALIZED_BYTES`
- `MAX_AOI_DATE_RANGE_DAYS`
- `MAP_LAYER_CACHE_TTL_SECONDS`
- `MAP_TILE_ALLOWED_HOSTS`
- `GEE_ENABLED`
- `GEE_PROJECT_ID`
- `GEE_SERVICE_ACCOUNT_EMAIL`
- `GEE_PRIVATE_KEY_FILE`

Recommended production values should be supplied through Cloud Run environment
variables and Secret Manager mounts only; do not ship a populated `.env` file.

### Recommended Cloud Run service settings

- Request timeout: `900s`
  - reason: Earth Engine AOI analysis and map-layer generation can exceed short
    default HTTP timeouts
  - note: Cloud Run timeout becomes the hard runtime cap because the backend
    does not yet enforce `REQUEST_TIMEOUT_SECONDS` around Earth Engine calls
- CPU: `1`
- Memory: `2Gi`
- Concurrency: `1` initially
  - safest for long-running Earth Engine requests and per-instance in-memory
    caches
- Min instances: `0` for cost-sensitive deployment, or `1` if cold-start
  latency is unacceptable
- Max instances: `3` initially
  - caps quota pressure from parallel Earth Engine requests

Operational caveats:

- in-memory caches are not shared across Cloud Run instances
- multiple instances reduce cache hit rate and can duplicate Earth Engine work
- Cloud Run filesystem is temporary and instance-local
- map-layer descriptors expire using `MAP_LAYER_CACHE_TTL_SECONDS` (default
  1200 seconds), and Earth Engine map IDs should be treated as temporary
- JSON, CSV, and PDF exports are safe for Cloud Run because responses are
  generated in memory and streamed directly

### Cloud Run preflight checklist

- [ ] Build backend container from [backend/Dockerfile](/D:/MangroveCarbonApp/backend/Dockerfile)
- [ ] Confirm no secrets are copied into the image
- [ ] Create or identify a dedicated Cloud Run runtime service account
- [ ] Grant that runtime service account access to the Earth Engine secret in
      Secret Manager
- [ ] Mount the Earth Engine secret as a file inside the container
- [ ] Set `APP_ENV=production`
- [ ] Set explicit `CORS_ORIGINS`
- [ ] Set `GEE_ENABLED=true`
- [ ] Set `GEE_PROJECT_ID`
- [ ] Set `GEE_SERVICE_ACCOUNT_EMAIL`
- [ ] Set `GEE_PRIVATE_KEY_FILE` to the mounted secret path
- [ ] Set AOI and timeout limits explicitly
- [ ] Deploy with `--timeout=900 --concurrency=1`
- [ ] Verify `GET /health`
- [ ] Verify `GET /ready`
- [ ] Verify `GET /api/gee/status`
- [ ] Run one manual AOI analysis and one export smoke test

### Exact Cloud Run commands prepared (do not execute blindly)

Build image:

```bash
gcloud builds submit D:/MangroveCarbonApp/backend \
  --tag REGION-docker.pkg.dev/PROJECT_ID/ARTIFACT_REPO/mangrove-carbon-backend:TAG
```

Deploy service:

```bash
gcloud run deploy mangrove-carbon-backend \
  --image REGION-docker.pkg.dev/PROJECT_ID/ARTIFACT_REPO/mangrove-carbon-backend:TAG \
  --region REGION \
  --platform managed \
  --service-account CLOUD_RUN_RUNTIME_SA@PROJECT_ID.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 900 \
  --cpu 1 \
  --memory 2Gi \
  --concurrency 1 \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars APP_ENV=production,CORS_ORIGINS=https://YOUR_FRONTEND_HOST,LOG_LEVEL=info,REQUEST_TIMEOUT_SECONDS=120,MAX_REQUEST_BODY_BYTES=1000000,MAX_AOI_TOTAL_VERTICES=5000,MAX_AOI_INTERIOR_RINGS=20,MAX_AOI_RING_VERTICES=2000,MAX_AOI_SERIALIZED_BYTES=200000,MAX_AOI_DATE_RANGE_DAYS=1461,MAP_LAYER_CACHE_TTL_SECONDS=1200,MAP_TILE_ALLOWED_HOSTS=earthengine.googleapis.com,GEE_ENABLED=true,GEE_PROJECT_ID=YOUR_GCP_PROJECT,GEE_SERVICE_ACCOUNT_EMAIL=YOUR_EE_SERVICE_ACCOUNT@YOUR_GCP_PROJECT.iam.gserviceaccount.com,GEE_PRIVATE_KEY_FILE=/app/secrets/gee-service-account.json \
  --update-secrets=/app/secrets/gee-service-account.json=EARTH_ENGINE_SERVICE_ACCOUNT_JSON:latest
```

Post-deploy smoke checks:

```bash
curl -fsS https://BACKEND_HOST/health
curl -fsS https://BACKEND_HOST/ready
curl -fsS https://BACKEND_HOST/api/gee/status
```

## Frontend production build

```powershell
cd frontend
npm run build
```

Serve `frontend/dist/` from a static host and rewrite SPA routes such as
`/analysis` to `index.html`.

## React Router advisory risk acceptance

- Advisory: `GHSA-qwww-vcr4-c8h2`
- Installed version: `react-router-dom@7.18.2` with `react-router@7.18.2`
- Officially affected feature: unstable React Server Components APIs
- Current frontend architecture: declarative client-only SPA using
  `BrowserRouter`, `Routes`, `Route`, and fixed internal `Link` destinations
  (`/` and `/analysis`)
- Not used in this application:
  - unstable RSC APIs
  - SSR
  - React Router framework mode
  - server actions
  - loaders/actions
  - `createBrowserRouter`
  - `RouterProvider`

The reported advisory is not considered reachable in the current deployment
architecture because this application does not expose the unstable RSC
features named in the advisory and does not execute React Router server-side
request handling.

Until a compatible patched `react-router-dom` release is published, do not add:

- unstable RSC usage
- React Router server actions

Re-review this decision and upgrade when a compatible patched
`react-router-dom` release becomes available.

## CORS

Use an explicit production allowlist. Do not rely on localhost defaults in
production.

## Secret injection

- Keep the Earth Engine service-account JSON backend-only.
- Inject credentials through the runtime environment or a mounted secret.
- Do not copy secrets into the frontend build.

## Recommended deployment options

| Option | Frontend | Backend | Notes |
| --- | --- | --- | --- |
| Static host + Linux VM | Static CDN | Uvicorn on a VM | Simple, predictable, cheapest to operate |
| Static host + managed container | Static CDN | Container platform | Easier scaling, but watch request timeouts |
| Single VM for both | Served from the backend or reverse proxy | Same host | Simplest network path, less isolation |

Recommended: static frontend hosting plus a single Linux backend service with
explicit CORS origins and managed secrets.

## Production checklist

- [ ] Backend `.env` contains production values only
- [ ] Frontend `VITE_API_BASE_URL` points to the deployed backend
- [ ] CORS allowlist includes only approved origins
- [ ] Earth Engine credentials are mounted backend-only
- [ ] `/ready` returns ready
- [ ] `/health` returns OK
- [ ] SPA route rewrites are configured
- [ ] JSON, CSV and PDF exports work
- [ ] Security headers are present
- [ ] Logs do not contain secrets
- [ ] Backend and frontend test suites pass
