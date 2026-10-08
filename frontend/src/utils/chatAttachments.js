export const MAX_CHAT_ATTACHMENTS = 10
export const MAX_CHAT_ATTACHMENT_SIZE = 20 * 1024 * 1024
const SAFE_IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/avif', 'image/bmp'])
const mime = value => String(value || '').split(';', 1)[0].trim().toLowerCase()

export function isSafeAttachmentImage(attachment) {
  return attachment?.is_image === true && SAFE_IMAGE_TYPES.has(mime(attachment.content_type))
}

export function formatAttachmentSize(size) {
  const bytes = Math.max(0, Number(size) || 0)
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function safeAttachmentFilename(name) {
  const cleaned = String(name || '').replace(/[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069<>:"/\\|?*]/g, '_')
    .replace(/^\.+/, '').replace(/[.\s]+$/, '').trim().slice(0, 180)
  return cleaned && !/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(cleaned) ? cleaned : 'attachment'
}

// The URL remains owned by the message's blob store until replacement/unmount.
export function downloadAttachmentUrl(url, name, documentApi = document) {
  const anchor = documentApi.createElement('a')
  anchor.href = url
  anchor.download = safeAttachmentFilename(name)
  anchor.rel = 'noopener noreferrer'
  try {
    documentApi.body.appendChild(anchor)
    anchor.click()
  } finally {
    anchor.remove()
  }
}

function errorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback
}

let nextLocalId = 0
// DELETE requests outlive keyed component instances. Share only their active
// promises by session; startCleanup removes each entry when the request settles.
const inFlightDeletes = new Map()

/** Owns unsent drafts only. clear() hands ready attachments to the sent message;
 * remove/session change/dispose discard drafts. A late upload always retains
 * its original session for cleanup, even when AbortSignal is ignored by transport.
 */
export function createAttachmentUploader({ sessionId = '', api, disabled = () => false,
  onChange = () => {}, onNotice = () => {}, urlApi = URL }) {
  let items = [], revision = 0, disposed = false, running = 0
  const tasks = new Map()
  const outstanding = new Set()
  const queue = []
  const pendingDeletes = new Map()
  const sentIds = new Set()
  const attachmentKey = (session, id) => JSON.stringify([session, id])
  const previews = new Map()
  const publish = () => { if (!disposed) onChange(items) }
  const update = (id, patch) => {
    items = items.map(row => row.localId === id ? { ...row, ...patch } : row)
    publish()
  }
  const queueCleanup = (session, id) => {
    if (id) pendingDeletes.set(attachmentKey(session, id), { session, id })
  }
  const startCleanup = (session, id) => {
    let finish
    const completion = new Promise(resolve => { finish = resolve })
    const active = inFlightDeletes.get(session) || new Set()
    active.add(completion)
    inFlightDeletes.set(session, active)
    // Register the barrier before calling the API: newly added files must not
    // deduplicate against an ID whose DELETE has already been sent.
    void (async () => {
      try { await api.removeAttachment(session, id) }
      catch { if (!disposed) onNotice('服务器附件草稿未能清理。') }
      finally {
        active.delete(completion)
        if (!active.size) inFlightDeletes.delete(session)
        finish()
      }
    })()
    return completion
  }
  const waitForCleanup = task => new Promise((resolve, reject) => {
    const signal = task.controller.signal
    let settled = false
    const finish = error => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      signal.removeEventListener('abort', onAbort)
      if (error) reject(error)
      else resolve()
    }
    const onAbort = () => finish(new Error('附件上传已取消。'))
    // Timing out fails this attempt; it never releases the DELETE barrier.
    // Retrying while the server is still deleting must wait again.
    const timer = setTimeout(() => finish(new Error('等待附件清理超时，请稍后重试。')), 30_000)
    signal.addEventListener('abort', onAbort, { once: true })
    const check = () => {
      if (settled) return
      const active = inFlightDeletes.get(task.session)
      if (!active?.size) finish()
      else void Promise.all([...active]).then(check)
    }
    if (signal.aborted) onAbort()
    else check()
  })
  const drainCleanup = async () => {
    const removals = []
    for (const [key, { session, id }] of pendingDeletes) {
      // A not-yet-finished upload may resolve to the very same server ID.
      if ([...outstanding].some(task => task.session === session)) continue
      pendingDeletes.delete(key)
      if (sentIds.has(key) || (session === sessionId && items.some(row => row.attachment_id === id))) continue
      removals.push(startCleanup(session, id))
    }
    await Promise.all(removals)
  }
  const releasePreview = id => {
    const url = previews.get(id)
    if (url) urlApi.revokeObjectURL(url)
    previews.delete(id)
  }
  const discard = (row, deleteDraft) => {
    const task = tasks.get(row.localId)
    task?.controller.abort()
    tasks.delete(row.localId)
    if (task && !task.started) {
      const index = queue.indexOf(task)
      if (index >= 0) queue.splice(index, 1)
      outstanding.delete(task)
      task.resolve()
    }
    releasePreview(row.localId)
    if (deleteDraft) queueCleanup(sessionId, row.attachment_id)
  }
  const reset = deleteDrafts => {
    revision++
    items.forEach(row => { void discard(row, deleteDrafts) })
    items = []
    publish()
    void drainCleanup()
  }

  async function runUpload(task) {
    const { row, id } = task
    const current = () => !disposed && revision === task.revision && tasks.get(id) === task
    try {
      if (inFlightDeletes.get(task.session)?.size) await waitForCleanup(task)
      if (!current()) return
      const result = await api.uploadAttachment(task.session, row.file, event => {
        if (!current()) return
        const progress = typeof event === 'number' ? event
          : event?.total > 0 ? event.loaded / event.total * 100 : (event?.progress || 0) * 100
        if (Number.isFinite(progress)) update(id, { progress: Math.max(0, Math.min(99, Math.round(progress))) })
      }, task.controller.signal)
      if (!current()) {
        queueCleanup(task.session, result?.attachment_id)
        return
      }
      if (!result?.attachment_id) throw new Error('上传响应缺少附件编号，请重试。')
      if (items.some(item => item.localId !== id && item.attachment_id === result.attachment_id && item.status === 'ready')) {
        releasePreview(id)
        items = items.filter(item => item.localId !== id)
        publish()
        return
      }
      update(id, {
        attachment_id: result.attachment_id,
        file_name: result.file_name || row.file_name,
        content_type: result.content_type || row.content_type,
        size: result.size ?? row.size,
        is_image: result.is_image === true,
        status: 'ready', progress: 100, error: undefined,
      })
    } catch (error) {
      if (current()) update(id, { status: 'error', error: errorMessage(error, '上传失败，请重试。') })
    } finally {
      if (tasks.get(id) === task) tasks.delete(id)
      outstanding.delete(task)
      // Cleanup owns a separate per-session barrier, not an upload slot.
      // A slow old-session DELETE must not hold up another session's uploads.
      void drainCleanup()
    }
  }

  function pump() {
    while (running < 2 && queue.length) {
      const task = queue.shift()
      task.started = true
      running++
      void runUpload(task).finally(() => {
        running--
        task.resolve()
        pump()
      })
    }
  }
  function upload(id) {
    const row = items.find(item => item.localId === id)
    if (!row || disposed) return Promise.resolve()
    const task = { row, id, session: sessionId, revision, controller: new AbortController(), started: false }
    const completion = new Promise(resolve => { task.resolve = resolve })
    tasks.set(id, task)
    outstanding.add(task)
    update(id, { status: 'uploading', progress: 0, error: undefined })
    queue.push(task)
    pump()
    return completion
  }

  return {
    get items() { return items },
    get isUploading() { return items.some(row => row.status === 'uploading') },
    async addFiles(files) {
      if (disposed || disabled()) return
      if (!sessionId) { onNotice('会话准备就绪后才能上传附件。'); return }
      const added = []
      for (const file of Array.from(files || [])) {
        if (!file || !Number.isFinite(file.size) || file.size < 0) continue
        if ([...items, ...added].some(row => row.file === file || (Number.isFinite(file.lastModified)
          && row.file?.name === file.name && row.file?.size === file.size && row.file?.lastModified === file.lastModified))) continue
        if (file.size > MAX_CHAT_ATTACHMENT_SIZE) { onNotice(`${file.name} 超过单个文件 20 MB 限制。`); continue }
        if (items.length + added.length >= MAX_CHAT_ATTACHMENTS) { onNotice('每条消息最多添加 10 个附件。'); break }
        const localId = `chat-file-${++nextLocalId}`
        const row = { localId, file, file_name: file.name || 'attachment', size: file.size,
          content_type: file.type || 'application/octet-stream', is_image: SAFE_IMAGE_TYPES.has(mime(file.type)),
          status: 'uploading', progress: 0 }
        if (isSafeAttachmentImage(row)) {
          try { row.preview_url = urlApi.createObjectURL(file); previews.set(localId, row.preview_url) }
          catch { /* Upload still works when a local thumbnail cannot be created. */ }
        }
        added.push(row)
      }
      items = [...items, ...added]
      publish()
      await Promise.all(added.map(row => upload(row.localId)))
    },
    retry(id) {
      if (disposed || disabled() || !sessionId || items.find(row => row.localId === id)?.status !== 'error') return
      return upload(id)
    },
    remove(id) {
      if (disposed || disabled()) return
      const row = items.find(item => item.localId === id)
      if (!row) return
      discard(row, true)
      items = items.filter(item => item.localId !== id)
      publish()
      return drainCleanup()
    },
    // For controlled v-model updates. The parent calls clear() after successful
    // send, before replacing the model; ordinary external removals discard drafts.
    syncModel(model) {
      if (disposed || model === items) return
      const next = Array.isArray(model) ? model : []
      const ids = new Set(next.map(row => row.localId))
      items.filter(row => !ids.has(row.localId)).forEach(row => { void discard(row, true) })
      items = next.map(row => {
        const owned = items.find(item => item.localId === row.localId)
        return owned || row
      })
      publish()
      void drainCleanup()
    },
    clear() {
      if (disposed) return
      items.forEach(row => { if (row.attachment_id) sentIds.add(attachmentKey(sessionId, row.attachment_id)) })
      reset(false)
    },
    setSession(next) {
      if (disposed || next === sessionId) return
      reset(true)
      sessionId = next || ''
    },
    dispose() {
      if (disposed) return
      disposed = true
      reset(true)
    },
  }
}

/** Authenticated downloads are cached per session + attachment. Stale requests
 * may complete, but never allocate URLs or publish into a different message.
 */
export function createAttachmentBlobStore({ api, onChange = () => {}, urlApi = URL }) {
  let sessionId = '', entries = new Map(), disposed = false
  const publish = () => { if (!disposed) onChange([...entries.values()].map(entry => entry.state)) }
  const release = entry => { if (entry.state.url) urlApi.revokeObjectURL(entry.state.url) }
  const identity = attachment => JSON.stringify([attachment.content_type, attachment.is_image, attachment.size, attachment.file_name])
  return {
    get items() { return [...entries.values()].map(entry => entry.state) },
    sync(session, attachments) {
      if (disposed) return
      const next = new Map()
      for (const attachment of attachments || []) {
        const id = attachment.attachment_id
        if (!id || next.has(id)) continue
        const previous = session === sessionId ? entries.get(id) : null
        next.set(id, previous && identity(previous.state.attachment) === identity(attachment) ? previous
          : { state: { attachment: { ...attachment }, status: 'idle', url: '', error: '' }, promise: null })
      }
      for (const [id, entry] of entries) if (next.get(id) !== entry) release(entry)
      sessionId = session || ''
      entries = next
      publish()
    },
    async load(id, { reload = false } = {}) {
      const entry = entries.get(id)
      if (disposed || !entry || !sessionId) return null
      if (entry.promise) return entry.promise
      if (entry.state.status === 'ready' && !reload) return entry.state
      if (reload) release(entry)
      const session = sessionId
      const current = () => !disposed && sessionId === session && entries.get(id) === entry
      entry.state = { ...entry.state, status: 'loading', url: '', error: '' }
      publish()
      entry.promise = (async () => {
        try {
          const blob = await api.attachmentBlob(session, id)
          if (!current()) return null
          if (isSafeAttachmentImage(entry.state.attachment) && !SAFE_IMAGE_TYPES.has(mime(blob.type))) {
            throw new Error('图片内容类型不安全，无法预览。')
          }
          const url = urlApi.createObjectURL(blob)
          entry.state = { ...entry.state, status: 'ready', url, error: '' }
          publish()
          return entry.state
        } catch (error) {
          if (current()) {
            entry.state = { ...entry.state, status: 'error', error: errorMessage(error, '附件加载失败，请重试。') }
            publish()
          }
          return null
        } finally {
          entry.promise = null
        }
      })()
      return entry.promise
    },
    dispose() {
      disposed = true
      entries.forEach(release)
      entries = new Map()
    },
  }
}
