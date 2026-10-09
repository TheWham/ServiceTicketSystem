import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'

function component(path, api = {}) {
  const source = readFileSync(new URL(`../src/${path}.vue`, import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  const compiled = compileScript(descriptor, { id: 'workspace' })
  const routes = [], notices = []
  const modules = {
    vue: { ...vue, onMounted() {}, onUnmounted() {}, watch() {} },
    'vue-router': { useRouter: () => ({ push: route => routes.push(route) }), useRoute: () => ({ query: {} }) },
    'element-plus': { ElMessage: Object.fromEntries(['success', 'warning', 'error'].map(key => [key, text => notices.push(text)])) },
    '@element-plus/icons-vue': {},
    '../api/index.js': { userApi: api, notificationApi: api, categoryApi: api },
    '../stores/user.js': { useUserStore: () => ({ setLogin() {} }) },
    '../api/consultation.js': { consultationApi: api, CONSULTATION_STATUS: {}, REFUSAL_REASON: {}, TERMINAL_STATUS: ['RESOLVED', 'CLOSED', 'CONVERTED_TO_TICKET'] }
  }
  const code = compiled.content.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g,
    (_, names, name) => `const {${names}} = modules[${JSON.stringify(name)}]`).replace('export default', 'return')
  const state = new Function('modules', 'setInterval', 'clearInterval', code)(modules, () => 1, () => {}).setup({}, { expose() {}, emit() {} })
  return { state, routes, notices }
}

test('canonical login sends the typed account and lands knowledge administrators in their workspace', async () => {
  let body
  const { state: c, routes } = component('views/LoginView', {
    login: async data => { body = data; return { data: { user: { name: '知识管理员', role: 'KNOWLEDGE_ADMIN' }, token: 'jwt' } } }
  })
  c.selectedId.value = ' K1 '
  c.password.value = 'secret123'
  await c.doLogin()
  assert.deepEqual(body, { user_id: 'K1', password: 'secret123' })
  assert.deepEqual(routes, ['/knowledge-admin'])
})

test('failed account options are retryable without inventing an account or blocking manual login', async () => {
  let unavailable = true
  const { state: c } = component('views/LoginView', {
    loginOptions: async () => { if (unavailable) throw new Error('服务暂不可用'); return { data: [{ user_id: 'U1', name: '同事' }] } }
  })
  c.selectedId.value = 'U2'
  await c.loadOptions()
  assert.match(c.optionsError.value, /服务暂不可用/)
  assert.deepEqual(c.users.value, [])
  assert.equal(c.optionsLoading.value, false)
  unavailable = false
  await c.loadOptions()
  assert.equal(c.optionsError.value, '')
  assert.equal(c.users.value[0].user_id, 'U1')
  assert.equal(c.selectedId.value, 'U2')
})

test('human transfer uses the current category catalog and distinguishes its outage from an empty catalog', async () => {
  let failing = false
  const { state: c } = component('components/ConsultationChat', {
    leaf: async () => { if (failing) throw new Error('分类服务不可用'); return { data: [
      { category_id: 'REMOTE_NEW', name: '当前远端分类', status: 'ACTIVE' },
      { category_id: 'OLD', name: '停用分类', status: 'DISABLED' }
    ] } }
  })
  await c.loadTransferCategories()
  assert.deepEqual(c.categories.value.map(item => item.id), ['REMOTE_NEW'])
  failing = true
  await c.loadTransferCategories()
  assert.equal(c.categories.value.length, 0)
  assert.match(c.categoriesError.value, /分类服务不可用/)
  assert.equal(c.categoriesLoading.value, false)
})

test('repeated login submit sends only one in-flight request', async () => {
  let finish, calls = 0
  const { state: c } = component('views/LoginView', {
    login: () => { calls++; return new Promise(resolve => { finish = resolve }) }
  })
  c.selectedId.value = 'U1'
  c.password.value = 'secret123'
  const first = c.doLogin()
  const second = c.doLogin()
  const count = calls
  finish({ data: { user: { role: 'EMPLOYEE' }, token: 'jwt' } })
  assert.equal(count, 1)
  await Promise.all([first, second])
  assert.equal(c.loading.value, false)
})

test('password forms send canonical backend fields', async () => {
  const sent = []
  const { state: login } = component('views/LoginView', { forgotPassword: async body => sent.push(body) })
  Object.assign(login.forgotForm.value, { user_id: 'U1', name: '同事', employee_no: 'E1', new_password: 'newpass123' })
  await login.doForgot()
  const { state: password } = component('components/ChangePasswordDialog', { changePassword: async body => sent.push(body) })
  Object.assign(password.form.value, { oldPassword: 'oldpass123', newPassword: 'newpass123', confirm: 'newpass123' })
  await password.submit()
  assert.deepEqual(sent, [
    { user_id: 'U1', name: '同事', employee_no: 'E1', new_password: 'newpass123' },
    { old_password: 'oldpass123', new_password: 'newpass123' }
  ])
})

test('consultation list failure cannot silently create a replacement conversation', async () => {
  let creates = 0, unavailable = true
  const { state: c } = component('components/ConsultationChat', {
    list: async () => { if (unavailable) throw new Error('咨询记录加载失败'); return { items: [] } },
    create: async () => { creates++; return { sessionId: 'S1', status: 'AI_ACTIVE' } }
  })
  await c.autoStart()
  assert.equal(creates, 0)
  assert.equal(c.session.value, null)
  assert.match(c.bootError.value, /咨询记录加载失败/)
  unavailable = false
  await c.autoStart()
  assert.equal(creates, 1)
  assert.equal(c.bootError.value, '')
  assert.equal(c.session.value.sessionId, 'S1')
})

test('IME Enter does not send an unfinished consultation message', async () => {
  let sends = 0
  const { state: c } = component('components/ConsultationChat', { aiMessage: async () => { sends++; return {} } })
  c.session.value = { sessionId: 'S1', status: 'AI_ACTIVE' }
  c.draft.value = '网络'
  await c.send({ isComposing: true })
  assert.equal(sends, 0)
  assert.equal(c.draft.value, '网络')
})

test('notification errors preserve previous notifications and clear after retry', async () => {
  let unavailable = true
  const { state: c } = component('components/NotificationBell', {
    list: async () => { if (unavailable) throw new Error('通知暂不可用'); return { data: { list: [] } } }
  })
  c.list.value = [{ notification_id: 'N1', title: '待处理' }]
  await c.loadList()
  assert.equal(c.list.value.length, 1)
  assert.match(c.listError.value, /通知暂不可用/)
  unavailable = false
  await c.loadList()
  assert.equal(c.listError.value, '')
  assert.deepEqual(c.list.value, [])
})

test('engineer list errors retain the current queue and expose a retryable failure', async () => {
  let unavailable = true
  const { state: c } = component('components/EngineerConsultation', {
    list: async () => { if (unavailable) throw new Error('列表暂不可用'); return { items: [] } }
  })
  c.sessions.value = [{ session_id: 'S1', status: 'HUMAN_ACTIVE' }]
  await c.loadSessions()
  assert.equal(c.sessions.value.length, 1)
  assert.match(c.listError.value, /列表暂不可用/)
  unavailable = false
  await c.loadSessions()
  assert.deepEqual(c.sessions.value, [])
  assert.equal(c.listError.value, '')
})

test('engineer IME confirmation does not send a partial reply', async () => {
  let sends = 0
  const { state: c } = component('components/EngineerConsultation', { sendMessage: async () => { sends++ } })
  c.selected.value = { session_id: 'S1', status: 'HUMAN_ACTIVE' }
  c.draft.value = '请检查'
  await c.send({ isComposing: true })
  assert.equal(sends, 0)
  assert.equal(c.draft.value, '请检查')
})
