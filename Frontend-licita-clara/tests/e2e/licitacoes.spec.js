import { test, expect } from '@playwright/test'
import { BASE, ITEM, PROCESS, item, otherItem, mockApi } from './fixtures.js'

const EXEC = '77777777-7777-4777-8777-777777777777'
const MODEL = '88888888-8888-4888-8888-888888888888'
const OTHER = '22222222-2222-4222-8222-333333333333'

async function setup(page) {
  const state = await mockApi(page, { fail: false, handler: async ({ path, url, send, error }) => {
    const done = async body => { await send(body); return true }
    const run = { id: EXEC, roteamento_automatico: true, concluido_em: '2026-11-08T15:00:00Z', modelos: [{ id: MODEL, algoritmo: 'isolation_forest' }] }
    if (path === '/analises/publicacao') return done({ execucao_id: EXEC, status: 'publicada_experimental' })
    if (path === '/analises/execucoes') return done({ dados: [run], total_paginas: 1 })
    if (path === `/analises/execucoes/${EXEC}`) return done(run)
    if (path === `/analises/execucoes/${EXEC}/itens/${ITEM}`) return done({ dados: [{ cobertura: [], resultados: [{ id: 'score-1', modelo_id: MODEL, algoritmo: 'isolation_forest', resultado_item_id: item.resultados[0].id, medida_if: '0.691' }] }] })
    if (!path.startsWith('/visao/licitacoes')) return false
    if (state.fail) { await error('Consulta temporariamente indisponível.'); return true }
    const rows = [
      { id: PROCESS, processo: item.processo, descricao: item.processo.objeto, valor_homologado: '100000.00000001', requer_validacao: !!state.reviewFirst, sinalizacao: state.reviewFirst ? 'requer_validacao' : 'anomalia_intermediaria', medida_if_media: '0.691', maior_medida_if: '0.99', itens_com_medida_if: 1, itens_importados: 2, itens_analise_parcial: 0, status_analise: 'parcial', valores_itens_importados: { valor_homologado: '0.10000001', resultados_sem_total: 0 } },
      { id: OTHER, processo: { ...item.processo, id: OTHER, numero_compra: '00002', objeto: 'Computadores' }, descricao: 'Computadores', valor_homologado: null, requer_validacao: false, sinalizacao: 'sem_analise', medida_if_media: null, maior_medida_if: null, itens_com_medida_if: 0, itens_importados: 0, itens_analise_parcial: 0, status_analise: 'nao_analisados', valores_itens_importados: { valor_homologado: null, resultados_sem_total: 0 } },
    ]
    const context = { base_id: BASE, execucao_id: EXEC, modelo_id: null, resumo: { licitacoes: 2, com_medida_if: 1, itens_importados: 2, itens_com_medida_if: 1 } }
    const paginate = entries => {
      const page = Number(url.searchParams.get('pagina') || 1), size = Number(url.searchParams.get('tamanho_pagina') || 20)
      return { dados: entries.slice((page-1)*size,page*size), pagina: page, tamanho_pagina: size, total: entries.length, total_paginas: Math.ceil(entries.length/size) }
    }
    if (path === '/visao/licitacoes') return done({ ...context, ...paginate(rows.filter(r => r.descricao.toLowerCase().includes((url.searchParams.get('busca') || '').toLowerCase()) && (!url.searchParams.getAll('sinalizacao').length || url.searchParams.getAll('sinalizacao').includes(r.sinalizacao)))) })
    const row = rows.find(r => path.endsWith('/'+r.id))
    if (!row) { await error('Licitação não encontrada nesta base.',404); return true }
    const items = [item, otherItem].map((r,i) => ({ ...r, resultados: r.resultados.filter(e=>!e.cancelado), valor_homologado: r.valor_homologado_item, resultados_sem_total: 0, medida_if: i === 0 ? '0.691' : null, status_analise: i === 0 ? 'analisados' : 'nao_analisados', resultados_analisados: i === 0 ? 1 : 0, motivos: {} }))
    return done({ ...context, licitacao: row, itens: paginate(row.id === PROCESS ? items : []) })
  } })
  return state
}

test('licitações usam cores pela média, ocultam medidas e abrem itens e análise correta', async ({ page }) => {
  await setup(page)
  await page.goto('/licitacoes')
  await expect(page.getByRole('heading', { name: 'Licitações Sinalizadas', exact: true })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: 'Medida IF média', exact: true })).toHaveCount(0)
  await expect(page.getByRole('columnheader', { name: 'Maior medida IF', exact: true })).toHaveCount(0)
  await expect(page.getByRole('row').filter({ has: page.getByRole('link', { name: 'Compra 00001', exact: true }) })).toHaveAttribute('data-if-band', 'yellow')
  await expect(page.locator('.analysis-bar')).toHaveCount(0)
  await expect(page.locator('.kpis')).toHaveCount(0)
  await expect(page.getByText('Mais filtros', { exact: true })).toHaveCount(0)
  await page.getByRole('link', { name: 'Ver itens da compra 00001' }).click()
  await expect(page.getByRole('heading', { name: 'Compra 00001', exact: true })).toBeVisible()
  await expect(page.getByText('R$ 100.000,00', { exact: true })).toBeVisible()
  await expect(page.getByText('R$ 0,10', { exact: true }).first()).toBeVisible()
  await page.getByRole('link', { name: item.descricao, exact: true }).click()
  await expect(page.locator('.detail-score-number')).toContainText('0,6910')
  await page.getByRole('link', { name: 'Voltar à consulta', exact: true }).click()
  await expect(page).toHaveURL(new RegExp(`/licitacoes/${PROCESS}`))
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe(EXEC)
})

test('filtros, paginação dos itens e retentativa mantêm resumo da licitação', async ({ page }) => {
  const state = await setup(page)
  await page.goto(`/licitacoes?base_id=${BASE}&execucao_id=${EXEC}`)
  await page.getByLabel('Buscar licitação').fill('Computadores')
  await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
  await expect(page.getByRole('heading', { name: '1 licitação' })).toBeVisible()
  await page.getByRole('button', { name: 'Limpar filtros', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2 licitações' })).toBeVisible()
  await page.goto(`/licitacoes/${PROCESS}?base_id=${BASE}&execucao_id=${EXEC}&tamanho_pagina=1`)
  await page.getByRole('button', { name: 'Próxima', exact: true }).click()
  await expect(page.getByRole('link', { name: otherItem.descricao, exact: true })).toBeVisible()
  await expect(page.getByText('1 de 2 itens importados', { exact: false })).toBeVisible()
  state.fail = true
  await page.getByRole('link', { name: 'Voltar às licitações' }).click()
  await expect(page.getByRole('heading', { name: 'Consulta indisponível' })).toBeVisible()
  state.fail = false
  await page.getByRole('button', { name: 'Tentar novamente', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2 licitações' })).toBeVisible()
})

test('licitações são acessíveis no celular e indicam compra sem itens', async ({ page }) => {
  await setup(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`/licitacoes/${OTHER}?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.getByText('Nenhum item importado nesta compra.', { exact: true })).toBeVisible()
  await expect(page.getByText('Sem medida IF', { exact: true })).toHaveCount(2)
  await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
  const { default: AxeBuilder } = await import('@axe-core/playwright')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

for (const width of [1280, 390]) {
  test(`licitações filtram múltiplas sinalizações e preservam revisão neutra ${width}`, async ({ page }) => {
    const state = await setup(page)
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/licitacoes?base_id=${BASE}&execucao_id=00000000-0000-4000-8000-000000000000&modelo_id=${MODEL}&orgao_id=antigo`)
    await expect(page.getByRole('heading', { name: '2 licitações', exact: true })).toBeVisible()
    const params = new URL(page.url()).searchParams
    expect(params.get('execucao_id')).toBe(EXEC)
    expect(params.has('modelo_id')).toBe(false)
    expect(params.has('orgao_id')).toBe(false)
    const group = page.getByRole('group', { name: 'Sinalização da licitação', exact: true })
    await group.locator('summary').click()
    await expect(group.getByRole('checkbox')).toHaveCount(5)
    await page.getByRole('checkbox', { name: 'Anomalia intermediária', exact: true }).check()
    await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
    await expect(page.getByRole('heading', { name: '1 licitação', exact: true })).toBeVisible()
    await group.locator('summary').click()
    await page.getByRole('checkbox', { name: 'Sem análise disponível', exact: true }).check()
    await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
    await expect(page.getByRole('heading', { name: '2 licitações', exact: true })).toBeVisible()
    expect(new URL(page.url()).searchParams.getAll('sinalizacao')).toEqual(['anomalia_intermediaria', 'sem_analise'])
    await page.reload()
    await group.locator('summary').click()
    await expect(page.getByRole('checkbox', { name: 'Anomalia intermediária', exact: true })).toBeChecked()
    await expect(page.getByRole('checkbox', { name: 'Sem análise disponível', exact: true })).toBeChecked()
    await page.getByRole('button', { name: 'Limpar filtros', exact: true }).click()
    state.reviewFirst = true
    await page.reload()
    const row = page.getByRole('row').filter({ has: page.getByRole('link', { name: 'Compra 00001', exact: true }) })
    await expect(row).toContainText('Requer validação')
    await expect(row).not.toHaveAttribute('data-if-band')
    const { default: AxeBuilder } = await import('@axe-core/playwright')
    expect((await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  })
}
