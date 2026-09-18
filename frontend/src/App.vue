<template>
  <div id="app-root">
    <header class="app-header" v-if="userStore.userId">
      <div class="header-left">
        <span class="logo">🛠 IT 工单系统</span>
        <span class="role-badge" :class="userStore.currentUser?.role">
          {{ roleLabel }}
        </span>
      </div>
      <div class="header-right">
        <span class="user-name">{{ userStore.currentUser?.name }}</span>
        <button class="btn-sm" @click="logout">切换账号</button>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from './stores/user.js'

const userStore = useUserStore()
const router = useRouter()

const roleLabel = computed(() => {
  const map = { employee: '员工', engineer: '工程师', supervisor: '主管' }
  return map[userStore.currentUser?.role] || ''
})

function logout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f0f2f5; color: #333; }
#app-root { min-height: 100vh; display: flex; flex-direction: column; }
.app-header { background: #fff; border-bottom: 1px solid #e8e8e8; padding: 0 24px; height: 56px; display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
.header-left { display: flex; align-items: center; gap: 12px; }
.logo { font-size: 18px; font-weight: 700; color: #1a73e8; }
.role-badge { padding: 2px 10px; border-radius: 12px; font-size: 12px; color: #fff; }
.role-badge.employee { background: #52c41a; }
.role-badge.engineer { background: #1890ff; }
.role-badge.supervisor { background: #722ed1; }
.header-right { display: flex; align-items: center; gap: 12px; }
.user-name { font-size: 14px; color: #666; }
.btn-sm { padding: 4px 12px; font-size: 12px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; cursor: pointer; color: #666; }
.btn-sm:hover { color: #1a73e8; border-color: #1a73e8; }
.app-main { flex: 1; padding: 24px; max-width: 1400px; width: 100%; margin: 0 auto; }
</style>