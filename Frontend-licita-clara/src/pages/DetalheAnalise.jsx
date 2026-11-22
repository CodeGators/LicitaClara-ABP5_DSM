import PriceReview from '../components/PriceReview.jsx'
import { requiresPriceReview } from '../priceValidation.mjs'
import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ArrowLeft, FilePlus2 } from 'lucide-react'
import { useBase } from '../BaseContext.jsx'
import { useAnalysis } from '../AnalysisContext.jsx'
import { date, decimal, exactDecimal, money, reportLink, selectionLink } from '../api.mjs'
import { Field, Info, QueryState, Results } from '../components/consultas.jsx'
import { Head, Progress } from '../components/ui.jsx'
import useApi from '../useApi.js'

const algorithm = name => ({ isolation_forest: 'Isolation Forest', autoencoder: 'Autoencoder' })[name] || name
const numeric = value => value != null && value !== '' && Number.isFinite(Number(value)) ? Number(value) : null

function Comparison({ item, result, score }) {
  const comparison = score?.atributos?.comparacao
  const basis = comparison?.unidade_preco?.unidade_preco
  const median = numeric(comparison?.mediana)
  const price = numeric(result?.valor_unitario_homologado)
  const estimate = numeric(item.valor_unitario_estimado)
  const bars = [[`Mediana de itens parecidos${basis ? ` (R$/${basis})` : ''}`, median, 'var(--petroleo)'], ['Estimado para o item', estimate, 'var(--secundario)'], ['Homologado neste resultado', price, 'var(--alta)']]
  const max = Math.max(1, ...bars.map(([, value]) => value || 0)) * 1.1
  return <section className="card detail-comparison"><h2>Preço pago e referência</h2><p className="sub">Preço por unidade.</p>
    <p className="detail-unit-basis"><strong>Unidade da mediana: {basis || 'Não informada'}</strong><br />Unidade registrada no item: {item.unidade_medida || 'Não informada'}</p>
    <p className="detail-item-description">{item.descricao}</p><p className="hint">{item.catalogo || 'Catálogo não informado'} {item.codigo_catalogo} · {item.unidade_medida || 'Unidade não informada'} · Quantidade: {decimal(result?.quantidade_homologada ?? item.quantidade)}</p>
    <div className="detail-bars">{bars.map(([label, value, color]) => <div key={label}><div className="mini"><span>{label}</span><strong title={value == null ? undefined : `Valor original: ${exactDecimal(value)}`} style={{ color }}>{value == null ? 'Não informado' : money(value)}</strong></div>{value != null && <Progress pct={value} max={max} cor={color} />}</div>)}</div>
    <details className="detail-result-data"><summary>Ver resultados e dados do item</summary><Results results={item.resultados} hideStatus /><div className="stats"><Info label="Total homologado do item">{money(item.valor_homologado_item)}</Info><Info label="Quantidade do item">{decimal(item.quantidade)}</Info><Info label="Unidade">{item.unidade_medida || 'Não informada'}</Info></div></details>
  </section>
}

function Detail({ item }) {
  const { baseId } = useBase()
  const selection = useAnalysis()
  const location = useLocation()
  const [origin] = useState(location.state?.from || '')
  const [chosenResult, setResult] = useState('')
  const process = item.processo
  const analysis = useApi(`/analises/execucoes/${encodeURIComponent(selection.executionId || '')}/itens/${item.id}`, { base_id: baseId }, !!selection.executionId && !!selection.ready)
  const processQuery = useApi(`/processos/${process.id}`, { base_id: baseId })
  const data = analysis.data?.dados[0]
  const allScores = (data?.resultados || []).filter(s => s.algoritmo === 'isolation_forest')
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
  const preferred = [...eligible].sort((a, b) => Number(b.medida_if) - Number(a.medida_if) || a.id.localeCompare(b.id))[0]
  const result = results.find(r => r.id === chosenResult) || results.find(r => r.id === preferred?.resultado_item_id) || results[0]
  const scores = allScores.filter(s => s.resultado_item_id === result?.id)
  const candidates = eligible.filter(s => s.resultado_item_id === result?.id)
  const score = candidates.find(s => s.algoritmo === 'isolation_forest') || candidates[0]
  const invalidModel = selection.modelId && selection.run.data && !selection.run.data.modelos.some(m => m.id === selection.modelId)
  const activeScore = invalidModel ? null : score
  const mainProcess = processQuery.data?.processo
  const back = /^\/(painel|ranking|licitacoes|fornecedores)(\/[^?]*)?\?/.test(origin) ? origin : selectionLink('/ranking', location.search)
  const controls = <div className="detail-selection">{results.length > 1 && <Field label="Resultado do fornecedor"><select className="select" value={result?.id || ''} onChange={e => { setResult(e.target.value) }}>{results.map(r => <option key={r.id} value={r.id}>{r.fornecedor_nome} · Resultado {r.sequencial_resultado}</option>)}</select></Field>}{!invalidModel && (scores.length > 1 || (scores.length === 1 && !activeScore)) && <Field label="Modelo da comparação"><select className="select" value={activeScore?.modelo_id || ''} onChange={e => selection.setSelection('modelo_id', e.target.value)}>{!activeScore && <option value="" disabled>Modelo selecionado sem medida IF</option>}{scores.map(s => <option key={s.id} value={s.modelo_id}>{algorithm(s.algoritmo)}</option>)}</select></Field>}</div>
  const comparison = activeScore?.atributos?.comparacao
  const median = numeric(comparison?.mediana)
  const price = numeric(result?.valor_unitario_homologado)
  const ratio = median > 0 && price != null ? price / median : null
  const difference = ratio == null ? null : (ratio - 1) * 100
  const fmt = v => v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return <div className="analysis-detail">
    <Link className="link-a back-link" to={back}><ArrowLeft size={16} />Voltar à consulta</Link>
    <Head title={`Compra ${process.numero_compra} · Item ${item.numero_item}`} sub={`${item.descricao} · ${process.orgao_nome}`} action={<Link className="btn primary" to={reportLink(process.id, location.search)}><FilePlus2 size={16} />Gerar relatório da licitação</Link>} />
    <section className="card detail-hero" aria-label="Resumo do item">
      <div className="detail-body">
        <div>{requiresPriceReview(result?.valor_unitario_homologado, comparison?.mediana, comparison?.unidade_preco?.unidade_preco) && <PriceReview />}</div>
        <p className="detail-headline">{ratio != null ? <>O preço unitário homologado foi <span className="pill ana">{difference === 0 ? 'igual à mediana' : `${fmt(Math.abs(difference))}% ${difference > 0 ? 'acima' : 'abaixo'} da mediana`}</span> de itens parecidos ({money(median)}).</> : 'Não há referência de preço suficiente para comparar este resultado.'}</p>
        <div className="detail-facts">
          <Info label="Fornecedor do resultado">{result?.fornecedor_nome || 'Não informado'}</Info>
          <Info label="Total homologado do resultado">{money(result?.valor_total_homologado)}</Info>
          <Info label="Publicação → resultado">{date(process.data_publicacao)} → {date(result?.data_resultado)}</Info>
          <Info label="Valor homologado da compra">{money(mainProcess?.valor_homologado_processo)}</Info>
        </div>
        <QueryState query={processQuery} loading="Consultando valores da compra…" />
        {controls}
      </div>
    </section>
    <QueryState query={analysis} loading="Consultando análise do item…" />
    {invalidModel && <p className="note" role="alert">Modelo fora da execução selecionada. Nenhum score de outro modelo será usado.</p>}
      {!activeScore && !analysis.loading && !analysis.error && <p className="note">Nenhuma medida IF disponível para este resultado no modelo selecionado. {[...new Set((data?.cobertura || []).filter(c => (!selection.modelId || c.modelo_id === selection.modelId) && (!c.resultado_item_id || c.resultado_item_id === result?.id)).map(c => c.motivo?.replaceAll('_', ' ').toLowerCase()).filter(Boolean))].join('; ')}. Ausência de medida IF não representa regularidade.</p>}
    <Comparison item={item} result={result} score={activeScore} />
    <div className="detail-footer"><Link className="link-a" to={selectionLink(`/processos/${process.id}`, location.search)}>Ver todos os itens da compra</Link></div>
  </div>
}

export default function DetalheAnalise() {
  const { id } = useParams()
  const { baseId } = useBase()
  const query = useApi(`/itens/${encodeURIComponent(id)}`, { base_id: baseId }, !!baseId)
  return query.data ? <Detail key={`${baseId}:${id}`} item={query.data.item} /> : <QueryState query={query} loading="Carregando item…" />
}
