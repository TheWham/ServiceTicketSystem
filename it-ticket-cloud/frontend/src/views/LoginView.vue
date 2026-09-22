<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="card-header">
          <span class="logo">🛠 IT 服务工单系统</span>
          <div class="subtitle">请选择身份并输入密码登录</div>
        </div>
      </template>

      <!-- 用户列表 -->
      <div class="user-list">
        <div
          v-for="user in users"
          :key="user.user_id"
          class="user-item"
          :class="{ selected: selectedId === user.user_id }"
          @click="selectedId = user.user_id"
        >
          <el-avatar :size="40" class="avatar">{{ user.name[0] }}</el-avatar>
          <div class="info">
            <div class="name">{{ user.name }}</div>
            <div class="meta">{{ user.department }} · {{ roleMap[user.role] }}</div>
          </div>
          <el-tag :type="roleTagType(user.role)" size="small" effect="dark">
            {{ roleMap[user.role] }}
          </el-tag>
        </div>
      </div>

      <!-- 密码输入 -->
      <el-input
        v-model="password"
        type="password"
        placeholder="请输入密码（默认 123456）"
        size="large"
        show-password
        class="pwd-input"
        @keyup.enter="doLogin"
      >
        <template #prefix>
          <el-icon><Lock /></el-icon>
        </template>
      </el-input>

      <!-- 错误提示 -->
      <el-alert
        v-if="loginError"
        :title="loginError"
        type="error"
        :closable="false"
        class="login-error"
      />

      <!-- 登录按钮 -->
      <el-button
        type="primary"
        size="large"
        :loading="loading"
        :disabled="!selectedId"
        class="login-btn"
        @click="doLogin"
      >
        {{ loading ? '登录中...' : '进入系统' }}
      </el-button>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'

const roleMap = { employee: '员工', engineer: '工程师', supervisor: '主管' }
const roleTagType = (role) => ({ employee: 'success', engineer: 'primary', supervisor: 'warning' }[role] || 'info')

const users = ref([])
const selectedId = ref('')
const password = ref('')
const loading = ref(false)
const loginError = ref('')
const router = useRouter()
const userStore = useUserStore()

onMounted(async () => {
  try {
    const res = await userApi.loginOptions()
    users.value = res.data
  } catch (e) {
    ElMessage.error('获取登录选项失败：' + e.message)
  }
})

async function doLogin() {
  loading.value = true
  loginError.value = ''
  try {
    if (!selectedId.value) {
      loginError.value = '请选择登录身份'
      return
    }
    const res = await userApi.login({ userId: selectedId.value, password: password.value })
    userStore.setLogin(res.data.user, res.data.token)
    ElMessage.success(`欢迎，${res.data.user.name}`)
    const roleRoute = { employee: '/employee', engineer: '/engineer', supervisor: '/supervisor' }
    router.push(roleRoute[res.data.user.role])
  } catch (e) {
    loginError.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

html.dark .login-page {
  background: linear-gradient(135deg, #1a1f3a 0%, #2d1b3d 100%);
}

.login-card {
  width: 480px;
  border-radius: 12px;
}

.card-header {
  text-align: center;
}

.logo {
  font-size: 22px;
  font-weight: 700;
  color: var(--el-color-primary);
  display: block;
}

.subtitle {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-top: 6px;
}

.user-list {
  max-height: 320px;
  overflow-y: auto;
  margin-bottom: 20px;
}

.user-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  border: 2px solid transparent;
  margin-bottom: 4px;
  transition: all .2s;
}

.user-item:hover {
  background: var(--el-fill-color-light);
}

.user-item.selected {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

html.dark .user-item.selected {
  background: rgba(91, 140, 255, 0.15);
}

.avatar {
  background: var(--el-color-primary);
  color: #fff;
  font-weight: 600;
  flex-shrink: 0;
}

.info { flex: 1; min-width: 0; }
.name { font-size: 15px; font-weight: 600; color: var(--el-text-color-primary); }
.meta { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; }

.pwd-input { margin-bottom: 12px; }

.login-error { margin-bottom: 12px; }

.login-btn {
  width: 100%;
  letter-spacing: 4px;
}
</style>
