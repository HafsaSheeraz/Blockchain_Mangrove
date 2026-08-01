import { TileLayer } from 'react-leaflet'

export default function RasterTileLayers({ layers, visibilityById, opacityById }) {
  if (!Array.isArray(layers) || layers.length === 0) {
    return null
  }

  return (
    <>
      {layers
        .filter((layer) => visibilityById[layer.id])
        .map((layer) => (
          <TileLayer
            key={`raster-layer-${layer.id}`}
            url={layer.tile_url_template}
            opacity={opacityById[layer.id] ?? layer.default_opacity ?? 1}
            zIndex={600}
            crossOrigin
          />
        ))}
    </>
  )
}
