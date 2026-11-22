import { test, expect } from '@playwright/test'
import { mockApi } from './fixtures.js'

test('primeiro acesso mostra espera e se recupera sem exigir recarregar a página', async ({ page }) => {
  let calls = 0
  await mockApi(page, { handler: async ({ path, send }) => {
    if (path !== '/base/status' || ++calls > 2) return false
    await send({ erro: { mensagem: 'Serviço iniciando' } }, 503)
    return true
  } })
  await page.goto('/ranking')
  await expect(page.getByText('Conectando ao serviço. O primeiro acesso pode levar até 90 segundos.', { exact: true })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '2 produtos' })).toBeVisible({ timeout: 15000 })
  expect(calls).toBeGreaterThanOrEqual(3)
})

test('base inválida mostra erro imediatamente mesmo com espera de inicialização habilitada', async ({ page }) => {
  await mockApi(page)
  await page.goto('/ranking?base_id=inexistente')
  await expect(page.getByRole('heading', { name: 'Registro não encontrado' })).toBeVisible()
})
