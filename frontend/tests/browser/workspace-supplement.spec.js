import { test, expect, login, ticket } from './workspace.fixture.js'

test('employee supplies requested information, retains text on failure and refreshes detail on success', async ({ page, api }) => {
  api.tickets = [{ ...ticket, status: 'PENDING_SUPPLEMENT' }]
  let fail = true
  api.overrides.push(async ({ path, method, route, reply }) => {
    if (path !== '/tickets/TK-1001/actions' || method !== 'POST') return false
    if (fail) await route.fulfill({ status: 503, json: { code: 503, msg: '补充信息暂时未保存，请重试' } })
    else {
      api.tickets[0].status = 'IN_PROGRESS'
      await reply({ ticket_id: 'TK-1001', status: 'IN_PROGRESS' })
    }
    return true
  })
  await login(page, api)
  await page.getByRole('button', { name: '查看工单 TK-1001 会议室投屏无法连接', exact: true }).click()
  const drawer = page.getByRole('dialog')
  const submit = drawer.getByRole('button', { name: '提交补充信息', exact: true })
  const input = drawer.getByRole('textbox', { name: '补充内容', exact: true })
  await expect(submit).toBeDisabled()
  await input.fill('重启后错误代码仍为 NET-101，其他会议室网络正常。')
  await submit.click()
  await expect(page.getByRole('alert').filter({ hasText: '补充信息暂时未保存，请重试' })).toBeVisible()
  await expect(input).toHaveValue('重启后错误代码仍为 NET-101，其他会议室网络正常。')
  fail = false
  await expect(submit).toBeEnabled()
  await submit.click()
  await expect(drawer.getByRole('heading', { name: '补充信息', exact: true })).toHaveCount(0)
  await expect(drawer).toContainText('处理中')
  const actions = api.requests.filter(r => r.path === '/tickets/TK-1001/actions')
  expect(actions).toHaveLength(2)
  expect(actions[1].body).toEqual({ action: 'supply_info', remark: '重启后错误代码仍为 NET-101，其他会议室网络正常。' })
})
