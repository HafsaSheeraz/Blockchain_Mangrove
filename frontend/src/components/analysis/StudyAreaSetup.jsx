import { formatDecimal } from '../../utils/formatters'
import { getPolygonBounds, getPolygonVertexCount } from '../../utils/geo'

function formatBound(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'N/A'
  }
  return formatDecimal(value, 4)
}

export default function StudyAreaSetup({
  studyAreaMode,
  selectedRegionId,
  regions,
  startDate,
  endDate,
  activeAoi,
  customAoi,
  validationErrors,
  onModeChange,
  onRegionChange,
  onStartDateChange,
  onEndDateChange,
  onClearCustomAoi,
}) {
  const bounds = getPolygonBounds(activeAoi)
  const activeVertexCount = getPolygonVertexCount(activeAoi)
  const customVertexCount = getPolygonVertexCount(customAoi)

  return (
    <section className="setup-panel" aria-labelledby="setup-title">
      <h2 id="setup-title" className="panel-title">Study Area &amp; Analysis Setup</h2>
      <p className="setup-desc">
        Choose a predefined region or draw a custom AOI, then review the derived request summary below.
      </p>

      <fieldset className="mode-fieldset">
        <legend className="mode-legend">Study area mode</legend>
        <div className="mode-segmented" role="radiogroup" aria-label="Study area mode options">
          <label className={`mode-option mode-option-segmented ${studyAreaMode === 'predefined' ? 'is-active' : ''}`}>
          <input
            type="radio"
            name="studyAreaMode"
            value="predefined"
            checked={studyAreaMode === 'predefined'}
            onChange={() => onModeChange('predefined')}
          />
          <span>Predefined Region</span>
          </label>
          <label className={`mode-option mode-option-segmented ${studyAreaMode === 'custom' ? 'is-active' : ''}`}>
          <input
            type="radio"
            name="studyAreaMode"
            value="custom"
            checked={studyAreaMode === 'custom'}
            onChange={() => onModeChange('custom')}
          />
          <span>Custom AOI</span>
          </label>
        </div>
      </fieldset>

      <div className="setup-grid">
        <div className="field-group">
          <label className="field-label" htmlFor="regionSelect">Region</label>
          <select
            id="regionSelect"
            className="field-input"
            value={selectedRegionId}
            onChange={(event) => onRegionChange(event.target.value)}
            disabled={studyAreaMode !== 'predefined'}
          >
            {regions.map((region) => (
              <option key={region.id} value={region.id}>
                {region.name}, {region.country}
              </option>
            ))}
          </select>
        </div>

        <div className="field-group">
          <label className="field-label" htmlFor="startDateInput">Start date</label>
          <input
            id="startDateInput"
            type="date"
            className="field-input"
            value={startDate}
            onChange={(event) => onStartDateChange(event.target.value)}
          />
        </div>

        <div className="field-group">
          <label className="field-label" htmlFor="endDateInput">End date</label>
          <input
            id="endDateInput"
            type="date"
            className="field-input"
            value={endDate}
            onChange={(event) => onEndDateChange(event.target.value)}
          />
        </div>
      </div>

      {studyAreaMode === 'custom' && (
        <div className="custom-controls">
          <button
            type="button"
            className="clear-btn"
            onClick={onClearCustomAoi}
            disabled={!customAoi}
          >
            Clear custom AOI
          </button>
          <p className="custom-hint">
            Draw, edit, or delete a polygon directly on the map. Custom AOI is preserved if you switch back to a predefined region.
          </p>
        </div>
      )}

      <div className="aoi-summary" aria-live="polite">
        <h3 className="summary-title">AOI summary</h3>
        <p><strong>Active mode:</strong> {studyAreaMode === 'custom' ? 'Custom AOI' : 'Predefined region'}</p>
        <p><strong>Polygon vertices:</strong> {activeVertexCount || 'Unavailable'}</p>
        {bounds ? (
          <p>
            <strong>Bounds (lon/lat):</strong>{' '}
            [{formatBound(bounds.minLon)}, {formatBound(bounds.minLat)}] to [{formatBound(bounds.maxLon)}, {formatBound(bounds.maxLat)}]
          </p>
        ) : (
          <p><strong>Bounds:</strong> Unavailable</p>
        )}
        {studyAreaMode === 'custom' && (
          <p><strong>Saved custom vertices:</strong> {customVertexCount || 'None'}</p>
        )}
      </div>

      {validationErrors.length > 0 && (
        <div className="validation-list" role="alert">
          <h3 className="summary-title">Input validation</h3>
          <ul>
            {validationErrors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
