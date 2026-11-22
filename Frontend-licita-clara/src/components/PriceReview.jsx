import { PRICE_REVIEW_LABEL, PRICE_REVIEW_REASON } from '../priceValidation.mjs'

export default function PriceReview({ compact = false }) {
  return <div className="price-review"><strong className="pill media" title={PRICE_REVIEW_REASON}>{PRICE_REVIEW_LABEL}</strong>{!compact && <><p>{PRICE_REVIEW_REASON}</p><p className="hint">Preço mais de 500% acima da mediana histórica (mais de 6 vezes a referência). Limite provisório de conferência; o registro e a análise permanecem disponíveis.</p></>}</div>
}
