import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '../src/stores/user.js'

function storage(seed = {}) {
  const values = new Map(Object.entries(seed))
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, String(value)), removeItem: key => values.delete(key) }
}

test('stored legacy knowledge-admin role is normalized on reload', () => {
  globalThis.localStorage = storage({ mock_user: JSON.stringify({ user_id: 'K1', role: 'KB_ADMIN', name: 'Legacy' }) })
  setActivePinia(createPinia())
  const store = useUserStore()
  assert.equal(store.currentUser.role, 'KNOWLEDGE_ADMIN')
  assert.equal(store.currentUser.display_name, 'Legacy')
  assert.equal(store.isSupervisor, false)
})

test('canonical account fields and explicit disabled status survive login', () => {
  globalThis.localStorage = storage()
  setActivePinia(createPinia())
  const store = useUserStore()
  store.setLogin({ user_id: 'K1', role: 'KNOWLEDGE_ADMIN', display_name: 'Canonical', name: 'Legacy', enabled: false, status: 'ACTIVE' }, 'jwt')
  assert.equal(store.currentUser.display_name, 'Canonical')
  assert.equal(store.currentUser.enabled, false)
  assert.equal(store.token, 'jwt')
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
    createRouter, () => ({}), () => ({ userId: 'U1', currentUser: { role } }), {})
  return { config, guard }
}

test('knowledge admins have an independent landing page without account-management access', async () => {
  const { config, guard } = routerFor('KNOWLEDGE_ADMIN')
  const home = config.routes.find(route => route.path === '/knowledge')
  assert.equal(home?.meta.role, 'KNOWLEDGE_ADMIN')
  for (const path of ['/supervisor', '/accounts']) {
    const route = config.routes.find(route => route.path === path)
    let redirected
    await guard(route, {}, value => { redirected = value })
    assert.equal(redirected, '/knowledge')
  }
})

test('platform admins retain account management and ticket notification deep links', async () => {
  const { config, guard } = routerFor('PLATFORM_ADMIN')
  const account = config.routes.find(route => route.path === '/accounts')
  let redirected = 'not called'
  await guard(account, {}, value => { redirected = value })
  assert.equal(redirected, undefined)
  const notification = config.routes.find(route => route.path === '/tickets/:id')
  assert.deepEqual(notification.redirect({ params: { id: 'T1' } }), { path: '/supervisor', query: { ticket: 'T1' } })
})
