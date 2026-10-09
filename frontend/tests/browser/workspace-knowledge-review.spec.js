import { test, expect, login, users } from './workspace.fixture.js'

test('platform sidebar opens knowledge review and publishes high-risk article through API boundary', async ({ page, api }) => {
  const article = { articleId: 'KB-HIGH', categoryId: 'CAT-NET', status: 'PENDING_REVIEW', riskLevel: 'HIGH', currentVersionId: 'VER-HIGH', updatedAt: '2026-09-30T09:00:00' }
  const version = { versionId: 'VER-HIGH', versionNo: 1, title: '权限变更安全审核流程', authorId: users.KNOWLEDGE_ADMIN.user_id }
  api.overrides.push(async ({ path, method, reply }) => {
    if (path === '/rag/articles') { await reply({ records: [article], total: 1 }); return true }
    if (path === '/rag/articles/KB-HIGH') { await reply({ article, currentVersion: version, transitions: [] }); return true }
    if (path === '/rag/articles/KB-HIGH/publish' && method === 'POST') {
      article.status = 'PUBLISHED'
      await reply({ indexStatus: 'INDEXED', message: '高风险知识已发布（浏览器测试响应）' }); return true
    }
    return false
  })
  await login(page, api, 'PLATFORM_ADMIN')
  await page.getByRole('menuitem', { name: '知识审核', exact: true }).click()
  await expect(page).toHaveURL(/\/knowledge-admin$/)
  await expect(page.getByRole('heading', { name: '知识库', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '查看详情', exact: true }).click()
  const drawer = page.getByRole('dialog', { name: /知识详情/ })
  await expect(drawer).toContainText('权限变更安全审核流程')
  await expect(drawer).toContainText('高风险')
  await drawer.getByRole('button', { name: '平台复核并发布', exact: true }).click()
  const confirmation = page.getByRole('dialog', { name: '审核通过并发布', exact: true })
  await confirmation.getByRole('textbox').fill('平台管理员已复核权限操作范围')
  await confirmation.getByRole('button', { name: '发布', exact: true }).click()
  await expect(drawer.getByRole('button', { name: '下线', exact: true })).toBeVisible()
  const writes = api.requests.filter(r => r.path === '/rag/articles/KB-HIGH/publish')
  expect(writes).toHaveLength(1)
  expect(writes[0].body).toMatchObject({ changeNote: '平台管理员已复核权限操作范围' })
  expect(writes[0].headers.authorization).toBe('Bearer browser-fixture-token')
})

for (const { role, own } of [{ role: 'KNOWLEDGE_ADMIN', own: false }, { role: 'KNOWLEDGE_ADMIN', own: true }, { role: 'PLATFORM_ADMIN', own: true }]) {
  test(`high-risk publication is blocked for ${role} ${own ? 'article author' : 'non-platform reviewer'}`, async ({ page, api }) => {
    const article = { articleId: 'KB-HIGH', categoryId: 'CAT-NET', status: 'PENDING_REVIEW', riskLevel: 'HIGH', currentVersionId: 'VER-HIGH' }
    api.overrides.push(async ({ path, reply }) => {
      if (path === '/rag/articles') { await reply({ records: [article], total: 1 }); return true }
      if (path === '/rag/articles/KB-HIGH') {
        await reply({ article, currentVersion: { versionId: 'VER-HIGH', title: '高风险审核边界', authorId: own ? users[role].user_id : users.PLATFORM_ADMIN.user_id }, transitions: [] }); return true
      }
      return false
    })
    await login(page, api, role)
    if (role === 'PLATFORM_ADMIN') await page.getByRole('menuitem', { name: '知识审核', exact: true }).click()
    await page.getByRole('button', { name: '查看详情', exact: true }).click()
    const drawer = page.getByRole('dialog', { name: /知识详情/ })
    const label = own ? '不可自审' : '等待平台管理员复核'
    await expect(drawer.getByRole('button', { name: label, exact: true })).toBeDisabled()
    await expect(drawer).toContainText(own ? '你是当前版本的作者，不能自审' : '高风险文章须由平台管理员复核发布')
    expect(api.requests.some(r => r.path.endsWith('/publish'))).toBe(false)
  })
}

test('knowledge administrator has no accounts entry and direct account URL remains blocked', async ({ page, api }) => {
  await login(page, api, 'KNOWLEDGE_ADMIN')
  await expect(page.getByRole('menuitem', { name: '账号管理', exact: true })).toHaveCount(0)
  await page.goto('/accounts')
  await expect(page).toHaveURL(/\/knowledge-admin$/)
  await expect(page.getByRole('heading', { name: '知识库', exact: true })).toBeVisible()
  expect(api.requests.some(r => r.path === '/users/accounts')).toBe(false)
})
