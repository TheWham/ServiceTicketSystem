import test from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '../src/stores/user.js'
import { requireCurrentIdentity, requireCurrentAccounts } from '../src/auth/identity.js'
function setup(values = {}) {
  const storage = new Map(Object.entries(values))
  globalThis.localStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) }
  setActivePinia(createPinia())
  return { store: useUserStore(), storage }
}
const employee = { user_id: 'E1', name: 'Current employee', role: 'EMPLOYEE', status: 'ACTIVE' }
test('old gateway accounts are rejected, not translated into current roles', () => {
  for (const role of ['supervisor', 'employee', 'KB_ADMIN', 'SUPER_ADMIN']) {
    assert.throws(() => requireCurrentIdentity({ ...employee, role }), /不受支持/)
  }
  assert.throws(() => requireCurrentAccounts({ data: [{ ...employee, role: 'supervisor' }] }), /不受支持/)
})
test('old cached user cannot grant a role before current server identity is verified', () => {
  const { store, storage } = setup({ mock_user: JSON.stringify({ ...employee, role: 'supervisor' }), mock_user_id: 'OLD', auth_token: 'token' })
  assert.equal(store.currentUser, null)
  assert.equal(store.userId, '')
  assert.equal(storage.has('mock_user'), false)
  assert.equal(storage.has('mock_user_id'), false)
})
test('session restoration replaces stale identity with current server identity and is deduplicated', async () => {
  const { store } = setup({ auth_token: 'token' })
  let calls = 0
  const fetchMe = async () => { calls++; return { data: employee } }
  await Promise.all([store.restoreSession(fetchMe), store.restoreSession(fetchMe)])
  assert.equal(calls, 1)
  assert.equal(store.userId, 'E1')
  assert.equal(store.currentUser.role, 'EMPLOYEE')
})
test('temporary identity failure blocks protected identity but retains credentials for retry', async () => {
  const { store, storage } = setup({ auth_token: 'token' })
  await store.restoreSession(async () => { throw new Error('Identity service unavailable') })
  assert.equal(store.currentUser, null)
  assert.equal(storage.get('auth_token'), 'token')
  assert.match(store.sessionError, /Identity service unavailable/)
  await store.restoreSession(async () => ({ data: employee }))
  assert.equal(store.currentUser.user_id, 'E1')
  assert.equal(store.sessionError, '')
})
test('definitive identity rejection clears credentials rather than retrying stale privileges', async () => {
  const { store, storage } = setup({ auth_token: 'old-token' })
  await store.restoreSession(async () => { const error = new Error('登录已失效'); error.status = 401; throw error })
  assert.equal(store.currentUser, null)
  assert.equal(storage.has('auth_token'), false)
  assert.match(store.sessionError, /登录已失效/)
})
test('a late identity response cannot sign a logged-out user back in', async () => {
  const { store } = setup({ auth_token: 'token' })
  let resolve
  const restoring = store.restoreSession(() => new Promise(yes => { resolve = yes }))
  store.logout()
  resolve({ data: employee })
  await restoring
  assert.equal(store.currentUser, null)
  assert.equal(store.token, '')
})
