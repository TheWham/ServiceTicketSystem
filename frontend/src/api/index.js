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
    const msg = err.response?.data?.msg || err.message || '网络错误'
    console.error('[API Error]', msg)
    return Promise.reject(new Error(msg))
  }
)

// ---- 用户 API ----
export const userApi = {
  login: (data) => api.post('/users/login', data),
  loginOptions: () => api.get('/users/login-options'),
  getMe: () => api.get('/users/me'),
  listUsers: (params) => api.get('/users', { params })
}

// ---- 工单 API ----
export const ticketApi = {
  // config 可透传 { headers: { 'Idempotency-Key': ... } }(建单幂等键由表单会话持有)
  create: (data, config) => api.post('/tickets', data, config),
  list: (params) => api.get('/tickets', { params }),
  detail: (id) => api.get(`/tickets/${id}`),
  assign: (id, data) => api.post(`/tickets/${id}/assign`, data),
  claim: (id) => api.post(`/tickets/${id}/claim`),
  action: (id, data) => api.post(`/tickets/${id}/actions`, data),
  rating: (id, data) => api.post(`/tickets/${id}/rating`, data)
}

// ---- 草稿 API(spec 05 saveTicketDraft:PUT /ticket-drafts/{id};每员工一个活动草稿) ----
// draftId 由前端生成并持久化在 localStorage,登录过期后重新登录凭同一 id 恢复(PRD 10.4)
export const draftApi = {
  DRAFT_ID_KEY: 'ticket_draft_id',
  ensureDraftId() {
    let id = localStorage.getItem(this.DRAFT_ID_KEY)
    if (!id) {
      id = 'draft-' + randomId('f')
      localStorage.setItem(this.DRAFT_ID_KEY, id)
    }
    return id
  },
  get: (id) => api.get(`/ticket-drafts/${id}`),
  save: (id, data) => api.put(`/ticket-drafts/${id}`, data),
  delete: (id) => api.delete(`/ticket-drafts/${id}`)
}

export default api