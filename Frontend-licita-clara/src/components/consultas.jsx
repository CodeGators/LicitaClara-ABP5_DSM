import { cloneElement, useId, useState } from 'react'
import { date, decimal, exactDecimal, money, safeOfficialUrl } from '../api.mjs'
import useApi from '../useApi.js'

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
export function LookupFilter({ kind, title, value, onChange, baseId, compact = false }) {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [label, setLabel] = useState('')
  const query = useApi(kind, { base_id: baseId, busca: search, pagina: page, tamanho_pagina: 20 }, !!baseId)
  const options = query.data?.dados || []
  return <div className="lookup-filter">
    <Field label={`Buscar ${title.toLowerCase()}`}><input className="input" type="search" maxLength={200} value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} /></Field>
    <Field label={title}><select className="select" value={value} onChange={e => { setLabel(options.find(o => o.id === e.target.value)?.nome || ''); onChange(e.target.value) }}>
      <option value="">Todos</option>
      {value && !options.some(o => o.id === value) && <option value={value}>{label || `${title} selecionado`}</option>}
      {options.map(o => <option key={o.id} value={o.id}>{o.nome}</option>)}
    </select></Field>
    {query.loading && <small role="status">Carregando opções…</small>}
    {query.error && <div role="alert">Não foi possível carregar as opções. <button type="button" className="link-a" onClick={query.retry}>Tentar novamente</button></div>}
    {query.data?.meta.total_paginas > 1 && <div className="pager"><button className="btn ghost sm" type="button" disabled={page === 1 || query.loading} onClick={() => setPage(p => p - 1)}>{compact ? 'Lista anterior' : 'Opções anteriores'}</button><small>{compact ? `${title}: página ${page} de ${query.data.meta.total_paginas}` : `${page}/${query.data.meta.total_paginas}`}</small><button className="btn ghost sm" type="button" disabled={page >= query.data.meta.total_paginas || query.loading} onClick={() => setPage(p => p + 1)}>{compact ? 'Próxima lista' : 'Mais opções'}</button></div>}
  </div>
}

// Mantido fora das telas para reutilizar o contrato de resultados por fornecedor.
export function Results({ results, hideStatus = false }) {
  return <div className="card"><h2>Resultados do item</h2><p className="sub">Preço e quantidade por fornecedor. Resultados cancelados ficam fora do total.</p>
    {!results.length ? <p className="sub">Nenhum resultado conhecido nesta base.</p> : <div className="table-scroll" role="region" aria-label="Resultados do item; use as setas para rolar na horizontal" tabIndex={0}><table className="tbl"><thead><tr><th scope="col">Fornecedor</th><th scope="col">Quantidade homologada</th><th scope="col">Preço unitário</th><th scope="col">Total homologado</th><th scope="col">Data do resultado</th>{!hideStatus && <th scope="col">Situação</th>}</tr></thead><tbody>{results.map(r => <tr key={r.id}><td>{r.fornecedor_nome}</td><td>{decimal(r.quantidade_homologada)}</td><td title={`Valor original: ${exactDecimal(r.valor_unitario_homologado)}`}>{money(r.valor_unitario_homologado)}</td><td>{money(r.valor_total_homologado)}</td><td>{date(r.data_resultado)}</td>{!hideStatus && <td>{r.cancelado ? 'Cancelado' : 'Não cancelado'}<small>{r.situacao}</small></td>}</tr>)}</tbody></table></div>}
  </div>
}

export function Documents({ processId, baseId }) {
  const [page, setPage] = useState(1)
  const query = useApi(`/processos/${processId}/documentos`, { base_id: baseId, pagina: page, tamanho_pagina: 10 })
  return <section className="card"><h2>Documentos da compra e contratos vinculados</h2><p className="sub">Os links abrem a fonte oficial. Um documento da compra pode não tratar especificamente deste item.</p>
    <QueryState query={query} loading="Carregando documentos…" />
    {query.data && <>
      {!query.data.dados.length ? <p className="sub">Nenhum documento conhecido nesta base.</p> : <ul className="document-list">{query.data.dados.map(d => {
        const url = safeOfficialUrl(d.url_origem)
        return <li key={d.id}>{url ? <a className="link-a" href={url} target="_blank" rel="noopener noreferrer">{d.titulo || 'Documento sem título'} ↗</a> : <span>{d.titulo || 'Documento sem título'} · Link indisponível</span>}<small>{d.tipo_nome || 'Tipo não informado'} · {d.contrato_versao_id ? 'Contrato vinculado' : 'Compra'} · Publicação: {date(d.publicado_na_origem_em)} · {d.ativo === true ? 'Ativo' : d.ativo === false ? 'Inativo' : 'Situação desconhecida'}</small></li>
      })}</ul>}
      <Pager meta={query.data.meta} onChange={setPage} />
    </>}
  </section>
}

export function Pager({ meta, onChange }) {
  return <div className="mini pagination"><span>{meta.total} registro(s){meta.total_paginas ? ` · página ${meta.pagina} de ${meta.total_paginas}` : ''}</span><div className="pager">{meta.pagina > 1 && <button className="btn ghost sm" onClick={() => onChange(1)}>Primeira página</button>}<button className="btn ghost sm" disabled={meta.pagina <= 1} onClick={() => onChange(meta.pagina - 1)}>Anterior</button><button className="btn ghost sm" disabled={meta.pagina >= meta.total_paginas} onClick={() => onChange(meta.pagina + 1)}>Próxima</button></div></div>
}
