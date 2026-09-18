import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const userId = ref(localStorage.getItem('mock_user_id') || '')
  const currentUser = ref(null)

  function setUser(user) {
    userId.value = user.user_id
    currentUser.value = user
    localStorage.setItem('mock_user_id', user.user_id)
  }

  function logout() {
    userId.value = ''
    currentUser.value = null
    localStorage.removeItem('mock_user_id')
  }

  const isEmployee = computed(() => currentUser.value?.role === 'employee')
  const isEngineer = computed(() => currentUser.value?.role === 'engineer')
  const isSupervisor = computed(() => currentUser.value?.role === 'supervisor')

  return { userId, currentUser, setUser, logout, isEmployee, isEngineer, isSupervisor }
})