import PriceReview from '../components/PriceReview.jsx'
import { itemRequiresPriceReview } from '../priceValidation.mjs'
import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { useBase } from '../BaseContext.jsx'
import { AnalysisGate, AnalysisSelector, selectionLink, useAnalysis, viewFields } from '../AnalysisContext.jsx'
import { ifMeasure, decimal, money, reportLink } from '../api.mjs'
import { Pager, QueryState } from '../components/consultas.jsx'
import { FileOutput, Building2, Landmark, ScanSearch } from 'lucide-react'
import { Head, Aviso } from '../components/ui.jsx'
import useApi from '../useApi.js'
import PainelGeral from './PainelGeral.jsx'
import ItemFilters from '../components/ItemFilters.jsx'

export const indexText = value => value == null ? 'Indisponível' : ifMeasure(value)
const read = params => Object.fromEntries(viewFields.map(key => [key, params.get(key) || (key === 'analise' ? 'todos' : key === 'ordenacao' ? 'indice_desc' : key === 'tamanho_pagina' ? '20' : '')]))

export function Filters({ purchases = false, suppliers = false }) {
  const { params, setParams } = useAnalysis()
  const { baseId } = useBase()
  const [draft, setDraft] = useState(() => read(params))
  useEffect(() => setDraft(read(params)), [params])
  const change = (key, value) => setDraft(previous => ({ ...previous, [key]: value }))
  const apply = event => {
    event.preventDefault()
    setParams(previous => {
      const next = new URLSearchParams(previous)
      for (const key of [...viewFields, 'pagina', 'pagina_itens']) next.delete(key)
      for (const key of viewFields) if (draft[key]) next.set(key, draft[key])
      return next
    })
  }
  const clear = () => { setDraft(read(new URLSearchParams())); setParams(previous => {
    const next = new URLSearchParams(previous); for (const key of [...viewFields, 'pagina', 'pagina_itens']) next.delete(key); return next
  }) }
  return <ItemFilters draft={draft} change={change} apply={apply} clear={clear} baseId={baseId} params={params} purchases={purchases} suppliers={suppliers}>
    {suppliers && <p className="hint">Filtrar por fornecedor seleciona os itens em que ele tem resultado. Valores e concentração incluem os demais vencedores desses itens.</p>}
  </ItemFilters>
}


function Cards({ summary }) {
  const itens = [
    ['Itens no recorte', summary.itens, `${summary.processos} compras · ${summary.contratos_vinculados} contratos`],
    ['Total homologado', money(summary.valor_homologado), summary.resultados_sem_total ? `${summary.resultados_sem_total} resultado(s) sem total` : 'Não é valor pago'],
    ['Fornecedores', summary.fornecedores, `${summary.orgaos} órgãos`],
    ['Com análise completa', summary.analisados, 'Todos os resultados do item têm medida IF'],
    ['Com análise parcial', summary.parcial, 'Há resultados sem medida IF'],
    ['Sem análise', summary.nao_analisados, 'Motivo na consulta'],
  ]
  return <section className="card" aria-label="Resumo do recorte"><div className="stat-strip">{itens.map(([label, value, text]) => <div key={label}><span>{label}</span><strong>{value}</strong><small>{text}</small></div>)}</div></section>
}

export function useView(path) {
  const { baseId } = useBase()
  const s = useAnalysis()
  const filters = read(s.params)
  const query = useApi(path, { base_id: baseId, execucao_id: s.executionId, modelo_id: s.modelId, ...filters, pagina: s.params.get('pagina') || '1' }, !!s.ready)
  const changePage = page => s.setParams(previous => { const next = new URLSearchParams(previous); next.set('pagina', String(page)); return next })
  return { query, params: s.params, changePage }
}

export function ItemRows({ rows, params, scoreLabel = 'Medida IF' }) {
  const location = useLocation()
  return <div className="table-scroll" role="region" aria-label="Itens e resultados do recorte; use as setas para rolar na horizontal" tabIndex={0}><table className="tbl tbl-stack"><thead><tr><th scope="col">Item / compra</th><th scope="col">Órgão / fornecedores</th><th scope="col">Total homologado</th><th scope="col">{scoreLabel}</th><th scope="col">Cobertura</th></tr></thead><tbody>{rows.map(r => <tr key={r.id}>
    <td><Link className="link-a" to={selectionLink(`/ranking/${r.id}`, params)} state={{ from: location.pathname + location.search }}>{r.descricao}</Link><small>Item {r.numero_item} · Compra {r.processo.numero_compra}</small>{itemRequiresPriceReview(r) && <PriceReview compact />}</td>
    <td data-label="Órgão">{r.processo.orgao_nome}<small>{[...new Set(r.resultados.map(e => e.fornecedor_nome))].join('; ') || 'Nenhum resultado conhecido'}</small></td>
    <td className="numeric" data-label="Total homologado">{money(r.valor_homologado)}{r.resultados_sem_total > 0 && <small>Total incompleto na fonte</small>}</td>
    <td className="numeric" data-label={scoreLabel}>{indexText(r.medida_if)}</td>
    <td data-label="Cobertura">{r.status_analise === 'analisados' ? 'Integral' : r.status_analise === 'parcial' ? 'Parcial' : 'Não analisado'}<small>{r.resultados_analisados}/{r.resultados_ativos} resultados</small>{Object.keys(r.motivos).map(reason => <small key={reason}>{reason.replaceAll('_', ' ').toLocaleLowerCase('pt-BR')}</small>)}</td>
  </tr>)}</tbody></table></div>
}

function Shell({ title, summary, children }) {
  return <><Head title={title} sub={title === 'Itens Sinalizados' ? 'Itens ordenados pela medida IF experimental. Busque pelo nome ou abra Mais filtros para refinar.' : 'Consulta com base e análise versionadas. Os filtros valem para o painel, o ranking e os fornecedores.'} />{summary && <Cards summary={summary} />}<AnalysisSelector /><Filters suppliers={title !== 'Itens Sinalizados'} />{children}<Aviso detalhe /></>
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
  const { query, params, changePage } = useView('/visao/ranking')
  const data = query.data
  return <Shell title="Itens Sinalizados" summary={data?.resumo}><QueryState query={query} />{data && <><section className="card"><h2>{data.total} item(ns) no ranking</h2><p className="sub">Quem tem medida IF aparece primeiro; quem não tem fica no fim, sem receber zero. Não é uma fila de risco validada.</p>{data.dados.length ? <ItemRows rows={data.dados} params={params} /> : <p>Nenhum item encontrado nesta página.</p>}<Pager meta={data} onChange={changePage} /></section></>}</Shell>
}

function SuppliersContent() {
  const { id } = useParams()
  const { query, params, changePage } = useView('/visao/fornecedores')
  const { baseId } = useBase()
  const analysis = useAnalysis()
  const selectedId = id || query.data?.dados[0]?.id
  const detail = useApi(`/visao/fornecedores/${encodeURIComponent(selectedId || '')}`, {
    base_id: baseId, execucao_id: analysis.executionId, modelo_id: analysis.modelId,
    ...read(params), pagina: params.get('pagina_itens') || '1',
  }, !!selectedId && analysis.ready)
  const data = query.data
  const selected = detail.data
  const supplier = selected?.fornecedor
  const selectLink = supplierId => {
    const next = new URLSearchParams(params)
    next.delete('pagina_itens')
    return `/fornecedores/${supplierId}?${next}`
  }
  const relatedPage = page => analysis.setParams(previous => {
    const next = new URLSearchParams(previous); next.set('pagina_itens', String(page)); return next
  })
  const processId = selected?.itens.dados[0]?.processo.id
  return <div className="suppliers-page">
    <Head title="Fornecedores" sub="Veja com quais órgãos cada fornecedor contrata e quanto pesa no gasto de cada um."
      action={<Link className="btn primary" to={processId ? reportLink(processId, params) : selectionLink('/relatorios', params)}><FileOutput size={16} /> Preparar relatório</Link>} />
    <div className="kpis">
      {[
        ['Fornecedores no recorte', data?.resumo.fornecedores, 'Com resultados no recorte', Building2],
        ['Órgãos contratantes', data?.resumo.orgaos, 'Concentração calculada por órgão', Landmark],
        ['Itens com análise completa', data?.resumo.analisados, 'No recorte selecionado', ScanSearch],
      ].map(([label, value, hint, Icon]) => <div className="card kpi" key={label}><div className="row"><span>{label}</span><Icon size={18} /></div><strong>{value ?? '—'}</strong><small>{hint}</small></div>)}
    </div>
    <AnalysisSelector />
    <div className="supplier-columns">
      <section className="card supplier-ranking">
        <h2>Ranking de fornecedores</h2><p className="sub">Mostra a maior medida IF entre os resultados de cada fornecedor.</p>
        <Filters suppliers />
        <QueryState query={query} />
        {data && <>{data.dados.length ? <div className="table-scroll" role="region" aria-label="Ranking de fornecedores; use as setas para rolar na horizontal" tabIndex={0}><table className="tbl tbl-stack"><thead><tr><th scope="col">Fornecedor</th><th scope="col">Compras</th><th scope="col">Homologado</th><th scope="col">Maior medida IF</th></tr></thead><tbody>{data.dados.map(r => <tr key={r.id} className={r.id === selectedId ? 'sel' : ''}>
          <td><Link className="link-a" to={selectLink(r.id)} aria-current={r.id === selectedId ? 'true' : undefined}>{r.nome}</Link><small>{r.orgaos} órgãos · {r.itens} itens</small></td><td data-label="Compras">{r.compras_com_resultado}<small>{r.contratos_vinculados} contratos vinculados</small></td><td className="numeric" data-label="Homologado">{money(r.valor_homologado)}{r.resultados_sem_total > 0 && <small>Total incompleto</small>}</td><td className="numeric" data-label="Maior medida IF">{indexText(r.medida_if)}</td>
        </tr>)}</tbody></table></div> : <p>Nenhum fornecedor encontrado neste recorte.</p>}<Pager meta={data} onChange={changePage} /></>}
      </section>
      <div className="grid supplier-summary" aria-label="Fornecedor selecionado">
        <QueryState query={detail} loading="Carregando fornecedor…" />
        {supplier && <><section className="card">
          <div className="mini"><h2>{supplier.nome}</h2><span className="pill ana">Selecionado</span></div><p className="sub">Dados oficiais do recorte</p>
          <div className="stats supplier-stats"><div><strong>{supplier.compras_com_resultado}</strong><small>compras com resultado</small></div><div><strong>{money(supplier.valor_homologado)}</strong><small>homologado</small></div><div><strong>{supplier.orgaos}</strong><small>órgãos</small></div></div>
          <p className="hint">Maior medida IF: {indexText(supplier.medida_if)} · {supplier.contratos_vinculados} contratos vinculados conhecidos</p>
          {supplier.resultados_sem_total > 0 && <p className="hint">Total incompleto na fonte.</p>}
        </section>
        <section className="card"><h2>Participação no gasto por órgão</h2><p className="sub">Valor do fornecedor ÷ total dos resultados de cada órgão no recorte.</p>
          <div className="supplier-relations">{selected.relacoes.map(r => <div key={r.orgao_id}>
            <div className="mini"><b>{r.orgao_nome}</b><span className="t-pet">{r.participacao == null ? 'Indisponível' : `${decimal((Number(r.participacao) * 100).toFixed(2))}%`}</span></div>
            {r.participacao != null && <div className="supplier-bar" role="meter" aria-label={`Participação em ${r.orgao_nome}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Number(r.participacao) * 100}><span style={{ width: `${Math.min(100, Math.max(0, Number(r.participacao) * 100))}%` }} /></div>}
            <p className="hint">{money(r.valor_fornecedor)} · {r.compras_com_resultado} compras com resultado · <span>HHI: {r.hhi == null ? 'Indisponível' : decimal(r.hhi, 0, 4)}</span></p>
            {r.motivo && <small className="hint">{r.motivo.replaceAll('_', ' ').toLowerCase()}</small>}
          </div>)}</div>
          {!selected.relacoes.length && <p>Sem relações disponíveis neste recorte.</p>}
          <p className="hint supplier-limit">HHI mede a concentração entre os fornecedores dos itens filtrados, de 0 a 1. Quanto maior, mais concentrado. O recorte não cobre todo o órgão, e concentração sozinha não indica irregularidade.</p>
        </section></>}
        {!selectedId && data && <section className="card"><h2>Selecione um fornecedor</h2><p>Os vínculos e a participação aparecem aqui.</p></section>}
      </div>
    </div>
    {selected && <section className="card supplier-related"><h2>Itens relacionados a {supplier.nome}</h2><p className="sub">Valores e medidas IF consideram só os resultados deste fornecedor. O detalhe do item mostra todos os vencedores.</p>
      {selected.itens.dados.length ? <ItemRows rows={selected.itens.dados} params={params} scoreLabel="Medida IF" /> : <p>Nenhum item encontrado nesta página.</p>}<Pager meta={selected.itens} onChange={relatedPage} />
    </section>}
    <Aviso detalhe />
  </div>
}

export const PainelReal = () => <AnalysisGate><DashboardContent /></AnalysisGate>
export const RankingReal = () => <AnalysisGate><RankingContent /></AnalysisGate>
export const FornecedoresReal = () => <AnalysisGate><SuppliersContent /></AnalysisGate>
