import test from 'node:test'
import assert from 'node:assert/strict'

const navigation = await import('../src/utils/navigation.js').catch(() => ({}))

test('role home and label support the canonical knowledge role and legacy alias', () => {
  assert.equal(typeof navigation.roleHome, 'function')
  assert.equal(navigation.roleHome('KNOWLEDGE_ADMIN'), '/knowledge-admin')
  assert.equal(navigation.roleHome('KB_ADMIN'), '/knowledge-admin')
  assert.equal(navigation.roleLabel('KNOWLEDGE_ADMIN'), '知识库管理员')
  assert.equal(navigation.roleHome('employee'), '/employee')
  assert.equal(navigation.roleHome('unknown'), '/login')
})

test('employee navigation separates create and list even though they share a route', () => {
  assert.equal(typeof navigation.activeNavigation, 'function')
  const links = navigation.navigationFor('EMPLOYEE')
  assert.deepEqual(links.map(item => item.id), ['consultation', 'create', 'list'])
  assert.equal(navigation.activeNavigation('EMPLOYEE', { path: '/employee', query: {} }), 'create')
  assert.equal(navigation.activeNavigation('EMPLOYEE', { path: '/employee', query: { tab: 'list' } }), 'list')
  assert.equal(navigation.activeNavigation('EMPLOYEE', { path: '/employee', query: { ticket: 'T1' } }), 'list')
  assert.equal(navigation.activeNavigation('EMPLOYEE', { path: '/consultation', query: {} }), 'consultation')
})

test('navigation stays within each role and supports query-selected knowledge and engineering views', () => {
  assert.equal(typeof navigation.navigationFor, 'function')
  assert.equal(navigation.navigationFor('ENGINEER').some(item => item.to.path === '/accounts'), false)
  assert.equal(navigation.navigationFor('KNOWLEDGE_ADMIN').some(item => item.to.path === '/accounts'), false)
  assert.equal(navigation.activeNavigation('ENGINEER', { path: '/engineer', query: { view: 'completed' } }), 'completed')
  assert.equal(navigation.activeNavigation('KNOWLEDGE_ADMIN', { path: '/knowledge-admin', query: { tab: 'lifecycle' } }), 'lifecycle')
  assert.deepEqual(navigation.navigationFor('unknown'), [])
})
