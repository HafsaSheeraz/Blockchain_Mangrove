export function formatInteger(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'N/A'
  }
  return value.toLocaleString('en-US', { maximumFractionDigits: 0 })
}

export function formatDecimal(value, digits = 2) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'N/A'
  }
  return value.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function formatRange(minValue, maxValue, digits = 2) {
  return `${formatDecimal(minValue, digits)}–${formatDecimal(maxValue, digits)}`
}

export function formatPercent(value, digits = 2) {
  return `${formatDecimal(value, digits)}%`
}

export function withUnit(valueText, unit) {
  if (!valueText || valueText === 'N/A') {
    return 'N/A'
  }
  return `${valueText} ${unit}`
}
