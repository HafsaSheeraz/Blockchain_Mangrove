import { StrictMode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import RasterTileLayers from '../components/analysis/mapLayers/RasterTileLayers'

vi.mock('react-leaflet', () => ({
  TileLayer: ({ url }) => <div data-testid="tile-layer">{url}</div>,
}))

describe('RasterTileLayers', () => {
  it('renders one tile layer per visible descriptor in stable order', () => {
    const layers = [
      { id: 'gmw', tile_url_template: 'https://earthengine.googleapis.com/a', default_opacity: 0.6 },
      { id: 'gedi', tile_url_template: 'https://earthengine.googleapis.com/b', default_opacity: 0.6 },
      { id: 'carbon', tile_url_template: 'https://earthengine.googleapis.com/c', default_opacity: 0.6 },
    ]
    render(
      <RasterTileLayers
        layers={layers}
        visibilityById={{ gmw: true, gedi: false, carbon: true }}
        opacityById={{ gmw: 0.5, carbon: 0.8 }}
      />,
    )
    const rendered = screen.getAllByTestId('tile-layer')
    expect(rendered).toHaveLength(2)
    expect(rendered[0].textContent).toContain('/a')
    expect(rendered[1].textContent).toContain('/c')
  })

  it('does not duplicate tile layers under StrictMode', () => {
    const layers = [
      { id: 'gmw', tile_url_template: 'https://earthengine.googleapis.com/a', default_opacity: 0.6 },
      { id: 'gedi', tile_url_template: 'https://earthengine.googleapis.com/b', default_opacity: 0.6 },
    ]
    render(
      <StrictMode>
        <RasterTileLayers
          layers={layers}
          visibilityById={{ gmw: true, gedi: true }}
          opacityById={{ gmw: 0.6, gedi: 0.7 }}
        />
      </StrictMode>,
    )
    expect(screen.getAllByTestId('tile-layer')).toHaveLength(2)
  })
})
