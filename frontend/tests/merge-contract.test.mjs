import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'

function employee(overrides = {}) {
  const source = readFileSync(new URL('../src/views/EmployeeView.vue', import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  const compiled = compileScript(descriptor, { id: 'Employee' })
  const storage = new Map()
  const created = []
  const route = { query: { session: 'S1', ticket: 'T1' } }
  const ticketApi = {
    create: async (...args) => created.push(args),
    list: async () => ({ data: { list: [], total: 0 } }),
    ...overrides.ticketApi
  }
  const modules = {
    vue: { ...vue, watch() {}, onMounted() {}, onUnmounted() {} },
    'vue-router': { useRoute: () => route, useRouter: () => ({ replace: ({ query }) => { route.query = query } }) },
    'element-plus': { ElMessage: { success() {}, warning() {}, error() {} }, ElMessageBox: {} },
    '@element-plus/icons-vue': {},
    '../api/index.js': { ticketApi, categoryApi: {}, draftApi: { ensureDraftId: () => 'D1', delete: async () => {}, ...overrides.draftApi } },
    '../api/consultation.js': { consultationApi: overrides.consultationApi || {} },
    '../stores/user.js': { useUserStore: () => ({ userId: 'U1', currentUser: { role: 'EMPLOYEE' } }) },
    '../components/SlaBadge.vue': {},
    '../components/SlaTimer.vue': {}
  }
  const code = compiled.content
    .replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g,
      (_, names, path) => `const {${names}} = modules[${JSON.stringify(path)}]`)
    .replace(/import\s+(\w+)\s+from\s*['"]([^'"]+)['"]/g,
      (_, name, path) => `const ${name} = modules[${JSON.stringify(path)}]`)
    .replace('export default', 'return')
  const localStorage = { getItem: k => storage.get(k), setItem: (k, v) => storage.set(k, v), removeItem: k => storage.delete(k) }
  const options = new Function('modules', 'localStorage', code)(modules, localStorage)
  const state = options.setup({}, { expose() {} })
  return { state, created, route, storage }
}

test('consultation prefill uses the main category catalog and its ticket nature', async () => {
  const { state: c } = employee({ consultationApi: { ticketDraft: async () => ({
    title: 'New account', description: 'Please create an account', category_id: 'C_ACC', convert_allowed: true
  }) } })
  c.categories.value = [{ category_id: 'C_ACC', ticket_nature: 'SERVICE_REQUEST', status: 'ACTIVE' }]
  await c.loadConsultPrefill('S1')
  assert.equal(c.form.value.category_id, 'C_ACC')
  assert.equal(c.form.value.nature, 'SERVICE_REQUEST')
  assert.equal(c.sourceSession.value, 'S1')
})

test('closed consultation reference is not sent as a new conversion', async () => {
  const { state: c } = employee({ consultationApi: { ticketDraft: async () => ({
    title: 'Reference only', category_id: 'C_NET', convert_allowed: false
  }) } })
  await c.loadConsultPrefill('S1')
  assert.equal(c.sourceSession.value, '')
  assert.equal(c.form.value.title, 'Reference only')
})

test('restoring drafts accepts legacy nature while saving the main contract and source session', () => {
  const { state: c } = employee()
  c.categories.value = [{ category_id: 'C_ACC', ticket_nature: 'SERVICE_REQUEST', status: 'ACTIVE' }]
  c.applyDraftPayload({ ticket_nature: 'SERVICE_REQUEST', category_id: 'C_ACC', source_session_id: 'S1' })
  assert.equal(c.form.value.nature, 'SERVICE_REQUEST')
  assert.equal(c.draftPayload().ticket_nature, 'SERVICE_REQUEST')
  assert.equal(c.draftPayload().source_session_id, 'S1')
  c.applyDraftPayload({ nature: 'INCIDENT', category_id: 'C_ACC' })
  assert.equal(c.form.value.category_id, '')
  assert.equal(c.sourceSession.value, '')
})

test('ticket creation maps draft ticket_nature to ticket nature and keeps idempotency in headers', async () => {
  const { state: c, created, route } = employee()
  c.formRef.value = { validate: async () => true }
  c.applyDraftPayload({ ticket_nature: 'INCIDENT', nature: 'SERVICE_REQUEST' })
  assert.equal(c.draftPayload().ticket_nature, 'INCIDENT')
  assert.equal(c.draftPayload().nature, undefined)
  Object.assign(c.form.value, { category_id: 'C_NET', title: 'Offline',
    description: 'Network is unavailable', impact_description: 'One user', urgency_description: 'Meeting soon' })
  c.sourceSession.value = 'S1'
  c.formToken.value = 'stable-key'
  await c.submitTicket()
  assert.equal(created.length, 1)
  const [body, config] = created[0]
  assert.equal(body.nature, 'INCIDENT')
  assert.equal(body.ticket_nature, undefined)
  assert.equal(body.source_session_id, 'S1')
  assert.equal(body.idempotency_key, undefined)
  assert.equal(config.headers['Idempotency-Key'], 'stable-key')
  assert.deepEqual(route.query, { ticket: 'T1' })
})

test('canonical category fields populate consultation conversion', async () => {
  const { state: c } = employee({ consultationApi: { ticketDraft: async () => ({
    category_id: 'C_ACC', convert_allowed: true
  }) } })
  c.categories.value = [{ category_id: 'C_ACC', ticket_nature: 'SERVICE_REQUEST', status: 'ACTIVE', nature: 'INCIDENT', enabled: false }]
  await c.loadConsultPrefill('S1')
  assert.equal(c.form.value.category_id, 'C_ACC')
  assert.equal(c.form.value.nature, 'SERVICE_REQUEST')
})

test('impact and urgency limits match the 2000-character HTTP contract', () => {
  const { state: c } = employee()
  assert.equal(c.formRules.impact_description.find(rule => rule.max).max, 2000)
  assert.equal(c.formRules.urgency_description.find(rule => rule.max).max, 2000)
})

test('draft server failure saves the source context under the current employee key', async () => {
  const { state: c, storage } = employee({ draftApi: { save: async () => { throw new Error('offline') } } })
  c.form.value.title = 'Offline draft'
  c.sourceSession.value = 'S1'
  await c.saveDraft()
  assert.equal(c.localDraftBanner.value, true)
  assert.equal(JSON.parse(storage.get('ticket_draft_local:U1')).source_session_id, 'S1')
})
