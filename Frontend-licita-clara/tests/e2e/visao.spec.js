import AxeBuilder from '@axe-core/playwright'
import { test, expect } from '@playwright/test'
import { BASE, ITEM, PROCESS, SUPPLIER, item, otherItem, mockApi } from './fixtures.js'

const EXEC = '77777777-7777-4777-8777-777777777777'
const NEW_EXEC = '77777777-7777-4777-8777-888888888888'
const MODEL = '88888888-8888-4888-8888-888888888888'
const OTHER_SUPPLIER = '99999999-9999-4999-8999-999999999999'
const AE = '88888888-8888-4888-8888-999999999999'

async function mockView(page, overrides = {}) {
  const state = await mockApi(page, { active: EXEC, scored: true, ...overrides, handler: async ({ url, path, send, error }) => {
    const done = async body => { await send(body); return true }
    const bad = async (message, status) => { await error(message, status); return true }
    if (path === '/analises/publicacao' && state.publicationOffline) return bad('Publicação indisponível.', 503)
    if (path === '/analises/publicacao') return done({ base_id: BASE, execucao_id: state.active, status: state.active ? 'publicada_experimental' : 'nao_publicada', experimental: true })
    const run = id => ({ id, roteamento_automatico: !!state.automatic, base_id: BASE, concluido_em: '2026-11-03T15:00:00Z', modelos: [{ id: MODEL, algoritmo: 'isolation_forest' }, { id: AE, algoritmo: 'autoencoder' }] })
    if (path === '/analises/execucoes') return done({ dados: [run(EXEC), run(NEW_EXEC)], total: 2, total_paginas: 1 })
    if (path === `/analises/execucoes/${EXEC}` || path === `/analises/execucoes/${NEW_EXEC}`) return done(run(path.split('/').at(-1)))
    if (state.bothModels && path.includes(`/itens/${ITEM}`) && path.startsWith('/analises/')) return done({ dados: [{ cobertura: [], resultados: [
      { id: 'score-if', modelo_id: MODEL, resultado_item_id: item.resultados[0].id, algoritmo: 'isolation_forest', medida_if: '0.514' },
      { id: 'score-ae', modelo_id: AE, resultado_item_id: state.separateResults ? 'co-vencedor' : item.resultados[0].id, algoritmo: 'autoencoder', medida_if: null, erro_reconstrucao: '0.4' },
    ] }] })
    if (state.automatic && path.startsWith('/analises/') && path.includes('/processos/')) return done({ dados: [{ id: PROCESS, status: 'disponivel', resultados: [], cobertura_agrupada: { itens_importados: 2, itens_com_analise: 1, resultados_ativos_importados: 2, resultados_com_analise: 1, quantidade_grupos: 1, itens_oficiais: null, score_processo: null } }] })
    if (path.startsWith('/analises/execucoes/') && !path.includes('/itens/')) return bad('Execução não publicada nesta base.', 404)
    if (path.includes(`/itens/${ITEM}`) && path.startsWith('/analises/')) return done({ dados: [{ cobertura: [{ modelo_id: MODEL, motivo: state.scored ? null : 'SEM_REFERENCIA_EXATA' }], resultados: state.scored ? [{ id: 'score-1', modelo_id: MODEL, resultado_item_id: item.resultados[0].id, algoritmo: 'isolation_forest', score_bruto: '0.514', medida_if: '0.514', explicacao: { status: 'indisponivel', parcelas: [] } }] : [] }] })
    if (!path.startsWith('/visao/')) return false
    if (state.viewOffline) return bad('Consulta do recorte indisponível.', 503)
    if (url.searchParams.get('modelo_id') === 'invalido') return bad('Modelo não pertence à execução selecionada.', 422)
    const hasScore = state.scored && url.searchParams.get('execucao_id') && (state.automatic || path === '/visao/produtos' || path.startsWith('/visao/fornecedores') || url.searchParams.get('modelo_id'))
    let rows = [item, state.twoScored ? { ...otherItem, resultados: [{ ...item.resultados[0], id: 'caneta-result', fornecedor_nome: 'Fornecedor da caneta', valor_unitario_homologado: '2.00' }] } : otherItem].map((r, i) => ({ ...r, resultados: r.resultados.filter(e => !e.cancelado), valor_homologado: r.valor_homologado_item, soma_valores_conhecidos: r.valor_homologado_item, resultados_sem_total: 0, resultados_analisados: (i === 0 || state.twoScored) && hasScore ? 1 : 0, status_analise: (i === 0 || state.twoScored) && hasScore ? 'analisados' : 'nao_analisados', medida_if: (i === 0 || state.twoScored) && hasScore ? '0.514' : null, scores: (i === 0 || state.twoScored) && hasScore ? [{ id: 'score-1', resultado_item_id: r.resultados[0].id, score_bruto: '0.514', atributos: { comparacao: { mediana: state.noReference ? null : state.extremePrice ? '0.01' : '0.05', n_treino: 100, unidade_preco: { unidade_preco: 'UN' } } } }] : [], motivos: (i === 0 || state.twoScored) && hasScore ? {} : { SEM_REFERENCIA_EXATA: 1 } }))
    if (state.separateResults) rows[0].resultados.push({ ...item.resultados[0], id: 'co-vencedor', fornecedor_nome: 'Outro fornecedor do item' })
    rows = rows.filter(r => r.descricao.toLowerCase().includes((url.searchParams.get('busca') || '').toLowerCase()))
    const filter = url.searchParams.get('analise') || 'todos'
    if (filter !== 'todos') rows = rows.filter(r => r.status_analise === filter)
    const context = { base_id: BASE, execucao_id: url.searchParams.get('execucao_id'), modelo_id: url.searchParams.get('modelo_id'), experimental: true, universo: {}, resumo: { itens: rows.length, processos: rows.length ? 1 : 0, orgaos: 1, fornecedores: 1, fornecedores_no_denominador: 1, contratos_vinculados: 0, resultados: 1, analisados: rows.filter(r => r.status_analise === 'analisados').length, parcial: 0, nao_analisados: rows.filter(r => r.status_analise === 'nao_analisados').length, valor_homologado: '0.10000001', soma_valores_conhecidos: '0.10000001', resultados_sem_total: 0 } }
    const pageOf = entries => {
      const size = Number(url.searchParams.get('tamanho_pagina') || 20), n = Number(url.searchParams.get('pagina') || 1)
      return { dados: entries.slice((n-1)*size,n*size), total: entries.length, pagina: n, tamanho_pagina: size, total_paginas: Math.ceil(entries.length/size) }
    }
    if (path === '/visao/painel') return done({ ...context, distribuicao: Array.from({ length: 10 }, (_,i) => ({ inicio: i/10, fim: (i+1)/10, itens: i === 8 ? context.resumo.analisados : 0 })), evolucao: rows.length ? [{ mes: '2026-09', itens: rows.length, analisados: context.resumo.analisados, parcial: 0, nao_analisados: context.resumo.nao_analisados }] : [], motivos_indisponibilidade: context.resumo.nao_analisados ? { SEM_REFERENCIA_EXATA: context.resumo.nao_analisados } : {} })
    if (path === '/visao/ranking') return done({ ...context, ...pageOf(rows) })
    if (path === '/visao/produtos') {
      const selected = url.searchParams.getAll('sinalizacao')
      const products = rows.map(r => {
        const review = !!state.extremePrice
        const signal = review ? 'requer_validacao' : r.medida_if == null ? 'sem_analise' : Number(r.medida_if) >= 0.70 ? 'maior_anomalia' : Number(r.medida_if) >= 0.50 ? 'anomalia_intermediaria' : 'menor_anomalia'
        return { id: r.id, descricao: r.descricao, catalogo: r.catalogo, codigo_catalogo: r.codigo_catalogo,
          unidade_medida: r.unidade_medida, preco_minimo: r.resultados[0]?.valor_unitario_homologado ?? null,
          preco_maximo: r.resultados[0]?.valor_unitario_homologado ?? null,
          mediana: state.extremePrice ? '0.01' : r.resultados[0]?.valor_unitario_homologado ?? null,
          quantidade_registros: r.resultados.length, requer_validacao: review, medida_if: r.medida_if,
          sinalizacao: signal, itens: [{ id: r.id, numero_item: r.numero_item, numero_compra: r.processo.numero_compra }],
        }
      }).filter(r => !selected.length || selected.includes(r.sinalizacao))
      return done({ ...context, ...pageOf(products) })
    }
    const supplier = { id: SUPPLIER, nome: 'Fornecedor do recorte', compras_com_resultado: 1, contratos_vinculados: 0, itens: 1, orgaos: 1, valor_homologado: '0.10000001', resultados_sem_total: 0, itens_com_medida_if: hasScore ? 1 : 0, requer_validacao: !!state.supplierReview, sinalizacao: state.supplierReview ? 'requer_validacao' : hasScore ? 'anomalia_intermediaria' : 'sem_analise', medida_if: hasScore ? '0.514' : null }
    if (path === '/visao/fornecedores') {
      const selected = url.searchParams.getAll('sinalizacao')
      const suppliers = (state.twoSuppliers ? [supplier, { ...supplier, id: OTHER_SUPPLIER, nome: 'Segundo fornecedor' }] : [supplier]).filter(r => r.nome.toLowerCase().includes((url.searchParams.get('busca') || '').toLowerCase()) && (!selected.length || selected.includes(r.sinalizacao)))
      return done({ ...context, ...pageOf(suppliers) })
    }
    const purchases = [{ id: PROCESS, orgao_id: 'org', orgao_nome: 'Órgão do recorte', numero_compra: '00001', itens: 1, resultados: 1, valor_homologado: '0.10000001', resultados_sem_total: 0 }]
    if (state.twoSuppliers && path === `/visao/fornecedores/${OTHER_SUPPLIER}`) return done({ ...context, fornecedor: { ...supplier, id: OTHER_SUPPLIER, nome: 'Segundo fornecedor' }, compras: purchases, relacoes: [], itens: pageOf(rows) })
    if (path === `/visao/fornecedores/${SUPPLIER}`) return done({ ...context, fornecedor: supplier, compras: purchases, relacoes: [{ orgao_id: 'org', orgao_nome: 'Órgão do recorte', compras_com_resultado: 1, valor_fornecedor: null, valor_homologado: null, participacao: null, hhi: null, motivo: 'TOTAIS_INCOMPLETOS' }], itens: pageOf(rows.slice(0,1)) })
    return bad('Fornecedor não encontrado neste recorte.', 404)
  } })
  return state
}

test('painel fixa versão/modelo, conserva filtros entre telas e distingue índices de risco', async ({ page }) => {
  const state = await mockView(page)
  const errors = []; page.on('pageerror', e => errors.push(e.message))
  await page.goto('/painel')
  await expect(page.getByRole('heading', { name: 'Painel geral' })).toBeVisible()
  await expect(page).toHaveURL(new RegExp(`execucao_id=${EXEC}`))
  await expect(page).toHaveURL(new RegExp(`modelo_id=${MODEL}`))
  await expect(page.getByRole('heading', { name: 'Itens para conferir' })).toBeVisible()
  await expect(page.locator('.dashboard-kpis').getByText('R$ 0,10', { exact: true })).toBeVisible()
  await page.locator('.dashboard-start').getByRole('link', { name: 'Ver análise', exact: true }).first().click()
  await expect(page.locator('.crumb')).toContainText('Detalhe do item')
  await expect(page.getByRole('link', { name: 'Itens Sinalizados', exact: true })).not.toHaveClass(/active/)
  await expect(page.getByRole('link', { name: 'Itens Sinalizados', exact: true })).not.toHaveAttribute('aria-current', 'page')
  await expect(page.getByRole('heading', { name: 'Compra 00001 · Item 00001' })).toBeVisible()
  await expect(page.locator('.detail-score-number')).toContainText('0,5140')
  await page.getByRole('link', { name: 'Itens Sinalizados', exact: true }).click()
  await page.getByLabel('Buscar item ou código de catálogo').fill('Borracha')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByRole('heading', { name: '1 produto' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('busca')).toBe('Borracha')
  state.active = NEW_EXEC
  await page.getByRole('link', { name: 'Borracha do recorte', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Compra 00001 · Item 00001' })).toBeVisible()
  await expect(page.locator('.detail-score-number')).toContainText('0,5140')
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe(EXEC)
  await page.getByRole('link', { name: 'Voltar à consulta' }).click()
  await expect(page.getByRole('heading', { name: '1 produto' })).toBeVisible()
  expect(errors).toEqual([])
})

test('ausência de scores e publicação não vira zero nem bloqueia consultas reais', async ({ page }) => {
  await mockView(page, { active: null, scored: false })
  await page.goto('/painel')
  await expect(page.getByText('Nenhum item analisado disponível neste recorte.')).toBeVisible()
  await expect(page).toHaveURL(/execucao_id=nenhuma/)
  await page.getByRole('link', { name: 'Itens Sinalizados', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2 produtos' })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Indisponível', exact: true })).toHaveCount(3)
  await page.locator('.signal-filter summary').click()
  await page.getByRole('checkbox', { name: 'Menor anomalia', exact: true }).check()
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByText('Nenhum item encontrado nesta página.')).toBeVisible()
})

test('fornecedor mostra compras e contratos separados e concentração desconhecida', async ({ page }) => {
  await mockView(page)
  await page.goto('/fornecedores')
  await page.getByRole('link', { name: 'Ver fornecedor Fornecedor do recorte', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Fornecedor do recorte', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Participação no gasto por órgão' })).toBeVisible()
  await expect(page.getByLabel('Fornecedor selecionado').getByText('Indisponível', { exact: true })).toBeVisible()
  await expect(page.getByText('HHI: Indisponível', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Fornecedor selecionado').getByText('compras com resultado', { exact: true })).toBeVisible()
})

test('seleção automática, paginação, erro e retentativa conservam a execução publicada', async ({ page }) => {
  const state = await mockView(page)
  await page.goto(`/ranking?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=${MODEL}&tamanho_pagina=1`)
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Próxima', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Caneta do recorte', exact: true })).toBeVisible()
  await expect(page.locator('.analysis-bar')).toHaveCount(0)
  state.viewOffline = true
  await page.getByLabel('Ordenação', { exact: true }).selectOption('descricao_asc')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByRole('heading', { name: 'Consulta indisponível' })).toBeVisible()
  state.viewOffline = false
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('heading', { name: '2 produtos' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('modelo_id')).toBeNull()
})

test('listagem ignora execução antiga e detalhe preserva validação de modelo explícito', async ({ page }) => {
  await mockView(page)
  await page.goto(`/ranking?base_id=${BASE}&execucao_id=00000000-0000-4000-8000-000000000000`)
  await expect(page.getByRole('heading', { name: '2 produtos' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe(EXEC)
  await expect(page.locator('.analysis-bar')).toHaveCount(0)
  await page.goto(`/itens/${ITEM}?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=00000000-0000-4000-8000-000000000000`)
  await expect(page.getByRole('heading', { name: 'Modelo fora da execução selecionada' })).toBeVisible()
  await expect(page.getByRole('cell', { name: '0,5140', exact: true })).toHaveCount(0)
})

test('painel real é utilizável em tela pequena e tema escuro', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.addInitScript(() => localStorage.setItem('lc_tema', 'dark'))
  await mockView(page, { scored: false })
  await page.goto('/painel')
  await expect(page.getByText('Nenhum item analisado disponível neste recorte.')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('painel-mobile.png'), fullPage: true })
})


test('modelo automático preserva roteamento por item e cobertura sem média entre grupos', async ({ page }) => {
  await mockView(page, { automatic: true })
  await page.goto(`/painel?base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Painel geral' })).toBeVisible()
  await expect(page.getByLabel('Modelo experimental')).toHaveCount(0)
  expect(new URL(page.url()).searchParams.get('modelo_id')).toBeNull()
  await page.getByRole('link', { name: 'Itens Sinalizados', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2 produtos' })).toBeVisible()
  await page.getByRole('link', { name: 'Borracha do recorte', exact: true }).click()
  await expect(page.locator('.detail-score-number')).toContainText('0,5140')
  expect(new URL(page.url()).searchParams.get('modelo_id')).toBeNull()
  await page.goto(`/processos/${PROCESS}?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.getByText('Itens com análise / importados', { exact: true })).toBeVisible()
  await expect(page.getByText('O universo oficial completo ainda não está confirmado.', { exact: false })).toBeVisible()
  await expect(page.getByText('Média dos sinais disponíveis', { exact: true })).toHaveCount(0)
})


test('painel compara preços na unidade do grupo sem expor medida técnica', async ({ page }) => {
  await page.setViewportSize({ width: 1062, height: 880 })
  await mockView(page, { bothModels: true })
  await page.goto('/painel')
  await expect(page.getByRole('heading', { name: 'Painel geral', exact: true })).toBeVisible()
  await expect(page.locator('.dashboard-kpis .kpi')).toHaveCount(4)
  const positions = await page.locator('.dashboard-kpis .kpi').evaluateAll(cards => cards.map(card => card.getBoundingClientRect().top))
  expect(new Set(positions).size).toBe(1)
  await expect(page.getByRole('form', { name: 'Filtros do recorte' })).toHaveCount(0)
  await expect(page.getByText('Filtros e versão da análise', { exact: true })).toHaveCount(0)
  await expect(page.locator('.dashboard-period')).toContainText('2026')
  const analysisLink = page.locator('.dashboard-start').getByRole('link', { name: 'Ver análise', exact: true }).first()
  await expect(analysisLink).toHaveAttribute('title', 'Ver análise')
  await expect(analysisLink).toHaveAttribute('href', new RegExp(`/ranking/${ITEM}\\?`))
  await expect(page.getByRole('heading', { name: 'Itens para conferir' })).toBeVisible()
  const reading = page.locator('.dashboard-reading')
  await expect(reading).toContainText('100,00% acima')
  await expect(reading).toContainText('Fornecedor do recorte')
  await expect(reading).toContainText('preços por UN')
  await expect(page.locator('.dashboard')).not.toContainText('0,5140')
  await expect(page.locator('.dashboard')).not.toContainText('Isolation Forest')
  await expect(page.getByText('Alta prioridade', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Em revisão humana', { exact: true })).toHaveCount(0)
  await page.goto('/painel?busca=nenhum-item')
  await expect(page.getByText('Nenhum item analisado disponível neste recorte.')).toBeVisible()
  await expect(page.locator('.dashboard-reading .dashboard-model')).toHaveCount(0)
})


test('comparação não mistura resultados de fornecedores diferentes', async ({ page }) => {
  await mockView(page, { bothModels: true, separateResults: true })
  await page.goto('/painel')
  const reading = page.locator('.dashboard-reading')
  await expect(reading.getByLabel('Resultado do fornecedor')).toHaveCount(0)
  await expect(reading).toContainText('Fornecedor do recorte')
  await expect(reading).not.toContainText('Outro fornecedor do item')
  await expect(reading).toContainText('100,00% acima')
  await expect(reading).not.toContainText('Autoencoder')
})

test('detalhe sinalizado separa resultado, referência de treino e explicação dos modelos', async ({ page }, testInfo) => {
  const errors = []; page.on('pageerror', e => errors.push(e.message))
  const state = await mockView(page, { automatic: true })
  await page.route(`**/analises/execucoes/${EXEC}/itens/${ITEM}*`, route => route.fulfill({ json: { dados: [{ cobertura: [], resultados: [
    { id: 'score-if', modelo_id: MODEL, resultado_item_id: item.resultados[0].id, algoritmo: 'isolation_forest', medida_if: '0.514', score_bruto: '0.514', atributos: { comparacao: { mediana: '0.05', n_treino: 100, grupo: 'CATMAT-123', unidade_preco: { unidade_preco: 'kg' } } }, explicacao: { status: 'indisponivel', parcelas: [] } },
    { id: 'score-ae', modelo_id: AE, resultado_item_id: item.resultados[0].id, algoritmo: 'autoencoder', medida_if: null, erro_reconstrucao: '0.4', score_bruto: '0.4', atributos: { comparacao: { mediana: '0.05', n_treino: 100, grupo: 'CATMAT-123', unidade_preco: { unidade_preco: 'kg' } } }, explicacao: { status: 'disponivel', parcelas: [{ atributo: 'log_quantidade', parcela_score_bruto: '0.3' }, { atributo: 'log_preco_mediana', parcela_score_bruto: '0.1' }] } },
  ] }] } }))
  await page.goto(`/ranking/${ITEM}?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.getByRole('heading', { name: 'Compra 00001 · Item 00001' })).toBeVisible()
  await expect(page.locator('.detail-score-number')).toContainText('0,5140')
  await expect(page.getByText('100 observações no treino', { exact: false })).toBeVisible()
  await expect(page.getByText('Unidade da mediana: kg', { exact: true })).toBeVisible()
  await expect(page.getByText('Unidade registrada no item: UN', { exact: false })).toBeVisible()
  await expect(page.getByText('Contribuição por atributo indisponível para este modelo.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Modelo da comparação')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Parcelas do erro de reconstrução' })).toHaveCount(0)
  await expect(page.locator('.detail-score-number')).not.toContainText('/ 100')
  await page.getByRole('button', { name: 'Documentos', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Edital da compra', exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Revisão', exact: true }).click()
  await expect(page.getByText('Nenhuma revisão humana registrada.', { exact: false })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Incluir no relatório', exact: true })).toHaveAttribute('href', new RegExp(`processo_id=${PROCESS}`))
  await page.getByRole('button', { name: 'Preço e sinais', exact: true }).click()
  const { default: AxeBuilder } = await import('@axe-core/playwright')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.screenshot({ path: testInfo.outputPath('detalhe-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('detalhe-mobile.png'), fullPage: true })
  expect(errors).toEqual([])
})

test('detalhe sinalizado sem score não inventa zero nem usa resultado cancelado', async ({ page }) => {
  await mockView(page, { scored: false })
  await page.goto(`/ranking/${ITEM}?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=${MODEL}`)
  await expect(page.locator('.detail-score-number')).toContainText('—')
  await expect(page.getByText('Nenhuma medida IF disponível para este resultado no modelo selecionado.', { exact: false })).toBeVisible()
  await expect(page.getByText('Referência de treino indisponível para este resultado.')).toBeVisible()
  await expect(page.getByLabel('Resultado do fornecedor')).toHaveCount(0)
  await page.goto(`/ranking/00000000-0000-4000-8000-000000000000?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.getByRole('heading', { name: 'Registro não encontrado' })).toBeVisible()
})

test('detalhe mantém scores de fornecedores separados e respeita modelo fixado', async ({ page }) => {
  await mockView(page, { automatic: true, bothModels: true, separateResults: true })
  await page.route(`**/api/v1/itens/${ITEM}?*`, route => route.fulfill({ json: { base_id: BASE, item: { ...item, resultados: [...item.resultados, { ...item.resultados[0], id: 'co-vencedor', fornecedor_nome: 'Outro fornecedor', sequencial_resultado: 3 }] } } }))
  await page.goto(`/ranking/${ITEM}?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=${MODEL}`)
  await expect(page.locator('.detail-score-number')).toContainText('0,5140')
  await page.getByLabel('Resultado do fornecedor').selectOption('co-vencedor')
  await expect(page.locator('.detail-score-number')).toContainText('—')
  await expect(page.locator('.detail-score')).not.toContainText('0,5140')
  await expect(page.getByLabel('Modelo da comparação')).toHaveCount(0)
  expect(new URL(page.url()).searchParams.get('modelo_id')).toBe(MODEL)
  await expect(page.locator('.detail-score-number')).toContainText('—')
})

test('detalhe automático conserva preferência do grupo e escolhe maior resultado desse modelo', async ({ page }) => {
  await mockView(page, { automatic: true })
  await page.route(`**/api/v1/analises/execucoes/${EXEC}?*`, route => route.fulfill({ json: { id: EXEC, roteamento_automatico: true, modelos: [{ id: MODEL, algoritmo: 'isolation_forest', grupo: 'grupo-1' }, { id: AE, algoritmo: 'autoencoder', grupo: 'grupo-1' }] } }))
  await page.route(`**/api/v1/itens/${ITEM}?*`, route => route.fulfill({ json: { item: { ...item, resultados: [...item.resultados, { ...item.resultados[0], id: 'segundo-ativo', fornecedor_nome: 'Fornecedor maior score IF', sequencial_resultado: 3 }] } } }))
  await page.route(`**/analises/execucoes/${EXEC}/itens/${ITEM}*`, route => route.fulfill({ json: { dados: [{ cobertura: [], resultados: [
    { id: 'if-1', modelo_id: MODEL, resultado_item_id: item.resultados[0].id, algoritmo: 'isolation_forest', medida_if: '0.4' },
    { id: 'ae-1', modelo_id: AE, resultado_item_id: item.resultados[0].id, algoritmo: 'autoencoder', medida_if: null, erro_reconstrucao: '99' },
    { id: 'if-2', modelo_id: MODEL, resultado_item_id: 'segundo-ativo', algoritmo: 'isolation_forest', medida_if: '0.88' },
  ] }] } }))
  await page.goto(`/ranking/${ITEM}?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.locator('.detail-score-number')).toHaveText('0,8800')
  await expect(page.locator('.score-ruler i')).toHaveAttribute('style', /width: 88%/)
  await expect(page.locator('.score-scale')).toHaveText('01')
  await expect(page.getByLabel('Resultado do fornecedor')).toHaveValue('segundo-ativo')
  await expect(page.locator('.detail-score')).not.toContainText('99')
})

test('itens remove Mais filtros e descarta filtros antigos da URL e da consulta', async ({ page }) => {
  const state = await mockView(page)
  await page.goto(`/ranking?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=${MODEL}&orgao_id=antigo&fornecedor_id=antigo&modalidade_id=antigo&homologacao_inicio=2026-09-01&homologacao_fim=2026-09-30&valor_minimo=2&valor_maximo=10&pagina=2`)
  await expect(page.getByRole('heading', { name: 'Filtrar itens' })).toBeVisible()
  await expect(page.getByText('Mais filtros', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Órgão', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Registros por página', { exact: true })).toHaveCount(0)
  const removed = ['orgao_id', 'fornecedor_id', 'modalidade_id', 'homologacao_inicio', 'homologacao_fim', 'valor_minimo', 'valor_maximo']
  await expect.poll(() => removed.some(key => new URL(page.url()).searchParams.has(key))).toBe(false)
  await page.getByLabel('Buscar item ou código de catálogo').fill('Borracha')
  await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
  await expect(page.getByRole('heading', { name: '1 produto', exact: true })).toBeVisible()
  const calls = state.calls.filter(url => url.pathname.endsWith('/visao/produtos'))
  expect(calls.length).toBeGreaterThan(0)
  expect(calls.every(url => removed.every(key => !url.searchParams.has(key)))).toBe(true)
  await page.getByRole('button', { name: 'Limpar filtros', exact: true }).click()
  await expect(page.getByLabel('Buscar item ou código de catálogo')).toHaveValue('')
  await expect(page.getByRole('heading', { name: '2 produtos', exact: true })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe(EXEC)
})

test('filtros básicos dos produtos funcionam no celular sem opções avançadas', async ({ page }) => {
  await mockView(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`/ranking?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=${MODEL}`)
  await expect(page.getByText('Mais filtros', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Buscar item ou código de catálogo')).toBeVisible()
  await expect(page.getByRole('group', { name: 'Sinalização do item', exact: true })).toBeVisible()
  await page.getByLabel('Ordenação', { exact: true }).selectOption('descricao_asc')
  await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
  expect(new URL(page.url()).searchParams.get('ordenacao')).toBe('descricao_asc')
  await page.getByRole('button', { name: 'Ativar modo escuro', exact: true }).click()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})


test('fornecedores usa lista simplificada e abre resumo e relações pela lupa', async ({ page }, testInfo) => {
  await mockView(page)
  await page.goto(`/fornecedores?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=${MODEL}`)
  await expect(page.getByRole('heading', { name: 'Fornecedores', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '1 fornecedor', exact: true })).toBeVisible()
  await expect(page.locator('.analysis-bar')).toHaveCount(0)
  await expect(page.locator('.kpis')).toHaveCount(0)
  await expect(page.getByText('Mais filtros', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('columnheader', { name: 'Maior medida IF', exact: true })).toHaveCount(0)
  await expect(page.getByRole('row').filter({ has: page.getByRole('button', { name: 'Fornecedor do recorte', exact: true }) })).toHaveAttribute('data-if-band', 'yellow')
  await page.getByRole('link', { name: 'Ver fornecedor Fornecedor do recorte', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Fornecedor do recorte', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Itens relacionados a Fornecedor do recorte' })).toBeVisible()
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()).violations).toEqual([])
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('fornecedores-mobile.png'), fullPage: true })
})


test('paginação dos itens do fornecedor mantém retorno à página da lista', async ({ page }) => {
  await mockView(page, { twoSuppliers: true })
  await page.goto(`/fornecedores?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=${MODEL}&tamanho_pagina=1`)
  const ranking = page.locator('.supplier-ranking')
  await expect(ranking.getByRole('button', { name: 'Fornecedor do recorte', exact: true })).toBeVisible()
  await ranking.getByRole('button', { name: 'Próxima', exact: true }).click()
  await ranking.getByRole('link', { name: 'Ver fornecedor Segundo fornecedor', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Segundo fornecedor', exact: true })).toBeVisible()
  await expect(page.getByText('Sem relações disponíveis neste recorte.')).toBeVisible()
  const related = page.locator('.supplier-related')
  await related.getByRole('button', { name: 'Próxima', exact: true }).click()
  await expect(page).toHaveURL(/pagina_itens=2/)
  await expect(related.getByRole('link', { name: 'Caneta do recorte', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Voltar aos fornecedores', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Fornecedores', exact: true })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('pagina')).toBe('2')
  expect(new URL(page.url()).searchParams.has('pagina_itens')).toBe(false)
  await page.getByRole('button', { name: 'Limpar filtros', exact: true }).click()
  expect(new URL(page.url()).searchParams.has('pagina')).toBe(false)
})

 test('painel não inventa comparação sem mediana válida', async ({ page }) => {
  await mockView(page, { noReference: true })
  await page.goto('/painel')
  await expect(page.locator('.dashboard-reading')).toContainText('Comparação de preço indisponível')
  await expect(page.locator('.dashboard-start')).toContainText('Sem referência')
  await expect(page.locator('.dashboard-reading')).not.toContainText('% acima')
})

 test('preço extremo recebe aviso no painel e ranking sem excluir o item', async ({ page }) => {
  await mockView(page, { extremePrice: true })
  await page.goto('/painel')
  const reading = page.locator('.dashboard-reading')
  await expect(reading).toContainText('Requer validação')
  await expect(reading).not.toContainText('Possível erro de digitação ou cadastro')
  await expect(page.locator('.dashboard-start')).toContainText('Requer validação')
  await expect(reading.getByText('900,00% acima', { exact: true })).not.toBeVisible()
  await reading.getByText('Ver diferença registrada', { exact: true }).click()
  await expect(reading.getByText('900,00% acima', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Itens Sinalizados', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2 produtos' })).toBeVisible()
  await expect(page.locator('tbody')).toContainText('Requer validação')
})

 test('painel simplifica textos e atualiza o quadro por clique na linha ou teclado', async ({ page }) => {
  await mockView(page, { twoScored: true })
  await page.goto('/painel')
  await expect(page.locator('.chips')).not.toContainText('Dados oficiais')
  await expect(page.getByText('Todos os dados foram retirados da base Compras.gov.br', { exact: true })).toBeVisible()
  await expect(page.getByText('Requer validação: possível erro de digitação ou de cadastro pelo Compras.gov.br', { exact: true })).toBeVisible()
  const reading = page.locator('.dashboard-reading')
  await expect(reading.getByRole('heading', { name: 'Borracha do recorte' })).toBeVisible()
  await page.locator('.dashboard-start').getByText('Caneta do recorte', { exact: true }).click()
  await expect(reading.getByRole('heading', { name: 'Caneta do recorte' })).toBeVisible()
  await expect(reading).toContainText('Fornecedor da caneta')
  await expect(reading).toContainText('R$ 2,00')
  const first = page.getByRole('button', { name: 'Compra 00001 · item 00001', exact: true })
  await first.focus()
  await page.keyboard.press('Enter')
  await expect(first).toHaveAttribute('aria-pressed', 'true')
  await expect(reading.getByRole('heading', { name: 'Borracha do recorte' })).toBeVisible()
  await expect(reading).not.toContainText('Fornecedor da caneta')
})

 test('itens sinalizados mostra menor preço, maior preço e mediana sem órgão ou fornecedor', async ({ page }) => {
  await mockView(page)
  await page.goto('/ranking')
  for (const name of ['Menor valor unitário', 'Maior valor unitário', 'Mediana da base atual']) await expect(page.getByRole('columnheader', { name, exact: true })).toBeVisible()
  for (const name of ['Medida IF', 'Órgão / fornecedor', 'Total do item']) await expect(page.getByRole('columnheader', { name, exact: true })).toHaveCount(0)
  const row = page.getByRole('row').filter({ has: page.getByRole('link', { name: 'Borracha do recorte', exact: true }) })
  await expect(row.locator('[data-label="Mediana da base atual"]')).toContainText('R$ 0,10')
  await expect(row).not.toContainText('Fornecedor do recorte')
})

 test('produto agrupa compras e mantém acesso às análises de cada ocorrência', async ({ page }) => {
  await mockView(page)
  await page.route('**/api/v1/visao/produtos?*', route => route.fulfill({ json: {
    dados: [{ id: 'agua-copo', descricao: 'Água mineral sem gás', catalogo: 'CATMAT', codigo_catalogo: '445484', unidade_medida: 'Copo 200 ML', preco_minimo: '0.60', preco_maximo: '30185.20', mediana: '0.80', quantidade_registros: 4, requer_validacao: true, itens: [{ id: ITEM, numero_item: '1', numero_compra: '5' }, { id: 'outra-compra', numero_item: '2', numero_compra: '10' }] }],
    total: 1, pagina: 1, tamanho_pagina: 20, total_paginas: 1,
  } }))
  await page.goto('/ranking')
  await expect(page.locator('tbody tr')).toHaveCount(1)
  await expect(page.getByRole('cell', { name: 'R$ 0,60', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'R$ 30.185,20', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'R$ 0,80', exact: true })).toBeVisible()
  await expect(page.locator('tbody')).toContainText('Requer validação')
  await page.locator('.product-purchases summary').click()
  await expect(page.getByRole('link', { name: 'Compra 5 · item 1', exact: true })).toHaveAttribute('href', new RegExp(`/ranking/${ITEM}`))
  await expect(page.getByRole('link', { name: 'Compra 10 · item 2', exact: true })).toBeVisible()
})

for (const theme of ['light', 'dark']) for (const width of [1280, 390]) {
  test(`faixas IF preservam revisão neutra e contraste ${theme} ${width}`, async ({ page }) => {
    await mockView(page)
    const samples = [
      ['verde', '0.499999999999', false, 'green'],
      ['amarelo', '0.50', false, 'yellow'],
      ['limite amarelo', '0.699999999999', false, 'yellow'],
      ['vermelho', '0.70', false, 'red'],
      ['revisar', '0.90', true, null],
      ['sem análise', null, false, null],
    ]
    await page.route('**/api/v1/visao/produtos?*', route => route.fulfill({ json: {
      dados: samples.map(([name, measure, review]) => ({ id: name, descricao: `Produto ${name}`, catalogo: 'CATMAT', codigo_catalogo: '123', unidade_medida: 'UN', preco_minimo: '10', preco_maximo: '20', mediana: '15', quantidade_registros: 3, medida_if: measure, requer_validacao: review, itens: [{ id: ITEM, numero_compra: '1', numero_item: '1' }] })),
      total: 6, pagina: 1, tamanho_pagina: 20, total_paginas: 1,
    } }))
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/ranking')
    await expect(page.locator('tbody tr')).toHaveCount(6)
    await page.evaluate(value => { document.documentElement.dataset.theme = value }, theme)
    const backgrounds = {}
    for (const [name, , , band] of samples) {
      const row = page.getByRole('row').filter({ has: page.getByRole('link', { name: `Produto ${name}`, exact: true }) })
      if (band) {
        await expect(row).toHaveAttribute('data-if-band', band)
        backgrounds[band] = await row.evaluate(el => getComputedStyle(el).backgroundColor)
        expect(backgrounds[band]).not.toBe('rgba(0, 0, 0, 0)')
      } else await expect(row).not.toHaveAttribute('data-if-band')
    }
    expect(new Set(Object.values(backgrounds)).size).toBe(3)
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    expect(axe.violations).toEqual([])
    await expect(page.getByRole('columnheader', { name: 'Medida IF', exact: true })).toHaveCount(0)
  })
}

for (const width of [1280, 390]) {
  test(`sinalização permite múltipla seleção, restauração e limpeza ${width}`, async ({ page }) => {
    const state = await mockView(page)
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/ranking')
    await expect(page.getByLabel('Estado da análise', { exact: true })).toHaveCount(0)
    const group = page.getByRole('group', { name: 'Sinalização do item', exact: true })
    await group.locator('summary').click()
    await expect(group.getByRole('checkbox')).toHaveCount(5)
    await expect(group.getByRole('checkbox', { name: 'Todos os itens', exact: true })).toHaveCount(0)
    await page.getByRole('checkbox', { name: 'Menor anomalia', exact: true }).check()
    await page.getByRole('checkbox', { name: 'Maior anomalia', exact: true }).check()
    await expect(page.getByRole('checkbox', { name: 'Menor anomalia', exact: true })).toBeChecked()
    await expect(page.getByRole('checkbox', { name: 'Maior anomalia', exact: true })).toBeChecked()
    expect(new URL(page.url()).searchParams.getAll('sinalizacao')).toEqual([])
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()
    expect(axe.violations).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
    await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
    await expect.poll(() => new URL(page.url()).searchParams.getAll('sinalizacao')).toEqual(['menor_anomalia', 'maior_anomalia'])
    await expect(page.getByText('Nenhum item encontrado nesta página.', { exact: true })).toBeVisible()
    expect(state.calls.filter(u => u.pathname.endsWith('/visao/produtos')).at(-1).searchParams.getAll('sinalizacao')).toEqual(['menor_anomalia', 'maior_anomalia'])
    await page.reload()
    await group.locator('summary').click()
    await expect(page.getByRole('checkbox', { name: 'Menor anomalia', exact: true })).toBeChecked()
    await expect(page.getByRole('checkbox', { name: 'Maior anomalia', exact: true })).toBeChecked()
    await page.getByRole('checkbox', { name: 'Menor anomalia', exact: true }).uncheck()
    await page.getByRole('checkbox', { name: 'Maior anomalia', exact: true }).uncheck()
    await expect(page.getByRole('checkbox', { name: 'Menor anomalia', exact: true })).not.toBeChecked()
    await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
    await expect(page.getByRole('heading', { name: '2 produtos', exact: true })).toBeVisible()
    expect(new URL(page.url()).searchParams.getAll('sinalizacao')).toEqual([])
    await group.locator('summary').click()
    await page.getByRole('checkbox', { name: 'Sem análise disponível', exact: true }).check()
    await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
    await expect(page.getByRole('heading', { name: '1 produto', exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Limpar filtros', exact: true }).click()
    await expect(page.getByRole('heading', { name: '2 produtos', exact: true })).toBeVisible()
  })
}

test('itens escolhe publicação ativa e modelo automático mesmo com seleção antiga na URL', async ({ page }) => {
  const state = await mockView(page)
  await page.goto(`/ranking/?base_id=${BASE}&execucao_id=${NEW_EXEC}&modelo_id=${AE}&busca=Borracha&sinalizacao=anomalia_intermediaria&sinalizacao=sem_analise`)
  await expect(page.getByRole('heading', { name: '1 produto', exact: true })).toBeVisible()
  const params = new URL(page.url()).searchParams
  expect(params.get('execucao_id')).toBe(EXEC)
  expect(params.has('modelo_id')).toBe(false)
  expect(params.getAll('sinalizacao')).toEqual(['anomalia_intermediaria', 'sem_analise'])
  expect(params.get('busca')).toBe('Borracha')
  await expect(page.getByLabel('Execução publicada')).toHaveCount(0)
  await expect(page.getByLabel('Modelo experimental')).toHaveCount(0)
  expect(state.calls.filter(u => u.pathname.endsWith('/analises/execucoes'))).toHaveLength(0)
  const calls = state.calls.filter(u => u.pathname.endsWith('/visao/produtos'))
  expect(calls.length).toBeGreaterThan(0)
  expect(calls.every(u => u.searchParams.get('execucao_id') === EXEC && !u.searchParams.has('modelo_id'))).toBe(true)
  state.active = NEW_EXEC
  await page.reload()
  await expect(page.getByRole('heading', { name: '1 produto', exact: true })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe(NEW_EXEC)
  expect(new URL(page.url()).searchParams.has('modelo_id')).toBe(false)
})

test('sem publicação a seleção automática mantém dados e não inventa análise', async ({ page }) => {
  const state = await mockView(page, { active: null, scored: false })
  await page.goto(`/ranking?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=${MODEL}`)
  await expect(page.getByRole('heading', { name: '2 produtos', exact: true })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe('nenhuma')
  await expect(page.locator('.analysis-bar')).toHaveCount(0)
  await expect(page.locator('[data-if-band]')).toHaveCount(0)
  expect(state.calls.some(u => u.pathname.endsWith(`/analises/execucoes/${EXEC}`))).toBe(false)
})

test('falha na publicação oferece retentativa sem seletor manual ou uso da versão antiga', async ({ page }) => {
  const state = await mockView(page, { publicationOffline: true })
  await page.goto(`/ranking?base_id=${BASE}&execucao_id=${NEW_EXEC}`)
  await expect(page.getByRole('heading', { name: 'Consulta indisponível', exact: true })).toBeVisible()
  await expect(page.locator('.analysis-bar')).toHaveCount(0)
  expect(state.calls.some(u => u.pathname.endsWith('/visao/produtos'))).toBe(false)
  state.publicationOffline = false
  await page.getByRole('button', { name: 'Tentar novamente', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2 produtos', exact: true })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe(EXEC)
})

for (const width of [1280, 390]) {
  test(`fornecedores filtram sinalizações, mantêm automação e revisão neutra ${width}`, async ({ page }) => {
    const state = await mockView(page)
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/fornecedores?base_id=${BASE}&execucao_id=${NEW_EXEC}&modelo_id=${AE}&orgao_id=antigo`)
    await expect(page.getByRole('heading', { name: '1 fornecedor', exact: true })).toBeVisible()
    const params = new URL(page.url()).searchParams
    expect(params.get('execucao_id')).toBe(EXEC)
    expect(params.has('modelo_id')).toBe(false)
    expect(params.has('orgao_id')).toBe(false)
    await expect(page.getByLabel('Execução publicada')).toHaveCount(0)
    await page.getByLabel('Buscar fornecedor', { exact: true }).fill('Fornecedor do recorte')
    const group = page.getByRole('group', { name: 'Sinalização do fornecedor', exact: true })
    await group.locator('summary').click()
    await expect(group.getByRole('checkbox')).toHaveCount(5)
    await page.getByRole('checkbox', { name: 'Anomalia intermediária', exact: true }).check()
    await page.getByRole('checkbox', { name: 'Requer validação', exact: true }).check()
    await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
    await expect(page.getByRole('heading', { name: '1 fornecedor', exact: true })).toBeVisible()
    expect(new URL(page.url()).searchParams.getAll('sinalizacao')).toEqual(['anomalia_intermediaria', 'requer_validacao'])
    await expect(page.locator('td[data-label="Itens analisados"]')).toHaveText('1 de 1 analisado')
    state.supplierReview = true
    await page.reload()
    const row = page.getByRole('row').filter({ has: page.getByRole('button', { name: 'Fornecedor do recorte', exact: true }) })
    await expect(row).toContainText('Requer validação')
    await expect(row).not.toHaveAttribute('data-if-band')
    await group.locator('summary').click()
    await expect(page.getByRole('checkbox', { name: 'Anomalia intermediária', exact: true })).toBeChecked()
    await expect(page.getByRole('checkbox', { name: 'Requer validação', exact: true })).toBeChecked()
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()
    expect(axe.violations).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
    await page.getByRole('button', { name: 'Limpar filtros', exact: true }).click()
    await expect(page.getByLabel('Buscar fornecedor', { exact: true })).toHaveValue('')
    expect(new URL(page.url()).searchParams.getAll('sinalizacao')).toEqual([])
  })
}

for (const width of [1280, 390]) {
  test(`nome do fornecedor expande compras com animação, retentativa e sem IF ${width}`, async ({ page }) => {
    await mockView(page)
    await page.setViewportSize({ width, height: 900 })
    const purchases = [
      { id: 'purchase-1', orgao_nome: 'CONSELHO DA ESCOLA DE 1 E 2 GRAUS MARIO DE OLIVEIRA CHA', numero_compra: '3', itens: 2, valor_homologado: '7818.10', resultados_sem_total: 0 },
      { id: 'purchase-2', orgao_nome: 'Outro conselho escolar', numero_compra: '4', itens: 1, valor_homologado: null, resultados_sem_total: 1 },
    ]
    let calls = 0, fail = true
    await page.route(`**/api/v1/visao/fornecedores/${SUPPLIER}?*`, route => {
      calls += 1
      return route.fulfill(fail ? { status: 503, json: { erro: { mensagem: 'Compras indisponíveis.', codigo: 'temporario' } } } : { json: { compras: purchases } })
    })
    await page.goto('/fornecedores')
    await expect(page.getByRole('heading', { name: '1 fornecedor', exact: true })).toBeVisible()
    const originalUrl = page.url()
    const button = page.getByRole('button', { name: 'Fornecedor do recorte', exact: true })
    expect(calls).toBe(0)
    await expect(button).toHaveAttribute('aria-expanded', 'false')
    await button.focus()
    await page.keyboard.press('Enter')
    await expect(button).toHaveAttribute('aria-expanded', 'true')
    const panel = page.getByRole('region', { name: 'Licitações de Fornecedor do recorte', exact: true })
    await expect(panel.getByRole('heading', { name: 'Consulta indisponível', exact: true })).toBeVisible()
    fail = false
    await panel.getByRole('button', { name: 'Tentar novamente', exact: true }).click()
    await expect(panel.getByText(purchases[0].orgao_nome, { exact: true })).toBeVisible()
    await expect(panel.getByText('R$ 7.818,10', { exact: true })).toBeVisible()
    await expect(panel.getByText('Total incompleto na fonte', { exact: true })).toBeVisible()
    await expect(panel.getByText('Não informado', { exact: true })).toBeVisible()
    await expect(panel.getByText(/Medida IF|Isolation Forest|Score/)).toHaveCount(0)
    expect(page.url()).toBe(originalUrl)
    expect(calls).toBe(2)
    expect((await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
    await button.click()
    await expect(button).toHaveAttribute('aria-expanded', 'false')
    const grid = page.locator('.supplier-expansion-grid').first()
    await expect.poll(() => grid.evaluate(el => el.getBoundingClientRect().height)).toBe(0)
    await expect(grid).toHaveAttribute('inert', '')
    await button.click()
    await expect(panel.getByText('R$ 7.818,10', { exact: true })).toBeVisible()
    expect(calls).toBe(2)
  })
}

for (const entry of ['/', '/itens', '/processos']) test(`entrada ${entry} usa somente Itens Sinalizados`, async ({ page }) => {
  const state = await mockView(page)
  await page.goto(`${entry}?base_id=${BASE}&busca=Borracha`)
  await expect(page.getByRole('heading', { name: 'Itens Sinalizados', exact: true })).toBeVisible()
  await expect(page).toHaveURL(/\/ranking\?/)
  expect(new URL(page.url()).searchParams.get('base_id')).toBe(BASE)
  expect(new URL(page.url()).searchParams.get('busca')).toBe('Borracha')
  await expect(page.getByText('Consultar itens', { exact: true })).toHaveCount(0)
  expect(state.calls.some(url => url.pathname === '/api/v1/itens')).toBe(false)
})

test('compra e endereço antigo abrem detalhe único e retornam aos itens sinalizados', async ({ page }) => {
  const state = await mockView(page)
  await page.goto(`/processos/${PROCESS}?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.getByRole('link', { name: '← Itens Sinalizados' })).toHaveAttribute('href', /\/ranking\?/)
  await page.getByRole('link', { name: 'Item 00001 · Borracha do recorte', exact: true }).click()
  await expect(page).toHaveURL(new RegExp(`/ranking/${ITEM}\\?`))
  await expect(page.getByRole('heading', { name: 'Compra 00001 · Item 00001' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Gerar relatório da licitação' })).toBeVisible()
  expect(state.calls.some(url => url.pathname.endsWith('/documentos'))).toBe(false)
  await page.goto(`/itens/${ITEM}?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page).toHaveURL(new RegExp(`/ranking/${ITEM}\\?`))
  await page.getByRole('link', { name: 'Voltar à consulta' }).click()
  await expect(page.getByRole('heading', { name: 'Itens Sinalizados', exact: true })).toBeVisible()
})
