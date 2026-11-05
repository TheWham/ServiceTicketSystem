import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createPinia, setActivePinia } from 'pinia'
import { consultationApi, consumeAiSseStream } from '../src/api/consultation.js'

globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} }
setActivePinia(createPinia())

const source = readFileSync(new URL('../src/components/ConsultationChat.vue', import.meta.url), 'utf8')

const encoder = new TextEncoder()
/** 把若干 SSE 帧打包成一次网络分片流；分片故意切碎，验证跨分片拼接。 */
function sseResponse(frames, { ok = true, status = 200 } = {}) {
  const bytes = frames.map(text => encoder.encode(text))
  return {
    ok, status,
    body: {
      getReader() {
        let i = 0
        return {
          read: async () => i < bytes.length ? { done: false, value: bytes[i++] } : { done: true, value: undefined }
        }
      }
    }
  }
}

test('token frames stream through the typewriter handler in order and final returns the payload', async () => {
  const tokens = []
  const queued = []
  const result = await consumeAiSseStream(sseResponse([
    ': keep-alive\n\n',
    'event: queued\ndata: {"position":1}\n\n',
    'event: token\ndata: {"text":"第一步："}\n\n' +
    'event: token\ndata: {"text":"重启"}\n\n' +
    'event: token\ndata: {"text":"路由器"}\n\n',
    'event: final\ndata: {"sessionId":"S1","replyType":"ANSWER","answerText":"第一步：重启路由器","interactionId":"I1"}\n\n'
  ]), {
    onQueued: position => queued.push(position),
    onToken: text => tokens.push(text)
  })
  assert.deepEqual(tokens, ['第一步：', '重启', '路由器'])
  assert.deepEqual(queued, [1])
  assert.equal(result.replyType, 'ANSWER')
  assert.equal(result.interactionId, 'I1')
})

test('a frame split across network chunks is reassembled before parsing', async () => {
  const tokens = []
  const full = encoder.encode('event: token\ndata: {"text":"跨分片"}\n\nevent: final\ndata: {"replyType":"ANSWER"}\n\n')
  const response = {
    ok: true, status: 200,
    body: {
      getReader() {
        let i = 0
        const chunks = [full.slice(0, 11), full.slice(11, 24), full.slice(24)]
        return { read: async () => i < chunks.length ? { done: false, value: chunks[i++] } : { done: true, value: undefined } }
      }
    }
  }
  const result = await consumeAiSseStream(response, { onToken: text => tokens.push(text) })
  assert.deepEqual(tokens, ['跨分片'])
  assert.equal(result.replyType, 'ANSWER')
})

test('error event surfaces the real error class and is flagged as interrupted', async () => {
  await assert.rejects(consumeAiSseStream(sseResponse([
    'event: token\ndata: {"text":"已流出"}\n\n',
    'event: error\ndata: {"errorClass":"TIMEOUT","message":"本轮回答超时"}\n\n'
  ]), { onToken: () => {} }), error =>
    error.code === 'TIMEOUT' && error.message === '本轮回答超时' && error.interrupted === true)
})

test('a stream that ends without final or error is interrupted, not success', async () => {
  await assert.rejects(consumeAiSseStream(sseResponse([
    'event: token\ndata: {"text":"半截"}\n\n'
  ]), { onToken: () => {} }), error =>
    error.interrupted === true && /未完成/.test(error.message))
})

test('non-OK envelope errors are surfaced with the business message, not swallowed', async () => {
  const response = { ok: false, status: 401, json: async () => ({ code: 'UNAUTHENTICATED', message: '登录已过期' }) }
  await assert.rejects(consumeAiSseStream(response, {}), error => error.code === 'UNAUTHENTICATED' && error.message === '登录已过期')
})

test('aiMessageStream posts to the stream endpoint with the interceptor-equivalent headers', async () => {
  let captured
  const originalFetch = globalThis.fetch
  globalThis.fetch = async (url, init) => {
    captured = { url, init }
    return sseResponse(['event: final\ndata: {"replyType":"ANSWER","answerText":"好的"}\n\n'])
  }
  try {
    const result = await consultationApi.aiMessageStream('S9', '打印机没反应', undefined, { onToken: () => {} })
    assert.equal(captured.url, '/api/v1/consultations/S9/ai-messages/stream')
    assert.equal(captured.init.method, 'POST')
    assert.ok(captured.init.headers['X-Request-Id'])
    assert.ok(captured.init.headers['Idempotency-Key'])
    assert.deepEqual(JSON.parse(captured.init.body), { message: '打印机没反应' })
    assert.equal(result.answerText, '好的')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('vue ai branch always uses the streaming endpoint without fallback to the sync endpoint', () => {
  // 组件内透传 stillActive 闭包与事件句柄；旧同步端点不再是 AI 首选路径——不允许静默回退
  assert.match(source, /consultationApi\.aiMessageStream\(sessionId, text, undefined, \{/)
  assert.match(source, /await sendAiStreamed\(sessionId, text, stillActive\)/)
  assert.doesNotMatch(source, /consultationApi\.aiMessage\(sessionId,/)
})

test('queued position and streaming state are rendered on the pending AI bubble', () => {
  assert.match(source, /已受理，排队中…前方还有 \$\{msg\.queuedPosition\} 条消息/)
  assert.match(source, /'streaming-text': msg\.streaming/)
  assert.match(source, /stream-caret/)
  assert.match(source, /v-if="msg\.streaming" class="stream-caret"/)
})

test('interrupted streams keep the streamed text and mark it as unfinished instead of faking success', () => {
  assert.match(source, /msg\.interrupted = true/)
  assert.match(source, /回复被中断（未完成）/)
  assert.match(source, /stream-interrupted-note/)
})

test('final settle rolls back the typewriter residue for refusal answers', () => {
  assert.match(source, /function settleAiAnswer\(msg, res\)/)
  assert.match(source, /msg\.content = '' \/\/ 回滚打字机残留/)
  assert.match(source, /msg\.refusalReason = res\.refusalReason/)
})

test('input stays open while an answer is streaming thanks to the server-side session FIFO', () => {
  // 发送框不再被 aiThinking 阻塞：会话串行由服务端队列保证
  assert.match(source, /:disabled="sending \|\| inputDisabled \|\| closing \|\| cancelingQueue"/)
  // 发送按钮 loading 只反映"本地正在发出"，不反映"AI 正在回答"
  assert.match(source, /:loading="sending"/)
  assert.doesNotMatch(source, /:loading="sending \|\| aiThinking"/)
})

test('in-flight stream bookkeeping resets when leaving AI mode', () => {
  assert.match(source, /const streamingCount = ref\(0\)/)
  assert.match(source, /streamingCount\.value = Math\.max\(0, streamingCount\.value - 1\)/)
  assert.match(source, /streamingCount\.value = 0/)
})

test('final answer payload fills citations, ticket draft and system hints like the sync endpoint did', () => {
  assert.match(source, /msg\.ticketDraft = res\.ticketDraft \|\| null/)
  assert.match(source, /msg\.citations = res\.citations \|\| \[\]/)
  assert.match(source, /这条回答暂无知识库依据，仅供排查参考/)
})
