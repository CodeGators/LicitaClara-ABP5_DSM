import { useEffect, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { Head, Aviso } from '../components/ui.jsx'
import { Field, ItemTable, LookupFilter, NoAnalysis, Pager, QueryState } from '../components/consultas.jsx'
import { useBase } from '../BaseContext.jsx'
import useApi from '../useApi.js'

const names = ['busca', 'orgao_id', 'fornecedor_id', 'modalidade_id', 'processo_id', 'homologacao_inicio', 'homologacao_fim', 'valor_minimo', 'valor_maximo', 'ordenacao', 'tamanho_pagina']
const readFilters = params => Object.fromEntries(names.map(key => [key, params.get(key) || (key === 'ordenacao' ? 'publicacao_desc' : key === 'tamanho_pagina' ? '20' : '')]))

export default function Itens() {
  const { baseId } = useBase()
  const location = useLocation()
  const [params, setParams] = useSearchParams()
  const [draft, setDraft] = useState(() => readFilters(params))
  const [lookupReset, setLookupReset] = useState(0)
  useEffect(() => setDraft(readFilters(params)), [params])
  const filters = readFilters(params)
  const page = params.get('pagina') || '1'
  const query = useApi('/itens', { base_id: baseId, ...filters, pagina: page }, !!baseId)
  const change = (field, value) => setDraft(previous => ({ ...previous, [field]: value }))
  const apply = event => {
    event.preventDefault()
    const next = new URLSearchParams({ base_id: baseId })
    for (const key of names) if (draft[key]) next.set(key, draft[key])
    setParams(next)
  }
  const setPage = value => setParams(previous => {
    const next = new URLSearchParams(previous); next.set('pagina', String(value)); return next
  })
  return <>
    <Head kicker="Consulta / Itens de compras públicas" title="Consultar itens" sub="Dados oficiais do recorte importado. Cada linha representa um item; abra o detalhe para consultar seus resultados e o processo da compra." />
    <form className="card" onSubmit={apply}>
      <h2>Refine o recorte</h2>
      <div className="filters real-filters">
        <Field label="Buscar item, compra ou fornecedor"><input className="input" type="search" maxLength={200} value={draft.busca} onChange={e => change('busca', e.target.value)} /></Field>
        <LookupFilter key={`orgao:${lookupReset}`} kind="/orgaos" title="Órgão" baseId={baseId} value={draft.orgao_id} onChange={value => change('orgao_id', value)} />
        <LookupFilter key={`fornecedor:${lookupReset}`} kind="/fornecedores/opcoes" title="Fornecedor" baseId={baseId} value={draft.fornecedor_id} onChange={value => change('fornecedor_id', value)} />
        <LookupFilter key={`modalidade:${lookupReset}`} kind="/modalidades" title="Modalidade" baseId={baseId} value={draft.modalidade_id} onChange={value => change('modalidade_id', value)} />
        <Field label="Homologação a partir de"><input className="input" type="date" value={draft.homologacao_inicio} onChange={e => change('homologacao_inicio', e.target.value)} /></Field>
        <Field label="Homologação até"><input className="input" type="date" value={draft.homologacao_fim} onChange={e => change('homologacao_fim', e.target.value)} /></Field>
        <Field label="Total homologado mínimo (R$)"><input className="input" type="number" min="0" step="0.00000001" value={draft.valor_minimo} onChange={e => change('valor_minimo', e.target.value)} /></Field>
        <Field label="Total homologado máximo (R$)"><input className="input" type="number" min="0" step="0.00000001" value={draft.valor_maximo} onChange={e => change('valor_maximo', e.target.value)} /></Field>
        <Field label="Ordenação"><select className="select" value={draft.ordenacao} onChange={e => change('ordenacao', e.target.value)}><option value="publicacao_desc">Publicação mais recente</option><option value="publicacao_asc">Publicação mais antiga</option><option value="valor_desc">Maior total do item</option><option value="valor_asc">Menor total do item</option><option value="descricao_asc">Descrição do item</option></select></Field>
        <Field label="Itens por página"><select className="select" value={draft.tamanho_pagina} onChange={e => change('tamanho_pagina', e.target.value)}>{[5, 10, 20, 50, 100].map(value => <option key={value} value={value}>{value}</option>)}</select></Field>
      </div>
      {filters.processo_id && <p className="sub">Consulta restrita ao processo selecionado. Use “Limpar filtros” para consultar toda a base.</p>}
      <div className="filter-actions"><button className="btn primary" type="submit">Aplicar filtros</button><button className="btn ghost" type="button" onClick={() => { setDraft(readFilters(new URLSearchParams())); setParams({ base_id: baseId }); setLookupReset(value => value + 1) }}>Limpar filtros</button></div>
      <p className="hint">O período considera resultados não cancelados. Valores são totais do item, não da compra inteira.</p>
    </form>
    <NoAnalysis />
    <QueryState query={query} loading="Carregando itens…" />
    {query.data && <section className="card" aria-label="Resultados da consulta"><h2>{query.data.meta.total} item(ns) encontrado(s)</h2>
      {query.data.dados.length ? <ItemTable items={query.data.dados} baseId={baseId} from={location.pathname + location.search} /> : <p className="sub">Nenhum item encontrado nesta página. Ajuste os filtros ou volte à primeira página.</p>}
      <Pager meta={query.data.meta} onChange={setPage} />
    </section>}
    <Aviso />
  </>
}
