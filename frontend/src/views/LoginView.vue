<template>
  <div class="login-page">
    <!-- 左侧品牌展示区 -->
    <div class="brand-panel">
      <div class="glow glow-a"></div>
      <div class="glow glow-b"></div>
      <div class="grid-overlay"></div>
      <div class="brand-inner">
        <div class="brand-logo">
          <span class="logo-icon">🛠</span>
          <span>IT 服务工单系统</span>
        </div>
        <h1 class="brand-title">一站式 IT 服务<br />请求与工单流转平台</h1>
        <p class="brand-desc">智能受理 · 高效协同 · 全程可追踪</p>
        <ul class="brand-features">
          <li><span class="dot"></span>AI 智能预受理，秒级响应员工诉求</li>
          <li><span class="dot"></span>工单全流程 SLA 跟踪与超时预警</li>
          <li><span class="dot"></span>站内信实时通知，处理进展不遗漏</li>
        </ul>
      </div>
      <div class="brand-footer">© IT Service Desk · 让每一次请求都有回音</div>
    </div>

    <!-- 右侧登录表单区 -->
    <div class="form-panel">
      <div class="form-card">
        <div class="form-header">
          <div class="form-logo">🛠</div>
          <h2 class="form-title">欢迎登录</h2>
          <p class="form-subtitle">请使用您的账号登录系统</p>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent>
          <el-form-item prop="user_id">
            <el-input
              v-model="form.user_id"
              placeholder="用户ID（如 U001）"
              :prefix-icon="User"
              clearable
              @keyup.enter="doLogin"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码（默认 123456）"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="doLogin"
            />
          </el-form-item>

          <div class="form-extra">
            <el-link type="primary" :underline="false" @click="forgotVisible = true">忘记密码？</el-link>
          </div>

          <el-alert
            v-if="loginError"
            :title="loginError"
            type="error"
            :closable="false"
            class="login-error"
          />

          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="doLogin"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form>
      </div>
    </div>

    <!-- 忘记密码弹窗：工号+姓名+员工号验证后重置 -->
    <el-dialog v-model="forgotVisible" title="忘记密码 · 身份验证" width="420px" :close-on-click-modal="false">
      <el-alert type="info" :closable="false" class="forgot-tip"
        title="请输入账号信息进行身份验证，验证通过后可设置新密码" />
      <el-form :model="forgotForm" label-width="90px" class="forgot-form">
        <el-form-item label="用户ID" required>
          <el-input v-model="forgotForm.user_id" placeholder="如 U_EMP01" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="forgotForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="员工号" required>
          <el-input v-model="forgotForm.employee_no" placeholder="如 E1001" />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="forgotForm.new_password" type="password" show-password
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
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'

const formRef = ref()
const form = reactive({ user_id: '', password: '' })
const rules = {
  user_id: [{ required: true, message: '请输入用户ID', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const loading = ref(false)
const loginError = ref('')
const router = useRouter()
const userStore = useUserStore()

// 忘记密码
const forgotVisible = ref(false)
const forgotLoading = ref(false)
const forgotForm = ref({ user_id: '', name: '', employee_no: '', new_password: '' })

async function doForgot() {
  const f = forgotForm.value
  if (!f.user_id || !f.name || !f.employee_no || !f.new_password) {
    ElMessage.warning('请填写完整的身份验证信息和新密码')
    return
  }
  forgotLoading.value = true
  try {
    await userApi.forgotPassword(f)
    ElMessage.success('密码已重置，请使用新密码登录')
    forgotVisible.value = false
    forgotForm.value = { user_id: '', name: '', employee_no: '', new_password: '' }
    form.password = ''
  } catch (e) {
    ElMessage.error(e.message || '重置失败')
  } finally {
    forgotLoading.value = false
  }
}

async function doLogin() {
  loginError.value = ''
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    // 登录接口契约：{ user_id, password }，角色经 user_role 关联返回
    const res = await userApi.login({ user_id: form.user_id.trim(), password: form.password })
    userStore.setLogin(res.data.user, res.data.token)
    ElMessage.success(`欢迎，${userStore.currentUser.name}`)
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
/* ---------- 页面骨架：左品牌区 + 右表单区 ---------- */
.login-page {
  display: flex;
  min-height: 100vh;
  background: #f4f6fb;
}

/* ---------- 左侧品牌区 ---------- */
.brand-panel {
  position: relative;
  flex: 1.2;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 56px 64px 40px;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(135deg, #4a63e7 0%, #6a3fd4 55%, #8e3bd8 100%);
}

.brand-inner {
  position: relative;
  z-index: 2;
  max-width: 520px;
  margin-top: 6vh;
  animation: fade-up .7s ease both;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 1px;
  opacity: .95;
}

.logo-icon { font-size: 22px; }

.brand-title {
  margin-top: 42px;
  font-size: 40px;
  line-height: 1.35;
  font-weight: 700;
  letter-spacing: 2px;
}

.brand-desc {
  margin-top: 18px;
  font-size: 16px;
  letter-spacing: 4px;
  opacity: .82;
}

.brand-features {
  margin-top: 52px;
  list-style: none;
}

.brand-features li {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  line-height: 2.6;
  opacity: .92;
}

.brand-features .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, .9);
  box-shadow: 0 0 10px rgba(255, 255, 255, .7);
  flex-shrink: 0;
}

.brand-footer {
  position: relative;
  z-index: 2;
  font-size: 13px;
  opacity: .55;
  letter-spacing: 1px;
}

/* 装饰光斑 */
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: .45;
  pointer-events: none;
}

.glow-a {
  width: 420px;
  height: 420px;
  top: -120px;
  right: -100px;
  background: #8fd3ff;
  animation: float 11s ease-in-out infinite;
}

.glow-b {
  width: 360px;
  height: 360px;
  bottom: -140px;
  left: -80px;
  background: #ff9ad5;
  animation: float 13s ease-in-out infinite reverse;
}

/* 细网格纹理 */
.grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, .06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, .06) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse at 30% 40%, #000 0%, transparent 75%);
  pointer-events: none;
}

/* ---------- 右侧表单区 ---------- */
.form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
}

.form-card {
  width: 100%;
  max-width: 400px;
  animation: fade-up .7s .1s ease both;
}

.form-header {
  text-align: center;
  margin-bottom: 34px;
}

.form-logo {
  width: 64px;
  height: 64px;
  margin: 0 auto 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  border-radius: 18px;
  background: linear-gradient(135deg, #4a63e7, #8e3bd8);
  box-shadow: 0 12px 28px rgba(96, 84, 224, .35);
}

.form-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: 1px;
}

.form-subtitle {
  margin-top: 8px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.form-extra {
  display: flex;
  justify-content: flex-end;
  margin: -6px 0 16px;
}

.login-error { margin-bottom: 16px; }

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  letter-spacing: 8px;
  border: none;
  background: linear-gradient(135deg, #4a63e7, #7a3fe0);
  box-shadow: 0 10px 24px rgba(96, 84, 224, .35);
  transition: transform .15s ease, box-shadow .15s ease, opacity .15s ease;
}

.login-btn:hover {
  opacity: .92;
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(96, 84, 224, .42);
}

.login-btn:active { transform: translateY(0); }

/* ---------- 深色模式 ---------- */
html.dark .login-page { background: #0d1020; }

/* ---------- 动效 ---------- */
@keyframes fade-up {
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(24px, 20px); }
}

/* ---------- 小屏适配：收起品牌区 ---------- */
@media (max-width: 900px) {
  .brand-panel { display: none; }
  .form-panel { flex: 1; }
}

.forgot-tip { margin-bottom: 16px; }
.forgot-form :deep(.el-form-item) { margin-bottom: 18px; }
</style>
