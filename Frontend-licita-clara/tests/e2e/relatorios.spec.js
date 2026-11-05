import { test, expect } from '@playwright/test'
import { BASE, PROCESS, item, context, mockApi } from './fixtures.js'

async function reportApi(page) {
  const state = { conflict: false }
  await mockApi(page, { handler: async ({ url, path, send, error }) => {
    if (path === `/relatorios/processos/${PROCESS}/previa`) {
      await send({
        titulo: url.searchParams.get('titulo'), snapshot_sha256: 'a'.repeat(64),
        base: { id: BASE, versao: 'teste', periodo_inicio: '2026-09-01', periodo_fim: '2026-09-30', manifesto_sha256: 'b'.repeat(64) },
        analise: null, processo: { ...context, objeto: 'Material de escritório real', valor_estimado_processo: null, valor_homologado_processo: '100.00000001', valor_homologado_itens_recorte: '0.10000001' },
        resumo: { itens: 1, itens_analisados: 0, scores: 0 },
        itens: [{ ...item, scores: [], cobertura: [] }],
        limites: ['Anomalia estatística não é prova de irregularidade.'], fonte: 'Compras.gov.br',
      }); return true
    }
    if (path === '/processos') { await send({ dados: [{ ...context }], meta: { total: 1 } }); return true }
    if (path.endsWith('/arquivo')) {
      if (state.conflict) { await error('Os dados diferem da prévia. Atualize antes de exportar.', 409); return true }
      expect(url.searchParams.get('snapshot_sha256')).toBe('a'.repeat(64))
      await send({ arquivo: 'download de teste' }); return true
    }
    return false
  } })
  return state
}

test('relatório real permite selecionar processo, conferir prévia e baixar PDF/CSV sem login', async ({ page }) => {
  await reportApi(page)
  await page.goto(`/relatorios?base_id=${BASE}`)
  await expect(page.getByRole('heading', { name: 'Selecione um processo', exact: true })).toBeVisible()
  await page.getByLabel('Processo selecionado').selectOption(PROCESS)
  await expect(page.getByRole('heading', { name: 'Relatório de anomalias', exact: true })).toBeVisible()
  await expect(page.getByText('Sem análise disponível para este item na seleção.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Exportar PDF', exact: true })).toBeEnabled()
  const pdfPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar PDF', exact: true }).click()
  expect((await pdfPromise).suggestedFilename()).toMatch(/\.pdf$/)
  await page.getByRole('button', { name: 'CSV', exact: true }).click()
  const csvPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar CSV', exact: true }).click()
  expect((await csvPromise).suggestedFilename()).toMatch(/\.csv$/)
  await page.getByLabel('Título do relatório').fill('Conferência de preços')
  await expect(page.getByRole('button', { name: 'Exportar CSV', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Atualizar prévia', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Conferência de preços', exact: true })).toBeVisible()
})

test('download desatualizado mostra erro e prévia é utilizável em celular', async ({ page }) => {
  const state = await reportApi(page)
  await page.goto(`/relatorios?base_id=${BASE}&processo_id=${PROCESS}`)
  await expect(page.getByRole('button', { name: 'Exportar PDF', exact: true })).toBeEnabled()
  state.conflict = true
  await page.getByRole('button', { name: 'Exportar PDF', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Os dados diferem da prévia.')
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByLabel('Processo selecionado')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await expect(page.getByText('Nexo Suprimentos Ltda.', { exact: true })).toHaveCount(0)
})
