<template>
  <div class="login-page">
    <div class="login-card">
      <h1>🛠 IT 服务工单系统</h1>
      <p class="subtitle">请选择模拟登录身份（P0 Mock 认证）</p>
      <div class="user-list">
        <div
          v-for="user in users"
          :key="user.user_id"
          class="user-item"
          :class="{ selected: selectedId === user.user_id }"
          @click="selectedId = user.user_id"
        >
          <span class="avatar">{{ user.name[0] }}</span>
          <div class="info">
            <div class="name">{{ user.name }}</div>
            <div class="meta">{{ user.department }} · {{ roleMap[user.role] }}</div>
          </div>
          <span class="role-tag" :class="user.role">{{ roleMap[user.role] }}</span>
        </div>
      </div>
      <button class="btn-primary" :disabled="!selectedId || loading" @click="doLogin">
        {{ loading ? '登录中...' : '进入系统' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'

const roleMap = { employee: '员工', engineer: '工程师', supervisor: '主管' }
const users = ref([])
const selectedId = ref('')
const loading = ref(false)
const router = useRouter()
const userStore = useUserStore()

onMounted(async () => {
  try {
    const res = await userApi.loginOptions()
    users.value = res.data
  } catch (e) { console.error(e) }
})

async function doLogin() {
  loading.value = true
  const user = users.value.find(u => u.user_id === selectedId.value)
  if (!user) {
    alert('请选择登录身份')
    loading.value = false
    return
  }
  userStore.setUser(user)
  const roleRoute = { employee: '/employee', engineer: '/engineer', supervisor: '/supervisor' }
  router.push(roleRoute[user.role])
  loading.value = false
}
</script>

<style scoped>
.login-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.login-card { background: #fff; border-radius: 16px; padding: 40px; width: 440px; box-shadow: 0 20px 60px rgba(0,0,0,.15); text-align: center; }
h1 { font-size: 24px; margin-bottom: 4px; }
.subtitle { color: #999; font-size: 14px; margin-bottom: 24px; }
.user-list { text-align: left; margin-bottom: 24px; max-height: 360px; overflow-y: auto; }
.user-item { display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: 8px; cursor: pointer; border: 2px solid transparent; margin-bottom: 4px; transition: all .2s; }
.user-item:hover { background: #f5f8ff; }
.user-item.selected { border-color: #1a73e8; background: #e8f0fe; }
.avatar { width: 40px; height: 40px; border-radius: 50%; background: #e0e0e0; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 600; color: #555; flex-shrink: 0; }
.info { flex: 1; }
.name { font-size: 15px; font-weight: 600; }
.meta { font-size: 12px; color: #999; }
.role-tag { font-size: 12px; padding: 2px 8px; border-radius: 10px; color: #fff; }
.role-tag.employee { background: #52c41a; }
.role-tag.engineer { background: #1890ff; }
.role-tag.supervisor { background: #722ed1; }
.btn-primary { width: 100%; padding: 12px; border: none; border-radius: 8px; background: #1a73e8; color: #fff; font-size: 16px; cursor: pointer; transition: opacity .2s; }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.btn-primary:hover:not(:disabled) { background: #1557b0; }
</style>