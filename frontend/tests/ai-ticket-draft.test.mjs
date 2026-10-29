import test from 'node:test'
import assert from 'node:assert/strict'

// sessionStorage 在 Node 里不存在，按浏览器语义补一个最小实现（含 set/get/remove/clear）
class MemoryStorage {
  constructor() { this.map = new Map() }
  getItem(k) { return this.map.has(k) ? this.map.get(k) : null }
  setItem(k, v) { this.map.set(k, String(v)) }
  removeItem(k) { this.map.delete(k) }
  clear() { this.map.clear() }
}

globalThis.sessionStorage = new MemoryStorage()
const draft = await import('../src/utils/aiTicketDraft.js').catch(() => ({}))

test.beforeEach(() => globalThis.sessionStorage.clear())

test('往返：存进去能按同一会话取出来，字段原样保留', () => {
  assert.equal(typeof draft.saveAiTicketDraft, 'function')
  assert.equal(typeof draft.takeAiTicketDraft, 'function')
  draft.saveAiTicketDraft('S1', { title: 'vpn连不上', description: '现象：提示认证失败', category: 'C_NET', priority: 'MEDIUM' })
  const got = draft.takeAiTicketDraft('S1')
  assert.equal(got.title, 'vpn连不上')
  assert.equal(got.description, '现象：提示认证失败')
  assert.equal(got.category, 'C_NET')
  assert.equal(got.sessionId, 'S1')
})

test('读取即消费：第二次取不到，避免下次手动提单被旧草稿顶上', () => {
  draft.saveAiTicketDraft('S1', { title: 't', description: 'd' })
  assert.notEqual(draft.takeAiTicketDraft('S1'), null)
  assert.equal(draft.takeAiTicketDraft('S1'), null)
})

test('会话不匹配不返回：一个会话的草稿不能被另一个会话误用', () => {
  draft.saveAiTicketDraft('S1', { title: 't', description: 'd' })
  assert.equal(draft.takeAiTicketDraft('S2'), null)
})

test('缺字段的调用不写入也不报错', () => {
  draft.saveAiTicketDraft('', { title: 't' })
  assert.equal(draft.takeAiTicketDraft(''), null)
  draft.saveAiTicketDraft('S1', null)
  assert.equal(draft.takeAiTicketDraft('S1'), null)
})

test('存储里是坏数据时返回 null 而不是抛错', () => {
  globalThis.sessionStorage.setItem('ai_ticket_draft', '{不是 JSON')
  assert.equal(draft.takeAiTicketDraft('S1'), null)
})

test('增删字段只留约定的四个，不把整份草稿塞进存储', () => {
  draft.saveAiTicketDraft('S1', { title: 't', description: 'd', category: 'C_NET', priority: 'LOW', summary: '不该带走', attachments: ['x'] })
  const got = draft.takeAiTicketDraft('S1')
  assert.deepEqual(Object.keys(got).sort(), ['category', 'description', 'priority', 'sessionId', 'title'])
})