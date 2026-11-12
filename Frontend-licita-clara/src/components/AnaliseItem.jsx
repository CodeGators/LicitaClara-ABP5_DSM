import { useSearchParams } from 'react-router-dom'
import { useBase } from '../BaseContext.jsx'
import { useAnalysis } from '../AnalysisContext.jsx'
import { ifMeasure } from '../api.mjs'
import useApi from '../useApi.js'
import { NoAnalysis, QueryState } from './consultas.jsx'

export default function AnaliseItem({ item }) {
  const [params] = useSearchParams()
  const { baseId } = useBase()
  const selection = useAnalysis()
  const execution = params.get('execucao_id')
  const model = params.get('modelo_id')
  const enabled = !!execution && execution !== 'nenhuma'
  const query = useApi(`/analises/execucoes/${encodeURIComponent(execution || '')}/itens/${item.id}`, { base_id: baseId }, enabled)
  if (!enabled) return <NoAnalysis />
  if (model && selection.run.loading) return <QueryState query={selection.run} loading="Consultando o modelo selecionado…" />
  if (model && selection.run.data && !selection.run.data.modelos.some(m => m.id === model)) return <section className="card" role="alert"><h2>Modelo fora da execução selecionada</h2><p>Abra o ranking para escolher um modelo desta execução. Nenhuma medida de outro modelo será usado.</p></section>
  const data = query.data?.dados[0]
  const scores = data?.resultados.filter(r => r.algoritmo === 'isolation_forest' && (!model || r.modelo_id === model)) || []
  const coverage = data?.cobertura.filter(r => !model || r.modelo_id === model) || []
  return <section className="card"><h2>Análise experimental selecionada</h2><p className="sub">Medida original do Isolation Forest, de 0 a 1: maior indica maior anomalia. Não é percentil nem probabilidade. Resultados de fornecedores são apresentados separadamente.</p><QueryState query={query} />
    {data && (!scores.length ? <p>Nenhuma medida IF disponível para este item no modelo selecionado. {coverage.map(r => r.motivo?.replaceAll('_',' ').toLowerCase()).filter((r,i,all) => r && all.indexOf(r) === i).join('; ')}.</p> : <div className="table-scroll" role="region" aria-label="Resultados dos modelos; use as setas para rolar na horizontal" tabIndex={0}><table className="tbl"><thead><tr><th scope="col">Fornecedor</th><th scope="col">Modelo</th><th scope="col">Medida IF</th><th scope="col">Explicação</th></tr></thead><tbody>{scores.map(r => <tr key={r.id}><td>{item.resultados.find(e => e.id === r.resultado_item_id)?.fornecedor_nome || 'Fornecedor não localizado no item'}</td><td>{r.algoritmo === 'isolation_forest' ? 'Isolation Forest' : r.algoritmo === 'autoencoder' ? 'Autoencoder' : r.algoritmo}</td><td className="numeric">{ifMeasure(r.medida_if)}</td><td>{r.explicacao.status === 'disponivel' ? r.explicacao.parcelas.map(p => <p key={p.atributo}>{p.atributo === 'log_quantidade' ? 'Quantidade' : 'Preço relativo à mediana'}: {ifMeasure(p.parcela_score_bruto)} do erro bruto</p>) : 'Contribuição por atributo indisponível para este modelo'}<small>Parcelas AE são erros de reconstrução, não causas ou importância do IF.</small></td></tr>)}</tbody></table></div>)}
  </section>
}
