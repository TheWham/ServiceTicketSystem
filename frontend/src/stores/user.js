import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const USER_KEY = 'mock_user'
const ID_KEY = 'mock_user_id'

// 从 localStorage 恢复登录态（刷新页面后不丢失）
function loadStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

export const useUserStore = defineStore('user', () => {
  const stored = loadStoredUser()
  const userId = ref(stored?.user_id || localStorage.getItem(ID_KEY) || '')
  const currentUser = ref(stored)

  function setUser(user) {
    if (!user) return
    userId.value = user.user_id
    currentUser.value = user
    localStorage.setItem(ID_KEY, user.user_id)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  }

  function logout() {
    userId.value = ''
    currentUser.value = null
    localStorage.removeItem(ID_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const isEmployee = computed(() => currentUser.value?.role === 'employee')
  const isEngineer = computed(() => currentUser.value?.role === 'engineer')
  const isSupervisor = computed(() => currentUser.value?.role === 'supervisor')

  return { userId, currentUser, setUser, logout, isEmployee, isEngineer, isSupervisor }
})