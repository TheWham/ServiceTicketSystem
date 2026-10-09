import { test, expect, login, users, ticket, gate } from './workspace.fixture.js'

test('employee flat list searches only loaded page and clears empty results', async ({ page, api }) => {
  await login(page, api)
  await expect(page.locator('ul.ticket-list > li')).toHaveCount(2)
  await expect(page.getByText('搜索仅匹配当前页已加载的工单', { exact: false })).toBeVisible()
  const search = page.getByRole('textbox', { name: '搜索本页工单' })
  await search.fill('投屏')
  await expect(page.locator('ul.ticket-list > li')).toHaveCount(1)
  await search.fill('仅存在于下一页的工单')
  await expect(page.getByRole('heading', { name: '本页没有匹配的工单' })).toBeVisible()
  await expect(page.getByText('还没有工单', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: '清除搜索' }).click()
  await expect(page.locator('ul.ticket-list > li')).toHaveCount(2)
  expect(api.requests.filter(r => r.path === '/tickets')).toHaveLength(1)
})

test('ticket details open by keyboard, close and browser back restore list', async ({ page, api }) => {
  await login(page, api)
  const row = page.getByRole('button', { name: '查看工单 TK-1001 会议室投屏无法连接', exact: true })
  await row.focus(); await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/ticket=TK-1001/)
  await expect(page.getByRole('dialog')).toContainText(ticket.description)
  await page.getByRole('button', { name: '返回列表' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page).not.toHaveURL(/ticket=/)
  await row.click()
  await expect(page.getByRole('dialog')).toContainText(ticket.impact_description)
  await page.goBack()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(row).toBeVisible()
})

async function createTicket(page) {
  await page.getByRole('button', { name: '提交新工单', exact: true }).click()
  const submit = page.getByRole('button', { name: '提交工单', exact: true })
  await expect(submit).toBeDisabled()
  await page.getByPlaceholder('一句话概括问题，如：市场部打印机无法连接').fill('浏览器验证创建工单')
  await page.getByText('选择末级分类', { exact: true }).click()
  await page.getByRole('option', { name: '网络连接' }).click()
  await page.getByPlaceholder('请详细描述问题：何时开始、报错原文、已尝试的操作...').fill('今天上午开始无法访问办公网络，重启设备无效。')
  await page.getByPlaceholder('影响了哪些人/业务？如：本人无法打印 / 全部门网络中断').fill('影响项目组工作')
  await page.getByPlaceholder('为什么紧急？如：下午有重要会议需投屏').fill('下午需要交付项目')
  await expect(submit).toBeEnabled(); await submit.click()
  await expect(page.getByRole('heading', { name: '我的工单', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: /查看工单 TK-1003/ })).toBeVisible()
}
test('create validates required fields and sends actual form payload to boundary', async ({ page, api }) => {
  await login(page, api); await createTicket(page)
  const writes = api.requests.filter(r => r.path === '/tickets' && r.method === 'POST')
  expect(writes).toHaveLength(1)
  expect(writes[0].body).toMatchObject({ title: '浏览器验证创建工单', category_id: 'CAT-NET', nature: 'INCIDENT', source_session_id: null })
  expect(writes[0].headers.authorization).toBe('Bearer browser-fixture-token')
})
test('create transmits its idempotency key', async ({ page, api }) => {
  await login(page, api); await createTicket(page)
  expect(api.requests.find(r => r.path === '/tickets' && r.method === 'POST').headers['idempotency-key']).toBeTruthy()
})

test('engineer queue filters status, searches and opens assigned ticket', async ({ page, api }) => {
  await login(page, api, 'ENGINEER')
  await expect(page.getByRole('heading', { name: '工程师工作台' })).toBeVisible()
  await expect(page.getByRole('button', { name: '接单', exact: true })).toBeVisible()
  await page.getByRole('textbox', { name: '搜索本页工单' }).fill('打印机')
  await expect(page.locator('li.ticket-row')).toHaveCount(1)
  await page.getByRole('button', { name: '查看工单 TK-1002 打印机卡纸', exact: true }).click()
  await expect(page.getByRole('dialog')).toContainText('接单需确认影响范围与紧急程度')
  expect(api.requests.find(r => r.path === '/tickets').query.mine_or_pool).toBe(users.ENGINEER.user_id)
})

test('platform administrator lands on dispatch and can search accounts', async ({ page, api }) => {
  await login(page, api, 'PLATFORM_ADMIN')
  await expect(page.getByRole('heading', { name: '工单调度', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'TK-1001', exact: true })).toBeVisible()
  await page.getByRole('menuitem', { name: '账号管理' }).click()
  await expect(page).toHaveURL(/\/accounts$/)
  await page.getByRole('textbox', { name: '搜索账号' }).fill('陈工')
  await expect(page.locator('.el-table__body-wrapper')).toContainText('engineer-test')
  await expect(page.locator('.el-table__body-wrapper')).not.toContainText('employee-test')
  await page.getByRole('button', { name: '新建账号' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByRole('dialog').getByRole('button', { name: '取消' }).click()
})

test('knowledge library loads published article lifecycle list', async ({ page, api }) => {
  await login(page, api, 'KNOWLEDGE_ADMIN')
  await expect(page.getByRole('heading', { name: '知识库', exact: true })).toBeVisible()
  await expect(page.getByText('KB-100', { exact: true })).toBeVisible()
  await expect(page.getByText('VER-100', { exact: true })).toBeVisible()
  await page.getByRole('textbox', { name: '搜索本页文章' }).fill('NOT-FOUND')
  await expect(page.getByText('本页没有匹配的文章', { exact: true })).toBeVisible()
  await page.getByRole('textbox', { name: '搜索本页文章' }).fill('')
  await page.locator('label').filter({ has: page.getByRole('radio', { name: '已发布', exact: true }) }).click()
  await expect(page.getByRole('radio', { name: '已发布', exact: true })).toBeChecked()
  await expect.poll(() => api.requests.filter(r => r.path === '/rag/articles').at(-1)?.query.status).toBe('PUBLISHED')
})

test('consultation drawer creates real UI session and renders grounded answer', async ({ page, api }) => {
  await login(page, api)
  await page.getByRole('button', { name: '智能客服 / 转人工' }).click()
  const drawer = page.getByRole('dialog', { name: '智能客服', exact: true })
  await expect(drawer.getByRole('heading', { name: 'IT 服务助手' })).toBeVisible()
  await drawer.getByPlaceholder('描述你遇到的问题，回车发送').fill('办公网络无法连接应该如何检查？')
  await drawer.getByRole('button', { name: '发送', exact: true }).click()
  await expect(drawer.getByRole('log')).toContainText('请在系统网络设置中确认已连接办公网络。')
  await expect(drawer.getByRole('button', { name: '查看知识依据：办公网络连接指南' })).toBeVisible()
  const sent = api.requests.find(r => r.path.endsWith('/ai-messages'))
  expect(sent.body.message).toBe('办公网络无法连接应该如何检查？')
  expect(sent.headers['x-request-id']).toBeTruthy(); expect(sent.headers['idempotency-key']).toBeTruthy()
  await page.keyboard.press('Escape')
  await expect(drawer).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '我的工单', exact: true })).toBeVisible()
})

test('command Ctrl+K arrow navigation Enter opens create', async ({ page, api }) => {
  await login(page, api)
  await page.keyboard.press('Control+k')
  const input = page.getByRole('combobox', { name: '搜索页面和操作' })
  await expect(input).toBeFocused()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('option', { name: /提交工单/ })).toHaveAttribute('aria-selected', 'true')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: '提交新工单', exact: true })).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
})
test('command Escape returns focus to original control', async ({ page, api }) => {
  await login(page, api)
  const search = page.getByRole('textbox', { name: '搜索本页工单' })
  await search.focus(); await page.keyboard.press('Control+k')
  await page.getByRole('combobox', { name: '搜索页面和操作' }).fill('不存在的页面')
  await expect(page.getByText('没有找到相关页面，换个关键词试试。')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(search).toBeFocused()
})

test('command IME composition Enter does not navigate before normal Enter', async ({ page, api }) => {
  await login(page, api)
  await page.keyboard.press('Control+k')
  const input = page.getByRole('combobox', { name: '搜索页面和操作' })
  await input.fill('提交工单')
  await input.dispatchEvent('keydown', { key: 'Enter', code: 'Enter', isComposing: true, bubbles: true, cancelable: true })
  await expect(page.getByRole('dialog', { name: '快速前往', exact: true })).toBeVisible()
  await expect(page).toHaveURL(/\/employee$/)
  await expect(input).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: '提交新工单', exact: true })).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
})

test('light dark themes persist and produce screenshots', async ({ page, api }, testInfo) => {
  await login(page, api)
  await expect(page.locator('li.ticket-row')).toHaveCount(2)
  await page.screenshot({ path: testInfo.outputPath('workspace-light.png'), fullPage: true })
  await page.getByRole('button', { name: '切换深色主题', exact: true }).click()
  await expect(page.locator('html')).toHaveClass(/dark/)
  await page.screenshot({ path: testInfo.outputPath('workspace-dark.png'), fullPage: true })
  await page.reload()
  await expect(page.getByRole('heading', { name: '我的工单', exact: true })).toBeVisible()
  await expect(page.locator('html')).toHaveClass(/dark/)
  expect(api.requests.some(r => r.path === '/users/me')).toBe(true)
  await page.getByRole('button', { name: '切换浅色主题', exact: true }).click()
  await expect(page.locator('html')).not.toHaveClass(/dark/)
})

test('mobile navigation create and detail stay inside viewport', async ({ page, api }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, api)
  await expect(page.locator('li.ticket-row')).toHaveCount(2)
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)
  expect(await overflow()).toBe(false)
  await page.screenshot({ path: testInfo.outputPath('workspace-mobile.png'), fullPage: true })
  await page.getByRole('button', { name: '打开导航' }).click()
  await page.getByRole('menuitem', { name: '提交工单', exact: true }).click()
  await expect(page.getByRole('heading', { name: '提交新工单', exact: true })).toBeVisible()
  expect(await overflow()).toBe(false)
  await page.getByRole('button', { name: '返回我的工单' }).click()
  await page.getByRole('button', { name: /查看工单 TK-1001/ }).click()
  await expect(page.getByRole('dialog')).toContainText(ticket.description)
  expect(await overflow()).toBe(false)
  const bounds = await page.getByRole('dialog').boundingBox()
  expect(bounds.x).toBeGreaterThanOrEqual(-1); expect(bounds.width).toBeLessThanOrEqual(391)
})

test('browser offline banner retains loaded list and clears on reconnect', async ({ page, context, api }) => {
  await login(page, api)
  await expect(page.locator('li.ticket-row')).toHaveCount(2)
  await context.setOffline(true)
  await expect(page.getByRole('status').filter({ hasText: '网络已断开' })).toBeVisible()
  await expect(page.locator('li.ticket-row')).toHaveCount(2)
  await context.setOffline(false)
  await expect(page.getByText('网络已断开。已显示的内容仍可查看，请联网后重试。')).toHaveCount(0)
})

test('ticket loading error and retry have distinct visible states', async ({ page, api }) => {
  const pending = gate(); let fail = true
  api.overrides.push(async ({ path, method, route }) => {
    if (path !== '/tickets' || method !== 'GET' || !fail) return false
    await pending.promise
    await route.fulfill({ status: 503, json: { code: 503, msg: '工单服务维护中' } }); return true
  })
  await login(page, api)
  await expect(page.getByRole('status').filter({ hasText: '正在加载工单…' })).toBeVisible()
  pending.release()
  await expect(page.getByRole('alert').filter({ hasText: '工单暂时无法加载' })).toContainText('工单服务维护中')
  await expect(page.getByText('还没有工单', { exact: true })).toHaveCount(0)
  fail = false; await page.getByRole('button', { name: '重试', exact: true }).click()
  await expect(page.locator('li.ticket-row')).toHaveCount(2)
})

test('legacy lowercase supervisor login options are rejected and retry recovers', async ({ page, api }) => {
  api.options = [{ user_id: 'legacy', name: '旧主管', role: 'supervisor', status: 'ACTIVE' }]
  await page.goto('/login')
  await expect(page.getByRole('status')).toContainText('不受支持的身份')
  await expect(page.getByRole('combobox', { name: '选择已有账号' })).toHaveCount(0)
  api.options = Object.values(users)
  await page.getByRole('button', { name: '重新加载' }).click()
  await expect(page.getByRole('combobox', { name: '选择已有账号' })).toBeVisible()
})

for (const bad of [{ role: 'supervisor', status: 'ACTIVE' }, { role: 'EMPLOYEE', status: 'DISABLED' }]) {
  test(`login rejects identity ${bad.role}/${bad.status}`, async ({ page, api }) => {
    api.loginIdentity = { ...users.EMPLOYEE, ...bad }
    await page.goto('/login')
    await page.getByLabel('账号', { exact: true }).fill('employee-test')
    await page.getByLabel('密码', { exact: true }).fill('BrowserTest123')
    await page.getByRole('button', { name: '登录工作台', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText(bad.status === 'DISABLED' ? '此账号当前不可用' : '不受支持的身份')
    await expect(page).toHaveURL(/\/login$/)
    expect(await page.evaluate(() => localStorage.getItem('auth_token'))).toBeNull()
  })
}

test('startup ignores cached administrator and awaits server me before routes', async ({ page, api }) => {
  const pending = gate()
  api.overrides.push(async ({ path, reply }) => { if (path !== '/users/me') return false; await pending.promise; await reply(users.EMPLOYEE); return true })
  await page.addInitScript(admin => {
    localStorage.setItem('auth_token', 'stale-token')
    localStorage.setItem('mock_user', JSON.stringify(admin)); localStorage.setItem('mock_user_id', admin.user_id)
  }, users.PLATFORM_ADMIN)
  await page.goto('/accounts')
  await expect(page.getByRole('status')).toContainText('正在核验登录身份')
  expect(api.requests.some(r => r.path === '/users/accounts')).toBe(false)
  await expect(page.getByRole('menuitem', { name: '账号管理' })).toHaveCount(0)
  pending.release()
  await expect(page).toHaveURL(/\/employee$/)
  await expect(page.getByRole('heading', { name: '我的工单', exact: true })).toBeVisible()
  const cache = await page.evaluate(() => ({ user: localStorage.getItem('mock_user'), id: localStorage.getItem('mock_user_id'), token: localStorage.getItem('auth_token') }))
  expect(cache).toEqual({ user: null, id: null, token: 'stale-token' })
  expect(api.requests.find(r => r.path === '/users/me').headers.authorization).toBe('Bearer stale-token')
})

test('invalid restored token clears cached auth and shows login failure reason', async ({ page, api }) => {
  api.overrides.push(async ({ path, route }) => { if (path !== '/users/me') return false; await route.fulfill({ status: 401, json: { code: 401, msg: '登录凭证已过期' } }); return true })
  await page.addInitScript(() => localStorage.setItem('auth_token', 'expired-token'))
  await page.goto('/accounts')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('alert')).toContainText('登录凭证已过期')
  expect(await page.evaluate(() => localStorage.getItem('auth_token'))).toBeNull()
  expect(api.requests.some(r => r.path === '/users/accounts')).toBe(false)
})

for (const role of ['EMPLOYEE', 'ENGINEER', 'PLATFORM_ADMIN']) {
  test(`cold notification /tickets/T1 restores ${role} before opening detail`, async ({ page, api }) => {
    api.identity = users[role]
    api.tickets = [{ ...ticket, ticket_id: 'T1' }]
    await page.addInitScript(() => localStorage.setItem('auth_token', 'notification-token'))
    await page.goto('/tickets/T1')
    const home = { EMPLOYEE: 'employee', ENGINEER: 'engineer', PLATFORM_ADMIN: 'dispatch' }[role]
    await expect(page).toHaveURL(new RegExp('/' + home + '\\?ticket=T1$'))
    await expect(page.getByRole('dialog')).toContainText(ticket.description)
    const me = api.requests.findIndex(r => r.path === '/users/me')
    const detail = api.requests.findIndex(r => r.path === '/tickets/T1')
    expect(me).toBeGreaterThanOrEqual(0); expect(detail).toBeGreaterThan(me)
  })
}

test('cold notification without token retains ticket across genuine login form', async ({ page, api }) => {
  api.tickets = [{ ...ticket, ticket_id: 'T1' }]
  await page.goto('/tickets/T1')
  await expect(page).toHaveURL(/\/login\?ticket=T1$/)
  await page.getByLabel('账号', { exact: true }).fill(users.EMPLOYEE.user_id)
  await page.getByLabel('密码', { exact: true }).fill('BrowserTest123')
  await page.getByRole('button', { name: '登录工作台', exact: true }).click()
  await expect(page).toHaveURL(/\/employee\?ticket=T1$/)
  await expect(page.getByRole('dialog')).toContainText(ticket.description)
})

test('consultation transfer loads ACTIVE API category choices', async ({ page, api }) => {
  await login(page, api)
  await page.getByRole('button', { name: '智能客服 / 转人工' }).click()
  const drawer = page.getByRole('dialog', { name: '智能客服', exact: true })
  await expect(drawer.getByRole('heading', { name: 'IT 服务助手' })).toBeVisible()
  const count = api.requests.filter(r => r.path === '/categories/leaf').length
  await drawer.getByRole('button', { name: '转人工', exact: true }).click()
  const transfer = page.getByRole('dialog', { name: '转人工咨询', exact: true })
  await expect(transfer.getByRole('radio', { name: /网络连接/ })).toBeVisible()
  await expect.poll(() => api.requests.filter(r => r.path === '/categories/leaf').length).toBeGreaterThan(count)
  await transfer.locator('label').filter({ has: page.getByRole('radio', { name: /网络连接/ }) }).click()
  await expect(transfer.getByRole('radio', { name: /网络连接/ })).toBeChecked()
  await expect(transfer.getByRole('button', { name: '确认转人工' })).toBeEnabled()
  await transfer.getByRole('button', { name: '取消', exact: true }).click()
  await expect(transfer).toHaveCount(0)
})

test('login options HTTP 500 shows failure and retry instead of empty success', async ({ page, api }, testInfo) => {
  let fail = true
  api.overrides.push(async ({ path, route }) => {
    if (path !== '/users/login-options' || !fail) return false
    await route.fulfill({ status: 500, json: { code: 500, msg: '账号服务暂不可用（浏览器测试注入）' } }); return true
  })
  await page.goto('/login')
  await expect(page.getByRole('status')).toContainText('账号列表加载失败')
  await expect(page.getByText('暂无可选账号，可直接输入账号登录。')).toHaveCount(0)
  await page.screenshot({ path: testInfo.outputPath('workspace-fixture-login-500.png'), fullPage: true })
  fail = false
  await page.getByRole('button', { name: '重新加载' }).click()
  await expect(page.getByRole('combobox', { name: '选择已有账号' })).toBeVisible()
})

test('dispatch category filter sends selected canonical category identifier', async ({ page, api }) => {
  await login(page, api, 'PLATFORM_ADMIN')
  await page.getByText('全部分类', { exact: true }).click()
  await page.getByRole('option', { name: '网络连接', exact: true }).click()
  await expect.poll(() => api.requests.filter(r => r.path === '/tickets').at(-1)?.query.category).toBe('CAT-NET')
})
