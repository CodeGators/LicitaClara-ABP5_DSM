import { useState } from 'react'

export default function FilterPanel({ title, primary, advanced, appliedCount = 0, apply, clear, applyLabel = 'Aplicar filtros', clearLabel = 'Limpar filtros', ariaLabel = 'Filtros do recorte', twoColumns = false, singleColumn = false, children }) {
  const [expanded, setExpanded] = useState(false)
  const Container = apply ? 'form' : 'section'
  return <Container className="card item-filters" aria-label={ariaLabel} onSubmit={apply}>
    <h2>{title}</h2>
    <div className={`item-filters-primary${singleColumn ? ' item-filters-one' : twoColumns ? ' item-filters-two' : ''}`}>{primary}</div>
    {advanced && <details className="item-filters-advanced" open={expanded} onToggle={e => setExpanded(e.currentTarget.open)}>
      <summary>Mais filtros{appliedCount > 0 && <span className="pill ana">{appliedCount} aplicado(s)</span>}</summary>
      {expanded && advanced}
    </details>}
    {(apply || clear) && <div className="filter-actions">{apply && <button className="btn primary" type="submit">{applyLabel}</button>}{clear && <button className="btn ghost" type="button" onClick={clear}>{clearLabel}</button>}</div>}
    {children}
  </Container>
}
