import { test, expect, users } from './workspace.fixture.js'

for (const failure of ['http500', 'network']) {
  test(`temporary me ${failure} keeps token, blocks protected data and recovers through retry`, async ({ page, api }) => {
    api.identity = users.PLATFORM_ADMIN
    let fail = true
    api.overrides.push(async ({ path, route }) => {
      if (path !== '/users/me' || !fail) return false
      if (failure === 'network') await route.abort('failed')
      else await route.fulfill({ status: 500, json: { code: 500, msg: '身份核验服务暂不可用' } })
      return true
    })
    await page.addInitScript(() => localStorage.setItem('auth_token', 'recoverable-token'))
    await page.goto('/accounts')
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByRole('button', { name: '重新核验登录身份' })).toBeVisible()
    expect(await page.evaluate(() => localStorage.getItem('auth_token'))).toBe('recoverable-token')
    await expect(page.getByRole('menuitem', { name: '账号管理' })).toHaveCount(0)
    expect(api.requests.some(r => r.path === '/users/accounts' || r.path === '/tickets')).toBe(false)
    fail = false
    await page.getByRole('button', { name: '重新核验登录身份' }).click()
    await expect(page).toHaveURL(/\/dispatch$/)
    await expect(page.getByRole('heading', { name: '工单调度', exact: true })).toBeVisible()
    expect(await page.evaluate(() => localStorage.getItem('auth_token'))).toBe('recoverable-token')
  })
}

test('restored invalid canonical identity clears token', async ({ page, api }) => {
  api.identity = { ...users.PLATFORM_ADMIN, role: 'supervisor' }
  await page.addInitScript(() => localStorage.setItem('auth_token', 'invalid-identity-token'))
  await page.goto('/accounts')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('alert')).toContainText('不受支持的身份')
  expect(await page.evaluate(() => localStorage.getItem('auth_token'))).toBeNull()
  await expect(page.getByRole('button', { name: '重新核验登录身份' })).toHaveCount(0)
})
