export default function FilterPanel({ title, primary, apply, clear, applyLabel = 'Aplicar filtros', clearLabel = 'Limpar filtros', ariaLabel = 'Filtros do recorte', children }) {
  const Container = apply ? 'form' : 'section'
  return <Container className="card item-filters" aria-label={ariaLabel} onSubmit={apply}>
    <h2 className="sr-only">{title}</h2>
    <div className="toolbar-row">
      <div className="item-filters-primary">{primary}</div>
      {(apply || clear) && <div className="filter-actions">{apply && <button className="btn primary" type="submit">{applyLabel}</button>}{clear && <button className="btn ghost" type="button" onClick={clear}>{clearLabel}</button>}</div>}
    </div>
    {children}
  </Container>
}
