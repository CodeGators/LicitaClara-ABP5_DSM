import test from 'node:test'
import assert from 'node:assert/strict'
import { ApiError, baseLink, createApiClient, date, decimal, ifMeasure, exactDecimal, money, safeOfficialUrl } from '../src/api.mjs'

test('exibição arredonda sem perder inteiros acima do limite de Number', () => {
  assert.equal(money('9007199254740993.00000001'), 'R$ 9.007.199.254.740.993,00')
  assert.equal(money('0.00000000'), 'R$ 0,00')
  assert.equal(money(null), 'Não informado')
  assert.equal(decimal('3.00000001'), '3')
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


test('arredondamento visual mantém valores pequenos, precisão original e HHI', () => {
  assert.equal(decimal('88.125'), '88,13')
  assert.equal(decimal('-1.235'), '-1,24')
  assert.equal(money('999.995'), 'R$ 1.000,00')
  assert.equal(money('0.004'), 'R$ 0,004')
  assert.equal(decimal('-0.00000001'), '-0,00000001')
  assert.equal(decimal('0.31567', 0, 4), '0,3157')
  assert.equal(exactDecimal('20.33333333'), '20,33333333')
  assert.equal(money('9007199254740993.995'), 'R$ 9.007.199.254.740.994,00')
})


test('medida IF mantém quatro casas e não converte para percentil', () => {
  assert.equal(ifMeasure('0.69103'), '0,6910')
  assert.equal(ifMeasure('0.514'), '0,5140')
  assert.equal(ifMeasure('1'), '1,0000')
  assert.equal(ifMeasure('0'), '0,0000')
  assert.equal(ifMeasure(null), 'Indisponível')
})

import { requiresPriceReview, itemRequiresPriceReview } from '../src/priceValidation.mjs'

test('revisão de preço é estritamente acima de 500%, antes do arredondamento', () => {
  assert.equal(requiresPriceReview('600', '100', 'UN'), false)
  assert.equal(requiresPriceReview('600.00000001', '100', 'UN'), true)
  assert.equal(requiresPriceReview('599.99999999', '100', 'UN'), false)
  assert.equal(requiresPriceReview('216.18', '22.8', 'UN'), true)
  assert.equal(requiresPriceReview('30185.2', '0.8', 'copo de 200 ml'), true)
  for (const [p, m, u] of [[null, '1', 'UN'], ['1', '0', 'UN'], ['1', '-1', 'UN'], ['900', '1', null], ['Infinity', '1', 'UN']]) assert.equal(requiresPriceReview(p, m, u), false)
})

test('revisão vincula preço e referência ao mesmo resultado, inclusive covencedores', () => {
  const item = { resultados: [{ id: 'a', valor_unitario_homologado: '1' }, { id: 'b', valor_unitario_homologado: '100' }], scores: [{ resultado_item_id: 'a', atributos: { comparacao: { mediana: '1', unidade_preco: { unidade_preco: 'UN' } } } }] }
  assert.equal(itemRequiresPriceReview(item), false)
  item.scores[0].resultado_item_id = 'b'
  assert.equal(itemRequiresPriceReview(item), true)
})

import { ifBand } from '../src/ifBands.mjs'

test('faixas visuais usam IF sem arredondamento e ignoram produtos que requerem validação', () => {
  for (const value of ['0', '0.49', '0.499999999999']) assert.equal(ifBand({ medida_if: value }), 'green')
  for (const value of ['0.50', '0.69', '0.699999999999']) assert.equal(ifBand({ medida_if: value }), 'yellow')
  for (const value of ['0.70', '0.99', '1']) assert.equal(ifBand({ medida_if: value }), 'red')
  for (const value of [null, undefined, '', ' ', 'invalido', 'Infinity', -1, 1.01, false]) assert.equal(ifBand({ medida_if: value }), '')
  for (const value of ['0.2', '0.6', '0.9']) assert.equal(ifBand({ medida_if: value, requer_validacao: true }), '')
})

test('cliente e links preservam múltiplas sinalizações como parâmetros repetidos', async () => {
  let requested
  const client = createApiClient({ fetchImpl: async url => {
    requested = new URL(url)
    return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } })
  } })
  await client('/visao/produtos', { sinalizacao: ['menor_anomalia', 'maior_anomalia'], busca: 'água' })
  assert.deepEqual(requested.searchParams.getAll('sinalizacao'), ['menor_anomalia', 'maior_anomalia'])
  const { selectionLink } = await import('../src/api.mjs')
  const link = new URL(selectionLink('/ranking', requested.searchParams), 'http://localhost')
  assert.deepEqual(link.searchParams.getAll('sinalizacao'), ['menor_anomalia', 'maior_anomalia'])
})
