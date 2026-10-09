import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'

// PRD §5.1 角色值域；KB_ADMIN 为历史别名
// 知识库管理员进入 RAG 知识管理工作台（/knowledge-admin）
const HOME = {
  EMPLOYEE: '/employee', ENGINEER: '/engineer', PLATFORM_ADMIN: '/supervisor',
  KNOWLEDGE_ADMIN: '/knowledge-admin', KB_ADMIN: '/knowledge-admin'
}

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue') },
  { path: '/employee', name: 'Employee', component: () => import('../views/EmployeeView.vue'), meta: { role: ['EMPLOYEE', 'employee'] } },
  { path: '/consultation', name: 'Consultation', component: () => import('../views/ConsultationView.vue'), meta: { role: ['EMPLOYEE', 'employee'] } },
  { path: '/engineer', name: 'Engineer', component: () => import('../views/EngineerView.vue'), meta: { role: ['ENGINEER', 'engineer'] } },
  { path: '/supervisor', name: 'Supervisor', component: () => import('../views/DispatchView.vue'), meta: { role: ['PLATFORM_ADMIN', 'KB_ADMIN'] } },
  { path: '/knowledge-admin', name: 'KnowledgeAdmin', component: () => import('../views/KnowledgeAdminView.vue'), meta: { role: ['KNOWLEDGE_ADMIN', 'KB_ADMIN'] } },
  { path: '/accounts', name: 'Accounts', component: () => import('../views/AccountManageView.vue'), meta: { role: ['PLATFORM_ADMIN', 'KB_ADMIN'] } },
  // 通知跳转：/tickets/:id → 按当前角色重定向到对应工作台并带上 ticket query（工作台自动打开详情）
  { path: '/tickets/:id', redirect: (to) => {
      const userStore = useUserStore()
      const home = HOME[userStore.currentUser?.role] || '/login'
      return { path: home, query: { ticket: to.params.id } }
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
