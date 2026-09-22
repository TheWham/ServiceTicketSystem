<template>
  <!-- 登录页：无侧边栏布局 -->
  <router-view v-if="isLoginPage" />

  <!-- 已登录：经典后台布局 -->
  <el-container v-else class="app-layout">
    <!-- ===== 侧边栏 ===== -->
    <el-aside :width="collapse ? '64px' : '220px'" class="app-aside">
      <div class="logo-area">
        <span class="logo-icon">🛠</span>
        <transition name="fade">
          <span v-if="!collapse" class="logo-text">IT 工单系统</span>
        </transition>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="collapse"
        class="app-menu"
        @select="onMenuSelect"
      >
        <el-menu-item index="home">
          <el-icon><Monitor /></el-icon>
          <template #title>工作台</template>
        </el-menu-item>
      </el-menu>

      <div class="aside-footer">
        <el-tooltip :content="collapse ? '展开' : '折叠'" placement="right">
          <el-button text circle class="collapse-btn" @click="collapse = !collapse">
            <el-icon><Expand v-if="collapse" /><Fold v-else /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </el-aside>

    <!-- ===== 主区 ===== -->
    <el-container class="app-main-container">
      <el-header class="app-header" height="56px">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ breadcrumb }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <!-- 暗黑切换 -->
          <el-tooltip :content="isDark ? '切换亮色' : '切换暗黑'" placement="bottom">
            <el-button text circle @click="toggleDark">
              <el-icon><Sunny v-if="isDark" /><Moon v-else /></el-icon>
            </el-button>
          </el-tooltip>

          <!-- 用户信息 -->
          <el-dropdown @command="onUserCommand">
            <div class="user-entry">
              <el-avatar :size="32" class="avatar">{{ userStore.currentUser?.name?.[0] || '?' }}</el-avatar>
              <span class="user-name">{{ userStore.currentUser?.name }}</span>
              <el-tag :type="roleTagType" size="small" effect="dark">{{ roleLabel }}</el-tag>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <el-icon><User /></el-icon>{{ userStore.currentUser?.department }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>切换账号
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from './stores/user.js'
import {
  Monitor, Expand, Fold, Sunny, Moon, User, SwitchButton
} from '@element-plus/icons-vue'

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const collapse = ref(false)
const isDark = ref(localStorage.getItem('app_theme') === 'dark')

// 初始化主题
watch(isDark, (val) => {
  document.documentElement.classList.toggle('dark', val)
  localStorage.setItem('app_theme', val ? 'dark' : 'light')
}, { immediate: true })

const isLoginPage = computed(() => route.path === '/login')

const activeMenu = computed(() => 'home')

const breadcrumb = computed(() => {
  const map = { '/employee': '员工工作台', '/engineer': '工程师工作台', '/supervisor': '主管看板' }
  return map[route.path] || '工作台'
})

const roleLabel = computed(() => {
  const map = { employee: '员工', engineer: '工程师', supervisor: '主管' }
  return map[userStore.currentUser?.role] || ''
})

const roleTagType = computed(() => {
  const map = { employee: 'success', engineer: 'primary', supervisor: 'warning' }
  return map[userStore.currentUser?.role] || 'info'
})

function toggleDark() { isDark.value = !isDark.value }

function onMenuSelect() { /* 单页应用，无需跳转 */ }

function onUserCommand(cmd) {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-layout { height: 100vh; overflow: hidden; }

/* ===== 侧边栏 ===== */
.app-aside {
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
  transition: width .25s ease;
}
.logo-area {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid var(--el-border-color);
  overflow: hidden;
}
.logo-icon { font-size: 22px; }
.logo-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-color-primary);
  white-space: nowrap;
}
.app-menu { flex: 1; border-right: none; }
.aside-footer {
  padding: 12px;
  border-top: 1px solid var(--el-border-color);
  text-align: center;
}
.collapse-btn { font-size: 16px; }

/* ===== 顶栏 ===== */
.app-header {
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.header-left { display: flex; align-items: center; }
.header-right { display: flex; align-items: center; gap: 12px; }
.user-entry {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background .15s;
}
.user-entry:hover { background: var(--el-fill-color-light); }
.user-name { font-size: 14px; color: var(--el-text-color-primary); }
.avatar { background: var(--el-color-primary); color: #fff; font-weight: 600; }

/* ===== 主内容区 ===== */
.app-main-container { display: flex; flex-direction: column; flex: 1; overflow: hidden; }
.app-main {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: var(--el-bg-color-page);
}

/* ===== 动画 ===== */
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
