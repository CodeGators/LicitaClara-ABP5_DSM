import { cloneElement, useId } from 'react'
import { date, decimal, exactDecimal, money } from '../api.mjs'

export function QueryState({ query, loading = 'Carregando…' }) {
  if (query.loading) return <div className="card skeleton" role="status" aria-live="polite" aria-label={loading}><i /><i /><i /><span className="sr-only">{loading}</span></div>
  if (!query.error) return null
  const { error } = query
  return <div className="card query-error" role="alert"><h2>{error.status === 404 ? 'Registro não encontrado' : error.status === 422 ? 'Consulta inválida' : 'Consulta indisponível'}</h2><p className="sub">{error.message}</p>{error.status === 422 && <p className="sub">Confira o intervalo de datas, os valores mínimo e máximo e as opções selecionadas.</p>}{error.requestId && <p className="hint">Referência do atendimento: {error.requestId}</p>}<button className="btn ghost sm" onClick={query.retry}>Tentar novamente</button></div>
}

export function Field({ label, children }) {
  const id = useId()
  const control = ['input', 'select', 'textarea'].includes(children.type)
  return <div className="field">{control ? <label htmlFor={id}>{label}</label> : <span id={id} className="field-label">{label}</span>}{cloneElement(children, control ? { id } : { role: 'group', 'aria-labelledby': id })}</div>
}
export const Info = ({ label, children, title }) => <div><small>{label}</small><strong title={title}>{children}</strong></div>
export function Results({ results }) {
  return <div className="card"><h2>Resultados do item</h2><p className="sub">Preço e quantidade por fornecedor. Resultados cancelados ficam fora do total.</p>
    {!results.length ? <p className="sub">Nenhum resultado conhecido nesta base.</p> : <div className="table-scroll" role="region" aria-label="Resultados do item; use as setas para rolar na horizontal" tabIndex={0}><table className="tbl"><thead><tr><th scope="col">Fornecedor</th><th scope="col">Quantidade homologada</th><th scope="col">Preço unitário</th><th scope="col">Total homologado</th><th scope="col">Data do resultado</th></tr></thead><tbody>{results.map(r => <tr key={r.id}><td>{r.fornecedor_nome}</td><td>{decimal(r.quantidade_homologada)}</td><td title={`Valor original: ${exactDecimal(r.valor_unitario_homologado)}`}>{money(r.valor_unitario_homologado)}</td><td>{money(r.valor_total_homologado)}</td><td>{date(r.data_resultado)}</td></tr>)}</tbody></table></div>}
  </div>
}

export function Pager({ meta, onChange }) {
  return <div className="mini pagination"><span>{meta.total} registro(s){meta.total_paginas ? ` · página ${meta.pagina} de ${meta.total_paginas}` : ''}</span><div className="pager">{meta.pagina > 1 && <button className="btn ghost sm" onClick={() => onChange(1)}>Primeira página</button>}<button className="btn ghost sm" disabled={meta.pagina <= 1} onClick={() => onChange(meta.pagina - 1)}>Anterior</button><button className="btn ghost sm" disabled={meta.pagina >= meta.total_paginas} onClick={() => onChange(meta.pagina + 1)}>Próxima</button></div></div>
}
