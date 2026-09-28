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

const roleMap = { employee: '员工', engineer: '工程师', supervisor: '主管', knowledge_admin: '知识库管理员' }
const roleTagType = (role) => ({ employee: 'success', engineer: 'primary', supervisor: 'warning', knowledge_admin: 'danger' }[role] || 'info')

const getUserDisplayName = (user) => {
  if (!user) return ''
  if (user.role === 'knowledge_admin' || user.user_id === 'kb_admin' || user.name === '孙知识') {
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
  if (user.role === 'knowledge_admin' || user.user_id === 'kb_admin') {
    return 'IT部'
  }
  return user.department || ''
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
      if (u.role === 'knowledge_admin' || u.user_id === 'kb_admin' || u.name === '孙知识') {
        return {
          ...u,
          name: '知识库管理员',
          department: 'IT部',
          role: 'knowledge_admin'
        }
      }
      return u
    })
    const hasKb = list.some(u => u.role === 'knowledge_admin' || u.user_id === 'kb_admin')
    if (!hasKb) {
      list.push({ user_id: 'kb_admin', name: '知识库管理员', department: 'IT部', role: 'knowledge_admin' })
    }
    users.value = list
  } catch (e) {
    ElMessage.error('获取登录选项失败：' + e.message)
    // 降级兜底预设
    users.value = [
      { user_id: 'emp_01', name: '张小明', department: '市场部', role: 'employee' },
      { user_id: 'emp_02', name: '李丽', department: '财务部', role: 'employee' },
      { user_id: 'emp_03', name: '王强', department: '研发部', role: 'employee' },
      { user_id: 'eng_01', name: '赵工', department: 'IT部', role: 'engineer' },
      { user_id: 'eng_02', name: '钱工', department: 'IT部', role: 'engineer' },
      { user_id: 'sup_01', name: '周主管', department: 'IT部', role: 'supervisor' },
      { user_id: 'kb_admin', name: '知识库管理员', department: 'IT部', role: 'knowledge_admin' }
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
      if (res.data.user.role === 'knowledge_admin' || res.data.user.user_id === 'kb_admin' || res.data.user.name === '孙知识') {
        res.data.user.name = '知识库管理员'
        res.data.user.department = 'IT部'
      }
    }
    userStore.setLogin(res.data.user, res.data.token)
    ElMessage.success(`欢迎，${res.data.user.name}`)
    const roleRoute = {
      employee: '/employee',
      engineer: '/engineer',
      supervisor: '/supervisor',
      knowledge_admin: '/knowledge-admin'
    }
    router.push(roleRoute[res.data.user.role] || '/knowledge-admin')
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
