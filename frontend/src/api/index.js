import axios from 'axios'
import { useUserStore } from '../stores/user.js'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

// 请求拦截：注入 JWT（Spring Cloud 网关统一鉴权）
api.interceptors.request.use(config => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers['Authorization'] = `Bearer ${userStore.token}`
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
  create: (data) => api.post('/tickets', data),
  list: (params) => api.get('/tickets', { params }),
  detail: (id) => api.get(`/tickets/${id}`),
  assign: (id, data) => api.post(`/tickets/${id}/assign`, data),
  claim: (id) => api.post(`/tickets/${id}/claim`),
  action: (id, data) => api.post(`/tickets/${id}/actions`, data),
  rating: (id, data) => api.post(`/tickets/${id}/rating`, data)
}

// ---- AI 智能助手 API（员工侧） ----
export const aiApi = {
  chat: (data) => api.post('/ai/chat', data),                    // 提问 {session_id?, question}
  resolve: (id) => api.post(`/ai/sessions/${id}/resolve`),        // 反馈已解决
  escalate: (id) => api.post(`/ai/sessions/${id}/escalate`),      // 转人工
  close: (id) => api.post(`/ai/sessions/${id}/close`),            // 直接结束
  mySessions: () => api.get('/ai/sessions/mine'),                 // 我的会话列表
  messages: (id) => api.get(`/ai/sessions/${id}/messages`)        // 会话消息记录
}

// ---- 人工客服工作台 API（客服侧） ----
export const agentApi = {
  queue: () => api.get('/ai/agent/queue'),
  accept: (id) => api.post(`/ai/agent/sessions/${id}/accept`),
  resolve: (id) => api.post(`/ai/agent/sessions/${id}/resolve`),
  reject: (id, data) => api.post(`/ai/agent/sessions/${id}/reject`, data),
  toTicket: (id, data) => api.post(`/ai/agent/sessions/${id}/to-ticket`, data),
  messages: (id) => api.get(`/ai/agent/sessions/${id}/messages`)
}

// ---- 知识库管理 API（客服/主管） ----
export const knowledgeApi = {
  add: (data) => api.post('/ai/knowledge', data),
  list: (params) => api.get('/ai/knowledge', { params }),
  remove: (id) => api.delete(`/ai/knowledge/${id}`)
}

// ---- 草稿 API ----
export const draftApi = {
  get: () => api.get('/users/drafts'),
  save: (data) => api.post('/users/drafts', data),
  delete: () => api.delete('/users/drafts')
}

export default api