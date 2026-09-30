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
  listUsers: (params) => api.get('/users', { params }),
  // 认证模块：忘记密码(免登录)/修改密码
  forgotPassword: (data) => api.post('/users/forgot-password', data),
  changePassword: (data) => api.post('/users/change-password', data),
  // 主管账号管理
  listAccounts: () => api.get('/users/accounts'),
  createAccount: (data) => api.post('/users/accounts', data),
  resetPassword: (userId, data) => api.post(`/users/accounts/${userId}/reset-password`, data),
  changeRole: (userId, data) => api.put(`/users/accounts/${userId}/role`, data)
}

// ---- 工单 API ----
export const ticketApi = {
  create: (data) => api.post('/tickets', data),
  list: (params) => api.get('/tickets', { params }),
  detail: (id) => api.get(`/tickets/${id}`),
  assign: (id, data) => api.post(`/tickets/${id}/assign`, data),
  claim: (id, data) => api.post(`/tickets/${id}/claim`, data),
  action: (id, data) => api.post(`/tickets/${id}/actions`, data),
  rating: (id, data) => api.post(`/tickets/${id}/rating`, data)
}

export const categoryApi = {
  // 后端返回 snake_case（category_id / ticket_nature），统一归一化为前端使用的 camelCase
  leaf: () => api.get('/categories/leaf').then(res => {
    if (res && Array.isArray(res.data)) {
      res.data = res.data.map(c => ({
        ...c,
        categoryId: c.categoryId || c.category_id,
        parentId: c.parentId || c.parent_id,
        nature: c.nature || c.ticketNature || c.ticket_nature
      }))
    }
    return res
  })
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
  get: () => api.get('/users/drafts'),
  save: (data) => api.post('/users/drafts', data),
  delete: () => api.delete('/users/drafts')
}

// ---- RAG 知识库 API ----
export const ragApi = {
  uploadDocument: (formData) => api.post('/rag/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getTrace: (traceId) => api.get(`/rag/traces/${traceId}`),
  listTraces: () => api.get('/rag/traces'),
  initIndex: (recreate = false) => api.post(`/rag/indices/init?recreate=${recreate}`),

  // ---- 知识生命周期管理（SM-KNOWLEDGE-001）----
  listArticles: (params) => api.get('/rag/articles', { params }),
  getArticle: (id) => api.get(`/rag/articles/${id}`),
  submitArticle: (id, data) => api.post(`/rag/articles/${id}/submit`, data || {}),
  publishArticle: (id, data) => api.post(`/rag/articles/${id}/publish`, data || {}),
  rejectArticle: (id, data) => api.post(`/rag/articles/${id}/reject`, data || {}),
  offlineArticle: (id, data) => api.post(`/rag/articles/${id}/offline`, data || {}),
  reindexArticle: (id) => api.post(`/rag/articles/${id}/reindex`)
}

export default api
