import { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import { FeatureGroup, MapContainer, Polygon, TileLayer, useMap } from 'react-leaflet'
import { getPolygonBounds, normalizePolygonGeometry, polygonToLeafletLatLngs } from '../../utils/geo'
import LayerControls from './mapLayers/LayerControls'
import LayerLegend from './mapLayers/LayerLegend'
import RasterTileLayers from './mapLayers/RasterTileLayers'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import 'leaflet-draw'

function FitMapToGeometry({ geometry, center, zoom }) {
  const map = useMap()

  useEffect(() => {
    const bounds = getPolygonBounds(geometry)
    if (bounds) {
      map.fitBounds([
        [bounds.minLat, bounds.minLon],
        [bounds.maxLat, bounds.maxLon],
      ], { padding: [20, 20], maxZoom: 13 })
      return
    }
    map.setView(center, zoom)
  }, [map, geometry, center, zoom])

  return null
}

function DrawControls({ studyAreaMode, featureGroupRef, onCustomAoiChange }) {
  const map = useMap()

  useEffect(() => {
    if (studyAreaMode !== 'custom' || !featureGroupRef.current) {
      return undefined
    }

    const featureGroup = featureGroupRef.current
    const drawControl = new L.Control.Draw({
      position: 'topright',
      draw: {
        rectangle: false,
        circle: false,
        circlemarker: false,
        marker: false,
        polyline: false,
        polygon: {
          allowIntersection: false,
          showArea: false,
        },
      },
      edit: {
        featureGroup,
      },
    })

    const handleCreated = (event) => {
      const layer = event.layer
      const normalized = normalizePolygonGeometry(layer.toGeoJSON().geometry)
      if (!normalized) {
        onCustomAoiChange(null)
        return
      }
      featureGroup.clearLayers()
      featureGroup.addLayer(layer)
      onCustomAoiChange(normalized)
    }

    const handleEdited = (event) => {
      const editedLayers = event.layers.getLayers()
      if (editedLayers.length === 0) {
        return
      }
      const normalized = normalizePolygonGeometry(editedLayers[0].toGeoJSON().geometry)
      onCustomAoiChange(normalized)
    }

    const handleDeleted = () => {
      onCustomAoiChange(null)
    }

    map.addControl(drawControl)
    map.on(L.Draw.Event.CREATED, handleCreated)
    map.on(L.Draw.Event.EDITED, handleEdited)
    map.on(L.Draw.Event.DELETED, handleDeleted)

    return () => {
      map.off(L.Draw.Event.CREATED, handleCreated)
      map.off(L.Draw.Event.EDITED, handleEdited)
      map.off(L.Draw.Event.DELETED, handleDeleted)
      map.removeControl(drawControl)
    }
  }, [map, studyAreaMode, featureGroupRef, onCustomAoiChange])

  return null
}

export default function StudyAreaMap({
  studyAreaMode,
  selectedRegion,
  predefinedAoi,
  customAoi,
  onCustomAoiChange,
  analyzedAoiGeometry,
  mapLayers,
  mapLayerVisibilityById,
  mapLayerOpacityById,
  onToggleMapLayer,
  onChangeMapLayerOpacity,
  onResetMapLayerDefaults,
  mapLayerWarnings,
  mapLayerMessage,
}) {
  const featureGroupRef = useRef(null)
  const defaultCenter = selectedRegion?.map?.center ?? [24.15, 67.5]
  const defaultZoom = selectedRegion?.map?.zoom ?? 9
  const displayedGeometry = studyAreaMode === 'custom' ? customAoi : predefinedAoi
  const analyzedGeometry = useMemo(
    () => normalizePolygonGeometry(analyzedAoiGeometry),
    [analyzedAoiGeometry],
  )
  const fitGeometry = analyzedGeometry || displayedGeometry
  const displayedPolygonLatLngs = useMemo(
    () => polygonToLeafletLatLngs(displayedGeometry),
    [displayedGeometry],
  )
  const analyzedPolygonLatLngs = useMemo(
    () => polygonToLeafletLatLngs(analyzedGeometry),
    [analyzedGeometry],
  )
  const activeLegendLayer = useMemo(
    () => (Array.isArray(mapLayers) ? mapLayers.find((layer) => mapLayerVisibilityById[layer.id]) || mapLayers[0] : null),
    [mapLayers, mapLayerVisibilityById],
  )

  useEffect(() => {
    if (!featureGroupRef.current) {
      return
    }
    const group = featureGroupRef.current
    group.clearLayers()
    if (studyAreaMode === 'custom' && customAoi) {
      const latLngs = polygonToLeafletLatLngs(customAoi)
      if (latLngs.length > 0) {
        const layer = L.polygon(latLngs)
        group.addLayer(layer)
      }
    }
  }, [studyAreaMode, customAoi])

  return (
    <section className="map-panel" aria-labelledby="aoi-map-title">
      <div className="map-header">
        <h2 id="aoi-map-title" className="panel-title">Interactive AOI Map</h2>
        <p className="map-note">
          Coordinates are stored in GeoJSON order [longitude, latitude]. The active study area and overlays remain visible for context.
        </p>
      </div>
      <div className="map-canvas-wrap">
        <MapContainer
          center={defaultCenter}
          zoom={defaultZoom}
          className="aoi-map"
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitMapToGeometry geometry={fitGeometry} center={defaultCenter} zoom={defaultZoom} />

          <RasterTileLayers
            layers={mapLayers}
            visibilityById={mapLayerVisibilityById}
            opacityById={mapLayerOpacityById}
          />

          {studyAreaMode === 'predefined' && displayedPolygonLatLngs.length > 0 && (
            <Polygon positions={displayedPolygonLatLngs} pathOptions={{ color: '#0d6b61', weight: 2 }} />
          )}
          {analyzedPolygonLatLngs.length > 0 && (
            <Polygon positions={analyzedPolygonLatLngs} pathOptions={{ color: '#0f172a', weight: 3, dashArray: '8 6', fill: false }} />
          )}

          <FeatureGroup ref={featureGroupRef} />
          <DrawControls
            studyAreaMode={studyAreaMode}
            featureGroupRef={featureGroupRef}
            onCustomAoiChange={onCustomAoiChange}
          />
        </MapContainer>
      </div>
      {Array.isArray(mapLayerWarnings) && mapLayerWarnings.length > 0 && (
        <div className="validation-list" role="status" aria-live="polite">
          <h3 className="summary-title">Map-layer warnings</h3>
          <ul>
            {mapLayerWarnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}
      {mapLayerMessage && (
        <p className="custom-hint">{mapLayerMessage}</p>
      )}
      <LayerControls
        layers={mapLayers}
        visibilityById={mapLayerVisibilityById}
        opacityById={mapLayerOpacityById}
        onToggleLayer={onToggleMapLayer}
        onOpacityChange={onChangeMapLayerOpacity}
        onResetDefaults={onResetMapLayerDefaults}
      />
      <LayerLegend layer={activeLegendLayer} />
      <p className="map-mode-note">
        {studyAreaMode === 'custom'
          ? 'Custom mode: use draw controls to create, edit, or delete one polygon.'
          : `Predefined mode: showing ${selectedRegion?.name}, ${selectedRegion?.country}.`}
      </p>
    </section>
  )
}
