import { test, expect } from '@playwright/test'
import { BASE, OTHER_BASE, ITEM, PROCESS, item, otherItem, mockApi } from './fixtures.js'

const searchLabel = 'Buscar item ou código de catálogo'

test('entrada usa produtos da base atual sem dados fictícios ou análise fabricada', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Itens Sinalizados', exact: true })).toBeVisible()
  await expect(page).toHaveURL(new RegExp(`/ranking\\?base_id=${BASE}`))
  await expect(page.getByRole('heading', { name: '2 produtos' })).toBeVisible()
  await expect(page.locator('tbody .pill')).toHaveText(['Sem análise disponível', 'Sem análise disponível'])
  await expect(page.locator('tbody tr[data-if-band]')).toHaveCount(0)
  await expect(page.getByText('Nexo Suprimentos Ltda.', { exact: true })).toHaveCount(0)
  expect(state.calls.some(url => url.pathname === '/api/v1/itens')).toBe(false)
})

test('busca e ordenação chegam à API; limpar remove também o rascunho', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/ranking')
  await page.getByLabel(searchLabel).fill('Caneta')
  await page.getByLabel('Ordenação', { exact: true }).selectOption('valor_desc')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByRole('heading', { name: '1 produto' })).toBeVisible()
  const params = state.calls.filter(url => url.pathname.endsWith('/produtos')).at(-1).searchParams
  expect(params.get('busca')).toBe('Caneta')
  expect(params.get('ordenacao')).toBe('valor_desc')
  await page.getByLabel(searchLabel).fill('Rascunho')
  await page.getByRole('button', { name: 'Limpar filtros' }).click()
  await expect(page.getByLabel(searchLabel)).toHaveValue('')
  await expect(page.getByRole('heading', { name: '2 produtos' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('base_id')).toBe(BASE)
})

test('lista, detalhe e compra preservam contexto, valores e ausência de referência', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/ranking?busca=Borracha')
  await page.getByRole('link', { name: item.descricao, exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Compra 00001 · Item 00001' })).toBeVisible()
  await expect(page.getByText('Não há referência de preço suficiente para comparar este resultado.')).toBeVisible()
  await page.getByText('Ver resultados e dados do item', { exact: true }).click()
  await expect(page.getByRole('columnheader', { name: 'Situação' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Resultados do item' })).toBeVisible()
  await page.getByRole('link', { name: 'Voltar à consulta' }).click()
  await expect(page).toHaveURL(/busca=Borracha/)
  await page.getByRole('link', { name: item.descricao, exact: true }).click()
  await page.getByRole('link', { name: 'Ver todos os itens da compra' }).click()
  await expect(page).toHaveURL(new RegExp(`/processos/${PROCESS}`))
  await expect(page.getByText('R$ 200,00', { exact: true })).toBeVisible()
  await expect(page.getByText('Não informado', { exact: true }).first()).toBeVisible()
  expect(state.calls.some(url => url.pathname.endsWith('/documentos'))).toBe(false)
})

test('paginação e buscas vazias não mantêm dados antigos', async ({ page }) => {
  await mockApi(page)
  await page.goto(`/ranking?base_id=${BASE}&pagina=2&tamanho_pagina=1`)
  await expect(page.getByRole('link', { name: otherItem.descricao, exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Anterior', exact: true }).click()
  await expect(page.getByRole('link', { name: item.descricao, exact: true })).toBeVisible()
  await page.goto(`/ranking?base_id=${BASE}&busca=ausente`)
  await expect(page.getByText('Nenhum item encontrado nesta página.')).toBeVisible()
  await expect(page.locator('tbody tr')).toHaveCount(0)
})

test('IDs inexistentes e inválidos nunca mostram o primeiro item', async ({ page }) => {
  await mockApi(page)
  await page.goto(`/ranking/00000000-0000-0000-0000-000000000000?base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Registro não encontrado' })).toBeVisible()
  await expect(page.locator('.analysis-detail')).toHaveCount(0)
  await page.goto(`/ranking/LC-2026-0142?base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Consulta inválida' })).toBeVisible()
})

test('sem base e falha de conexão permitem recuperação', async ({ page }) => {
  const state = await mockApi(page, { noBase: true })
  await page.goto('/ranking')
  await expect(page.getByRole('heading', { name: 'Nenhuma base disponível' })).toBeVisible()
  expect(state.calls.some(url => url.pathname.endsWith('/produtos'))).toBe(false)
  state.noBase = false; state.offline = true
  await page.getByRole('button', { name: 'Consultar novamente' }).click()
  await expect(page.getByRole('heading', { name: 'Consulta indisponível' })).toBeVisible()
  state.offline = false
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByRole('link', { name: item.descricao, exact: true })).toBeVisible()
})

test('base fixada não muda quando outra se torna mais recente', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/ranking')
  await expect(page).toHaveURL(new RegExp(BASE))
  state.latest = OTHER_BASE
  await page.reload()
  await expect(page.getByRole('link', { name: item.descricao, exact: true })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('base_id')).toBe(BASE)
  await page.goto('/ranking?base_id=inexistente')
  await expect(page.getByRole('heading', { name: 'Registro não encontrado' })).toBeVisible()
})

test('falha ao consultar item permite retentar sem mudar o endereço', async ({ page }) => {
  let failing = true
  await mockApi(page, { handler: async ({ path, error }) => {
    if (path !== `/itens/${ITEM}` || !failing) return false
    await error('Item temporariamente indisponível.'); return true
  } })
  await page.goto(`/ranking/${ITEM}?base_id=${BASE}`)
  await expect(page.getByText('Item temporariamente indisponível.')).toBeVisible()
  failing = false
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.locator('.analysis-detail')).toBeVisible()
})

test('respostas antigas não substituem uma busca nova', async ({ page }) => {
  await mockApi(page, { handler: async ({ url, path, send }) => {
    if (path !== '/visao/produtos' || url.searchParams.get('busca') !== 'lenta') return false
    await new Promise(resolve => setTimeout(resolve, 600))
    await send({ dados: [], total: 0, total_paginas: 0, pagina: 1 }); return true
  } })
  await page.goto('/ranking')
  await expect(page.getByRole('link', { name: item.descricao, exact: true })).toBeVisible()
  await page.getByLabel(searchLabel).fill('lenta')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await page.getByLabel(searchLabel).fill('Caneta')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(page.getByRole('link', { name: otherItem.descricao, exact: true })).toBeVisible()
  await page.waitForTimeout(750)
  await expect(page.getByRole('heading', { name: '1 produto' })).toBeVisible()
})

test('rotas demonstrativas foram removidas e oferecem acesso aos dados reais', async ({ page }) => {
  await mockApi(page)
  for (const path of ['painel', 'itens', `itens/${ITEM}`, 'fornecedores', 'relatorios']) {
    await page.goto(`/demonstracao/${path}`)
    await expect(page.getByRole('heading', { name: 'Página não encontrada' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Itens Sinalizados', exact: true }).last()).toHaveAttribute('href', '/ranking')
    await expect(page.getByText('Órgãos e empresas fictícios')).toHaveCount(0)
  }
})

test('item sem resultados mostra ausência e valores desconhecidos', async ({ page }) => {
  await mockApi(page)
  await page.goto(`/ranking/${otherItem.id}?base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Compra 00001 · Item 00002' })).toBeVisible()
  await page.getByText('Ver resultados e dados do item', { exact: true }).click()
  await expect(page.getByText('Nenhum resultado conhecido nesta base.')).toBeVisible()
  await expect(page.getByText('Não informado', { exact: true }).first()).toBeVisible()
})

test('itens funcionam no celular em tema escuro sem alargar a página', async ({ page }) => {
  await mockApi(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/ranking')
  await expect(page.getByRole('link', { name: item.descricao, exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
