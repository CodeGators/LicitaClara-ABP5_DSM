import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { useBase } from '../BaseContext.jsx'
import { AnalysisGate, AnalysisSelector, selectionLink, useAnalysis, viewFields } from '../AnalysisContext.jsx'
import { decimal, money, reportLink } from '../api.mjs'
import { Pager, QueryState } from '../components/consultas.jsx'
import { FileOutput, Building2, Landmark, ScanSearch } from 'lucide-react'
import { Head, Aviso } from '../components/ui.jsx'
import useApi from '../useApi.js'
import PainelGeral from './PainelGeral.jsx'
import ItemFilters from '../components/ItemFilters.jsx'

export const indexText = value => value == null ? 'Indisponível' : decimal(value)
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
    {suppliers && <p className="hint">O fornecedor seleciona itens com resultado dele. Valores e concentração conservam os demais vencedores desses itens no período.</p>}
  </ItemFilters>
}


function Notice() {
  return <div className="note"><b>Análise experimental · utilidade não validada</b>O índice é uma posição em relação ao treino do modelo, não probabilidade de fraude ou prioridade de auditoria. Sem faixas de risco validadas. Ausência de índice não representa regularidade.</div>
}

function Cards({ summary }) {
  return <div className="grid g3">
    {[
      ['Itens no recorte', summary.itens, `${summary.processos} compras · ${summary.contratos_vinculados} contratos vinculados`],
      ['Total homologado no recorte', money(summary.valor_homologado), summary.resultados_sem_total ? `${summary.resultados_sem_total} resultado(s) sem total; soma conhecida: ${money(summary.soma_valores_conhecidos)}` : `${summary.resultados} resultados não cancelados; não é valor pago`],
      ['Fornecedores exibidos', summary.fornecedores, `${summary.orgaos} órgãos · ${summary.fornecedores_no_denominador} fornecedores no universo de concentração`],
      ['Analisados integralmente', summary.analisados, 'Todos os resultados selecionados do item têm índice'],
      ['Parcialmente analisados', summary.parcial, 'Há resultados sem score; cobertura não é completada com zero'],
      ['Não analisados', summary.nao_analisados, 'Motivo disponível na consulta; sem conclusão de auditoria'],
    ].map(([label, value, text]) => <div className="card kpi" key={label}><span>{label}</span><strong>{value}</strong><small>{text}</small></div>)}
  </div>
}

export function useView(path) {
  const { baseId } = useBase()
  const s = useAnalysis()
  const filters = read(s.params)
  const query = useApi(path, { base_id: baseId, execucao_id: s.executionId, modelo_id: s.modelId, ...filters, pagina: s.params.get('pagina') || '1' }, !!s.ready)
  const changePage = page => s.setParams(previous => { const next = new URLSearchParams(previous); next.set('pagina', String(page)); return next })
  return { query, params: s.params, changePage }
}

export function ItemRows({ rows, params, scoreLabel = 'Índice experimental' }) {
  const location = useLocation()
  return <div className="table-scroll" role="region" aria-label="Itens e resultados do recorte; use as setas para rolar na horizontal" tabIndex={0}><table className="tbl"><thead><tr><th scope="col">Item / compra</th><th scope="col">Órgão / fornecedores</th><th scope="col">Total homologado no recorte</th><th scope="col">{scoreLabel}</th><th scope="col">Cobertura</th></tr></thead><tbody>{rows.map(r => <tr key={r.id}>
    <td><Link className="link-a" to={selectionLink(`/ranking/${r.id}`, params)} state={{ from: location.pathname + location.search }}>{r.descricao}</Link><small>Item {r.numero_item} · Compra {r.processo.numero_compra}</small></td>
    <td>{r.processo.orgao_nome}<small>{[...new Set(r.resultados.map(e => e.fornecedor_nome))].join('; ') || 'Nenhum resultado conhecido'}</small></td>
    <td>{money(r.valor_homologado)}{r.resultados_sem_total > 0 && <small>Total incompleto na fonte</small>}</td>
    <td>{indexText(r.indice_experimental)}{r.indice_experimental != null && <small>Máximo dos resultados analisados do item</small>}</td>
    <td>{r.status_analise === 'analisados' ? 'Integral' : r.status_analise === 'parcial' ? 'Parcial' : 'Não analisado'}<small>{r.resultados_analisados}/{r.resultados_ativos} resultados</small>{Object.keys(r.motivos).map(reason => <small key={reason}>{reason.replaceAll('_', ' ').toLocaleLowerCase('pt-BR')}</small>)}</td>
  </tr>)}</tbody></table></div>
}

function Shell({ title, summary, children }) {
  return <><Head kicker="Dados oficiais / Recorte selecionado" title={title} sub={title === 'Itens Sinalizados' ? 'Consulte os itens importados e seus Scores. Use a busca ou refine a seleção em Mais filtros.' : 'Consultas reais, com base e análise versionadas. Filtros compartilhados entre painel, ranking e fornecedores.'} />{summary && <Cards summary={summary} />}<AnalysisSelector /><Notice /><Filters suppliers={title !== 'Itens Sinalizados'} />{children}</>
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
  return <Shell title="Itens Sinalizados" summary={data?.resumo}><QueryState query={query} />{data && <><section className="card"><h2>{data.total} item(ns) no ranking</h2><p className="sub">Índices disponíveis primeiro; ausências ficam ao final, sem receber zero. Não é uma fila de risco validado.</p>{data.dados.length ? <ItemRows rows={data.dados} params={params} /> : <p>Nenhum item encontrado nesta página.</p>}<Pager meta={data} onChange={changePage} /></section></>}</Shell>
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
    <Head kicker="Relações e concentração / Recorte importado" title="Fornecedores" sub="Explore vínculos de contratação e participação no gasto de cada órgão."
      action={<Link className="btn primary" to={processId ? reportLink(processId, params) : selectionLink('/relatorios', params)}><FileOutput size={16} /> Preparar relatório</Link>} />
    <div className="grid g3">
      {[
        ['Fornecedores no recorte', data?.resumo.fornecedores, 'Fornecedores com resultados no recorte', Building2],
        ['Órgãos contratantes', data?.resumo.orgaos, 'Concentração calculada por órgão', Landmark],
        ['Itens com análise completa', data?.resumo.analisados, 'Cobertura da análise no recorte selecionado', ScanSearch],
      ].map(([label, value, hint, Icon]) => <div className="card kpi" key={label}><div className="row"><span>{label}</span><Icon size={18} /></div><strong>{value ?? '—'}</strong><small>{hint}</small></div>)}
    </div>
    <details className="supplier-analysis"><summary>Versão da análise</summary><AnalysisSelector /></details>
    <div className="supplier-columns">
      <section className="card supplier-ranking">
        <h2>Ranking de fornecedores</h2><p className="sub">Maior Score disponível entre os resultados do fornecedor. Ordenação ajustável nos filtros.</p>
        <Filters suppliers />
        <QueryState query={query} />
        {data && <>{data.dados.length ? <div className="table-scroll" role="region" aria-label="Ranking de fornecedores; use as setas para rolar na horizontal" tabIndex={0}><table className="tbl"><thead><tr><th scope="col">Fornecedor</th><th scope="col">Compras</th><th scope="col">Homologado</th><th scope="col">Maior Score</th></tr></thead><tbody>{data.dados.map(r => <tr key={r.id} className={r.id === selectedId ? 'sel' : ''}>
          <td><Link className="link-a" to={selectLink(r.id)} aria-current={r.id === selectedId ? 'true' : undefined}>{r.nome}</Link><small>{r.orgaos} órgãos · {r.itens} itens</small></td><td>{r.compras_com_resultado}<small>{r.contratos_vinculados} contratos vinculados</small></td><td>{money(r.valor_homologado)}{r.resultados_sem_total > 0 && <small>Total incompleto</small>}</td><td>{indexText(r.indice_experimental)}</td>
        </tr>)}</tbody></table></div> : <p>Nenhum fornecedor encontrado neste recorte.</p>}<Pager meta={data} onChange={changePage} /></>}
      </section>
      <div className="grid supplier-summary" aria-label="Fornecedor selecionado">
        <QueryState query={detail} loading="Carregando fornecedor…" />
        {supplier && <><section className="card">
          <div className="mini"><h2>{supplier.nome}</h2><span className="pill ana">Selecionado</span></div><p className="sub">Fornecedor selecionado · dados oficiais do recorte</p>
          <div className="stats supplier-stats"><div><strong>{supplier.compras_com_resultado}</strong><small>compras com resultado</small></div><div><strong>{money(supplier.valor_homologado)}</strong><small>homologado</small></div><div><strong>{supplier.orgaos}</strong><small>órgãos</small></div></div>
          <p className="hint">Maior Score: {indexText(supplier.indice_experimental)} · {supplier.contratos_vinculados} contratos vinculados conhecidos</p>
          {supplier.resultados_sem_total > 0 && <p className="hint">Total incompleto na fonte.</p>}
        </section>
        <section className="card"><h2>Participação no gasto por órgão</h2><p className="sub">Valor deste fornecedor ÷ total dos resultados no recorte de cada órgão.</p>
          <div className="supplier-relations">{selected.relacoes.map(r => <div key={r.orgao_id}>
            <div className="mini"><b>{r.orgao_nome}</b><span className="t-pet">{r.participacao == null ? 'Indisponível' : `${decimal((Number(r.participacao) * 100).toFixed(2))}%`}</span></div>
            {r.participacao != null && <div className="supplier-bar" role="meter" aria-label={`Participação em ${r.orgao_nome}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Number(r.participacao) * 100}><span style={{ width: `${Math.min(100, Math.max(0, Number(r.participacao) * 100))}%` }} /></div>}
            <p className="hint">{money(r.valor_fornecedor)} · {r.compras_com_resultado} compras com resultado <span>HHI: {r.hhi == null ? 'Indisponível' : decimal(r.hhi, 0, 4)}</span></p>
            {r.motivo && <small className="hint">{r.motivo.replaceAll('_', ' ').toLowerCase()}</small>}
          </div>)}</div>
          {!selected.relacoes.length && <p>Sem relações disponíveis neste recorte.</p>}
          <p className="hint supplier-limit">HHI mede a concentração de todos os fornecedores dos itens filtrados por órgão, de 0 a 1. Quanto maior, mais concentrado. O recorte não representa o universo completo do órgão. Concentração, isoladamente, não indica irregularidade.</p>
        </section></>}
        {!selectedId && data && <section className="card"><h2>Selecione um fornecedor</h2><p>Os vínculos e a participação aparecem aqui.</p></section>}
      </div>
    </div>
    {selected && <section className="card supplier-related"><h2>Itens relacionados a {supplier.nome}</h2><p className="sub">Valores e Scores consideram somente os resultados deste fornecedor; o detalhe do item apresenta todos os vencedores.</p>
      {selected.itens.dados.length ? <ItemRows rows={selected.itens.dados} params={params} scoreLabel="Score" /> : <p>Nenhum item encontrado nesta página.</p>}<Pager meta={selected.itens} onChange={relatedPage} />
    </section>}
    <Aviso detalhe />
  </div>
}

export const PainelReal = () => <AnalysisGate><DashboardContent /></AnalysisGate>
export const RankingReal = () => <AnalysisGate><RankingContent /></AnalysisGate>
export const FornecedoresReal = () => <AnalysisGate><SuppliersContent /></AnalysisGate>
