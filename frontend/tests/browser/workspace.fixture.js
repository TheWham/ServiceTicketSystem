import { test as base, expect } from '@playwright/test'

export const users = {
  EMPLOYEE: { user_id: 'employee-test', name: '林晓', role: 'EMPLOYEE', status: 'ACTIVE', employee_no: 'E100', department: '设计部' },
  ENGINEER: { user_id: 'engineer-test', name: '陈工', role: 'ENGINEER', status: 'ACTIVE', employee_no: 'E200', department: 'IT' },
  PLATFORM_ADMIN: { user_id: 'admin-test', name: '周管理员', role: 'PLATFORM_ADMIN', status: 'ACTIVE', employee_no: 'E300', department: 'IT' },
  KNOWLEDGE_ADMIN: { user_id: 'knowledge-test', name: '许知识', role: 'KNOWLEDGE_ADMIN', status: 'ACTIVE', employee_no: 'E400', department: 'IT' },
}
export const ticket = {
  ticket_id: 'TK-1001', title: '会议室投屏无法连接', nature: 'INCIDENT', category_id: 'CAT-NET', category_name: '网络连接',
  creator_id: 'employee-test', creator_name: '林晓', assignee_id: 'engineer-test', assignee_name: '陈工',
  status: 'IN_PROGRESS', priority: 'MEDIUM', created_at: '2026-09-30T09:00:00+08:00',
  description: '会议室无线投屏无法连接，重启设备后仍然失败。', impact_description: '项目组无法进行会议演示', urgency_description: '下午客户会议需要使用', location: '三楼会议室',
}
export const categories = [{ category_id: 'CAT-NET', name: '网络连接', ticket_nature: 'INCIDENT', status: 'ACTIVE' }]
export function gate() { let release; const promise = new Promise(resolve => { release = resolve }); return { promise, release } }

export const test = base.extend({
  api: async ({ page }, use) => {
    const state = {
      identity: users.EMPLOYEE, loginIdentity: null, options: Object.values(users),
      tickets: [structuredClone(ticket), { ...ticket, ticket_id: 'TK-1002', title: '打印机卡纸', status: 'ASSIGNED' }],
      requests: [], unknown: [], errors: [], overrides: [],
    }
    page.on('pageerror', error => state.errors.push(error.message))
    await page.route(url => url.pathname.startsWith('/api/'), async route => {
      const request = route.request(), url = new URL(request.url())
      const path = url.pathname.replace('/api/v1', ''), method = request.method()
      const record = { path, method, query: Object.fromEntries(url.searchParams), headers: request.headers(), body: request.postDataJSON() }
      state.requests.push(record)
      const reply = (data, status = 200) => route.fulfill({ status, json: { code: path.startsWith('/consultations') ? 'SUCCESS' : 0, data } })
      for (const override of [...state.overrides].reverse()) {
        if (await override({ route, request, path, method, record, reply })) return
      }
      if (path === '/users/login-options') return reply(state.options)
      if (path === '/users/login') return reply({ token: 'browser-fixture-token', user: state.loginIdentity || state.identity })
      if (path === '/users/me') return reply(state.identity)
      if (path === '/notifications/pending-count') return reply(0)
      if (path === '/notifications') return reply({ list: [], total: 0 })
      if (path === '/categories/leaf') return reply(categories)
      if (path === '/users/drafts') return reply(null)
      if (path === '/users/accounts' && method === 'GET') return reply(Object.values(users))
      if (path === '/users' && method === 'GET') return reply([users.ENGINEER])
      if (path === '/tickets' && method === 'GET') {
        const list = state.tickets.filter(t => !record.query.status || t.status === record.query.status)
        return reply({ list, total: list.length })
      }
      if (path === '/tickets' && method === 'POST') {
        const created = { ...ticket, ...record.body, ticket_id: 'TK-1003', status: 'NEW', assignee_name: null }
        state.tickets.unshift(created)
        return reply(created)
      }
      if (/^\/tickets\/[^/]+$/.test(path)) return reply({ ticket: state.tickets.find(t => t.ticket_id === path.split('/').pop()), flow_logs: [] })
      if (path.startsWith('/sla/')) return reply({ status: 'RUNNING', remaining_work_seconds: 14400, target_work_seconds: 28800, elapsed_work_seconds: 14400, priority_snapshot: 'MEDIUM' })
      if (path === '/consultations' && method === 'GET') return reply({ items: [], total: 0 })
      if (path === '/consultations' && method === 'POST') return reply({ sessionId: 'CONS-100', status: 'AI_ACTIVE' })
      if (path === '/consultations/CONS-100') return reply({ session_id: 'CONS-100', status: 'AI_ACTIVE' })
      if (path === '/consultations/CONS-100/messages') return reply({ items: [], total: 0 })
      if (path === '/consultations/CONS-100/ai-messages') return reply({ interactionId: 'AI-100', replyType: 'ANSWER', answerText: '请在系统网络设置中确认已连接办公网络。', citations: [{ versionId: 'VER-100', title: '办公网络连接指南', snippet: '打开网络设置，确认办公网络连接状态。' }], suggestTransfer: false })
      if (path === '/rag/traces') return reply([])
      if (path === '/rag/articles') return reply({ records: [{ articleId: 'KB-100', categoryId: 'CAT-NET', status: 'PUBLISHED', riskLevel: 'LOW', currentVersionId: 'VER-100', updatedAt: '2026-09-30T09:00:00' }], total: 1 })
      state.unknown.push(`${method} ${path}`)
      return route.fulfill({ status: 501, json: { code: 501, msg: `Unconfigured browser fixture: ${method} ${path}` } })
    })
    await use(state)
    expect(state.unknown, 'Every API must be explicitly isolated; no backend writes').toEqual([])
    expect(state.errors, 'No uncaught browser errors').toEqual([])
  },
})
export { expect }
export async function login(page, api, role = 'EMPLOYEE') {
  api.identity = users[role]
  await page.goto('/login')
  await page.getByLabel('账号', { exact: true }).fill(api.identity.user_id)
  await page.getByLabel('密码', { exact: true }).fill('BrowserTest123')
  await page.getByRole('button', { name: '登录工作台', exact: true }).click()
  const home = { EMPLOYEE: '/employee', ENGINEER: '/engineer', PLATFORM_ADMIN: '/dispatch', KNOWLEDGE_ADMIN: '/knowledge-admin' }[role]
  await expect(page).toHaveURL(new RegExp(home + '$'))
  expect(api.requests.find(r => r.path === '/users/login').body).toEqual({ user_id: api.identity.user_id, password: 'BrowserTest123' })
}
