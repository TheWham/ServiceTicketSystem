// Run against Vite: PLAYWRIGHT_MODULE may point to an existing local Playwright install.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')

;(async () => {
  const browser = await chromium.launch({ headless: true })
  try {
    const context = await browser.newContext({ viewport: { width: 1280, height: 1000 } })
    await context.addInitScript(() => {
      localStorage.setItem('mock_user', JSON.stringify({ user_id: 'U1', name: '测试员工', role: 'EMPLOYEE' }))
      localStorage.setItem('auth_token', 'ticket-edit-browser-fixture')
    })
    const ticket = { ticket_id: 'TK-EDIT', creator_id: 'U1', creator_name: '测试员工', nature: 'INCIDENT',
      category_id: 'DISABLED', category_snapshot: '网络/已停用分类', title: '原工单标题', description: '原问题描述',
      impact_description: '本人', urgency_description: '今天', contact: '123', location: '301', asset_id: 'PC01',
      status: 'IN_PROGRESS', priority: 'MEDIUM', created_at: '2026-10-01T01:00:00Z', attachments: ['OLD'] }
    const writes = [], deletes = [], creates = [], drafts = [], errors = [], withdrawals = []
    let failSave = true
    let failWithdraw = true
    await context.route('**/api/v1/**', async route => {
      const req = route.request(), path = new URL(req.url()).pathname
      let data = null
      if (path.endsWith('/tickets/TK-EDIT/withdraw') && req.method() === 'POST') {
        withdrawals.push(path)
        if (failWithdraw) {
          failWithdraw = false
          return route.fulfill({ status: 503, json: { code: 50000, msg: '模拟撤回失败' } })
        }
        ticket.status = 'CANCELLED'
        data = { ticket_id: ticket.ticket_id, status: 'CANCELLED' }
      } else if (path.endsWith('/tickets/TK-EDIT') && req.method() === 'PUT') {
        writes.push(req.postDataJSON())
        if (failSave) {
          failSave = false
          return route.fulfill({ status: 503, json: { code: 50000, msg: '模拟保存失败' } })
        }
        Object.assign(ticket, req.postDataJSON())
      } else if (path.endsWith('/tickets/TK-EDIT')) data = { ticket, flow_logs: [] }
      else if (path.endsWith('/tickets') && req.method() === 'POST') creates.push(req.postDataJSON())
      else if (path.endsWith('/tickets')) data = { list: [ticket], total: 1 }
      else if (path.endsWith('/categories/leaf')) data = []
      else if (path.endsWith('/tickets/attachments/upload')) data = { attachment_id: 'NEW' }
      else if (path.includes('/attachments/') && req.method() === 'DELETE') deletes.push(path)
      else if (path.endsWith('/attachments/OLD/content')) return route.fulfill({ contentType: 'image/png', body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/a9sAAAAASUVORK5CYII=', 'base64') })
      else if (path.includes('/draft') && req.method() !== 'GET') drafts.push(req.postDataJSON())
      else if (path.includes('/sla/')) data = { status: ticket.status === 'CANCELLED' ? 'CANCELLED' : 'RUNNING', remaining_work_seconds: 3600, elapsed_work_seconds: 7200, target_at: '2026-10-09T09:00:00Z' }
      else if (path.endsWith('/notifications')) data = { list: [] }
      else if (path.endsWith('/pending-count')) data = 0
      await route.fulfill({ json: { code: 0, data } })
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    page.setDefaultTimeout(10000)
    await page.goto('http://localhost:5173/employee?tab=create')
    const title = () => page.locator('.el-form-item').filter({ hasText: '工单标题' }).locator('input')
    await title().fill('保留的新工单草稿')
    await page.getByRole('tab', { name: /我的工单/ }).click()
    await page.locator('.ticket-card').click()
    await page.getByRole('dialog').getByText('网络/已停用分类', { exact: true }).waitFor()
    await page.getByRole('button', { name: '重新编辑', exact: true }).click()
    await page.getByRole('button', { name: '取消编辑' }).waitFor()
    assert.equal(await title().inputValue(), '原工单标题')
    assert.equal(await page.getByRole('textbox', { name: '问题类型（不可修改）' }).getAttribute('readonly'), '')
    assert.equal(await page.locator('.el-radio-group input:not([disabled])').count(), 0)
    await page.waitForFunction(() => !document.querySelector('.photo-upload .el-upload')?.classList.contains('is-disabled'))
    await page.locator('.el-upload-list__item').hover()
    await page.locator('.el-upload-list__item-delete').click()
    await page.getByRole('button', { name: '取消编辑' }).click()
    assert.deepEqual(deletes, [])
    await page.getByRole('tab', { name: '提交工单', exact: true }).click()
    assert.equal(await title().inputValue(), '保留的新工单草稿')
    await page.getByRole('tab', { name: /我的工单/ }).click()
    await page.locator('.ticket-card').click()
    await page.getByRole('button', { name: '重新编辑', exact: true }).click()
    await title().fill('修改后的标题')
    await page.waitForFunction(() => !document.querySelector('.photo-upload .el-upload')?.classList.contains('is-disabled'))
    await page.locator('.photo-upload input[type=file]').setInputFiles({ name: 'new-photo.png', mimeType: 'image/png',
      buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/a9sAAAAASUVORK5CYII=', 'base64') })
    await page.waitForFunction(() => document.querySelectorAll('.el-upload-list__item.is-success').length === 2)
    await page.locator('.el-upload-list__item').last().hover()
    await page.locator('.el-upload-list__item-delete').last().click()
    await page.waitForFunction(() => document.querySelectorAll('.el-upload-list__item').length === 1)
    await page.locator('.el-upload-list__item').hover()
    await page.locator('.el-upload-list__item-delete').click()
    await page.getByRole('button', { name: '保存修改', exact: true }).click()
    await page.getByText(/保存失败：模拟保存失败/).waitFor()
    assert.equal(await title().inputValue(), '修改后的标题')
    await page.getByRole('button', { name: '保存修改', exact: true }).click()
    await page.getByRole('dialog').getByRole('heading', { name: '修改后的标题', exact: true }).waitFor()
    assert.equal(writes.length, 2)
    assert.deepEqual(writes[1].attachments, [])
    assert.deepEqual(deletes, ['/api/v1/tickets/attachments/NEW'])
    assert.equal(writes[1].category_id, undefined)
    assert.equal(writes[1].created_at, undefined)
    assert.equal(ticket.created_at, '2026-10-01T01:00:00Z')
    assert.equal(ticket.status, 'IN_PROGRESS')
    assert.deepEqual(creates, [])
    assert.deepEqual(drafts, [])
    assert.deepEqual(errors, [])
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 1000 })
      const gaps = await page.evaluate(() => {
        const actions = document.querySelector('.ticket-detail-actions').getBoundingClientRect()
        const sla = document.querySelector('.sla-card').getBoundingClientRect()
        const flow = document.querySelector('.flow-card').getBoundingClientRect()
        return { before: actions.top - sla.bottom, after: flow.top - actions.bottom,
          overflow: document.documentElement.scrollWidth > innerWidth }
      })
      assert.ok(gaps.before >= 19 && gaps.after >= 19, `Cards have breathing room at ${width}px`)
      assert.equal(gaps.overflow, false)
    }
    await page.getByRole('button', { name: '撤回工单', exact: true }).click()
    await page.getByRole('button', { name: '继续保留', exact: true }).click()
    assert.deepEqual(withdrawals, [])
    await page.getByRole('button', { name: '撤回工单', exact: true }).click()
    await page.getByRole('button', { name: '确认撤回', exact: true }).click()
    await page.getByText('撤回失败：模拟撤回失败', { exact: true }).waitFor()
    assert.equal(ticket.status, 'IN_PROGRESS')
    await page.getByRole('button', { name: '撤回工单', exact: true }).click()
    await page.getByRole('button', { name: '确认撤回', exact: true }).click()
    await page.getByRole('dialog').getByText('本工单已作废并停止计时，内容和流转记录保留存档，平台管理员仍可查看。', { exact: true }).waitFor()
    assert.equal(withdrawals.length, 2)
    assert.equal(await page.getByRole('button', { name: '重新编辑', exact: true }).count(), 0)
    assert.equal(await page.getByRole('button', { name: '撤回工单', exact: true }).count(), 0)
    assert.equal(ticket.title, '修改后的标题')
    assert.equal(ticket.created_at, '2026-10-01T01:00:00Z')
    await page.getByText('工单已撤回，SLA 已停止计时', { exact: true }).waitFor()
    const fs = require('node:fs')
    fs.mkdirSync('../logs/ticket-withdraw', { recursive: true })
    await page.screenshot({ path: '../logs/ticket-withdraw/archive-mobile.png', fullPage: true })
    assert.deepEqual(errors, [])
    console.log('Browser passed: edit regression, desktop/mobile card spacing, withdrawal confirmation/cancel/failure/retry, read-only archive, stopped timer.')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
