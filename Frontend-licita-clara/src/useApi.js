import { useEffect, useState } from 'react'
import { api } from './api.mjs'

export default function useApi(path, params = {}, enabled = true) {
  const key = JSON.stringify([path, params, enabled])
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState({ key: null, data: null, loading: enabled, error: null })
  useEffect(() => {
    if (!enabled) return
    const controller = new AbortController()
    let active = true
    setState({ key, data: null, loading: true, error: null })
    api(path, params, { signal: controller.signal }).then(
      data => active && setState({ key, data, loading: false, error: null }),
      error => active && error.name !== 'AbortError' && setState({ key, data: null, loading: false, error }),
    )
    return () => { active = false; controller.abort() }
  }, [key, attempt])
  const current = state.key === key ? state : { data: null, loading: enabled, error: null }
  return { ...current, retry: () => setAttempt(value => value + 1) }
}
