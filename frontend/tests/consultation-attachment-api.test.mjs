import test from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import http, { consultationApi } from '../src/api/consultation.js'

globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} }
setActivePinia(createPinia())
const response = (config, data) => ({ status: 200, statusText: 'OK', headers: {}, config, data })

test('attachment-only send omits blank content and carries IDs with stable client message ID', async () => {
  let request
  http.defaults.adapter = async config => { request = config; return response(config, { code: 'SUCCESS', data: { message_id: 'M1' } }) }
  const result = await consultationApi.sendMessage('S1', '', 'retry-id', ['ATT1', 'ATT2'])
  assert.deepEqual(JSON.parse(request.data), { attachment_ids: ['ATT1', 'ATT2'], client_message_id: 'retry-id' })
  assert.equal(request.url, '/consultations/S1/messages')
  assert.ok(request.headers['X-Request-Id'])
  assert.ok(request.headers['Idempotency-Key'])
  assert.equal(result.message_id, 'M1')
})

test('upload sends multipart file and forwards progress and cancellation', async () => {
  const file = new File(['test content'], '故障说明.txt', { type: 'text/plain' })
  const controller = new AbortController()
  const progress = []
  http.defaults.adapter = async config => {
    assert.equal(config.url, '/consultations/S1/attachments')
    assert.equal(config.data.get('file').name, '故障说明.txt')
    assert.equal(config.signal, controller.signal)
    config.onUploadProgress({ loaded: 50, total: 100 })
    return response(config, { code: 'SUCCESS', data: { attachment_id: 'ATT1' } })
  }
  const result = await consultationApi.uploadAttachment('S1', file, value => progress.push(value), controller.signal)
  assert.equal(result.attachment_id, 'ATT1')
  assert.deepEqual(progress, [50])
})

test('attachment download returns the Blob without treating it as a JSON envelope', async () => {
  const blob = new Blob(['original bytes'], { type: 'application/octet-stream' })
  http.defaults.adapter = async config => {
    assert.equal(config.url, '/consultations/S1/attachments/ATT1/content')
    assert.equal(config.responseType, 'blob')
    return response(config, blob)
  }
  const result = await consultationApi.attachmentBlob('S1', 'ATT1')
  assert.equal(result, blob)
  assert.equal(await result.text(), 'original bytes')
})

test('download authorization errors still surface the structured server message', async () => {
  http.defaults.adapter = async config => {
    throw Object.assign(new Error('HTTP 404'), { config, response: { status: 404,
      data: new Blob([JSON.stringify({ code: 'OBJECT_NOT_FOUND', message: '附件不存在或无权访问' })], { type: 'application/json' }) } })
  }
  await assert.rejects(consultationApi.attachmentBlob('S1', 'ATT1'), error => error.code === 'OBJECT_NOT_FOUND' && error.message === '附件不存在或无权访问')
})
