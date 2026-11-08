import { test, expect } from '@playwright/test'
import { BASE, OTHER_BASE, ITEM, PROCESS, SUPPLIER, item, otherItem, mockApi } from './fixtures.js'

test('entrada abre dados reais, fixa base e pagina sem fabricar scores', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Consultar itens' })).toBeVisible()
  await expect(page).toHaveURL(new RegExp(`/itens\\?base_id=${BASE}`))
  await expect(page.getByRole('heading', { name: '2 item(ns) encontrado(s)' })).toBeVisible()
  await expect(page.getByText('Sem análise selecionada', { exact: true })).toBeVisible()
  await expect(page.getByText('Dados oficiais · consulta de dados')).toBeVisible()
  await expect(page.getByText('Nexo Suprimentos Ltda.', { exact: true })).toHaveCount(0)
  await page.getByText('Mais filtros', { exact: true }).click()
  await page.getByLabel('Itens por página', { exact: true }).selectOption('5')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect.poll(() => state.calls.filter(u => u.pathname.endsWith('/itens')).at(-1).searchParams.get('tamanho_pagina')).toBe('5')
  expect(state.calls.filter(u => !u.pathname.endsWith('/base/status')).every(u => u.searchParams.get('base_id') === BASE)).toBe(true)
})

test('busca, seletores, datas, valores e ordenação chegam à API como strings', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/itens')
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toBeVisible()
  await page.getByText('Mais filtros', { exact: true }).click()
  await page.getByLabel('Fornecedor', { exact: true }).selectOption(SUPPLIER)
  await page.getByLabel('Órgão', { exact: true }).selectOption({ label: 'Órgão do recorte' })
  await page.getByLabel('Modalidade', { exact: true }).selectOption({ label: 'Pregão' })
  await page.getByLabel('Homologação a partir de').fill('2026-09-01')
  await page.getByLabel('Homologação até').fill('2026-09-30')
  await page.getByLabel('Total homologado mínimo').fill('0.00000001')
  await page.getByLabel('Total homologado máximo').fill('200')
  await page.getByLabel('Ordenação').selectOption('valor_desc')
  await page.getByLabel('Buscar item, compra ou fornecedor').fill('Caneta')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByRole('heading', { name: '1 item(ns) encontrado(s)' })).toBeVisible()
  const params = state.calls.filter(u => u.pathname.endsWith('/itens')).at(-1).searchParams
  expect(params.get('valor_minimo')).toBe('0.00000001')
  expect(params.get('fornecedor_id')).toBe(SUPPLIER)
  expect(params.get('homologacao_inicio')).toBe('2026-09-01')
  expect(params.get('ordenacao')).toBe('valor_desc')
  await page.getByRole('button', { name: 'Limpar filtros' }).click()
  await expect(page.getByRole('heading', { name: '2 item(ns) encontrado(s)' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('base_id')).toBe(BASE)
  await page.getByLabel('Buscar item, compra ou fornecedor').fill('Rascunho não aplicado')
  await page.getByRole('button', { name: 'Limpar filtros' }).click()
  await expect(page.getByLabel('Buscar item, compra ou fornecedor')).toHaveValue('')
})

test('lista, detalhe, processo e documentos preservam o contexto e os nulos', async ({ page }) => {
  await mockApi(page)
  await page.goto('/itens?busca=Borracha')
  await page.getByRole('link', { name: 'Borracha do recorte', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Borracha do recorte', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Cancelado', exact: false }).last()).toContainText('Cancelado')
  await expect(page.getByText('R$ 0,10000001', { exact: true }).first()).toBeVisible()
  const doc = page.getByRole('link', { name: 'Edital da compra' })
  await expect(doc).toHaveAttribute('href', 'https://pncp.gov.br/arquivo.pdf')
  await expect(doc).toHaveAttribute('rel', 'noopener noreferrer')
  await page.getByRole('link', { name: 'Voltar à consulta' }).click()
  await expect(page).toHaveURL(/busca=Borracha/)
  await page.getByRole('link', { name: 'Borracha do recorte', exact: true }).click()
  await page.getByRole('link', { name: 'Ver processo da compra' }).click()
  await expect(page).toHaveURL(new RegExp(`/processos/${PROCESS}\\?base_id=${BASE}`))
  await expect(page.getByText('R$ 200,00000001', { exact: true })).toBeVisible()
  await expect(page.getByText('Não informado', { exact: true })).toBeVisible()
})

test('páginas fora do intervalo e buscas vazias não mantêm dados antigos', async ({ page }) => {
  await mockApi(page)
  await page.goto(`/itens?base_id=${BASE}&pagina=2&tamanho_pagina=1`)
  await expect(page.getByRole('link', { name: 'Caneta do recorte', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Anterior', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toBeVisible()
  await page.goto(`/itens?base_id=${BASE}&busca=ausente`)
  await expect(page.getByText('Nenhum item encontrado nesta página.', { exact: false })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toHaveCount(0)
})

test('IDs inexistentes e inválidos nunca mostram o primeiro item', async ({ page }) => {
  await mockApi(page)
  await page.goto(`/itens/00000000-0000-0000-0000-000000000000?base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Registro não encontrado' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Borracha do recorte', exact: true })).toHaveCount(0)
  await page.goto(`/itens/LC-2026-0142?base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Consulta inválida' })).toBeVisible()
})

test('sem base, serviço indisponível e recuperação têm estados explícitos', async ({ page }) => {
  const state = await mockApi(page, { noBase: true })
  await page.goto('/itens')
  await expect(page.getByRole('heading', { name: 'Nenhuma base disponível' })).toBeVisible()
  expect(state.calls.some(u => u.pathname.endsWith('/itens'))).toBe(false)
  state.noBase = false; state.offline = true
  await page.getByRole('button', { name: 'Consultar novamente' }).click()
  await expect(page.getByRole('heading', { name: 'Consulta indisponível' })).toBeVisible()
  state.offline = false
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toBeVisible()
})

test('base fixada na URL não muda quando uma nova base passa a ser a mais recente', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/itens')
  await expect(page).toHaveURL(new RegExp(BASE))
  state.latest = OTHER_BASE
  await page.reload()
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('base_id')).toBe(BASE)
  await page.goto('/itens?base_id=inexistente')
  await expect(page.getByRole('heading', { name: 'Registro não encontrado' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('base_id')).toBe('inexistente')
})

test('falha nos documentos permite repetir sem apagar o detalhe', async ({ page }) => {
  const state = await mockApi(page, { documentsOffline: true })
  await page.goto(`/itens/${ITEM}?base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Borracha do recorte', exact: true })).toBeVisible()
  await expect(page.getByText('Documentos indisponíveis.', { exact: true })).toBeVisible()
  state.documentsOffline = false
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('link', { name: 'Edital da compra' })).toBeVisible()
})

test('respostas antigas não substituem resultados de uma busca nova', async ({ page }) => {
  await mockApi(page, { handler: async ({ url, path, send }) => {
    if (path !== '/itens' || url.searchParams.get('busca') !== 'lenta') return false
    await new Promise(resolve => setTimeout(resolve, 600))
    await send({ dados: [{ ...item, descricao: 'RESULTADO ANTIGO' }], meta: { total: 1, total_paginas: 1, pagina: 1 } })
    return true
  } })
  await page.goto('/itens')
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toBeVisible()
  await page.getByLabel('Buscar item, compra ou fornecedor').fill('lenta')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await page.getByLabel('Buscar item, compra ou fornecedor').fill('Caneta')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByRole('link', { name: 'Caneta do recorte', exact: true })).toBeVisible()
  await page.waitForTimeout(750)
  await expect(page.getByText('RESULTADO ANTIGO')).toHaveCount(0)
})

test('demonstração separada e relatório real não caem em exemplos fictícios', async ({ page }) => {
  await mockApi(page)
  await page.goto('/demonstracao/painel')
  await expect(page.getByText('Esta tela é demonstrativa e usa dados fictícios.')).toBeVisible()
  await page.goto(`/relatorios?item=${ITEM}&base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Relatório indisponível' })).toBeVisible()
  await expect(page.getByText('Nexo Suprimentos Ltda.', { exact: true })).toHaveCount(0)
})

test('intervalo inválido mostra erro e permite corrigir os filtros', async ({ page }) => {
  await mockApi(page)
  await page.goto('/itens')
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toBeVisible()
  await page.getByText('Mais filtros', { exact: true }).click()
  await page.getByLabel('Total homologado mínimo').fill('2')
  await page.getByLabel('Total homologado máximo').fill('1')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByRole('heading', { name: 'Consulta inválida' })).toBeVisible()
  await expect(page.getByText('Intervalo inválido.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Limpar filtros' }).click()
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toBeVisible()
})

test('item sem resultados mostra ausência e mantém documentos da compra', async ({ page }) => {
  await mockApi(page)
  await page.goto(`/itens/${otherItem.id}?base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Caneta do recorte', exact: true })).toBeVisible()
  await expect(page.getByText('Nenhum resultado conhecido nesta base.', { exact: true })).toBeVisible()
  await expect(page.getByText('Não informado', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'Edital da compra' })).toBeVisible()
})

test('consulta funciona em tela pequena e tema escuro sem rolagem horizontal da página', async ({ page }, testInfo) => {
  await mockApi(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/itens')
  await expect(page.getByRole('link', { name: 'Borracha do recorte', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('consulta-mobile.png'), fullPage: true })
})
