<template>
  <!-- 登录页：无侧边栏布局 -->
  <router-view v-if="isLoginPage" />

  <!-- 已登录：经典后台布局 -->
  <div v-else class="app-shell">
  <el-container class="app-layout">
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
        <!-- 智能客服与转人工(PRD F-02/F-03),仅员工可见 -->
        <el-menu-item v-if="userStore.isEmployee" index="consultation">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>智能客服</template>
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

    <!-- ===== 智能客服对话框入口(PRD F-02/F-03,仅员工) ===== -->
    <template v-if="userStore.isEmployee">
      <transition name="fade">
        <button v-show="!isLoginPage" class="chat-fab" title="智能客服 / 转人工"
                @click="consultOpen = true">
          <el-icon :size="22"><ChatDotRound /></el-icon>
        </button>
      </transition>

      <el-drawer v-model="consultOpen" title="智能客服" size="540px"
                 :append-to-body="true" :close-on-click-modal="false"
                 destroy-on-close class="consult-drawer">
        <ConsultationChat @navigate="consultOpen = false" />
      </el-drawer>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from './stores/user.js'
import ConsultationChat from './components/ConsultationChat.vue'
import {
  Monitor, Expand, Fold, Sunny, Moon, User, SwitchButton, ChatDotRound
} from '@element-plus/icons-vue'

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const collapse = ref(false)
const isDark = ref(localStorage.getItem('app_theme') === 'dark')
/** 智能客服对话框(转人工入口不再整页跳转) */
const consultOpen = ref(false)

// 初始化主题
watch(isDark, (val) => {
  document.documentElement.classList.toggle('dark', val)
  localStorage.setItem('app_theme', val ? 'dark' : 'light')
}, { immediate: true })

const isLoginPage = computed(() => route.path === '/login')

const activeMenu = computed(() => (route.path === '/consultation' ? 'consultation' : 'home'))

const breadcrumb = computed(() => {
  const map = { '/employee': '员工工作台', '/engineer': '工程师工作台', '/supervisor': '主管看板', '/consultation': '智能客服' }
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

function onMenuSelect(index) {
  // 智能客服入口是对话框(抽屉),不再整页跳转
  if (index === 'consultation') {
    consultOpen.value = true
    return
  }
  const target = { employee: '/employee', engineer: '/engineer', supervisor: '/supervisor' }[userStore.currentUser?.role]
  if (target && route.path !== target) router.push(target)
}

function onUserCommand(cmd) {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-shell { height: 100vh; overflow: hidden; }
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

/* ===== 智能客服悬浮入口 ===== */
.chat-fab {
  position: fixed; right: 28px; bottom: 32px; z-index: 100;
  width: 52px; height: 52px; border-radius: 50%;
  border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  background: var(--el-color-primary); color: #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, .22);
  transition: transform .15s ease, box-shadow .15s ease;
}
.chat-fab:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 22px rgba(0, 0, 0, .28);
}

/* ===== 动画 ===== */
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
