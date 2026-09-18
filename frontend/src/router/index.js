import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user.js'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue') },
  { path: '/employee', name: 'Employee', component: () => import('../views/EmployeeView.vue'), meta: { role: 'employee' } },
  { path: '/engineer', name: 'Engineer', component: () => import('../views/EngineerView.vue'), meta: { role: 'engineer' } },
  { path: '/supervisor', name: 'Supervisor', component: () => import('../views/SupervisorView.vue'), meta: { role: 'supervisor' } },
  { path: '/:pathMatch(.*)*', redirect: '/login' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (to.path === '/login') return next()
  if (!userStore.userId) return next('/login')
  if (to.meta.role && to.meta.role !== userStore.currentUser?.role) {
    const redirectMap = { employee: '/employee', engineer: '/engineer', supervisor: '/supervisor' }
    return next(redirectMap[userStore.currentUser?.role] || '/login')
  }
  next()
})

export default router