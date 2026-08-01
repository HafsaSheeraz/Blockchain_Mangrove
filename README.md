# Mangrove Carbon Explorer

A full-stack application for exploring mangrove extent, above-ground biomass, and carbon stock estimates using satellite remote sensing data.

For production deployment and readiness details, see [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md).

## Project Structure

```
MangroveCarbonApp/
├── frontend/   # React + Vite SPA
└── backend/    # Python FastAPI REST API
```

---

## Prerequisites

| Tool | Minimum version | Download |
|------|-----------------|---------|
| Node.js | 18 LTS | https://nodejs.org |
| Python | 3.11 | https://python.org |

---

## Windows Setup (first time)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```powershell
cd frontend
npm install
```

---

## Running the Application

### Start the backend (terminal 1)

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

API will be available at: http://127.0.0.1:8001  
Interactive docs: http://127.0.0.1:8001/docs

### Start the frontend (terminal 2)

```powershell
cd frontend
# Ensure .env contains VITE_API_BASE_URL=http://127.0.0.1:8001
npm run dev
```

App will be available at: http://localhost:5173

---

## Running Tests

### Backend tests

```powershell
cd backend
.\.venv\Scripts\activate
pytest
```

### Frontend tests

```powershell
cd frontend
npm test
```

---

## Linting & Production Build

### Lint frontend

```powershell
cd frontend
npm run lint
```

### Build frontend for production

```powershell
cd frontend
npm run build
```

Output is placed in `frontend/dist/`.

---

## Environment Variables

Copy the example files before first run:

```powershell
# Backend
copy backend\.env.example backend\.env

# Frontend
copy frontend\.env.example frontend\.env
```

Edit each `.env` file as needed (see comments inside).

Backend CORS is environment-driven via `CORS_ORIGINS` (comma-separated).  
For local development include:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

---

## API Endpoints (Module 10)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{"status": "ok"}` |
| POST | `/api/analyze` | Returns demonstration-only mangrove biomass/carbon analysis output |
| GET | `/api/gee/status` | Returns Google Earth Engine authentication status only (no analysis) |
| GET | `/api/gee/datasets/status` | Metadata-only Earth Engine dataset access check for Indus Delta |
| GET | `/api/gee/rh98/summary` | Live Earth Engine RH98 summary statistics (whole AOI and GMW-masked) |
| GET | `/api/gee/biomass/summary` | Live mangrove biomass and carbon-density statistics (GMW-masked only) |
| GET | `/api/gee/carbon/stock-summary` | Live mangrove area, GEDI raster coverage, and carbon stock totals |

### POST `/api/analyze` (Mock demonstration endpoint)

This endpoint currently returns **mock demonstration data** only.  
No live Google Earth Engine processing is performed.

Request body:

```json
{
  "study_area": "indus_delta",
  "start_date": "2019-01-01",
  "end_date": "2021-12-31"
}
```

Validation rules:
- `study_area` must currently be `indus_delta`
- `start_date` and `end_date` must be valid ISO dates (`YYYY-MM-DD`)
- `end_date` must be after `start_date`

Windows curl example:

```powershell
curl -X POST "http://127.0.0.1:8001/api/analyze" `
  -H "Content-Type: application/json" `
  -d "{\"study_area\":\"indus_delta\",\"start_date\":\"2019-01-01\",\"end_date\":\"2021-12-31\"}"
```

### Testing from Swagger UI (`/docs`)

1. Start backend on port 8001:

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

2. Open: `http://127.0.0.1:8001/docs`
3. Expand `POST /api/analyze`
4. Click **Try it out**
5. Paste:

```json
{
  "study_area": "indus_delta",
  "start_date": "2019-01-01",
  "end_date": "2021-12-31"
}
```

6. Click **Execute**
7. Confirm `mode` is `"demonstration"` and `warning` states no live Earth Engine processing.

---

## Frontend ↔ Backend integration (Module 4)

The Analysis dashboard now calls the mock endpoint:

- `POST {VITE_API_BASE_URL}/api/analyze`
- Default `.env.example` value:

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

### Manual integration check

1. Backend running on `http://127.0.0.1:8001`
2. Frontend running on `http://localhost:5173`
3. Open `http://localhost:5173/analysis`
4. Click **Run Biomass Analysis**
5. Confirm:
   - button enters loading/disabled state
   - cards populate from API response values
   - formulas are rendered from `methodology`
   - warning shows: `Demonstration results only. No live Earth Engine processing was performed.`

If backend is down, UI should show:

`Unable to connect to the analysis server. Confirm that the FastAPI backend is running on port 8001.`

---

## Google Earth Engine authentication status (Module 5)

Module 5 adds **authentication status checks only**.  
It does **not** execute GEDI/Sentinel-2/GMW analysis and does **not** replace mock `/api/analyze` output.

### Secure backend configuration

Set these values in `backend/.env`:

```env
GEE_ENABLED=false
GEE_PROJECT_ID=
GEE_SERVICE_ACCOUNT_EMAIL=
GEE_PRIVATE_KEY_FILE=secrets/gee-service-account.json
```

Security notes:
- Keep service-account key files under `backend/secrets/`
- Never commit key files or `.env` to source control
- The API never returns private key content or full secret file paths

### Test Earth Engine auth status from API

1. Start backend:

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

2. Check status endpoint:

```powershell
curl "http://127.0.0.1:8001/api/gee/status"
```

Expected when disabled:

```json
{
  "enabled": false,
  "connected": false,
  "status": "disabled"
}
```

Expected when configured and connected:

```json
{
  "enabled": true,
  "connected": true,
  "status": "connected",
  "project_id": "your-gee-project-id"
}
```

---

## Earth Engine dataset metadata check (Module 7)

Module 7 keeps a **lightweight, read-only metadata check** endpoint:

- `GET /api/gee/datasets/status`

This endpoint **does not** run RH98 statistics, area, biomass, or carbon processing.

### Dataset identifiers

- GEDI L2A monthly: `LARSE/GEDI/GEDI02_A_002_MONTHLY`
- Sentinel-2 L2A Harmonized: `COPERNICUS/S2_SR_HARMONIZED`
- Project-owned GMW Indus Delta mask: `projects/mangroves123/assets/GMW_2020_IndusDelta`

### Study area and mask semantics

Current checks use an **Indus Delta temporary processing rectangle**:

`[66.5, 23.5, 68.5, 24.8]`

Important semantics:
- The rectangle is the processing boundary and is not claimed as an exact administrative boundary.
- The project-owned GMW IMAGE asset is the mangrove mask.
- Future GEDI/biomass workflows must run only on positive, valid mask pixels.
- Results should not be described as covering unmasked parts of the rectangle.

### Date range and filter convention

- `start_date = 2019-04-01`
- `end_date = 2021-12-31`
- Earth Engine filtering uses **end-exclusive** convention: `filterDate(start, end)`

### Quota and restricted-mode safety

This metadata endpoint intentionally avoids heavy processing:

- no `reduceRegion`
- no `sample`
- no `mosaic`
- no Sentinel-2 composites
- no area or pixel-statistic calculations
- no RH98, biomass, or carbon calculations

If noncommercial/restricted quota issues occur, endpoint returns a safe dataset-level error status.

### Manual dataset-status test

1. Ensure backend is running on port `8001`
2. Call:

```powershell
curl "http://127.0.0.1:8001/api/gee/datasets/status"
```

3. Confirm:
   - `processing_performed` is `false`
   - `message` indicates metadata-only check
   - `datasets.gmw_2020` reports `source`, `asset_type`, `band_names`, and `usable_as_mask`
   - each dataset block reports `accessible` and, where applicable, band-availability status

### Cache behavior

One successful dataset-status result is cached in the backend process to reduce repeated live metadata calls.  
Restart the backend process to refresh cached success results.

---

## Live GEDI RH98 summary (Module 8.1)

Module 8 adds live, quality-filtered GEDI RH98 summary statistics endpoint:

- `GET /api/gee/rh98/summary`

### Inputs and filters

- GEDI dataset: `LARSE/GEDI/GEDI02_A_002_MONTHLY`
- Baseline date range: `2020-01-01` to `2020-04-01` with end-exclusive `filterDate(start, end)`
- Processing rectangle: `[66.5, 23.5, 68.5, 24.8]`
- Required GEDI bands: `rh98`, `quality_flag`, `degrade_flag`
- Quality filters per monthly image:
  - `quality_flag == 1`
  - `degrade_flag == 0`
  - select `rh98` and preserve valid-data mask

### Aggregation and semantics

- Aggregation method: `mosaic`
- Earth Engine mosaic behavior: the **last valid image in collection order** wins where overlaps occur
- Output is a sparse 25 m raster representation (not a wall-to-wall canopy map)
- Scientific reduce scale: **25 metres** (`bestEffort=false`)
- Statistics are produced for:
  - whole processing rectangle
  - same mosaic with validated positive GMW mask pixels only

### GMW mask used

- Asset: `projects/mangroves123/assets/GMW_2020_IndusDelta`
- Validated band: `b1`
- Positive pixels only

### Baseline diagnostics and reference comparison

The endpoint includes diagnostic fields to align live validation against the earlier Jan–Mar 2020 baseline workflow:

- `filtered_monthly_image_count`
- `baseline_purpose = "reproduce_jan_mar_2020_reference"`
- `reference_results` (expected comparison values only)
- `difference_from_reference` (live calculated minus reference)

Reference values are reported for comparison only and never replace live Earth Engine calculations.

The endpoint also performs an optional metadata comparison check for:

- `projects/mangroves123/assets/GEDI_L2A_RH98_JanMar2020_IndusDelta`

When accessible and IMAGE-type, it reports band names and projection metadata.  
It is never used as the computed RH98 output in this module.

### Correct interpretation of count

The response field is:

- `valid_gedi_raster_pixel_count`

This count represents valid RH98 mosaic raster cells and **must not** be interpreted as unique GEDI shots/footprints.

### Quota and failure behavior

- Quota/restricted-mode and timeout errors are returned as safe structured API statuses
- No credentials, private key paths, or stack traces are exposed
- One successful RH98 summary result is cached in-process; restart backend to refresh
- Extra warnings are emitted when:
  - whole-AOI RH98 max exceeds 50 m
  - mangrove-masked RH98 max exceeds 15 m
  - valid GEDI raster pixel counts differ substantially from Jan–Mar 2020 reference counts

### Scope boundary

Module 8.1 does **not** calculate AGB, BGB, TAB, carbon, mangrove area, or Sentinel-2 pixel products.

### Manual endpoint test

1. Start backend:

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

2. Run:

```powershell
curl "http://127.0.0.1:8001/api/gee/rh98/summary"
```

3. Confirm:
   - `mode` is `live_earth_engine`
   - `baseline_purpose` is `reproduce_jan_mar_2020_reference`
   - `filters.aggregation_method` is `mosaic`
   - `filters.scale_m` is `25`
   - `date_range.start_date` is `2020-01-01` and `date_range.end_date` is `2020-04-01`
   - both `whole_aoi` and `mangrove_masked` return RH98 min/mean/max and `valid_gedi_raster_pixel_count`
   - `reference_results` and `difference_from_reference` are present and distinct from live calculated values
   - `comparison_asset` reports metadata/check status for `GEDI_L2A_RH98_JanMar2020_IndusDelta`
   - warnings include sparse coverage and raster-cell interpretation notes

---

## Live biomass and carbon-density summary (Module 9)

Module 9 adds live biomass and carbon-density statistics for the Indus Delta mangroves.

- `GET /api/gee/biomass/summary`

This endpoint calculates **density statistics only** (Mg/ha or Mg C/ha at valid GEDI/GMW pixels).  
It does **not** calculate mangrove area, total ecosystem carbon stock, or any pixel-area-weighted extrapolation.

### Processing graph

Reuses the validated Module 8.1 pipeline:

1. Filter `LARSE/GEDI/GEDI02_A_002_MONTHLY` to the Indus Delta rectangle (`[66.5, 23.5, 68.5, 24.8]`) and date range `2020-01-01` → `2020-04-01` (end-exclusive)
2. Per monthly image: `quality_flag == 1`, `degrade_flag == 0`, select `rh98`
3. `mosaic()` the quality-filtered images
4. Apply GMW binary mask (`projects/mangroves123/assets/GMW_2020_IndusDelta`, band `b1`, positive pixels only)
5. Build a 5-band image stack with explicit band names and shared valid-data mask
6. `reduceRegion(min + mean + max + count, scale=25 m, tileScale=4, bestEffort=False)` in **one call**

### Formula coefficients (centralized in `gee_datasets.py`)

| Coefficient | Value | Meaning |
|---|---|---|
| `BIOMASS_HEIGHT_TO_AGB` | 10.0 | AGB (Mg/ha) = 10.0 × RH98 (m) |
| `BIOMASS_ROOT_TO_SHOOT` | 0.49 | BGB (Mg/ha) = 0.49 × AGB |
| `BIOMASS_TO_CARBON` | 0.5 | Carbon (Mg C/ha) = 0.5 × TAB |

Formulas applied pixel-wise to each valid raster cell:

```
AGB    = 10.0  × RH98         [Mg/ha]
BGB    = 0.49  × AGB          [Mg/ha]
TAB    = AGB + BGB             [Mg/ha]
Carbon = 0.5   × TAB          [Mg C/ha]
```

### Expected approximate results (Jan–Mar 2020 baseline, n ≈ 1130 valid pixels)

| Band | Unit | Approx. min | Approx. mean | Approx. max |
|---|---|---|---|---|
| RH98 | m | 2.39 | 3.09 | 5.76 |
| AGB | Mg/ha | 23.90 | 30.91 | 57.60 |
| BGB | Mg/ha | 11.71 | 15.14 | 28.22 |
| TAB | Mg/ha | 35.61 | 46.05 | 85.82 |
| Carbon | Mg C/ha | 17.81 | 23.03 | 42.91 |

### Important limitations

- **Density vs total stock**: values are per-pixel densities (Mg/ha or Mg C/ha), not total ecosystem carbon.
- **GEDI coverage is sparse**: 25 m mosaic raster cells are not a continuous wall-to-wall map.
- **Not locally calibrated**: the height-to-AGB factor (10.0) is a stand-level approximation; no field calibration data from the Indus Delta has been applied.
- **Pixel counts ≠ GEDI shots**: `valid_raster_pixel_count` counts raster cells, not unique physical GEDI footprints.
- **Processing rectangle ≠ administrative boundary**: the rectangle `[66.5, 23.5, 68.5, 24.8]` is a temporary processing boundary.

### Formula validation

After each live computation, the service validates that derived-band means satisfy the formula invariants (relative tolerance `1e-6`).  
If validation fails (e.g., due to a computation error or data inconsistency), the response status is `formula_validation_failed` and the raw statistics are still returned for debugging.

### Caching

One successful biomass summary is cached in-process.  
Restart the backend to refresh cached results.

### Manual endpoint test

1. Start backend:

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

2. Run:

```powershell
curl "http://127.0.0.1:8001/api/gee/biomass/summary"
```

3. Confirm:
   - `mode` is `live_earth_engine`
   - `methodology` block shows all three coefficients and formula strings
   - `statistics` contains five band entries (`rh98`, `agb`, `bgb`, `tab`, `carbon`) each with `unit`, `min`, `mean`, `max`, `valid_raster_pixel_count`
   - All five `valid_raster_pixel_count` values are equal (shared mask)
   - `processing.scale_m` is `25`
   - `gmw_mask.positive_pixels_only` is `true`
   - `processing_performed` is `true`
   - Four warnings are present
   - No `total_carbon`, `mangrove_area`, or `carbon_stock` fields appear anywhere in the response

---

## Live mangrove area and carbon stock (Module 10)

Module 10 adds live mangrove area, GEDI raster coverage, direct sampled raster carbon stock,
and extrapolated ecosystem carbon stock for the Indus Delta.

- `GET /api/gee/carbon/stock-summary`

### Key definitions

| Term | Definition |
|---|---|
| **Mapped mangrove area** | Sum of pixel areas (ha) for all positive-valued pixels in the project-owned GMW b1 mask, computed at 10 m scale |
| **Valid GEDI raster coverage area** | Sum of pixel areas (ha) where the quality-filtered, GMW-masked Carbon raster has valid data, computed at 25 m scale |
| **GEDI raster coverage %** | `(coverage area / mapped area) × 100` — typically well below 1% (sparse GEDI) |
| **Direct sampled raster carbon stock** | `sum(Carbon_Mg_C_ha × pixel_area_ha)` over valid GEDI/GMW raster cells only; covers sampled area, not all mangroves |
| **Extrapolated ecosystem carbon stock** | `mean_Carbon_Mg_C_ha × mapped_mangrove_area_ha` — assumes sparse GEDI is spatially representative; labelled as an extrapolated estimate |

### Area processing

```
Mapped mangrove area:
  ee.Image.pixelArea().divide(10000)          # m² → ha per pixel
  .updateMask(GMW_b1_binary_mask)
  .reduceRegion(sum, scale=10 m, bestEffort=False)
  → {"area": mapped_mangrove_area_ha}

GEDI raster coverage + direct stock (combined, at 25 m):
  carbon_band   = biomass_stack.select("Carbon")
  gedi_coverage = pixel_area_ha.updateMask(carbon_band).rename("gedi_coverage_ha")
  direct_stock  = carbon_band.multiply(pixel_area_ha).rename("direct_stock_mgc")
  analysis_img  = carbon_band.addBands(gedi_coverage).addBands(direct_stock)
  .reduceRegion(min+mean+max+count+sum, scale=25 m, bestEffort=False)
  → gedi_coverage_ha_sum  = GEDI raster coverage area (ha)
  → direct_stock_mgc_sum  = direct sampled carbon (Mg C)
  → Carbon_mean           = mean density (Mg C/ha)

Extrapolated stock (no EE call):
  extrapolated = Carbon_mean × mapped_mangrove_area_ha
```

### Expected approximate results (Jan–Mar 2020)

| Field | Unit | Approx. value |
|---|---|---|
| Mapped mangrove area | ha | 90,769 |
| Valid GEDI raster coverage | ha | ~64.29 |
| GEDI raster coverage % | % | ~0.0708% |
| Direct sampled raster carbon | Mg C | ~1,480.37 |
| Extrapolated ecosystem carbon | Mg C | ~2,090,028 |

### Reference discrepancy note

The live Earth Engine area-weighted raster sum reproduces the older direct sampled
value of **~1,480.37 Mg C** and is authoritative.

The earlier 70.6 ha estimate came from a fixed-cell assumption:

```
1130 raster pixels × 625 m²/pixel = 706,250 m² = 70.625 ha
```

That fixed-area estimate is **not** authoritative for this geographic raster grid.
Area-weighted stock is computed from:

```
direct_stock = sum(Carbon_density × pixel_area_ha) for all valid raster cells
```

where `pixel_area_ha` comes from `ee.Image.pixelArea().divide(10000)`.

Therefore:
- **Pixel count** (`valid_gedi_raster_pixel_count`) and
- **Pixel-area ground-area sum** (`valid_gedi_raster_coverage_area_ha`)

are different measurements and are not interchangeable.

The older extrapolated value (~2,090,417.67 Mg C) came from using a rounded mean
carbon density (`23.03 Mg C/ha`). The live implementation retains full precision
(`23.02570844643939 Mg C/ha`), giving ~2,090,028 Mg C.

### Important limitations

- **Density vs total stock**: `carbon_density` values are Mg C/ha (density at valid raster pixels). `stock.direct_sampled_raster_carbon_mg_c` and `stock.extrapolated_ecosystem_carbon_mg_c` are totals in Mg C.
- **Representativeness assumption**: The extrapolated stock assumes that the sparse GEDI samples uniformly represent the full mapped mangrove extent. This is an approximation only.
- **GEDI raster coverage ≠ physical footprint area**: `valid_gedi_raster_coverage_area_ha` is the sum of 25 m raster cell areas; it does not represent unique GEDI-shot physical footprints.
- **No continuous Sentinel-2 carbon map**: This module does not produce a Sentinel-2-based spatially continuous carbon surface. Only the sparse GEDI raster is used.
- **Height-to-AGB not locally calibrated**: `AGB = 10 × RH98` is a stand-level approximation.
- **Processing rectangle ≠ administrative boundary**: `[66.5, 23.5, 68.5, 24.8]` is a temporary boundary.

### Validation invariants

After each live computation the service checks:
- `mapped_mangrove_area_ha > 0`
- `valid_gedi_raster_coverage_area_ha > 0`
- `valid_gedi_raster_coverage_area_ha ≤ mapped_mangrove_area_ha`
- `0 ≤ coverage_percent ≤ 100`
- `direct_sampled_stock ≥ 0`
- `extrapolated_stock ≥ direct_sampled_stock`
- `extrapolated_stock ≈ mean_Carbon × mapped_area` (relative tolerance `1e-6`)
- `valid_gedi_raster_pixel_count > 0`

If any invariant fails, the response status is `validation_failed` and raw statistics are still included for debugging. No success cache is written.

### Caching

One successful stock summary is cached in-process.  
Restart the backend to refresh cached results.

### Manual endpoint test

1. Start backend:

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

2. Run:

```powershell
curl "http://127.0.0.1:8001/api/gee/carbon/stock-summary"
```

3. Confirm:
   - `mode` is `live_earth_engine`
   - `area.mapped_mangrove_area_ha` ≈ 90,769 ha
   - `area.valid_gedi_raster_coverage_area_ha` ≈ 64.29 ha  
   - `area.gedi_raster_coverage_percent` < 1%
   - `stock.direct_sampled_raster_carbon_mg_c` ≈ 1,480.37 Mg C
   - `stock.extrapolated_ecosystem_carbon_mg_c` ≈ 2,090,028 Mg C
   - `reference_comparison.note` states the live area-weighted result reproduces ~1,480.37 Mg C
   - `processing.gmw_area_scale_m` is `10`, `processing.gedi_analysis_scale_m` is `25`
   - `processing.best_effort` is `false`
   - Three warnings and three assumptions present
   - No `sentinel`, `ndvi`, or `unique_gedi_shots` fields appear in the response

---

## Carbon Stock Summary dashboard (Module 11)

Module 11 upgrades the `/analysis` page into a live Carbon Stock Summary dashboard that consumes:

- `GET {VITE_API_BASE_URL}/api/gee/carbon/stock-summary`

The frontend does not hardcode scientific outputs and does not recompute carbon stock totals independently.
It renders the backend response fields directly, including status, study-area metadata, carbon density, area, stock,
and reference comparison blocks.

### Frontend API configuration

Use the existing environment-variable pattern:

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

The API service layer now includes:

- `buildCarbonStockSummaryUrl()`
- `getCarbonStockSummary({ signal })`

`getCarbonStockSummary` supports request cancellation, checks non-2xx responses, validates required response keys,
and surfaces safe backend error messages.

### Dashboard behavior

The dashboard implements:

- Loading state with accessible status text and placeholders
- Success state with formatted summary cards and units
- Empty/unavailable state when stock data blocks are not usable
- Error state with accessible message and manual **Retry**
- Responsive layout for mobile, tablet, and desktop

### Dashboard metrics shown

- Mapped mangrove area (ha)
- GEDI-covered mangrove area (ha)
- GEDI coverage percentage (%)
- Valid GEDI raster sample count
- Mean carbon density (Mg C/ha)
- Direct sampled carbon stock (Mg C)
- Extrapolated ecosystem carbon stock (Mg C)
- Validated reference result and difference from reference (Mg C)

### Scientific interpretation in UI

The dashboard text preserves the corrected Module 10.1 interpretation:

- ~1,480.37 Mg C is a validated direct sampled result reproduced by live area-weighted processing.
- The older 70.625 ha estimate came from `1130 × 625 m²` fixed-cell assumption.
- Authoritative GEDI-covered area is based on `ee.Image.pixelArea()` sum over the geographic raster grid (~64.293 ha).
- Pixel count and pixel-area ground-area sum are different measurements.
- Extrapolated ecosystem stock uses full-precision mean carbon density from backend results.

### Development and verification commands

Backend:

---

## Module 16 — Centralized Region Catalog and Abu Dhabi Asset Correction

### Root cause

The backend previously used a single project GMW asset
(`projects/mangroves123/assets/GMW_2020_IndusDelta`) for every region.
That asset covers only approximately lon 66.49–68.50°E, lat 23.49–24.80°N
(Indus Delta only). Abu Dhabi is at approximately lon 54°E and therefore
returned zero mangrove coverage. This was an asset-selection bug, not a
masking or coordinate error.

### Region catalog

A centralized `REGION_CATALOG` (`backend/app/core/gee_datasets.py`) maps
each study-area ID to its region-specific GMW configuration. Clients never
supply an asset ID; asset selection is entirely server-side.

| ID | Name | GMW asset | Asset type | Default dates |
|----|------|-----------|------------|---------------|
| `indus_delta` | Indus Delta, Pakistan | `projects/mangroves123/assets/GMW_2020_IndusDelta` | IMAGE | 2020-01-01 → 2020-04-01 |
| `abu_dhabi` | Abu Dhabi, United Arab Emirates | `projects/mangroves123/assets/GMW_2020_AbuDhabi_v2` | IMAGE | 2019-01-01 → 2021-12-31 |
| `custom` | Custom AOI | `projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020` | IMAGE_COLLECTION | user-supplied |

### Abu Dhabi verified study extent

The Abu Dhabi AOI was corrected from a broad provisional rectangle
(53.6–55.9°E, 23.7–25.6°N) to the verified project study extent:

```
[54.32, 24.40, 54.52, 24.55]  (lon_min, lat_min, lon_max, lat_max)
```

Live diagnostic on `GMW_2020_AbuDhabi_v2` confirmed:
- Asset footprint: 54.319–54.520°E, 24.399–24.550°N
- `b1_count` within Abu Dhabi AOI: 153,678 positive pixels (after selfMask)
- Positive pixel-area sum: ≈1,391.92 ha

### IMAGE_COLLECTION handling

The public global GMW 2020 source
(`projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020`) is an
`ImageCollection` of 1,646 tiles. `gee_mask_service.build_binary_mask` now
accepts an `asset_type` parameter and mosaics the collection before band
selection when `asset_type == "IMAGE_COLLECTION"`.

### Cache key isolation

Cache keys for custom AOI results and map-layer descriptors now include
`gmw_asset_id`. This ensures that results for Indus Delta (using the
Indus-only GMW asset) and Abu Dhabi (using its own asset) are never
incorrectly shared, even when the same geometry and date range are submitted.

### Frontend changes

- `ABU_DHABI_BOUNDS` updated to `[54.32, 24.40, 54.52, 24.55]`.
- Abu Dhabi map center updated to `[24.475, 54.42]`, zoom 12.
- Each study area now carries `defaultStartDate` and `defaultEndDate`.
- Selecting a region resets the date range to the region's defaults.

### No-data message

The no-data message is now:
```
AOI has no mapped mangrove area (no GMW mask coverage).
```
The previous message appended an asset-coverage note referencing the
Indus-Delta footprint; this was removed because each region now uses its
own correct asset.

### Backward compatibility

`GMW_2020 = GMW_2020_INDUS` alias is preserved so the fixed Indus baseline
pipeline (`/api/gee/carbon/stock-summary` endpoint) is unchanged.

### Files changed

| File | Change |
|------|--------|
| `backend/app/core/gee_datasets.py` | Added `GMW_2020_INDUS`, `GMW_2020_ABU_DHABI`, `GMW_GLOBAL_2020_COLLECTION`, asset-type tokens, `RegionConfig` dataclass, `REGION_CATALOG` |
| `backend/app/services/gee_mask_service.py` | Added `asset_type` parameter; IMAGE_COLLECTION mosaic branch |
| `backend/app/services/gee_carbon_stock_service.py` | REGION_CATALOG lookup in `run_live_summary_for_custom_aoi` and `run_live_map_layers_for_custom_aoi`; GMW asset threaded through `_run_live_summary_parameterized`; cache keys include `gmw_asset_id` |
| `frontend/src/config/studyAreas.js` | Abu Dhabi bounds, map center, `defaultStartDate`/`defaultEndDate` |
| `frontend/src/pages/Analysis.jsx` | `handleRegionChange` resets dates from region defaults |
| `backend/tests/test_gmw_coverage_diagnostics.py` | Updated for simplified no-data message; added `TestRegionCatalog` class (11 tests) |
| `backend/tests/test_custom_aoi_service_audit.py` | Fixed `fake_run` signatures; updated cache-count assertion |

### Final test counts (Module 16 complete)

- **Backend:** 244 passed
- **Frontend:** 116 passed
- **Lint:** clean (0 warnings)
- **Build:** passed


```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/ -q
```

Frontend:

```powershell
cd frontend
npm test -- --run
npm run lint
npm run build
```

---

## Region selection, AOI drawing, and date-range workflow (Module 12+)

The Analysis page provides an interactive **Study Area setup** workflow for predefined regions and custom AOIs, with validated inputs ready for live Earth Engine analysis.

### Added frontend modules

- `frontend/src/config/studyAreas.js`
  - Central predefined-region catalog (Indus Delta, Abu Dhabi)
  - Includes IDs, display names, countries, map defaults, and provisional polygon extents
- `frontend/src/utils/geo.js`
  - Coordinate normalization and conversions
  - GeoJSON storage uses `[longitude, latitude]` order
  - Leaflet display conversion is handled separately
- `frontend/src/services/analysisRequestBuilder.js`
  - Builds validated **prepared request preview** payloads
  - Preserves valid GeoJSON coordinate order (`[longitude, latitude]`)
- `frontend/src/components/analysis/StudyAreaSetup.jsx`
  - Mode switch (predefined vs custom), region selector, date inputs, AOI summary, validation
- `frontend/src/components/analysis/StudyAreaMap.jsx`
  - Interactive map, polygon draw/edit/delete, mode-aware display, cleanup-safe listeners

### Mapping stack and compatibility

Module 12 uses:

- `leaflet`
- `react-leaflet`
- `leaflet-draw`

Compatibility was verified before implementation:

- `react-leaflet@5.0.0` declares peers `react:^19.0.0` and `react-dom:^19.0.0`
- `leaflet-draw@1.0.4` is integrated through a small React-Leaflet adapter in `StudyAreaMap.jsx`

`react-leaflet-draw` metadata was checked, but a Vite production-build spike showed an ESM export incompatibility in this environment.  
Therefore Module 12 uses `leaflet-draw` directly via `useMap()` + explicit setup/cleanup listeners.

The map renders with explicit container height, Leaflet CSS, drawing controls, and OpenStreetMap attribution.

### Study area workflow behavior

- Two modes:
  - **Predefined region** (Indus Delta or Abu Dhabi)
  - **Custom AOI polygon**
- Predefined mode displays selected region AOI and map view
- Custom mode enables draw/edit/delete polygon controls
- Clearing polygon removes custom AOI from prepared request
- Date range validation requires `end_date > start_date`
- Prepared request preview is shown as normalized JSON

### Important scope guard

This setup workflow does **not** modify Earth Engine science formulas or Module 10.1 interpretation.

---

## Interactive Earth Engine map layers (Module 14)

Module 14 adds live map-layer descriptors for AOI analysis results:

- `POST /api/analyze/map-layers`

### Response contract

- `mode`: `live_earth_engine_map_layers`
- top-level metadata:
  - `study_area`
  - `date_range`
  - `aoi_geometry`
  - `processing_version`
  - `visualization_version`
  - `generated_at`
  - `expires_at`
- ordered `layers` array of raster descriptors
- `warnings` and optional `message`

The AOI boundary is rendered from top-level `aoi_geometry` and is not included as a raster layer in `layers`.

### Initial layer set

Layer descriptors currently include:

1. `gmw_mangrove_extent`
2. `valid_gedi_coverage`
3. `carbon_density`
4. `rh98_canopy_height`

### Scientific consistency

Map layers reuse the same validated pipeline as numeric AOI analysis:

- same AOI geometry and date range
- same GEDI quality/degrade filtering
- same GMW masking
- same shared biomass/carbon image construction
- same processing-version fingerprint

Styling operations (masking/visualization ranges/palettes) do not change scientific numeric outputs.

### Security and caching

- Layer descriptors are cached separately from numeric results.
- Cache key includes canonical geometry, dates, processing fingerprint, and visualization fingerprint.
- Expired descriptors regenerate automatically (default TTL ~20 minutes).
- Tile URLs must be HTTPS and must match allowed hostnames (default `earthengine.googleapis.com`).
- Responses return only safe `tile_url_template` values and layer metadata.
- Raw Earth Engine `token`, `mapid`, and descriptor internals are not returned.

### No-data and partial-data behavior

- Valid no-data AOIs return HTTP 200 with top-level metadata and warnings.
- `layers` may be empty when there is no valid GEDI/GMW coverage.
- No fabricated tiles are returned for no-data AOIs.
- Numeric AOI analysis results remain visible in the UI if map-layer fetching fails.

---

## Export authoritative AOI analysis results (Module 15)

Module 15 adds backend exports for the authoritative AOI analysis results:

- `POST /api/analyze/export/json`
- `POST /api/analyze/export/csv`
- `POST /api/analyze/export/pdf`

All three formats are generated from one shared normalized export document
(`report_schema_version = module15_v1`) and do not recalculate science values in React.

### Shared export schema

The export document includes:

- `report_schema_version`
- `generated_at_utc`
- `processing_mode`
- `processing_version`
- `study_area`
- `date_range` with end-exclusive convention
- `coordinate_order = longitude_latitude`
- `aoi_geometry`
- `aoi_bounds`
- `vertex_count`
- `datasets`
- `results` with units
- `methodology`
- `assumptions`
- `warnings`
- `no_data`

### JSON export

JSON preserves full numeric precision and includes the complete normalized document.
It rejects non-finite values and never includes tile URLs, map IDs, tokens,
credentials, or local filesystem paths.

### CSV export

CSV uses one fixed header row and one data row with a stable column order:

1. `report_schema_version`
2. `generated_at_utc`
3. `processing_mode`
4. `processing_version`
5. `study_area_id`
6. `study_area_name`
7. `start_date`
8. `end_date`
9. `date_convention`
10. `coordinate_order`
11. `aoi_type`
12. `aoi_geometry_json`
13. `aoi_bounds_min_lon`
14. `aoi_bounds_min_lat`
15. `aoi_bounds_max_lon`
16. `aoi_bounds_max_lat`
17. `vertex_count`
18. `datasets_json`
19. `no_data`
20. `warnings_json`
21. `assumptions_json`
22. `methodology_json`
23. `valid_gedi_samples_value`
24. `valid_gedi_samples_unit`
25. `mean_rh98_m_value`
26. `mean_rh98_m_unit`
27. `min_rh98_m_value`
28. `min_rh98_m_unit`
29. `max_rh98_m_value`
30. `max_rh98_m_unit`
31. `mean_agb_mg_ha_value`
32. `mean_agb_mg_ha_unit`
33. `mean_bgb_mg_ha_value`
34. `mean_bgb_mg_ha_unit`
35. `mean_carbon_mg_c_ha_value`
36. `mean_carbon_mg_c_ha_unit`
37. `min_carbon_mg_c_ha_value`
38. `min_carbon_mg_c_ha_unit`
39. `max_carbon_mg_c_ha_value`
40. `max_carbon_mg_c_ha_unit`
41. `mangrove_area_ha_value`
42. `mangrove_area_ha_unit`
43. `gedi_sampled_coverage_percent_value`
44. `gedi_sampled_coverage_percent_unit`
45. `direct_sampled_carbon_mg_c_value`
46. `direct_sampled_carbon_mg_c_unit`
47. `extrapolated_total_carbon_mg_c_value`
48. `extrapolated_total_carbon_mg_c_unit`

Text cells are CSV-formula-injection protected, missing numeric values are blank,
and quoting is applied normally.

### PDF export

The PDF is rendered from the same shared model and includes:

- title and executive summary
- study-area metadata
- date range and end-exclusive statement
- AOI geometry, bounds, and vertex count
- scientific results table with units
- datasets and processing details
- methodology
- assumptions and warnings
- reproducibility metadata
- page numbers

### Security and response headers

Exports return:

- `Content-Type` matching the format
- `Content-Disposition: attachment`
- `X-Content-Type-Options: nosniff`
- `Cache-Control: no-store`

Filenames are sanitized, bounded, and resistant to path traversal and CRLF
injection. Unsupported formats are rejected.

### Frontend download behavior

The Analysis page downloads real blobs, revokes object URLs, aborts in-flight
exports on unmount or AOI edits, and prevents duplicate clicks for one format.
Failed exports do not erase numeric results or map overlays.

### Dependencies

Module 15 uses existing backend libraries and the installed PDF renderer
(`fpdf`) for PDF generation. JSON and CSV are generated with the Python
standard library.

### Verification

Recommended checks:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/ --collect-only -q
.\.venv\Scripts\python -m pytest tests/ -q

cd frontend
npm test -- --run
npm run lint
npm run build
```

### Limitations

- Exports are authoritative snapshots of a successful AOI analysis.
- No-data exports are supported and clearly marked.
- Exports do not include live map-layer tile descriptors or Earth Engine secrets.
