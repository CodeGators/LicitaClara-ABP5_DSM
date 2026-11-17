import { useState } from 'react'

// Barra de filtros: o essencial (busca e ordenação) fica à vista; o restante, em "Mais filtros".
export default function FilterPanel({ title, primary, advanced, appliedCount = 0, apply, clear, applyLabel = 'Aplicar filtros', clearLabel = 'Limpar filtros', ariaLabel = 'Filtros do recorte', children }) {
  const [expanded, setExpanded] = useState(false)
  const Container = apply ? 'form' : 'section'
  return <Container className="card item-filters" aria-label={ariaLabel} onSubmit={apply}>
    <h2 className="sr-only">{title}</h2>
    <div className="toolbar-row">
      <div className="item-filters-primary">{primary}</div>
      {(apply || clear) && <div className="filter-actions">{apply && <button className="btn primary" type="submit">{applyLabel}</button>}{clear && <button className="btn ghost" type="button" onClick={clear}>{clearLabel}</button>}</div>}
    </div>
    {advanced && <details className="item-filters-advanced" open={expanded} onToggle={e => setExpanded(e.currentTarget.open)}>
      <summary>Mais filtros{appliedCount > 0 && <span className="pill ana">{appliedCount} aplicado(s)</span>}</summary>
      {expanded && advanced}
    </details>}
    {children}
  </Container>
}
