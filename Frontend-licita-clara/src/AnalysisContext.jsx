import { createContext, useContext, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useBase } from './BaseContext.jsx'
import useApi from './useApi.js'
import { Field, QueryState } from './components/consultas.jsx'

const Context = createContext(null)
export const useAnalysis = () => useContext(Context)
export { viewFields, selectionLink } from './api.mjs'

export function AnalysisProvider({ enabled, children }) {
  const base = useBase()
  const [params, setParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const selected = params.get('execucao_id') || ''
  const modelId = params.get('modelo_id') || ''
  const validBase = !!(enabled && base.baseId && base.data?.base)
  const publication = useApi('/analises/publicacao', { base_id: base.baseId }, validBase && !params.has('execucao_id'))
  const runs = useApi('/analises/execucoes', { base_id: base.baseId, pagina: page, tamanho_pagina: 20 }, validBase)
  const executionId = selected && selected !== 'nenhuma' ? selected : ''
  const run = useApi(`/analises/execucoes/${encodeURIComponent(executionId)}`, { base_id: base.baseId }, validBase && !!executionId)
  useEffect(() => {
    if (validBase && !params.has('execucao_id') && publication.data) setParams(previous => {
      if (previous.has('execucao_id')) return previous
      const next = new URLSearchParams(previous)
      next.set('execucao_id', publication.data.execucao_id || 'nenhuma')
      next.delete('modelo_id')
      return next
    }, { replace: true })
  }, [validBase, params, publication.data, setParams])
  useEffect(() => {
    if (run.data && !run.data.roteamento_automatico && !modelId && run.data.modelos.some(m => m.algoritmo === 'isolation_forest')) setParams(previous => {
      const next = new URLSearchParams(previous)
      if (next.get('execucao_id') !== executionId || next.get('modelo_id')) return previous
      const models = run.data.modelos.filter(m => m.algoritmo === 'isolation_forest').sort((a, b) => a.id.localeCompare(b.id))
      next.set('modelo_id', (models.find(m => m.algoritmo === 'isolation_forest') || models[0]).id)
      return next
    }, { replace: true })
  }, [run.data, executionId, modelId, setParams])
  const ready = validBase && params.has('execucao_id') && (!executionId || (run.data && (modelId || run.data.roteamento_automatico || !run.data.modelos.some(m => m.algoritmo === 'isolation_forest'))))
  const setSelection = (key, value) => setParams(previous => {
    const next = new URLSearchParams(previous)
    next.set(key, value); next.delete('pagina'); next.delete('pagina_itens')
    if (key === 'execucao_id') next.delete('modelo_id')
    return next
  })
  return <Context.Provider value={{ ready, executionId, modelId, run, runs, publication, page, setPage, params, setParams, setSelection, selected }}>{children}</Context.Provider>
}

export function AnalysisGate({ children }) {
  const selection = useAnalysis()
  if (selection.executionId && selection.run.error) return <><h1>Não foi possível abrir a análise</h1><AnalysisSelector /><QueryState query={selection.run} /></>
  if (selection.publication.error && !selection.params.has('execucao_id')) return <section><h1>Consulta da análise</h1><QueryState query={selection.publication} /></section>
  if (!selection.ready) return <section><h1 className="sr-only">Consulta da análise</h1><div className="card" role="status">Selecionando a versão da análise…</div></section>
  return children
}

const modelName = m => m.algoritmo === 'autoencoder' ? 'Autoencoder' : m.algoritmo === 'isolation_forest' ? 'Isolation Forest' : m.algoritmo

// Linha resumida: mostra a análise em uso e só abre as opções quando a pessoa pede.
export function AnalysisSelector({ allModels = false }) {
  const s = useAnalysis()
  const model = s.run.data?.modelos.find(m => m.id === s.modelId)
  const when = s.run.data?.concluido_em ? new Date(s.run.data.concluido_em).toLocaleDateString('pt-BR') : null
  const summary = !s.executionId ? 'Sem análise: só dados importados'
    : [when && `versão de ${when}`, allModels ? 'todos os modelos' : model ? modelName(model) : s.run.data?.roteamento_automatico ? 'modelo automático por item' : null].filter(Boolean).join(' · ') || 'carregando…'
  return <details className="card analysis-bar" aria-label="Seleção da análise">
    <summary><span className="ab-label">Versão da análise</span><span className="ab-value">{summary}</span><span className="ab-change">Alterar</span></summary>
    <div className="ab-body">
      <div className="ab-fields">
        <Field label="Execução publicada"><select className="select" value={s.selected || 'nenhuma'} onChange={e => s.setSelection('execucao_id', e.target.value)}>
          <option value="nenhuma">Consultar sem análise</option>
          {s.executionId && !s.runs.data?.dados.some(r => r.id === s.executionId) && <option value={s.executionId}>Execução selecionada · {s.executionId.slice(0, 8)}</option>}
          {(s.runs.data?.dados || []).map(r => <option key={r.id} value={r.id}>{new Date(r.concluido_em).toLocaleString('pt-BR')} · {r.id.slice(0, 8)}</option>)}
        </select></Field>
        {!allModels && <Field label="Modelo experimental"><select className="select" value={s.modelId} disabled={!s.executionId} onChange={e => s.setSelection('modelo_id', e.target.value)}>
          {s.run.data?.roteamento_automatico && <option value="">Automático por item</option>}
          {!s.run.data?.modelos.some(m => m.algoritmo === 'isolation_forest') && <option value="">Sem modelo selecionado</option>}
          {s.modelId && !s.run.data?.modelos.some(m => m.id === s.modelId) && <option value={s.modelId}>Modelo fora desta execução</option>}
          {(s.run.data?.modelos || []).filter(m => m.algoritmo === 'isolation_forest').map(m => <option key={m.id} value={m.id}>{modelName(m)} · {m.catalogo ? `CATMAT ${m.catalogo} · ` : ''}{m.id.slice(0, 8)}</option>)}
        </select></Field>}
      </div>
      {s.runs.error && <p role="alert">Não foi possível carregar as versões. <button className="link-a" onClick={s.runs.retry}>Tentar novamente</button></p>}
      {s.runs.data?.total_paginas > 1 && <div className="pager"><button className="btn ghost sm" disabled={s.page === 1} onClick={() => s.setPage(p => p - 1)}>Versões anteriores</button><span>{s.page}/{s.runs.data.total_paginas}</span><button className="btn ghost sm" disabled={s.page >= s.runs.data.total_paginas} onClick={() => s.setPage(p => p + 1)}>Mais versões</button></div>}
      <p className="hint">{allModels ? 'O relatório mostra a medida original do IF e, separadamente, o erro de reconstrução do Autoencoder, em outra escala.' : 'Cada item usa o Isolation Forest do seu grupo. Medida original de 0 a 1: maior indica maior anomalia. Não é percentil ou probabilidade. Grupos sem IF disponível ficam sem medida.'}</p>
    </div>
  </details>
}
