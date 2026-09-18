import axios from 'axios'
import { useUserStore } from '../stores/user.js'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

// 请求拦截：注入 Mock 用户标识
api.interceptors.request.use(config => {
  const userStore = useUserStore()
  if (userStore.userId) {
    config.headers['X-User-Id'] = userStore.userId
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
  action: (id, data) => api.post(`/tickets/${id}/actions`, data),
  rating: (id, data) => api.post(`/tickets/${id}/rating`, data)
}

// ---- 草稿 API ----
export const draftApi = {
  get: () => api.get('/users/drafts'),
  save: (data) => api.post('/users/drafts', data),
  delete: () => api.delete('/users/drafts')
}

export default api