import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '../src/stores/user.js'

function storage(seed = {}) {
  const values = new Map(Object.entries(seed))
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, String(value)), removeItem: key => values.delete(key) }
}

test('cached legacy knowledge-admin identity is discarded on reload', () => {
  globalThis.localStorage = storage({ mock_user: JSON.stringify({ user_id: 'K1', role: 'KB_ADMIN', display_name: 'Legacy', enabled: false }) })
  setActivePinia(createPinia())
  const store = useUserStore()
  assert.equal(store.currentUser, null)
  assert.equal(store.userId, '')
  assert.equal(store.isPlatformAdmin, false)
})

test('canonical name and status override conflicting legacy fields during login', () => {
  globalThis.localStorage = storage()
  setActivePinia(createPinia())
  const store = useUserStore()
  store.setLogin({ user_id: 'K1', role: 'KNOWLEDGE_ADMIN', name: 'Canonical', display_name: 'Legacy', status: 'ACTIVE', enabled: false,
    employee_no: 'E1', department_id: 'D_IT', identity_source: 'LOCAL' }, 'jwt')
  assert.equal(store.currentUser.name, 'Canonical')
  assert.equal(store.currentUser.status, 'ACTIVE')
  assert.equal(store.currentUser.employee_no, 'E1')
  assert.equal(store.currentUser.department_id, 'D_IT')
  assert.equal(store.currentUser.identity_source, 'LOCAL')
  assert.equal(store.currentUser.display_name, undefined)
  assert.equal(store.currentUser.enabled, undefined)
  assert.equal(store.token, 'jwt')
  assert.equal(localStorage.getItem('mock_user'), null)
})

test('even a canonical cached identity must be revalidated on reload', () => {
  globalThis.localStorage = storage({ mock_user: JSON.stringify({
    user_id: 'U1', name: 'Current', display_name: 'Previous', status: 'ACTIVE', enabled: false,
    employee_no: 'E1', department_id: 'D_IT', identity_source: 'LOCAL', role: 'EMPLOYEE'
  }) })
  setActivePinia(createPinia())
  const store = useUserStore()
  assert.equal(store.currentUser, null)
})

function routerFor(role) {
  const source = readFileSync(new URL('../src/router/index.js', import.meta.url), 'utf8')
  let config, guard
  const createRouter = value => {
    config = value
    return { beforeEach: fn => { guard = fn } }
  }
  const code = source.replace(/^import .*$/gm, '').replace('export default router', 'return router')
  new Function('createRouter', 'createWebHistory', 'useUserStore', 'userApi', code)(
    createRouter, () => ({}), () => ({ userId: 'U1', currentUser: { role }, restoreSession: async () => {} }), {})
  return { config, guard }
}

test('knowledge admins have an independent landing page without account-management access', async () => {
  const { config, guard } = routerFor('KNOWLEDGE_ADMIN')
  const home = config.routes.find(route => route.path === '/knowledge-admin')
  assert.ok(home?.meta.role.includes('KNOWLEDGE_ADMIN'))
  for (const path of ['/dispatch', '/accounts']) {
    const route = config.routes.find(route => route.path === path)
    let redirected
    await guard(route, {}, value => { redirected = value })
    assert.equal(redirected, '/knowledge-admin')
  }
})

test('platform admins retain account management and ticket notification deep links', async () => {
  const { config, guard } = routerFor('PLATFORM_ADMIN')
  const account = config.routes.find(route => route.path === '/accounts')
  let redirected = 'not called'
  await guard(account, {}, value => { redirected = value })
  assert.equal(redirected, undefined)
  const notification = config.routes.find(route => route.path === '/tickets/:id')
  const destination = notification.redirect({ params: { id: 'T1' } })
  assert.deepEqual(destination, { path: '/login', query: { ticket: 'T1' } })
  await guard(destination, {}, value => { redirected = value })
  assert.deepEqual(redirected, { path: '/dispatch', query: { ticket: 'T1' } })
  await guard(config.routes.find(route => route.path === '/knowledge-admin'), {}, value => { redirected = value })
  assert.equal(redirected, undefined, 'platform admins need the high-risk knowledge review route')
})

function accountComponent(path, userApi = {}) {
  const source = readFileSync(new URL(`../src/${path}.vue`, import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  const compiled = compileScript(descriptor, { id: 'account' })
  const modules = {
    vue: { ...vue, onMounted() {}, onUnmounted() {} },
    'vue-router': { useRouter: () => ({ push() {} }), useRoute: () => ({ query: {} }) },
    'element-plus': { ElMessage: { success() {}, warning() {}, error() {} } },
    '@element-plus/icons-vue': {},
    '../api/index.js': { userApi },
    '../stores/user.js': { useUserStore: () => ({ setLogin() {}, currentUser: { name: 'Current', role: 'EMPLOYEE' } }) }
  }
  const code = compiled.content.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g,
    (_, names, path) => `const {${names}} = modules[${JSON.stringify(path)}]`).replace('export default', 'return')
  return new Function('modules', code)(modules).setup({}, { expose() {}, emit() {} })
}

test('account creation sends PRD names and snake_case fields', async () => {
  const sent = []
  const c = accountComponent('views/AccountManageView', {
    createAccount: async body => sent.push({ ...body }), listAccounts: async () => ({ data: [] })
  })
  Object.assign(c.createForm.value, { user_id: 'U1', employee_no: 'E1', name: 'Current', department_id: 'D_IT', role_code: 'EMPLOYEE', password: 'secret123' })
  await c.doCreate()
  assert.deepEqual(sent, [{ user_id: 'U1', employee_no: 'E1', name: 'Current', department_id: 'D_IT', role_code: 'EMPLOYEE', password: 'secret123' }])
})

test('login and forgotten-password requests use canonical identity fields', async () => {
  const sent = []
  const c = accountComponent('views/LoginView', {
    login: async body => { sent.push({ ...body }); return { data: { user: { user_id: 'U1', role: 'EMPLOYEE', status: 'ACTIVE' }, token: 'jwt' } } },
    forgotPassword: async body => sent.push({ ...body })
  })
  c.selectedId.value = 'U1'
  c.password.value = 'secret123'
  await c.doLogin()
  Object.assign(c.forgotForm.value, { user_id: 'U1', employee_no: 'E1', name: 'Current', new_password: 'changed123' })
  await c.doForgot()
  assert.deepEqual(sent, [{ user_id: 'U1', password: 'secret123' }, { user_id: 'U1', name: 'Current', employee_no: 'E1', new_password: 'changed123' }])
})

test('password changes and account resets send snake_case passwords', async () => {
  const sent = []
  const c = accountComponent('components/ChangePasswordDialog', { changePassword: async body => sent.push(body) })
  Object.assign(c.form.value, { oldPassword: 'secret123', newPassword: 'changed123', confirm: 'changed123' })
  await c.submit()
  const a = accountComponent('views/AccountManageView', { resetPassword: async (id, body) => sent.push({ id, ...body }) })
  a.openReset({ user_id: 'U1', name: 'Current' })
  a.resetPwd.value = 'reset123'
  await a.doReset()
  assert.deepEqual(sent, [{ old_password: 'secret123', new_password: 'changed123' }, { id: 'U1', new_password: 'reset123' }])
})
