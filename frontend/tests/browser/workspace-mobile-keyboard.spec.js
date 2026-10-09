import { test, expect, login } from './workspace.fixture.js'

test('mobile navigation hides closed links, traps Tab and restores focus after Escape or backdrop', async ({ page, api }, testInfo) => {
  await page.addInitScript(() => {
    window.__workspaceFocusEvents = []
    const describe = el => el instanceof Element ? `${el.tagName}.${el.className}[${el.getAttribute('aria-label') || ''}]` : String(el)
    for (const type of ['focusin', 'focusout', 'pointerdown', 'pointerup', 'click']) {
      document.addEventListener(type, event => window.__workspaceFocusEvents.push({
        type, target: describe(event.target), related: describe(event.relatedTarget), active: describe(document.activeElement),
        navOpen: !!document.querySelector('.nav-open'), time: Math.round(performance.now()),
      }), true)
    }
  })
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, api)
  const nav = page.locator('aside.workspace-nav')
  const trigger = page.getByRole('button', { name: '打开导航', exact: true })
  await expect(nav).toBeHidden()
  await expect(page.getByRole('menuitem', { name: '提交工单', exact: true })).toHaveCount(0)
  await trigger.focus()
  await page.keyboard.press('Tab')
  expect(await page.evaluate(() => !!document.activeElement.closest('aside.workspace-nav'))).toBe(false)

  await trigger.click()
  const close = nav.getByRole('button', { name: '关闭导航', exact: true })
  try { await expect(close).toBeFocused() } catch (error) {
    const diagnostic = await page.evaluate(() => ({
      active: document.activeElement.outerHTML.slice(0, 600), documentFocused: document.hasFocus(),
      closeVisibility: getComputedStyle(document.querySelector('.mobile-nav-close')).visibility,
      closeInertAncestor: document.querySelector('.mobile-nav-close').closest('[inert]')?.className,
      events: window.__workspaceFocusEvents,
      setupNavMatches: document.querySelector('#app').__vue_app__?._instance?.setupState?.navRef === document.querySelector('aside.workspace-nav'),
      templateNavMatches: document.querySelector('#app').__vue_app__?._instance?.refs?.navRef === document.querySelector('aside.workspace-nav'),
      setupMobileNav: document.querySelector('#app').__vue_app__?._instance?.setupState?.mobileNav,
    }))
    console.log('Mobile focus diagnostics:', JSON.stringify(diagnostic))
    await testInfo.attach('focus-diagnostics', { contentType: 'application/json', body: JSON.stringify(diagnostic, null, 2) })
    throw error
  }
  await expect(page.locator('.workspace-body')).toHaveAttribute('inert', '')
  await page.keyboard.press('Shift+Tab')
  await expect(nav.getByRole('button', { name: '账号信息与修改密码', exact: true })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(close).toBeFocused()
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Tab')
    expect(await page.evaluate(() => !!document.activeElement.closest('aside.workspace-nav'))).toBe(true)
  }
  await page.keyboard.press('Escape')
  await expect(nav).toBeHidden()
  await expect(trigger).toBeFocused()
  await expect(page.locator('.workspace-body')).not.toHaveAttribute('inert')

  await trigger.click()
  await expect(close).toBeFocused()
  // Visible backdrop area to the right of the 240px navigation panel.
  await page.locator('.nav-backdrop').click({ position: { x: 360, y: 300 } })
  await expect(nav).toBeHidden()
  await expect(trigger).toBeFocused()
})

test('mobile profile closes navigation before opening usable password dialog', async ({ page, api }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, api)
  await page.getByRole('button', { name: '打开导航', exact: true }).click()
  const nav = page.locator('aside.workspace-nav')
  await nav.getByRole('button', { name: '账号信息与修改密码', exact: true }).click()
  await expect(nav).toBeHidden()
  await expect(page.locator('.workspace-body')).not.toHaveAttribute('inert')
  const dialog = page.getByRole('dialog', { name: '修改密码', exact: true })
  await expect(dialog).toBeVisible()
  await dialog.getByPlaceholder('请输入当前密码').fill('BrowserTest123')
  await expect(dialog.getByPlaceholder('请输入当前密码')).toBeFocused()
  await page.keyboard.press('Tab')
  expect(await page.evaluate(() => !!document.activeElement.closest('[role="dialog"]'))).toBe(true)
  await dialog.getByRole('button', { name: '取消', exact: true }).click()
  await expect(dialog).toHaveCount(0)
})

test('resizing open mobile navigation to desktop clears inert and leaves content usable', async ({ page, api }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, api)
  await page.getByRole('button', { name: '打开导航', exact: true }).click()
  await expect(page.locator('.workspace-body')).toHaveAttribute('inert', '')
  await page.setViewportSize({ width: 1100, height: 844 })
  await expect(page.locator('.workspace-body')).not.toHaveAttribute('inert')
  await expect(page.locator('.nav-backdrop')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '打开导航', exact: true })).toHaveCount(0)
  await page.getByRole('textbox', { name: '搜索本页工单' }).fill('投屏')
  await expect(page.locator('li.ticket-row')).toHaveCount(1)
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('aside.workspace-nav')).toBeHidden()
})

test('command Escape preserves open mobile navigation and returns focus to search trigger', async ({ page, api }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, api)
  await page.getByRole('button', { name: '打开导航', exact: true }).click()
  const nav = page.locator('aside.workspace-nav')
  const search = nav.getByRole('button', { name: /快速前往/ })
  await search.click()
  await expect(page.getByRole('combobox', { name: '搜索页面和操作' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(nav).toBeVisible()
  await expect(page.locator('.workspace-body')).toHaveAttribute('inert', '')
  await expect(search).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(nav).toBeHidden()
  await expect(page.getByRole('button', { name: '打开导航', exact: true })).toBeFocused()
})
