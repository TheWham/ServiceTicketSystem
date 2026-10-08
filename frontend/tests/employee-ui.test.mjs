import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { computed, reactive, ref, watch } from 'vue'

const source = readFileSync(new URL('../src/views/EmployeeView.vue', import.meta.url), 'utf8')
const functionBlock = name => {
  const match = source.match(new RegExp(`(?:async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}`))
  assert.ok(match, `Production ${name} exists`)
  return match[0]
}
const productionFunction = (name, dependencies = {}) => new Function(...Object.keys(dependencies), `${functionBlock(name)}; return ${name}`)(...Object.values(dependencies))

test('employee tab follows history and ticket links, preserving consultation context on switching', () => {
  const block = source.match(/const tab = computed\(\{[\s\S]*?\n\}\)/)?.[0]
  assert.ok(block)
  const route = reactive({ path: '/employee', query: { from: 'consultation', session: 'S1' } })
  const pushes = []
  const tab = new Function('computed', 'route', 'router', `${block}; return tab`)(computed, route, { push: location => pushes.push(location) })
  assert.equal(tab.value, 'create')
  tab.value = 'list'
  assert.deepEqual(pushes[0].query, { from: 'consultation', session: 'S1', tab: 'list' })
  route.query = pushes[0].query
  assert.equal(tab.value, 'list')
  route.query = { ticket: 'T1' }
  assert.equal(tab.value, 'list')
  route.query = { ticket: 'T1', tab: 'create' }
  assert.equal(tab.value, 'create')
  route.query = { tab: 'invalid' }
  assert.equal(tab.value, 'create')
})

test('status filter returns to page one and clears explicitly scoped page search', () => {
  const page = ref(5)
  const pageSearch = ref('printer')
  const requests = []
  productionFunction('applyFilters', { page, pageSearch, loadTickets: () => requests.push(page.value) })()
  assert.equal(page.value, 1)
  assert.equal(pageSearch.value, '')
  assert.deepEqual(requests, [1])
})

test('consultation mapping uses exact DTO fields and only known leaf categories', () => {
  const map = productionFunction('mapConsultationDraft')
  const draft = { session_id: 'S1', convert_allowed: true, title: 'Install software', description: 'Need work software', category_id: 'C_SW' }
  assert.deepEqual(map(draft, [{ categoryId: 'C_SW', nature: 'SERVICE_REQUEST' }]), { title: 'Install software', description: 'Need work software', category_id: 'C_SW', nature: 'SERVICE_REQUEST' })
  assert.equal(map(draft, []).category_id, '')
  assert.equal(map({ ...draft, convert_allowed: false }, []), null)
  assert.equal(map({ ...draft, description: '', summary: 'Summary' }, []).description, 'Summary')
  assert.equal(map({ ...draft, title: 'A'.repeat(120) }, []).title.length, 100)
})

test('explicit consultation fill preserves edited fields and chooses nature from newly filled category', () => {
  const fill = productionFunction('fillEmptyDraftFields')
  const current = { title: 'My edited title', description: '', category_id: '', nature: 'INCIDENT', contact: 'Desk 12' }
  const prefill = { title: 'Consultation title', description: 'Consultation description', category_id: 'C_SW', nature: 'SERVICE_REQUEST' }
  const result = fill(current, prefill)
  assert.equal(result.form.title, current.title)
  assert.equal(result.form.description, prefill.description)
  assert.equal(result.form.nature, 'SERVICE_REQUEST')
  assert.equal(result.form.contact, 'Desk 12')
  assert.equal(result.changed, true)
  assert.equal(current.description, '')
  assert.equal(fill({ ...current, description: 'Edited', category_id: 'C_NET' }, prefill).changed, false)
})

test('reading consultation draft never overwrites edits made while request is pending', async () => {
  let resolve
  const consultationSession = ref('S1')
  const form = ref({ title: '', description: '' })
  const state = { consultationSession, prefillDraft: ref(null), prefillError: ref(''), prefillLoading: ref(false), consultationApi: { ticketDraft: () => new Promise(done => { resolve = done }) }, form }
  const load = new Function(...Object.keys(state), `let prefillRequest = 0; ${functionBlock('loadConsultationPrefill')}; return loadConsultationPrefill`)(...Object.values(state))
  const pending = load()
  form.value.title = 'Typed while waiting'
  resolve({ session_id: 'S1', convert_allowed: true, title: 'Remote title' })
  await pending
  assert.equal(form.value.title, 'Typed while waiting')
  assert.equal(state.prefillDraft.value.title, 'Remote title')
  assert.equal(state.prefillLoading.value, false)
})

test('fully populated form can explicitly associate a validated consultation without overwriting fields', () => {
  const initial = { title: 'Edited title', description: 'Edited description', category_id: 'C_NET', nature: 'INCIDENT', contact: 'Desk 12' }
  const messages = []
  const state = {
    form: ref({ ...initial }), consultationSession: ref('S1'), appliedSession: ref(''), formToken: ref('old-token'),
    prefillLoading: ref(false), categoryLoading: ref(false), submitting: ref(false),
    prefillDraft: ref({ session_id: 'S1', convert_allowed: true, title: 'Remote title', description: 'Remote description', category_id: 'C_SW' }),
    categories: ref([{ categoryId: 'C_SW', nature: 'SERVICE_REQUEST' }]),
    mapConsultationDraft: productionFunction('mapConsultationDraft'),
    fillEmptyDraftFields: productionFunction('fillEmptyDraftFields'),
    genClientToken: () => 'associated-token', ElMessage: { info: message => messages.push(message) }
  }
  const apply = productionFunction('applyConsultationPrefill', state)
  for (const guard of ['prefillLoading', 'categoryLoading', 'submitting']) {
    state[guard].value = true
    apply()
    assert.equal(state.appliedSession.value, '')
    state[guard].value = false
  }
  state.prefillDraft.value.convert_allowed = false
  apply()
  assert.equal(state.appliedSession.value, '')
  state.prefillDraft.value.convert_allowed = true
  apply()
  assert.deepEqual(state.form.value, initial)
  assert.equal(state.appliedSession.value, 'S1')
  assert.equal(state.formToken.value, 'associated-token')
  assert.deepEqual(messages, ['已关联咨询，保留现有内容'])
})

test('closing employee details invalidates a pending response and keeps the modal closed', async () => {
  let resolve
  const state = {
    detailVisible: ref(false), detailLoading: ref(false), detailError: ref(''), detailId: ref(''), detailTicket: ref(null), detailFlows: ref([]), detailPhotos: ref([]),
    rejectReason: ref(''), rejectError: ref(''), ratingScore: ref(0), ratingComment: ref(''),
    ticketApi: { detail: () => new Promise(done => { resolve = done }) }, revokePhotoUrls: () => {}, loadPhotoUrls: async () => [], watch
  }
  const closeWatcher = source.split('\n').find(line => line.startsWith('watch(detailVisible,'))
  assert.ok(closeWatcher)
  const open = new Function(...Object.keys(state), `let detailRequest = 0; ${functionBlock('invalidateDetailRequest')}; ${functionBlock('openDetail')}; ${closeWatcher}; return openDetail`)(...Object.values(state))
  const pending = open({ ticket_id: 'T1' })
  assert.equal(state.detailVisible.value, true)
  state.detailVisible.value = false
  resolve({ data: { ticket: { ticket_id: 'T1' }, flow_logs: [] } })
  await pending
  assert.equal(state.detailVisible.value, false)
  assert.equal(state.detailTicket.value, null)
  assert.equal(state.detailLoading.value, false)
})

test('latest employee list response wins when requests complete out of order', async () => {
  const resolves = []
  const state = { listLoading: ref(false), listError: ref(''), tickets: ref([]), total: ref(0), page: ref(1), pageSize: 10, filter: ref({ status: '' }), userStore: { userId: 'U1' }, ticketApi: { list: () => new Promise(resolve => resolves.push(resolve)) } }
  const load = new Function(...Object.keys(state), `let listRequest = 0; ${functionBlock('loadTickets')}; return loadTickets`)(...Object.values(state))
  const older = load()
  state.filter.value.status = 'COMPLETED'
  const newer = load()
  resolves[1]({ data: { list: [{ ticket_id: 'new' }], total: 1 } })
  await newer
  resolves[0]({ data: { list: [{ ticket_id: 'old' }], total: 15 } })
  await older
  assert.equal(state.tickets.value[0].ticket_id, 'new')
  assert.equal(state.total.value, 1)
  assert.equal(state.listLoading.value, false)
})
