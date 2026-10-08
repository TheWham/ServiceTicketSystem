import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import * as vue from 'vue'
import * as icons from '@element-plus/icons-vue'
import * as attachments from '../src/utils/chatAttachments.js'

const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const file = (name = 'photo.png', type = 'image/png', size = 12) => ({ name, type, size })
const metadata = (id = 'A1', type = 'image/png') => ({
  attachment_id: id, file_name: 'photo.png', content_type: type, size: 12, is_image: type.startsWith('image/'),
})
function urls() {
  const created = [], revoked = []
  return {
    created, revoked,
    createObjectURL(blob) { const url = `blob:test-${created.length}`; created.push({ blob, url }); return url },
    revokeObjectURL(url) { revoked.push(url) },
  }
}
function uploader(overrides = {}) {
  const urlApi = urls(), removed = [], notices = [], models = []
  const api = {
    uploadAttachment: async () => metadata(),
    removeAttachment: async (session, id) => { removed.push([session, id]) },
    ...overrides.api,
  }
  const controller = attachments.createAttachmentUploader({
    sessionId: 'S1', urlApi, api,
    onChange: rows => models.push(rows), onNotice: message => notices.push(message),
    ...overrides, api,
  })
  return { controller, urlApi, removed, notices, models }
}

test('20 MB boundary is accepted, larger files are rejected without consuming one of ten slots', async () => {
  let count = 0
  const { controller: c, notices } = uploader({ api: { uploadAttachment: async (_s, f) => ({ ...metadata(`A${++count}`), file_name: f.name }) } })
  await c.addFiles([file('too-large', '', 20 * 1024 * 1024 + 1), file('boundary', '', 20 * 1024 * 1024),
    ...Array.from({ length: 10 }, (_, i) => file(`${i}.txt`, 'text/plain'))])
  assert.equal(c.items.length, 10)
  assert.equal(c.items[0].file_name, 'boundary')
  assert.equal(count, 10)
  assert.equal(notices.length, 2)
  assert.ok(c.items.every(row => row.status === 'ready'))
})

test('failed upload remains in the model and retry changes error to ready with progress', async () => {
  let fail = true
  const { controller: c, models } = uploader({ api: {
    uploadAttachment: async (_session, _file, progress) => {
      progress({ loaded: 5, total: 10 })
      if (fail) throw new Error('连接中断')
      return metadata()
    },
  } })
  await c.addFiles([file()])
  assert.equal(c.items[0].status, 'error')
  assert.equal(c.items[0].error, '连接中断')
  assert.equal(c.isUploading, false)
  assert.ok(models.some(rows => rows[0]?.progress === 50))
  fail = false
  await c.retry(c.items[0].localId)
  assert.equal(c.items[0].attachment_id, 'A1')
  assert.equal(c.items[0].status, 'ready')
  assert.equal(c.items[0].progress, 100)
  assert.equal(c.items[0].error, undefined)
})

test('disabled uploader rejects adding, removing and retrying without changing the draft', async () => {
  let disabled = false
  const { controller: c } = uploader({ disabled: () => disabled, api: { uploadAttachment: async () => { throw new Error('failed') } } })
  await c.addFiles([file()])
  const before = c.items
  disabled = true
  await c.addFiles([file()])
  await c.remove(before[0].localId)
  await c.retry(before[0].localId)
  assert.equal(c.items, before)
})

test('upload queue uses at most two requests and removing a queued file never uploads it', async () => {
  const pending = [deferred(), deferred(), deferred()]
  const submitted = []
  const { controller: c } = uploader({ api: {
    uploadAttachment: (_s, f) => { submitted.push(f.name); return pending[submitted.length - 1].promise },
  } })
  const adding = c.addFiles([file('one'), file('two'), file('remove'), file('four')])
  assert.deepEqual(submitted, ['one', 'two'])
  assert.equal(c.items.length, 4)
  await c.remove(c.items[2].localId)
  pending[0].resolve(metadata('one'))
  await new Promise(resolve => setImmediate(resolve))
  assert.deepEqual(submitted, ['one', 'two', 'four'])
  pending[1].resolve(metadata('two'))
  pending[2].resolve(metadata('four'))
  await adding
  assert.ok(c.items.every(row => row.status === 'ready'))
})

test('number progress callbacks update the model and preserve room for server completion', async () => {
  const pending = deferred()
  let progress
  const { controller: c } = uploader({ api: {
    uploadAttachment: (_s, _f, callback) => { progress = callback; return pending.promise },
  } })
  const adding = c.addFiles([file()])
  progress(42)
  assert.equal(c.items[0].progress, 42)
  progress(100)
  assert.equal(c.items[0].status, 'uploading')
  pending.resolve(metadata())
  await adding
  assert.equal(c.items[0].progress, 100)
})

test('server dedup keeps one ready row and never deletes its shared attachment ID', async () => {
  const { controller: c, removed, urlApi } = uploader()
  await c.addFiles([file('one.png'), file('two.png')])
  assert.equal(c.items.length, 1)
  assert.equal(c.items[0].attachment_id, 'A1')
  assert.equal(urlApi.revoked.length, 1)
  assert.deepEqual(removed, [])
  c.clear()
  c.dispose()
  assert.deepEqual(removed, [])
  assert.equal(urlApi.revoked.length, 2)
})

test('removing a ready duplicate waits for pending uploads before deleting a shared ID', async () => {
  const pending = deferred()
  let calls = 0
  const { controller: c, removed } = uploader({ api: {
    uploadAttachment: () => ++calls === 1 ? Promise.resolve(metadata()) : pending.promise,
  } })
  await c.addFiles([file('one.png')])
  const adding = c.addFiles([file('two.png')])
  await c.remove(c.items[0].localId)
  assert.deepEqual(removed, [])
  pending.resolve(metadata())
  await adding
  assert.equal(c.items[0].status, 'ready')
  assert.deepEqual(removed, [])
  await c.remove(c.items[0].localId)
  assert.deepEqual(removed, [['S1', 'A1']])
})

test('re-upload waits for in-flight DELETE so dedup cannot return an ID about to be deleted', async () => {
  const deletion = deferred()
  let storedId = 'old', uploads = 0
  const { controller: c } = uploader({ api: {
    uploadAttachment: async () => {
      uploads++
      storedId ||= 'new'
      return metadata(storedId)
    },
    removeAttachment: async () => { await deletion.promise; storedId = null },
  } })
  await c.addFiles([file('original.png')])
  const removing = c.remove(c.items[0].localId)
  const adding = c.addFiles([file('same-content.png')])
  await new Promise(resolve => setImmediate(resolve))
  const uploadsBeforeDeleteFinished = uploads
  deletion.resolve()
  await Promise.all([removing, adding])
  assert.equal(c.items[0].status, 'ready')
  assert.equal(c.items[0].attachment_id, storedId, 'ready attachment must still exist on the server')
  assert.equal(c.items[0].attachment_id, 'new')
  assert.equal(uploadsBeforeDeleteFinished, 1)
  c.clear()
})

test('rejected DELETE releases same-session uploads without poisoning the queue', async () => {
  const deletion = deferred()
  let uploads = 0
  const { controller: c, notices } = uploader({ api: {
    uploadAttachment: async () => { uploads++; return metadata() },
    removeAttachment: () => deletion.promise,
  } })
  await c.addFiles([file('original.png')])
  const removing = c.remove(c.items[0].localId)
  const adding = c.addFiles([file('same-content.png')])
  await new Promise(resolve => setImmediate(resolve))
  const uploadsBeforeRejection = uploads
  deletion.reject(new Error('delete failed'))
  await Promise.all([removing, adding])
  assert.equal(uploadsBeforeRejection, 1)
  assert.equal(uploads, 2)
  assert.equal(c.items[0].status, 'ready')
  assert.equal(notices.length, 1)
  c.clear()
})

test('changing session cancels cleanup waits and another session can upload before DELETE settles', async () => {
  const deletion = deferred(), sessions = []
  const { controller: c } = uploader({ api: {
    uploadAttachment: async session => { sessions.push(session); return metadata(`${session}-${sessions.length}`) },
    removeAttachment: () => deletion.promise,
  } })
  await c.addFiles([file('original.png')])
  const removing = c.remove(c.items[0].localId)
  const waiting = c.addFiles([file('same-one.png'), file('same-two.png')])
  c.setSession('S2')
  const fresh = c.addFiles([file('new-session.png')])
  await new Promise(resolve => setImmediate(resolve))
  const beforeDeleteFinished = [...sessions]
  const freshDraft = c.items[0]
  deletion.resolve()
  await Promise.all([removing, waiting, fresh])
  assert.deepEqual(beforeDeleteFinished, ['S1', 'S2'])
  assert.equal(freshDraft.status, 'ready')
  assert.equal(freshDraft.attachment_id, 'S2-2')
  c.clear()
})

test('stalled DELETE gives waiting uploads a bounded error; retry still waits for actual completion', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const deletion = deferred()
  let uploads = 0
  const { controller: c } = uploader({ api: {
    uploadAttachment: async () => metadata(`A${++uploads}`),
    removeAttachment: () => deletion.promise,
  } })
  await c.addFiles([file('original.png')])
  const removing = c.remove(c.items[0].localId)
  const adding = c.addFiles([file('same-content.png')])
  t.mock.timers.tick(30_001)
  await new Promise(resolve => setImmediate(resolve))
  const timedOutDraft = c.items[0]
  const uploadsBeforeCompletion = uploads
  const retrying = c.retry(timedOutDraft.localId)
  await new Promise(resolve => setImmediate(resolve))
  const uploadsDuringRetry = uploads
  deletion.resolve()
  await Promise.all([removing, adding, retrying])
  assert.equal(timedOutDraft.status, 'error')
  assert.ok(timedOutDraft.error)
  assert.equal(uploadsBeforeCompletion, 1)
  assert.equal(uploadsDuringRetry, 1)
  assert.equal(c.items[0].status, 'ready')
  assert.equal(c.items[0].attachment_id, 'A2')
  c.clear()
})

test('upload waits for every in-flight DELETE in its session, not only the first one', async () => {
  const deletions = [deferred(), deferred()]
  let uploads = 0, deletes = 0
  const { controller: c } = uploader({ api: {
    uploadAttachment: async () => metadata(`A${++uploads}`),
    removeAttachment: () => deletions[deletes++].promise,
  } })
  await c.addFiles([file('one.png'), file('two.png')])
  const ids = c.items.map(row => row.localId)
  const removals = ids.map(id => c.remove(id))
  const adding = c.addFiles([file('again.png')])
  deletions[0].resolve()
  await new Promise(resolve => setImmediate(resolve))
  const uploadsAfterFirstDelete = uploads
  deletions[1].resolve()
  await Promise.all([...removals, adding])
  assert.equal(uploadsAfterFirstDelete, 2)
  assert.equal(c.items[0].attachment_id, 'A3')
  assert.equal(c.items[0].status, 'ready')
  c.clear()
})

test('late-upload cleanup does not retain either upload slot while another session needs them', async () => {
  const late = [deferred(), deferred()], deletion = deferred(), sessions = []
  const { controller: c } = uploader({ api: {
    uploadAttachment: session => {
      sessions.push(session)
      return session === 'S1' ? late[sessions.length - 1].promise : Promise.resolve(metadata('new'))
    },
    removeAttachment: () => deletion.promise,
  } })
  const old = c.addFiles([file('one.png'), file('two.png')])
  c.setSession('S2')
  late[0].resolve(metadata('old-one'))
  late[1].resolve(metadata('old-two'))
  await new Promise(resolve => setImmediate(resolve))
  const fresh = c.addFiles([file('new.png')])
  await new Promise(resolve => setImmediate(resolve))
  const beforeDeleteFinished = [...sessions]
  const freshDraft = c.items[0]
  deletion.resolve()
  await Promise.all([old, fresh])
  assert.deepEqual(beforeDeleteFinished, ['S1', 'S1', 'S2'])
  assert.equal(freshDraft.status, 'ready')
  assert.equal(freshDraft.attachment_id, 'new')
  c.clear()
})

test('late duplicate response after successful clear cannot delete a sent ID', async () => {
  const pending = deferred()
  let calls = 0
  const { controller: c, removed } = uploader({ api: {
    uploadAttachment: () => ++calls === 1 ? Promise.resolve(metadata()) : pending.promise,
  } })
  await c.addFiles([file('one.png')])
  const adding = c.addFiles([file('two.png')])
  await c.remove(c.items[1].localId)
  c.clear()
  c.dispose()
  pending.resolve(metadata())
  await adding
  assert.deepEqual(removed, [])
})

test('an identical local file is queued once, while extensionless ordinary files remain valid', async () => {
  let calls = 0
  const { controller: c } = uploader({ api: {
    uploadAttachment: async (_s, f) => ({ ...metadata(`A${++calls}`, 'application/octet-stream'), file_name: f.name }),
  } })
  const same = { ...file('README', ''), lastModified: 123 }
  await c.addFiles([same, { ...same }])
  assert.equal(c.items.length, 1)
  assert.equal(c.items[0].file_name, 'README')
  assert.equal(c.items[0].status, 'ready')
  assert.equal(c.items[0].is_image, false)
  assert.equal(calls, 1)
})

test('session change aborts upload and deletes a late response using its original session', async () => {
  const pending = deferred()
  let signal, progress
  const { controller: c, removed, urlApi } = uploader({ api: {
    uploadAttachment: (_s, _f, p, s) => { signal = s; progress = p; return pending.promise },
  } })
  const adding = c.addFiles([file()])
  assert.equal(c.isUploading, true)
  c.setSession('S2')
  assert.equal(signal.aborted, true)
  progress({ loaded: 10, total: 10 })
  pending.resolve(metadata())
  await adding
  assert.deepEqual(c.items, [])
  assert.deepEqual(removed, [['S1', 'A1']])
  assert.deepEqual(urlApi.revoked, ['blob:test-0'])
})

test('remove during upload ignores late completion and frees the preview exactly once', async () => {
  const pending = deferred()
  let signal
  const { controller: c, removed, urlApi } = uploader({ api: {
    uploadAttachment: (_s, _f, _p, s) => { signal = s; return pending.promise },
  } })
  const adding = c.addFiles([file()])
  await c.remove(c.items[0].localId)
  assert.equal(signal.aborted, true)
  pending.resolve(metadata())
  await adding
  c.dispose()
  assert.deepEqual(c.items, [])
  assert.deepEqual(removed, [['S1', 'A1']])
  assert.deepEqual(urlApi.revoked, ['blob:test-0'])
})

test('clear after sending releases local resources without deleting the sent attachment on unmount', async () => {
  const { controller: c, removed, urlApi } = uploader()
  await c.addFiles([file()])
  c.clear()
  c.dispose()
  assert.deepEqual(c.items, [])
  assert.deepEqual(removed, [])
  assert.deepEqual(urlApi.revoked, ['blob:test-0'])
})

test('unmount removes ready drafts and late uploaded drafts, but publishes no more model events', async () => {
  const pending = deferred()
  let count = 0
  const { controller: c, removed, models, urlApi } = uploader({ api: {
    uploadAttachment: async () => ++count === 1 ? metadata('ready') : pending.promise,
  } })
  await c.addFiles([file()])
  const adding = c.addFiles([file('pending.png')])
  c.dispose()
  const events = models.length
  pending.resolve(metadata('late'))
  await adding
  assert.equal(models.length, events)
  assert.deepEqual(removed, [['S1', 'ready'], ['S1', 'late']])
  assert.equal(urlApi.revoked.length, 2)
})

test('safe preview requires an explicit image flag and a raster MIME; SVG and HTML never preview', () => {
  assert.equal(attachments.isSafeAttachmentImage(metadata()), true)
  assert.equal(attachments.isSafeAttachmentImage({ ...metadata(), is_image: false }), false)
  assert.equal(attachments.isSafeAttachmentImage(metadata('svg', 'image/svg+xml')), false)
  assert.equal(attachments.isSafeAttachmentImage({ ...metadata(), content_type: 'text/html' }), false)
})

test('message blob store retries failure, revokes changed attachments and ignores old-session blobs', async () => {
  const pending = deferred(), urlApi = urls()
  let fail = true
  const store = attachments.createAttachmentBlobStore({ urlApi, api: {
    attachmentBlob: async (session) => {
      if (session === 'S2') return pending.promise
      if (fail) throw new Error('下载失败')
      return new Blob(['png'], { type: 'image/png' })
    },
  } })
  store.sync('S1', [metadata()])
  await store.load('A1')
  assert.equal(store.items[0].status, 'error')
  fail = false
  await store.load('A1')
  assert.equal(store.items[0].status, 'ready')
  assert.equal(store.items[0].url, 'blob:test-0')
  store.sync('S2', [metadata('A2')])
  const loading = store.load('A2')
  store.sync('S3', [])
  pending.resolve(new Blob(['png'], { type: 'image/png' }))
  assert.equal(await loading, null)
  assert.deepEqual(store.items, [])
  assert.deepEqual(urlApi.revoked, ['blob:test-0'])
  assert.equal(urlApi.created.length, 1)
})

test('message blob validation refuses active MIME even when metadata claims image/png', async () => {
  const urlApi = urls()
  const store = attachments.createAttachmentBlobStore({ urlApi, api: {
    attachmentBlob: async () => new Blob(['<svg/>'], { type: 'image/svg+xml' }),
  } })
  store.sync('S1', [metadata()])
  assert.equal(await store.load('A1'), null)
  assert.equal(store.items[0].status, 'error')
  assert.equal(urlApi.created.length, 0)
})

test('blob store shares in-flight loads and releases a loaded URL on attachment removal or disposal', async () => {
  const urlApi = urls(), pending = deferred()
  let calls = 0
  const store = attachments.createAttachmentBlobStore({ urlApi, api: {
    attachmentBlob: () => { calls++; return pending.promise },
  } })
  store.sync('S1', [metadata()])
  const one = store.load('A1'), two = store.load('A1')
  pending.resolve(new Blob(['png'], { type: 'image/png' }))
  await Promise.all([one, two])
  assert.equal(calls, 1)
  store.sync('S1', [])
  store.dispose()
  assert.deepEqual(urlApi.revoked, ['blob:test-0'])
})

test('image decode retry replaces and releases its previous URL', async () => {
  const urlApi = urls()
  const store = attachments.createAttachmentBlobStore({ urlApi, api: {
    attachmentBlob: async () => new Blob(['png'], { type: 'image/png' }),
  } })
  store.sync('S1', [metadata()])
  await store.load('A1')
  await store.load('A1', { reload: true })
  assert.equal(store.items[0].url, 'blob:test-1')
  assert.deepEqual(urlApi.revoked, ['blob:test-0'])
  store.dispose()
  assert.deepEqual(urlApi.revoked, ['blob:test-0', 'blob:test-1'])
})

test('download uses a sanitized filename and removes its temporary anchor even if clicking throws', () => {
  let anchor, removed = false
  const documentApi = {
    createElement(tag) {
      assert.equal(tag, 'a')
      anchor = { click() { throw new Error('blocked') }, remove() { removed = true } }
      return anchor
    },
    body: { appendChild() {} },
  }
  assert.throws(() => attachments.downloadAttachmentUrl('blob:download', '../bad\\name\u202e.html\u0000', documentApi), /blocked/)
  assert.equal(anchor.href, 'blob:download')
  assert.equal(/[\\/\u0000\u202e]/.test(anchor.download), false)
  assert.equal(anchor.rel, 'noopener noreferrer')
  assert.equal(removed, true)
})

// Real SFC setup + Vue effects. Only browser/network boundaries and lifecycle
// registration are replaced; assertions exercise the component's public API.
function component(name, props, api, urlApi = urls()) {
  const source = readFileSync(new URL(`../src/components/${name}.vue`, import.meta.url), 'utf8')
  const { descriptor, errors } = parse(source)
  assert.deepEqual(errors, [])
  const compiled = compileScript(descriptor, { id: name })
  const template = compileTemplate({ source: descriptor.template.content, filename: name, id: name,
    compilerOptions: { bindingMetadata: compiled.bindings } })
  assert.deepEqual(template.errors, [])
  const unmount = [], mounted = [], events = [], exposed = {}
  const modules = {
    vue: { ...vue, resolveComponent: name => name, onBeforeUnmount: fn => unmount.push(fn), onMounted: fn => mounted.push(fn) },
    '@element-plus/icons-vue': icons,
    '../api/consultation.js': { consultationApi: api },
    '../utils/chatAttachments.js': {
      ...attachments,
      createAttachmentUploader: options => attachments.createAttachmentUploader({ ...options, urlApi }),
      createAttachmentBlobStore: options => attachments.createAttachmentBlobStore({ ...options, urlApi }),
    },
  }
  const code = compiled.content.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g,
    (_, names, path) => `const {${names.replace(/\bas\b/g, ':')}} = modules[${JSON.stringify(path)}]`)
    .replace('export default', 'return')
  const options = new Function('modules', code)(modules)
  const renderCode = template.code.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g,
    (_, names, path) => `const {${names.replace(/\bas\b/g, ':')}} = modules[${JSON.stringify(path)}]`)
    .replace('export function render', 'return function render')
  const render = new Function('modules', renderCode)(modules)
  const scope = vue.effectScope()
  const reactiveProps = vue.reactive(props)
  const state = scope.run(() => options.setup(reactiveProps, {
    expose: value => Object.assign(exposed, value),
    emit: (event, value) => { events.push([event, value]); if (event === 'update:modelValue') reactiveProps.modelValue = value },
  }))
  mounted.forEach(fn => fn())
  return { state, exposed, events, props: reactiveProps, urlApi,
    render: () => render(vue.proxyRefs(state), [], reactiveProps, vue.proxyRefs(state)),
    unmount() { unmount.forEach(fn => fn()); scope.stop() },
  }
}

test('uploader SFC exposes reactive uploading state, emits draft metadata and honors successful clear', async () => {
  const pending = deferred(), removed = []
  const c = component('ChatAttachmentUploader', { sessionId: 'S1', disabled: false, modelValue: [] }, {
    uploadAttachment: () => pending.promise, removeAttachment: async (...args) => removed.push(args),
  })
  const uploading = c.exposed.addFiles([file()])
  assert.equal(vue.unref(c.exposed.isUploading), true)
  pending.resolve(metadata())
  await uploading
  await vue.nextTick()
  assert.equal(vue.unref(c.exposed.isUploading), false)
  assert.equal(c.props.modelValue[0].attachment_id, 'A1')
  c.exposed.clear()
  c.unmount()
  assert.deepEqual(c.props.modelValue, [])
  assert.deepEqual(removed, [])
  assert.deepEqual(c.urlApi.revoked, ['blob:test-0'])
})

test('terminal unmount cleans independent snapshot even when parent clears model first', async () => {
  const removed = []
  const c = component('ChatAttachmentUploader', { sessionId: 'S1', disabled: false, modelValue: [] }, {
    uploadAttachment: async () => metadata(), removeAttachment: async (...args) => removed.push(args),
  })
  await c.exposed.addFiles([file()])
  await vue.nextTick()
  c.props.modelValue = []
  c.unmount()
  await vue.nextTick()
  assert.deepEqual(removed, [['S1', 'A1']])
  assert.deepEqual(c.urlApi.revoked, ['blob:test-0'])
})

test('parent model removal before terminal unmount cleans the draft once', async () => {
  const removed = []
  const c = component('ChatAttachmentUploader', { sessionId: 'S1', disabled: false, modelValue: [] }, {
    uploadAttachment: async () => metadata(), removeAttachment: async (...args) => removed.push(args),
  })
  await c.exposed.addFiles([file()])
  await vue.nextTick()
  c.props.modelValue = []
  await vue.nextTick()
  c.unmount()
  assert.deepEqual(removed, [['S1', 'A1']])
})

test('compiled uploader drop handler stops bubbling and handles files once', async () => {
  let calls = 0, prevented = 0, stopped = 0
  const c = component('ChatAttachmentUploader', { sessionId: 'S1', disabled: false, modelValue: [] }, {
    uploadAttachment: async () => { calls++; return metadata() }, removeAttachment: async () => {},
  })
  const tree = c.render()
  tree.props.onDrop({ dataTransfer: { files: [file()] },
    preventDefault() { prevented++ }, stopPropagation() { stopped++ },
  })
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(prevented, 1)
  assert.equal(stopped, 1)
  assert.equal(calls, 1)
  assert.equal(c.props.modelValue[0].status, 'ready')
  c.exposed.clear()
  c.unmount()
})

test('component session switch suppresses late responses while a new-session upload succeeds', async () => {
  const old = deferred(), removed = []
  const c = component('ChatAttachmentUploader', { sessionId: 'S1', disabled: false, modelValue: [] }, {
    uploadAttachment: async session => session === 'S1' ? old.promise : metadata('new'),
    removeAttachment: async (...args) => removed.push(args),
  })
  const adding = c.exposed.addFiles([file('old.png')])
  c.props.sessionId = 'S2'
  await c.exposed.addFiles([file('new.png')])
  old.resolve(metadata('old'))
  await adding
  await vue.nextTick()
  assert.deepEqual(c.props.modelValue.map(row => row.attachment_id), ['new'])
  assert.deepEqual(removed, [['S1', 'old']])
  c.exposed.clear()
  c.unmount()
})

test('remounting S1 after S2 waits for old instance DELETE before uploading the same file', async t => {
  const deletion = deferred(), instances = [], pending = [], sessions = []
  let storedId = 'old'
  const api = {
    uploadAttachment: async session => {
      sessions.push(session)
      if (session === 'S2') return metadata('other-session')
      storedId ||= 'new'
      return metadata(storedId)
    },
    removeAttachment: async session => {
      if (session === 'S1') { await deletion.promise; storedId = null }
    },
  }
  const mount = sessionId => {
    const instance = component('ChatAttachmentUploader', { sessionId, disabled: false, modelValue: [] }, api)
    instances.push(instance)
    return instance
  }
  t.after(async () => {
    // Even a failed assertion must settle the shared DELETE barrier so it
    // cannot block another test's S1 controller.
    deletion.resolve()
    await Promise.allSettled(pending)
    for (const instance of instances) { instance.exposed.clear(); instance.unmount() }
    await new Promise(resolve => setImmediate(resolve))
  })
  const sameFile = file('same-file.png')
  const old = mount('S1')
  await old.exposed.addFiles([sameFile])
  old.unmount()
  const other = mount('S2')
  const otherUpload = other.exposed.addFiles([file('other.png')])
  pending.push(otherUpload)
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(other.props.modelValue[0].status, 'ready', 'another session must not wait for S1 cleanup')
  other.exposed.clear()
  other.unmount()
  const fresh = mount('S1')
  const reupload = fresh.exposed.addFiles([sameFile])
  pending.push(reupload)
  await new Promise(resolve => setImmediate(resolve))
  const beforeDeleteFinished = [...sessions]
  deletion.resolve()
  await reupload
  assert.equal(fresh.props.modelValue[0].attachment_id, storedId, 'the remounted ready attachment must still exist')
  assert.equal(fresh.props.modelValue[0].attachment_id, 'new')
  assert.equal(fresh.props.modelValue[0].status, 'ready')
  assert.deepEqual(beforeDeleteFinished, ['S1', 'S2'])
})

test('rejected old-instance DELETE releases a remounted same-session controller', async t => {
  const deletion = deferred(), instances = [], pending = []
  let uploads = 0
  const api = {
    uploadAttachment: async () => { uploads++; return metadata('retained') },
    removeAttachment: () => deletion.promise,
  }
  t.after(async () => {
    deletion.resolve()
    await Promise.allSettled(pending)
    for (const instance of instances) { instance.clear(); instance.dispose() }
    await new Promise(resolve => setImmediate(resolve))
  })
  const old = uploader({ api }).controller
  instances.push(old)
  await old.addFiles([file()])
  old.dispose()
  const fresh = uploader({ api }).controller
  instances.push(fresh)
  const adding = fresh.addFiles([file()])
  pending.push(adding)
  await new Promise(resolve => setImmediate(resolve))
  const beforeRejection = uploads
  deletion.reject(new Error('delete rejected'))
  await adding
  assert.equal(beforeRejection, 1)
  assert.equal(fresh.items[0].status, 'ready')
  assert.equal(fresh.items[0].attachment_id, 'retained')
  assert.equal(uploads, 2)
})

test('message SFC loads authenticated images, reacts to attachment changes and frees URLs on unmount', async () => {
  const c = component('ChatMessageAttachments', { sessionId: 'S1', attachments: [metadata()] }, {
    attachmentBlob: async () => new Blob(['png'], { type: 'image/png' }),
  })
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(c.urlApi.created.length, 1)
  c.props.attachments = [metadata('B1', 'text/html')]
  await vue.nextTick()
  assert.deepEqual(c.urlApi.revoked, ['blob:test-0'])
  assert.equal(c.urlApi.created.length, 1)
  c.props.attachments = [metadata('A2')]
  await new Promise(resolve => setImmediate(resolve))
  c.unmount()
  assert.equal(c.urlApi.revoked.length, 2)
})
