import test from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import api, { userApi, ticketApi } from '../src/api/index.js'
import consultation from '../src/api/consultation.js'

globalThis.localStorage = { getItem() { return null }, removeItem() {}, setItem() {} }
setActivePinia(createPinia())
function response(data) { return { data, status: 200, statusText: 'OK', headers: {}, config: {} } }

test('a business rejection cannot appear as an empty successful response', async () => {
  api.defaults.adapter = async () => response({ code: 4001, msg: '当前状态不允许操作', data: null })
  await assert.rejects(ticketApi.list(), /当前状态不允许操作/)
})
test('ticket creation carries a stable idempotency key at the actual transport boundary', async () => {
  let sent
  api.defaults.adapter = async config => { sent = config; return response({ code: 0, data: { ticket_id: 'T1' } }) }
  await ticketApi.create({ title: 'Network', nature: 'INCIDENT' }, { headers: { 'Idempotency-Key': 'stable-key' } })
  assert.equal(sent.headers['Idempotency-Key'], 'stable-key')
  assert.equal(JSON.parse(sent.data).idempotency_key, undefined)
})
test('login options reject an old gateway role instead of presenting old accounts', async () => {
  api.defaults.adapter = async () => response({ code: 0, data: [{ user_id: 'old', role: 'supervisor', status: 'ACTIVE' }] })
  await assert.rejects(userApi.loginOptions(), /不受支持/)
  api.defaults.adapter = async () => response({ code: 0, data: [{ user_id: 'K1', role: 'KNOWLEDGE_ADMIN', status: 'ACTIVE', name: 'Current' }] })
  const result = await userApi.loginOptions()
  assert.equal(result.data[0].role, 'KNOWLEDGE_ADMIN')
})
test('consultation business rejection retains its reason instead of becoming missing data', async () => {
  consultation.defaults.adapter = async () => response({ code: 'KNOWLEDGE_UNAVAILABLE', message: '知识服务暂不可用', data: null })
  await assert.rejects(consultation.get('/consultations'), error => error.code === 'KNOWLEDGE_UNAVAILABLE' && error.message === '知识服务暂不可用')
})
