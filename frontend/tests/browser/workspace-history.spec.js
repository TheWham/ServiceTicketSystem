import { test, expect, login } from './workspace.fixture.js'

test('consultation restored history includes the 101st message through transport pagination', async ({ page, api }) => {
  const messages = Array.from({ length: 101 }, (_, index) => ({
    message_id: `MSG-${index + 1}`, sender_type: 'EMPLOYEE', content: `历史消息第${index + 1}条`, sent_at: '2026-09-30T09:00:00+08:00',
  }))
  api.overrides.push(async ({ path, record, reply }) => {
    if (path === '/consultations') { await reply({ items: [{ session_id: 'CONS-100', status: 'AI_ACTIVE' }], total: 1 }); return true }
    if (path === '/consultations/CONS-100/messages') {
      const page = Number(record.query.page || 1)
      await reply({ items: messages.slice((page - 1) * 100, page * 100), total: 101 }); return true
    }
    return false
  })
  await login(page, api)
  await page.getByRole('button', { name: '智能客服 / 转人工', exact: true }).click()
  const log = page.getByRole('log', { name: '咨询消息', exact: true })
  await expect(log).toContainText('历史消息第1条')
  await expect(log).toContainText('历史消息第101条')
  expect(api.requests.filter(r => r.path === '/consultations/CONS-100/messages').map(r => r.query.page)).toContain('2')
  expect(api.requests.some(r => r.path === '/consultations' && r.method === 'POST')).toBe(false)
})
