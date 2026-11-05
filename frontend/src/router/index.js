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
  { path: '/consultation', name: 'Consultation', component: () => import('../views/ConsultationView.vue'), meta: { role: ['EMPLOYEE', 'employee', 'PLATFORM_ADMIN', 'KNOWLEDGE_ADMIN', 'KB_ADMIN'] } },
  { path: '/engineer', name: 'Engineer', component: () => import('../views/EngineerView.vue'), meta: { role: ['ENGINEER', 'engineer'] } },
  { path: '/supervisor', name: 'Supervisor', component: () => import('../views/DispatchView.vue'), meta: { role: ['PLATFORM_ADMIN', 'KB_ADMIN'] } },
  { path: '/knowledge-admin', name: 'KnowledgeAdmin', component: () => import('../views/KnowledgeAdminView.vue'), meta: { role: ['KNOWLEDGE_ADMIN', 'KB_ADMIN'] } },
  { path: '/knowledge-admin/refusals', name: 'RefusalCases', component: () => import('../views/RefusalCaseView.vue'), meta: { role: ['KNOWLEDGE_ADMIN', 'KB_ADMIN'] } },
  { path: '/knowledge-admin/golden', name: 'GoldenCases', component: () => import('../views/GoldenCaseView.vue'), meta: { role: ['KNOWLEDGE_ADMIN', 'KB_ADMIN'] } },
  // 跨工单分析：跨人聚合，**仅工程师**可进（与后端 AuthzService 的角色门禁一致）。
  // EMPLOYEE 与 PLATFORM_ADMIN 都不在此列表 —— 前端不展示入口，后端也会拒答
  // （POLICY_BLOCKED / 403），两层都不放行。
  { path: '/analytics', name: 'Analytics', component: () => import('../views/AnalyticsView.vue'), meta: { role: ['ENGINEER'] } },
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

  // 刷新页面或会话恢复：若持有凭证则向后端复核当前有效身份
  await userStore.restoreSession(userApi.getMe)

  // 已登录用户访问登录页 → 直接回各自主页（若带工单参数则透传）
  if (to.path === '/login') {
    if (userStore.userId && userStore.currentUser) {
      const home = HOME[userStore.currentUser.role] || '/login'
      return next(to.query?.ticket ? { path: home, query: { ticket: to.query.ticket } } : home)
    }
    return next()
  }

  if (!userStore.currentUser) return next('/login')

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
