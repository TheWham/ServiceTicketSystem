import test from 'node:test'
import assert from 'node:assert/strict'
import { engineerView, filterEngineerTickets, engineerStatuses } from '../src/utils/engineerViews.js'
import { readFileSync } from 'node:fs'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'

function consultation(api) {
  const { descriptor } = parse(readFileSync(new URL('../src/components/EngineerConsultation.vue', import.meta.url), 'utf8'))
  const script = compileScript(descriptor, { id: 'engineer-selection' })
  const modules = {
    vue: { ...vue, onMounted() {}, onUnmounted() {} },
    'element-plus': { ElMessage: { error() {}, success() {}, warning() {}, info() {} }, ElMessageBox: {} },
    '@element-plus/icons-vue': {},
    './ChatAttachmentUploader.vue': {},
    './ChatMessageAttachments.vue': {},
    '../api/index.js': { userApi: {} },
    '../api/consultation.js': { consultationApi: api, TERMINAL_STATUS: ['CLOSED', 'RESOLVED', 'CONVERTED_TO_TICKET'], TICKET_ENTRY_MESSAGE: 'entry' }
  }
  const code = script.content.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g, (_, names, path) => `const {${names}} = modules[${JSON.stringify(path)}]`)
    .replace(/import\s+(\w+)\s+from\s*['"]([^'"]+\.vue)['"]/g, (_, name, path) => `const ${name} = modules[${JSON.stringify(path)}]`)
    .replace('export default', 'return')
  return new Function('modules', 'setInterval', 'clearInterval', code)(modules, () => 0, () => {}).setup({ visible: false }, { expose() {}, emit() {} })
}
function deferred() { let resolve; const promise = new Promise(r => { resolve = r }); return { promise, resolve } }

test('older refresh cannot unlock controls while another session is opening', async () => {
  const oldRefresh = deferred(), newSelection = deferred()
  let sent = 0
  const c = consultation({ get: id => id === 'A' ? oldRefresh.promise : newSelection.promise, listMessages: async () => ({ items: [] }), sendMessage: async () => { sent++ } })
  c.selected.value = { session_id: 'A', status: 'HUMAN_ACTIVE' }
  const refreshing = c.reloadSelected()
  const opening = c.openSession('B')
  oldRefresh.resolve({ session_id: 'A', status: 'HUMAN_ACTIVE' })
  await refreshing
  assert.equal(c.loadingMessages.value, true)
  c.draft.value = 'must not go to A'
  await c.send()
  assert.equal(sent, 0)
  newSelection.resolve({ session_id: 'B', status: 'HUMAN_ACTIVE' })
  await opening
  assert.equal(c.selected.value.session_id, 'B')
  assert.equal(c.loadingMessages.value, false)
})

test('failed first selection exposes an attempted target and retry loads that target', async () => {
  let failing = true
  const ids = []
  const c = consultation({ get: async id => { ids.push(id); if (failing) throw new Error('offline'); return { session_id: id, status: 'HUMAN_ACTIVE' } }, listMessages: async () => ({ items: [] }) })
  await c.openSession('B')
  assert.equal(c.selected.value, null)
  assert.ok(c.messagesError.value)
  assert.equal(c.attemptedSessionId.value, 'B')
  failing = false
  await c.reloadSelected()
  assert.deepEqual(ids, ['B', 'B'])
  assert.equal(c.selected.value.session_id, 'B')
  assert.equal(c.messagesError.value, '')
})

test('failed switch keeps retry targeted at B and polling cannot replace the error', async () => {
  const oldPoll = deferred()
  let firstA = true, failingB = true, sent = 0
  const ids = []
  const c = consultation({
    get: async id => { ids.push(id); if (id === 'A' && firstA) { firstA = false; return oldPoll.promise } if (id === 'B' && failingB) throw new Error('offline'); return { session_id: id, status: 'HUMAN_ACTIVE' } },
    list: async () => ({ items: [{ session_id: 'A', status: 'CLOSED' }] }),
    listMessages: async () => ({ items: [] }), sendMessage: async () => { sent++ }
  })
  c.selected.value = { session_id: 'A', status: 'HUMAN_ACTIVE' }
  const polling = c.pollSelected()
  await c.openSession('B')
  const failure = c.messagesError.value
  assert.ok(failure)
  oldPoll.resolve({ session_id: 'A', status: 'CLOSED' })
  await polling
  await c.loadSessions()
  await c.pollSelected()
  c.draft.value = 'cannot send to old selection'
  await c.send()
  assert.equal(sent, 0)
  assert.equal(c.messagesError.value, failure)
  assert.equal(c.selected.value.status, 'HUMAN_ACTIVE')
  failingB = false
  await c.reloadSelected()
  assert.deepEqual(ids, ['A', 'B', 'B'])
  assert.equal(c.selected.value.session_id, 'B')
})

const tickets = ['ASSIGNED', 'IN_PROGRESS', 'PENDING_SUPPLEMENT', 'PENDING_EXTERNAL', 'PENDING_ACCEPTANCE', 'COMPLETED', 'CANCELLED', 'CLOSED'].map((status, i) => ({ ticket_id: `IT-${i}`, title: i === 1 ? 'VPN connection' : '打印机', creator_name: '王小明', status }))
test('query resolves supported views and keeps overview fallback', () => {
  for (const view of ['pool', 'tasks', 'completed', 'consultations']) assert.equal(engineerView(view), view)
  assert.equal(engineerView(undefined), 'all')
  assert.equal(engineerView(['tasks']), 'all')
  assert.equal(engineerView('unknown'), 'all')
})
test('views isolate the backend ticket states without conflating terminal states', () => {
  assert.deepEqual(filterEngineerTickets(tickets, 'pool').map(t => t.status), ['ASSIGNED'])
  assert.deepEqual(filterEngineerTickets(tickets, 'tasks').map(t => t.status), ['IN_PROGRESS', 'PENDING_SUPPLEMENT', 'PENDING_EXTERNAL', 'PENDING_ACCEPTANCE'])
  assert.deepEqual(filterEngineerTickets(tickets, 'completed').map(t => t.status), ['COMPLETED', 'CANCELLED', 'CLOSED'])
  assert.equal(filterEngineerTickets(tickets, 'all').length, 8)
  assert.deepEqual(engineerStatuses('consultations'), [])
})
test('search combines view and case insensitive title id or applicant search', () => {
  assert.equal(filterEngineerTickets(tickets, 'tasks', ' vpn ').length, 1)
  assert.equal(filterEngineerTickets(tickets, 'pool', 'VPN').length, 0)
  assert.equal(filterEngineerTickets(tickets, 'completed', '王小明').length, 3)
  assert.equal(filterEngineerTickets(tickets, 'tasks', 'it-1').length, 1)
  assert.deepEqual(filterEngineerTickets([{ status: 'ASSIGNED' }], 'pool', 'unknown'), [])
})
