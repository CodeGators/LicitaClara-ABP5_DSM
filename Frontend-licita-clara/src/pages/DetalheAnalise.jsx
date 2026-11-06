import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ArrowLeft, FilePlus2 } from 'lucide-react'
import { useBase } from '../BaseContext.jsx'
import { useAnalysis } from '../AnalysisContext.jsx'
import { date, decimal, money, reportLink, selectionLink } from '../api.mjs'
import { Documents, Field, Info, QueryState, Results } from '../components/consultas.jsx'
import { Head, Aviso, Progress } from '../components/ui.jsx'
import useApi from '../useApi.js'

const algorithm = name => ({ isolation_forest: 'Isolation Forest', autoencoder: 'Autoencoder' })[name] || name
const numeric = value => value != null && value !== '' && Number.isFinite(Number(value)) ? Number(value) : null

function Comparison({ item, result, score }) {
  const comparison = score?.atributos?.comparacao
  const median = numeric(comparison?.mediana)
  const price = numeric(result?.valor_unitario_homologado)
  const estimate = numeric(item.valor_unitario_estimado)
  const bars = [['Mediana do grupo de treino', median, 'var(--petroleo)'], ['Estimado do item', estimate, 'var(--secundario)'], ['Homologado do resultado', price, 'var(--alta)']]
  const max = Math.max(1, ...bars.map(([, value]) => value || 0)) * 1.1
  return <section className="card detail-comparison"><h2>Comparação com itens similares</h2><p className="sub">Preços unitários · referência histórica do modelo selecionado</p>
    <p className="detail-item-description">{item.descricao}</p><p className="hint">{item.catalogo || 'Catálogo não informado'} {item.codigo_catalogo} · {item.unidade_medida || 'Unidade não informada'} · Quantidade: {decimal(result?.quantidade_homologada ?? item.quantidade)}</p>
    {comparison ? <p className="hint">{comparison.n_treino != null ? `${Number(comparison.n_treino).toLocaleString('pt-BR')} observações no treino` : 'Quantidade do treino não informada'}</p> : <p className="hint">Referência de treino indisponível para este resultado.</p>}
    <div className="detail-bars">{bars.map(([label, value, color]) => <div key={label}><div className="mini"><span>{label}</span><strong style={{ color }}>{value == null ? 'Não informado' : money(value)}</strong></div>{value != null && <Progress pct={value} max={max} cor={color} />}</div>)}</div>
    {median > 0 && price != null && <p className="detail-price-ratio"><span className="pill ana">{(price / median).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}× a mediana</span> {((price / median - 1) * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}% em relação à mediana do treino</p>}
    <p className="hint">A referência usa o grupo histórico do modelo. A equivalência de especificações e condições de entrega exige conferência documental.</p>
    <details className="detail-result-data"><summary>Ver resultados e dados do item</summary><Results results={item.resultados} /><div className="stats"><Info label="Total homologado do item">{money(item.valor_homologado_item)}</Info><Info label="Quantidade do item">{decimal(item.quantidade)}</Info><Info label="Unidade">{item.unidade_medida || 'Não informada'}</Info></div></details>
  </section>
}

function Explanation({ score, result, children }) {
  const parts = score?.explicacao?.status === 'disponivel' ? score.explicacao.parcelas || [] : []
  const total = parts.reduce((sum, part) => sum + Math.max(0, numeric(part.parcela_score_bruto) || 0), 0)
  return <section className="card detail-explanation"><h2>Por que este item foi sinalizado?</h2><p className="sub">Dados utilizados e explicação disponível da análise</p>{children}
    <div className="detail-observations"><Info label="Modelo">{score ? algorithm(score.algoritmo) : 'Sem score disponível'}</Info><Info label="Quantidade homologada">{decimal(result?.quantidade_homologada)}</Info><Info label="Preço unitário homologado">{money(result?.valor_unitario_homologado)}</Info></div>
    {parts.length ? <><h3>Parcelas do erro de reconstrução</h3><div className="detail-bars">{parts.map(part => <div key={part.atributo}><div className="mini"><span>{({ log_quantidade: 'Quantidade', log_preco_mediana: 'Preço relativo à mediana' })[part.atributo] || part.atributo}</span><strong>{decimal(part.parcela_score_bruto)}</strong></div><Progress pct={Math.max(0, numeric(part.parcela_score_bruto) || 0)} max={total || 1} cor="var(--media)" /><p className="hint">{total > 0 ? `${(100 * Number(part.parcela_score_bruto) / total).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}% do erro bruto` : 'Sem erro de reconstrução'}</p></div>)}</div><p className="hint">Parcelas do Autoencoder são erros de reconstrução. Não representam causas ou importância dos atributos do Isolation Forest.</p></> : <p className="detail-unavailable">{score ? 'Contribuição por atributo indisponível para este modelo.' : 'Este resultado não possui score na execução selecionada.'}</p>}
    {score && <p className="hint">Score bruto: {decimal(score.score_bruto)} · Score de 0 a 100 relativo ao treino. Os scores dos modelos não são somados.</p>}
    <div className="note"><b>Próxima etapa da revisão</b>Conferir preços, quantidade, especificações e documentos antes de qualquer conclusão.</div>
  </section>
}

function Detail({ item }) {
  const { baseId } = useBase()
  const selection = useAnalysis()
  const location = useLocation()
  const [tab, setTab] = useState('sinais')
  const [origin] = useState(location.state?.from || '')
  const [chosenResult, setResult] = useState('')
  const process = item.processo
  const analysis = useApi(`/analises/execucoes/${encodeURIComponent(selection.executionId || '')}/itens/${item.id}`, { base_id: baseId }, !!selection.executionId && !!selection.ready)
  const processQuery = useApi(`/processos/${process.id}`, { base_id: baseId })
  const data = analysis.data?.dados[0]
  const allScores = data?.resultados || []
  const results = item.resultados.filter(r => !r.cancelado)
  const models = selection.run.data?.modelos || []
  const routes = new Map()
  if (selection.run.data?.roteamento_automatico) {
    for (const model of [...models].sort((a, b) => Number(a.algoritmo !== 'isolation_forest') - Number(b.algoritmo !== 'isolation_forest') || a.id.localeCompare(b.id))) {
      if (model.grupo && !routes.has(model.grupo)) routes.set(model.grupo, model.id)
    }
  }
  const eligible = allScores.filter(s => {
    if (selection.modelId) return s.modelo_id === selection.modelId
    const group = models.find(m => m.id === s.modelo_id)?.grupo
    return !group || !routes.has(group) || routes.get(group) === s.modelo_id
  }).filter(s => results.some(r => r.id === s.resultado_item_id))
  const preferred = [...eligible].sort((a, b) => Number(b.indice_experimental) - Number(a.indice_experimental) || a.id.localeCompare(b.id))[0]
  const result = results.find(r => r.id === chosenResult) || results.find(r => r.id === preferred?.resultado_item_id) || results[0]
  const scores = allScores.filter(s => s.resultado_item_id === result?.id)
  const candidates = eligible.filter(s => s.resultado_item_id === result?.id)
  const score = candidates.find(s => s.algoritmo === 'isolation_forest') || candidates[0]
  const invalidModel = selection.modelId && selection.run.data && !selection.run.data.modelos.some(m => m.id === selection.modelId)
  const activeScore = invalidModel ? null : score
  const mainProcess = processQuery.data?.processo
  const back = /^\/(painel|ranking|fornecedores)(\/[^?]*)?\?/.test(origin) ? origin : selectionLink('/ranking', location.search)
  const controls = <div className="detail-selection">{results.length > 1 && <Field label="Resultado do fornecedor"><select className="select" value={result?.id || ''} onChange={e => { setResult(e.target.value) }}>{results.map(r => <option key={r.id} value={r.id}>{r.fornecedor_nome} · Resultado {r.sequencial_resultado}</option>)}</select></Field>}{!invalidModel && (scores.length > 1 || (scores.length === 1 && !activeScore)) && <Field label="Modelo da comparação"><select className="select" value={activeScore?.modelo_id || ''} onChange={e => selection.setSelection('modelo_id', e.target.value)}>{!activeScore && <option value="" disabled>Modelo selecionado sem score</option>}{scores.map(s => <option key={s.id} value={s.modelo_id}>{algorithm(s.algoritmo)}</option>)}</select></Field>}</div>
  return <div className="analysis-detail">
    <Head kicker="Ranking / Detalhe do item" title={`Compra ${process.numero_compra} · Item ${item.numero_item}`} sub={`${item.descricao} · ${process.orgao_nome} · ${process.modalidade_nome || 'Modalidade não informada'}`} action={<Link className="btn primary" to={reportLink(process.id, location.search)}><FilePlus2 size={16} />Incluir no relatório</Link>} />
    <section className="card detail-summary"><div className="detail-facts">
      <Info label="Valor estimado da compra">{money(mainProcess?.valor_estimado_processo)}</Info><Info label="Valor homologado da compra">{money(mainProcess?.valor_homologado_processo)}</Info><Info label="Fornecedor do resultado">{result?.fornecedor_nome || 'Não informado'}</Info>
      <Info label="Publicação → resultado do item">{date(process.data_publicacao)} → {date(result?.data_resultado)}</Info><Info label="Total homologado do resultado">{money(result?.valor_total_homologado)}</Info><Info label="Situação da revisão">Não registrada</Info>
      <p className="hint detail-summary-note">Valores da compra e do resultado são distintos. O score ao lado pertence ao resultado do item, sem score agregado da licitação.</p><QueryState query={processQuery} loading="Consultando valores da compra…" />
    </div><div className="detail-score"><span className="pill ana">Score do item · experimental</span><div className="detail-score-number">{activeScore ? decimal(activeScore.indice_experimental) : '—'}<small>/ 100</small></div><p className="hint">{activeScore ? algorithm(activeScore.algoritmo) : 'Sem score disponível'}</p><p className="hint">{!invalidModel && scores.filter(s => s !== activeScore).map(s => `${algorithm(s.algoritmo)}: ${decimal(s.indice_experimental)}`).join(' · ')}</p></div></section>
    <Aviso detalhe />
    <nav className="tabs" aria-label="Seções da análise">{[['sinais', 'Sinais e comparação'], ['docs', 'Documentos'], ['revisao', 'Registro da revisão']].map(([key, label]) => <button key={key} className={tab === key ? 'on' : ''} aria-pressed={tab === key} onClick={() => setTab(key)}>{label}</button>)}</nav>
    <QueryState query={analysis} loading="Consultando análise do item…" />
    {invalidModel && <p className="note" role="alert">Modelo fora da execução selecionada. Nenhum score de outro modelo será usado.</p>}
    {tab === 'sinais' && <>
      {!activeScore && !analysis.loading && !analysis.error && <p className="note">Nenhum score disponível para este resultado no modelo selecionado. {[...new Set((data?.cobertura || []).filter(c => (!selection.modelId || c.modelo_id === selection.modelId) && (!c.resultado_item_id || c.resultado_item_id === result?.id)).map(c => c.motivo?.replaceAll('_', ' ').toLowerCase()).filter(Boolean))].join('; ')}. Ausência de score não representa regularidade.</p>}
      <div className="detail-panels"><Comparison item={item} result={result} score={activeScore} /><Explanation score={activeScore} result={result}>{controls}</Explanation></div></>}
    {tab === 'docs' && <Documents key={`${baseId}:${process.id}`} processId={process.id} baseId={baseId} />}
    {tab === 'revisao' && <section className="card"><h2>Registro da revisão</h2><p className="sub">Nenhuma revisão humana registrada. A persistência de pareceres ainda não está disponível nesta versão.</p></section>}
    <section className="card detail-review"><div><h2>Revisão humana</h2><p className="sub">A análise estatística exige conferência documental. Nenhuma conclusão de auditoria registrada.</p></div><span className="pill rev">Não registrada</span></section>
    <div className="detail-footer"><Link className="link-a" to={back}><ArrowLeft size={14} />Voltar à consulta</Link><Link className="link-a" to={selectionLink(`/processos/${process.id}`, location.search)}>Ver todos os itens da compra</Link></div>
  </div>
}

export default function DetalheAnalise() {
  const { id } = useParams()
  const { baseId } = useBase()
  const query = useApi(`/itens/${encodeURIComponent(id)}`, { base_id: baseId }, !!baseId)
  return query.data ? <Detail key={`${baseId}:${id}`} item={query.data.item} /> : <QueryState query={query} loading="Carregando item…" />
}
