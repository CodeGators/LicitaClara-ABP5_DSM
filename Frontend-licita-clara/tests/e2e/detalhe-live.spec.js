import { readFileSync, mkdirSync, writeFileSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

for (const theme of ['light', 'dark']) for (const width of [1280, 1062, 390]) {
  test(`detalhe real ${theme} ${width}`, async ({ page, request }) => {
    test.setTimeout(60000)
    const config = JSON.parse(readFileSync(process.env.LICITA_INTERFACE_CONFIG, 'utf8'))
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(theme => { localStorage.setItem('lc_ajuda_vista', '1'); localStorage.setItem('lc_tema', theme) }, theme)
    const errors = []; page.on('pageerror', e => errors.push(e.message))
    await page.goto(config.routes.find(([name]) => name === 'painel')[1])
    const link = page.locator('.dashboard-start').getByRole('link', { name: 'Ver análise', exact: true }).first()
    await expect(link).toBeVisible({ timeout: 20000 })
    const href = await link.getAttribute('href')
    await link.click()
    await expect(page.locator('.analysis-detail')).toBeVisible()
    await expect(page.locator('.detail-score-number')).not.toContainText('—')
    await expect(page.locator('[role="status"]')).toHaveCount(0, { timeout: 20000 })
    const url = new URL(page.url()), id = url.pathname.split('/').at(-1)
    expect(url.pathname).toBe(new URL(href, url).pathname)
    expect(url.searchParams.get('base_id')).toBe(config.base)
    expect(url.searchParams.get('execucao_id')).toBe(config.execucao)
    const response = await request.get(`/api/v1/analises/execucoes/${config.execucao}/itens/${id}?base_id=${config.base}`)
    expect(response.ok()).toBe(true)
    const scores = (await response.json()).dados[0].resultados
    const score = scores.find(s => s.algoritmo === 'isolation_forest') || scores[0]
    await expect(page.locator('.detail-score-number')).toContainText(Number(score.indice_experimental).toLocaleString('pt-BR', { maximumFractionDigits: 8 }))
    await expect(page.locator('.detail-comparison')).toContainText(`${score.atributos.comparacao.n_treino.toLocaleString('pt-BR')} observações no treino`)
    const violations = (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations
    expect(violations).toEqual([])
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
    expect(overflow).toBe(false)
    expect(errors).toEqual([])
    const output = process.env.LICITA_DETAIL_OUTPUT || '../data/diagnostico/detalhe_figma'
    mkdirSync(output, { recursive: true })
    await page.screenshot({ path: `${output}/${theme}-${width}.png`, fullPage: true })
    writeFileSync(`${output}/${theme}-${width}.json`, JSON.stringify({ route: page.url(), score: score.indice_experimental, violations, overflow, errors }, null, 2))
  })
}
