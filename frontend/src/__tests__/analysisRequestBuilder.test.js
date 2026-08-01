import { describe, expect, it } from 'vitest'
import { buildBackendAnalyzeRequest, buildPreparedAnalysisRequest } from '../services/analysisRequestBuilder'
import { rectangleBoundsToPolygon } from '../utils/geo'

const region = {
  id: 'indus_delta',
  name: 'Indus Delta',
  country: 'Pakistan',
}

describe('analysis request builder', () => {
  it('builds valid predefined-region request preview', () => {
    const result = buildPreparedAnalysisRequest({
      studyAreaMode: 'predefined',
      selectedRegion: region,
      predefinedAoi: rectangleBoundsToPolygon([66.5, 23.5, 68.5, 24.8]),
      customAoi: null,
      startDate: '2020-01-01',
      endDate: '2020-04-01',
    })

    expect(result.isValid).toBe(true)
    expect(result.errors).toEqual([])
    expect(result.requestPreview.study_area_mode).toBe('predefined_region')
    expect(result.requestPreview.study_area_id).toBe('indus_delta')
    expect(result.requestPreview.note).toBe('Study area validated and ready for live Earth Engine analysis.')
  })

  it('requires polygon in custom mode', () => {
    const result = buildPreparedAnalysisRequest({
      studyAreaMode: 'custom',
      selectedRegion: region,
      predefinedAoi: rectangleBoundsToPolygon([66.5, 23.5, 68.5, 24.8]),
      customAoi: null,
      startDate: '2020-01-01',
      endDate: '2020-04-01',
    })

    expect(result.isValid).toBe(false)
    expect(result.errors).toContain('Draw a custom AOI polygon to continue.')
  })

  it('validates date range ordering', () => {
    const result = buildPreparedAnalysisRequest({
      studyAreaMode: 'predefined',
      selectedRegion: region,
      predefinedAoi: rectangleBoundsToPolygon([66.5, 23.5, 68.5, 24.8]),
      customAoi: null,
      startDate: '2020-04-01',
      endDate: '2020-04-01',
    })

    expect(result.isValid).toBe(false)
    expect(result.errors).toContain('End date must be after start date.')
  })

  it('builds backend payload with GeoJSON coordinates preserved as [longitude, latitude]', () => {
    const prepared = buildPreparedAnalysisRequest({
      studyAreaMode: 'custom',
      selectedRegion: region,
      predefinedAoi: rectangleBoundsToPolygon([66.5, 23.5, 68.5, 24.8]),
      customAoi: {
        type: 'Polygon',
        coordinates: [[[66.5, 23.5], [68.5, 23.5], [68.5, 24.8], [66.5, 24.8], [66.5, 23.5]]],
      },
      startDate: '2020-01-01',
      endDate: '2020-04-01',
    })

    const payload = buildBackendAnalyzeRequest(prepared.requestPreview)
    expect(payload.aoi_geometry.coordinates[0][0]).toEqual([66.5, 23.5])
    expect(payload.aoi_geometry.coordinates[0][2]).toEqual([68.5, 24.8])
  })

  it('returns null backend payload when prepared request has no AOI geometry', () => {
    const payload = buildBackendAnalyzeRequest(null)
    expect(payload).toBeNull()
  })
})
