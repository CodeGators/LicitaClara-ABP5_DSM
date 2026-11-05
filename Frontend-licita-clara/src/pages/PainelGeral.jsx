import { useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { Files, Wallet, Activity, ScanSearch, CalendarDays, ArrowRight } from 'lucide-react'
import { useBase } from '../BaseContext.jsx'
import { AnalysisSelector, useAnalysis } from '../AnalysisContext.jsx'
import { decimal, money, selectionLink } from '../api.mjs'
import { QueryState, Field } from '../components/consultas.jsx'
import { Head, Aviso } from '../components/ui.jsx'
import useApi from '../useApi.js'

const number = value => Number(value).toLocaleString('pt-BR')
const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
const month = value => value ? `${months[Number(value.slice(5, 7)) - 1]} ${value.slice(0, 4)}` : 'Período não informado'
const period = (start, end) => start?.slice(0, 7) === end?.slice(0, 7) ? month(start) : `${month(start)} – ${month(end)}`
const range = (b, i) => i === 9 ? '90–100' : `${b.inicio}–${b.fim - 1}`
const algorithm = value => ({ isolation_forest: 'Isolation Forest', autoencoder: 'Autoencoder' })[value] || value
const compactMoney = value => value == null ? 'Não informado' : Math.abs(Number(value)) >= 1_000_000 ? `R$ ${(Number(value) / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi` : money(value)

function Distribution({ data }) {
  const max = Math.max(1, ...data.map(b => b.itens))
  const available = data.some(b => b.itens)
  return <section className="card dashboard-chart"><h2>Distribuição de scores</h2><p className="sub">Índice de 0 a 100 · posição relativa ao treino de cada grupo</p>
    {!available ? <p className="dashboard-chart-empty">Nenhum índice disponível neste recorte.</p> : <div className="dashboard-chart-scroll" role="region" aria-label="Distribuição dos índices; use as setas para rolar" tabIndex={0}><div className="dashboard-bins">{data.map((b, i) => <div className="dashboard-bin" key={b.inicio}><div className="dashboard-bar-track"><div className="dashboard-bar" style={{ height: `${100 * b.itens / max}%`, background: `var(${i < 5 ? '--baixa' : i < 8 ? '--media' : '--alta'})` }}><span>{b.itens}</span></div></div><small>{range(b, i)}</small></div>)}</div></div>}
    <div className="dashboard-legend">{[[0, 5, '0–49', 'baixa'], [5, 8, '50–79', 'media'], [8, 10, '80–100', 'alta']].map(([start, end, label, color]) => <span key={label}><i style={{ background: `var(--${color})` }} />{label}: {number(data.slice(start, end).reduce((n, b) => n + b.itens, 0))}</span>)}</div>
    <p className="dashboard-chart-caption">{number(data.reduce((n, b) => n + b.itens, 0))} itens com índice disponível · um índice máximo por item</p>
    <details className="dashboard-chart-data"><summary>Ver dados da distribuição</summary><table className="tbl"><caption>Contagem de itens por intervalo</caption><thead><tr><th scope="col">Intervalo</th><th scope="col">Itens</th></tr></thead><tbody>{data.map((b, i) => <tr key={b.inicio}><th scope="row">{range(b, i)}</th><td>{b.itens}</td></tr>)}</tbody></table></details>
  </section>
}

function Evolution({ data }) {
  const id = useId()
  const dated = data.filter(m => m.mes !== 'sem_data').sort((a, b) => a.mes.localeCompare(b.mes))
  const unknown = data.filter(m => m.mes === 'sem_data').reduce((n, m) => n + m.itens, 0)
  const count = m => m.analisados + m.parcial
  const max = Math.max(1, ...dated.map(count))
  const serial = m => Number(m.slice(0, 4)) * 12 + Number(m.slice(5, 7))
  const first = dated.length ? serial(dated[0].mes) : 0
  const last = dated.length ? serial(dated.at(-1).mes) : 0
  const points = dated.map(m => ({ ...m, n: count(m), x: first === last ? 230 : 38 + (serial(m.mes) - first) * 382 / (last - first), y: 142 - 108 * count(m) / max }))
  const oneYear = new Set(dated.map(m => m.mes.slice(0, 4))).size <= 1
  const ticks = []
  points.forEach((p, i) => { if (!ticks.length || p.x - points[ticks.at(-1)].x >= (oneYear ? 55 : 100)) ticks.push(i) })
  if (points.length && ticks.at(-1) !== points.length - 1) {
    while (ticks.length > 1 && points.at(-1).x - points[ticks.at(-1)].x < (oneYear ? 55 : 100)) ticks.pop()
    ticks.push(points.length - 1)
  }
  const hasAnalysis = points.some(p => p.n)
  const line = points.map(p => `${p.x},${p.y}`).join(' ')
  return <section className="card dashboard-chart"><h2>Evolução dos itens analisados</h2><p className="sub">Quantidade de itens por mês do último resultado conhecido</p>
    {hasAnalysis ? <svg className="dashboard-line" viewBox="0 0 450 180" role="img" aria-labelledby={id}>
      <title id={id}>{points.map(p => `${month(p.mes)}: ${p.n} itens com análise`).join('; ')}</title>
      {[0, 0.5, 1].map(t => <g key={t}><line x1="38" x2="420" y1={142 - 108 * t} y2={142 - 108 * t} className="dashboard-grid-line" /><text x="30" y={146 - 108 * t} textAnchor="end">{Math.round(max * t)}</text></g>)}
      {points.length > 1 && <><polygon points={`${points[0].x},142 ${line} ${points.at(-1).x},142`} className="dashboard-line-area" /><polyline points={line} className="dashboard-line-path" /></>}
      {points.map((p, i) => <g key={p.mes}><circle cx={p.x} cy={p.y} r="3" className="dashboard-point" />{ticks.includes(i) && <><text x={p.x} y={p.y - 10} textAnchor="middle">{p.n}</text><text x={p.x} y="164" textAnchor={i === 0 && points.length > 1 ? 'start' : i === points.length - 1 && points.length > 1 ? 'end' : 'middle'}>{months[Number(p.mes.slice(5, 7)) - 1]}{oneYear ? '' : ` ${p.mes.slice(2, 4)}`}</text></>}</g>)}
    </svg> : <p className="dashboard-chart-empty">Nenhum item analisado nos meses com data conhecida.</p>}
    <p className="dashboard-chart-caption">{dated.length > 0 && `${dated[0].mes.slice(0, 4)}${oneYear ? '' : `–${dated.at(-1).mes.slice(0, 4)}`} · `}{unknown ? `${number(unknown)} itens sem data de resultado ficam fora do eixo temporal.` : 'Cada item aparece uma vez; não representa a data de pagamento.'}</p>
    <details className="dashboard-chart-data"><summary>Ver dados da evolução</summary><table className="tbl"><caption>Cobertura de análise por mês</caption><thead><tr><th scope="col">Mês</th><th scope="col">Com análise</th><th scope="col">Total de itens</th></tr></thead><tbody>{data.map(m => <tr key={m.mes}><th scope="row">{m.mes === 'sem_data' ? 'Sem data conhecida' : month(m.mes)}</th><td>{count(m)}</td><td>{m.itens}</td></tr>)}</tbody></table></details>
  </section>
}

function ModelReading({ item, baseId, executionId }) {
  const [chosen, setChosen] = useState('')
  const query = useApi(`/analises/execucoes/${encodeURIComponent(executionId || '')}/itens/${item?.id}`, { base_id: baseId }, !!item && !!executionId)
  const scores = query.data?.dados[0]?.resultados || []
  const results = [...new Set(scores.map(s => s.resultado_item_id))].sort()
  const resultId = results.includes(chosen) ? chosen : results[0]
  const supplier = item?.resultados.find(r => r.id === resultId)?.fornecedor_nome
  return <section className="card dashboard-reading"><h2>Leitura dos modelos</h2><p className="sub">Comparação dos índices para o mesmo resultado</p>
    {!item ? <p className="dashboard-muted">Selecione um item com análise disponível.</p> : <>
      <p className="dashboard-selected">Compra {item.processo.numero_compra} · Item {item.numero_item}</p>
      <QueryState query={query} loading="Consultando os modelos do item…" />
      {results.length > 1 && <Field label="Resultado do fornecedor"><select className="select" value={resultId} onChange={e => setChosen(e.target.value)}>{results.map(id => <option key={id} value={id}>{item.resultados.find(r => r.id === id)?.fornecedor_nome || id.slice(0, 8)}</option>)}</select></Field>}
      {supplier && <p className="dashboard-supplier" title={supplier}>{supplier}</p>}
      {scores.filter(s => s.resultado_item_id === resultId).map(score => <div className="dashboard-model" key={score.id}><span title={`Modelo ${score.modelo_id}`}>{algorithm(score.algoritmo)}</span><strong>{decimal(score.indice_experimental)} <small>/ 100</small></strong></div>)}
      {query.data && !scores.length && <p>Nenhum índice disponível para este item na execução.</p>}
      <Link className="link-a" to={selectionLink(`/itens/${item.id}`, `base_id=${baseId}&execucao_id=${executionId}`)}>Ver análise do item <ArrowRight size={13} /></Link>
    </>}
    <p className="dashboard-model-note">Análise experimental · utilidade não validada</p>
    <p className="hint">Os modelos podem discordar. Índices não são probabilidades nem devem ser somados.</p>
  </section>
}

export default function PainelGeral({ query, ranking, params, Filters }) {
  const { baseId, data: baseData } = useBase()
  const selection = useAnalysis()
  const [settings, setSettings] = useState(false)
  const [chosen, setChosen] = useState('')
  const data = query.data
  const rows = ranking.data?.dados.filter(r => r.indice_experimental != null) || []
  const selected = rows.find(r => r.id === chosen) || rows[0]
  const summary = data?.resumo
  const periodLabel = period(baseData?.base?.periodo_inicio, baseData?.base?.periodo_fim)
  const activeFilters = ['busca', 'orgao_id', 'fornecedor_id', 'modalidade_id', 'homologacao_inicio', 'homologacao_fim', 'valor_minimo', 'valor_maximo'].filter(key => params.get(key)).length + (params.get('analise') && params.get('analise') !== 'todos' ? 1 : 0)
  const withAnalysis = summary ? summary.analisados + summary.parcial : 0
  const cards = summary ? [
    ['Processos no recorte', number(summary.processos), `${number(summary.orgaos)} órgãos · ${number(summary.fornecedores)} fornecedores`, Files],
    ['Valor homologado', compactMoney(summary.valor_homologado), 'Resultados não cancelados do recorte', Wallet],
    ['Itens com análise', number(withAnalysis), `${number(summary.itens)} itens importados · ${summary.itens ? (100 * withAnalysis / summary.itens).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) : 0}% com índice`, Activity],
    ['Sem análise', number(summary.nao_analisados), 'Motivos detalhados na consulta', ScanSearch],
  ] : []
  return <div className="dashboard">
    <Head kicker={`Visão consolidada / ${periodLabel}`} title="Clareza para priorizar a análise." sub="Acompanhe sinais estatísticos de compras públicas em um único lugar."
      action={<button className="btn ghost dashboard-period" aria-expanded={settings} aria-controls="dashboard-settings" title="Período da base; abrir filtros e versão da análise" onClick={() => setSettings(s => !s)}><CalendarDays size={16} />{periodLabel}</button>} />
    <details id="dashboard-settings" className="dashboard-settings" open={settings} onToggle={e => setSettings(e.currentTarget.open)}><summary>Filtros e versão da análise{activeFilters > 0 && <span className="pill ana">{activeFilters} filtro(s) aplicado(s)</span>}</summary><AnalysisSelector /><Filters /></details>
    <QueryState query={query} />
    {data && <>
      <div className="dashboard-kpis">{cards.map(([label, value, note, Icon], i) => <section className="card kpi" key={label}><div className="dashboard-kpi-label"><span>{label}</span><Icon size={17} aria-hidden="true" /></div><strong title={i === 1 ? money(summary.valor_homologado) : undefined}>{value}</strong><small>{note}</small></section>)}</div>
      <div className="dashboard-charts"><Distribution data={data.distribuicao} /><Evolution data={data.evolucao} /></div>
      <div className="dashboard-bottom"><section className="card dashboard-start"><div className="mini"><div><h2>Por onde começar</h2><p className="sub">Maiores índices disponíveis no recorte · ordenação exploratória</p></div><Link className="link-a" to={selectionLink('/ranking', params)}>Ver todos <ArrowRight size={13} /></Link></div>
        <QueryState query={ranking} loading="Consultando itens do recorte…" />
        {ranking.data && (!rows.length ? <p className="dashboard-muted">Nenhum item com índice disponível nos filtros selecionados.</p> : <div className="table-scroll" role="region" aria-label="Itens com maior índice; use as setas para rolar" tabIndex={0}><table className="tbl"><thead><tr><th scope="col">Compra / item</th><th scope="col">Órgão / fornecedor</th><th scope="col">Homologado</th><th scope="col">Índice</th></tr></thead><tbody>{rows.map(row => <tr key={row.id} className={selected?.id === row.id ? 'sel' : ''}><td><button className="dashboard-row-select" aria-pressed={selected?.id === row.id} onClick={() => setChosen(row.id)}>Compra {row.processo.numero_compra} · item {row.numero_item}</button><small className="dashboard-clamp" title={row.descricao}>{row.descricao}</small></td><td><span className="dashboard-clamp" title={row.processo.orgao_nome}>{row.processo.orgao_nome}</span><small className="dashboard-clamp" title={[...new Set(row.resultados.map(r => r.fornecedor_nome))].join('; ')}>{[...new Set(row.resultados.map(r => r.fornecedor_nome))].join('; ') || 'Fornecedor não informado'}</small></td><td className="numeric">{money(row.valor_homologado)}</td><td className="numeric dashboard-index">{decimal(row.indice_experimental)}</td></tr>)}</tbody></table></div>)}
      </section><ModelReading key={`${selection.executionId}:${selected?.id}`} item={selected} baseId={baseId} executionId={selection.executionId} /></div>
      <Aviso detalhe />
      <details className="dashboard-chart-data dashboard-motives"><summary>Consultar motivos de indisponibilidade</summary>{Object.keys(data.motivos_indisponibilidade).length ? <ul>{Object.entries(data.motivos_indisponibilidade).map(([reason, n]) => <li key={reason}>{reason.replaceAll('_', ' ').toLocaleLowerCase('pt-BR')}: {n} ocorrência(s)</li>)}</ul> : <p>Nenhum motivo registrado neste recorte.</p>}</details>
    </>}
  </div>
}
