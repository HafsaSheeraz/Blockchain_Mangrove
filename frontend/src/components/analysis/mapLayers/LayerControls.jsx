export default function LayerControls({
  layers,
  visibilityById,
  opacityById,
  onToggleLayer,
  onOpacityChange,
  onResetDefaults,
}) {
  if (!Array.isArray(layers) || layers.length === 0) {
    return null
  }

  return (
    <section className="map-layer-controls" aria-label="Map layer controls">
      <div className="map-layer-controls-header">
        <h3 className="summary-title">Layer controls</h3>
        {onResetDefaults && (
          <button type="button" className="reset-defaults-btn" onClick={onResetDefaults}>
            Reset defaults
          </button>
        )}
      </div>
      <ul className="map-layer-controls-list">
        {layers.map((layer) => (
          <li key={layer.id} className="map-layer-control-item">
            <label className="mode-option">
              <input
                type="checkbox"
                checked={Boolean(visibilityById[layer.id])}
                onChange={(event) => onToggleLayer(layer.id, event.target.checked)}
              />
              {layer.name}
            </label>
            <label className="field-label" htmlFor={`opacity-${layer.id}`}>
              Opacity ({Math.round((opacityById[layer.id] ?? layer.default_opacity ?? 1) * 100)}%)
            </label>
            <input
              id={`opacity-${layer.id}`}
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={opacityById[layer.id] ?? layer.default_opacity ?? 1}
              onChange={(event) => onOpacityChange(layer.id, Number(event.target.value))}
            />
          </li>
        ))}
      </ul>
    </section>
  )
}
