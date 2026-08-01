export function rectangleBoundsToPolygon(bounds) {
  const [minLon, minLat, maxLon, maxLat] = bounds
  return {
    type: 'Polygon',
    coordinates: [[
      [minLon, minLat],
      [maxLon, minLat],
      [maxLon, maxLat],
      [minLon, maxLat],
      [minLon, minLat],
    ]],
  }
}

function isCoordinatePair(value) {
  return (
    Array.isArray(value)
    && value.length === 2
    && Number.isFinite(value[0])
    && Number.isFinite(value[1])
  )
}

function closeLinearRing(ring) {
  if (!Array.isArray(ring) || ring.length < 3) {
    return null
  }
  const normalized = ring.filter(isCoordinatePair).map(([lon, lat]) => [lon, lat])
  if (normalized.length < 3) {
    return null
  }
  const first = normalized[0]
  const last = normalized[normalized.length - 1]
  if (first[0] !== last[0] || first[1] !== last[1]) {
    normalized.push([first[0], first[1]])
  }
  return normalized
}

export function normalizePolygonGeometry(geometry) {
  if (!geometry || geometry.type !== 'Polygon' || !Array.isArray(geometry.coordinates)) {
    return null
  }
  const outerRing = closeLinearRing(geometry.coordinates[0])
  if (!outerRing) {
    return null
  }
  return {
    type: 'Polygon',
    coordinates: [outerRing],
  }
}

export function lonLatToLeafletLatLng([lon, lat]) {
  return [lat, lon]
}

export function polygonToLeafletLatLngs(geometry) {
  const normalized = normalizePolygonGeometry(geometry)
  if (!normalized) {
    return []
  }
  return normalized.coordinates[0].map(lonLatToLeafletLatLng)
}

export function getPolygonBounds(geometry) {
  const normalized = normalizePolygonGeometry(geometry)
  if (!normalized) {
    return null
  }
  const ring = normalized.coordinates[0]
  const longitudes = ring.map(([lon]) => lon)
  const latitudes = ring.map(([, lat]) => lat)
  return {
    minLon: Math.min(...longitudes),
    minLat: Math.min(...latitudes),
    maxLon: Math.max(...longitudes),
    maxLat: Math.max(...latitudes),
  }
}

export function getPolygonVertexCount(geometry) {
  const normalized = normalizePolygonGeometry(geometry)
  if (!normalized) {
    return 0
  }
  return Math.max(0, normalized.coordinates[0].length - 1)
}
