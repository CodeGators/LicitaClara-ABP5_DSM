import AxeBuilder from '@axe-core/playwright'
import { test, expect } from '@playwright/test'
import { BASE, ITEM, mockApi } from './fixtures.js'

async function wcag(page, include) {
  let builder = new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
  if (include) builder = builder.include(include)
  expect((await builder.analyze()).violations).toEqual([])
}

test('ajuda mantém foco, aceita teclado nas abas e devolve foco ao fechar', async ({ page }) => {
  await mockApi(page)
  await page.goto(`/itens?base_id=${BASE}`)
  const trigger = page.getByRole('button', { name: 'Como funciona', exact: true })
  await trigger.click()
  const dialog = page.getByRole('dialog', { name: 'Bem-vindo ao Licita Clara' })
  await expect(dialog.getByRole('button', { name: 'Fechar', exact: true })).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect.poll(() => dialog.evaluate(el => el.contains(document.activeElement))).toBe(true)
  await page.keyboard.press('Tab')
  await expect(dialog.getByRole('button', { name: 'Fechar', exact: true })).toBeFocused()
  await dialog.getByRole('tab', { name: 'Como funciona', exact: true }).focus()
  await page.keyboard.press('ArrowRight')
  await expect(dialog.getByRole('tab', { name: 'Glossário' })).toBeFocused()
  await expect(dialog.getByRole('tabpanel')).toContainText('Índice de anomalia relativo ao treino')
  await page.keyboard.press('End')
  await expect(dialog.getByRole('tab', { name: 'Créditos' })).toBeFocused()
  await page.keyboard.press('Home')
  await expect(dialog.getByRole('tab', { name: 'Como funciona', exact: true })).toBeFocused()
  for (let i = 0; i < 12; i++) { await page.keyboard.press('Tab'); expect(await dialog.evaluate(el => el.contains(document.activeElement))).toBe(true) }
  await wcag(page, '[role="dialog"]')
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(trigger).toBeFocused()
  expect(await page.evaluate(() => document.body.style.overflow)).toBe('')
})

test('menu móvel fechado fica fora do teclado; aberto isola foco e fecha com Escape', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await mockApi(page)
  await page.goto('/itens')
  const trigger = page.getByRole('button', { name: 'Abrir menu' })
  await expect(page.locator('#menu-principal')).toHaveAttribute('inert', '')
  await trigger.focus(); await page.keyboard.press('Enter')
  const dialog = page.getByRole('dialog', { name: 'Menu principal', exact: true })
  await expect(dialog.getByRole('button', { name: 'Fechar menu' })).toBeFocused()
  await expect(trigger).toHaveAttribute('aria-expanded', 'true')
  await page.keyboard.press('Shift+Tab')
  await expect(dialog.getByRole('link', { name: 'Relatórios', exact: true })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(dialog.getByRole('button', { name: 'Fechar menu' })).toBeFocused()
  await wcag(page, '#menu-principal')
  await page.keyboard.press('Escape')
  await expect(trigger).toBeFocused()
  await expect(trigger).toHaveAttribute('aria-expanded', 'false')
  for (let i = 0; i < 12; i++) { await page.keyboard.press('Tab'); expect(await page.evaluate(() => !!document.activeElement.closest('#menu-principal'))).toBe(false) }
  await trigger.click()
  await page.setViewportSize({ width: 1280, height: 900 })
  await expect(page.getByRole('main')).toBeFocused()
})

test('atalho pula navegação; mudar de tela atualiza título e foco no conteúdo', async ({ page }) => {
  await mockApi(page)
  await page.goto('/itens')
  await expect(page.getByRole('heading', { name: 'Consultar itens', exact: true })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Navegação principal' }).getByRole('link')).toHaveText(['Painel Geral', 'Itens Sinalizados', 'Fornecedores', 'Relatórios'])
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Pular para o conteúdo' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('main')).toBeFocused()
  await page.getByRole('navigation', { name: 'Navegação principal' }).getByRole('link', { name: 'Relatórios', exact: true }).click()
  await expect(page).toHaveTitle('Relatórios — Licita Clara')
  await expect(page.getByRole('main')).toBeFocused()
})

test('tabelas rolam com teclado sem alargar a página em 320px e tema persiste', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 844 })
  await mockApi(page)
  await page.goto(`/itens/${ITEM}?base_id=${BASE}`)
  const table = page.getByRole('region', { name: 'Resultados do item; use as setas para rolar na horizontal' })
  await table.focus()
  await page.keyboard.press('ArrowRight')
  await expect.poll(() => table.evaluate(el => el.scrollLeft)).toBeGreaterThan(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await wcag(page)
})

for (const mode of ['empty', 'error', 'loading']) test(`estado ${mode} mantém conteúdo identificado e acessível`, async ({ page }) => {
  await mockApi(page, mode === 'empty' ? { noBase: true } : {})
  if (mode === 'error') await page.route('**/api/v1/base/status**', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ erro: { mensagem: 'Base temporariamente indisponível.' } }) }))
  let release
  if (mode === 'loading') {
    const pending = new Promise(resolve => { release = resolve })
    await page.route('**/api/v1/base/status**', async route => { await pending; await route.fallback().catch(() => {}) })
  }
  await page.goto('/itens')
  if (mode === 'empty') await expect(page.getByRole('heading', { name: 'Nenhuma base disponível' })).toBeVisible()
  if (mode === 'error') await expect(page.getByRole('alert')).toBeVisible()
  if (mode === 'loading') await expect(page.getByRole('status')).toContainText('Consultando a base de dados')
  try {
    await expect(page.getByRole('main')).toHaveCount(1)
    await wcag(page)
  } finally { release?.() }
})

test('consulta de itens mantém a versão escolhida ao aplicar e limpar filtros', async ({ page }) => {
  await mockApi(page)
  const execution = '77777777-7777-4777-8777-777777777777'
  const model = '88888888-8888-4888-8888-888888888888'
  await page.goto(`/itens?base_id=${BASE}&execucao_id=${execution}&modelo_id=${model}`)
  await expect(page.getByText('Análise selecionada', { exact: true })).toBeVisible()
  await page.getByLabel('Buscar item, compra ou fornecedor', { exact: true }).fill('Borracha')
  await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe(execution)
  expect(new URL(page.url()).searchParams.get('modelo_id')).toBe(model)
  await page.getByRole('button', { name: 'Limpar filtros', exact: true }).click()
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe(execution)
  expect(new URL(page.url()).searchParams.get('busca')).toBe(null)
})

test('ajuda e menu em tema escuro mantêm contraste e navegação acessível', async ({ page }) => {
  await mockApi(page)
  await page.addInitScript(() => localStorage.setItem('lc_tema', 'dark'))
  await page.goto('/itens')
  await page.getByRole('button', { name: 'Como funciona', exact: true }).click()
  await wcag(page, '[role="dialog"]')
  await page.keyboard.press('Escape')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('button', { name: 'Abrir menu' }).click()
  await wcag(page, '#menu-principal')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Abrir menu' })).toBeFocused()
})
