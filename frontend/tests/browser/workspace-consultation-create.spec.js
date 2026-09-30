import { test, expect, login } from './workspace.fixture.js'

test('consultation startup failure still opens ticket create form', async ({ page, api }) => {
  api.overrides.push(async ({ path, route }) => {
    if (path !== '/consultations') return false
    await route.fulfill({ status: 503, json: { code: 'SERVICE_UNAVAILABLE', message: '咨询服务暂不可用' } }); return true
  })
  await login(page, api)
  await page.getByRole('button', { name: '智能客服 / 转人工' }).click()
  const drawer = page.getByRole('dialog', { name: '智能客服', exact: true })
  await expect(drawer.getByRole('alert')).toContainText('咨询服务暂不可用')
  await drawer.getByRole('button', { name: '提交工单', exact: true }).click()
  await expect(page).toHaveURL(/\/employee\?view=create$/)
  await expect(page.getByRole('heading', { name: '提交新工单', exact: true })).toBeVisible()
  await expect(drawer).toHaveCount(0)
})

test('closed consultation historical ticket entry opens fresh create form without old session', async ({ page, api }) => {
  api.overrides.push(async ({ path, reply }) => {
    if (path === '/consultations') { await reply({ items: [{ session_id: 'CONS-100', status: 'HUMAN_ACTIVE' }], total: 1 }); return true }
    if (path === '/consultations/CONS-100') { await reply({ session_id: 'CONS-100', status: 'CLOSED' }); return true }
    if (path === '/consultations/CONS-100/messages') {
      await reply({ items: [{ message_id: 'ENTRY-1', sender_type: 'ENGINEER', content: '[提交工单入口]', sent_at: '2026-09-30T09:00:00' }], total: 1 }); return true
    }
    return false
  })
  await login(page, api)
  await page.getByRole('button', { name: '智能客服 / 转人工' }).click()
  const drawer = page.getByRole('dialog', { name: '智能客服', exact: true })
  await expect(drawer).toContainText('本次对话已结束')
  await drawer.getByRole('button', { name: '前往提交工单', exact: true }).click()
  await expect(page).toHaveURL(/\/employee\?view=create$/)
  await expect(page.getByRole('heading', { name: '提交新工单', exact: true })).toBeVisible()
  expect(api.requests.some(r => r.path.endsWith('/ticket-draft'))).toBe(false)
})

test('active consultation ticket entry opens create form and preserves session prefill', async ({ page, api }) => {
  api.overrides.push(async ({ path, reply }) => {
    if (path !== '/consultations/CONS-100/ticket-draft') return false
    await reply({ title: '咨询预填网络问题', description: '办公网络持续无法连接，已联系服务助手。', category_id: 'CAT-NET', convert_allowed: true }); return true
  })
  await login(page, api)
  await page.getByRole('button', { name: '智能客服 / 转人工' }).click()
  const drawer = page.getByRole('dialog', { name: '智能客服', exact: true })
  await drawer.getByRole('button', { name: '提交工单', exact: true }).click()
  await expect(page).toHaveURL(/view=create/)
  await expect(page).toHaveURL(/session=CONS-100/)
  await expect(page.getByRole('heading', { name: '提交新工单', exact: true })).toBeVisible()
  await expect(page.getByPlaceholder('一句话概括问题，如：市场部打印机无法连接')).toHaveValue('咨询预填网络问题')
})
