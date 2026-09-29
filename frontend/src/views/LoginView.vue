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
          <el-avatar :size="40" class="avatar">{{ (user.display_name || user.name || '?')[0] }}</el-avatar>
          <div class="info">
            <div class="name">{{ user.display_name || user.name }}</div>
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

      <!-- 忘记密码入口 -->
      <div class="forgot-link">
        <el-link type="primary" :underline="false" @click="forgotVisible = true">忘记密码？</el-link>
      </div>
    </el-card>

    <!-- 忘记密码弹窗：工号+姓名+员工号验证后重置 -->
    <el-dialog v-model="forgotVisible" title="忘记密码 · 身份验证" width="420px" :close-on-click-modal="false">
      <el-alert type="info" :closable="false" class="forgot-tip"
        title="请输入账号信息进行身份验证，验证通过后可设置新密码" />
      <el-form :model="forgotForm" label-width="90px" class="forgot-form">
        <el-form-item label="用户ID" required>
          <el-input v-model="forgotForm.userId" placeholder="如 U_EMP01" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="forgotForm.display_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="员工号" required>
          <el-input v-model="forgotForm.employeeNo" placeholder="如 E1001" />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="forgotForm.newPassword" type="password" show-password
            placeholder="6-32位，含字母和数字" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="forgotVisible = false">取消</el-button>
        <el-button type="primary" :loading="forgotLoading" @click="doForgot">重置密码</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'

// PRD §5.1 角色值域（大写）：EMPLOYEE/ENGINEER/PLATFORM_ADMIN/KNOWLEDGE_ADMIN
const roleMap = { EMPLOYEE: '员工', ENGINEER: '工程师', PLATFORM_ADMIN: '平台管理员', KNOWLEDGE_ADMIN: '知识库管理员' }
const roleTagType = (role) => ({ EMPLOYEE: 'success', ENGINEER: 'primary', PLATFORM_ADMIN: 'warning', KNOWLEDGE_ADMIN: 'danger' }[role] || 'info')

const users = ref([])
const selectedId = ref('')
const password = ref('')
const loading = ref(false)
const loginError = ref('')
const router = useRouter()
const userStore = useUserStore()

// 忘记密码
const forgotVisible = ref(false)
const forgotLoading = ref(false)
const forgotForm = ref({ userId: '', display_name: '', employeeNo: '', newPassword: '' })

async function doForgot() {
  const f = forgotForm.value
  if (!f.userId || !f.display_name || !f.employeeNo || !f.newPassword) {
    ElMessage.warning('请填写完整的身份验证信息和新密码')
    return
  }
  forgotLoading.value = true
  try {
    await userApi.forgotPassword(f)
    ElMessage.success('密码已重置，请使用新密码登录')
    forgotVisible.value = false
    forgotForm.value = { userId: '', display_name: '', employeeNo: '', newPassword: '' }
    password.value = ''
  } catch (e) {
    ElMessage.error(e.message || '重置失败')
  } finally {
    forgotLoading.value = false
  }
}

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
    ElMessage.success(`欢迎，${userStore.currentUser.display_name}`)
    const roleRoute = { EMPLOYEE: '/employee', ENGINEER: '/engineer', PLATFORM_ADMIN: '/supervisor', KNOWLEDGE_ADMIN: '/knowledge' }
    router.push(roleRoute[userStore.currentUser.role] || '/employee')
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

.forgot-link {
  margin-top: 14px;
  text-align: center;
}

.forgot-tip { margin-bottom: 16px; }
.forgot-form :deep(.el-form-item) { margin-bottom: 18px; }
</style>
