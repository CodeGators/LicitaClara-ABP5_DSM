import { cloneElement, useId, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { baseLink, date, decimal, money, safeOfficialUrl, selectionLink } from '../api.mjs'
import useApi from '../useApi.js'

export function QueryState({ query, loading = 'Carregando…' }) {
  if (query.loading) return <div className="card" role="status" aria-live="polite">{loading}</div>
  if (!query.error) return null
  const { error } = query
  return <div className="card query-error" role="alert"><h2>{error.status === 404 ? 'Registro não encontrado' : error.status === 422 ? 'Consulta inválida' : 'Consulta indisponível'}</h2><p className="sub">{error.message}</p>{error.requestId && <p className="hint">Referência do atendimento: {error.requestId}</p>}<button className="btn ghost sm" onClick={query.retry}>Tentar novamente</button></div>
}

export function Field({ label, children }) {
  const id = useId()
  return <div className="field"><label htmlFor={id}>{label}</label>{cloneElement(children, { id })}</div>
}
export const Info = ({ label, children }) => <div><small>{label}</small><strong>{children}</strong></div>
export const NoAnalysis = () => <div className="note"><b>Análise não publicada</b>Não há prioridade de auditoria validada. O canal experimental, quando selecionado, pode ser consultado no detalhe e no ranking. Ausência de score não representa conclusão sobre regularidade.</div>

export function LookupFilter({ kind, title, value, onChange, baseId }) {
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
    {query.data?.meta.total_paginas > 1 && <div className="pager"><button type="button" disabled={page === 1 || query.loading} onClick={() => setPage(p => p - 1)}>Opções anteriores</button><small>{page}/{query.data.meta.total_paginas}</small><button type="button" disabled={page >= query.data.meta.total_paginas || query.loading} onClick={() => setPage(p => p + 1)}>Mais opções</button></div>}
  </div>
}

// Mantido fora das telas para reutilizar o contrato de resultados por fornecedor.
export function Results({ results }) {
  return <div className="card"><h2>Resultados do item</h2><p className="sub">Preços e quantidades por fornecedor. Resultados cancelados não entram no total homologado do item.</p>
    {!results.length ? <p className="sub">Nenhum resultado conhecido nesta base.</p> : <div className="table-scroll"><table className="tbl"><thead><tr><th>Fornecedor</th><th>Quantidade homologada</th><th>Preço unitário</th><th>Total homologado</th><th>Data do resultado</th><th>Situação</th></tr></thead><tbody>{results.map(r => <tr key={r.id}><td>{r.fornecedor_nome}</td><td>{decimal(r.quantidade_homologada)}</td><td>{money(r.valor_unitario_homologado)}</td><td>{money(r.valor_total_homologado)}</td><td>{date(r.data_resultado)}</td><td>{r.cancelado ? 'Cancelado' : 'Não cancelado'}<small>{r.situacao}</small></td></tr>)}</tbody></table></div>}
  </div>
}

export function Documents({ processId, baseId }) {
  const [page, setPage] = useState(1)
  const query = useApi(`/processos/${processId}/documentos`, { base_id: baseId, pagina: page, tamanho_pagina: 10 })
  return <section className="card"><h2>Documentos da compra e contratos vinculados</h2><p className="sub">A presença de um documento da compra não comprova que ele trate especificamente deste item. Os links abrem a fonte oficial.</p>
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
  return <div className="mini pagination"><span>{meta.total} registro(s) · {meta.total_paginas ? `Página ${meta.pagina} de ${meta.total_paginas}` : 'Nenhuma página de resultados'}</span><div className="pager">{meta.pagina > 1 && <button className="btn ghost sm" onClick={() => onChange(1)}>Primeira página</button>}<button className="btn ghost sm" disabled={meta.pagina <= 1} onClick={() => onChange(meta.pagina - 1)}>Anterior</button><button className="btn ghost sm" disabled={meta.pagina >= meta.total_paginas} onClick={() => onChange(meta.pagina + 1)}>Próxima</button></div></div>
}

export function ItemTable({ items, baseId, from }) {
  const location = useLocation()
  const selected = new URLSearchParams(location.search).get('execucao_id')
  return <div className="table-scroll"><table className="tbl"><thead><tr><th>Item</th><th>Órgão / compra</th><th>Fornecedores com resultados não cancelados</th><th>Total homologado do item</th><th>Análise</th></tr></thead><tbody>{items.map(item => {
    const suppliers = [...new Set(item.resultados.filter(r => !r.cancelado).map(r => r.fornecedor_nome))]
    return <tr key={item.id}><td><Link className="link-a" to={selected ? selectionLink(`/itens/${item.id}`, location.search) : baseLink(`/itens/${item.id}`, baseId)} state={{ from }}>{item.descricao}</Link><small>Item {item.numero_item} · {item.catalogo ? `${item.catalogo} ${item.codigo_catalogo}` : 'Catálogo não informado'}</small></td><td>{item.processo.orgao_nome}<small>Compra {item.processo.numero_compra}</small></td><td>{suppliers.length ? suppliers.join('; ') : 'Não informado'}</td><td>{money(item.valor_homologado_item)}{item.resultados_sem_valor_total > 0 && <small>Total incompleto na fonte</small>}</td><td><span className="pill rev">{selected && selected !== 'nenhuma' ? 'Consultar análise no detalhe' : 'Não publicada'}</span></td></tr>
  })}</tbody></table></div>
}
