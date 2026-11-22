// Presentation rule, not an IF cutoff or proof of a source error.
export const PRICE_REVIEW_LABEL = 'Requer validação'

export function requiresPriceReview(price, median, basis) {
  if (!basis) return false
  // Compare original decimal strings, before display rounding (strictly > 500%).
  const parts = value => /^(\d+)(?:\.(\d+))?$/.exec(String(value ?? ''))
  const p = parts(price), m = parts(median)
  if (!p || !m) return false
  const scale = Math.max(p[2]?.length || 0, m[2]?.length || 0)
  const integer = match => BigInt(match[1] + (match[2] || '').padEnd(scale, '0'))
  const reference = integer(m)
  return reference > 0n && integer(p) > reference * 6n
}

export function itemRequiresPriceReview(item) {
  return (item.scores || []).some(score => {
    const reference = score.atributos?.comparacao
    const result = item.resultados?.find(r => r.id === score.resultado_item_id)
    return requiresPriceReview(result?.valor_unitario_homologado, reference?.mediana, reference?.unidade_preco?.unidade_preco)
  })
}
