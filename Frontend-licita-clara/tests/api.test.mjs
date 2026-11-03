import test from 'node:test'
import assert from 'node:assert/strict'
import { ApiError, baseLink, createApiClient, date, decimal, money, safeOfficialUrl } from '../src/api.mjs'

test('dinheiro preserva decimais e inteiros acima do limite de Number', () => {
  assert.equal(money('9007199254740993.00000001'), 'R$ 9.007.199.254.740.993,00000001')
  assert.equal(money('0.00000000'), 'R$ 0,00')
  assert.equal(money(null), 'Não informado')
  assert.equal(decimal('3.00000001'), '3,00000001')
  assert.equal(decimal(null), 'Não informado')
  assert.equal(date('2026-09-01'), '01/09/2026')
})

test('URLs oficiais aceitam HTTP(S), sem credenciais ou execução de script', () => {
  assert.equal(safeOfficialUrl('javascript:alert(1)'), null)
  assert.equal(safeOfficialUrl('https://user:password@example.test'), null)
  assert.equal(safeOfficialUrl('/arquivo.pdf'), null)
  assert.equal(safeOfficialUrl('https://pncp.gov.br/arquivo'), 'https://pncp.gov.br/arquivo')
  assert.equal(baseLink('/itens/0001', 'base-1'), '/itens/0001?base_id=base-1')
})

test('cliente preserva strings decimais e escapa buscas na URL', async () => {
  let requested
  const get = createApiClient({ baseUrl: 'https://api.example.test/api/v1/', fetchImpl: async (url, options) => {
    requested = { url: new URL(url), options }
    return Response.json({ valor: '0.00000001' })
  } })
  assert.deepEqual(await get('/itens', { base_id: 'base', busca: '100% & ?', valor_minimo: '9007199254740993.00000001', nulo: null }), { valor: '0.00000001' })
  assert.equal(requested.url.pathname, '/api/v1/itens')
  assert.equal(requested.url.searchParams.get('busca'), '100% & ?')
  assert.equal(requested.url.searchParams.get('valor_minimo'), '9007199254740993.00000001')
  assert.equal(requested.url.searchParams.has('nulo'), false)
  assert.equal(requested.options.headers.Accept, 'application/json')
})

test('erro estruturado mantém status, código e referência de atendimento', async () => {
  const get = createApiClient({ fetchImpl: async () => Response.json({ erro: { mensagem: 'Item não encontrado.', codigo: 'item_nao_encontrado', request_id: 'req-1' } }, { status: 404 }) })
  await assert.rejects(get('/itens/ausente'), error => error instanceof ApiError && error.status === 404 && error.code === 'item_nao_encontrado' && error.requestId === 'req-1')
})

test('erro de rede e resposta inválida não expõem detalhes internos', async () => {
  const offline = createApiClient({ fetchImpl: async () => { throw new Error('PRIVATE_DETAIL') } })
  await assert.rejects(offline('/itens'), error => error.code === 'conexao_indisponivel' && !error.message.includes('PRIVATE_DETAIL'))
  const invalid = createApiClient({ fetchImpl: async () => new Response('<html>erro</html>') })
  await assert.rejects(invalid('/itens'), error => error.code === 'resposta_invalida')
})

test('cancelamento e timeout interrompem a consulta com estados distintos', async () => {
  const pending = async (_url, { signal }) => new Promise((_resolve, reject) => {
    const abort = () => reject(new DOMException('cancelado', 'AbortError'))
    if (signal.aborted) abort()
    else signal.addEventListener('abort', abort, { once: true })
  })
  const get = createApiClient({ fetchImpl: pending, timeoutMs: 10 })
  const controller = new AbortController()
  const request = get('/itens', {}, { signal: controller.signal })
  controller.abort()
  await assert.rejects(request, error => error.name === 'AbortError')
  await assert.rejects(get('/itens'), error => error.code === 'tempo_esgotado')
})

test('links analíticos preservam seleção e filtros sem carregar página ou parâmetros estranhos', async () => {
  const { selectionLink } = await import('../src/api.mjs')
  const url = new URL(selectionLink('/ranking', '?base_id=base&execucao_id=exec&modelo_id=model&busca=A%26B&pagina=9&estranho=valor'), 'https://example.test')
  assert.equal(url.searchParams.get('modelo_id'), 'model')
  assert.equal(url.searchParams.get('execucao_id'), 'exec')
  assert.equal(url.searchParams.get('busca'), 'A&B')
  assert.equal(url.searchParams.has('pagina'), false)
  assert.equal(url.searchParams.has('estranho'), false)
})
