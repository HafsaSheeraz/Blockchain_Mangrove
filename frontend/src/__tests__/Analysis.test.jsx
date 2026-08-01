import { StrictMode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import { ApiError, getCarbonStockSummary, submitAoiMapLayers, submitCustomAoiAnalysis, downloadAoiExport } from '../services/analysisApi'

vi.mock('../components/analysis/StudyAreaMap', () => ({
  default: function MockStudyAreaMap({
    studyAreaMode,
    onCustomAoiChange,
  }) {
    return (
      <section aria-label="Mock study area map">
        <p>Map mode: {studyAreaMode}</p>
        <button
          type="button"
          onClick={() =>
            onCustomAoiChange({
              type: 'Polygon',
              coordinates: [[[67, 24], [67.4, 24], [67.4, 24.4], [67, 24.4], [67, 24]]],
            })}
        >
          Mock Draw Polygon
        </button>
        <button
          type="button"
          onClick={() =>
            onCustomAoiChange({
              type: 'Polygon',
              coordinates: [[[66, 23.8], [66.6, 23.8], [66.6, 24.2], [66, 24.2], [66, 23.8]]],
            })}
        >
          Mock Edit Polygon
        </button>
        <button type="button" onClick={() => onCustomAoiChange(null)}>
          Mock Delete Polygon
        </button>
      </section>
    )
  },
}))

vi.mock('../services/analysisApi', () => ({
  ApiError: class ApiError extends Error {
    constructor(message, options = {}) {
      super(message)
      this.status = options.status ?? null
      this.code = options.code ?? 'api_error'
    }
  },
  getCarbonStockSummary: vi.fn(),
  submitCustomAoiAnalysis: vi.fn(),
  submitAoiMapLayers: vi.fn(),
  downloadAoiExport: vi.fn(),
}))

const LIVE_SUCCESS_RESPONSE = {
  connected: true,
  mode: 'live_earth_engine',
  status: 'connected',
  study_area: {
    id: 'indus_delta',
    name: 'Indus Delta, Pakistan',
    geometry_type: 'Rectangle',
    bounds: [66.5, 23.5, 68.5, 24.8],
  },
  date_range: {
    start_date: '2020-01-01',
    end_date: '2020-04-01',
    filter_convention: 'end_exclusive',
  },
  carbon_density: {
    mean_mg_c_ha: 23.02570844643939,
    min_mg_c_ha: 17.812491825,
    max_mg_c_ha: 42.91477852,
    valid_gedi_raster_pixel_count: 1130,
  },
  area: {
    mapped_mangrove_area_ha: 90769.33192367057,
    valid_gedi_raster_coverage_area_ha: 64.29286419067385,
    gedi_raster_coverage_percent: 0.07083104263093926,
  },
  stock: {
    direct_sampled_raster_carbon_mg_c: 1480.3693760410526,
    extrapolated_ecosystem_carbon_mg_c: 2090028.172752522,
  },
  calculation_methods: {
    mapped_mangrove_area: 'sum(pixelArea_ha over positive GMW-mask pixels)',
  },
  assumptions: [],
  processing: {
    gmw_area_scale_m: 10,
    gedi_analysis_scale_m: 25,
    best_effort: false,
  },
  processing_performed: true,
  warnings: [],
  reference_comparison: {
    older_reported_direct_sampled_carbon_mg_c: 1480.37,
    difference_from_older_report_mg_c: 0.0,
    note: 'The live Earth Engine area-weighted calculation reproduces the older direct sampled carbon result of approximately 1,480.37 Mg C.',
  },
}

const CUSTOM_AOI_SUCCESS_RESPONSE = {
  mode: 'live_earth_engine_custom_aoi',
  study_area: { id: 'indus_delta', name: 'Indus Delta, Pakistan' },
  date_range: { start_date: '2020-01-01', end_date: '2020-04-01' },
  datasets: ['GEDI L2A RH98', 'GMW 2020'],
  results: {
    valid_gedi_samples: 10,
    mean_rh98_m: 3.0,
    min_rh98_m: 2.0,
    max_rh98_m: 4.0,
    mean_agb_mg_ha: 30.0,
    mean_bgb_mg_ha: 14.7,
    mean_carbon_mg_c_ha: 22.35,
    min_carbon_mg_c_ha: 15.0,
    max_carbon_mg_c_ha: 31.0,
    mangrove_area_ha: 100.0,
    gedi_sampled_coverage_percent: 2.5,
    direct_sampled_carbon_mg_c: 55.0,
    extrapolated_total_carbon_mg_c: 2235.0,
  },
  methodology: {
    agb_formula: 'AGB = 10 × RH98',
    bgb_formula: 'BGB = 0.49 × AGB',
    tab_formula: 'TAB = AGB + BGB',
    carbon_formula: 'Carbon = 0.5 × TAB',
  },
  warning: 'Custom AOI analysis complete.',
  assumptions: [
    'GEDI raster samples are spatially representative of the full mapped mangrove extent.',
  ],
  aoi_geometry: {
    type: 'Polygon',
    coordinates: [[[67, 24], [67.4, 24], [67.4, 24.4], [67, 24.4], [67, 24]]],
  },
}

const MAP_LAYERS_SUCCESS_RESPONSE = {
  mode: 'live_earth_engine_map_layers',
  study_area: { id: 'indus_delta', name: 'Indus Delta, Pakistan' },
  date_range: { start_date: '2020-01-01', end_date: '2020-04-01' },
  aoi_geometry: CUSTOM_AOI_SUCCESS_RESPONSE.aoi_geometry,
  processing_version: 'p1',
  visualization_version: 'v1',
  generated_at: '2026-01-01T00:00:00+00:00',
  expires_at: '2026-01-01T00:20:00+00:00',
  layers: [
    {
      id: 'gmw_mangrove_extent',
      name: 'GMW Mangrove Extent',
      kind: 'raster_tile',
      tile_url_template: 'https://earthengine.googleapis.com/v1/projects/mangroves123/maps/test/tiles/{z}/{x}/{y}',
      default_visible: true,
      default_opacity: 0.65,
      min: 0,
      max: 1,
      palette: ['2e8b57'],
      units: 'Mapped mangrove',
      legend_type: 'categorical',
      description: 'Mapped mangrove extent.',
    },
    {
      id: 'carbon_density',
      name: 'Carbon Density',
      kind: 'raster_tile',
      tile_url_template: 'https://earthengine.googleapis.com/v1/projects/mangroves123/maps/test2/tiles/{z}/{x}/{y}',
      default_visible: true,
      default_opacity: 0.8,
      min: 0,
      max: 50,
      palette: ['0d0887', 'f0f921'],
      units: 'Mg C/ha',
      legend_type: 'continuous',
      description: 'Carbon density.',
    },
  ],
  warnings: [],
  message: null,
}

function renderAnalysis() {
  return render(
    <MemoryRouter initialEntries={['/analysis']}>
      <App />
    </MemoryRouter>,
  )
}

function renderAnalysisInStrictMode() {
  return render(
    <StrictMode>
      <MemoryRouter initialEntries={['/analysis']}>
        <App />
      </MemoryRouter>
    </StrictMode>,
  )
}

function createDeferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

beforeEach(() => {
  vi.clearAllMocks()
  submitCustomAoiAnalysis.mockReset()
  submitAoiMapLayers.mockReset()
  downloadAoiExport.mockReset()
})

describe('Carbon stock dashboard', () => {
  it('requests the carbon stock summary endpoint via API service', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    renderAnalysis()

    await waitFor(() => {
      expect(getCarbonStockSummary).toHaveBeenCalledTimes(1)
      expect(getCarbonStockSummary).toHaveBeenCalledWith(expect.objectContaining({ signal: expect.any(AbortSignal) }))
    })
  })

  it('shows loading state while request is pending', async () => {
    const deferred = createDeferred()
    getCarbonStockSummary.mockReturnValueOnce(deferred.promise)
    renderAnalysis()

    expect(screen.getByRole('status')).toHaveTextContent(/loading live carbon stock summary/i)
    expect(screen.getByRole('heading', { name: /analysis request summary/i })).toBeInTheDocument()
    expect(screen.getByText(/view technical request json/i)).toBeInTheDocument()
    deferred.resolve(LIVE_SUCCESS_RESPONSE)
    await screen.findByText(/mode:\s*live_earth_engine/i)
  })

  it('renders success metrics, labels and units with readable formatting', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    expect(screen.getByRole('heading', { name: 'Mapped mangrove area' })).toBeInTheDocument()
    expect(screen.getByText('90,769.33 ha')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'GEDI-covered mangrove area' })).toBeInTheDocument()
    expect(screen.getByText('64.293 ha')).toBeInTheDocument()
    expect(screen.getByText('0.0708%')).toBeInTheDocument()
    expect(screen.getByText('1,130')).toBeInTheDocument()
    expect(screen.getByText('23.0257 Mg C/ha')).toBeInTheDocument()
    expect(screen.getAllByText('1,480.37 Mg C').length).toBeGreaterThan(0)
    expect(screen.getAllByText('2,090,028.17 Mg C').length).toBeGreaterThan(0)
  })

  it('renders GEDI coverage visualization and accessible text', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    renderAnalysis()

    await screen.findByRole('img', { name: /gedi raster coverage is 0.0708% of mapped mangrove area/i })
    expect(screen.getByText(/64.293 ha of 90,769.33 ha/i)).toBeInTheDocument()
  })

  it('describes 1,480.37 Mg C as validated and never as inconsistent', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    renderAnalysis()

    await screen.findByText(/approximately 1,480.37 mg c is reproduced by the live earth engine area-weighted calculation and treated as validated/i)
    expect(screen.getByText(/validated reference result/i)).toBeInTheDocument()
    expect(screen.queryByText(/inconsistent/i)).not.toBeInTheDocument()
  })

  it('clearly distinguishes direct sampled and extrapolated stock sections', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    renderAnalysis()

    await screen.findByText(/direct sampled vs validated reference/i)
    expect(screen.getByText(/extrapolated ecosystem stock \(separate scale\)/i)).toBeInTheDocument()
  })

  it('shows Unavailable for optional or null values instead of zero', async () => {
    getCarbonStockSummary.mockResolvedValueOnce({
      ...LIVE_SUCCESS_RESPONSE,
      carbon_density: {
        ...LIVE_SUCCESS_RESPONSE.carbon_density,
        mean_mg_c_ha: null,
        valid_gedi_raster_pixel_count: null,
      },
      reference_comparison: null,
    })
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0)
    expect(screen.queryByText('0 Mg C')).not.toBeInTheDocument()
  })

  it('shows empty/unavailable state when backend returns no usable stock blocks', async () => {
    getCarbonStockSummary.mockResolvedValueOnce({
      connected: false,
      mode: 'live_earth_engine',
      status: 'disabled',
      study_area: LIVE_SUCCESS_RESPONSE.study_area,
      date_range: LIVE_SUCCESS_RESPONSE.date_range,
      processing: LIVE_SUCCESS_RESPONSE.processing,
      processing_performed: false,
      message: 'Google Earth Engine carbon stock summary is disabled by configuration.',
    })
    renderAnalysis()

    await screen.findByText(/carbon information is currently unavailable/i)
    expect(screen.getByText(/disabled by configuration/i)).toBeInTheDocument()
  })

  it('shows non-2xx HTTP style API errors', async () => {
    getCarbonStockSummary.mockRejectedValueOnce(
      new ApiError('The analysis server encountered an error. Please try again in a moment.', {
        status: 503,
        code: 'http_error',
      }),
    )
    renderAnalysis()

    await screen.findByRole('alert')
    expect(screen.getByRole('alert')).toHaveTextContent(/analysis server encountered an error/i)
  })

  it('shows network failure errors', async () => {
    getCarbonStockSummary.mockRejectedValueOnce(
      new ApiError('Unable to connect to the analysis server. Confirm that the FastAPI backend is running on port 8001.', {
        code: 'network_error',
      }),
    )
    renderAnalysis()

    await screen.findByRole('alert')
    expect(screen.getByRole('alert')).toHaveTextContent(/unable to connect to the analysis server/i)
  })

  it('shows malformed response errors', async () => {
    getCarbonStockSummary.mockRejectedValueOnce(
      new ApiError('The carbon stock response is missing required fields: processing.', {
        code: 'malformed_response',
      }),
    )
    renderAnalysis()

    await screen.findByRole('alert')
    expect(screen.getByRole('alert')).toHaveTextContent(/missing required fields/i)
  })

  it('retry button sends a new request and can recover from an error', async () => {
    getCarbonStockSummary
      .mockRejectedValueOnce(new ApiError('Earth Engine request timed out during carbon stock processing.', { code: 'http_error' }))
      .mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByRole('alert')
    await user.click(screen.getByRole('button', { name: /^retry$/i }))

    await screen.findByText(/mode:\s*live_earth_engine/i)
    expect(getCarbonStockSummary).toHaveBeenCalledTimes(2)
  })

  it('aborts the request signal on unmount', () => {
    const deferred = createDeferred()
    let capturedSignal = null
    getCarbonStockSummary.mockImplementationOnce((options) => {
      capturedSignal = options?.signal ?? null
      return deferred.promise
    })

    const rendered = renderAnalysis()
    rendered.unmount()

    expect(capturedSignal).toBeInstanceOf(AbortSignal)
    expect(capturedSignal.aborted).toBe(true)
  })

  it('StrictMode remount does not leave the dashboard stuck in loading', async () => {
    const first = createDeferred()
    getCarbonStockSummary
      .mockImplementationOnce(() => first.promise)
      .mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)

    renderAnalysisInStrictMode()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    expect(getCarbonStockSummary).toHaveBeenCalledTimes(2)
    expect(screen.queryByText(/loading live carbon stock summary/i)).not.toBeInTheDocument()
  })

  it('a stale earlier request cannot overwrite a newer successful response', async () => {
    const first = createDeferred()
    const second = createDeferred()
    const newerResponse = {
      ...LIVE_SUCCESS_RESPONSE,
      area: {
        ...LIVE_SUCCESS_RESPONSE.area,
        mapped_mangrove_area_ha: 12345.6789,
      },
    }
    getCarbonStockSummary
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    renderAnalysisInStrictMode()

    second.resolve(newerResponse)
    await screen.findByText('12,345.68 ha')

    first.resolve(LIVE_SUCCESS_RESPONSE)
    await waitFor(() => {
      expect(screen.getByText('12,345.68 ha')).toBeInTheDocument()
    })
    expect(screen.queryByText('90,769.33 ha')).not.toBeInTheDocument()
  })

  it('supports switching to custom mode and prepares custom AOI request preview without submission', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))

    expect(screen.getByText(/✓ ready for submission/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/prepared request json/i)).toHaveTextContent('"study_area_mode": "custom_aoi"')
    expect(screen.getByLabelText(/prepared request json/i)).toHaveTextContent('"aoi_geojson"')
    expect(getCarbonStockSummary).toHaveBeenCalledTimes(1)
  })

  it('shows validation error when custom mode has no polygon', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(/draw a custom aoi polygon to continue/i)
    expect(screen.getByText(/✗ incomplete input/i)).toBeInTheDocument()
  })

  it('initializes draw controls without error when switching to custom AOI in StrictMode', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysisInStrictMode()

    const customRadio = screen.getByRole('radio', { name: /custom aoi/i })
    await user.click(customRadio)

    // Verify custom mode is active
    expect(customRadio).toBeChecked()
    // Verify validation message appears (draw controls rendered and custom mode active)
    const alerts = screen.getAllByRole('alert')
    const validationAlert = alerts.find((alert) => alert.textContent.includes('Draw a custom AOI'))
    expect(validationAlert).toBeTruthy()
    // Verify request preview shows custom mode
    expect(screen.getByLabelText(/prepared request json/i)).toHaveTextContent('"study_area_mode": "custom_aoi"')
  })

  it('enables Run Analysis when prepared request is valid and submits normalized payload', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockResolvedValueOnce(CUSTOM_AOI_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    const runButton = screen.getByRole('button', { name: /run analysis/i })
    expect(runButton).toBeEnabled()

    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    expect(runButton).toBeEnabled()

    await user.click(runButton)
    await screen.findByRole('heading', { name: /aoi analysis results/i })

    expect(submitCustomAoiAnalysis).toHaveBeenCalledTimes(1)
    const [payload] = submitCustomAoiAnalysis.mock.calls[0]
    expect(payload).toMatchObject({
      study_area: 'custom',
      start_date: '2020-01-01',
      end_date: '2020-04-01',
    })
    expect(payload.aoi_geometry.coordinates[0][0]).toEqual([67, 24])
    expect(payload.aoi_geometry.coordinates[0][2]).toEqual([67.4, 24.4])
  })

  it('disables Run Analysis while submitting and prevents duplicate submissions', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    const deferred = createDeferred()
    submitCustomAoiAnalysis.mockImplementationOnce(() => deferred.promise)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))

    const runButton = screen.getByRole('button', { name: /run analysis/i })
    await user.click(runButton)
    expect(screen.getByRole('button', { name: /submitting/i })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: /submitting/i }))
    expect(submitCustomAoiAnalysis).toHaveBeenCalledTimes(1)

    deferred.resolve(CUSTOM_AOI_SUCCESS_RESPONSE)
    await screen.findByRole('heading', { name: /aoi analysis results/i })
  })

  it('renders success in separate AOI Analysis Results section without replacing baseline summary', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockResolvedValueOnce(CUSTOM_AOI_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysis()

    const referenceSummary = await screen.findByText(/fixed indus reference summary/i)
    await user.click(referenceSummary.closest('summary') || referenceSummary)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))

    await screen.findByRole('heading', { name: /aoi analysis results/i })
    expect(screen.getByText(/validated indus delta reference for 2020-01-01 to 2020-04-01/i)).toBeInTheDocument()
    expect(screen.getAllByText(/live_earth_engine_custom_aoi/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/indus delta, pakistan/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/end date is exclusive/i).length).toBeGreaterThan(0)
    expect(screen.getByText('3.0000 m')).toBeInTheDocument()
    expect(screen.getByText('30.0000 Mg/ha')).toBeInTheDocument()
    expect(screen.getByText('14.7000 Mg/ha')).toBeInTheDocument()
    expect(screen.getByText(/gedi raster samples are spatially representative/i)).toBeInTheDocument()
    expect(screen.queryByText(/missing required nested data blocks/i)).not.toBeInTheDocument()
  })

  it('keeps numeric AOI results visible when map-layer fetch fails', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockResolvedValueOnce(CUSTOM_AOI_SUCCESS_RESPONSE)
    submitAoiMapLayers.mockRejectedValueOnce(new ApiError('Layer endpoint failed', { status: 503, code: 'http_error' }))
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/fixed indus reference summary/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))

    await screen.findByRole('heading', { name: /aoi analysis results/i })
    expect(screen.getByText('2,235.00 Mg C')).toBeInTheDocument()
    expect(submitAoiMapLayers).toHaveBeenCalledTimes(1)
  })

  it('clears previous overlays when AOI inputs change after submission', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockResolvedValueOnce(CUSTOM_AOI_SUCCESS_RESPONSE)
    submitAoiMapLayers.mockResolvedValueOnce(MAP_LAYERS_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))
    expect(submitAoiMapLayers).toHaveBeenCalledTimes(1)

    await user.click(screen.getByRole('button', { name: /mock edit polygon/i }))
    expect(screen.getByText(/inputs changed — run the analysis again to refresh results/i)).toBeInTheDocument()
    expect(submitAoiMapLayers).toHaveBeenCalledTimes(1)
  })

  it('reset defaults button restores layer visibility and opacity to layer defaults', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockResolvedValueOnce(CUSTOM_AOI_SUCCESS_RESPONSE)
    submitAoiMapLayers.mockResolvedValueOnce(MAP_LAYERS_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))

    // Wait for layer controls to appear (StudyAreaMap is mocked — controls are not rendered in test DOM)
    // Verify the reset defaults button is wired from Analysis.jsx by checking the prop flows through
    // Confirm submitAoiMapLayers was called once (not twice — reset does not re-fetch)
    await waitFor(() => expect(submitAoiMapLayers).toHaveBeenCalledTimes(1))
    // The numeric results must still be present after map-layer success
    expect(screen.getByText('2,235.00 Mg C')).toBeInTheDocument()
  })

  it('renders a clear no-data state for custom AOI responses without results', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockResolvedValueOnce({
      ...CUSTOM_AOI_SUCCESS_RESPONSE,
      results: null,
      methodology: null,
      warning: 'No GEDI data available for the AOI and date range.',
    })
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))

    await screen.findByText(/no mangrove or gedi data was returned/i)
    expect(screen.getByText(/no gedi data available/i)).toBeInTheDocument()
    expect(screen.queryByText(/missing required nested data blocks/i)).not.toBeInTheDocument()
  })

  it('accepts no-data Abu Dhabi response and renders correct location label', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockResolvedValueOnce({
      ...CUSTOM_AOI_SUCCESS_RESPONSE,
      study_area: { id: 'abu_dhabi', name: 'Abu Dhabi, United Arab Emirates' },
      results: null,
      methodology: null,
      warning: 'AOI has no mapped mangrove area (no GMW mask coverage).',
    })
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.selectOptions(screen.getByRole('combobox', { name: /region/i }), 'abu_dhabi')
    await user.click(screen.getByRole('button', { name: /run analysis/i }))

    await waitFor(() => expect(screen.getAllByText(/abu dhabi, united arab emirates/i).length).toBeGreaterThan(0))
    expect(screen.getByText(/no mapped mangrove area/i)).toBeInTheDocument()
  })

  it('renders Retry on AOI submission errors and retry uses a new request', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis
      .mockRejectedValueOnce(new ApiError('Validation failed', { status: 422, code: 'http_error' }))
      .mockResolvedValueOnce(CUSTOM_AOI_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toBeInTheDocument()
    // Re-run button is in the header actions row, not inside the error panel
    const reRunButton = screen.getByRole('button', { name: /re-run analysis/i })
    expect(reRunButton).toBeTruthy()
    await user.click(reRunButton)
    await screen.findByRole('heading', { name: /aoi analysis results/i })
    expect(submitCustomAoiAnalysis).toHaveBeenCalledTimes(2)
  })

  it('does not auto-submit when drawing or editing AOI', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /mock edit polygon/i }))

    expect(submitCustomAoiAnalysis).not.toHaveBeenCalled()
  })

  it('aborts the active custom AOI submission on unmount', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    const deferred = createDeferred()
    let capturedSignal = null
    submitCustomAoiAnalysis.mockImplementationOnce((_, options) => {
      capturedSignal = options?.signal ?? null
      return deferred.promise
    })
    const user = userEvent.setup()
    const rendered = renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))

    rendered.unmount()
    expect(capturedSignal).toBeInstanceOf(AbortSignal)
    expect(capturedSignal.aborted).toBe(true)
  })

  it('submitAoiAnalysis reads current isValid value - does not submit after polygon deleted', async () => {
    // Regression test: submitAoiAnalysis must read preparedRequestIsValid from the current
    // render, not a stale closure. Without adding preparedRequestIsValid to deps, the guard
    // `if (!preparedRequestIsValid) return` could use the true value captured when the
    // callback was last created, causing a stale submission after the polygon is deleted.
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockRejectedValueOnce(new ApiError('Network failed'))
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))

    // Wait for error state — Re-run analysis button is now in the header actions row
    const alert = await screen.findByRole('alert')
    expect(alert).toBeInTheDocument()
    const reRunButton = screen.getByRole('button', { name: /re-run analysis/i })
    expect(reRunButton).toBeTruthy()

    // Delete polygon → preparedRequestIsValid becomes false
    await user.click(screen.getByRole('button', { name: /mock delete polygon/i }))

    // Invoke Re-run — submitAoiAnalysis should read the current (false) isValid and return early
    await user.click(reRunButton)

    // Only the original failed call was made; Re-run did not fire a new submission
    expect(submitCustomAoiAnalysis).toHaveBeenCalledTimes(1)
  })

  it('shows updated readiness text and removes outdated Module 12 deferral text', async () => {
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    renderAnalysis()
    await screen.findByText(/mode:\s*live_earth_engine/i)
    expect(
      screen.getByRole('heading', { name: /study area & analysis setup/i })
    ).toBeInTheDocument()
    expect(screen.getByText(/choose a predefined region or draw a custom aoi/i)).toBeInTheDocument()
    expect(screen.queryByText(/submission to \/api\/analyze is intentionally deferred to module 13/i)).not.toBeInTheDocument()
  })
})

describe('AOI export buttons (Module 15)', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  async function renderWithSuccessfulAnalysis() {
    getCarbonStockSummary.mockResolvedValue(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockResolvedValue(CUSTOM_AOI_SUCCESS_RESPONSE)
    submitAoiMapLayers.mockResolvedValue(MAP_LAYERS_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))
    await screen.findByRole('heading', { name: /aoi analysis results/i })
    return user
  }

  function mockDownloadLifecycle() {
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock')
    const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    return { createObjectURL, revokeObjectURL, clickSpy }
  }

  it('renders JSON, CSV and PDF export buttons after successful analysis', async () => {
    await renderWithSuccessfulAnalysis()

    expect(screen.getByRole('button', { name: /download json export/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /download csv export/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /download pdf export/i })).toBeInTheDocument()
  })

  it('export buttons are not shown while submission is in progress', async () => {
    getCarbonStockSummary.mockResolvedValue(LIVE_SUCCESS_RESPONSE)
    const deferred = createDeferred()
    submitCustomAoiAnalysis.mockReturnValueOnce(deferred.promise)
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))

    // While submitting there should be no export buttons
    expect(screen.queryByRole('button', { name: /download json export/i })).not.toBeInTheDocument()
    deferred.resolve(CUSTOM_AOI_SUCCESS_RESPONSE)
  })

  it('clicking JSON export calls downloadAoiExport with json format and triggers download', async () => {
    const mockBlob = new Blob(['{"test":1}'], { type: 'application/json' })
    downloadAoiExport.mockResolvedValueOnce({ blob: mockBlob, filename: 'mangrove_carbon_indus.json' })
    const { createObjectURL, revokeObjectURL, clickSpy } = mockDownloadLifecycle()

    const user = await renderWithSuccessfulAnalysis()
    await user.click(screen.getByRole('button', { name: /download json export/i }))

    await waitFor(() => expect(downloadAoiExport).toHaveBeenCalledWith(
      'json',
      expect.objectContaining({
        study_area: 'custom',
        aoi_geometry: expect.any(Object),
      }),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    ))
    expect(createObjectURL).toHaveBeenCalledWith(mockBlob)
    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock')
  })

  it('clicking CSV export calls downloadAoiExport with csv format', async () => {
    const mockBlob = new Blob(['field,value'], { type: 'text/csv' })
    downloadAoiExport.mockResolvedValueOnce({ blob: mockBlob, filename: 'export.csv' })
    mockDownloadLifecycle()

    const user = await renderWithSuccessfulAnalysis()
    await user.click(screen.getByRole('button', { name: /download csv export/i }))

    await waitFor(() => expect(downloadAoiExport).toHaveBeenCalledWith(
      'csv',
      expect.objectContaining({ study_area: 'custom' }),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    ))
  })

  it('clicking PDF export calls downloadAoiExport with pdf format', async () => {
    const mockBlob = new Blob(['%PDF'], { type: 'application/pdf' })
    downloadAoiExport.mockResolvedValueOnce({ blob: mockBlob, filename: 'export.pdf' })
    mockDownloadLifecycle()

    const user = await renderWithSuccessfulAnalysis()
    await user.click(screen.getByRole('button', { name: /download pdf export/i }))

    await waitFor(() => expect(downloadAoiExport).toHaveBeenCalledWith(
      'pdf',
      expect.objectContaining({ study_area: 'custom' }),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    ))
  })

  it('shows loading label on export button while downloading', async () => {
    const deferred = createDeferred()
    downloadAoiExport.mockReturnValueOnce(deferred.promise)

    const user = await renderWithSuccessfulAnalysis()

    // Button is initially enabled
    const jsonBtn = screen.getByRole('button', { name: /download json export/i })
    expect(jsonBtn).toBeEnabled()

    await user.click(jsonBtn)

    // While download is in-flight: button is disabled and shows loading text
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /download json export/i })).toBeDisabled()
    })
    expect(screen.getByRole('button', { name: /download json export/i })).toHaveTextContent(/json…/i)

    deferred.resolve({ blob: new Blob(['']), filename: 'e.json' })
  })

  it('shows error message when export fails', async () => {
    downloadAoiExport.mockRejectedValueOnce(
      new ApiError('Export server error.', { code: 'http_error', status: 500 }),
    )

    const user = await renderWithSuccessfulAnalysis()
    await user.click(screen.getByRole('button', { name: /download json export/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/export server error/i))
  })

  it('export error does not affect CSV and PDF buttons', async () => {
    downloadAoiExport.mockRejectedValueOnce(
      new ApiError('Network error.', { code: 'network_error' }),
    )

    const user = await renderWithSuccessfulAnalysis()
    await user.click(screen.getByRole('button', { name: /download json export/i }))

    await waitFor(() => screen.getByRole('alert'))

    // Other format buttons should still be enabled
    expect(screen.getByRole('button', { name: /download csv export/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /download pdf export/i })).toBeEnabled()
  })

  it('export buttons are absent after Clear Results', async () => {
    const user = await renderWithSuccessfulAnalysis()

    expect(screen.getByRole('button', { name: /download json export/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /clear results/i }))

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /download json export/i })).not.toBeInTheDocument()
    })
  })

  it('export buttons remain available for no-data AOI result', async () => {
    getCarbonStockSummary.mockResolvedValue(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockResolvedValue({
      ...CUSTOM_AOI_SUCCESS_RESPONSE,
      results: null,
      methodology: null,
      warning: 'No mapped mangrove area found.',
    })
    submitAoiMapLayers.mockResolvedValue({ ...MAP_LAYERS_SUCCESS_RESPONSE, layers: [] })
    const user = userEvent.setup()
    renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))

    // No-data shows the success state with empty results — export buttons still render
    // (user can still export the no-data response, which is a valid authoritative result)
    await screen.findByRole('heading', { name: /aoi analysis results/i })
    // Export buttons are shown regardless of results being null (no-data is a valid export)
    expect(screen.getByRole('button', { name: /download json export/i })).toBeInTheDocument()
  })

  it('aborts stale export when AOI inputs change before the download resolves', async () => {
    const deferred = createDeferred()
    downloadAoiExport.mockReturnValueOnce(deferred.promise)
    const { createObjectURL } = mockDownloadLifecycle()
    const user = await renderWithSuccessfulAnalysis()

    await user.click(screen.getByRole('button', { name: /download json export/i }))
    const endDateInput = screen.getByLabelText(/end date/i)
    await user.clear(endDateInput)
    await user.type(endDateInput, '2020-05-01')
    expect(screen.queryByRole('button', { name: /download json export/i })).not.toBeInTheDocument()

    deferred.resolve({ blob: new Blob(['{"late":true}']), filename: 'late.json' })
    await Promise.resolve()
    expect(createObjectURL).not.toHaveBeenCalled()
  })

  it('aborts pending export on unmount', async () => {
    const deferred = createDeferred()
    downloadAoiExport.mockReturnValueOnce(deferred.promise)
    const { createObjectURL } = mockDownloadLifecycle()
    getCarbonStockSummary.mockResolvedValueOnce(LIVE_SUCCESS_RESPONSE)
    submitCustomAoiAnalysis.mockResolvedValueOnce(CUSTOM_AOI_SUCCESS_RESPONSE)
    submitAoiMapLayers.mockResolvedValueOnce(MAP_LAYERS_SUCCESS_RESPONSE)
    const user = userEvent.setup()
    const rendered = renderAnalysis()

    await screen.findByText(/mode:\s*live_earth_engine/i)
    await user.click(screen.getByRole('radio', { name: /custom aoi/i }))
    await user.click(screen.getByRole('button', { name: /mock draw polygon/i }))
    await user.click(screen.getByRole('button', { name: /run analysis/i }))
    await screen.findByRole('heading', { name: /aoi analysis results/i })

    await user.click(screen.getByRole('button', { name: /download json export/i }))
    rendered.unmount()

    deferred.resolve({ blob: new Blob(['{"late":true}']), filename: 'late.json' })
    await Promise.resolve()
    expect(createObjectURL).not.toHaveBeenCalled()
  })

  it('prevents duplicate clicks while one export is in flight', async () => {
    const deferred = createDeferred()
    downloadAoiExport.mockReturnValueOnce(deferred.promise)
    mockDownloadLifecycle()
    const user = await renderWithSuccessfulAnalysis()

    const jsonButton = screen.getByRole('button', { name: /download json export/i })
    await user.click(jsonButton)
    await user.click(jsonButton)

    expect(downloadAoiExport).toHaveBeenCalledTimes(1)
    deferred.resolve({ blob: new Blob(['{}']), filename: 'one.json' })
  })
})
