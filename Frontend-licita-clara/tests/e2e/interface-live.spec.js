import { readFileSync, mkdirSync, writeFileSync } from 'node:fs'
import AxeBuilder from '@axe-core/playwright'
import { test, expect } from '@playwright/test'

const target = process.env.LICITA_INTERFACE_CONFIG ? JSON.parse(readFileSync(process.env.LICITA_INTERFACE_CONFIG, 'utf8')) : { routes: [] }
for (const theme of ['light', 'dark']) for (const width of [1280, 390]) for (const [label, path] of target.routes) {
  test(`interface ${label} ${theme} ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(theme => { localStorage.setItem('lc_ajuda_vista', '1'); localStorage.setItem('lc_tema', theme) }, theme)
    const errors = []
    page.on('pageerror', e => errors.push(e.message))
    await page.goto(path)
    await expect(page.locator('.content h1').first()).toBeVisible()
    await expect(page.locator('[role="status"]')).toHaveCount(0)
    await expect(page.locator('.query-error')).toHaveCount(0)
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']).analyze()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
    const valuesOverflow = await page.locator('.kpi strong').evaluateAll(nodes => nodes.some(el => el.scrollWidth > el.clientWidth + 1))
    const report = { page: label, theme, width, overflow, valuesOverflow, errors, violations: results.violations }
    const folder = process.env.LICITA_INTERFACE_OUTPUT || '../data/diagnostico/11/interface'
    mkdirSync(folder, { recursive: true })
    writeFileSync(`${folder}/${label}-${theme}-${width}.json`, JSON.stringify(report, null, 2))
    await page.screenshot({ path: `${folder}/${label}-${theme}-${width}.png` })
    if (!process.env.LICITA_INTERFACE_BASELINE) {
      expect(overflow).toBe(false)
      expect(valuesOverflow).toBe(false)
      expect(errors).toEqual([])
      expect(results.violations).toEqual([])
    }
  })
}
