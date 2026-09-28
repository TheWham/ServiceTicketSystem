<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="card-header">
          <span class="logo">🛠 IT 服务工单系统</span>
          <div class="subtitle">使用工号或手机号登录</div>
        </div>
      </template>

      <!-- 账号输入 -->
      <el-input
        v-model="account"
        placeholder="请输入工号（如 U001）或手机号"
        size="large"
        class="input-field"
        @keyup.enter="focusPassword"
      >
        <template #prefix>
          <el-icon><User /></el-icon>
        </template>
      </el-input>

      <!-- 密码输入 -->
      <el-input
        ref="passwordRef"
        v-model="password"
        type="password"
        placeholder="请输入密码（默认 123456）"
        size="large"
        show-password
        class="input-field"
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
        :disabled="!account || !password"
        class="login-btn"
        @click="doLogin"
      >
        {{ loading ? '登录中...' : '登 录' }}
      </el-button>

      <!-- 提示信息 -->
      <div class="login-hint">
        <el-text type="info" size="small">
          默认密码：123456
        </el-text>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'

const account = ref('')
const password = ref('')
const loading = ref(false)
const loginError = ref('')
const router = useRouter()
const userStore = useUserStore()
const passwordRef = ref(null)

// 点击账号输入框后，回车跳转到密码框
function focusPassword() {
  passwordRef.value?.focus()
}

async function doLogin() {
  if (!account.value || !password.value) {
    loginError.value = '请输入账号和密码'
    return
  }

  loading.value = true
  loginError.value = ''
  try {
    // 调用登录接口，userId 字段传工号或手机号
    const res = await userApi.login({ userId: account.value.trim(), password: password.value })
    userStore.setLogin(res.data.user, res.data.token)
    ElMessage.success(`欢迎，${res.data.user.name}`)
    const roleRoute = {
      employee: '/employee',
      engineer: '/engineer',
      supervisor: '/supervisor',
      customer_service: '/agent'
    }
    router.push(roleRoute[res.data.user.role] || '/employee')
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
  width: 420px;
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

.input-field {
  margin-bottom: 16px;
}

.login-error {
  margin-bottom: 12px;
}

.login-btn {
  width: 100%;
  letter-spacing: 8px;
  margin-top: 8px;
}

.login-hint {
  text-align: center;
  margin-top: 16px;
}
</style>
