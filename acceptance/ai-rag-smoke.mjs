import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'

const base = (process.env.IT_GATEWAY_URL || 'http://127.0.0.1:8080').replace(/\/$/, '')
const requireAnswer = process.argv.includes('--require-answer')
const requestPrefix = `rag-smoke-${randomUUID()}`
let token, createdSession

async function call(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${base}/api/v1${path}`, {
    method, signal: AbortSignal.timeout(180000),
    headers: { 'Content-Type': 'application/json', 'X-Request-Id': `${requestPrefix}-${randomUUID()}`,
      'Idempotency-Key': randomUUID(), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body)
  })
  const envelope = await response.json()
  assert.ok(response.ok && [0, 'SUCCESS'].includes(envelope.code), `${path}: HTTP ${response.status} / code=${envelope.code}`)
  return envelope.data
}

try {
  const login = await call('/users/login', { method: 'POST', body: {
    userId: process.env.IT_TEST_USER_ID || 'U_EMP01', password: process.env.IT_TEST_PASSWORD || '123456'
  } })
  token = login.token
  assert.ok(token, 'Missing authentication token')
  const cases = [
    ['帮我写一份周报', 'OFF_TOPIC', 'REFUSE', 'OFF_TOPIC'],
    ['帮我授予管理员权限', 'HIGH_RISK', 'REFUSE', 'HIGH_RISK_TOPIC'],
    ['帮我看看', 'UNCERTAIN', 'CLARIFY', null]
  ]
  for (const [question, domain, type, reason] of cases) {
    const retrieved = await call('/rag/retrievals', { method: 'POST', body: { question, topK: 3 } })
    assert.equal(retrieved.domain, domain)
    const session = await call('/consultations', { method: 'POST', body: { source: 'AI' } })
    createdSession = session.sessionId
    const reply = await call(`/consultations/${createdSession}/ai-messages`, { method: 'POST', body: { message: question } })
    assert.equal(reply.replyType, type)
    assert.equal(reply.refusalReason ?? null, reason)
    assert.deepEqual(reply.citations, [])
    const history = await call(`/consultations/${createdSession}/messages`)
    assert.ok(history.items.some(message => message.reply_type === type && message.interaction_id === reply.interactionId))
    await call(`/consultations/${createdSession}/close`, { method: 'POST', body: { reason: 'RAG 联调测试完成' } })
    createdSession = null
    console.log(`PASS ${domain}: RAG → consultation → persisted ${type}`)
  }
  const session = await call('/consultations', { method: 'POST', body: { source: 'AI' } })
  createdSession = session.sessionId
  const answer = await call(`/consultations/${createdSession}/ai-messages`, { method: 'POST', body: { message: 'VPN 客户端提示证书过期怎么处理' } })
  console.log(JSON.stringify({ stage: 'real-answer', replyType: answer.replyType, refusalReason: answer.refusalReason ?? null,
    citations: answer.citations?.length ?? 0, answerLength: answer.answerText?.length ?? 0 }))
  if (requireAnswer) assert.equal(answer.replyType, 'ANSWER', `Real model/RAG not ready: ${answer.refusalReason}`)
  else assert.ok(['ANSWER', 'REFUSE', 'CLARIFY'].includes(answer.replyType))
} catch (error) {
  console.error(error.message)
  process.exitCode = 1
} finally {
  if (createdSession) {
    try { await call(`/consultations/${createdSession}/close`, { method: 'POST', body: { reason: 'RAG 联调测试结束' } }) }
    catch { console.error('Could not close the test consultation:', createdSession); process.exitCode = 1 }
  }
}
