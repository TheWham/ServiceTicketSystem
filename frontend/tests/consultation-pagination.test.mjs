import test from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import http, { consultationApi } from '../src/api/consultation.js'

globalThis.localStorage = { getItem() { return null }, removeItem() {}, setItem() {} }
setActivePinia(createPinia())

function transport(handler) {
  const requests = []
  http.defaults.adapter = async config => {
    requests.push(config)
    assert.equal(config.url, '/consultations/S1/messages')
    assert.equal(config.method, 'get')
    assert.ok(config.headers['X-Request-Id'])
    const data = await handler(config.params, config)
    return { data, status: 200, statusText: 'OK', headers: {}, config }
  }
  return requests
}
const success = data => ({ code: 'SUCCESS', data })
const history = Array.from({ length: 205 }, (_, i) => ({ message_id: `M${i + 1}`, content: `消息${i + 1}` }))

test('message facade fetches the complete ordered history including arrivals beyond 100', async () => {
  const requests = transport(({ page, pageSize }) => success({ items: history.slice((page - 1) * pageSize, page * pageSize), total: 205 }))
  const messages = await consultationApi.listMessages('S1')
  assert.deepEqual(messages, history)
  assert.deepEqual(requests.map(r => r.params), [{ page: 1, pageSize: 100 }, { page: 2, pageSize: 100 }, { page: 3, pageSize: 100 }])
})

test('reported total ends a full final page without a redundant request', async () => {
  const requests = transport(() => success({ items: history.slice(0, 100), total: 100 }))
  assert.equal((await consultationApi.listMessages('S1')).length, 100)
  assert.equal(requests.length, 1)
})

test('empty pages terminate even with a stale nonzero total', async () => {
  const requests = transport(({ page }) => {
    assert.ok(page <= 2, 'must stop on an empty page')
    return success({ items: page === 1 ? history.slice(0, 100) : [], total: 205 })
  })
  assert.equal((await consultationApi.listMessages('S1')).length, 100)
  assert.equal(requests.length, 2)
})

test('empty history is a successful empty array', async () => {
  const requests = transport(() => success({ items: [], total: 0 }))
  assert.deepEqual(await consultationApi.listMessages('S1'), [])
  assert.equal(requests.length, 1)
})

test('without total, continue full pages until a short page', async () => {
  transport(({ page, pageSize }) => success({ items: history.slice((page - 1) * pageSize, page * pageSize) }))
  assert.deepEqual(await consultationApi.listMessages('S1'), history)
})

test('total takes precedence over a short page when the server caps page size', async () => {
  const requests = transport(({ page }) => success({ items: history.slice((page - 1) * 50, page * 50), total: 205 }))
  assert.deepEqual(await consultationApi.listMessages('S1'), history)
  assert.equal(requests.length, 5)
})

test('later page rejection preserves the business reason instead of returning partial history', async () => {
  transport(({ page }) => page === 1 ? success({ items: history.slice(0, 100), total: 205 }) : { code: 'FORBIDDEN', message: '会话权限已失效', request_id: 'req-denied' })
  await assert.rejects(consultationApi.listMessages('S1'), error => error.code === 'FORBIDDEN' && error.requestId === 'req-denied' && error.message === '会话权限已失效')
})

test('malformed success data is not treated as empty history', async () => {
  transport(() => success({ total: 100 }))
  await assert.rejects(consultationApi.listMessages('S1'), /消息/)
})

test('disposing the owner stops pagination before another page is requested', async () => {
  const controller = new AbortController()
  const requests = transport(() => {
    controller.abort()
    return success({ items: history.slice(0, 100), total: 205 })
  })
  await assert.rejects(consultationApi.listMessages('S1', { signal: controller.signal }))
  assert.equal(requests.length, 1)
})
