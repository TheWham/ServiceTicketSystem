import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { renderToString } from '@vue/server-renderer'
import ElementPlus, { ID_INJECTION_KEY, ZINDEX_INJECTION_KEY } from 'element-plus'
import * as icons from '@element-plus/icons-vue'

// Compile the actual page and render its UI. Only child panels and external
// services are replaced; Vue and Element Plus use their real implementations.
function page(file, role = 'EMPLOYEE', path = '/employee', inlineTemplate = true) {
  const store = { currentUser: { role, name: '测试用户' }, isEmployee: role === 'EMPLOYEE', logout() {} }
  const destinations = []
  const child = { render: () => null }
  const modules = {
    vue: { ...vue, onMounted() {}, onUnmounted() {} }, 'vue-router': { useRoute: () => ({ path, query: {} }), useRouter: () => ({ push: value => destinations.push(value) }) },
    'element-plus': ElementPlus, '@element-plus/icons-vue': icons,
  }
  const { descriptor } = parse(readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8'))
  const compiled = compileScript(descriptor, { id: file, inlineTemplate })
  const dependency = name => modules[name] || (name.endsWith('/stores/user.js')
    ? { useUserStore: () => store } : name.endsWith('.vue') ? child : {})
  const code = compiled.content
    .replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g,
      (_, names, name) => `const {${names.replace(/\s+as\s+/g, ':')}} = dependency(${JSON.stringify(name)})`)
    .replace(/import\s+(\w+)\s+from\s*['"]([^'"]+)['"]/g,
      (_, binding, name) => `const ${binding} = dependency(${JSON.stringify(name)})`)
    .replace('export default', 'return')
  const component = new Function('dependency', 'localStorage', 'document', code)(dependency,
    { getItem() {}, setItem() {} }, { documentElement: { classList: { toggle() {} } } })
  const app = vue.createSSRApp(component)
  app.provide(ID_INJECTION_KEY, { prefix: 100, current: 0 })
  app.provide(ZINDEX_INJECTION_KEY, { current: 0 })
  app.use(ElementPlus)
  app.component('router-view', child)
  app.component('router-link', { props: ['to'], template: '<a><slot /></a>' })
  return { app, destinations, component }
}

test('employee layout exposes the chat button and intelligent support menu', async () => {
  const html = await renderToString(page('App.vue').app)
  assert.ok(html.includes('title="智能客服 / 转人工"'), 'employee chat launcher is missing')
  const menuItems = html.match(/<li\b[^>]*role="menuitem"[^>]*>[\s\S]*?<\/li>/g) || []
  assert.ok(menuItems.some(item => item.includes('智能客服')), 'intelligent support menu is missing')
})

test('login and non-employee layouts do not expose employee chat', async () => {
  for (const [role, path] of [['EMPLOYEE', '/login'], ['ENGINEER', '/engineer'], ['KNOWLEDGE_ADMIN', '/knowledge-admin']]) {
    const html = await renderToString(page('App.vue', role, path).app)
    assert.doesNotMatch(html, /title="智能客服 \/ 转人工"/)
  }
})

test('engineer workbench exposes the current consultation entry alongside ticket search', async () => {
  const html = await renderToString(page('views/EngineerView.vue', 'ENGINEER', '/engineer').app)
  assert.ok(html.includes('当前咨询'), 'engineer consultation entry is missing')
  assert.ok(html.includes('搜索工单号'), 'existing ticket search must remain available')
})

test('support menu opens the drawer and account switching closes it', () => {
  const { component, destinations } = page('App.vue', 'EMPLOYEE', '/employee', false)
  const state = component.setup({}, { expose() {} })
  assert.equal(state.consultOpen.value, false)
  state.onMenuSelect('consultation')
  assert.equal(state.consultOpen.value, true)
  assert.equal(destinations.length, 0, 'opening support must keep the current workbench')
  state.onUserCommand('logout')
  assert.equal(state.consultOpen.value, false)
  assert.deepEqual(destinations, ['/login'])
})
