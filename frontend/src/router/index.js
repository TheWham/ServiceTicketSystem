import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'

const HOME = { EMPLOYEE: '/employee', ENGINEER: '/engineer', PLATFORM_ADMIN: '/supervisor', KB_ADMIN: '/supervisor' }

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue') },
  { path: '/employee', name: 'Employee', component: () => import('../views/EmployeeView.vue'), meta: { role: 'EMPLOYEE' } },
  { path: '/engineer', name: 'Engineer', component: () => import('../views/EngineerView.vue'), meta: { role: 'ENGINEER' } },
  { path: '/supervisor', name: 'Supervisor', component: () => import('../views/SupervisorView.vue'), meta: { role: ['PLATFORM_ADMIN', 'KB_ADMIN'] } },
  { path: '/:pathMatch(.*)*', redirect: '/login' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  // 已登录用户访问登录页 → 直接回各自主页
  if (to.path === '/login') {
    if (userStore.userId && userStore.currentUser) {
      return next(HOME[userStore.currentUser.role] || '/login')
    }
    return next()
  }

  if (!userStore.userId) return next('/login')

  // 有 userId 但缺用户信息（旧版本残留 / 手动写入）→ 从后端恢复
  if (!userStore.currentUser) {
    try {
      const res = await userApi.getMe()
      if (res?.data) userStore.setUser(res.data)
    } catch (e) {
      // 恢复失败：登录态已失效
    }
  }

  if (!userStore.currentUser) {
    userStore.logout()
    return next('/login')
  }

  const allowed = to.meta.role
  if (allowed) {
    const ok = Array.isArray(allowed)
      ? allowed.includes(userStore.currentUser.role)
      : allowed === userStore.currentUser.role
    if (!ok) return next(HOME[userStore.currentUser.role] || '/login')
  }

  next()
})

export default router