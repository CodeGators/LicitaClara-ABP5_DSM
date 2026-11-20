import { useEffect, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { Head, Aviso } from '../components/ui.jsx'
import { ItemTable, NoAnalysis, Pager, QueryState } from '../components/consultas.jsx'
import { useBase } from '../BaseContext.jsx'
import useApi from '../useApi.js'
import ItemFilters from '../components/ItemFilters.jsx'

const names = ['busca', 'orgao_id', 'fornecedor_id', 'modalidade_id', 'processo_id', 'homologacao_inicio', 'homologacao_fim', 'valor_minimo', 'valor_maximo', 'ordenacao', 'tamanho_pagina']
const readFilters = params => Object.fromEntries(names.map(key => [key, params.get(key) || (key === 'ordenacao' ? 'publicacao_desc' : key === 'tamanho_pagina' ? '20' : '')]))

export default function Itens() {
  const { baseId } = useBase()
  const location = useLocation()
  const [params, setParams] = useSearchParams()
  const [draft, setDraft] = useState(() => readFilters(params))
  useEffect(() => setDraft(readFilters(params)), [params])
  const filters = readFilters(params)
  const page = params.get('pagina') || '1'
  const query = useApi('/itens', { base_id: baseId, ...filters, pagina: page }, !!baseId)
  const change = (field, value) => setDraft(previous => ({ ...previous, [field]: value }))
  const apply = event => {
    event.preventDefault()
    const next = new URLSearchParams({ base_id: baseId })
    for (const key of ['execucao_id', 'modelo_id']) if (params.has(key)) next.set(key, params.get(key))
    for (const key of names) if (draft[key]) next.set(key, draft[key])
    setParams(next)
  }
  const setPage = value => setParams(previous => {
    const next = new URLSearchParams(previous); next.set('pagina', String(value)); return next
  })
  return <>
    <Head title="Consultar itens" sub="Dados oficiais importados. Cada linha é um item; abra um para ver resultados, documentos e a compra." />
    <ItemFilters official draft={draft} change={change} apply={apply} baseId={baseId} params={params} clear={() => {
      setDraft(readFilters(new URLSearchParams()))
      setParams(previous => {
        const next = new URLSearchParams({ base_id: baseId })
        for (const key of ['execucao_id', 'modelo_id']) if (previous.has(key)) next.set(key, previous.get(key))
        return next
      })
    }}>
      {filters.processo_id && <p className="hint">Mostrando só a compra selecionada. Use “Limpar filtros” para ver toda a base.</p>}
      
    </ItemFilters>
    <NoAnalysis />
    <QueryState query={query} loading="Carregando itens…" />
    {query.data && <section className="card" aria-label="Resultados da consulta"><h2>{query.data.meta.total} item(ns) encontrado(s)</h2>
      {query.data.dados.length ? <ItemTable items={query.data.dados} baseId={baseId} from={location.pathname + location.search} /> : <p className="sub">Nenhum item encontrado nesta página. Ajuste os filtros ou volte à primeira página.</p>}
      <Pager meta={query.data.meta} onChange={setPage} />
    </section>}
    <Aviso />
  </>
}
