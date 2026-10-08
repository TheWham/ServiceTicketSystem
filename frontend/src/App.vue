<template>
  <router-view v-if="isLoginPage" />
  <div v-else class="desk-app">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <aside class="desk-sidebar" :class="{ compact: collapse }" aria-label="主导航">
      <RouterLink :to="home" class="desk-brand" aria-label="IT 智能服务台首页">
        <span class="brand-monogram">IT<span class="brand-dot"></span></span>
        <span v-if="!collapse" class="brand-copy"><strong>智能服务台</strong><small>SERVICE DESK</small></span>
      </RouterLink>
      <div class="nav-section-title">{{ collapse ? '服务' : `${label}工作空间` }}</div>
      <nav class="desk-nav">
        <RouterLink v-for="link in links" :key="link.id" :to="link.to" class="desk-nav-link" :class="{ active: active === link.id }" :aria-current="active === link.id ? 'page' : undefined" :aria-label="link.label" :title="collapse ? link.label : undefined">
          <el-icon aria-hidden="true"><component :is="link.icon" /></el-icon><span v-if="!collapse">{{ link.label }}</span>
          <span v-if="!collapse && active === link.id" class="nav-active-dot"></span>
        </RouterLink>
      </nav>
      <div v-if="!collapse" class="sidebar-note"><el-icon aria-hidden="true"><Connection /></el-icon><strong>让每一次请求都有回应</strong><p>连接问题与答案<br>让工作顺畅一点</p></div>
      <div class="sidebar-bottom"><span v-if="!collapse">IT SERVICE DESK</span><el-button text class="sidebar-toggle" :aria-label="collapse ? '展开导航' : '收起导航'" @click="collapse = !collapse"><el-icon><Expand v-if="collapse" /><Fold v-else /></el-icon></el-button></div>
    </aside>
    <div class="desk-main-container">
      <header class="desk-header">
        <div class="header-location"><el-button text class="mobile-menu" aria-label="打开导航" :aria-expanded="mobileNav" @click="mobileNav = true"><el-icon><Menu /></el-icon></el-button><span class="workspace-label">{{ label }}服务</span><span class="breadcrumb-divider">/</span><span class="current-page">{{ currentTitle }}</span></div>
        <div class="header-actions"><NotificationBell /><el-button text circle :aria-label="isDark ? '切换亮色' : '切换暗黑'" @click="isDark = !isDark"><el-icon><Sunny v-if="isDark" /><Moon v-else /></el-icon></el-button><span class="header-divider"></span>
          <el-dropdown @command="onUserCommand">
            <button type="button" class="user-entry" aria-label="用户菜单"><el-avatar :size="34">{{ userStore.currentUser?.name?.[0] || '?' }}</el-avatar><span class="user-copy"><strong>{{ userStore.currentUser?.name }}</strong><small>{{ label }}</small></span><el-icon class="user-chevron"><ArrowDown /></el-icon></button>
            <template #dropdown><el-dropdown-menu><el-dropdown-item disabled>{{ userStore.currentUser?.department || label }}</el-dropdown-item><el-dropdown-item command="changePwd" :icon="Lock">修改密码</el-dropdown-item><el-dropdown-item v-if="isAdmin" command="accounts" :icon="Setting">账号管理</el-dropdown-item><el-dropdown-item divided command="logout" :icon="SwitchButton">退出登录</el-dropdown-item></el-dropdown-menu></template>
          </el-dropdown>
        </div>
      </header>
      <main id="main-content" class="desk-main" tabindex="-1"><router-view /></main>
    </div>
    <el-drawer v-model="mobileNav" title="工作空间" direction="ltr" size="280px" class="mobile-navigation" :append-to-body="true">
      <div class="mobile-brand"><span class="brand-monogram">IT</span><strong>智能服务台</strong></div>
      <nav aria-label="移动端导航"><RouterLink v-for="link in links" :key="link.id" :to="link.to" class="mobile-nav-link" :class="{ active: active === link.id }" :aria-current="active === link.id ? 'page' : undefined" @click="mobileNav = false"><el-icon aria-hidden="true"><component :is="link.icon" /></el-icon>{{ link.label }}</RouterLink></nav>
    </el-drawer>
    <ChangePasswordDialog v-model="pwdVisible" />
  </div>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Expand, Fold, Sunny, Moon, Menu, Lock, Setting, SwitchButton, Connection, ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from './stores/user.js'
import { roleHome, roleLabel, navigationFor, activeNavigation } from './utils/navigation.js'
import NotificationBell from './components/NotificationBell.vue'
import ChangePasswordDialog from './components/ChangePasswordDialog.vue'
const userStore = useUserStore()
const router = useRouter()
const route = useRoute()
const collapse = ref(false)
const mobileNav = ref(false)
const pwdVisible = ref(false)
const isDark = ref(localStorage.getItem('app_theme') === 'dark')
watch(isDark, value => {
  document.documentElement.classList.toggle('dark', value)
  localStorage.setItem('app_theme', value ? 'dark' : 'light')
}, { immediate: true })
watch(() => route.fullPath, () => { mobileNav.value = false })
const isLoginPage = computed(() => route.path === '/login')
const role = computed(() => userStore.currentUser?.role)
const home = computed(() => roleHome(role.value))
const label = computed(() => roleLabel(role.value))
const links = computed(() => navigationFor(role.value))
const active = computed(() => activeNavigation(role.value, route))
const currentTitle = computed(() => links.value.find(link => link.id === active.value)?.label || '工作台')
const isAdmin = computed(() => ['PLATFORM_ADMIN', 'KB_ADMIN'].includes(role.value))
function onUserCommand(command) {
  if (command === 'logout') { userStore.logout(); router.push('/login') }
  else if (command === 'changePwd') pwdVisible.value = true
  else if (command === 'accounts') router.push('/accounts')
}
</script>
<style scoped>
.desk-app { height: 100dvh; display: flex; overflow: hidden; }
.desk-sidebar { flex: 0 0 224px; width: 224px; display: flex; flex-direction: column; overflow-y: auto; overflow-x: hidden; background: var(--desk-nav); color: #cbd5e1; }
.desk-sidebar.compact { flex-basis: 76px; width: 76px; }
.desk-brand { display: flex; gap: 12px; align-items: center; min-height: 96px; padding: 24px; text-decoration: none; color: white; }
.compact .desk-brand { padding: 20px 16px; }
.brand-monogram { width: 40px; height: 40px; display: grid; place-items: center; flex-shrink: 0; position: relative; background: #2563eb; color: white; font-size: 21px; font-weight: 800; border-radius: 12px; letter-spacing: -1px; }
.brand-dot { width: 6px; height: 6px; background: #93c5fd; position: absolute; right: 7px; top: 7px; border-radius: 50%; }
.brand-copy strong { display: block; font-size: 18px; letter-spacing: .5px; }
.brand-copy small { display: block; font-size: 9px; letter-spacing: 2px; margin-top: 4px; color: #a8b9d1; }
.nav-section-title { padding: 24px 26px 14px; font-size: 11px; letter-spacing: 1px; color: #a8b9d1; white-space: nowrap; }
.compact .nav-section-title { padding-left: 24px; }
.desk-nav { padding: 0 14px; display: flex; flex-direction: column; gap: 8px; }
.desk-nav-link { display: flex; align-items: center; gap: 13px; min-height: 48px; padding: 12px 14px; border-radius: 9px; text-decoration: none; color: #cbd5e1; font-size: 14px; transition: background .18s, color .18s; }
.desk-nav-link .el-icon { font-size: 20px; flex-shrink: 0; }
.desk-nav-link:hover { background: #263955; color: white; }
.desk-nav-link.active { background: #2563eb; color: white; font-weight: 600; box-shadow: 0 4px 12px #07163040; }
.nav-active-dot { margin-left: auto; width: 5px; height: 5px; border-radius: 50%; background: #bfdbfe; }
.sidebar-note { margin: auto 18px 24px; padding: 20px 16px; border: 1px solid #31415c; border-radius: 12px; background: #1b2d48; }
.sidebar-note > .el-icon { font-size: 22px; color: #93c5fd; margin-bottom: 12px; }
.sidebar-note strong { display: block; font-size: 12px; color: #f1f5f9; }
.sidebar-note p { margin: 10px 0 0; font-size: 12px; line-height: 1.8; color: #a8b9d1; }
.sidebar-bottom { margin-top: auto; display: flex; justify-content: space-between; align-items: center; min-height: 68px; padding: 10px 20px; border-top: 1px solid #31415c; }
.sidebar-bottom span { font-size: 9px; letter-spacing: 1.8px; color: #a8b9d1; }
.sidebar-toggle { color: #cbd5e1; }
.sidebar-toggle:hover { color: white; background: #263955; }
.compact .sidebar-bottom { padding: 10px 16px; }
.desk-main-container { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.desk-header { height: 72px; flex-shrink: 0; display: flex; align-items: center; justify-content: space-between; gap: 12px; background: var(--el-bg-color); border-bottom: 1px solid var(--el-border-color-lighter); padding: 0 32px; }
.header-location, .header-actions { display: flex; align-items: center; gap: 16px; }
.header-location { font-size: 13px; min-width: 0; }
.workspace-label { color: var(--el-text-color-secondary); }
.breadcrumb-divider { color: var(--el-text-color-placeholder); }
.current-page { font-weight: 600; white-space: nowrap; }
.header-divider { height: 26px; width: 1px; background: var(--el-border-color-lighter); }
.user-entry { border: 0; background: none; color: var(--el-text-color-primary); display: flex; align-items: center; gap: 10px; padding: 5px; border-radius: 8px; cursor: pointer; font: inherit; text-align: left; }
.user-entry:hover { background: var(--el-fill-color-light); }
.user-entry .el-avatar { background: var(--el-color-primary-light-9); color: var(--el-color-primary); font-weight: 700; }
.user-copy strong { display: block; font-size: 13px; font-weight: 600; }
.user-copy small { font-size: 10px; color: var(--el-text-color-secondary); }
.user-chevron { margin-left: 8px; font-size: 12px; }
.desk-main { padding: 30px 32px; flex: 1; min-height: 0; overflow-y: auto; background: var(--el-bg-color-page); scroll-padding-top: 24px; }
.desk-main:focus { outline: none; }
.mobile-menu { display: none; }
.mobile-brand { display: flex; align-items: center; gap: 12px; margin: 0 0 28px; }
.mobile-nav-link { display: flex; align-items: center; gap: 14px; color: var(--el-text-color-regular); text-decoration: none; padding: 14px; margin-bottom: 6px; border-radius: 8px; }
.mobile-nav-link.active { color: var(--el-color-primary); background: var(--el-color-primary-light-9); font-weight: 600; }
@media (max-width: 1199px) and (min-width: 768px) { .desk-sidebar:not(.compact) { flex-basis: 196px; width: 196px; } .desk-brand { padding: 24px 18px; gap: 9px; } .brand-copy strong { font-size: 16px; } .desk-main { padding: 24px; } .desk-header { padding: 0 24px; } }
@media (max-width: 767px) { .desk-sidebar { display: none; } .desk-header { height: 64px; padding: 0 12px; } .mobile-menu { display: inline-flex; margin: 0; } .header-location { gap: 6px; } .workspace-label, .breadcrumb-divider, .user-copy, .user-chevron, .header-divider { display: none; } .header-actions { gap: 4px; } .desk-main { padding: 20px 16px; } }
</style>
