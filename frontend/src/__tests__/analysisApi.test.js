import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  analyzeMangrove,
  buildAnalyzeUrl,
  buildCarbonStockSummaryUrl,
  buildExportUrl,
  buildMapLayersUrl,
  downloadAoiExport,
  getCarbonStockSummary,
  submitAoiMapLayers,
  submitCustomAoiAnalysis,
} from '../services/analysisApi'

describe('analysisApi service', () => {
  const LIVE_SHAPED_CARBON_STOCK_RESPONSE = {
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
      gedi_raster_coverage: 'sum(pixelArea_ha over valid Carbon raster cells)',
      direct_sampled_stock: 'sum(Carbon_Mg_C_ha × pixelArea_ha)',
      extrapolated_stock: 'mean_Carbon_Mg_C_ha × mapped_mangrove_area_ha',
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
      difference_from_older_report_mg_c: -0.0006239589474609734,
      note: 'The live Earth Engine area-weighted calculation reproduces the older direct sampled carbon result of approximately 1,480.37 Mg C.',
    },
  }

  const CUSTOM_AOI_SUCCESS_RESPONSE = {
    mode: 'live_earth_engine_custom_aoi',
    study_area: { id: 'custom', name: 'Custom AOI' },
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
  }

  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8001')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('builds the expected analyze URL from VITE_API_BASE_URL', () => {
    expect(buildAnalyzeUrl()).toBe('http://127.0.0.1:8001/api/analyze')
  })

  it('builds the expected carbon-stock URL from VITE_API_BASE_URL', () => {
    expect(buildCarbonStockSummaryUrl()).toBe('http://127.0.0.1:8001/api/gee/carbon/stock-summary')
  })

  it('builds the expected map-layer URL from VITE_API_BASE_URL', () => {
    expect(buildMapLayersUrl()).toBe('http://127.0.0.1:8001/api/analyze/map-layers')
  })

  it('normalizes trailing slash in VITE_API_BASE_URL', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8001/')
    expect(buildCarbonStockSummaryUrl()).toBe('http://127.0.0.1:8001/api/gee/carbon/stock-summary')
  })

  it('sends POST request with JSON headers and payload', async () => {
    const mockResponseBody = { mode: 'demonstration', study_area: {}, date_range: {}, datasets: [], results: {}, methodology: {}, warning: 'x' }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mockResponseBody), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const payload = {
      study_area: 'indus_delta',
      start_date: '2019-01-01',
      end_date: '2021-12-31',
    }
    await analyzeMangrove(payload)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8001/api/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
  })

  it('sends GET request to carbon-stock endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(LIVE_SHAPED_CARBON_STOCK_RESPONSE), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    const abortController = new AbortController()

    await getCarbonStockSummary({ signal: abortController.signal })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8001/api/gee/carbon/stock-summary',
      expect.objectContaining({
        method: 'GET',
        signal: abortController.signal,
      }),
    )
  })

  it('accepts a live-shaped carbon stock summary response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(LIVE_SHAPED_CARBON_STOCK_RESPONSE), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(getCarbonStockSummary()).resolves.toMatchObject({
      connected: true,
      status: 'connected',
      area: {
        mapped_mangrove_area_ha: 90769.33192367057,
        valid_gedi_raster_coverage_area_ha: 64.29286419067385,
      },
    })
  })

  it('throws friendly 400 error message from API detail', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: "Unsupported study_area 'x'" }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(analyzeMangrove({})).rejects.toMatchObject({
      name: 'ApiError',
      status: 400,
      message: "Unsupported study_area 'x'",
    })
  })

  it('throws friendly 422 error message from API detail', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'end_date must be after start_date' }), {
        status: 422,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(analyzeMangrove({})).rejects.toMatchObject({
      status: 422,
      message: 'end_date must be after start_date',
    })
  })

  it('throws generic 500 error message', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Internal Error' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(analyzeMangrove({})).rejects.toMatchObject({
      status: 500,
      message: 'The analysis server encountered an error. Please try again in a moment.',
    })
  })

  it('throws network failure message when fetch rejects', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(analyzeMangrove({})).rejects.toMatchObject({
      message:
        'Unable to connect to the analysis server. Confirm that the FastAPI backend is running on port 8001.',
    })
  })

  it('throws malformed response error when expected fields are missing', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ mode: 'demonstration' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(analyzeMangrove({})).rejects.toMatchObject({
      message: expect.stringContaining('missing required fields'),
    })
  })

  it('throws malformed response for incomplete carbon stock payload', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ mode: 'live_earth_engine', status: 'connected' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(getCarbonStockSummary()).rejects.toMatchObject({
      message: expect.stringContaining('missing required fields'),
    })
  })

  it('throws API message for non-2xx carbon stock response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Earth Engine quota or restricted-mode limitation was encountered.' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(getCarbonStockSummary()).rejects.toMatchObject({
      status: 503,
      message: 'The analysis server encountered an error. Please try again in a moment.',
    })
  })

  it('throws network message for carbon stock fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(getCarbonStockSummary()).rejects.toMatchObject({
      code: 'network_error',
      message:
        'Unable to connect to the analysis server. Confirm that the FastAPI backend is running on port 8001.',
    })
  })

  it('throws cancellation code when carbon stock request is aborted', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new DOMException('The operation was aborted', 'AbortError'))

    await expect(getCarbonStockSummary()).rejects.toMatchObject({
      code: 'request_aborted',
      message: 'The carbon stock request was cancelled.',
    })
  })

  it('submits custom AOI payload to /api/analyze with JSON body and signal', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(CUSTOM_AOI_SUCCESS_RESPONSE), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const controller = new AbortController()
    const payload = {
      study_area: 'custom',
      aoi_geometry: {
        type: 'Polygon',
        coordinates: [[[66.5, 23.5], [68.5, 23.5], [68.5, 24.8], [66.5, 24.8], [66.5, 23.5]]],
      },
      start_date: '2020-01-01',
      end_date: '2020-04-01',
    }

    const result = await submitCustomAoiAnalysis(payload, { signal: controller.signal })
    expect(result.mode).toBe('live_earth_engine_custom_aoi')
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8001/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
  })

  it('rejects custom AOI response with wrong mode', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ...CUSTOM_AOI_SUCCESS_RESPONSE, mode: 'demonstration' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    await expect(submitCustomAoiAnalysis({})).rejects.toMatchObject({
      code: 'malformed_response',
      message: 'Unexpected analysis mode returned from server.',
    })
  })

  it('returns request_aborted when custom AOI submission is cancelled', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new DOMException('The operation was aborted', 'AbortError'))
    await expect(submitCustomAoiAnalysis({})).rejects.toMatchObject({
      code: 'request_aborted',
      message: 'The analysis request was cancelled.',
    })
  })

  it('accepts valid custom AOI no-data response where results is null', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({
        ...CUSTOM_AOI_SUCCESS_RESPONSE,
        study_area: { id: 'abu_dhabi', name: 'Abu Dhabi, United Arab Emirates' },
        results: null,
        methodology: null,
        warning: 'No GEDI data available for the AOI and date range.',
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const response = await submitCustomAoiAnalysis({ study_area: 'abu_dhabi' })
    expect(response.mode).toBe('live_earth_engine_custom_aoi')
    expect(response.results).toBeNull()
    expect(response.warning).toMatch(/No GEDI data/i)
  })

  it('rejects malformed custom AOI response missing study_area metadata', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({
        ...CUSTOM_AOI_SUCCESS_RESPONSE,
        study_area: null,
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(submitCustomAoiAnalysis({ study_area: 'custom' })).rejects.toMatchObject({
      code: 'malformed_response',
      message: expect.stringContaining('invalid study_area metadata'),
    })
  })

  it('accepts valid map-layer response with ordered layers array', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({
        mode: 'live_earth_engine_map_layers',
        study_area: { id: 'custom', name: 'Custom AOI' },
        date_range: { start_date: '2020-01-01', end_date: '2020-04-01' },
        aoi_geometry: { type: 'Polygon', coordinates: [[[67, 24], [67.4, 24], [67.4, 24.4], [67, 24.4], [67, 24]]] },
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
        ],
        warnings: [],
        message: null,
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    const response = await submitAoiMapLayers({ study_area: 'custom' })
    expect(response.mode).toBe('live_earth_engine_map_layers')
    expect(response.layers[0].id).toBe('gmw_mangrove_extent')
  })

  it('rejects map-layer response with non-array layers', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({
        mode: 'live_earth_engine_map_layers',
        study_area: { id: 'custom', name: 'Custom AOI' },
        date_range: { start_date: '2020-01-01', end_date: '2020-04-01' },
        aoi_geometry: { type: 'Polygon', coordinates: [] },
        processing_version: 'p1',
        visualization_version: 'v1',
        generated_at: '2026-01-01T00:00:00+00:00',
        expires_at: '2026-01-01T00:20:00+00:00',
        layers: {},
        warnings: [],
        message: null,
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    await expect(submitAoiMapLayers({ study_area: 'custom' })).rejects.toMatchObject({
      code: 'malformed_response',
    })
  })
})

describe('downloadAoiExport', () => {
  const EXPORT_PAYLOAD = {
    study_area: 'indus_delta',
    aoi_geometry: {
      type: 'Polygon',
      coordinates: [[[66.5, 23.5], [68.5, 23.5], [68.5, 24.8], [66.5, 24.8], [66.5, 23.5]]],
    },
    start_date: '2020-01-01',
    end_date: '2020-04-01',
  }

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('buildExportUrl returns correct endpoint for each format', () => {
    expect(buildExportUrl('json')).toContain('/api/analyze/export/json')
    expect(buildExportUrl('csv')).toContain('/api/analyze/export/csv')
    expect(buildExportUrl('pdf')).toContain('/api/analyze/export/pdf')
  })

  it('returns the server filename on successful JSON export', async () => {
    const headers = new Headers({
      'Content-Type': 'application/json',
      'Content-Disposition': 'attachment; filename="mangrove_carbon_indus_delta_20200101_20200401.json"',
    })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ study_area: { id: 'indus_delta' }, exported_at: '2026-01-01T00:00:00Z' }), {
        status: 200,
        headers,
      }),
    )
    const result = await downloadAoiExport('json', EXPORT_PAYLOAD)
    expect(result.filename).toBe('mangrove_carbon_indus_delta_20200101_20200401.json')
    expect(result.blob).toBeInstanceOf(Blob)
  })

  it('accepts quoted Content-Disposition filenames for CSV export', async () => {
    const headers = new Headers({
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="mangrove_carbon_indus_delta_20200101_20200401.csv"',
    })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('field,value\nstudy_area_id,indus_delta', { status: 200, headers }),
    )
    const result = await downloadAoiExport('csv', EXPORT_PAYLOAD)
    expect(result.filename).toBe('mangrove_carbon_indus_delta_20200101_20200401.csv')
  })

  it('accepts UTF-8 Content-Disposition filenames for PDF export', async () => {
    const headers = new Headers({
      'Content-Type': 'application/pdf',
      'Content-Disposition': "attachment; filename*=UTF-8''mangrove_carbon_indus_delta_20200101_20200401.pdf",
    })
    const pdfBytes = new Uint8Array([0x25, 0x50, 0x44, 0x46])  // %PDF
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(pdfBytes, { status: 200, headers }),
    )
    const result = await downloadAoiExport('pdf', EXPORT_PAYLOAD)
    expect(result.filename).toBe('mangrove_carbon_indus_delta_20200101_20200401.pdf')
  })

  it('falls back to default filename when Content-Disposition is absent', async () => {
    const headers = new Headers({ 'Content-Type': 'application/json' })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{}', { status: 200, headers }),
    )
    const result = await downloadAoiExport('json', EXPORT_PAYLOAD)
    expect(result.filename).toBe('mangrove_carbon_export.json')
  })

  it('falls back to default filename when Content-Disposition is suspicious', async () => {
    const headers = new Headers({
      'Content-Type': 'application/json',
      'Content-Disposition': 'attachment; filename="../../evil.json"',
    })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{}', { status: 200, headers }),
    )
    const result = await downloadAoiExport('json', EXPORT_PAYLOAD)
    expect(result.filename).toBe('mangrove_carbon_export.json')
  })

  it('falls back to default filename when Content-Disposition extension is wrong', async () => {
    const headers = new Headers({
      'Content-Type': 'application/json',
      'Content-Disposition': 'attachment; filename="mangrove_carbon_indus_delta_20200101_20200401.txt"',
    })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{}', { status: 200, headers }),
    )
    const result = await downloadAoiExport('json', EXPORT_PAYLOAD)
    expect(result.filename).toBe('mangrove_carbon_export.json')
  })

  it('falls back to default filename when Content-Disposition includes CRLF injection', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        get(name) {
          if (name === 'content-type') {
            return 'application/json'
          }
          if (name === 'content-disposition') {
            return 'attachment; filename="mangrove_carbon_indus_delta_20200101_20200401.json\r\nX-Evil: 1"'
          }
          return null
        },
      },
      blob: async () => new Blob(['{}'], { type: 'application/json' }),
    })
    const result = await downloadAoiExport('json', EXPORT_PAYLOAD)
    expect(result.filename).toBe('mangrove_carbon_export.json')
  })

  it('uses distinct server filenames for Indus, Abu Dhabi and custom AOIs', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      const body = JSON.parse(init.body)
      const studyArea = body.study_area
      const filename =
        studyArea === 'abu_dhabi'
          ? 'mangrove_carbon_abu_dhabi_20200101_20200401.json'
          : studyArea === 'custom'
            ? 'mangrove_carbon_custom_20200101_20200401.json'
            : 'mangrove_carbon_indus_delta_20200101_20200401.json'
      return new Response('{}', {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Content-Disposition': `attachment; filename="${filename}"`,
        },
      })
    })

    const indus = await downloadAoiExport('json', EXPORT_PAYLOAD)
    const abuDhabi = await downloadAoiExport('json', {
      ...EXPORT_PAYLOAD,
      study_area: 'abu_dhabi',
    })
    const custom = await downloadAoiExport('json', {
      ...EXPORT_PAYLOAD,
      study_area: 'custom',
    })

    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(indus.filename).toBe('mangrove_carbon_indus_delta_20200101_20200401.json')
    expect(abuDhabi.filename).toBe('mangrove_carbon_abu_dhabi_20200101_20200401.json')
    expect(custom.filename).toBe('mangrove_carbon_custom_20200101_20200401.json')
  })

  it('throws ApiError with http_error code on 400 response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'aoi_geometry required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    await expect(downloadAoiExport('json', {})).rejects.toMatchObject({ code: 'http_error' })
  })

  it('throws ApiError with network_error code on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Network failure'))
    await expect(downloadAoiExport('json', EXPORT_PAYLOAD)).rejects.toMatchObject({ code: 'network_error' })
  })

  it('throws ApiError with malformed_response when content type does not match format', async () => {
    const headers = new Headers({ 'Content-Type': 'text/html' })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('<html/>', { status: 200, headers }),
    )
    await expect(downloadAoiExport('json', EXPORT_PAYLOAD)).rejects.toMatchObject({ code: 'malformed_response' })
  })

  it('rejects unsupported export format before making a request', async () => {
    await expect(downloadAoiExport('xlsx', EXPORT_PAYLOAD)).rejects.toMatchObject({ code: 'config_error' })
  })
})
