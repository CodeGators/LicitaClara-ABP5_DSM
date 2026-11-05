import { readFileSync, mkdirSync, writeFileSync } from 'node:fs'
import AxeBuilder from '@axe-core/playwright'
import { test, expect } from '@playwright/test'

for (const theme of ['light', 'dark']) for (const width of [1280, 1062, 390]) {
  test(`painel figma ${theme} ${width}`, async ({ page }) => {
    const target = JSON.parse(readFileSync(process.env.LICITA_INTERFACE_CONFIG, 'utf8'))
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(theme => { localStorage.setItem('lc_ajuda_vista', '1'); localStorage.setItem('lc_tema', theme) }, theme)
    const errors = []; page.on('pageerror', e => errors.push(e.message))
    await page.goto(target.routes.find(([name]) => name === 'painel')[1])
    await expect(page.locator('.dashboard-kpis .kpi')).toHaveCount(4)
    await expect(page.getByRole('heading', { name: 'Por onde começar' })).toBeVisible()
    await expect(page.locator('[role="status"]')).toHaveCount(0)
    await expect(page.locator('.query-error')).toHaveCount(0)
    await expect(page.locator('#dashboard-settings')).not.toHaveAttribute('open')
    if (width >= 1062) {
      const positions = await page.locator('.dashboard-kpis .kpi').evaluateAll(cards => cards.map(el => el.getBoundingClientRect().top))
      expect(new Set(positions).size).toBe(1)
    }
    const snapshot = await page.request.get(`/api/v1/visao/painel?base_id=${target.base}&execucao_id=${target.execucao}`)
    expect(snapshot.ok()).toBe(true)
    const data = await snapshot.json()
    const displayed = await page.locator('.dashboard-kpis strong').allTextContents()
    expect(displayed[0]).toBe(data.resumo.processos.toLocaleString('pt-BR'))
    expect(displayed[2]).toBe((data.resumo.analisados + data.resumo.parcial).toLocaleString('pt-BR'))
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']).analyze()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
    const folder = process.env.LICITA_PAINEL_OUTPUT || '../data/diagnostico/painel_figma'
    mkdirSync(folder, { recursive: true })
    writeFileSync(`${folder}/${theme}-${width}.json`, JSON.stringify({ errors, overflow, violations: axe.violations, resumo: data.resumo }, null, 2))
    await page.screenshot({ path: `${folder}/${theme}-${width}.png`, fullPage: true })
    expect(axe.violations).toEqual([])
    expect(overflow).toBe(false)
    expect(errors).toEqual([])
  })
}
