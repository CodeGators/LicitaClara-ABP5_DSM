import { test, expect } from '@playwright/test'
import { BASE, ITEM, PROCESS, SUPPLIER, item, otherItem, mockApi } from './fixtures.js'

const EXEC = '77777777-7777-4777-8777-777777777777'
const NEW_EXEC = '77777777-7777-4777-8777-888888888888'
const MODEL = '88888888-8888-4888-8888-888888888888'
const AE = '88888888-8888-4888-8888-999999999999'

async function mockView(page, overrides = {}) {
  const state = await mockApi(page, { active: EXEC, scored: true, ...overrides, handler: async ({ url, path, send, error }) => {
    const done = async body => { await send(body); return true }
    const bad = async (message, status) => { await error(message, status); return true }
    if (path === '/analises/publicacao') return done({ base_id: BASE, execucao_id: state.active, status: state.active ? 'publicada_experimental' : 'nao_publicada', experimental: true })
    const run = id => ({ id, roteamento_automatico: !!state.automatic, base_id: BASE, concluido_em: '2026-11-03T15:00:00Z', modelos: [{ id: MODEL, algoritmo: 'isolation_forest' }, { id: AE, algoritmo: 'autoencoder' }] })
    if (path === '/analises/execucoes') return done({ dados: [run(EXEC), run(NEW_EXEC)], total: 2, total_paginas: 1 })
    if (path === `/analises/execucoes/${EXEC}` || path === `/analises/execucoes/${NEW_EXEC}`) return done(run(path.split('/').at(-1)))
    if (state.bothModels && path.includes(`/itens/${ITEM}`) && path.startsWith('/analises/')) return done({ dados: [{ cobertura: [], resultados: [
      { id: 'score-if', modelo_id: MODEL, resultado_item_id: item.resultados[0].id, algoritmo: 'isolation_forest', indice_experimental: '88.125' },
      { id: 'score-ae', modelo_id: AE, resultado_item_id: state.separateResults ? 'co-vencedor' : item.resultados[0].id, algoritmo: 'autoencoder', indice_experimental: '77.800' },
    ] }] })
    if (state.automatic && path.startsWith('/analises/') && path.includes('/processos/')) return done({ dados: [{ id: PROCESS, status: 'disponivel', resultados: [], cobertura_agrupada: { itens_importados: 2, itens_com_analise: 1, resultados_ativos_importados: 2, resultados_com_analise: 1, quantidade_grupos: 1, itens_oficiais: null, score_processo: null } }] })
    if (path.startsWith('/analises/execucoes/') && !path.includes('/itens/')) return bad('Execução não publicada nesta base.', 404)
    if (path.includes(`/itens/${ITEM}`) && path.startsWith('/analises/')) return done({ dados: [{ cobertura: [{ modelo_id: MODEL, motivo: state.scored ? null : 'SEM_REFERENCIA_EXATA' }], resultados: state.scored ? [{ id: 'score-1', modelo_id: MODEL, resultado_item_id: item.resultados[0].id, algoritmo: 'isolation_forest', score_bruto: '0.514', indice_experimental: '88.125', explicacao: { status: 'indisponivel', parcelas: [] } }] : [] }] })
    if (!path.startsWith('/visao/')) return false
    if (state.viewOffline) return bad('Consulta do recorte indisponível.', 503)
    if (url.searchParams.get('modelo_id') === 'invalido') return bad('Modelo não pertence à execução selecionada.', 422)
    const hasScore = state.scored && url.searchParams.get('execucao_id') && (state.automatic || url.searchParams.get('modelo_id'))
    let rows = [item, otherItem].map((r, i) => ({ ...r, resultados: r.resultados.filter(e => !e.cancelado), valor_homologado: r.valor_homologado_item, soma_valores_conhecidos: r.valor_homologado_item, resultados_sem_total: 0, resultados_analisados: i === 0 && hasScore ? 1 : 0, status_analise: i === 0 && hasScore ? 'analisados' : 'nao_analisados', indice_experimental: i === 0 && hasScore ? '88.125' : null, motivos: i === 0 && hasScore ? {} : { SEM_REFERENCIA_EXATA: 1 } }))
    if (state.separateResults) rows[0].resultados.push({ ...item.resultados[0], id: 'co-vencedor', fornecedor_nome: 'Outro fornecedor do item' })
    rows = rows.filter(r => r.descricao.toLowerCase().includes((url.searchParams.get('busca') || '').toLowerCase()))
    const filter = url.searchParams.get('analise') || 'todos'
    if (filter !== 'todos') rows = rows.filter(r => r.status_analise === filter)
    const context = { base_id: BASE, execucao_id: url.searchParams.get('execucao_id'), modelo_id: url.searchParams.get('modelo_id'), experimental: true, universo: {}, resumo: { itens: rows.length, processos: rows.length ? 1 : 0, orgaos: 1, fornecedores: 1, fornecedores_no_denominador: 1, contratos_vinculados: 0, resultados: 1, analisados: rows.filter(r => r.status_analise === 'analisados').length, parcial: 0, nao_analisados: rows.filter(r => r.status_analise === 'nao_analisados').length, valor_homologado: '0.10000001', soma_valores_conhecidos: '0.10000001', resultados_sem_total: 0 } }
    const pageOf = entries => {
      const size = Number(url.searchParams.get('tamanho_pagina') || 20), n = Number(url.searchParams.get('pagina') || 1)
      return { dados: entries.slice((n-1)*size,n*size), total: entries.length, pagina: n, tamanho_pagina: size, total_paginas: Math.ceil(entries.length/size) }
    }
    if (path === '/visao/painel') return done({ ...context, distribuicao: Array.from({ length: 10 }, (_,i) => ({ inicio: i*10, fim: (i+1)*10, itens: i === 8 ? context.resumo.analisados : 0 })), evolucao: rows.length ? [{ mes: '2026-09', itens: rows.length, analisados: context.resumo.analisados, parcial: 0, nao_analisados: context.resumo.nao_analisados }] : [], motivos_indisponibilidade: context.resumo.nao_analisados ? { SEM_REFERENCIA_EXATA: context.resumo.nao_analisados } : {} })
    if (path === '/visao/ranking') return done({ ...context, ...pageOf(rows) })
    const supplier = { id: SUPPLIER, nome: 'Fornecedor do recorte', compras_com_resultado: 1, contratos_vinculados: 0, itens: 1, orgaos: 1, valor_homologado: '0.10000001', resultados_sem_total: 0, indice_experimental: hasScore ? '88.125' : null }
    if (path === '/visao/fornecedores') return done({ ...context, ...pageOf(rows.length ? [supplier] : []) })
    if (path === `/visao/fornecedores/${SUPPLIER}`) return done({ ...context, fornecedor: supplier, relacoes: [{ orgao_id: 'org', orgao_nome: 'Órgão do recorte', compras_com_resultado: 1, valor_fornecedor: null, valor_homologado: null, participacao: null, hhi: null, motivo: 'TOTAIS_INCOMPLETOS' }], itens: pageOf(rows.slice(0,1)) })
    return bad('Fornecedor não encontrado neste recorte.', 404)
  } })
  return state
}

test('painel fixa versão/modelo, conserva filtros entre telas e distingue índices de risco', async ({ page }) => {
  const state = await mockView(page)
  const errors = []; page.on('pageerror', e => errors.push(e.message))
  await page.goto('/painel')
  await expect(page.getByRole('heading', { name: 'Clareza para priorizar a análise.' })).toBeVisible()
  await expect(page).toHaveURL(new RegExp(`execucao_id=${EXEC}`))
  await expect(page).toHaveURL(new RegExp(`modelo_id=${MODEL}`))
  await expect(page.getByText('Análise experimental · utilidade não validada')).toBeVisible()
  await expect(page.locator('.dashboard-kpis').getByText('R$ 0,10000001', { exact: true })).toBeVisible()
  await page.locator('.dashboard-start').getByRole('link', { name: 'Ver análise', exact: true }).first().click()
  await expect(page.locator('.crumb')).toContainText('Ranking')
  await expect(page.getByRole('link', { name: 'Itens Sinalizados', exact: true })).not.toHaveClass(/active/)
  await expect(page.getByRole('link', { name: 'Itens Sinalizados', exact: true })).not.toHaveAttribute('aria-current', 'page')
  await expect(page.getByRole('heading', { name: 'Compra 00001 · Item 00001' })).toBeVisible()
  await expect(page.locator('.detail-score-number')).toContainText('88,125')
  await page.getByRole('link', { name: 'Itens Sinalizados', exact: true }).click()
  await page.getByLabel('Buscar item, compra ou fornecedor').fill('Borracha')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByRole('heading', { name: '1 item(ns) no ranking' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('busca')).toBe('Borracha')
  state.active = NEW_EXEC
  await page.getByRole('link', { name: 'Borracha do recorte', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Compra 00001 · Item 00001' })).toBeVisible()
  await expect(page.locator('.detail-score-number')).toContainText('88,125')
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe(EXEC)
  await page.getByRole('link', { name: 'Voltar à consulta' }).click()
  await expect(page.getByRole('heading', { name: '1 item(ns) no ranking' })).toBeVisible()
  expect(errors).toEqual([])
})

test('ausência de scores e publicação não vira zero nem bloqueia consultas reais', async ({ page }) => {
  await mockView(page, { active: null, scored: false })
  await page.goto('/painel')
  await expect(page.getByText('Nenhum índice disponível neste recorte.')).toBeVisible()
  await expect(page).toHaveURL(/execucao_id=nenhuma/)
  await page.getByRole('link', { name: 'Itens Sinalizados', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2 item(ns) no ranking' })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Indisponível', exact: true })).toHaveCount(2)
  await page.getByLabel('Estado da análise').selectOption('analisados')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByText('Nenhum item encontrado nesta página.')).toBeVisible()
})

test('fornecedor mostra compras e contratos separados e concentração desconhecida', async ({ page }) => {
  await mockView(page)
  await page.goto('/fornecedores')
  await page.getByRole('link', { name: 'Fornecedor do recorte', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Fornecedor do recorte', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Participação e concentração por órgão' })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Indisponível', exact: false })).toHaveCount(2)
  await expect(page.getByText('1 compras com resultado · 0 contratos vinculados conhecidos · 1 órgãos')).toBeVisible()
})

test('troca de modelo, paginação, erro e retentativa mantêm seleção explícita', async ({ page }) => {
  const state = await mockView(page)
  await page.goto(`/ranking?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=${MODEL}&tamanho_pagina=1`)
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Próxima', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Caneta do recorte', exact: true })).toBeVisible()
  await page.getByLabel('Modelo experimental').selectOption(AE)
  await expect(page).not.toHaveURL(/pagina=2/)
  state.viewOffline = true
  await page.getByLabel('Ordenação', { exact: true }).selectOption('descricao_asc')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByRole('heading', { name: 'Consulta indisponível' })).toBeVisible()
  state.viewOffline = false
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('heading', { name: '2 item(ns) no ranking' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('modelo_id')).toBe(AE)
})

test('execução inexistente não troca silenciosamente para a ativa e permite escolher outra', async ({ page }) => {
  await mockView(page)
  await page.goto(`/ranking?base_id=${BASE}&execucao_id=00000000-0000-4000-8000-000000000000`)
  await expect(page.getByRole('heading', { name: 'Registro não encontrado' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toHaveCount(0)
  await page.getByLabel('Execução publicada').selectOption(EXEC)
  await expect(page.getByRole('heading', { name: '2 item(ns) no ranking' })).toBeVisible()
  await page.goto(`/itens/${ITEM}?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=00000000-0000-4000-8000-000000000000`)
  await expect(page.getByRole('heading', { name: 'Modelo fora da execução selecionada' })).toBeVisible()
  await expect(page.getByRole('cell', { name: '88,125', exact: true })).toHaveCount(0)
})

test('painel real é utilizável em tela pequena e tema escuro', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.addInitScript(() => localStorage.setItem('lc_tema', 'dark'))
  await mockView(page, { scored: false })
  await page.goto('/painel')
  await expect(page.getByText('Nenhum índice disponível neste recorte.')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('painel-mobile.png'), fullPage: true })
})


test('modelo automático preserva roteamento por item e cobertura sem média entre grupos', async ({ page }) => {
  await mockView(page, { automatic: true })
  await page.goto(`/painel?base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Clareza para priorizar a análise.' })).toBeVisible()
  await expect(page.getByLabel('Modelo experimental')).toHaveCount(0)
  expect(new URL(page.url()).searchParams.get('modelo_id')).toBeNull()
  await page.getByRole('link', { name: 'Itens Sinalizados', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2 item(ns) no ranking' })).toBeVisible()
  await page.getByRole('link', { name: 'Borracha do recorte', exact: true }).click()
  await expect(page.locator('.detail-score-number')).toContainText('88,125')
  expect(new URL(page.url()).searchParams.get('modelo_id')).toBeNull()
  await page.goto(`/processos/${PROCESS}?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.getByText('Itens com análise / importados', { exact: true })).toBeVisible()
  await expect(page.getByText('O universo oficial completo ainda não está confirmado.', { exact: false })).toBeVisible()
  await expect(page.getByText('Média dos sinais disponíveis', { exact: true })).toHaveCount(0)
})


test('painel segue composição do Figma e compara modelos do mesmo resultado sem criar prioridade', async ({ page }) => {
  await page.setViewportSize({ width: 1062, height: 880 })
  await mockView(page, { bothModels: true })
  await page.goto('/painel')
  await expect(page.getByRole('heading', { name: 'Clareza para priorizar a análise.', exact: true })).toBeVisible()
  await expect(page.locator('.dashboard-kpis .kpi')).toHaveCount(4)
  const positions = await page.locator('.dashboard-kpis .kpi').evaluateAll(cards => cards.map(card => card.getBoundingClientRect().top))
  expect(new Set(positions).size).toBe(1)
  await expect(page.getByRole('form', { name: 'Filtros do recorte' })).toHaveCount(0)
  await expect(page.getByText('Filtros e versão da análise', { exact: true })).toHaveCount(0)
  await expect(page.locator('.dashboard-period')).toHaveText('Set 2026')
  const analysisLink = page.locator('.dashboard-start').getByRole('link', { name: 'Ver análise', exact: true }).first()
  await expect(analysisLink).toHaveAttribute('title', 'Ver análise')
  await expect(analysisLink).toHaveAttribute('href', new RegExp(`/ranking/${ITEM}\\?`))
  await expect(page.locator('.dashboard-bin')).toHaveCount(10)
  await expect(page.getByRole('heading', { name: 'Evolução dos itens analisados' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Por onde começar' })).toBeVisible()
  const reading = page.locator('.dashboard-reading')
  await expect(reading).toContainText('Isolation Forest')
  await expect(reading).toContainText('Autoencoder')
  await expect(reading.locator('.dashboard-model')).toHaveCount(2)
  await expect(reading).toContainText('88,125')
  await expect(reading).toContainText('77,8')
  await expect(page.getByText('Alta prioridade', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Em revisão humana', { exact: true })).toHaveCount(0)
  await page.goto('/painel?busca=nenhum-item')
  await expect(page.getByText('Nenhum item com índice disponível nos filtros selecionados.')).toBeVisible()
  await expect(page.locator('.dashboard-reading .dashboard-model')).toHaveCount(0)
})


test('leitura não mistura índices de resultados de fornecedores diferentes', async ({ page }) => {
  await mockView(page, { bothModels: true, separateResults: true })
  await page.goto('/painel')
  const reading = page.locator('.dashboard-reading')
  await reading.getByLabel('Resultado do fornecedor').selectOption(item.resultados[0].id)
  await expect(reading.locator('.dashboard-model')).toHaveCount(1)
  await expect(reading).toContainText('Isolation Forest')
  await expect(reading.locator('.dashboard-model')).toContainText('88,125')
  await reading.getByLabel('Resultado do fornecedor').selectOption('co-vencedor')
  await expect(reading.locator('.dashboard-model')).toHaveCount(1)
  await expect(reading.locator('.dashboard-model')).toContainText('Autoencoder')
  await expect(reading.locator('.dashboard-model')).toContainText('77,8')
  await expect(reading.locator('.dashboard-model')).not.toContainText('88,125')
})

test('detalhe sinalizado separa resultado, referência de treino e explicação dos modelos', async ({ page }, testInfo) => {
  const errors = []; page.on('pageerror', e => errors.push(e.message))
  const state = await mockView(page, { automatic: true })
  await page.route(`**/analises/execucoes/${EXEC}/itens/${ITEM}*`, route => route.fulfill({ json: { dados: [{ cobertura: [], resultados: [
    { id: 'score-if', modelo_id: MODEL, resultado_item_id: item.resultados[0].id, algoritmo: 'isolation_forest', indice_experimental: '88.125', score_bruto: '0.514', atributos: { comparacao: { mediana: '0.05', n_treino: 100, grupo: 'CATMAT-123' } }, explicacao: { status: 'indisponivel', parcelas: [] } },
    { id: 'score-ae', modelo_id: AE, resultado_item_id: item.resultados[0].id, algoritmo: 'autoencoder', indice_experimental: '77.800', score_bruto: '0.4', atributos: { comparacao: { mediana: '0.05', n_treino: 100, grupo: 'CATMAT-123' } }, explicacao: { status: 'disponivel', parcelas: [{ atributo: 'log_quantidade', parcela_score_bruto: '0.3' }, { atributo: 'log_preco_mediana', parcela_score_bruto: '0.1' }] } },
  ] }] } }))
  await page.goto(`/ranking/${ITEM}?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.getByRole('heading', { name: 'Compra 00001 · Item 00001' })).toBeVisible()
  await expect(page.locator('.detail-score-number')).toContainText('88,125')
  await expect(page.getByText('100 observações no treino', { exact: false })).toBeVisible()
  await expect(page.getByText('Contribuição por atributo indisponível para este modelo.', { exact: true })).toBeVisible()
  await page.getByLabel('Modelo da comparação').selectOption(AE)
  await expect(page.locator('.detail-score-number')).toContainText('77,8')
  await expect(page.getByRole('heading', { name: 'Parcelas do erro de reconstrução' })).toBeVisible()
  await expect(page.getByText('75% do erro bruto', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Documentos', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Edital da compra', exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Registro da revisão', exact: true }).click()
  await expect(page.getByText('Nenhuma revisão humana registrada.', { exact: false })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Incluir no relatório', exact: true })).toHaveAttribute('href', new RegExp(`processo_id=${PROCESS}`))
  await page.getByRole('button', { name: 'Sinais e comparação', exact: true }).click()
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
  await expect(page.getByText('Nenhum score disponível para este resultado no modelo selecionado.', { exact: false })).toBeVisible()
  await expect(page.getByText('Referência de treino indisponível para este resultado.')).toBeVisible()
  await expect(page.getByLabel('Resultado do fornecedor')).toHaveCount(0)
  await page.goto(`/ranking/00000000-0000-4000-8000-000000000000?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.getByRole('heading', { name: 'Registro não encontrado' })).toBeVisible()
})

test('detalhe mantém scores de fornecedores separados e respeita modelo fixado', async ({ page }) => {
  await mockView(page, { automatic: true, bothModels: true, separateResults: true })
  await page.route(`**/api/v1/itens/${ITEM}?*`, route => route.fulfill({ json: { base_id: BASE, item: { ...item, resultados: [...item.resultados, { ...item.resultados[0], id: 'co-vencedor', fornecedor_nome: 'Outro fornecedor', sequencial_resultado: 3 }] } } }))
  await page.goto(`/ranking/${ITEM}?base_id=${BASE}&execucao_id=${EXEC}&modelo_id=${MODEL}`)
  await expect(page.locator('.detail-score-number')).toContainText('88,125')
  await page.getByLabel('Resultado do fornecedor').selectOption('co-vencedor')
  await expect(page.locator('.detail-score-number')).toContainText('—')
  await expect(page.locator('.detail-score')).not.toContainText('88,125')
  await page.getByLabel('Modelo da comparação').selectOption(AE)
  await expect(page.locator('.detail-score-number')).toContainText('77,8')
  expect(new URL(page.url()).searchParams.get('modelo_id')).toBe(AE)
  await expect(page.locator('.detail-score')).not.toContainText('88,125')
})

test('detalhe automático conserva preferência do grupo e escolhe maior resultado desse modelo', async ({ page }) => {
  await mockView(page, { automatic: true })
  await page.route(`**/api/v1/analises/execucoes/${EXEC}?*`, route => route.fulfill({ json: { id: EXEC, roteamento_automatico: true, modelos: [{ id: MODEL, algoritmo: 'isolation_forest', grupo: 'grupo-1' }, { id: AE, algoritmo: 'autoencoder', grupo: 'grupo-1' }] } }))
  await page.route(`**/api/v1/itens/${ITEM}?*`, route => route.fulfill({ json: { item: { ...item, resultados: [...item.resultados, { ...item.resultados[0], id: 'segundo-ativo', fornecedor_nome: 'Fornecedor maior score IF', sequencial_resultado: 3 }] } } }))
  await page.route(`**/analises/execucoes/${EXEC}/itens/${ITEM}*`, route => route.fulfill({ json: { dados: [{ cobertura: [], resultados: [
    { id: 'if-1', modelo_id: MODEL, resultado_item_id: item.resultados[0].id, algoritmo: 'isolation_forest', indice_experimental: '40' },
    { id: 'ae-1', modelo_id: AE, resultado_item_id: item.resultados[0].id, algoritmo: 'autoencoder', indice_experimental: '99' },
    { id: 'if-2', modelo_id: MODEL, resultado_item_id: 'segundo-ativo', algoritmo: 'isolation_forest', indice_experimental: '88' },
  ] }] } }))
  await page.goto(`/ranking/${ITEM}?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.locator('.detail-score-number')).toHaveText('88/ 100')
  await expect(page.getByLabel('Resultado do fornecedor')).toHaveValue('segundo-ativo')
  await expect(page.locator('.detail-score')).not.toContainText('99')
})
