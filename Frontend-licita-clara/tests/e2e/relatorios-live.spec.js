import { readFileSync } from 'node:fs'
import { test, expect } from '@playwright/test'

test('prévia e arquivos reais preservam processo e snapshot, sem login', async ({ page }) => {
  const target = JSON.parse(readFileSync(process.env.LICITA_REPORT_TEST_CONFIG, 'utf8'))
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.addInitScript(() => localStorage.setItem('lc_ajuda_vista', '1'))
  const params = new URLSearchParams({ base_id: target.base, execucao_id: target.execucao, processo_id: target.processo })
  const response = page.waitForResponse(r => r.url().includes('/relatorios/processos/') && r.url().includes('/previa'))
  await page.goto(`/relatorios?${params}`)
  const preview = await (await response).json()
  expect(preview.processo.id).toBe(target.processo)
  expect(preview.resumo.scores).toBeGreaterThan(0)
  await expect(page.getByRole('heading', { name: 'Relatório de anomalias', exact: true })).toBeVisible()
  await page.screenshot({ path: 'test-results/relatorio-desktop.png' })
  const pdfEvent = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar PDF', exact: true }).click()
  const pdf = await pdfEvent
  await pdf.saveAs('test-results/relatorio-real.pdf')
  expect(readFileSync('test-results/relatorio-real.pdf').subarray(0, 5).toString()).toBe('%PDF-')
  await page.getByRole('button', { name: 'CSV', exact: true }).click()
  const csvEvent = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar CSV', exact: true }).click()
  const csv = await csvEvent
  await csv.saveAs('test-results/relatorio-real.csv')
  expect(readFileSync('test-results/relatorio-real.csv', 'utf8')).toContain(preview.snapshot_sha256)
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(() => page.locator('.side').evaluate(el => el.getBoundingClientRect().right)).toBeLessThanOrEqual(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.getByRole('heading', { name: 'Relatório de anomalias', exact: true }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: 'test-results/relatorio-mobile.png' })
  expect(errors).toEqual([])
})
