import { defineConfig } from '@playwright/test'

const port = Number(process.env.FRONTEND_TEST_PORT || 4197)
export default defineConfig({
  testDir: './tests/e2e',
  workers: 1,
  timeout: 30000,
  reporter: 'list',
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR || './test-results',
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    headless: true,
    ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}),
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'mock', testMatch: ['consultas.spec.js', 'visao.spec.js'] },
    { name: 'live', testMatch: 'live.spec.js' },
  ],
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${port} --strictPort`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: false,
    env: { API_PROXY_TARGET: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000' },
  },
})
