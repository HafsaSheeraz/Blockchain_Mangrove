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
