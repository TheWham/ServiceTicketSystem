import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { renderToString } from '@vue/server-renderer'

function component(name, apis = {}, currentUser = { user_id: 'reviewer', role: 'KNOWLEDGE_ADMIN', status: 'ACTIVE' }) {
  const source = readFileSync(new URL(`../src/views/${name}.vue`, import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  const notices = []
  const route = vue.reactive({ query: {} })
  const navigations = []
  const navigate = kind => async ({ query }) => { navigations.push(kind); route.query = query }
  const scope = vue.effectScope()
  const unmount = []
  const userStore = vue.reactive({ currentUser })
  const modules = {
    vue: { ...vue, onMounted() {}, onUnmounted(fn) { unmount.push(fn) } },
    'vue-router': { useRoute: () => route, useRouter: () => ({ replace: navigate('replace'), push: navigate('push') }) },
    'element-plus': { ElMessage: Object.fromEntries(['info', 'error', 'warning', 'success'].map(k => [k, text => notices.push(text)])), ElMessageBox: { confirm: async () => {}, prompt: async () => ({ value: '审核原因' }) } },
    '@element-plus/icons-vue': {},
    '../api/index.js': apis,
    '../stores/user.js': { useUserStore: () => userStore },
    '../components/SlaBadge.vue': {}
  }
  const code = compileScript(descriptor, { id: name }).content
    .replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g, (_, names, path) => `const {${names}} = modules[${JSON.stringify(path)}]`)
    .replace(/import\s+(\w+)\s+from\s*['"]([^'"]+)['"]/g, (_, name, path) => `const ${name} = modules[${JSON.stringify(path)}]`)
    .replace('export default', 'return')
  const options = new Function('modules', code)(modules)
  const state = scope.run(() => options.setup({}, { expose() {} }))
  async function renderFooter() {
    const footer = descriptor.template.content.match(/<template #footer>([\s\S]*?)<\/template>/)[1]
    const app = vue.createSSRApp({ setup: () => ({ ...state }), render: vue.compile(footer) })
    app.component('ElButton', { props: ['disabled', 'loading'], setup: (props, { slots }) => () => vue.h('button', { disabled: props.disabled || props.loading }, slots.default?.()) })
    app.component('ElAlert', { props: ['title'], setup: props => () => vue.h('div', props.title) })
    return renderToString(app)
  }
  return { state, notices, route, navigations, userStore, renderFooter, stop: () => { unmount.forEach(fn => fn()); scope.stop() } }
}
const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

test('account search combines normalized text and role without changing source accounts', () => {
  const { state: c } = component('AccountManageView')
  c.accounts.value = [{ user_id: 'U1', name: '王林', department: 'IT', role: 'ENGINEER' }, { user_id: 'U2', name: '李林', department: 'IT', role: 'EMPLOYEE' }]
  c.search.value = '  it '
  c.roleFilter.value = 'ENGINEER'
  assert.deepEqual(c.filteredAccounts.value.map(a => a.user_id), ['U1'])
  c.search.value = '不存在'
  assert.equal(c.filteredAccounts.value.length, 0)
  assert.equal(c.accounts.value.length, 2)
})

test('account load ignores a stale response and exposes a current failure for retry', async () => {
  const first = deferred()
  let calls = 0
  const { state: c } = component('AccountManageView', { userApi: { listAccounts: () => ++calls === 1 ? first.promise : Promise.reject(new Error('账号服务不可用')) } })
  const old = c.load()
  await c.load()
  first.resolve({ data: [{ user_id: 'OLD' }] })
  await old
  assert.equal(c.loadError.value, '账号服务不可用')
  assert.equal(c.accounts.value.length, 0)
  assert.equal(c.loading.value, false)
})

test('dispatch detail switching ignores late results and closing clears route selection', async () => {
  const first = deferred()
  const { state: c, route, stop } = component('DispatchView', { ticketApi: { detail: id => id === 'T1' ? first.promise : Promise.resolve({ data: { ticket: { ticket_id: id }, flow_logs: [] } }) } })
  const old = c.openDetail({ ticket_id: 'T1' })
  await c.openDetail({ ticket_id: 'T2' })
  first.resolve({ data: { ticket: { ticket_id: 'T1' }, flow_logs: [] } })
  await old
  assert.equal(c.detailTicket.value.ticket_id, 'T2')
  route.query = { ticket: 'T2', keep: 'yes' }
  await c.closeDetail()
  await vue.nextTick()
  assert.equal(route.query.ticket, undefined)
  assert.equal(route.query.keep, 'yes')
  assert.equal(c.detailVisible.value, false)
  assert.equal(c.detailTicket.value, null)
  stop()
})

test('dispatch route removal closes detail and invalidates an in-flight request', async () => {
  const pending = deferred()
  const { state: c, route, stop } = component('DispatchView', { ticketApi: { detail: () => pending.promise } })
  route.query = { ticket: 'T1' }
  await vue.nextTick()
  route.query = {}
  await vue.nextTick()
  pending.resolve({ data: { ticket: { ticket_id: 'T1' }, flow_logs: [] } })
  await pending.promise
  await vue.nextTick()
  assert.equal(c.detailVisible.value, false)
  assert.equal(c.detailTicket.value, null)
  stop()
})

test('knowledge defaults to the library and clears old detail while another article loads', async () => {
  const pending = deferred()
  const { state: c } = component('KnowledgeAdminView', { ragApi: { getArticle: () => pending.promise } })
  assert.equal(c.activeTab.value, 'lifecycle')
  c.detail.value = { article: { articleId: 'OLD', status: 'PUBLISHED' } }
  const loading = c.openDetail('NEW')
  assert.equal(c.detail.value, null)
  pending.reject(new Error('文章读取失败'))
  await loading
  assert.equal(c.detailError.value, '文章读取失败')
  assert.equal(c.detail.value, null)
})

test('knowledge articles use only the latest filter response', async () => {
  const first = deferred()
  const { state: c } = component('KnowledgeAdminView', { ragApi: { listArticles: q => q.status === 'DRAFT' ? first.promise : Promise.resolve({ data: { records: [{ articleId: 'P' }], total: 1 } }) } })
  c.listQuery.value.status = 'DRAFT'
  const old = c.fetchArticles(1)
  c.listQuery.value.status = 'PUBLISHED'
  await c.fetchArticles(1)
  first.resolve({ data: { records: [{ articleId: 'D' }], total: 6 } })
  await old
  assert.equal(c.articles.value[0].articleId, 'P')
  assert.equal(c.articleTotal.value, 1)
})

test('knowledge trace failure is distinct from empty history and retry clears the error', async () => {
  let failed = true
  const { state: c } = component('KnowledgeAdminView', { ragApi: { listTraces: async () => { if (failed) throw new Error('处理记录暂不可用'); return { data: [] } } } })
  await c.fetchRecentTraces()
  assert.equal(c.historyError.value, '处理记录暂不可用')
  failed = false
  await c.fetchRecentTraces()
  assert.equal(c.historyError.value, '')
  assert.deepEqual(c.historyTraces.value, [])
})

test('dispatch list preserves failure distinction and retry ignores a stale response', async () => {
  const pending = deferred()
  let calls = 0
  const { state: c } = component('DispatchView', { ticketApi: { list: async () => {
    if (++calls === 1) return pending.promise
    if (calls === 2) throw new Error('调度暂不可用')
    return { data: { list: [], total: 0 } }
  } } })
  const old = c.loadTickets()
  await c.loadTickets()
  pending.resolve({ data: { list: [{ ticket_id: 'OLD' }], total: 1 } })
  await old
  assert.equal(c.listError.value, '调度暂不可用')
  assert.deepEqual(c.tickets.value, [])
  await c.loadTickets()
  assert.equal(c.listError.value, '')
  assert.equal(c.listLoading.value, false)
})

test('knowledge route selection handles switching, closing and browser navigation', async () => {
  const pending = deferred()
  const { state: c, route, stop } = component('KnowledgeAdminView', { ragApi: {
    getArticle: id => id === 'A' ? pending.promise : Promise.resolve({ data: { article: { articleId: id } } })
  } })
  const old = c.openDetail('A')
  await c.openDetail('B')
  pending.resolve({ data: { article: { articleId: 'A' } } })
  await old
  assert.equal(c.detail.value.article.articleId, 'B')
  assert.equal(route.query.article, 'B')
  route.query = { ...route.query, keep: 'yes' }
  await c.closeDetail()
  assert.equal(route.query.article, undefined)
  assert.equal(route.query.keep, 'yes')
  assert.equal(c.detail.value, null)
  route.query = { article: 'C' }
  await vue.nextTick()
  await vue.nextTick()
  assert.equal(c.detail.value.article.articleId, 'C')
  route.query = {}
  await vue.nextTick()
  assert.equal(c.drawerVisible.value, false)
  stop()
})

test('knowledge publication completing after close does not reopen its article', async () => {
  const pending = deferred()
  const { state: c, notices, stop } = component('KnowledgeAdminView', { ragApi: {
    getArticle: async id => ({ data: { article: { articleId: id, status: 'PENDING_REVIEW' }, currentVersion: { versionId: 'V1', authorId: 'author' } } }),
    publishArticle: () => pending.promise,
    listArticles: async () => ({ data: { records: [], total: 0 } })
  } })
  await c.openDetail('A')
  const action = c.doPublish()
  await vue.nextTick()
  await c.closeDetail()
  pending.resolve({ data: { indexStatus: 'PENDING_COMPENSATION' } })
  await action
  assert.equal(c.drawerVisible.value, false)
  assert.equal(c.detail.value, null)
  assert.ok(notices.some(message => message.includes('未完成')))
  stop()
})

test('knowledge request completing after unmount cannot repopulate detail', async () => {
  const pending = deferred()
  const { state: c, stop } = component('KnowledgeAdminView', { ragApi: { getArticle: () => pending.promise } })
  const opening = c.openDetail('A')
  await vue.nextTick()
  stop()
  pending.resolve({ data: { article: { articleId: 'A' } } })
  await opening
  assert.equal(c.detail.value, null)
})

for (const [view, key, record] of [['DispatchView', 'ticket', { ticket_id: 'A' }], ['KnowledgeAdminView', 'article', 'A']]) {
  test(`${view} opens a history entry so Back can return to the list`, async () => {
    const { state: c, navigations, route, stop } = component(view, {
      ticketApi: { detail: async id => ({ data: { ticket: { ticket_id: id } } }) },
      ragApi: { getArticle: async id => ({ data: { article: { articleId: id } } }) }
    })
    await c.openDetail(record)
    assert.equal(navigations[0], 'push')
    assert.equal(route.query[key], 'A')
    await c.openDetail(view === 'DispatchView' ? { ticket_id: 'B' } : 'B')
    assert.equal(navigations[1], 'replace')
    await c.closeDetail()
    assert.equal(navigations[2], 'replace')
    stop()
  })
}

test('knowledge duplicate publish clicks issue one request and unknown index state is not success', async () => {
  const pending = deferred()
  let calls = 0
  const { state: c, notices, stop } = component('KnowledgeAdminView', { ragApi: {
    getArticle: async id => ({ data: { article: { articleId: id, status: 'PENDING_REVIEW' }, currentVersion: { versionId: 'V1', authorId: 'author' } } }),
    publishArticle: () => { ++calls; return pending.promise },
    listArticles: async () => ({ data: { records: [], total: 0 } })
  } })
  await c.openDetail('A')
  const first = c.doPublish()
  const second = c.doPublish()
  await vue.nextTick()
  assert.equal(calls, 1)
  pending.resolve({ data: { indexStatus: 'UNKNOWN' } })
  await Promise.all([first, second])
  assert.ok(notices.some(message => message.includes('未完成')))
  stop()
})

test('knowledge failed upload retains its trace and reports failure instead of success', async () => {
  const { state: c, notices } = component('KnowledgeAdminView', { ragApi: {
    uploadDocument: async () => ({ data: { trace: { traceId: 'FAILED-1', status: 'FAILED', stages: [] } } }),
    listTraces: async () => ({ data: [] })
  } })
  c.categories.value = [{ category_id: 'REAL-NET', name: '办公网络', status: 'ACTIVE' }]
  c.uploadForm.value.categoryId = 'REAL-NET'
  c.selectedFile.value = new File(['content'], 'knowledge.md')
  await c.submitUploadAndProcess()
  assert.equal(c.currentTrace.value.traceId, 'FAILED-1')
  assert.match(c.uploadError.value, /失败/)
  assert.equal(c.isProcessing.value, false)
  assert.ok(!notices.some(message => /成功|完成/.test(message)))
})

test('knowledge upload categories use active canonical records and invalidate an obsolete selection', async () => {
  const { state: c } = component('KnowledgeAdminView', { categoryApi: { leaf: async () => ({ data: [
    { category_id: 'CURRENT', name: '当前分类', status: 'ACTIVE' },
    { category_id: 'RETIRED', name: '已停用', status: 'INACTIVE' }
  ] }) } })
  assert.equal(c.uploadForm.value.categoryId, '')
  c.uploadForm.value.categoryId = 'OLD-SEED'
  await c.fetchCategories()
  assert.deepEqual(c.categories.value.map(category => category.category_id), ['CURRENT'])
  assert.equal(c.uploadForm.value.categoryId, '')
  assert.equal(c.categoryError.value, '')
})

test('knowledge category failure is retryable and different from a successful empty result', async () => {
  let failed = true
  const { state: c } = component('KnowledgeAdminView', { categoryApi: { leaf: async () => {
    if (failed) throw new Error('分类服务不可用')
    return { data: [] }
  } } })
  await c.fetchCategories()
  assert.equal(c.categoryError.value, '分类服务不可用')
  assert.equal(c.categoryLoading.value, false)
  failed = false
  await c.fetchCategories()
  assert.equal(c.categoryError.value, '')
  assert.deepEqual(c.categories.value, [])
})

test('knowledge upload rejects a category not returned by the current service', async () => {
  let uploaded = false
  const { state: c, notices } = component('KnowledgeAdminView', { ragApi: { uploadDocument: async () => { uploaded = true } } })
  c.selectedFile.value = new File(['content'], 'knowledge.md')
  c.uploadForm.value.categoryId = 'C_NET'
  await c.submitUploadAndProcess()
  assert.equal(uploaded, false)
  assert.ok(notices.some(message => message.includes('分类')))
})

test('knowledge lifecycle actions retain real API payloads and selected article identity', async () => {
  const calls = []
  const apis = {
    getArticle: async id => ({ data: { article: { articleId: id, status: 'DRAFT' }, currentVersion: { versionId: 'V1', authorId: 'author' } } }),
    listArticles: async () => ({ data: { records: [], total: 0 } })
  }
  for (const name of ['submitArticle', 'publishArticle', 'rejectArticle', 'offlineArticle', 'reindexArticle']) {
    apis[name] = async (...args) => { calls.push([name, ...args]); return { data: { indexStatus: 'INDEXED' } } }
  }
  const { state: c, stop } = component('KnowledgeAdminView', { ragApi: apis })
  await c.openDetail('REAL-ARTICLE')
  await c.doSubmit()
  c.detail.value.article.status = 'PENDING_REVIEW'
  await c.doPublish()
  c.detail.value.article.status = 'PENDING_REVIEW'
  await c.doReject()
  c.detail.value.article.status = 'PUBLISHED'
  await c.doOffline()
  c.detail.value.article.status = 'PUBLISHED'
  await c.doReindex()
  assert.deepEqual(calls, [
    ['submitArticle', 'REAL-ARTICLE', { remark: '工作台提交审核' }],
    ['publishArticle', 'REAL-ARTICLE', { changeNote: '审核原因' }],
    ['rejectArticle', 'REAL-ARTICLE', { reason: '审核原因' }],
    ['offlineArticle', 'REAL-ARTICLE', { reason: '审核原因' }],
    ['reindexArticle', 'REAL-ARTICLE']
  ])
  stop()
})

test('knowledge upload sends the current category ID under the existing multipart field', async () => {
  let form
  const { state: c } = component('KnowledgeAdminView', { ragApi: {
    uploadDocument: async body => { form = body; return { data: { article: { status: 'DRAFT' }, trace: { traceId: 'TRACE', status: 'SUCCESS' } } } },
    listTraces: async () => ({ data: [] }),
    listArticles: async () => ({ data: { records: [], total: 0 } })
  } })
  c.categories.value = [{ category_id: 'CURRENT-LEAF', name: '当前分类', status: 'ACTIVE' }]
  c.uploadForm.value.categoryId = 'CURRENT-LEAF'
  c.selectedFile.value = new File(['document'], 'knowledge.md')
  await c.submitUploadAndProcess()
  assert.equal(form.get('categoryId'), 'CURRENT-LEAF')
  assert.equal(form.get('publishNow'), 'false')
  assert.equal(form.get('file').name, 'knowledge.md')
  assert.equal(c.uploadError.value, '')
})

test('dispatch assigns and resumes tickets through the existing API payloads', async () => {
  const calls = []
  const { state: c, stop } = component('DispatchView', { ticketApi: {
    assign: async (...args) => calls.push(['assign', ...args]),
    action: async (...args) => calls.push(['action', ...args]),
    list: async () => ({ data: { list: [], total: 0 } })
  } })
  c.showReassign({ ticket_id: 'T1', assignee_id: 'OLD' })
  c.selectedEngineer.value = 'CURRENT-ENGINEER'
  c.reassignReason.value = '调整处理人'
  await c.doAssign()
  await c.forceResolve({ ticket_id: 'T1' })
  assert.deepEqual(calls, [
    ['assign', 'T1', { assignee_id: 'CURRENT-ENGINEER', reason: '调整处理人' }],
    ['action', 'T1', { action: 'external_resolved', remark: '平台管理员强制恢复' }]
  ])
  stop()
})

for (const scenario of [
  { role: 'KNOWLEDGE_ADMIN', risk: 'HIGH', author: 'author', allowed: false, label: '等待平台管理员复核', reason: '移交平台管理员' },
  { role: 'PLATFORM_ADMIN', risk: 'HIGH', author: 'author', allowed: true, label: '平台复核并发布' },
  { role: 'KNOWLEDGE_ADMIN', risk: 'NORMAL', author: 'author', allowed: true, label: '审核发布' },
  { role: 'PLATFORM_ADMIN', risk: 'NORMAL', author: 'author', allowed: true, label: '审核发布' },
  { role: 'KNOWLEDGE_ADMIN', risk: 'NORMAL', author: 'reviewer', allowed: false, label: '不可自审', reason: '其他管理员' },
  { role: 'PLATFORM_ADMIN', risk: 'HIGH', author: 'reviewer', allowed: false, label: '不可自审', reason: '其他平台管理员' }
]) {
  test(`knowledge publish ${scenario.role} ${scenario.risk} author=${scenario.author} matches backend permissions`, async () => {
    const calls = []
    const { state: c, renderFooter, stop } = component('KnowledgeAdminView', { ragApi: {
      publishArticle: async (...args) => { calls.push(args); return { data: { indexStatus: 'INDEXED' } } },
      listArticles: async () => ({ data: { records: [], total: 0 } })
    } }, { user_id: 'reviewer', role: scenario.role, status: 'ACTIVE' })
    c.detail.value = { article: { articleId: 'ARTICLE', status: 'PENDING_REVIEW', riskLevel: scenario.risk }, currentVersion: { versionId: 'VERSION', authorId: scenario.author } }
    const html = await renderFooter()
    assert.ok(html.includes(scenario.label), html)
    const button = html.match(new RegExp('<button([^>]*)>' + scenario.label + '</button>'))
    assert.ok(button, html)
    assert.equal(button[1].includes('disabled'), !scenario.allowed)
    if (scenario.reason) assert.ok(html.includes(scenario.reason), html)
    assert.match(html, /<button(?![^>]*disabled)[^>]*>驳回<\/button>/)
    await c.doPublish()
    assert.deepEqual(calls, scenario.allowed ? [['ARTICLE', { changeNote: '审核原因' }]] : [])
    stop()
  })
}

test('knowledge publish rechecks identity after the confirmation prompt', async () => {
  let calls = 0
  const { state: c, userStore, stop } = component('KnowledgeAdminView', { ragApi: {
    publishArticle: async () => { ++calls; return { data: { indexStatus: 'INDEXED' } } },
    listArticles: async () => ({ data: { records: [], total: 0 } })
  } }, { user_id: 'reviewer', role: 'PLATFORM_ADMIN', status: 'ACTIVE' })
  c.detail.value = { article: { articleId: 'ARTICLE', status: 'PENDING_REVIEW', riskLevel: 'HIGH' }, currentVersion: { versionId: 'VERSION', authorId: 'author' } }
  const pending = c.doPublish()
  userStore.currentUser = { user_id: 'reviewer', role: 'KNOWLEDGE_ADMIN', status: 'ACTIVE' }
  await pending
  assert.equal(calls, 0)
  assert.equal(c.actionLoading.value, false)
  stop()
})

test('knowledge unrelated roles see no lifecycle management actions and cannot publish', async () => {
  let calls = 0
  const { state: c, renderFooter, stop } = component('KnowledgeAdminView', { ragApi: {
    publishArticle: async () => { ++calls; return { data: { indexStatus: 'INDEXED' } } },
    listArticles: async () => ({ data: { records: [], total: 0 } })
  } }, { user_id: 'employee', role: 'EMPLOYEE', status: 'ACTIVE' })
  c.detail.value = { article: { articleId: 'ARTICLE', status: 'PENDING_REVIEW', riskLevel: 'NORMAL' }, currentVersion: { versionId: 'VERSION', authorId: 'author' } }
  assert.doesNotMatch(await renderFooter(), /<button/)
  await c.doPublish()
  assert.equal(calls, 0)
  stop()
})
