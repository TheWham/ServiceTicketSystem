import axios from 'axios'
import { useUserStore } from '../stores/user.js'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

function randomId(prefix) {
  const uuid = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID().replace(/-/g, '')
    : Math.random().toString(36).slice(2) + Date.now().toString(36)
  return `${prefix}_${uuid}`
}

// 请求拦截：注入 JWT（Spring Cloud 网关统一鉴权）
// + 契约头:X-Request-Id 每请求必带;写请求带 Idempotency-Key(spec 05 / PRD 21.1,RD-002)
api.interceptors.request.use(config => {
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

// 响应拦截：统一错误处理
api.interceptors.response.use(
  res => res.data,
  err => {
    const msg = err.response?.data?.message || err.response?.data?.msg || err.message || '网络错误'
    console.error('[API Error]', msg)
    return Promise.reject(new Error(msg))
  }
)

// ---- 用户 API ----
export const userApi = {
  login: (data) => api.post('/users/login', data),
  loginOptions: () => api.get('/users/login-options'),
  getMe: () => api.get('/users/me'),
  listUsers: (params) => api.get('/users', { params }),
  // 认证模块：忘记密码(免登录)/修改密码
  forgotPassword: (data) => api.post('/users/forgot-password', data),
  changePassword: (data) => api.post('/users/change-password', data),
  // 平台管理员账号管理
  listAccounts: () => api.get('/users/accounts'),
  createAccount: (data) => api.post('/users/accounts', data),
  resetPassword: (userId, data) => api.post(`/users/accounts/${userId}/reset-password`, data)
}

// ---- 工单 API ----
export const ticketApi = {
  // config 可透传 { headers: { 'Idempotency-Key': ... } }(建单幂等键由表单会话持有)
  create: (data, config) => api.post('/tickets', data, config),
  list: (params) => api.get('/tickets', { params }),
  detail: (id) => api.get(`/tickets/${id}`),
  assign: (id, data) => api.post(`/tickets/${id}/assign`, data),
  claim: (id, data) => api.post(`/tickets/${id}/claim`, data),
  action: (id, data) => api.post(`/tickets/${id}/actions`, data),
  rating: (id, data) => api.post(`/tickets/${id}/rating`, data)
}

export const categoryApi = {
  leaf: () => api.get('/categories/leaf')
}

// ---- 通知中心 API ----
export const notificationApi = {
  list: (params) => api.get('/notifications', { params }),
  pendingCount: () => api.get('/notifications/pending-count')
}

// ---- SLA 计时 API ----
export const slaApi = {
  byTicket: (ticketId) => api.get(`/sla/${ticketId}`)
}

// ---- 草稿 API ----
export const draftApi = {
  DRAFT_ID_KEY: 'ticket_draft_id',
  ensureDraftId() {
    const key = `${this.DRAFT_ID_KEY}:${useUserStore().userId}`
    let id = localStorage.getItem(key)
    if (!id) {
      id = 'draft-' + randomId('f')
      localStorage.setItem(key, id)
    }
    return id
  },
  get: (id) => api.get(`/ticket-drafts/${id}`),
  save: (id, data) => api.put(`/ticket-drafts/${id}`, data),
  delete: (id) => api.delete(`/ticket-drafts/${id}`)
}

// ---- RAG 知识库 API ----
export const ragApi = {
  uploadDocument: (formData) => api.post('/rag/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getTrace: (traceId) => api.get(`/rag/traces/${traceId}`),
  listTraces: () => api.get('/rag/traces'),
  initIndex: (recreate = false) => api.post(`/rag/indices/init?recreate=${recreate}`)
}

export default api
