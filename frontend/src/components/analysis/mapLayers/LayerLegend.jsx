function LegendScale({ min, max, palette, units }) {
  const gradient = `linear-gradient(90deg, ${palette.join(',')})`
  return (
    <div className="map-layer-legend-scale">
      <div className="map-layer-legend-gradient" style={{ background: gradient }} aria-hidden="true" />
      <div className="map-layer-legend-range">
        <span>{min}</span>
        <span>{max} {units}</span>
      </div>
    </div>
  )
}

export default function LayerLegend({ layer }) {
  if (!layer) {
    return null
  }
  return (
    <section className="map-layer-legend" aria-label="Scientific map legend">
      <h3 className="summary-title">{layer.name} legend</h3>
      <p className="custom-hint">{layer.description}</p>
      {layer.legend_type === 'categorical' ? (
        <div className="map-layer-legend-categorical" role="img" aria-label={`Colour key: ${layer.units}`}>
          <span className="map-layer-legend-chip" style={{ backgroundColor: layer.palette?.[0] ?? '#2e8b57' }} aria-hidden="true" />
          <span className="map-layer-legend-label">{layer.units}</span>
        </div>
      ) : (
        <LegendScale min={layer.min} max={layer.max} palette={layer.palette ?? []} units={layer.units} />
      )}
    </section>
  )
}
