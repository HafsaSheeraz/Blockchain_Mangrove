const NETWORK_ERROR_MESSAGE =
  'Unable to connect to the analysis server. Confirm that the FastAPI backend is running on port 8001.'

export class ApiError extends Error {
  constructor(message, options = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status || null
    this.code = options.code || 'api_error'
    this.details = options.details || null
  }
}

function ensureApiBaseUrl() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL
  if (!baseUrl || !baseUrl.trim()) {
    throw new ApiError(
      'Frontend API base URL is not configured. Set VITE_API_BASE_URL in frontend/.env or in the frontend deployment environment.',
      { code: 'config_error' },
    )
  }
  return baseUrl.replace(/\/+$/, '')
}

function getUserFriendlyApiError(status, detail) {
  const detailText = typeof detail === 'string' && detail.trim() ? detail : null
  if (status === 400 || status === 422) {
    return detailText || 'The analysis request is invalid. Please review your inputs and try again.'
  }
  if (status >= 500) {
    return 'The analysis server encountered an error. Please try again in a moment.'
  }
  return detailText || 'Unexpected response received from the analysis server.'
}

function isPlainObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function validateCustomAoiResponseShape(payload) {
  if (!isPlainObject(payload)) {
    throw new ApiError('The analysis server returned malformed data.', { code: 'malformed_response' })
  }

  const requiredTopLevel = ['mode', 'study_area', 'date_range', 'datasets', 'results', 'warning']
  const missingTopLevel = requiredTopLevel.filter((key) => !(key in payload))
  if (missingTopLevel.length > 0) {
    throw new ApiError(
      `The custom AOI response is missing required fields: ${missingTopLevel.join(', ')}.`,
      { code: 'malformed_response' },
    )
  }

  if (!isPlainObject(payload.study_area) || typeof payload.study_area.id !== 'string' || typeof payload.study_area.name !== 'string') {
    throw new ApiError('The custom AOI response has invalid study_area metadata.', {
      code: 'malformed_response',
    })
  }

  if (!isPlainObject(payload.date_range) || typeof payload.date_range.start_date !== 'string' || typeof payload.date_range.end_date !== 'string') {
    throw new ApiError('The custom AOI response has invalid date_range metadata.', {
      code: 'malformed_response',
    })
  }

  if (!Array.isArray(payload.datasets)) {
    throw new ApiError('The custom AOI response has invalid datasets metadata.', {
      code: 'malformed_response',
    })
  }

  if (payload.results !== null && !isPlainObject(payload.results)) {
    throw new ApiError('The custom AOI response has invalid results payload.', {
      code: 'malformed_response',
    })
  }

  if (payload.methodology !== undefined && payload.methodology !== null && !isPlainObject(payload.methodology)) {
    throw new ApiError('The custom AOI response has invalid methodology payload.', {
      code: 'malformed_response',
    })
  }
}

function validateAnalysisResponseShape(payload) {
  if (!isPlainObject(payload)) {
    throw new ApiError('The analysis server returned malformed data.', { code: 'malformed_response' })
  }

  const requiredTopLevel = ['mode', 'study_area', 'date_range', 'datasets', 'results', 'methodology', 'warning']
  const missingTopLevel = requiredTopLevel.filter((key) => !(key in payload))
  if (missingTopLevel.length > 0) {
    throw new ApiError(
      `The analysis response is missing required fields: ${missingTopLevel.join(', ')}.`,
      { code: 'malformed_response' },
    )
  }

  if (!isPlainObject(payload.results) || !isPlainObject(payload.methodology)) {
    throw new ApiError('The analysis response is missing required nested data blocks.', {
      code: 'malformed_response',
    })
  }
}

function validateCarbonStockSummaryResponseShape(payload) {
  if (!isPlainObject(payload)) {
    throw new ApiError('The carbon stock service returned malformed data.', {
      code: 'malformed_response',
    })
  }

  const requiredTopLevel = ['connected', 'mode', 'status', 'study_area', 'date_range', 'processing', 'processing_performed']
  const missingTopLevel = requiredTopLevel.filter((key) => !(key in payload))
  if (missingTopLevel.length > 0) {
    throw new ApiError(
      `The carbon stock response is missing required fields: ${missingTopLevel.join(', ')}.`,
      { code: 'malformed_response' },
    )
  }
}

export function buildAnalyzeUrl() {
  return `${ensureApiBaseUrl()}/api/analyze`
}

export function buildCarbonStockSummaryUrl() {
  return `${ensureApiBaseUrl()}/api/gee/carbon/stock-summary`
}

export function buildMapLayersUrl() {
  return `${ensureApiBaseUrl()}/api/analyze/map-layers`
}

export function buildGmwLayerUrl(studyArea = 'custom') {
  const params = new URLSearchParams({ study_area: studyArea })
  return `${ensureApiBaseUrl()}/api/map/gmw-layer?${params.toString()}`
}

export function buildGmwCoverageCheckUrl() {
  return `${ensureApiBaseUrl()}/api/map/gmw-coverage-check`
}

export function buildExportUrl(format) {
  return `${ensureApiBaseUrl()}/api/analyze/export/${format}`
}

export async function analyzeMangrove(payload) {
  let response
  try {
    response = await fetch(buildAnalyzeUrl(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
  } catch (error) {
    throw new ApiError(NETWORK_ERROR_MESSAGE, {
      code: 'network_error',
      details: error instanceof Error ? error.message : null,
    })
  }

  let body = null
  try {
    body = await response.json()
  } catch (error) {
    throw new ApiError('The analysis server returned a non-JSON response.', {
      status: response.status,
      code: 'malformed_response',
      details: error instanceof Error ? error.message : null,
    })
  }

  if (!response.ok) {
    const detail = body && typeof body === 'object' ? body.detail : null
    throw new ApiError(getUserFriendlyApiError(response.status, detail), {
      status: response.status,
      code: 'http_error',
      details: detail,
    })
  }

  validateAnalysisResponseShape(body)
  return body
}

export async function submitCustomAoiAnalysis(payload, options = {}) {
  /**
   * Submit a custom AOI for live Earth Engine analysis.
   *
   * Payload should include:
   * - study_area: string ID (e.g., "custom")
   * - aoi_geometry: GeoJSON Polygon
   * - start_date: ISO date string
   * - end_date: ISO date string
   *
   * Options:
   * - signal: AbortSignal for cancellation
   *
   * Returns: response from /api/analyze with mode='live_earth_engine_custom_aoi'
   */
  const { signal } = options
  let response

  try {
    response = await fetch(buildAnalyzeUrl(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The analysis request was cancelled.', {
        code: 'request_aborted',
      })
    }
    throw new ApiError(NETWORK_ERROR_MESSAGE, {
      code: 'network_error',
      details: error instanceof Error ? error.message : null,
    })
  }

  let body = null
  try {
    body = await response.json()
  } catch (error) {
    throw new ApiError('The analysis server returned a non-JSON response.', {
      status: response.status,
      code: 'malformed_response',
      details: error instanceof Error ? error.message : null,
    })
  }

  if (!response.ok) {
    const detail = body && typeof body === 'object' ? body.detail : null
    throw new ApiError(getUserFriendlyApiError(response.status, detail), {
      status: response.status,
      code: 'http_error',
      details: detail,
    })
  }

  validateCustomAoiResponseShape(body)
  if (body.mode !== 'live_earth_engine_custom_aoi') {
    throw new ApiError('Unexpected analysis mode returned from server.', {
      code: 'malformed_response',
    })
  }

  return body
}

function validateMapLayersResponseShape(payload) {
  if (!isPlainObject(payload)) {
    throw new ApiError('The map-layer service returned malformed data.', { code: 'malformed_response' })
  }

  const requiredTopLevel = [
    'mode',
    'study_area',
    'date_range',
    'aoi_geometry',
    'processing_version',
    'visualization_version',
    'generated_at',
    'expires_at',
    'layers',
    'warnings',
  ]
  const missing = requiredTopLevel.filter((key) => !(key in payload))
  if (missing.length > 0) {
    throw new ApiError(`The map-layer response is missing required fields: ${missing.join(', ')}.`, {
      code: 'malformed_response',
    })
  }
  if (!Array.isArray(payload.layers)) {
    throw new ApiError('The map-layer response has invalid layers format.', { code: 'malformed_response' })
  }
  for (const layer of payload.layers) {
    if (!isPlainObject(layer) || layer.kind !== 'raster_tile' || typeof layer.tile_url_template !== 'string') {
      throw new ApiError('The map-layer response contains an invalid layer descriptor.', {
        code: 'malformed_response',
      })
    }
  }
}

function validateGmwLayerResponseShape(payload) {
  if (!isPlainObject(payload)) {
    throw new ApiError('The GMW layer service returned malformed data.', { code: 'malformed_response' })
  }
  const requiredTopLevel = [
    'mode',
    'study_area',
    'gmw_asset_id',
    'tile_url_template',
    'default_visible',
    'default_opacity',
    'palette',
    'label',
  ]
  const missing = requiredTopLevel.filter((key) => !(key in payload))
  if (missing.length > 0) {
    throw new ApiError(`The GMW layer response is missing required fields: ${missing.join(', ')}.`, {
      code: 'malformed_response',
    })
  }
  if (payload.mode !== 'live_earth_engine_gmw_layer') {
    throw new ApiError('Unexpected GMW layer mode returned from server.', {
      code: 'malformed_response',
    })
  }
  if (typeof payload.tile_url_template !== 'string') {
    throw new ApiError('The GMW layer response has an invalid tile URL.', {
      code: 'malformed_response',
    })
  }
}

function validateGmwCoverageCheckResponseShape(payload) {
  if (!isPlainObject(payload)) {
    throw new ApiError('The GMW coverage check service returned malformed data.', { code: 'malformed_response' })
  }
  const requiredTopLevel = ['mode', 'study_area', 'has_mangroves']
  const missing = requiredTopLevel.filter((key) => !(key in payload))
  if (missing.length > 0) {
    throw new ApiError(`The GMW coverage response is missing required fields: ${missing.join(', ')}.`, {
      code: 'malformed_response',
    })
  }
  if (payload.mode !== 'live_earth_engine_gmw_coverage_check') {
    throw new ApiError('Unexpected GMW coverage mode returned from server.', {
      code: 'malformed_response',
    })
  }
}

export async function submitAoiMapLayers(payload, options = {}) {
  const { signal } = options
  let response
  try {
    response = await fetch(buildMapLayersUrl(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The map-layer request was cancelled.', {
        code: 'request_aborted',
      })
    }
    throw new ApiError(NETWORK_ERROR_MESSAGE, {
      code: 'network_error',
      details: error instanceof Error ? error.message : null,
    })
  }

  let body = null
  try {
    body = await response.json()
  } catch (error) {
    throw new ApiError('The map-layer service returned a non-JSON response.', {
      status: response.status,
      code: 'malformed_response',
      details: error instanceof Error ? error.message : null,
    })
  }

  if (!response.ok) {
    const detail = body && typeof body === 'object' ? body.detail : null
    throw new ApiError(getUserFriendlyApiError(response.status, detail), {
      status: response.status,
      code: 'http_error',
      details: detail,
    })
  }

  validateMapLayersResponseShape(body)
  if (body.mode !== 'live_earth_engine_map_layers') {
    throw new ApiError('Unexpected map-layer mode returned from server.', {
      code: 'malformed_response',
    })
  }
  return body
}

export async function getGmwLayerOverlay(options = {}) {
  const { studyArea = 'custom', signal } = options
  let response
  try {
    response = await fetch(buildGmwLayerUrl(studyArea), {
      method: 'GET',
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The mangrove layer request was cancelled.', {
        code: 'request_aborted',
      })
    }
    throw new ApiError(NETWORK_ERROR_MESSAGE, {
      code: 'network_error',
      details: error instanceof Error ? error.message : null,
    })
  }

  let body = null
  try {
    body = await response.json()
  } catch (error) {
    throw new ApiError('The mangrove layer service returned a non-JSON response.', {
      status: response.status,
      code: 'malformed_response',
      details: error instanceof Error ? error.message : null,
    })
  }

  if (!response.ok) {
    throw toApiErrorFromResponse(response.status, body)
  }

  validateGmwLayerResponseShape(body)
  return body
}

export async function checkCustomAoiMangroveCoverage(payload, options = {}) {
  const { signal } = options
  let response
  try {
    response = await fetch(buildGmwCoverageCheckUrl(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The mangrove coverage check was cancelled.', {
        code: 'request_aborted',
      })
    }
    throw new ApiError(NETWORK_ERROR_MESSAGE, {
      code: 'network_error',
      details: error instanceof Error ? error.message : null,
    })
  }

  let body = null
  try {
    body = await response.json()
  } catch (error) {
    throw new ApiError('The mangrove coverage check service returned a non-JSON response.', {
      status: response.status,
      code: 'malformed_response',
      details: error instanceof Error ? error.message : null,
    })
  }

  if (!response.ok) {
    throw toApiErrorFromResponse(response.status, body)
  }

  validateGmwCoverageCheckResponseShape(body)
  return body
}

function toApiErrorFromResponse(status, body) {
  const detail = body && typeof body === 'object' ? (body.detail ?? body.message ?? null) : null
  return new ApiError(getUserFriendlyApiError(status, detail), {
    status,
    code: 'http_error',
    details: detail,
  })
}

export async function getCarbonStockSummary(options = {}) {
  const { signal } = options
  let response
  try {
    response = await fetch(buildCarbonStockSummaryUrl(), {
      method: 'GET',
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The carbon stock request was cancelled.', {
        code: 'request_aborted',
      })
    }
    throw new ApiError(NETWORK_ERROR_MESSAGE, {
      code: 'network_error',
      details: error instanceof Error ? error.message : null,
    })
  }

  let body = null
  try {
    body = await response.json()
  } catch (error) {
    throw new ApiError('The carbon stock service returned a non-JSON response.', {
      status: response.status,
      code: 'malformed_response',
      details: error instanceof Error ? error.message : null,
    })
  }

  if (!response.ok) {
    throw toApiErrorFromResponse(response.status, body)
  }

  validateCarbonStockSummaryResponseShape(body)
  return body
}

const EXPORT_CONTENT_TYPES = {
  json: 'application/json',
  csv: 'text/csv',
  pdf: 'application/pdf',
}

const EXPORT_FILENAME_FALLBACKS = {
  json: 'mangrove_carbon_export.json',
  csv: 'mangrove_carbon_export.csv',
  pdf: 'mangrove_carbon_export.pdf',
}

function getExportFallbackFilename(format) {
  return EXPORT_FILENAME_FALLBACKS[format] || 'mangrove_carbon_export.bin'
}

function sanitizeExportFilename(filename, format) {
  if (typeof filename !== 'string') {
    return getExportFallbackFilename(format)
  }

  let trimmed = filename.trim().replace(/^"|"$/g, '')
  if (!trimmed) {
    return getExportFallbackFilename(format)
  }

  if (trimmed.length > 120 || /[\r\n]/.test(trimmed) || trimmed.includes('/') || trimmed.includes('\\') || trimmed.includes('..')) {
    return getExportFallbackFilename(format)
  }

  try {
    trimmed = decodeURIComponent(trimmed)
  } catch {
    return getExportFallbackFilename(format)
  }

  const safe = trimmed.replace(/[^A-Za-z0-9._-]+/g, '_')
  if (!safe || safe.startsWith('.') || !safe.endsWith(`.${format}`)) {
    return getExportFallbackFilename(format)
  }

  return safe
}

function parseContentDispositionFilename(disposition, format) {
  if (typeof disposition !== 'string' || !disposition.trim()) {
    return getExportFallbackFilename(format)
  }

  const utf8Match = disposition.match(/filename\*\s*=\s*(?:UTF-8''|utf-8''|)([^;]+)/i)
  if (utf8Match && utf8Match[1]) {
    try {
      return sanitizeExportFilename(utf8Match[1], format)
    } catch {
      return getExportFallbackFilename(format)
    }
  }

  const quotedMatch = disposition.match(/filename\s*=\s*"([^"]+)"/i)
  if (quotedMatch && quotedMatch[1]) {
    return sanitizeExportFilename(quotedMatch[1], format)
  }

  const tokenMatch = disposition.match(/filename\s*=\s*([^;]+)/i)
  if (tokenMatch && tokenMatch[1]) {
    return sanitizeExportFilename(tokenMatch[1], format)
  }

  return getExportFallbackFilename(format)
}

/**
 * Download an authoritative AOI analysis export from the backend.
 *
 * Sends the same AnalyzeRequest payload to POST /api/analyze/export/{format}.
 * The backend reuses its cached analysis result — no new Earth Engine call
 * is triggered when an equivalent cached result exists.
 *
 * Returns { blob, filename } on success.
 * Throws ApiError on network failure, non-200 status, or unexpected content type.
 *
 * @param {'json'|'csv'|'pdf'} format
 * @param {object} payload  — backend AnalyzeRequest (must include aoi_geometry)
 * @param {{ signal?: AbortSignal }} [options]
 */
export async function downloadAoiExport(format, payload, options = {}) {
  const { signal } = options
  if (!Object.prototype.hasOwnProperty.call(EXPORT_CONTENT_TYPES, format)) {
    throw new ApiError(`Unsupported export format: ${format}`, { code: 'config_error' })
  }
  const url = buildExportUrl(format)
  let response

  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The export request was cancelled.', { code: 'request_aborted' })
    }
    throw new ApiError(NETWORK_ERROR_MESSAGE, {
      code: 'network_error',
      details: error instanceof Error ? error.message : null,
    })
  }

  if (!response.ok) {
    let detail = null
    try {
      const errBody = await response.json()
      detail = errBody && typeof errBody === 'object' ? (errBody.detail ?? null) : null
    } catch { /* ignore parse failure on error body */ }
    throw new ApiError(getUserFriendlyApiError(response.status, detail), {
      status: response.status,
      code: 'http_error',
      details: detail,
    })
  }

  const contentType = response.headers.get('content-type') || ''
  const expectedType = EXPORT_CONTENT_TYPES[format]
  if (expectedType && !contentType.startsWith(expectedType)) {
    throw new ApiError(`Unexpected content type for ${format} export: ${contentType}`, {
      code: 'malformed_response',
    })
  }
  const disposition = response.headers.get('content-disposition') || ''
  const filename = parseContentDispositionFilename(disposition, format)

  const blob = await response.blob()
  return { blob, filename }
}
