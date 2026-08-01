import { normalizePolygonGeometry } from '../utils/geo'

export function buildPreparedAnalysisRequest({
  studyAreaMode,
  selectedRegion,
  predefinedAoi,
  customAoi,
  startDate,
  endDate,
}) {
  const errors = []
  if (!startDate || !endDate) {
    errors.push('Start date and end date are required.')
  } else if (endDate <= startDate) {
    errors.push('End date must be after start date.')
  }

  const normalizedPredefinedAoi = normalizePolygonGeometry(predefinedAoi)
  const normalizedCustomAoi = normalizePolygonGeometry(customAoi)
  const activeAoi = studyAreaMode === 'predefined' ? normalizedPredefinedAoi : normalizedCustomAoi

  if (studyAreaMode === 'predefined' && !selectedRegion) {
    errors.push('A predefined region must be selected.')
  }
  if (studyAreaMode === 'custom' && !activeAoi) {
    errors.push('Draw a custom AOI polygon to continue.')
  }

  const requestPreview = {
    mode: 'module_12_prepared_request',
    study_area_mode: studyAreaMode === 'custom' ? 'custom_aoi' : 'predefined_region',
    study_area_id: studyAreaMode === 'predefined' ? (selectedRegion?.id ?? null) : null,
    study_area_name:
      studyAreaMode === 'predefined'
        ? (selectedRegion ? `${selectedRegion.name}, ${selectedRegion.country}` : null)
        : 'Custom AOI',
    start_date: startDate || null,
    end_date: endDate || null,
    aoi_geojson: activeAoi,
    note: 'Study area validated and ready for live Earth Engine analysis.',
  }

  return {
    isValid: errors.length === 0,
    errors,
    requestPreview,
  }
}

export function buildBackendAnalyzeRequest(preparedRequest) {
  /**
   * Convert Module 12 prepared request to backend /api/analyze format.
   * Adds aoi_geometry field for Module 13 processing.
   *
   * @param {Object} preparedRequest - Output from buildPreparedAnalysisRequest().requestPreview
   * @returns {Object} Request payload for submitCustomAoiAnalysis() or analyzeMangrove()
   */
  if (!preparedRequest || !preparedRequest.aoi_geojson) {
    return null
  }

  return {
    study_area: preparedRequest.study_area_id || 'custom',
    aoi_geometry: preparedRequest.aoi_geojson,
    start_date: preparedRequest.start_date,
    end_date: preparedRequest.end_date,
  }
}
