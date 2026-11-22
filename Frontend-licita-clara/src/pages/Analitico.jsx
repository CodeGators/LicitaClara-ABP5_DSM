import { ifBand, ifBandLabels } from '../ifBands.mjs'
import ItemPriceTable from '../components/ItemPriceTable.jsx'
import PriceReview from '../components/PriceReview.jsx'
import { itemRequiresPriceReview } from '../priceValidation.mjs'
import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { useBase } from '../BaseContext.jsx'
import { AnalysisGate, selectionLink, useAnalysis, viewFields } from '../AnalysisContext.jsx'
import { ifMeasure, decimal, money } from '../api.mjs'
import { Pager, QueryState } from '../components/consultas.jsx'
import { Search, ArrowLeft } from 'lucide-react'
import { Head } from '../components/ui.jsx'
import useApi from '../useApi.js'
import PainelGeral from './PainelGeral.jsx'
import ItemFilters from '../components/ItemFilters.jsx'

export const indexText = value => value == null ? 'Indisponível' : ifMeasure(value)
const productFields = ['busca', 'sinalizacao', 'ordenacao', 'tamanho_pagina']
const read = (params, products = false) => ({ ...Object.fromEntries(viewFields.map(key => [key, params.get(key) || (key === 'analise' ? 'todos' : key === 'ordenacao' ? 'indice_desc' : key === 'tamanho_pagina' ? '20' : '')])), ...(products ? { sinalizacao: params.getAll('sinalizacao') } : {}) })

export function Filters({ purchases = false, suppliers = false, products = false }) {
  const simple = products || purchases || suppliers
  const { params, setParams } = useAnalysis()
  const { baseId } = useBase()
  const [draft, setDraft] = useState(() => read(params, simple))
  useEffect(() => setDraft(read(params, simple)), [params, simple])
  useEffect(() => {
    if (!simple || !viewFields.some(key => !productFields.includes(key) && params.has(key))) return
    setParams(previous => {
      const next = new URLSearchParams(previous)
      for (const key of viewFields) if (!productFields.includes(key)) next.delete(key)
      next.delete('pagina')
      return next
    }, { replace: true })
  }, [simple, params, setParams])
  const change = (key, value) => setDraft(previous => ({ ...previous, [key]: value }))
  const apply = event => {
    event.preventDefault()
    setParams(previous => {
      const next = new URLSearchParams(previous)
      for (const key of [...viewFields, 'sinalizacao', 'pagina', 'pagina_itens']) next.delete(key)
      for (const key of simple ? productFields : viewFields) {
        const value = draft[key]
        if (Array.isArray(value)) value.forEach(entry => next.append(key, entry))
        else if (value) next.set(key, value)
      }
      return next
    })
  }
  const clear = () => { setDraft(read(new URLSearchParams(), simple)); setParams(previous => {
    const next = new URLSearchParams(previous); for (const key of [...viewFields, 'sinalizacao', 'pagina', 'pagina_itens']) next.delete(key); return next
  }) }
  return <ItemFilters draft={draft} change={change} apply={apply} clear={clear} baseId={baseId} params={params} purchases={purchases} suppliers={suppliers} products={products}>
  </ItemFilters>
}


export function useView(path, { enabled = true } = {}) {
  const { baseId } = useBase()
  const s = useAnalysis()
  const simple = path === '/visao/produtos' || path === '/visao/licitacoes' || path.startsWith('/visao/licitacoes/') || path === '/visao/fornecedores'
  const allFilters = read(s.params, simple)
  const filters = simple ? Object.fromEntries(productFields.map(key => [key, allFilters[key]])) : allFilters
  const query = useApi(path, { base_id: baseId, execucao_id: s.executionId, modelo_id: s.modelId, ...filters, pagina: s.params.get('pagina') || '1' }, !!s.ready && enabled)
  const changePage = page => s.setParams(previous => { const next = new URLSearchParams(previous); next.set('pagina', String(page)); return next })
  return { query, params: s.params, changePage }
}

export function ItemRows({ rows, params, scoreLabel = 'Medida IF' }) {
  const location = useLocation()
  return <div className="table-scroll" role="region" aria-label="Itens e resultados do recorte; use as setas para rolar na horizontal" tabIndex={0}><table className="tbl tbl-stack"><thead><tr><th scope="col">Item / compra</th><th scope="col">Órgão / fornecedores</th><th scope="col">Total homologado</th><th scope="col">{scoreLabel}</th><th scope="col">Cobertura</th></tr></thead><tbody>{rows.map(r => <tr key={r.id}>
    <td><Link className="link-a" to={selectionLink(`/ranking/${r.id}`, params)} state={{ from: location.pathname + location.search }}>{r.descricao}</Link><small>Item {r.numero_item} · Compra {r.processo.numero_compra}</small>{(r.requer_validacao ?? itemRequiresPriceReview(r)) && <PriceReview compact />}</td>
    <td data-label="Órgão">{r.processo.orgao_nome}<small>{[...new Set(r.resultados.map(e => e.fornecedor_nome))].join('; ') || 'Nenhum resultado conhecido'}</small></td>
    <td className="numeric" data-label="Total homologado">{money(r.valor_homologado)}{r.resultados_sem_total > 0 && <small>Total incompleto na fonte</small>}</td>
    <td className="numeric" data-label={scoreLabel}>{indexText(r.medida_if)}</td>
    <td data-label="Cobertura">{r.status_analise === 'analisados' ? 'Integral' : r.status_analise === 'parcial' ? 'Parcial' : 'Não analisado'}<small>{r.resultados_analisados}/{r.resultados_ativos} resultados</small>{Object.keys(r.motivos).map(reason => <small key={reason}>{reason.replaceAll('_', ' ').toLocaleLowerCase('pt-BR')}</small>)}</td>
  </tr>)}</tbody></table></div>
}

function Shell({ title, children }) {
  return <><Head title={title} /><Filters products={title === 'Itens Sinalizados'} suppliers={title !== 'Itens Sinalizados'} />{children}</>
}

function DashboardContent() {
  const { query, params } = useView('/visao/painel')
  const { baseId } = useBase()
  const s = useAnalysis()
  const filters = read(params)
  const ranking = useApi('/visao/ranking', {
    base_id: baseId, execucao_id: s.executionId, modelo_id: s.modelId,
    ...filters, ordenacao: 'indice_desc', pagina: 1, tamanho_pagina: 3,
  }, !!s.ready && !!query.data)
  return <PainelGeral query={query} ranking={ranking} params={params} />
}

function RankingContent() {
  const { query, params, changePage } = useView('/visao/produtos')
  const data = query.data
  return <Shell title="Itens Sinalizados"><QueryState query={query} />{data && <><section className="card"><h2>{data.total} {data.total === 1 ? 'produto' : 'produtos'}</h2><p className="sub">Preços unitários dos produtos da base atual, separados por especificação e unidade de fornecimento.</p>{data.dados.length ? <ItemPriceTable rows={data.dados} params={params} /> : <p>Nenhum item encontrado nesta página.</p>}<Pager meta={data} onChange={changePage} /></section></>}</Shell>
}

const supplierCoverage = supplier => supplier.itens_com_medida_if == null ? 'Não informado' : `${supplier.itens_com_medida_if} de ${supplier.itens} ${supplier.itens === 1 ? 'analisado' : 'analisados'}`

function SuppliersContent() {
  const { id } = useParams()
  const location = useLocation()
  const { query, params, changePage } = useView('/visao/fornecedores', { enabled: !id })
  const { baseId } = useBase()
  const analysis = useAnalysis()
  const detail = useApi(`/visao/fornecedores/${encodeURIComponent(id || '')}`, {
    base_id: baseId, execucao_id: analysis.executionId, modelo_id: analysis.modelId,
    pagina: params.get('pagina_itens') || '1', tamanho_pagina: params.get('tamanho_pagina') || '20',
  }, !!id && analysis.ready)
  const data = query.data, selected = detail.data, supplier = selected?.fornecedor
  const listParams = new URLSearchParams(params)
  listParams.delete('pagina_itens')
  const listLink = `/fornecedores?${listParams}`
  const back = location.state?.from?.startsWith('/fornecedores?') ? location.state.from : listLink
  const selectLink = supplierId => {
    const next = new URLSearchParams(params)
    next.delete('pagina'); next.delete('pagina_itens')
    return selectionLink(`/fornecedores/${supplierId}`, next)
  }
  const relatedPage = page => analysis.setParams(previous => {
    const next = new URLSearchParams(previous); next.set('pagina_itens', String(page)); return next
  }, { state: location.state })
  return <div className="suppliers-page">
    {id && <Link className="link-a back-link" to={back}><ArrowLeft size={16} />Voltar aos fornecedores</Link>}
    <Head title={id ? supplier?.nome || 'Detalhe do fornecedor' : 'Fornecedores'} />
    {!id && <>
      <Filters suppliers />
      <QueryState query={query} />
      {data && <section className="card supplier-ranking"><h2>{data.total} {data.total === 1 ? 'fornecedor' : 'fornecedores'}</h2>
        {data.dados.length ? <div className="table-scroll" role="region" aria-label="Fornecedores sinalizados; use as setas para rolar na horizontal" tabIndex={0}><table className="tbl tbl-stack product-table supplier-table"><thead><tr>
          <th scope="col">Fornecedor</th><th scope="col">Compras</th><th scope="col">Total homologado</th><th scope="col">Itens analisados</th><th scope="col"><span className="sr-only">Detalhes</span></th>
        </tr></thead><tbody>{data.dados.map(row => {
          const band = ifBand(row)
          return <tr key={row.id} className={band ? `if-band-${band}` : undefined} data-if-band={band || undefined} title={ifBandLabels[band]}>
            <td>{band && <span className="sr-only">{ifBandLabels[band]}. </span>}<Link className="link-a" to={selectLink(row.id)} state={{ from: listLink }}>{row.nome}</Link><small>{row.orgaos} {row.orgaos === 1 ? 'órgão' : 'órgãos'}</small>{row.requer_validacao && <PriceReview />}</td>
            <td data-label="Compras">{row.compras_com_resultado}</td>
            <td className="numeric" data-label="Total homologado">{money(row.valor_homologado)}{row.resultados_sem_total > 0 && <small>Total incompleto</small>}</td>
            <td data-label="Itens analisados">{supplierCoverage(row)}</td>
            <td><Link className="dashboard-analysis-link" title="Ver fornecedor" aria-label={`Ver fornecedor ${row.nome}`} to={selectLink(row.id)} state={{ from: listLink }}><Search size={17} aria-hidden="true" /></Link></td>
          </tr>
        })}</tbody></table></div> : <p>Nenhum fornecedor encontrado neste recorte.</p>}
        <Pager meta={data} onChange={changePage} />
      </section>}
    </>}
    {id && <QueryState query={detail} loading="Carregando fornecedor…" />}
    {supplier && <>
      <div className="supplier-detail-columns" aria-label="Fornecedor selecionado">
        <section className="card"><h2>Resumo do fornecedor</h2>{supplier.requer_validacao && <PriceReview />}
          <div className="stats supplier-stats"><div><strong>{supplier.compras_com_resultado}</strong><small>compras com resultado</small></div><div><strong>{money(supplier.valor_homologado)}</strong><small>homologado</small></div><div><strong>{supplier.orgaos}</strong><small>órgãos</small></div><div><strong>{supplierCoverage(supplier)}</strong><small>itens analisados</small></div></div>
          {supplier.resultados_sem_total > 0 && <p className="hint">Total incompleto na fonte.</p>}
        </section>
        <section className="card"><h2>Participação no gasto por órgão</h2>
          <div className="supplier-relations">{selected.relacoes.map(relation => <div key={relation.orgao_id}>
            <div className="mini"><b>{relation.orgao_nome}</b><span className="t-pet">{relation.participacao == null ? 'Indisponível' : `${decimal((Number(relation.participacao) * 100).toFixed(2))}%`}</span></div>
            {relation.participacao != null && <div className="supplier-bar" role="meter" aria-label={`Participação em ${relation.orgao_nome}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Number(relation.participacao) * 100}><span style={{ width: `${Math.min(100, Math.max(0, Number(relation.participacao) * 100))}%` }} /></div>}
            <p className="hint">{money(relation.valor_fornecedor)} · {relation.compras_com_resultado} compras com resultado · <span>HHI: {relation.hhi == null ? 'Indisponível' : decimal(relation.hhi, 0, 4)}</span></p>
          </div>)}</div>
          {!selected.relacoes.length && <p>Sem relações disponíveis neste recorte.</p>}
        </section>
      </div>
      <section className="card supplier-related"><h2>Itens relacionados a {supplier.nome}</h2>
        {selected.itens.dados.length ? <ItemRows rows={selected.itens.dados} params={params} /> : <p>Nenhum item encontrado nesta página.</p>}
        <Pager meta={selected.itens} onChange={relatedPage} />
      </section>
    </>}
  </div>
}

export const PainelReal = () => <AnalysisGate><DashboardContent /></AnalysisGate>
export const RankingReal = () => <AnalysisGate><RankingContent /></AnalysisGate>
export const FornecedoresReal = () => <AnalysisGate><SuppliersContent /></AnalysisGate>
