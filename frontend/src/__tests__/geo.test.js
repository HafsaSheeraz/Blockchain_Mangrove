import { describe, expect, it } from 'vitest'
import {
  getPolygonBounds,
  getPolygonVertexCount,
  normalizePolygonGeometry,
  polygonToLeafletLatLngs,
  rectangleBoundsToPolygon,
} from '../utils/geo'

describe('geo utils', () => {
  it('creates a closed rectangle polygon from bounds', () => {
    const polygon = rectangleBoundsToPolygon([66.5, 23.5, 68.5, 24.8])
    expect(polygon.type).toBe('Polygon')
    expect(polygon.coordinates[0][0]).toEqual([66.5, 23.5])
    expect(polygon.coordinates[0][4]).toEqual([66.5, 23.5])
  })

  it('normalizes polygon geometry and closes ring when needed', () => {
    const normalized = normalizePolygonGeometry({
      type: 'Polygon',
      coordinates: [[[66.5, 23.5], [68.5, 23.5], [68.5, 24.8], [66.5, 24.8]]],
    })
    expect(normalized.coordinates[0][0]).toEqual([66.5, 23.5])
    expect(normalized.coordinates[0][4]).toEqual([66.5, 23.5])
  })

  it('converts GeoJSON lon/lat polygon to Leaflet lat/lon points', () => {
    const latLngs = polygonToLeafletLatLngs(rectangleBoundsToPolygon([66.5, 23.5, 68.5, 24.8]))
    expect(latLngs[0]).toEqual([23.5, 66.5])
  })

  it('returns polygon bounds and vertex count', () => {
    const polygon = rectangleBoundsToPolygon([66.5, 23.5, 68.5, 24.8])
    expect(getPolygonBounds(polygon)).toEqual({
      minLon: 66.5,
      minLat: 23.5,
      maxLon: 68.5,
      maxLat: 24.8,
    })
    expect(getPolygonVertexCount(polygon)).toBe(4)
  })
})
