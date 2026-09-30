import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'

// Role values are verified by /users/me; no cached or legacy role grants access.
const HOME = {
  EMPLOYEE: '/employee', ENGINEER: '/engineer', PLATFORM_ADMIN: '/dispatch',
  KNOWLEDGE_ADMIN: '/knowledge-admin'
}

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue') },
  { path: '/employee', name: 'Employee', component: () => import('../views/EmployeeView.vue'), meta: { role: 'EMPLOYEE' } },
  { path: '/consultation', name: 'Consultation', component: () => import('../views/ConsultationView.vue'), meta: { role: 'EMPLOYEE' } },
  { path: '/engineer', name: 'Engineer', component: () => import('../views/EngineerView.vue'), meta: { role: 'ENGINEER' } },
  { path: '/dispatch', name: 'Dispatch', component: () => import('../views/DispatchView.vue'), meta: { role: 'PLATFORM_ADMIN' } },
  { path: '/knowledge-admin', name: 'KnowledgeAdmin', component: () => import('../views/KnowledgeAdminView.vue'), meta: { role: ['KNOWLEDGE_ADMIN', 'PLATFORM_ADMIN'] } },
  { path: '/accounts', name: 'Accounts', component: () => import('../views/AccountManageView.vue'), meta: { role: 'PLATFORM_ADMIN' } },
  // 通知跳转：/tickets/:id → 按当前角色重定向到对应工作台并带上 ticket query（工作台自动打开详情）
  { path: '/tickets/:id', redirect: (to) => {
      return { path: '/login', query: { ticket: to.params.id } }
    }
  },
  { path: '/:pathMatch(.*)*', redirect: '/login' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  await userStore.restoreSession(userApi.getMe)

  // 已登录用户访问登录页 → 直接回各自主页
  if (to.path === '/login') {
    if (userStore.userId && userStore.currentUser) {
      const path = HOME[userStore.currentUser.role]
      return next(to.query?.ticket ? { path, query: { ticket: to.query.ticket } } : path)
    }
    return next()
  }

  if (!userStore.currentUser) {
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
