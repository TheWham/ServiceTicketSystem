import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/browser',
  outputDir: './test-results/workspace-browser',
  fullyParallel: true,
  workers: 3,
  retries: 0,
  timeout: 30000,
  expect: { timeout: 7000 },
  reporter: [['list'], ['json', { outputFile: './test-results/workspace-browser-results.json' }]],
  use: {
    baseURL: 'http://127.0.0.1:5176',
    browserName: 'chromium',
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { launchOptions: { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } }
      : { channel: 'chrome' }),
    viewport: { width: 1440, height: 1000 },
    locale: 'zh-CN', colorScheme: 'light', reducedMotion: 'reduce',
    screenshot: 'only-on-failure', trace: 'retain-on-failure',
    serviceWorkers: 'block',
  },
  webServer: {
    command: `"${process.execPath}" node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5176 --strictPort`,
    url: 'http://127.0.0.1:5176', reuseExistingServer: false, timeout: 30000,
  },
})
