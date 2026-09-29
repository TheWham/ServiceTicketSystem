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
          <el-avatar :size="40" class="avatar">{{ getUserAvatar(user) }}</el-avatar>
          <div class="info">
            <div class="name">{{ getUserDisplayName(user) }}</div>
            <div class="meta">{{ getUserDepartment(user) }} · {{ roleMap[user.role] }}</div>
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

const roleMap = {
  EMPLOYEE: '员工',
  ENGINEER: '工程师',
  PLATFORM_ADMIN: '平台管理员',
  KB_ADMIN: '知识库管理员',
  employee: '员工',
  engineer: '工程师',
  supervisor: '主管',
  knowledge_admin: '知识库管理员',
  kb_admin: '知识库管理员'
}

const roleTagType = (role) => {
  const r = (role || '').toUpperCase()
  if (r === 'EMPLOYEE') return 'success'
  if (r === 'ENGINEER') return 'primary'
  if (r === 'PLATFORM_ADMIN' || r === 'SUPERVISOR') return 'warning'
  if (r === 'KB_ADMIN' || r === 'KNOWLEDGE_ADMIN') return 'danger'
  return 'info'
}

const getUserDisplayName = (user) => {
  if (!user) return ''
  const r = (user.role || '').toUpperCase()
  if (r === 'KB_ADMIN' || r === 'KNOWLEDGE_ADMIN' || user.user_id === 'kb_admin' || user.user_id === 'U_KBA01') {
    return '知识库管理员'
  }
  return user.name || ''
}

const getUserAvatar = (user) => {
  const displayName = getUserDisplayName(user)
  return displayName ? displayName[0] : '知'
}

const getUserDepartment = (user) => {
  if (!user) return ''
  const r = (user.role || '').toUpperCase()
  if (r === 'KB_ADMIN' || r === 'KNOWLEDGE_ADMIN' || user.user_id === 'kb_admin' || user.user_id === 'U_KBA01') {
    return 'IT部'
  }
  return user.department || user.department_id || 'IT部'
}

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
    const rawList = res.data || []
    const list = rawList.map(u => {
      const r = (u.role || '').toUpperCase()
      if (r === 'KB_ADMIN' || r === 'KNOWLEDGE_ADMIN' || u.user_id === 'kb_admin' || u.user_id === 'U_KBA01' || u.name === '孙知识') {
        return {
          ...u,
          name: '知识库管理员',
          department: 'IT部',
          role: 'KB_ADMIN'
        }
      }
      return u
    })
    const hasKb = list.some(u => {
      const r = (u.role || '').toUpperCase()
      return r === 'KB_ADMIN' || r === 'KNOWLEDGE_ADMIN' || u.user_id === 'kb_admin' || u.user_id === 'U_KBA01'
    })
    if (!hasKb) {
      list.push({ user_id: 'U_KBA01', name: '知识库管理员', department: 'IT部', role: 'KB_ADMIN' })
    }
    users.value = list
  } catch (e) {
    ElMessage.error('获取登录选项失败：' + e.message)
    // 降级兜底预设
    users.value = [
      { user_id: 'U_EMP01', name: '演示员工', department: 'D001', role: 'EMPLOYEE' },
      { user_id: 'U_ENG01', name: '演示工程师', department: 'D002', role: 'ENGINEER' },
      { user_id: 'U_ADM01', name: '平台管理员', department: 'D003', role: 'PLATFORM_ADMIN' },
      { user_id: 'U_KBA01', name: '知识库管理员', department: 'IT部', role: 'KB_ADMIN' }
    ]
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
    if (res.data && res.data.user) {
      const r = (res.data.user.role || '').toUpperCase()
      if (r === 'KB_ADMIN' || r === 'KNOWLEDGE_ADMIN' || res.data.user.user_id === 'kb_admin' || res.data.user.user_id === 'U_KBA01') {
        res.data.user.name = '知识库管理员'
        res.data.user.department = 'IT部'
      }
    }
    userStore.setLogin(res.data.user, res.data.token)
    ElMessage.success(`欢迎，${res.data.user.name}`)
    const role = (res.data.user.role || '').toUpperCase()
    const roleRoute = {
      EMPLOYEE: '/employee',
      ENGINEER: '/engineer',
      PLATFORM_ADMIN: '/supervisor',
      SUPERVISOR: '/supervisor',
      KB_ADMIN: '/knowledge-admin',
      KNOWLEDGE_ADMIN: '/knowledge-admin'
    }
    router.push(roleRoute[role] || (role.includes('KB') ? '/knowledge-admin' : '/employee'))
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
