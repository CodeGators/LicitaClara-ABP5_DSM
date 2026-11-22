import { PRICE_REVIEW_LABEL } from '../priceValidation.mjs'

export default function PriceReview() {
  return <div className="price-review"><strong className="pill media">{PRICE_REVIEW_LABEL}</strong></div>
}
