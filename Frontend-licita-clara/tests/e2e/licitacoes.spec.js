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
    if (path === `/analises/execucoes/${EXEC}/itens/${ITEM}`) return done({ dados: [{ cobertura: [], resultados: [{ id: 'score-1', modelo_id: MODEL, algoritmo: 'isolation_forest', resultado_item_id: item.resultados[0].id, indice_experimental: '100' }] }] })
    if (!path.startsWith('/visao/licitacoes')) return false
    if (state.fail) { await error('Consulta temporariamente indisponível.'); return true }
    const rows = [
      { id: PROCESS, processo: item.processo, descricao: item.processo.objeto, valor_homologado: '100000.00000001', score_medio: '100.000', maior_score: '100.000', itens_com_score: 1, itens_importados: 2, itens_analise_parcial: 0, status_analise: 'parcial', valores_itens_importados: { valor_homologado: '0.10000001', resultados_sem_total: 0 } },
      { id: OTHER, processo: { ...item.processo, id: OTHER, numero_compra: '00002', objeto: 'Computadores' }, descricao: 'Computadores', valor_homologado: null, score_medio: null, maior_score: null, itens_com_score: 0, itens_importados: 0, itens_analise_parcial: 0, status_analise: 'nao_analisados', valores_itens_importados: { valor_homologado: null, resultados_sem_total: 0 } },
    ]
    const context = { base_id: BASE, execucao_id: EXEC, modelo_id: null, resumo: { licitacoes: 2, com_score: 1, itens_importados: 2, itens_com_score: 1 } }
    const paginate = entries => {
      const page = Number(url.searchParams.get('pagina') || 1), size = Number(url.searchParams.get('tamanho_pagina') || 20)
      return { dados: entries.slice((page-1)*size,page*size), pagina: page, tamanho_pagina: size, total: entries.length, total_paginas: Math.ceil(entries.length/size) }
    }
    if (path === '/visao/licitacoes') return done({ ...context, ...paginate(rows.filter(r => r.descricao.toLowerCase().includes((url.searchParams.get('busca') || '').toLowerCase()))) })
    const row = rows.find(r => path.endsWith('/'+r.id))
    if (!row) { await error('Licitação não encontrada nesta base.',404); return true }
    const items = [item, otherItem].map((r,i) => ({ ...r, resultados: r.resultados.filter(e=>!e.cancelado), valor_homologado: r.valor_homologado_item, resultados_sem_total: 0, indice_experimental: i === 0 ? '100' : null, status_analise: i === 0 ? 'analisados' : 'nao_analisados', resultados_analisados: i === 0 ? 1 : 0, motivos: {} }))
    return done({ ...context, licitacao: row, itens: paginate(row.id === PROCESS ? items : []) })
  } })
  return state
}

test('licitações mostram média, maior score, cobertura e abrem itens e análise correta', async ({ page }) => {
  await setup(page)
  await page.goto('/licitacoes')
  await expect(page.getByRole('heading', { name: 'Licitações Sinalizadas', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: '1 de 2 itens importados', exact: false })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: 'Score médio', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Sem Score', exact: true })).toHaveCount(2)
  await page.getByRole('link', { name: 'Ver itens da compra 00001' }).click()
  await expect(page.getByRole('heading', { name: 'Compra 00001', exact: true })).toBeVisible()
  await expect(page.getByText('R$ 100.000,00000001', { exact: true })).toBeVisible()
  await expect(page.getByText('R$ 0,10000001', { exact: true }).first()).toBeVisible()
  await page.getByRole('link', { name: item.descricao, exact: true }).click()
  await expect(page.locator('.detail-score-number')).toContainText('100')
  await page.getByRole('link', { name: 'Voltar à consulta', exact: true }).click()
  await expect(page).toHaveURL(new RegExp(`/licitacoes/${PROCESS}`))
  expect(new URL(page.url()).searchParams.get('execucao_id')).toBe(EXEC)
})

test('filtros, paginação dos itens e retentativa mantêm resumo da licitação', async ({ page }) => {
  const state = await setup(page)
  await page.goto(`/licitacoes?base_id=${BASE}&execucao_id=${EXEC}`)
  await page.getByLabel('Buscar licitação, item ou fornecedor').fill('Computadores')
  await page.getByRole('button', { name: 'Aplicar filtros', exact: true }).click()
  await expect(page.getByRole('heading', { name: '1 licitação(ões) encontrada(s)' })).toBeVisible()
  await page.getByRole('button', { name: 'Limpar filtros', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2 licitação(ões) encontrada(s)' })).toBeVisible()
  await page.goto(`/licitacoes/${PROCESS}?base_id=${BASE}&execucao_id=${EXEC}&tamanho_pagina=1`)
  await page.getByRole('button', { name: 'Próxima', exact: true }).click()
  await expect(page.getByRole('link', { name: otherItem.descricao, exact: true })).toBeVisible()
  await expect(page.getByText('1 de 2 itens importados', { exact: false })).toBeVisible()
  state.fail = true
  await page.getByRole('link', { name: 'Voltar às licitações' }).click()
  await expect(page.getByRole('heading', { name: 'Consulta indisponível' })).toBeVisible()
  state.fail = false
  await page.getByRole('button', { name: 'Tentar novamente', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2 licitação(ões) encontrada(s)' })).toBeVisible()
})

test('licitações são acessíveis no celular e indicam compra sem itens', async ({ page }) => {
  await setup(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`/licitacoes/${OTHER}?base_id=${BASE}&execucao_id=${EXEC}`)
  await expect(page.getByText('Nenhum item importado nesta compra.', { exact: true })).toBeVisible()
  await expect(page.getByText('Sem Score', { exact: true })).toHaveCount(2)
  await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
  const { default: AxeBuilder } = await import('@axe-core/playwright')
  expect((await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
