import { forwardRef, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import StudyAreaMap from '../components/analysis/StudyAreaMap'
import StudyAreaSetup from '../components/analysis/StudyAreaSetup'
import { DEFAULT_STUDY_AREA_ID, STUDY_AREAS, STUDY_AREAS_BY_ID } from '../config/studyAreas'
import { buildPreparedAnalysisRequest, buildBackendAnalyzeRequest } from '../services/analysisRequestBuilder'
import {
  ApiError,
  checkCustomAoiMangroveCoverage,
  downloadAoiExport,
  getCarbonStockSummary,
  getGmwLayerOverlay,
  submitAoiMapLayers,
  submitCustomAoiAnalysis,
} from '../services/analysisApi'
import { formatDecimal, formatInteger, formatPercent, withUnit } from '../utils/formatters'
import './Analysis.css'

const STATE = {
  LOADING: 'loading',
  SUCCESS: 'success',
  EMPTY: 'empty',
  ERROR: 'error',
}

const AOI_SUBMISSION_STATE = {
  IDLE: 'idle',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error',
}

const MAP_LAYER_STATE = {
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error',
}

const GMW_OVERLAY_STATE = {
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error',
}

const GMW_COVERAGE_STATE = {
  IDLE: 'idle',
  CHECKING: 'checking',
  HAS_MANGROVES: 'has_mangroves',
  NO_MANGROVES: 'no_mangroves',
  ERROR: 'error',
}

const UNAVAILABLE = 'Unavailable'
const NO_MANGROVES_WARNING =
  'No mapped mangroves were found inside this polygon. Please draw inside the highlighted green areas.'

const ArrowLeftIcon = () => (
  <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" aria-hidden="true">
    <path
      fillRule="evenodd"
      d="M9.707 4.293a1 1 0 010 1.414L6.414 9H17a1 1 0 110 2H6.414l3.293 3.293a1 1 0 11-1.414 1.414l-5-5a1 1 0 010-1.414l5-5a1 1 0 011.414 0z"
      clipRule="evenodd"
    />
  </svg>
)

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value)
}

function formatValue(value, formatter, unit = '') {
  if (!isFiniteNumber(value)) {
    return UNAVAILABLE
  }
  const text = formatter(value)
  return unit ? withUnit(text, unit) : text
}

function getApiErrorMessage(error) {
  if (error instanceof ApiError) {
    return error.message
  }
  return 'Unexpected error while loading carbon stock summary.'
}

function CarbonSummaryCards({ summary }) {
  const cards = [
    {
      label: 'Mapped mangrove area',
      value: formatValue(summary?.area?.mapped_mangrove_area_ha, (v) => formatDecimal(v, 2), 'ha'),
    },
    {
      label: 'GEDI-covered mangrove area',
      value: formatValue(summary?.area?.valid_gedi_raster_coverage_area_ha, (v) => formatDecimal(v, 3), 'ha'),
    },
    {
      label: 'GEDI coverage percentage',
      value: isFiniteNumber(summary?.area?.gedi_raster_coverage_percent)
        ? formatPercent(summary.area.gedi_raster_coverage_percent, 4)
        : UNAVAILABLE,
    },
    {
      label: 'Valid GEDI raster sample count',
      value: formatValue(summary?.carbon_density?.valid_gedi_raster_pixel_count, formatInteger),
    },
    {
      label: 'Mean carbon density',
      value: formatValue(summary?.carbon_density?.mean_mg_c_ha, (v) => formatDecimal(v, 4), 'Mg C/ha'),
    },
    {
      label: 'Direct sampled carbon stock',
      value: formatValue(summary?.stock?.direct_sampled_raster_carbon_mg_c, (v) => formatDecimal(v, 2), 'Mg C'),
    },
    {
      label: 'Extrapolated ecosystem carbon stock',
      value: formatValue(summary?.stock?.extrapolated_ecosystem_carbon_mg_c, (v) => formatDecimal(v, 2), 'Mg C'),
    },
    {
      label: 'Validated reference result',
      value: formatValue(summary?.reference_comparison?.older_reported_direct_sampled_carbon_mg_c, (v) => formatDecimal(v, 2), 'Mg C'),
    },
    {
      label: 'Difference from validated reference',
      value: formatValue(summary?.reference_comparison?.difference_from_older_report_mg_c, (v) => formatDecimal(v, 2), 'Mg C'),
    },
  ]

  return (
    <section className="stock-cards" aria-label="Carbon stock summary cards">
      {cards.map((card) => (
        <article className="stock-card" key={card.label}>
          <h3 className="stock-card-label">{card.label}</h3>
          <p className="stock-card-value">{card.value}</p>
        </article>
      ))}
    </section>
  )
}

function ResultGroup({ title, description, children }) {
  return (
    <section className="result-group">
      <div className="result-group-header">
        <div>
          <h3 className="result-group-title">{title}</h3>
          {description && <p className="result-group-desc">{description}</p>}
        </div>
      </div>
      <div className="stock-cards stock-cards-grouped">{children}</div>
    </section>
  )
}

function GediCoverageViz({ summary }) {
  const coverage = summary?.area?.gedi_raster_coverage_percent
  const clampedCoverage = isFiniteNumber(coverage) ? Math.min(100, Math.max(0, coverage)) : null
  const mappedArea = summary?.area?.mapped_mangrove_area_ha
  const coveredArea = summary?.area?.valid_gedi_raster_coverage_area_ha

  // Scale the bar so even tiny coverage (e.g. 0.07%) is legible.
  // The bar is log-scaled: a minimum visible width of 2% is shown whenever
  // coverage > 0, and the remaining width grows logarithmically up to 100%.
  let barWidth = 0
  if (clampedCoverage !== null && clampedCoverage > 0) {
    const MIN_VISIBLE = 2
    const logScale = Math.log10(clampedCoverage + 1) / Math.log10(101)
    barWidth = MIN_VISIBLE + logScale * (100 - MIN_VISIBLE)
    barWidth = Math.min(100, barWidth)
  }

  return (
    <section className="viz-panel" aria-labelledby="gedi-coverage-title">
      <h3 id="gedi-coverage-title">GEDI coverage visualization</h3>
      <p className="viz-subtitle">
        Coverage is shown as GEDI-covered mangrove area relative to total mapped mangrove area.
        Bar uses a logarithmic scale so sparse coverage remains visible.
      </p>
      <div className="coverage-track" role="img" aria-label={isFiniteNumber(clampedCoverage) ? `GEDI raster coverage is ${formatPercent(clampedCoverage, 4)} of mapped mangrove area.` : 'GEDI coverage percentage is unavailable.'}>
        <span className="coverage-fill" style={{ width: `${barWidth}%` }} />
      </div>
      <p className="viz-meta">
        {formatValue(coveredArea, (v) => formatDecimal(v, 3), 'ha')} of {formatValue(mappedArea, (v) => formatDecimal(v, 2), 'ha')} ({isFiniteNumber(clampedCoverage) ? formatPercent(clampedCoverage, 4) : UNAVAILABLE})
      </p>
    </section>
  )
}

function CarbonStockViz({ summary }) {
  const direct = summary?.stock?.direct_sampled_raster_carbon_mg_c
  const reference = summary?.reference_comparison?.older_reported_direct_sampled_carbon_mg_c
  const extrapolated = summary?.stock?.extrapolated_ecosystem_carbon_mg_c
  const maxDirectReference = Math.max(isFiniteNumber(direct) ? direct : 0, isFiniteNumber(reference) ? reference : 0, 1)
  const directWidth = isFiniteNumber(direct) ? (direct / maxDirectReference) * 100 : 0
  const referenceWidth = isFiniteNumber(reference) ? (reference / maxDirectReference) * 100 : 0

  return (
    <section className="viz-panel" aria-labelledby="stock-viz-title">
      <h3 id="stock-viz-title">Carbon stock visualization</h3>
      <p className="viz-subtitle">
        Direct sampled and validated reference values share one comparison scale; extrapolated ecosystem stock is shown separately to avoid misleading compression.
      </p>

      <div className="stock-compare-grid">
        <article className="stock-compare-card">
          <h4>Direct sampled vs validated reference</h4>
          <div className="bar-row">
            <span className="bar-label">Direct sampled</span>
            <div className="bar-track"><span className="bar-fill direct" style={{ width: `${Math.min(100, Math.max(0, directWidth))}%` }} /></div>
            <span className="bar-value">{formatValue(direct, (v) => formatDecimal(v, 2), 'Mg C')}</span>
          </div>
          <div className="bar-row">
            <span className="bar-label">Validated reference</span>
            <div className="bar-track"><span className="bar-fill reference" style={{ width: `${Math.min(100, Math.max(0, referenceWidth))}%` }} /></div>
            <span className="bar-value">{formatValue(reference, (v) => formatDecimal(v, 2), 'Mg C')}</span>
          </div>
        </article>

        <article className="stock-compare-card">
          <h4>Extrapolated ecosystem stock (separate scale)</h4>
          <p className="extrapolated-value">{formatValue(extrapolated, (v) => formatDecimal(v, 2), 'Mg C')}</p>
          <p className="extrapolated-note">
            Displayed on its own scale because extrapolated stock represents full mapped mangrove extent and is not directly equivalent to sampled-area totals.
          </p>
        </article>
      </div>
    </section>
  )
}

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || 'mangrove_carbon_export'
  document.body.appendChild(a)
  try {
   a.click()
  } finally {
   document.body.removeChild(a)
   URL.revokeObjectURL(url)
  }
}

const EXPORT_FORMATS = [
  { id: 'json', label: 'JSON' },
  { id: 'csv', label: 'CSV' },
  { id: 'pdf', label: 'PDF' },
]

function ExportButtons({ exportStates, exportErrors, onExport }) {
  return (
    <div className="export-buttons" aria-label="Export analysis results">
      <span className="export-label">Download results:</span>
      {EXPORT_FORMATS.map(({ id, label }) => {
        const state = exportStates[id] || 'idle'
        const error = exportErrors[id] || ''
        return (
          <span key={id} className="export-format-group">
            <button
              type="button"
              className={`export-btn export-btn-${id}`}
              onClick={() => onExport(id)}
              disabled={state === 'loading'}
              aria-label={`Download ${label} export`}
            >
              {state === 'loading' ? `${label}…` : label}
            </button>
            {error && (
              <span className="export-error" role="alert">
                {error}
              </span>
            )}
          </span>
        )
      })}
    </div>
  )
}

const AoiAnalysisResults = forwardRef(function AoiAnalysisResults(
  {
    aoiResult,
    submissionState,
    onRetry,
    onClearResults,
    showExportControls,
    exportStates,
    exportErrors,
    onExport,
  },
  ref,
) {
  const studyAreaLabel = aoiResult?.study_area?.name || 'Unknown AOI'
  const dateRange = aoiResult?.date_range
   ? `${aoiResult.date_range.start_date} to ${aoiResult.date_range.end_date}`
   : 'Unknown date range'
  const results = aoiResult?.results || null
  const assumptions = Array.isArray(aoiResult?.assumptions) ? aoiResult.assumptions : []
  const statusLabel =
   submissionState === AOI_SUBMISSION_STATE.ERROR
     ? 'Error'
     : submissionState === AOI_SUBMISSION_STATE.SUBMITTING
       ? 'Loading'
       : results
         ? 'Success'
         : 'No data'

  const coverageCards = [
   {
     label: 'Mapped mangrove area',
     value: formatValue(results?.mangrove_area_ha, (v) => formatDecimal(v, 2), 'ha'),
     note: 'Total mapped area within the submitted AOI.',
   },
   {
     label: 'GEDI-covered area',
     value: formatValue(
       isFiniteNumber(results?.gedi_sampled_coverage_area_ha)
         ? results.gedi_sampled_coverage_area_ha
         : isFiniteNumber(results?.mangrove_area_ha) && isFiniteNumber(results?.gedi_sampled_coverage_percent)
           ? (results.mangrove_area_ha * results.gedi_sampled_coverage_percent) / 100
           : null,
       (v) => formatDecimal(v, 3),
       'ha',
     ),
     note: 'Valid raster cells with GEDI coverage.',
   },
   {
     label: 'Coverage percentage',
     value: isFiniteNumber(results?.gedi_sampled_coverage_percent)
       ? formatPercent(results.gedi_sampled_coverage_percent, 4)
       : UNAVAILABLE,
     note: 'Share of mapped mangrove area with valid GEDI coverage.',
   },
   {
     label: 'Valid GEDI count',
     value: formatValue(results?.valid_gedi_samples, formatInteger),
     note: 'Number of valid raster cells contributing to the analysis.',
   },
  ]

  const biomassCards = [
   {
     label: 'Mean RH98',
     value: formatValue(results?.mean_rh98_m, (v) => formatDecimal(v, 4), 'm'),
     note: 'GEDI canopy-height proxy used in the biomass equation.',
   },
   {
     label: 'Mean AGB',
     value: formatValue(results?.mean_agb_mg_ha, (v) => formatDecimal(v, 4), 'Mg/ha'),
     note: 'Above-ground biomass derived from RH98.',
   },
   {
     label: 'Mean BGB',
     value: formatValue(results?.mean_bgb_mg_ha, (v) => formatDecimal(v, 4), 'Mg/ha'),
     note: 'Below-ground biomass estimated from AGB.',
   },
  ]

  const carbonCards = [
   {
     label: 'Mean carbon density',
     value: formatValue(results?.mean_carbon_mg_c_ha, (v) => formatDecimal(v, 4), 'Mg C/ha'),
     note: 'Area-weighted mean carbon density for valid GEDI cells.',
   },
   {
     label: 'Direct sampled carbon',
     value: formatValue(results?.direct_sampled_carbon_mg_c, (v) => formatDecimal(v, 2), 'Mg C'),
     note: 'Sum over valid GEDI-covered carbon raster cells.',
   },
   {
     label: 'Extrapolated total carbon',
     value: formatValue(results?.extrapolated_total_carbon_mg_c, (v) => formatDecimal(v, 2), 'Mg C'),
     note: 'Mean carbon density projected across the mapped mangrove area.',
   },
  ]

  return (
   <section className="aoi-analysis-results" aria-labelledby="aoi-results-title" tabIndex="-1" ref={ref}>
     <div className="aoi-results-header">
       <div className="aoi-results-heading">
         <div className="eyebrow-row">
           <span className={`status-chip status-chip-${submissionState === AOI_SUBMISSION_STATE.ERROR ? 'error' : submissionState === AOI_SUBMISSION_STATE.SUBMITTING ? 'loading' : results ? 'success' : 'warning'}`}>
             {statusLabel}
           </span>
           <span className="status-chip status-chip-secondary">{aoiResult?.mode || 'live_earth_engine_custom_aoi'}</span>
         </div>
         <h2 id="aoi-results-title" className="panel-title">AOI Analysis Results</h2>
         <p className="aoi-results-subtitle">
           <strong>{studyAreaLabel}</strong> • {dateRange}
         </p>
         <p className="aoi-processing-mode">Processing mode: <strong>{aoiResult?.mode || 'live_earth_engine_custom_aoi'}</strong></p>
         <p className="aoi-processing-mode">Date filter convention: <strong>end date is exclusive</strong></p>
       </div>
       <div className="aoi-results-actions">
         {(submissionState === AOI_SUBMISSION_STATE.SUCCESS || submissionState === AOI_SUBMISSION_STATE.ERROR) && (
            <button
              type="button"
              className="retry-btn"
              onClick={onRetry}
              disabled={submissionState === AOI_SUBMISSION_STATE.SUBMITTING}
            >
              Re-run analysis
            </button>
          )}
          <button type="button" className="clear-results-btn" onClick={onClearResults} disabled={submissionState === AOI_SUBMISSION_STATE.SUBMITTING}>
            Clear results
          </button>
        </div>
      </div>

      {submissionState === AOI_SUBMISSION_STATE.SUCCESS && showExportControls && (
        <ExportButtons
          exportStates={exportStates}
          exportErrors={exportErrors}
          onExport={onExport}
        />
      )}

      {submissionState === AOI_SUBMISSION_STATE.SUBMITTING && (
        <div className="state-panel" role="status" aria-live="polite">
          <p className="state-title">Submitting to Earth Engine…</p>
          <p className="state-desc">This may take a moment depending on the AOI size and date range.</p>
          <div className="skeleton-grid" aria-hidden="true">
            <span className="skeleton-box" />
            <span className="skeleton-box" />
            <span className="skeleton-box" />
          </div>
        </div>
      )}

      {submissionState === AOI_SUBMISSION_STATE.ERROR && (
        <div className="state-panel error" role="alert">
          <p className="state-title">{aoiResult?.error_message || 'AOI analysis failed.'}</p>
        </div>
      )}

      {submissionState === AOI_SUBMISSION_STATE.SUCCESS && results && (
        <>
          <div className="result-groups">
            <ResultGroup title="Coverage" description="Mapped mangrove area and the valid GEDI footprint coverage used in the sample-backed stock calculation.">
              {coverageCards.map((card) => (
                <article className="stock-card" key={card.label}>
                  <h3 className="stock-card-label">{card.label}</h3>
                  <p className="stock-card-value">{card.value}</p>
                  <p className="stock-card-note">{card.note}</p>
                </article>
              ))}
            </ResultGroup>

            <ResultGroup title="Biomass" description="Canopy height and biomass intermediates computed before carbon conversion.">
              {biomassCards.map((card) => (
                <article className="stock-card" key={card.label}>
                  <h3 className="stock-card-label">{card.label}</h3>
                  <p className="stock-card-value">{card.value}</p>
                  <p className="stock-card-note">{card.note}</p>
                </article>
              ))}
            </ResultGroup>

            <ResultGroup title="Carbon" description="Directly sampled carbon versus the full-area extrapolated estimate.">
              {carbonCards.map((card) => (
                <article className="stock-card" key={card.label}>
                  <h3 className="stock-card-label">{card.label}</h3>
                  <p className="stock-card-value">{card.value}</p>
                  <p className="stock-card-note">{card.note}</p>
                </article>
              ))}
            </ResultGroup>
          </div>

          {aoiResult?.warning && (
            <div className="method-note" role="status" aria-live="polite">
              {aoiResult.warning}
            </div>
          )}

          {assumptions.length > 0 && (
            <section className="method-panel" aria-label="AOI assumptions">
              <h3>AOI assumptions</h3>
              <ul>
                {assumptions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      {submissionState === AOI_SUBMISSION_STATE.SUCCESS && !results && (
        <div className="state-panel empty" role="status" aria-live="polite">
          <p className="state-title">No mangrove or GEDI data was returned for this selection.</p>
          <p>{aoiResult?.warning || 'No-data response received from Earth Engine processing.'}</p>
        </div>
      )}
    </section>
  )
})

function Methodology({ summary }) {
  return (
    <section className="method-panel" aria-labelledby="method-title">
      <h3 id="method-title">Scientific methodology</h3>
      <ul>
        <li>Mapped mangrove area is taken from the GMW mangrove extent.</li>
        <li>GEDI-covered area is the sum of <code>ee.Image.pixelArea()</code> over valid carbon raster cells.</li>
        <li>Direct sampled carbon stock represents valid GEDI-covered mangrove pixels only.</li>
        <li>Mean carbon density is reported in Mg C/ha.</li>
        <li>Extrapolated ecosystem carbon stock uses the full-precision backend mean carbon density and mapped mangrove area.</li>
        <li>Approximately 1,480.37 Mg C is reproduced by the live Earth Engine area-weighted calculation and treated as validated.</li>
        <li>The earlier 70.625 ha estimate came from 1130 × 625 m² fixed-cell assumption; the authoritative geographic-grid area is approximately 64.293 ha.</li>
        <li>This dashboard displays backend calculations and does not independently recompute scientific stock results in React.</li>
      </ul>
      {summary?.reference_comparison?.note && <p className="method-note">{summary.reference_comparison.note}</p>}
    </section>
  )
}

const MANGROVE_INFO = {
  indus_delta: {
    headline: 'Grey Mangrove (Avicennia marina) dominates the Indus Delta.',
    detail:
      'Avicennia marina is the primary species across this region, forming dense salt-tolerant stands along tidal channels. Other coastal regions host Red Mangrove (Rhizophora) and Spurred Mangrove (Ceriops).',
  },
  abu_dhabi: {
    headline: 'Grey Mangrove (Avicennia marina) is the main mangrove of Abu Dhabi.',
    detail:
      'A. marina thrives in the hyper-arid, high-salinity conditions of the Arabian Gulf. Other mangrove types such as Red Mangrove (Rhizophora) and Spurred Mangrove (Ceriops) occur in wetter tropical coasts.',
  },
  custom: {
    headline: 'Mangrove species vary by region.',
    detail:
      'This analysis uses Global Mangrove Watch extent data. Dominant species in your drawn area may include Grey Mangrove (Avicennia marina), Red Mangrove (Rhizophora), or Spurred Mangrove (Ceriops) depending on climate and salinity.',
  },
}

function MangroveInfoCard({ studyAreaMode, selectedRegionId }) {
  const key = studyAreaMode === 'custom' ? 'custom' : (selectedRegionId in MANGROVE_INFO ? selectedRegionId : 'custom')
  const info = MANGROVE_INFO[key]
  return (
    <aside className="mangrove-info-card" aria-label="Mangrove species information">
      <span className="mangrove-info-icon" aria-hidden="true">🌿</span>
      <div className="mangrove-info-body">
        <p className="mangrove-info-headline">{info.headline}</p>
        <p className="mangrove-info-detail">{info.detail}</p>
      </div>
    </aside>
  )
}

function Analysis() {
  const [state, setState] = useState(STATE.LOADING)
  const [summary, setSummary] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [emptyMessage, setEmptyMessage] = useState('')
  const [studyAreaMode, setStudyAreaMode] = useState('predefined')
  const [selectedRegionId, setSelectedRegionId] = useState(DEFAULT_STUDY_AREA_ID)
  const [customAoi, setCustomAoi] = useState(null)
  const [startDate, setStartDate] = useState(
    STUDY_AREAS_BY_ID[DEFAULT_STUDY_AREA_ID]?.defaultStartDate ?? '2020-01-01'
  )
  const [endDate, setEndDate] = useState(
    STUDY_AREAS_BY_ID[DEFAULT_STUDY_AREA_ID]?.defaultEndDate ?? '2020-04-01'
  )
  const [aoiSubmissionState, setAoiSubmissionState] = useState(AOI_SUBMISSION_STATE.IDLE)
  const [aoiResult, setAoiResult] = useState(null)
  const [exportStates, setExportStates] = useState({})
  const [exportErrors, setExportErrors] = useState({})
  const [mapLayerState, setMapLayerState] = useState(MAP_LAYER_STATE.IDLE)
  const [mapLayerDescriptors, setMapLayerDescriptors] = useState([])
  const [mapLayerWarnings, setMapLayerWarnings] = useState([])
  const [mapLayerMessage, setMapLayerMessage] = useState('')
  const [mapLayerVisibilityById, setMapLayerVisibilityById] = useState({})
  const [mapLayerOpacityById, setMapLayerOpacityById] = useState({})
  const [gmwOverlayState, setGmwOverlayState] = useState(GMW_OVERLAY_STATE.IDLE)
  const [gmwOverlayError, setGmwOverlayError] = useState('')
  const [gmwOverlayTileUrl, setGmwOverlayTileUrl] = useState('')
  const [gmwOverlayOpacity, setGmwOverlayOpacity] = useState(0.5)
  const [showGmwOverlay, setShowGmwOverlay] = useState(true)
  const [gmwCoverageState, setGmwCoverageState] = useState(GMW_COVERAGE_STATE.IDLE)
  const [customAoiCoverageWarning, setCustomAoiCoverageWarning] = useState('')
  const [submittedAoiRequestSignature, setSubmittedAoiRequestSignature] = useState(null)
  const aoiResultsSectionRef = useRef(null)
  const isMountedRef = useRef(false)
  const requestControllerRef = useRef(null)
  const latestRequestIdRef = useRef(0)
  const aoiSubmissionControllerRef = useRef(null)
  const latestAoiRequestIdRef = useRef(0)
  const mapLayerControllerRef = useRef(null)
  const latestMapLayerRequestIdRef = useRef(0)
  const gmwOverlayControllerRef = useRef(null)
  const latestGmwOverlayRequestIdRef = useRef(0)
  const gmwCoverageControllerRef = useRef(null)
  const latestGmwCoverageRequestIdRef = useRef(0)
  const exportControllerRefs = useRef({})
  const latestExportRequestIdsRef = useRef({})

  const selectedRegion = STUDY_AREAS_BY_ID[selectedRegionId] ?? STUDY_AREAS_BY_ID[DEFAULT_STUDY_AREA_ID]
  const predefinedAoi = selectedRegion?.geometry ?? null
  const activeAoi = studyAreaMode === 'custom' ? customAoi : predefinedAoi

  const handleRegionChange = (regionId) => {
    setSelectedRegionId(regionId)
    const region = STUDY_AREAS_BY_ID[regionId]
    if (region?.defaultStartDate) setStartDate(region.defaultStartDate)
    if (region?.defaultEndDate) setEndDate(region.defaultEndDate)
  }

  const preparedRequest = useMemo(
    () =>
      buildPreparedAnalysisRequest({
        studyAreaMode,
        selectedRegion,
        predefinedAoi,
        customAoi,
        startDate,
        endDate,
      }),
    [studyAreaMode, selectedRegion, predefinedAoi, customAoi, startDate, endDate],
  )
  const preparedRequestIsValid = preparedRequest.isValid
  const preparedBackendRequest = useMemo(
    () => buildBackendAnalyzeRequest(preparedRequest.requestPreview),
    [preparedRequest.requestPreview],
  )
  const preparedRequestSignature = useMemo(
    () => (preparedBackendRequest ? JSON.stringify(preparedBackendRequest) : null),
    [preparedBackendRequest],
  )
  const setupValidationErrors = useMemo(
    () => (
      customAoiCoverageWarning
        ? [...preparedRequest.errors, customAoiCoverageWarning]
        : preparedRequest.errors
    ),
    [preparedRequest.errors, customAoiCoverageWarning],
  )

  const clearMapLayers = useCallback(() => {
    if (mapLayerControllerRef.current) {
      mapLayerControllerRef.current.abort()
      mapLayerControllerRef.current = null
    }
    setMapLayerState(MAP_LAYER_STATE.IDLE)
    setMapLayerDescriptors([])
    setMapLayerWarnings([])
    setMapLayerMessage('')
    setMapLayerVisibilityById({})
    setMapLayerOpacityById({})
  }, [])

  const loadMapLayers = useCallback(async (backendRequest) => {
    if (mapLayerControllerRef.current) {
      mapLayerControllerRef.current.abort()
    }
    const requestId = latestMapLayerRequestIdRef.current + 1
    latestMapLayerRequestIdRef.current = requestId
    const controller = new AbortController()
    mapLayerControllerRef.current = controller
    setMapLayerState(MAP_LAYER_STATE.LOADING)
    setMapLayerMessage('Loading Earth Engine map layers…')
    try {
      const payload = await submitAoiMapLayers(backendRequest, { signal: controller.signal })
      if (!isMountedRef.current || controller.signal.aborted || latestMapLayerRequestIdRef.current !== requestId) {
        return
      }
      const descriptors = Array.isArray(payload.layers) ? payload.layers : []
      setMapLayerDescriptors(descriptors)
      setMapLayerWarnings(Array.isArray(payload.warnings) ? payload.warnings : [])
      setMapLayerMessage(payload.message || '')
      const nextVisibility = {}
      const nextOpacity = {}
      for (const layer of descriptors) {
        nextVisibility[layer.id] = Boolean(layer.default_visible)
        nextOpacity[layer.id] = typeof layer.default_opacity === 'number' ? layer.default_opacity : 1
      }
      setMapLayerVisibilityById(nextVisibility)
      setMapLayerOpacityById(nextOpacity)
      setMapLayerState(MAP_LAYER_STATE.SUCCESS)
    } catch (error) {
      if ((error instanceof ApiError && error.code === 'request_aborted') || controller.signal.aborted) {
        return
      }
      if (!isMountedRef.current || latestMapLayerRequestIdRef.current !== requestId) {
        return
      }
      setMapLayerState(MAP_LAYER_STATE.ERROR)
      setMapLayerDescriptors([])
      setMapLayerWarnings([])
      setMapLayerMessage(getApiErrorMessage(error))
    } finally {
      if (latestMapLayerRequestIdRef.current === requestId && mapLayerControllerRef.current === controller) {
        mapLayerControllerRef.current = null
      }
    }
  }, [])

  const loadSummary = useCallback(async () => {
    if (requestControllerRef.current) {
      requestControllerRef.current.abort()
    }

    const requestId = latestRequestIdRef.current + 1
    latestRequestIdRef.current = requestId
    const controller = new AbortController()
    requestControllerRef.current = controller
    setState(STATE.LOADING)
    setErrorMessage('')
    setEmptyMessage('')

    try {
      const payload = await getCarbonStockSummary({ signal: controller.signal })
      if (!isMountedRef.current || controller.signal.aborted || latestRequestIdRef.current !== requestId) {
        return
      }

      const hasCompleteData = payload.status === 'connected' && payload.carbon_density && payload.area && payload.stock
      if (hasCompleteData) {
        setSummary(payload)
        setState(STATE.SUCCESS)
      } else {
        setSummary(payload)
        setEmptyMessage(payload.message || 'Carbon stock information is currently unavailable.')
        setState(STATE.EMPTY)
      }
    } catch (error) {
      if ((error instanceof ApiError && error.code === 'request_aborted') || controller.signal.aborted) {
        return
      }
      if (!isMountedRef.current || latestRequestIdRef.current !== requestId) {
        return
      }
      setSummary(null)
      setErrorMessage(getApiErrorMessage(error))
      setState(STATE.ERROR)
    } finally {
      if (latestRequestIdRef.current === requestId && requestControllerRef.current === controller) {
        requestControllerRef.current = null
      }
    }
  }, [])

  const loadGmwOverlay = useCallback(async () => {
    if (gmwOverlayControllerRef.current) {
      gmwOverlayControllerRef.current.abort()
    }

    const requestId = latestGmwOverlayRequestIdRef.current + 1
    latestGmwOverlayRequestIdRef.current = requestId
    const controller = new AbortController()
    gmwOverlayControllerRef.current = controller
    setGmwOverlayState(GMW_OVERLAY_STATE.LOADING)
    setGmwOverlayError('')

    // Always use the global GMW mask ('custom') for the visual overlay so that
    // mangroves are visible worldwide — not just within the selected region's asset.
    // The analysis pipeline uses the region-specific asset separately.
    const studyArea = 'custom'

    try {
      const payload = await getGmwLayerOverlay({ studyArea, signal: controller.signal })
      if (!isMountedRef.current || controller.signal.aborted || latestGmwOverlayRequestIdRef.current !== requestId) {
        return
      }
      setGmwOverlayTileUrl(payload.tile_url_template)
      setGmwOverlayOpacity(typeof payload.default_opacity === 'number' ? payload.default_opacity : 0.5)
      setShowGmwOverlay(Boolean(payload.default_visible))
      setGmwOverlayState(GMW_OVERLAY_STATE.SUCCESS)
    } catch (error) {
      if ((error instanceof ApiError && error.code === 'request_aborted') || controller.signal.aborted) {
        return
      }
      if (!isMountedRef.current || latestGmwOverlayRequestIdRef.current !== requestId) {
        return
      }
      setGmwOverlayState(GMW_OVERLAY_STATE.ERROR)
      setGmwOverlayError(getApiErrorMessage(error))
      setGmwOverlayTileUrl('')
    } finally {
      if (latestGmwOverlayRequestIdRef.current === requestId && gmwOverlayControllerRef.current === controller) {
        gmwOverlayControllerRef.current = null
      }
    }
  }, [])

  const submitAoiAnalysis = useCallback(async () => {
    if (!preparedRequestIsValid || customAoiCoverageWarning) {
      return
    }

    if (aoiSubmissionControllerRef.current) {
      aoiSubmissionControllerRef.current.abort()
    }

    const requestId = latestAoiRequestIdRef.current + 1
    latestAoiRequestIdRef.current = requestId
    const controller = new AbortController()
    aoiSubmissionControllerRef.current = controller
    setAoiSubmissionState(AOI_SUBMISSION_STATE.SUBMITTING)

    try {
      const backendRequest = preparedBackendRequest
      if (!backendRequest) {
        throw new ApiError('Failed to build analysis request.')
      }

      const response = await submitCustomAoiAnalysis(backendRequest, { signal: controller.signal })
      
      if (!isMountedRef.current || controller.signal.aborted || latestAoiRequestIdRef.current !== requestId) {
        return
      }

      setAoiResult(response)
      setAoiSubmissionState(AOI_SUBMISSION_STATE.SUCCESS)
      const signature = JSON.stringify(backendRequest)
      setSubmittedAoiRequestSignature(signature)
      await loadMapLayers(backendRequest)
    } catch (error) {
      if ((error instanceof ApiError && error.code === 'request_aborted') || controller.signal.aborted) {
        return
      }
      if (!isMountedRef.current || latestAoiRequestIdRef.current !== requestId) {
        return
      }
      setAoiResult({
        error_message: getApiErrorMessage(error),
      })
      setAoiSubmissionState(AOI_SUBMISSION_STATE.ERROR)
      clearMapLayers()
    } finally {
      if (latestAoiRequestIdRef.current === requestId && aoiSubmissionControllerRef.current === controller) {
        aoiSubmissionControllerRef.current = null
      }
    }
  }, [preparedRequestIsValid, preparedBackendRequest, loadMapLayers, clearMapLayers, customAoiCoverageWarning])

  const retryAoiAnalysis = useCallback(async () => {
    await submitAoiAnalysis()
  }, [submitAoiAnalysis])

  const abortExportRequests = useCallback(() => {
    const controllers = exportControllerRefs.current
    Object.keys(controllers).forEach((format) => {
      const controller = controllers[format]
      if (controller) {
        controller.abort()
      }
    })
    exportControllerRefs.current = {}
    latestExportRequestIdsRef.current = {}
  }, [])

  const clearAoiResults = useCallback(() => {
    abortExportRequests()
    setAoiResult(null)
    setAoiSubmissionState(AOI_SUBMISSION_STATE.IDLE)
    setSubmittedAoiRequestSignature(null)
    setExportStates({})
    setExportErrors({})
    clearMapLayers()
  }, [abortExportRequests, clearMapLayers])

  const handleExport = useCallback(async (format) => {
    if (
      !preparedBackendRequest ||
      !submittedAoiRequestSignature ||
      preparedRequestSignature !== submittedAoiRequestSignature ||
      aoiSubmissionState !== AOI_SUBMISSION_STATE.SUCCESS
    ) {
      return
    }

    if (exportControllerRefs.current[format]) {
      exportControllerRefs.current[format].abort()
    }

    const requestId = (latestExportRequestIdsRef.current[format] || 0) + 1
    latestExportRequestIdsRef.current = {
      ...latestExportRequestIdsRef.current,
      [format]: requestId,
    }

    const controller = new AbortController()
    exportControllerRefs.current = {
      ...exportControllerRefs.current,
      [format]: controller,
    }

    const requestSignature = submittedAoiRequestSignature
    setExportStates((prev) => ({ ...prev, [format]: 'loading' }))
    setExportErrors((prev) => ({ ...prev, [format]: '' }))

    try {
      const { blob, filename } = await downloadAoiExport(format, preparedBackendRequest, { signal: controller.signal })
      const isCurrentRequest =
        isMountedRef.current &&
        !controller.signal.aborted &&
        latestExportRequestIdsRef.current[format] === requestId &&
        submittedAoiRequestSignature === requestSignature &&
        preparedRequestSignature === requestSignature

      if (!isCurrentRequest) {
        return
      }

      triggerBlobDownload(blob, filename)
      setExportStates((prev) => ({ ...prev, [format]: 'idle' }))
    } catch (error) {
      if (error instanceof ApiError && error.code === 'request_aborted') {
        return
      }
      if (!isMountedRef.current || controller.signal.aborted || latestExportRequestIdsRef.current[format] !== requestId) {
        return
      }
      setExportStates((prev) => ({ ...prev, [format]: 'error' }))
      setExportErrors((prev) => ({ ...prev, [format]: getApiErrorMessage(error) }))
    } finally {
      if (exportControllerRefs.current[format] === controller) {
        const nextControllers = { ...exportControllerRefs.current }
        delete nextControllers[format]
        exportControllerRefs.current = nextControllers
      }
    }
  }, [aoiSubmissionState, preparedBackendRequest, preparedRequestSignature, submittedAoiRequestSignature])

  const toggleMapLayer = useCallback((layerId, checked) => {
    setMapLayerVisibilityById((prev) => ({ ...prev, [layerId]: checked }))
  }, [])

  const changeMapLayerOpacity = useCallback((layerId, opacity) => {
    setMapLayerOpacityById((prev) => ({ ...prev, [layerId]: opacity }))
  }, [])

  const resetMapLayerDefaults = useCallback(() => {
    const nextVisibility = {}
    const nextOpacity = {}
    for (const layer of mapLayerDescriptors) {
      nextVisibility[layer.id] = Boolean(layer.default_visible)
      nextOpacity[layer.id] = typeof layer.default_opacity === 'number' ? layer.default_opacity : 1
    }
    setMapLayerVisibilityById(nextVisibility)
    setMapLayerOpacityById(nextOpacity)
  }, [mapLayerDescriptors])

  useEffect(() => {
    isMountedRef.current = true
    loadSummary()
    return () => {
      isMountedRef.current = false
      abortExportRequests()
      if (requestControllerRef.current) {
        requestControllerRef.current.abort()
      }
      if (aoiSubmissionControllerRef.current) {
        aoiSubmissionControllerRef.current.abort()
      }
      if (mapLayerControllerRef.current) {
        mapLayerControllerRef.current.abort()
      }
      if (gmwOverlayControllerRef.current) {
        gmwOverlayControllerRef.current.abort()
      }
      if (gmwCoverageControllerRef.current) {
        gmwCoverageControllerRef.current.abort()
      }
    }
  }, [abortExportRequests, loadSummary])

  // Load the global GMW overlay once on mount so mangroves are visible
  // worldwide before the user selects a region or runs any analysis.
  useEffect(() => {
    loadGmwOverlay()
  }, [loadGmwOverlay])

  useEffect(() => {
    if (studyAreaMode !== 'custom') {
      setGmwCoverageState(GMW_COVERAGE_STATE.IDLE)
      setCustomAoiCoverageWarning('')
      if (gmwCoverageControllerRef.current) {
        gmwCoverageControllerRef.current.abort()
      }
      return
    }

    if (!customAoi) {
      setGmwCoverageState(GMW_COVERAGE_STATE.IDLE)
      setCustomAoiCoverageWarning('')
      if (gmwCoverageControllerRef.current) {
        gmwCoverageControllerRef.current.abort()
      }
      return
    }

    if (gmwCoverageControllerRef.current) {
      gmwCoverageControllerRef.current.abort()
    }
    const requestId = latestGmwCoverageRequestIdRef.current + 1
    latestGmwCoverageRequestIdRef.current = requestId
    const controller = new AbortController()
    gmwCoverageControllerRef.current = controller
    setGmwCoverageState(GMW_COVERAGE_STATE.CHECKING)
    setCustomAoiCoverageWarning('')

    const runCheck = async () => {
      try {
        const payload = await checkCustomAoiMangroveCoverage(
          {
            study_area: 'custom',
            aoi_geometry: customAoi,
          },
          { signal: controller.signal },
        )
        if (!isMountedRef.current || controller.signal.aborted || latestGmwCoverageRequestIdRef.current !== requestId) {
          return
        }
        if (payload.has_mangroves) {
          setGmwCoverageState(GMW_COVERAGE_STATE.HAS_MANGROVES)
          setCustomAoiCoverageWarning('')
          return
        }
        setGmwCoverageState(GMW_COVERAGE_STATE.NO_MANGROVES)
        setCustomAoiCoverageWarning(NO_MANGROVES_WARNING)
      } catch (error) {
        if ((error instanceof ApiError && error.code === 'request_aborted') || controller.signal.aborted) {
          return
        }
        if (!isMountedRef.current || latestGmwCoverageRequestIdRef.current !== requestId) {
          return
        }
        setGmwCoverageState(GMW_COVERAGE_STATE.ERROR)
        setCustomAoiCoverageWarning('')
      } finally {
        if (latestGmwCoverageRequestIdRef.current === requestId && gmwCoverageControllerRef.current === controller) {
          gmwCoverageControllerRef.current = null
        }
      }
    }

    runCheck()
  }, [studyAreaMode, customAoi])

  useEffect(() => {
    if (!submittedAoiRequestSignature) {
      return
    }
    if (!preparedRequestSignature || preparedRequestSignature === submittedAoiRequestSignature) {
      return
    }
    abortExportRequests()
    setExportStates({})
    setExportErrors({})
    clearMapLayers()
    setMapLayerMessage('Map overlays cleared because AOI/date inputs changed after the last submission.')
  }, [abortExportRequests, clearMapLayers, preparedRequestSignature, submittedAoiRequestSignature])

  const headingSummary = useMemo(() => {
    if (!summary?.study_area || !summary?.date_range) {
      return 'Live Earth Engine carbon stock summary'
    }
    return `${summary.study_area.name} • ${summary.date_range.start_date} to ${summary.date_range.end_date}`
  }, [summary])

  const isAoiResultsStale = Boolean(
    submittedAoiRequestSignature &&
      preparedRequestSignature &&
      preparedRequestSignature !== submittedAoiRequestSignature &&
      aoiSubmissionState !== AOI_SUBMISSION_STATE.IDLE,
  )
  const isRunAnalysisBlockedByCoverage = Boolean(
    studyAreaMode === 'custom'
      && customAoi
      && gmwCoverageState === GMW_COVERAGE_STATE.NO_MANGROVES,
  )

  useEffect(() => {
    if (aoiSubmissionState !== AOI_SUBMISSION_STATE.SUCCESS || !aoiResult || !aoiResultsSectionRef.current) {
      return
    }
    const reduceMotion = typeof window !== 'undefined'
      && window.matchMedia
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (typeof aoiResultsSectionRef.current.scrollIntoView === 'function') {
      aoiResultsSectionRef.current.scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'start',
      })
    }
    if (typeof aoiResultsSectionRef.current.focus === 'function') {
      aoiResultsSectionRef.current.focus({ preventScroll: true })
    }
  }, [aoiSubmissionState, aoiResult])

  return (
    <main className="analysis-page">
      <div className="analysis-shell">
        <header className="analysis-header">
          <div className="analysis-header-copy">
            <Link to="/" className="back-home">
              <ArrowLeftIcon />
              Back to Home
            </Link>
            <div className="analysis-eyebrow-row">
              <span className="analysis-badge">GEDI L2A</span>
              <span className="analysis-badge">Global Mangrove Watch</span>
              <span className="analysis-badge">Google Earth Engine</span>
            </div>
            <h1 className="analysis-title">Mangrove Carbon Analysis</h1>
            <p className="analysis-subtitle">
              Explore live mangrove biomass and carbon estimates powered by Google Earth Engine.
            </p>
          </div>
          <div className="analysis-header-meta">
            {(state === STATE.ERROR || state === STATE.LOADING) && (
              <button type="button" className="retry-btn" onClick={loadSummary} disabled={state === STATE.LOADING}>
                {state === STATE.LOADING ? 'Loading…' : 'Retry'}
              </button>
            )}
          </div>
        </header>

        <section className="analysis-workspace" aria-label="Analysis workspace">
          <div className="analysis-column analysis-column-left">
            <StudyAreaSetup
              studyAreaMode={studyAreaMode}
              selectedRegionId={selectedRegionId}
              regions={STUDY_AREAS}
              startDate={startDate}
              endDate={endDate}
              activeAoi={activeAoi}
              customAoi={customAoi}
              validationErrors={setupValidationErrors}
              onModeChange={setStudyAreaMode}
              onRegionChange={handleRegionChange}
              onStartDateChange={setStartDate}
              onEndDateChange={setEndDate}
              onClearCustomAoi={() => setCustomAoi(null)}
            />

            <MangroveInfoCard studyAreaMode={studyAreaMode} selectedRegionId={selectedRegionId} />

            <section className="request-preview-panel" aria-labelledby="request-preview-title">
              <h2 id="request-preview-title" className="panel-title">Analysis Request Summary</h2>

              {/* Compact human-readable summary card */}
              <dl className="request-summary-grid">
                <div className="request-summary-row">
                  <dt>Study area</dt>
                  <dd>{preparedRequest.requestPreview?.study_area_name ?? '—'}</dd>
                </div>
                <div className="request-summary-row">
                  <dt>Mode</dt>
                  <dd>{preparedRequest.requestPreview?.study_area_mode === 'predefined_region' ? 'Predefined region' : 'Custom AOI'}</dd>
                </div>
                <div className="request-summary-row">
                  <dt>Date range</dt>
                  <dd>
                    {preparedRequest.requestPreview?.start_date ?? '—'}
                    {' to '}
                    {preparedRequest.requestPreview?.end_date ?? '—'}
                    <span className="request-summary-note"> (end-exclusive)</span>
                  </dd>
                </div>
                <div className="request-summary-row">
                  <dt>Geometry</dt>
                  <dd>{preparedRequest.requestPreview?.aoi_geojson?.type ?? '—'}</dd>
                </div>
                <div className="request-summary-row">
                  <dt>Vertices</dt>
                  <dd>
                    {preparedRequest.requestPreview?.aoi_geojson?.coordinates?.[0]
                      ? preparedRequest.requestPreview.aoi_geojson.coordinates[0].length - 1
                      : '—'}
                  </dd>
                </div>
                <div className="request-summary-row">
                  <dt>Validation</dt>
                  <dd className={preparedRequest.isValid ? 'request-summary-valid' : 'request-summary-invalid'}>
                    {preparedRequest.isValid ? '✓ Ready for submission' : '✗ Incomplete input'}
                  </dd>
                </div>
              </dl>

              <div className="request-preview-actions">
                <button
                  type="button"
                  className="run-analysis-btn"
                  onClick={submitAoiAnalysis}
                  disabled={
                    !preparedRequest.isValid
                    || isRunAnalysisBlockedByCoverage
                    || aoiSubmissionState === AOI_SUBMISSION_STATE.SUBMITTING
                  }
                >
                  {aoiSubmissionState === AOI_SUBMISSION_STATE.SUBMITTING ? 'Submitting…' : 'Run Analysis'}
                </button>
              </div>

              {/* Collapsed technical detail — hidden by default */}
              <details className="request-json-disclosure">
                <summary>View technical request JSON</summary>
                <pre className="request-json" aria-label="Prepared request JSON">
                  {JSON.stringify(preparedRequest.requestPreview, null, 2)}
                </pre>
              </details>
            </section>

            {isAoiResultsStale && (
              <div className="state-panel stale" role="status" aria-live="polite">
                <p className="state-title">Inputs changed — run the analysis again to refresh results.</p>
              </div>
            )}
          </div>

          <div className="analysis-column analysis-column-right">
            <StudyAreaMap
              studyAreaMode={studyAreaMode}
              selectedRegion={selectedRegion}
              predefinedAoi={predefinedAoi}
              customAoi={customAoi}
              onCustomAoiChange={setCustomAoi}
              analyzedAoiGeometry={aoiResult?.aoi_geometry || null}
              mapLayers={mapLayerDescriptors}
              mapLayerVisibilityById={mapLayerVisibilityById}
              mapLayerOpacityById={mapLayerOpacityById}
              onToggleMapLayer={toggleMapLayer}
              onChangeMapLayerOpacity={changeMapLayerOpacity}
              onResetMapLayerDefaults={resetMapLayerDefaults}
              mapLayerWarnings={mapLayerWarnings}
              mapLayerMessage={
                mapLayerState === MAP_LAYER_STATE.LOADING
                  ? 'Loading Earth Engine map layers…'
                  : mapLayerMessage
              }
              gmwOverlayTileUrl={gmwOverlayTileUrl}
              gmwOverlayOpacity={gmwOverlayOpacity}
              gmwOverlayVisible={showGmwOverlay}
              onToggleGmwOverlay={setShowGmwOverlay}
              gmwOverlayStatus={gmwOverlayState}
              gmwOverlayError={gmwOverlayError}
              gmwCoverageState={gmwCoverageState}
            />
          </div>
        </section>

        {state === STATE.LOADING && (
          <section className="state-panel" role="status" aria-live="polite">
            <p className="state-title">Loading live carbon stock summary…</p>
            <div className="skeleton-grid" aria-hidden="true">
              <span className="skeleton-box" />
              <span className="skeleton-box" />
              <span className="skeleton-box" />
            </div>
          </section>
        )}

        {state === STATE.ERROR && (
          <section className="state-panel error" role="alert">
            <p className="state-title">Unable to load carbon stock summary.</p>
            <p>{errorMessage}</p>
          </section>
        )}

        {state === STATE.EMPTY && (
          <section className="state-panel empty" role="status" aria-live="polite">
            <p className="state-title">Carbon information is currently unavailable.</p>
            <p>{emptyMessage}</p>
          </section>
        )}

        {state === STATE.SUCCESS && summary && (
          <>
            <details className="reference-panel">
              <summary>
                <div className="reference-summary-copy">
                  <span className="reference-summary-badge">Reference only</span>
                  <h2>Fixed Indus Reference Summary</h2>
                  <p>Validated Indus Delta reference for 2020-01-01 to 2020-04-01. This section does not change with the controls above.</p>
                </div>
              </summary>
              <div className="reference-panel-body">
                <section className="summary-header" aria-label="Summary metadata">
                  <p>{headingSummary}</p>
                  <p>Mode: {summary.mode}</p>
                </section>

                <CarbonSummaryCards summary={summary} />

                <section className="viz-grid">
                  <GediCoverageViz summary={summary} />
                  <CarbonStockViz summary={summary} />
                </section>

                <Methodology summary={summary} />
              </div>
            </details>
          </>
        )}

        {aoiResult && aoiSubmissionState !== AOI_SUBMISSION_STATE.IDLE && (
          <AoiAnalysisResults
            ref={aoiResultsSectionRef}
            aoiResult={aoiResult}
            submissionState={aoiSubmissionState}
            onRetry={retryAoiAnalysis}
            onClearResults={clearAoiResults}
            showExportControls={
              Boolean(submittedAoiRequestSignature) &&
              preparedRequestSignature === submittedAoiRequestSignature &&
              aoiSubmissionState === AOI_SUBMISSION_STATE.SUCCESS
            }
            exportStates={exportStates}
            exportErrors={exportErrors}
            onExport={handleExport}
          />
        )}
      </div>
    </main>
  )
}

export default Analysis
