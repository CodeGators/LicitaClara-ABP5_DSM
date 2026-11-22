// Visual thresholds chosen for the interface, not probabilities or validated risk levels.
export function ifBand(product) {
  const value = product.medida_if
  if (product.requer_validacao || value == null || String(value).trim() === '') return ''
  if (typeof value !== 'string' && typeof value !== 'number') return ''
  const measure = Number(value)
  if (!Number.isFinite(measure) || measure < 0 || measure > 1) return ''
  return measure >= 0.70 ? 'red' : measure >= 0.50 ? 'yellow' : 'green'
}

export const ifBandLabels = {
  green: 'Faixa visual IF: abaixo de 0,50',
  yellow: 'Faixa visual IF: de 0,50 até menos de 0,70',
  red: 'Faixa visual IF: de 0,70 a 1',
}
