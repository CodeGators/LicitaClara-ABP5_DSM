import { Link, useSearchParams } from 'react-router-dom'
import { useBase } from '../BaseContext.jsx'
import { useAnalysis } from '../AnalysisContext.jsx'
import { decimal, selectionLink } from '../api.mjs'
import { Info, NoAnalysis, QueryState } from './consultas.jsx'
import useApi from '../useApi.js'

export default function SinteseProcesso({ processId }) {
  const { baseId } = useBase()
  const selection = useAnalysis()
  const [params] = useSearchParams()
  const execution = params.get('execucao_id')
  const enabled = !!execution && execution !== 'nenhuma'
  const query = useApi(`/analises/execucoes/${encodeURIComponent(execution || '')}/processos/${processId}`, { base_id: baseId, modelo_id: selection.modelId || undefined }, enabled)
  if (!enabled) return <NoAnalysis />
  const process = query.data?.dados[0]
  return <section className="card">
    <h2>Síntese experimental da licitação</h2>
    <p className="sub">O score integral exige análise de todos os itens e resultados do universo oficial consultado. A média dos sinais disponíveis descreve apenas a parte analisada. Não representa probabilidade de fraude ou prioridade validada.</p>
    <QueryState query={query} loading="Consultando a cobertura da licitação…" />
    {process?.status === 'sem_sintese' && <p>Esta versão da análise ainda não contém síntese por processo.</p>}
    {process?.resultados.map(result => <div key={result.id}>
      <h3>{result.algoritmo === 'autoencoder' ? 'Autoencoder' : 'Isolation Forest'}</h3>
      <div className="stats">
        <Info label="Score integral da licitação">{result.score_processo === null ? 'Indisponível' : decimal(result.score_processo)}</Info>
        <Info label="Média dos sinais disponíveis">{decimal(result.indice_observado)}</Info>
        <Info label="Itens integralmente analisados / itens oficiais">{result.cobertura.itens_oficiais === null ? 'Universo não confirmado' : `${result.cobertura.itens_integralmente_analisados} / ${result.cobertura.itens_oficiais}`}</Info>
      </div>
      {result.score_processo === null && <p className="note">{result.motivo === 'UNIVERSO_OFICIAL_NAO_CONFIRMADO' ? 'Falta confirmar o universo oficial de itens desta licitação.' : 'A cobertura é insuficiente para atribuir um score à licitação inteira.'}</p>}
      {result.limite_inferior !== null && result.score_processo === null && <p className="hint">Se todos os itens pudessem receber índices comparáveis, a média integral estaria entre {decimal(result.limite_inferior)} e {decimal(result.limite_superior)}. Esses limites não são uma estimativa de risco nem um intervalo de confiança.</p>}
      {!!result.sinais.itens.length && <><h4>Itens que sustentam os sinais observados</h4><ul className="document-list">{result.sinais.itens.map(item => {
        const context = new URLSearchParams(params)
        context.set('modelo_id', result.modelo_id)
        return <li key={item.item_id}><Link className="link-a" to={selectionLink(`/itens/${item.item_id}`, context)}>Item {item.numero_item || item.item_oficial} · índice observado {decimal(item.media_observada)}</Link></li>
      })}</ul></>}
    </div>)}
  </section>
}
