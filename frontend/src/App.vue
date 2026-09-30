<template>
  <a href="#main-content" class="skip-link">跳转到主要内容</a>
  <div v-if="!online" class="connection-banner" role="status"><el-icon><Connection /></el-icon>网络已断开。已显示的内容仍可查看，请联网后重试。</div>
  <router-view v-if="isLoginPage" />
  <main v-else-if="!userStore.currentUser" id="main-content" class="session-loading" role="status">正在核验登录身份…</main>
  <div v-else class="workspace-shell" :class="{ 'nav-open': mobileNav, 'is-offline': !online }">
    <button v-if="mobileNav" class="nav-backdrop" aria-label="关闭导航" @click="mobileNav = false" />
    <aside ref="navRef" class="workspace-nav" aria-label="工作区导航">
      <button class="mobile-nav-close" aria-label="关闭导航" @click="mobileNav = false">关闭 ×</button>
      <router-link :to="home" class="workspace-brand" @click="mobileNav = false">
        <span class="brand-symbol" aria-hidden="true">&gt;_</span>
        <span><strong>IT 服务工单系统</strong><small>IT SERVICE DESK</small></span>
      </router-link>
      <button class="workspace-search-trigger" @click="searchOpen = true">
        <el-icon><Search /></el-icon><span>快速前往</span><kbd>Ctrl K</kbd>
      </button>
      <p class="nav-caption">工作空间</p>
      <el-menu :default-active="activeMenu" class="workspace-menu" @select="onMenuSelect">
        <el-menu-item index="home"><el-icon><Tickets /></el-icon><template #title>{{ homeLabel }}</template></el-menu-item>
        <el-menu-item v-if="userStore.isEmployee" index="create"><el-icon><CirclePlus /></el-icon><template #title>提交工单</template></el-menu-item>
        <el-menu-item v-if="userStore.isEmployee" index="consultation"><el-icon><ChatDotRound /></el-icon><template #title>智能客服</template></el-menu-item>
        <el-menu-item v-if="isAdmin" index="accounts"><el-icon><User /></el-icon><template #title>账号管理</template></el-menu-item>
        <el-menu-item v-if="isAdmin" index="knowledge"><el-icon><Reading /></el-icon><template #title>知识审核</template></el-menu-item>
      </el-menu>
      <div class="nav-bottom">
        <div class="workspace-note">
          <span class="tiny-label">SUPPORT, SIMPLIFIED</span><p>每个问题，都有回应。</p><span>提交 · 协作 · 解决</span>
        </div>
        <button class="nav-profile" @click="openPassword" aria-label="账号信息与修改密码">
          <span class="profile-initial">{{ userStore.currentUser?.name?.[0] || '?' }}</span>
          <span><strong>{{ userStore.currentUser?.name }}</strong><small>{{ roleLabel }}</small></span>
          <el-icon><Setting /></el-icon>
        </button>
      </div>
    </aside>
    <div class="workspace-body" :inert="mobileNav || undefined">
      <header class="workspace-topbar">
        <div class="topbar-context">
          <el-button class="mobile-menu-btn" text circle aria-label="打开导航" @click="mobileNav = !mobileNav">
            <el-icon><Expand /></el-icon>
          </el-button>
          <span class="workspace-context">服务空间</span><span class="context-divider">/</span><strong>{{ breadcrumb }}</strong>
        </div>
        <div class="topbar-tools">
          <span class="local-date">{{ today }}</span>
          <NotificationBell />
          <el-button text circle :aria-label="isDark ? '切换浅色主题' : '切换深色主题'"
                     :title="isDark ? '切换浅色主题' : '切换深色主题'" @click="toggleDark">
            <el-icon><Sunny v-if="isDark" /><Moon v-else /></el-icon>
          </el-button>
          <el-dropdown @command="onUserCommand">
            <button class="account-trigger" aria-label="账号菜单">
              <span class="profile-initial small">{{ userStore.currentUser?.name?.[0] || '?' }}</span><el-icon><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ userStore.currentUser?.name }} · {{ roleLabel }}</el-dropdown-item>
                <el-dropdown-item command="changePwd">修改密码</el-dropdown-item>
                <el-dropdown-item v-if="isAdmin" command="accounts">账号管理</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main id="main-content" class="workspace-main" tabindex="-1"><router-view /></main>
      <footer class="workspace-footer"><span>IT 服务工单系统</span><span>IT SERVICE DESK</span></footer>
    </div>
    <WorkspaceSearch v-model="searchOpen" :items="searchItems" @select="onMenuSelect" />
    <ChangePasswordDialog v-model="pwdVisible" />
    <template v-if="userStore.isEmployee && route.path !== '/consultation'">
      <button class="chat-fab" title="智能客服 / 转人工" aria-label="智能客服 / 转人工" @click="consultOpen = true"><el-icon :size="20"><ChatDotRound /></el-icon><span>寻求帮助</span></button>
      <el-drawer v-model="consultOpen" title="智能客服" size="min(540px, 100vw)" :append-to-body="true" :close-on-click-modal="false" destroy-on-close class="consult-drawer"><ConsultationChat :key="userStore.userId" @navigate="consultOpen = false" /></el-drawer>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from './stores/user.js'
import { Tickets, CirclePlus, Expand, Sunny, Moon, User, Setting, ChatDotRound, Search, ArrowDown, Connection, Reading } from '@element-plus/icons-vue'
import NotificationBell from './components/NotificationBell.vue'
import ChangePasswordDialog from './components/ChangePasswordDialog.vue'
import ConsultationChat from './components/ConsultationChat.vue'
import WorkspaceSearch from './components/WorkspaceSearch.vue'
const userStore = useUserStore()
const router = useRouter()
const route = useRoute()
const consultOpen = ref(false)
const searchOpen = ref(false)
const mobileNav = ref(false)
const navRef = ref(null)
let navFocusFrame = 0
let mobileBreakpoint
const pwdVisible = ref(false)
const online = ref(typeof navigator === 'undefined' || navigator.onLine !== false)
const isDark = ref(localStorage.getItem('app_theme') === 'dark' || (!localStorage.getItem('app_theme') && typeof matchMedia !== 'undefined' && matchMedia('(prefers-color-scheme: dark)').matches))
watch(isDark, value => { document.documentElement.classList.toggle('dark', value); localStorage.setItem('app_theme', value ? 'dark' : 'light') }, { immediate: true })
const isLoginPage = computed(() => route.path === '/login')
const home = computed(() => ({ EMPLOYEE: '/employee', ENGINEER: '/engineer', PLATFORM_ADMIN: '/dispatch', KNOWLEDGE_ADMIN: '/knowledge-admin' }[userStore.currentUser?.role] || '/login'))
const homeLabel = computed(() => ({ EMPLOYEE: '我的工单', ENGINEER: '处理队列', PLATFORM_ADMIN: '工单调度', KNOWLEDGE_ADMIN: '知识管理' }[userStore.currentUser?.role] || '工作台'))
const activeMenu = computed(() => route.path === '/accounts' ? 'accounts' : route.path === '/knowledge-admin' && isAdmin.value ? 'knowledge' : route.path === '/consultation' ? 'consultation' : route.query.view === 'create' ? 'create' : 'home')
const breadcrumb = computed(() => ({ '/employee': '我的工单', '/engineer': '处理队列', '/dispatch': '工单调度', '/accounts': '账号管理', '/consultation': '智能客服', '/knowledge-admin': '知识管理' }[route.path] || '工作台'))
const roleLabel = computed(() => ({ EMPLOYEE: '员工', ENGINEER: '工程师', PLATFORM_ADMIN: '平台管理员', KNOWLEDGE_ADMIN: '知识库管理员' }[userStore.currentUser?.role] || ''))
const isAdmin = computed(() => userStore.currentUser?.role === 'PLATFORM_ADMIN')
const today = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }).format(new Date())
const searchItems = computed(() => [
  { id: 'home', label: homeLabel.value, description: '查看与你相关的工作', keywords: '工作台 工单 列表 知识' },
  ...(userStore.isEmployee ? [{ id: 'create', label: '提交工单', description: '描述问题并跟进处理', keywords: '新建 问题' }, { id: 'consultation', label: '智能客服', description: '获取帮助或转接人工', keywords: '咨询 AI 人工 帮助' }] : []),
  ...(isAdmin.value ? [
    { id: 'accounts', label: '账号管理', description: '查找账号、调整角色与重置密码', keywords: '用户 人员 角色' },
    { id: 'knowledge', label: '知识审核', description: '审核并发布知识文章', keywords: '知识库 高风险 发布' }
  ] : []),
  { id: 'theme', label: isDark.value ? '切换浅色主题' : '切换深色主题', description: '调整工作台外观', keywords: '亮色 暗色 主题' },
  { id: 'password', label: '修改密码', description: '更新你的登录密码', keywords: '安全 账号' }
])
function toggleDark() { isDark.value = !isDark.value }
async function openPassword() { mobileNav.value = false; await nextTick(); pwdVisible.value = true }
function onMenuSelect(index) {
  mobileNav.value = false; searchOpen.value = false
  if (index === 'consultation') { if (route.path !== '/consultation') consultOpen.value = true; return }
  if (index === 'theme') return toggleDark()
  if (index === 'password') return openPassword()
  if (index === 'accounts' && isAdmin.value) return router.push('/accounts')
  if (index === 'knowledge' && isAdmin.value) return router.push('/knowledge-admin')
  if (index === 'create' && userStore.isEmployee) return router.push({ path: '/employee', query: { view: 'create' } })
  router.push({ path: home.value, query: userStore.isEmployee ? { view: 'list' } : {} })
}
watch(() => userStore.userId, () => { consultOpen.value = false; searchOpen.value = false })
watch(() => route.fullPath, () => { mobileNav.value = false })
watch(mobileNav, async open => {
  cancelAnimationFrame(navFocusFrame)
  await nextTick()
  if (open) focusVisibleNavigation()
  else document.querySelector('.mobile-menu-btn')?.focus()
})
function focusVisibleNavigation() {
  if (!mobileNav.value) return
  const button = navRef.value?.querySelector('.mobile-nav-close')
  if (button && getComputedStyle(button).visibility === 'visible' && button.getClientRects().length) button.focus()
  else navFocusFrame = requestAnimationFrame(focusVisibleNavigation)
}
function syncMobileBreakpoint() {
  if (!mobileBreakpoint.matches) mobileNav.value = false
}
function onUserCommand(cmd) {
  if (cmd === 'logout') { consultOpen.value = false; userStore.logout(); router.push('/login') }
  else if (cmd === 'changePwd') openPassword()
  else if (cmd === 'accounts' && isAdmin.value) router.push('/accounts')
}
function syncConnection() { online.value = navigator.onLine }
function keyboard(event) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k' && !isLoginPage.value) { event.preventDefault(); searchOpen.value = !searchOpen.value }
  if (event.key === 'Escape' && !searchOpen.value) mobileNav.value = false
  if (mobileNav.value && !searchOpen.value && event.key === 'Tab') {
    const items = [...navRef.value.querySelectorAll('a[href], button:not([disabled]), [tabindex="0"]')].filter(item => item.getClientRects().length)
    const first = items[0], last = items.at(-1)
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
  }
}
onMounted(() => {
  mobileBreakpoint = window.matchMedia('(max-width: 760px)')
  mobileBreakpoint.addEventListener('change', syncMobileBreakpoint)
  window.addEventListener('online', syncConnection)
  window.addEventListener('offline', syncConnection)
  window.addEventListener('keydown', keyboard, true)
})
onUnmounted(() => {
  cancelAnimationFrame(navFocusFrame)
  mobileBreakpoint?.removeEventListener('change', syncMobileBreakpoint)
  window.removeEventListener('online', syncConnection)
  window.removeEventListener('offline', syncConnection)
  window.removeEventListener('keydown', keyboard, true)
})
</script>
