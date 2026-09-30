import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { requireCurrentIdentity } from '../auth/identity.js'

const TOKEN_KEY = 'auth_token'

export const useUserStore = defineStore('user', () => {
  // Cached roles must never authorize a new app session.
  localStorage.removeItem('mock_user')
  localStorage.removeItem('mock_user_id')
  const userId = ref('')
  const currentUser = ref(null)
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const sessionError = ref('')
  let restoring = null
  let generation = 0

  function setLogin(user, jwt) {
    user = requireCurrentIdentity(user)
    if (!jwt) throw new Error('登录服务未返回有效凭证，请重试。')
    generation++
    userId.value = user.user_id
    currentUser.value = user
    token.value = jwt || ''
    sessionError.value = ''
    localStorage.setItem(TOKEN_KEY, jwt)
  }

  async function restoreSession(fetchMe) {
    if (!token.value || currentUser.value) return
    if (restoring) return restoring
    sessionError.value = ''
    const version = generation
    const pending = (async () => {
      try {
        const response = await fetchMe()
        if (version !== generation) return
        setLogin(response.data, token.value)
      } catch (error) {
        if (version !== generation) return
        if ([401, 403].includes(error.status) || [401, 403, 'INVALID_IDENTITY', 'ACCOUNT_DISABLED'].includes(error.code)) logout()
        sessionError.value = error.message || '无法核验登录身份，请重新登录。'
      }
    })()
    restoring = pending
    try { await pending } finally { if (restoring === pending) restoring = null }
  }

  function logout() {
    generation++
    userId.value = ''
    currentUser.value = null
    token.value = ''
    sessionError.value = ''
    localStorage.removeItem(TOKEN_KEY)
  }

  const isEmployee = computed(() => currentUser.value?.role === 'EMPLOYEE')
  const isEngineer = computed(() => currentUser.value?.role === 'ENGINEER')
  const isPlatformAdmin = computed(() => currentUser.value?.role === 'PLATFORM_ADMIN')

  return { userId, currentUser, token, sessionError, setLogin, restoreSession, logout, isEmployee, isEngineer, isPlatformAdmin }
})
