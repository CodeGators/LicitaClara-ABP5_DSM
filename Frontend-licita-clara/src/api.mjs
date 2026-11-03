export class ApiError extends Error {
  constructor(message, { status = 0, code = 'conexao_indisponivel', requestId = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}

export function createApiClient({ baseUrl = '/api/v1', fetchImpl = globalThis.fetch, timeoutMs = 15000 } = {}) {
  const base = baseUrl.replace(/\/$/, '')
  return async function get(path, params = {}, { signal } = {}) {
    const url = new URL(`${base}${path}`, globalThis.location?.origin || 'http://localhost')
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== '') url.searchParams.set(key, String(value))
    }
    const controller = new AbortController()
    let timedOut = false
    const cancel = () => controller.abort()
    if (signal?.aborted) cancel()
    signal?.addEventListener('abort', cancel, { once: true })
    const timer = setTimeout(() => { timedOut = true; cancel() }, timeoutMs)
    try {
      const response = await fetchImpl(url.toString(), { signal: controller.signal, headers: { Accept: 'application/json' } })
      let body
      try { body = await response.json() } catch {
        throw new ApiError('Não foi possível interpretar a resposta do serviço.', { status: response.status, code: 'resposta_invalida' })
      }
      if (!response.ok) throw new ApiError(body.erro?.mensagem || 'Não foi possível concluir a consulta.', {
        status: response.status, code: body.erro?.codigo || 'consulta_falhou',
        requestId: body.erro?.request_id || response.headers.get('X-Request-ID'),
      })
      return body
    } catch (error) {
      if (signal?.aborted) throw new DOMException('Consulta cancelada', 'AbortError')
      if (timedOut) throw new ApiError('A consulta demorou mais que o esperado. Tente novamente.', { code: 'tempo_esgotado' })
      if (error instanceof ApiError) throw error
      throw new ApiError('Não foi possível conectar ao serviço. Verifique sua conexão e tente novamente.')
    } finally {
      clearTimeout(timer)
      signal?.removeEventListener('abort', cancel)
    }
  }
}

export const api = createApiClient({ baseUrl: import.meta.env?.VITE_API_URL || '/api/v1' })

// Formatação textual preserva inclusive valores maiores que Number.MAX_SAFE_INTEGER.
export function decimal(value, minimumFraction = 0) {
  if (value === null || value === undefined || value === '') return 'Não informado'
  const text = String(value)
  if (!/^-?\d+(\.\d+)?$/.test(text)) return 'Não informado'
  const [integer, raw = ''] = text.split('.')
  const fraction = raw.replace(/0+$/, '').padEnd(minimumFraction, '0')
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (fraction ? `,${fraction}` : '')
}

export const money = value => {
  const formatted = decimal(value, 2)
  return formatted === 'Não informado' ? formatted : `R$ ${formatted}`
}
export const date = value => value ? value.slice(0, 10).split('-').reverse().join('/') : 'Não informada'
export const baseLink = (path, baseId) => `${path}?${new URLSearchParams({ base_id: baseId })}`
export const safeOfficialUrl = value => {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null } catch { return null }
}

export const viewFields = ['busca', 'orgao_id', 'fornecedor_id', 'modalidade_id', 'homologacao_inicio', 'homologacao_fim', 'valor_minimo', 'valor_maximo', 'analise', 'ordenacao', 'tamanho_pagina']
const keys = ['base_id', 'execucao_id', 'modelo_id', ...viewFields]
export const selectionLink = (path, source) => {
  const params = new URLSearchParams(source)
  return `${path}?${new URLSearchParams([...params].filter(([key]) => keys.includes(key)))}`
}
