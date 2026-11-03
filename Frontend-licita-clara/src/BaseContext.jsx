import { createContext, useContext, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import useApi from './useApi.js'
import { QueryState } from './components/consultas.jsx'

const Context = createContext(null)
export const useBase = () => useContext(Context)

export function BaseProvider({ enabled, children }) {
  const [params, setParams] = useSearchParams()
  const selected = params.get('base_id') || ''
  const query = useApi('/base/status', { base_id: selected }, enabled)
  const baseId = selected || query.data?.base?.id
  useEffect(() => {
    if (enabled && !selected && query.data?.base?.id) setParams(previous => {
      const next = new URLSearchParams(previous)
      if (!next.get('base_id')) next.set('base_id', query.data.base.id)
      return next
    }, { replace: true })
  }, [enabled, selected, query.data, setParams])
  return <Context.Provider value={{ ...query, baseId, enabled }}>{children}</Context.Provider>
}

export function BaseGate({ children }) {
  const base = useBase()
  if (base.loading || base.error) return <QueryState query={base} loading="Consultando a base de dados…" />
  if (!base.data?.base) return <div className="card" role="status"><h2>Nenhuma base disponível</h2><p className="sub">Ainda não há dados importados disponíveis para consulta.</p><button className="btn ghost sm" onClick={base.retry}>Consultar novamente</button></div>
  return children
}
