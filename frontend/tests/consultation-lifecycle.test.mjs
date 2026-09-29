import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript } from '@vue/compiler-sfc'
import * as vue from 'vue'

const terminal = ['RESOLVED', 'CONVERTED_TO_TICKET', 'CLOSED']
const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

// Execute the compiled component setup with real Vue reactivity, replacing only
// network/UI services and timers. No browser or additional test dependency needed.
function component(name, api = {}, users = []) {
  const source = readFileSync(new URL(`../src/components/${name}.vue`, import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  const compiled = compileScript(descriptor, { id: name })
  const notices = []
  const intervals = new Set()
  const modules = {
    vue: { ...vue, onMounted() {}, onUnmounted() {} },
    'vue-router': { useRouter: () => ({ push() {} }) },
    'element-plus': {
      ElMessage: Object.fromEntries(['info', 'error', 'warning', 'success'].map(k => [k, text => notices.push(text)])),
      ElMessageBox: { prompt: async () => ({ value: '问题复发' }) }
    },
    '@element-plus/icons-vue': {},
    '../api/consultation.js': { consultationApi: api, TERMINAL_STATUS: terminal, CONSULTATION_STATUS: {}, REFUSAL_REASON: {}, TICKET_ENTRY_MESSAGE: '[提交工单入口]' },
    '../api/index.js': { userApi: { listUsers: async () => ({ data: users }) } }
  }
  const code = compiled.content.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g,
    (_, names, path) => `const {${names}} = modules[${JSON.stringify(path)}]`)
    .replace('export default', 'return')
  const options = new Function('modules', 'setInterval', 'clearInterval', code)(modules,
    fn => { intervals.add(fn); return fn }, fn => intervals.delete(fn))
  const state = options.setup({ visible: false }, { expose() {}, emit() {} })
  return { state, notices, intervals }
}

test('employee close clears the draft and transfer dialog, disconnects, and prevents further sends', async () => {
  let sent = 0
  const { state: c, intervals } = component('ConsultationChat', {
    close: async () => ({ status: 'CLOSED' }), sendMessage: async () => { sent++ }
  })
  c.session.value = { sessionId: 'S1', status: 'HUMAN_ACTIVE' }
  c.draft.value = '尚未发送'
  c.transferVisible.value = true
  c.startPolling()
  await c.closeSession()
  assert.equal(c.session.value.status, 'CLOSED')
  assert.equal(c.draft.value, '')
  assert.equal(c.transferVisible.value, false)
  assert.equal(intervals.size, 0)
  c.draft.value = '关闭后不能发送'
  await c.send()
  assert.equal(sent, 0)
})

test('only one close is submitted while an employee close is pending', async () => {
  const pending = deferred()
  let calls = 0
  const { state: c } = component('ConsultationChat', { close: () => { calls++; return pending.promise } })
  c.session.value = { sessionId: 'S1', status: 'WAITING_ENGINEER' }
  const first = c.closeSession()
  const second = c.closeSession()
  pending.resolve({ status: 'CLOSED' })
  await Promise.all([first, second])
  assert.equal(calls, 1)
})

test('failed close keeps the conversation and draft available for retry', async () => {
  const { state: c, notices, intervals } = component('ConsultationChat', { close: async () => { throw new Error('暂时不可用') } })
  c.session.value = { sessionId: 'S1', status: 'HUMAN_ACTIVE' }
  c.draft.value = '保留内容'
  c.startPolling()
  await c.closeSession()
  assert.equal(c.session.value.status, 'HUMAN_ACTIVE')
  assert.equal(c.draft.value, '保留内容')
  assert.equal(intervals.size, 1)
  assert.ok(notices.includes('暂时不可用'))
})

test('a delayed status poll cannot reactivate a closed employee conversation', async () => {
  const pending = deferred()
  const { state: c } = component('ConsultationChat', {
    get: () => pending.promise, close: async () => ({ status: 'CLOSED' }), listMessages: async () => ({ items: [] })
  })
  c.session.value = { sessionId: 'S1', status: 'HUMAN_ACTIVE' }
  const polling = c.refreshStatus()
  await c.closeSession()
  pending.resolve({ session_id: 'S1', status: 'HUMAN_ACTIVE' })
  await polling
  assert.equal(c.session.value.status, 'CLOSED')
})

test('a late AI response does not enter a new conversation after closing the old one', async () => {
  const pending = deferred()
  const { state: c } = component('ConsultationChat', {
    aiMessage: () => pending.promise, close: async () => ({ status: 'CLOSED' }),
    create: async () => ({ sessionId: 'S2', status: 'AI_ACTIVE' })
  })
  c.session.value = { sessionId: 'S1', status: 'AI_ACTIVE' }
  c.draft.value = '旧问题'
  const sending = c.send()
  await c.closeSession()
  await c.startAi()
  pending.resolve({ replyType: 'ANSWER', answerText: '旧回答' })
  await sending
  assert.equal(c.session.value.sessionId, 'S2')
  assert.equal(c.messages.value.some(m => m.content === '旧回答'), false)
})

test('reopening a resolved conversation resumes status polling', async () => {
  const { state: c, intervals } = component('ConsultationChat', {
    reopen: async () => ({ status: 'WAITING_ENGINEER' })
  })
  c.session.value = { sessionId: 'S1', status: 'RESOLVED' }
  await c.reopenSession()
  assert.equal(c.session.value.status, 'WAITING_ENGINEER')
  assert.equal(intervals.size, 1)
})

test('engineer sees applicant name, role and account, with an account fallback', async () => {
  const { state: c } = component('EngineerConsultation', {}, [{ user_id: 'U1', name: '张三', role: 'employee' }])
  await c.loadApplicants()
  assert.equal(c.applicantLabel({ creator_id: 'U1' }), '张三 · 员工 · U1')
  assert.equal(c.applicantLabel({ creator_id: 'U2' }), '员工 · U2')
})

test('engineer list detecting close still loads the final system message and stops sending', async () => {
  let sent = 0
  const closed = { session_id: 'S1', creator_id: 'U1', status: 'CLOSED' }
  const { state: c, notices } = component('EngineerConsultation', {
    list: async () => ({ items: [closed] }),
    get: async () => closed,
    listMessages: async () => ({ items: [{ message_id: 'M1', sender_type: 'SYSTEM', content: '员工已结束对话，会话已断开。' }] }),
    sendMessage: async () => { sent++ }
  })
  c.selected.value = { session_id: 'S1', status: 'HUMAN_ACTIVE' }
  c.draft.value = '回复'
  await c.loadSessions()
  await c.pollSelected()
  assert.equal(c.isTerminal.value, true)
  assert.equal(c.messages.value.at(-1)?.content, '员工已结束对话，会话已断开。')
  assert.equal(c.draft.value, '')
  c.draft.value = '无法发送'
  await c.send()
  assert.equal(sent, 0)
  assert.ok(notices.some(n => n.includes('结束')))
})

test('a delayed engineer resolution response cannot reactivate a closed conversation', async () => {
  const pending = deferred()
  const { state: c } = component('EngineerConsultation', {
    submitResolution: () => pending.promise, list: async () => ({ items: [] })
  })
  c.selected.value = { session_id: 'S1', status: 'HUMAN_ACTIVE' }
  const submission = c.submitResolution()
  await Promise.resolve()
  c.selected.value = { session_id: 'S1', status: 'CLOSED' }
  pending.resolve({ status: 'PENDING_CONFIRMATION' })
  await submission
  assert.equal(c.selected.value.status, 'CLOSED')
  assert.equal(c.messages.value.length, 0)
})

test('opening a conversation during closure includes its committed end message', async () => {
  const pending = deferred()
  let committed = false
  const { state: c } = component('EngineerConsultation', {
    get: () => pending.promise,
    listMessages: async () => ({ items: committed ? [{ message_id: 'M1', sender_type: 'SYSTEM', content: '员工已结束对话，会话已断开。' }] : [] })
  })
  const opening = c.openSession('S1')
  committed = true
  pending.resolve({ session_id: 'S1', status: 'CLOSED' })
  await opening
  assert.equal(c.isTerminal.value, true)
  assert.equal(c.messages.value.at(-1)?.content, '员工已结束对话，会话已断开。')
})

test('failed helpful feedback remains retryable instead of silently resolving the conversation', async () => {
  let confirmations = 0
  let unavailable = true
  const { state: c, notices } = component('ConsultationChat', {
    feedback: async () => {
      if (unavailable) throw new Error('反馈暂时无法保存')
      return { accepted: true }
    },
    confirm: async () => { confirmations++; return { status: 'RESOLVED' } }
  })
  c.session.value = { sessionId: 'S1', status: 'AI_ACTIVE' }
  const answer = { interactionId: 'AI1', feedback: null }
  await c.resolveAnswer(answer)
  assert.equal(confirmations, 0)
  assert.equal(c.session.value.status, 'AI_ACTIVE')
  assert.equal(answer.feedback, null)
  assert.ok(notices.some(n => n.includes('反馈')))
  unavailable = false
  await c.resolveAnswer(answer)
  assert.equal(confirmations, 1)
  assert.equal(answer.feedback, 'resolved')
  assert.equal(c.session.value.status, 'RESOLVED')
})

test('helpful feedback is saved once and double-clicking cannot submit twice', async () => {
  const pending = deferred()
  let feedbacks = 0, confirmations = 0
  const { state: c } = component('ConsultationChat', {
    feedback: () => { feedbacks++; return pending.promise },
    confirm: async () => { confirmations++; return { status: 'RESOLVED' } }
  })
  c.session.value = { sessionId: 'S1', status: 'AI_ACTIVE' }
  const answer = { interactionId: 'AI1', feedback: null }
  const first = c.resolveAnswer(answer)
  const second = c.resolveAnswer(answer)
  pending.resolve({ accepted: true })
  await Promise.all([first, second])
  assert.equal(feedbacks, 1)
  assert.equal(confirmations, 1)
  assert.equal(c.session.value.status, 'RESOLVED')
})

test('failed negative feedback stays available to retry and does not claim success', async () => {
  const { state: c, notices } = component('ConsultationChat', {
    feedback: async () => { throw new Error('反馈暂时无法保存') }
  })
  c.session.value = { sessionId: 'S1', status: 'AI_ACTIVE' }
  const answer = { interactionId: 'AI1', feedback: null }
  await c.markUnresolved(answer)
  assert.equal(answer.feedback, null)
  assert.ok(notices.some(n => n.includes('反馈')))
})

test('restored AI messages retain general-answer and off-topic metadata', () => {
  const { state: c } = component('ConsultationChat')
  const answer = c.toLocalMessage({ message_id: 'M1', sender_type: 'AI', content: '检查打印连接', interaction_id: 'AI1', reply_type: 'ANSWER', general_answer: true, citations: [] })
  const refusal = c.toLocalMessage({ message_id: 'M2', sender_type: 'AI', content: '不能答复', reply_type: 'REFUSE', refusal_reason: 'OFF_TOPIC', general_answer: false })
  assert.equal(answer.generalAnswer, true)
  assert.equal(answer.interactionId, 'AI1')
  assert.equal(refusal.refusalReason, 'OFF_TOPIC')
  assert.equal(refusal.replyType, 'REFUSE')
})
