import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { renderToString } from '@vue/server-renderer'

const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function component(name, api = {}, options = {}) {
  const source = readFileSync(new URL(`../src/views/${name}.vue`, import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename: name, id: name }).errors, [])
  const route = vue.reactive({ query: { retained: 'yes', ...options.query } })
  const navigations = []
  const navigate = async ({ query }) => { navigations.push(query); route.query = query; await vue.nextTick() }
  const unmount = []
  const user = vue.reactive({ userId: 'U1' })
  const storage = new Map()
  const messages = []
  const modules = {
    vue: { ...vue, onMounted() {}, onUnmounted(fn) { unmount.push(fn) } },
    'vue-router': { useRoute: () => route, useRouter: () => ({ push: navigate, replace: navigate }) },
    'element-plus': { ElMessage: Object.fromEntries(['success', 'error', 'warning'].map(level => [level, message => messages.push({ level, message })])), ElMessageBox: { confirm: options.confirm || (async () => {}) } },
    '@element-plus/icons-vue': {},
    '../api/index.js': { ticketApi: { list: async () => ({ data: { list: [], total: 0 } }), ...api }, categoryApi: { leaf: async () => ({ data: [] }) }, draftApi: { get: async () => ({ data: null }), delete: async () => {}, ...options.draftApi } },
    '../api/consultation.js': { consultationApi: options.consultationApi || {} },
    '../stores/user.js': { useUserStore: () => user },
  }
  const code = compileScript(descriptor, { id: name }).content
    .replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g, (_, names, path) => `const {${names}} = modules[${JSON.stringify(path)}]`)
    .replace(/import\s+(\w+)\s+from\s*['"]([^'"]+)['"]/g, (_, name, path) => `const ${name} = modules[${JSON.stringify(path)}]`)
    .replace('export default', 'return')
  const scope = vue.effectScope()
  const localStorage = { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) }
  const state = scope.run(() => new Function('modules', 'localStorage', code)(modules, localStorage).setup({}, { expose() {} }))
  async function renderPage({ details = false } = {}) {
    // Render the real template and capture the drawer's public event contract.
    const template = compileTemplate({ source: descriptor.template.content, filename: name, id: name }).code
      .replace(/import\s*\{([^}]+)\}\s*from\s*['"]vue['"]/g, (_, names) => `const {${names.replace(/\s+as\s+/g, ':')}} = vue`)
      .replace('export function render', 'return function render')
    const render = new Function('vue', template)(vue)
    let bindings
    const app = vue.createSSRApp({ setup: () => () => render(vue.proxyRefs(state), []) })
    app.config.warnHandler = () => {}
    app.component('el-drawer', { props: ['modelValue', 'beforeClose'], setup(props, { attrs, slots }) { bindings = { ...attrs, ...props }; return () => details && props.modelValue ? slots.default?.() : null } })
    const html = await renderToString(app)
    return { html, drawer: bindings }
  }
  return { state, route, navigations, user, storage, messages, renderPage, stop() { unmount.forEach(fn => fn()); scope.stop() } }
}
const settle = async () => { await vue.nextTick(); await Promise.resolve(); await vue.nextTick() }
for (const name of ['EmployeeView', 'EngineerView']) {
  test(`${name}: selection follows query, ignores stale details, closes and reopens without navigation loops`, async () => {
    const a = deferred(), b = deferred()
    const c = component(name, { detail: id => id === 'A' ? a.promise : b.promise })
    try {
      c.state.openDetail({ ticket_id: 'A' }); await settle(); assert.equal(c.route.query.ticket, 'A')
      c.state.openDetail({ ticket_id: 'B' }); await settle(); assert.equal(c.route.query.ticket, 'B')
      a.resolve({ data: { ticket: { ticket_id: 'A' }, flow_logs: [] } })
      await settle()
      const detail = c.state.detailTicket || c.state.detail
      assert.equal(detail.value, null)
      assert.equal(c.state.detailLoading.value, true)
      b.resolve({ data: { ticket: { ticket_id: 'B' }, flow_logs: [] } })
      await settle()
      assert.equal(detail.value.ticket_id, 'B')
      await c.state.closeDetail()
      assert.equal(c.route.query.ticket, undefined)
      assert.equal(c.route.query.retained, 'yes')
      assert.equal(c.state.detailVisible.value, false)
      c.route.query = { ...c.route.query, ticket: 'B' }
      await settle()
      assert.equal(c.state.detailVisible.value, true)
      assert.equal(c.navigations.length, 3)
    } finally { c.stop() }
  })
  test(`${name}: closing during a request prevents late content from reopening the drawer`, async () => {
    const pending = deferred()
    const c = component(name, { detail: () => pending.promise })
    try {
      c.state.openDetail({ ticket_id: 'A' }); await settle(); assert.equal(c.route.query.ticket, 'A')
      await c.state.closeDetail()
      pending.resolve({ data: { ticket: { ticket_id: 'A' }, flow_logs: [] } })
      await settle()
      assert.equal(c.state.detailVisible.value, false)
      assert.equal((c.state.detailTicket || c.state.detail).value, null)
    } finally { c.stop() }
  })
  test(`${name}: latest list wins and failures remain distinguishable from empty results`, async () => {
    const first = deferred(), second = deferred()
    let calls = 0
    const c = component(name, { list: () => ++calls === 1 ? first.promise : second.promise })
    try {
      const old = c.state.loadTickets(), current = c.state.loadTickets()
      second.resolve({ data: { list: [{ ticket_id: 'B' }], total: 1 } })
      await current
      first.resolve({ data: { list: [{ ticket_id: 'A' }], total: 1 } })
      await old
      assert.equal((c.state.tickets || c.state.allTickets).value[0].ticket_id, 'B')
      assert.equal(c.state.loading.value, false)
    } finally { c.stop() }
    const failure = component(name, { list: async () => { throw new Error('offline') } })
    try { await failure.state.loadTickets(); assert.match(failure.state.listError.value, /offline/); assert.equal(failure.state.loading.value, false) }
    finally { failure.stop() }
  })
}
test('employee starts on my tickets and searches only the loaded page', () => {
  const c = component('EmployeeView')
  try {
    assert.equal(c.state.tab.value, 'list')
    c.state.tickets.value = [{ ticket_id: 'A', title: 'Printer' }, { ticket_id: 'B', title: 'Network' }]
    c.state.keyword.value = ' printer '
    assert.deepEqual(c.state.filteredTickets.value.map(t => t.ticket_id), ['A'])
  } finally { c.stop() }
})
test('employee view query supports create, list and browser navigation', async () => {
  const c = component('EmployeeView')
  try {
    await c.state.setView('create')
    assert.equal(c.state.tab.value, 'create')
    c.route.query = { view: 'list' }
    await settle()
    assert.equal(c.state.tab.value, 'list')
    c.route.query = { view: 'create' }
    await settle()
    assert.equal(c.state.tab.value, 'create')
    assert.equal(c.navigations.length, 1)
  } finally { c.stop() }
})
for (const name of ['EmployeeView', 'EngineerView']) {
  test(`${name}: a completed action cannot close or overwrite a different selected ticket`, async () => {
    const action = deferred()
    const c = component(name, { detail: async id => ({ data: { ticket: { ticket_id: id, status: 'IN_PROGRESS' }, flow_logs: [] } }), action: () => action.promise })
    try {
      await c.state.openDetail({ ticket_id: 'A' }); await settle()
      const pending = name === 'EmployeeView' ? c.state.acceptTicket({ ticket_id: 'A' }) : c.state.doAction('external_resolved')
      await settle()
      await c.state.openDetail({ ticket_id: 'B' }); await settle()
      action.resolve({})
      await pending
      assert.equal(c.route.query.ticket, 'B')
      assert.equal((c.state.detailTicket || c.state.detail).value.ticket_id, 'B')
    } finally { c.stop() }
  })
}

for (const name of ['EmployeeView', 'EngineerView']) {
  test(`${name}: count is unknown until loading succeeds and remains unknown on error`, async () => {
    let failing = true
    const c = component(name, { list: async () => {
      if (failing) throw new Error('List offline')
      return { data: { list: [], total: 0 } }
    } })
    try {
      assert.match((await c.renderPage()).html, /共 — 项/)
      await c.state.loadTickets()
      assert.match((await c.renderPage()).html, /共 — 项/)
      failing = false
      await c.state.loadTickets()
      assert.match((await c.renderPage()).html, /共 0 项/)
    } finally { c.stop() }
  })

  test(`${name}: drawer close starts route navigation and late animation events cannot clear a new selection`, async () => {
    const c = component(name, { detail: async id => ({ data: { ticket: { ticket_id: id }, flow_logs: [] } }) })
    try {
      await c.state.openDetail({ ticket_id: 'A' }); await settle()
      const { drawer } = await c.renderPage()
      await drawer.beforeClose?.(() => {})
      assert.equal(c.route.query.ticket, undefined)
      await c.state.openDetail({ ticket_id: 'B' }); await settle()
      drawer['onUpdate:modelValue']?.(false)
      await settle()
      assert.equal(c.route.query.ticket, 'B')
      assert.equal(c.state.detailVisible.value, true)
    } finally { c.stop() }
  })

  test(`${name}: direct links open details and drawer dismissal clears selection and transient inputs`, async () => {
    const c = component(name, { detail: async id => ({ data: { ticket: { ticket_id: id }, flow_logs: [] } }) }, { query: { ticket: 'A' } })
    try {
      await settle()
      assert.equal((c.state.detailTicket || c.state.detail).value.ticket_id, 'A')
      assert.equal(c.state.detailVisible.value, true)
      const input = c.state.rejectReason || c.state.progressRemark
      input.value = 'unsaved remark'
      const { drawer } = await c.renderPage()
      await drawer.beforeClose(() => {})
      await settle()
      assert.equal(c.state.selectedTicketId.value, '')
      assert.equal((c.state.detailTicket || c.state.detail).value, null)
      assert.equal(input.value, '')
      assert.deepEqual(c.route.query, { retained: 'yes' })
    } finally { c.stop() }
  })

  test(`${name}: stale failure cannot replace a newer detail or its loading state`, async () => {
    const a = deferred(), b = deferred()
    const c = component(name, { detail: id => id === 'A' ? a.promise : b.promise })
    try {
      await c.state.openDetail({ ticket_id: 'A' })
      await c.state.openDetail({ ticket_id: 'B' })
      a.reject(new Error('old failure'))
      await settle()
      assert.equal(c.state.detailError.value, '')
      assert.equal(c.state.detailLoading.value, true)
      b.reject(new Error('current failure'))
      await settle()
      assert.equal(c.state.detailError.value, 'current failure')
      assert.equal(c.state.detailLoading.value, false)
    } finally { c.stop() }
  })

  test(`${name}: changing identity invalidates details before another action can run`, async () => {
    const actions = []
    const c = component(name, {
      detail: async id => ({ data: { ticket: { ticket_id: id }, flow_logs: [] } }),
      action: async (...args) => actions.push(args), rating: async (...args) => actions.push(args)
    })
    try {
      await c.state.openDetail({ ticket_id: 'A' }); await settle()
      const ticket = (c.state.detailTicket || c.state.detail).value
      c.user.userId = 'U2'
      if (name === 'EmployeeView') {
        c.state.ratingScore.value = 5
        await c.state.submitRating(ticket)
      } else await c.state.doAction('external_resolved')
      assert.deepEqual(actions, [])
      assert.equal((c.state.detailTicket || c.state.detail).value, null)
    } finally { c.stop() }
  })
}

test('employee locks submission during asynchronous validation to prevent duplicate creation', async () => {
  const validation = deferred(), response = deferred()
  const creates = []
  const c = component('EmployeeView', { create: (...args) => { creates.push(args); return response.promise } })
  try {
    c.state.formRef.value = { validate: () => validation.promise }
    const first = c.state.submitTicket(), second = c.state.submitTicket()
    validation.resolve(true)
    await settle()
    assert.equal(creates.length, 1)
    assert.ok(creates[0][1].headers['Idempotency-Key'])
    response.resolve({ data: { ticket_id: 'NEW' } })
    await Promise.all([first, second])
  } finally { c.stop() }
})

test('employee submission response cannot clear another identity form or delete its draft', async () => {
  const response = deferred()
  let deletes = 0
  const c = component('EmployeeView', { create: () => response.promise }, { draftApi: { delete: async () => { deletes++ } } })
  try {
    c.state.formRef.value = { validate: async () => true }
    c.state.formToken.value = 'U1-key'
    const pending = c.state.submitTicket()
    await settle()
    c.user.userId = 'U2'
    await settle()
    c.state.form.value.title = 'New employee draft'
    response.resolve({ data: { ticket_id: 'OLD' } })
    await pending
    assert.equal(c.state.form.value.title, 'New employee draft')
    assert.notEqual(c.state.formToken.value, 'U1-key')
    assert.equal(deletes, 0)
    assert.equal(c.messages.length, 0)
  } finally { c.stop() }
})

test('employee removing consultation query removes conversion context and ignores late prefill', async () => {
  const response = deferred()
  const c = component('EmployeeView', {}, { consultationApi: { ticketDraft: () => response.promise } })
  try {
    c.state.sourceSession.value = 'OLD'
    c.route.query = { session: 'S1', view: 'create' }
    await settle()
    assert.equal(c.state.sourceSession.value, '')
    c.route.query = { view: 'list' }
    await settle()
    response.resolve({ title: 'Late prefill', convert_allowed: true })
    await settle()
    assert.equal(c.state.form.value.title, '')
    assert.equal(c.state.sourceSession.value, '')
  } finally { c.stop() }
})

test('employee acceptance keeps the drawer open for rating and reloads the submitted score', async () => {
  let ticket = { ticket_id: 'A', status: 'PENDING_ACCEPTANCE' }
  const c = component('EmployeeView', {
    detail: async () => ({ data: { ticket: { ...ticket }, flow_logs: [] } }),
    action: async (id, body) => {
      assert.equal(id, 'A')
      assert.deepEqual(body, { action: 'accept' })
      ticket.status = 'COMPLETED'
    },
    rating: async (id, body) => {
      assert.equal(id, 'A')
      assert.deepEqual(body, { score: 5, comment: 'Resolved quickly' })
      ticket.rating_score = body.score
    }
  })
  try {
    await c.state.openDetail(ticket); await settle()
    await c.state.acceptTicket(c.state.detailTicket.value)
    assert.equal(c.state.detailTicket.value.status, 'COMPLETED')
    assert.equal(c.state.detailVisible.value, true)
    c.state.ratingScore.value = 5
    c.state.ratingComment.value = 'Resolved quickly'
    await c.state.submitRating(c.state.detailTicket.value)
    assert.equal(c.state.detailTicket.value.rating_score, 5)
    assert.equal(c.route.query.ticket, 'A')
  } finally { c.stop() }
})

test('employee supplement submits the existing action payload and refreshes the detail, history and list', async () => {
  let ticket = { ticket_id: 'A', status: 'PENDING_SUPPLEMENT' }
  const remark = 'Network diagnostics: ' + 'x'.repeat(220)
  const actions = [], flows = []
  const c = component('EmployeeView', {
    detail: async () => ({ data: { ticket: { ...ticket }, flow_logs: [...flows] } }),
    list: async () => ({ data: { list: [{ ...ticket }], total: 1 } }),
    action: async (id, payload) => {
      actions.push([id, payload])
      ticket.status = 'IN_PROGRESS'
      flows.push({ transition_id: 'F1', operator_id: 'U1', to_status: 'IN_PROGRESS', reason: payload.remark })
    }
  })
  try {
    await c.state.openDetail(ticket); await settle()
    assert.match((await c.renderPage({ details: true })).html, /提交补充信息/)
    c.state.supplementRemark.value = `  ${remark}  `
    await c.state.submitSupplement(c.state.detailTicket.value); await settle()
    assert.deepEqual(actions, [['A', { action: 'supply_info', remark }]])
    assert.equal(c.state.detailTicket.value.status, 'IN_PROGRESS')
    assert.equal(c.state.detailFlows.value[0].reason, remark)
    assert.equal(c.state.tickets.value[0].status, 'IN_PROGRESS')
    assert.equal(c.state.supplementRemark.value, '')
    assert.equal(c.state.detailVisible.value, true)
    assert.doesNotMatch((await c.renderPage({ details: true })).html, /提交补充信息/)
  } finally { c.stop() }
})

test('employee supplement rejects blank input, allows short content, and retains input after failure for retry', async () => {
  let failing = true
  const actions = []
  const c = component('EmployeeView', {
    detail: async () => ({ data: { ticket: { ticket_id: 'A', status: failing ? 'PENDING_SUPPLEMENT' : 'IN_PROGRESS' }, flow_logs: [] } }),
    action: async (id, payload) => { actions.push([id, payload]); if (failing) throw new Error('Supplement service offline') }
  })
  try {
    await c.state.openDetail({ ticket_id: 'A' }); await settle()
    c.state.supplementRemark.value = '   \n '
    await c.state.submitSupplement(c.state.detailTicket.value)
    assert.deepEqual(actions, [])
    assert.ok(c.state.supplementError.value)
    c.state.supplementRemark.value = '  是  '
    await c.state.submitSupplement(c.state.detailTicket.value)
    assert.deepEqual(actions, [['A', { action: 'supply_info', remark: '是' }]])
    assert.equal(c.state.supplementRemark.value, '  是  ')
    assert.equal(c.state.detailTicket.value.status, 'PENDING_SUPPLEMENT')
    assert.equal(c.state.actionBusy.value, false)
    assert.equal(c.messages.at(-1).message, 'Supplement service offline')
    failing = false
    await c.state.submitSupplement(c.state.detailTicket.value)
    assert.deepEqual(actions[1], ['A', { action: 'supply_info', remark: '是' }])
    assert.equal(c.state.detailTicket.value.status, 'IN_PROGRESS')
    assert.equal(c.state.supplementRemark.value, '')
  } finally { c.stop() }
})

for (const outcome of ['success', 'failure']) {
  test(`employee supplement ${outcome} cannot overwrite a newly selected ticket or its input`, async () => {
    const response = deferred(), actions = []
    const c = component('EmployeeView', {
      detail: async id => ({ data: { ticket: { ticket_id: id, status: 'PENDING_SUPPLEMENT' }, flow_logs: [] } }),
      action: (id, payload) => { actions.push([id, payload]); return response.promise }
    })
    try {
      await c.state.openDetail({ ticket_id: 'A' }); await settle()
      c.state.supplementRemark.value = 'A diagnostics'
      const pending = c.state.submitSupplement(c.state.detailTicket.value)
      await c.state.submitSupplement(c.state.detailTicket.value)
      assert.equal(actions.length, 1)
      await c.state.openDetail({ ticket_id: 'B' }); await settle()
      assert.equal(c.state.supplementRemark.value, '')
      c.state.supplementRemark.value = 'B diagnostics'
      if (outcome === 'success') response.resolve({})
      else response.reject(new Error('Old request failure'))
      await pending
      assert.equal(c.route.query.ticket, 'B')
      assert.equal(c.state.detailTicket.value.ticket_id, 'B')
      assert.equal(c.state.supplementRemark.value, 'B diagnostics')
      assert.equal(c.state.supplementError.value, '')
      assert.equal(c.messages.some(message => message.level === 'error'), false)
    } finally { c.stop() }
  })
}

test('employee rejection validates the reason and keeps API errors visible without closing details', async () => {
  const c = component('EmployeeView', {
    detail: async () => ({ data: { ticket: { ticket_id: 'A', status: 'PENDING_ACCEPTANCE' }, flow_logs: [] } }),
    action: async (id, body) => {
      assert.equal(id, 'A')
      assert.deepEqual(body, { action: 'reject', remark: 'The network is still unavailable' })
      throw new Error('Action service offline')
    }
  })
  try {
    await c.state.openDetail({ ticket_id: 'A' }); await settle()
    c.state.rejectReason.value = 'short'
    await c.state.rejectTicket(c.state.detailTicket.value)
    assert.ok(c.state.rejectError.value)
    assert.equal(c.messages.length, 0)
    c.state.rejectReason.value = ' The network is still unavailable '
    await c.state.rejectTicket(c.state.detailTicket.value)
    assert.equal(c.messages.at(-1).message, 'Action service offline')
    assert.equal(c.state.detailVisible.value, true)
    assert.equal(c.state.actionBusy.value, false)
  } finally { c.stop() }
})

test('employee failed creation retains form and idempotency token for a retry', async () => {
  const keys = []
  const c = component('EmployeeView', { create: async (body, config) => {
    assert.equal(body.title, 'Network unavailable')
    keys.push(config.headers['Idempotency-Key'])
    throw new Error('Create service offline')
  } })
  try {
    c.state.formRef.value = { validate: async () => true }
    c.state.form.value.title = 'Network unavailable'
    await c.state.submitTicket()
    assert.equal(c.state.form.value.title, 'Network unavailable')
    assert.equal(c.state.submitting.value, false)
    c.state.lastSubmitAt.value = 0
    await c.state.submitTicket()
    assert.equal(keys.length, 2)
    assert.ok(keys[0])
    assert.equal(keys[0], keys[1])
    assert.equal(c.messages.at(-1).level, 'error')
  } finally { c.stop() }
})

test('engineer claim uses the impact matrix and refreshes the selected ticket', async () => {
  let ticket = { ticket_id: 'A', status: 'ASSIGNED' }
  const c = component('EngineerView', {
    detail: async () => ({ data: { ticket: { ...ticket }, flow_logs: [] } }),
    claim: async (id, body) => {
      assert.equal(id, 'A')
      assert.deepEqual(body, { impact_scope: 'CROSS_DEPT', urgency_level: 'HIGH' })
      ticket = { ...ticket, status: 'IN_PROGRESS', priority: 'HIGH' }
    }
  })
  try {
    await c.state.openDetail(ticket); await settle()
    c.state.openClaimDialog(c.state.detail.value)
    c.state.claimForm.value = { impact_scope: 'CROSS_DEPT', urgency_level: 'HIGH' }
    assert.equal(c.state.claimPriority.value, 'HIGH')
    await c.state.confirmClaim()
    assert.equal(c.state.detail.value.status, 'IN_PROGRESS')
    assert.equal(c.state.claimDialogVisible.value, false)
    assert.equal(c.state.detailVisible.value, true)
  } finally { c.stop() }
})

test('engineer progress validates remarks and enables resolution after its flow is returned', async () => {
  const flows = []
  const c = component('EngineerView', {
    detail: async () => ({ data: { ticket: { ticket_id: 'A', status: 'IN_PROGRESS' }, flow_logs: [...flows] } }),
    action: async (id, body) => {
      assert.equal(id, 'A')
      assert.deepEqual(body, { action: 'progress', remark: 'Reconnected the network' })
      flows.push({ transition_id: 'F1', operator_id: 'U1', reason: body.remark, to_status: 'IN_PROGRESS' })
    }
  })
  try {
    await c.state.openDetail({ ticket_id: 'A' }); await settle()
    assert.equal(c.state.canDone.value, false)
    c.state.progressRemark.value = 'tiny'
    await c.state.doAction('progress')
    assert.ok(c.state.actionError.value)
    assert.equal(c.messages.length, 0)
    c.state.progressRemark.value = ' Reconnected the network '
    await c.state.doAction('progress')
    assert.equal(c.state.canDone.value, true)
    assert.equal(c.state.actionError.value, '')
    assert.equal(c.state.detailVisible.value, true)
  } finally { c.stop() }
})
