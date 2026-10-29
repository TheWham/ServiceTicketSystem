import axios from 'axios'
import { useUserStore } from '../stores/user.js'

/**
 * 咨询服务(智能客服/转人工)专用客户端。
 *
 * 不复用 api/index.js 的实例,原因有三:
 * 1. 响应包络不同 —— 咨询服务按 PRD 21.1 返回 {code:"SUCCESS", message, request_id, data},
 *    旧服务返回 {code:0, msg, data},两套错误判定逻辑没法共存;
 * 2. 咨询服务强制要求每个请求带 X-Request-Id,写接口还要带 Idempotency-Key(AI-002);
 * 3. AI 问答要调大模型,实测 10~70 秒,旧实例 15 秒的超时必然误杀。
 */

/** 默认超时。AI 问答单独放宽。 */
const DEFAULT_TIMEOUT = 20000
const AI_TIMEOUT = 180000

const http = axios.create({
  baseURL: '/api/v1',
  timeout: DEFAULT_TIMEOUT,
  headers: { 'Content-Type': 'application/json' }
})

function randomId(prefix) {
  const uuid = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID().replace(/-/g, '')
    : Math.random().toString(36).slice(2) + Date.now().toString(36)
  return `${prefix}_${uuid}`
}

/** 每个请求都带 X-Request-Id;写请求自动补 Idempotency-Key(调用方已给的优先)。 */
http.interceptors.request.use(config => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers['Authorization'] = `Bearer ${userStore.token}`
  }
  config.headers['X-Request-Id'] = config.headers['X-Request-Id'] || randomId('req')

  const method = (config.method || 'get').toLowerCase()
  if (method !== 'get' && !config.headers['Idempotency-Key']) {
    config.headers['Idempotency-Key'] = randomId('idem')
  }
  return config
})

/**
 * 成功时直接把 data 交给调用方;失败时抛出带业务码的 Error。
 * 字段级错误(PRD 21.1 errors 数组)拼进消息,方便直接展示。
 */
http.interceptors.response.use(
  res => res.config?.responseType === 'blob' ? res.data : res.data?.data,
  async err => {
    let body = err.response?.data
    if (typeof Blob !== 'undefined' && body instanceof Blob) {
      try { body = JSON.parse(await body.text()) } catch { body = null }
    }
    let msg = body?.message || err.message || '网络错误'
    if (Array.isArray(body?.errors) && body.errors.length) {
      msg = body.errors.map(e => `${e.field}: ${e.message || e.reason}`).join('；')
    }
    if (err.code === 'ECONNABORTED') {
      msg = err.config?.url?.includes('/ai-messages')
        ? 'AI 响应超时，可以转人工或直接提交工单' : '请求超时，请稍后重试'
    }
    const error = new Error(msg)
    error.code = body?.code || 'NETWORK_ERROR'
    error.requestId = body?.request_id
    error.errors = body?.errors
    return Promise.reject(error)
  }
)

export const consultationApi = {
  /** AI-API-001 创建咨询。source: AI | HUMAN_DIRECT | TICKET_FOLLOW_UP */
  create: (source, categoryId) =>
    http.post('/consultations', categoryId ? { source, categoryId } : { source }),

  /** OpenAPI 05 listConsultations */
  list: (page = 1, pageSize = 20) =>
    http.get('/consultations', { params: { page, pageSize } }),

  get: (id) => http.get(`/consultations/${id}`),

  /** 员工排队人数:只有已绑定工程师时 assigned 才为 true。 */
  queueStatus: (id) => http.get(`/consultations/${id}/queue-status`),

  /** AI-API-002 发送 AI 消息。超时单独放宽到 3 分钟。 */
  aiMessage: (id, message, contextRefs) =>
    http.post(`/consultations/${id}/ai-messages`,
      contextRefs ? { message, contextRefs } : { message },
      { timeout: AI_TIMEOUT }),

  /** AI-API-003 反馈。feedback: HELPFUL | NOT_HELPFUL | INCORRECT */
  feedback: (id, interactionId, feedback, comment) =>
    http.post(`/consultations/${id}/feedback`,
      comment ? { interactionId, feedback, comment } : { interactionId, feedback }),

  /** AI-API-004 转人工。不接受指定工程师。 */
  transfer: (id, categoryId) =>
    http.post(`/consultations/${id}/transfer`, { categoryId }),

  /** OpenAPI 05 人工消息。clientMessageId 用于重发防重(RD-002)。 */
  sendMessage: (id, content, clientMessageId, attachmentIds = []) =>
    http.post(`/consultations/${id}/messages`, {
      ...(content?.trim() ? { content } : {}),
      ...(attachmentIds.length ? { attachment_ids: attachmentIds } : {}),
      client_message_id: clientMessageId || randomId('cmsg')
    }),

  /** 聊天附件先上传为草稿，发送消息时以 attachment_ids 绑定。 */
  uploadAttachment: (id, file, onProgress, signal) => {
    const data = new FormData()
    data.append('file', file)
    return http.post(`/consultations/${id}/attachments`, data, {
      headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000, signal,
      onUploadProgress: event => onProgress?.(event.total ? Math.round(event.loaded * 100 / event.total) : 0)
    })
  },
  removeAttachment: (id, attachmentId) => http.delete(`/consultations/${id}/attachments/${attachmentId}`),
  attachmentBlob: (id, attachmentId) => http.get(`/consultations/${id}/attachments/${attachmentId}/content`, {
    responseType: 'blob', timeout: 120000
  }),

  listMessages: (id, page = 1, pageSize = 100) =>
    http.get(`/consultations/${id}/messages`, { params: { page, pageSize } }),

  /** 工程师提交解决结论 */
  submitResolution: (id, conclusion) =>
    http.post(`/consultations/${id}/resolution`, { conclusion }),

  /** 员工确认解决 */
  confirm: (id) => http.post(`/consultations/${id}/confirmation`),

  /** 员工主动结束。原因由具体操作场景提供,无需用户额外填写。 */
  close: (id, reason = '员工主动结束咨询') => http.post(`/consultations/${id}/close`, { reason }),

  /** 24 小时内恢复 */
  reopen: (id, reason) => http.post(`/consultations/${id}/reopen`, { reason }),

  /** OpenAPI 05 getTicketDraftFromConsultation:咨询转单预填(员工可修改) */
  ticketDraft: (id) => http.get(`/consultations/${id}/ticket-draft`),

  /** AI-API-005 知识搜索,只返回已发布版本 */
  searchKnowledge: (query, category, page = 1, pageSize = 10) =>
    http.get('/knowledge/search', { params: { query, category, page, pageSize } })
}

/** 咨询状态的中文标签与 Element Plus tag 类型。 */
export const CONSULTATION_STATUS = {
  AI_ACTIVE: { label: 'AI 咨询中', type: 'primary' },
  WAITING_ENGINEER: { label: '等待工程师', type: 'warning' },
  HUMAN_ACTIVE: { label: '工程师处理中', type: 'warning' },
  PENDING_CONFIRMATION: { label: '待你确认', type: 'success' },
  RESOLVED: { label: '已解决', type: 'success' },
  CONVERTED_TO_TICKET: { label: '已转工单', type: 'info' },
  CLOSED: { label: '已结束', type: 'info' }
}

/** 拒答原因的用户可读说明(AI-003 AiRefusalReason)。 */
export const REFUSAL_REASON = {
  NO_RELIABLE_KNOWLEDGE: '目前无法提供可靠的处理建议，请补充问题细节或转人工',
  LOW_CONFIDENCE: '目前信息不足，无法有把握地给出处理建议，请补充说明或转人工',
  CONFLICTING_KNOWLEDGE: '相关知识之间存在冲突，需要人工判断',
  HIGH_RISK_TOPIC: '该请求涉及未经授权、绕过安全控制或需要人工核实的操作，请联系 IT 人员处理',
  MODEL_UNAVAILABLE: 'AI 服务暂时不可用',
  POLICY_BLOCKED: 'AI 综合回答当前未开放',
  OFF_TOPIC: '抱歉，这个问题不属于 IT 或电脑技术范围，不能答复。我可以帮助你处理电脑、网络、软件、编程和设备使用等问题。'
}

export const TERMINAL_STATUS = ['RESOLVED', 'CONVERTED_TO_TICKET', 'CLOSED']

/**
 * 工程师提单快捷入口消息的固定内容(PRD 9.1:人工咨询中由工程师发送快捷入口,
 * 员工确认表单后提交,不得静默代替员工)。两端聊天组件按此精确匹配渲染成卡片。
 */
export const TICKET_ENTRY_MESSAGE = '[提交工单入口]'

export default http
