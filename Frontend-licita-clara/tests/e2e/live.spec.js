import { test, expect } from '@playwright/test'

test('consulta real pelo proxy Vite navega por lista, item, processo e documentos', async ({ page }, testInfo) => {
  await page.addInitScript(() => localStorage.setItem('lc_ajuda_vista', '1'))
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/itens')
  await expect(page.getByRole('heading', { name: 'Consultar itens', exact: true })).toBeVisible()
  const rows = page.locator('section[aria-label="Resultados da consulta"] tbody tr')
  await expect(rows.first()).toBeVisible()
  const base = new URL(page.url()).searchParams.get('base_id')
  expect(base).toMatch(/^[a-f0-9-]{36}$/)
  const initial = await rows.count()
  expect(initial).toBeGreaterThan(0)
  await page.getByLabel('Itens por página', { exact: true }).selectOption('5')
  await page.getByRole('button', { name: 'Aplicar filtros' }).click()
  await expect(rows).toHaveCount(Math.min(initial, 5))
  if (initial > 5) {
    await page.getByRole('button', { name: 'Próxima', exact: true }).click()
    await expect(page).toHaveURL(/pagina=2/)
  }
  await rows.first().getByRole('link').click()
  await expect(page.getByRole('heading', { name: 'Resultados do item', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Documentos da compra e contratos vinculados', exact: true })).toBeVisible()
  await expect(page.getByText('Carregando documentos…', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('alert')).toHaveCount(0)
  expect(new URL(page.url()).searchParams.get('base_id')).toBe(base)
  await page.screenshot({ path: testInfo.outputPath('item-real.png'), fullPage: true })
  await page.getByRole('link', { name: 'Ver processo da compra' }).click()
  await expect(page.getByRole('heading', { name: 'Itens deste processo', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Documentos da compra e contratos vinculados', exact: true })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('base_id')).toBe(base)
  expect(errors).toEqual([])
})
