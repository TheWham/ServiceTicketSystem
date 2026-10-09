import { test, expect } from '@playwright/test'

// Explicitly opt in: this GET-only observation uses the actual Vite -> 28080 proxy.
// No page.route interception, no credentials and no backend writes.
test('real login records actual 28080 login-options response', async ({ page }, testInfo) => {
  test.skip(process.env.WORKSPACE_LIVE !== '1', 'Run with WORKSPACE_LIVE=1 to capture the live backend failure')
  const outcomePromise = new Promise(resolve => {
    const matches = request => new URL(request.url()).pathname === '/api/v1/users/login-options'
    const cleanup = () => { page.off('response', onResponse); page.off('requestfailed', onFailed) }
    const onResponse = response => {
      if (!matches(response)) return
      cleanup(); resolve({ response })
    }
    const onFailed = request => {
      if (!matches(request)) return
      cleanup(); resolve({ failure: request.failure()?.errorText || 'request failed', url: request.url() })
    }
    page.on('response', onResponse); page.on('requestfailed', onFailed)
  })
  await page.goto('/login')
  const { response, failure, url } = await outcomePromise
  const observation = response
    ? { url: response.url(), status: response.status(), body: await response.text() }
    : { url, status: null, failure }
  await testInfo.attach('live-login-options-response', { body: JSON.stringify(observation, null, 2), contentType: 'application/json' })
  await expect(page.getByRole('heading', { name: '登录工作台' })).toBeVisible()
  if (failure || response.status() >= 400) {
    await expect(page.getByRole('status')).toContainText('账号列表加载失败')
    await expect(page.getByRole('button', { name: '重新加载' })).toBeVisible()
  } else {
    expect(response.status()).toBe(200)
    await expect(page.getByRole('combobox', { name: '选择已有账号' })).toBeVisible()
  }
  console.log(`Live login-options observation: ${failure || response.status()}; GET only, no business writes`)
  await page.screenshot({ path: testInfo.outputPath(`workspace-live-login-28080-${failure ? 'network-failure' : response.status()}.png`), fullPage: true })
})
