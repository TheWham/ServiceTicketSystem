<template>
  <div class="login-page">
    <div class="login-panel">
      <!-- 左侧：品牌区（简洁商务） -->
      <aside class="brand-side">
        <div class="brand-inner">
          <div class="brand-logo">
            <span class="logo-mark">🛠</span>
            <span class="logo-name">IT 服务工单系统</span>
          </div>
          <p class="brand-slogan">统一入口 · 高效协同 · 全程可追踪</p>

          <ul class="feature-list">
            <li>
              <el-icon><Promotion /></el-icon>
              <div>
                <div class="f-title">智能派单</div>
                <div class="f-desc">按分类自动路由，加权负载均衡分配</div>
              </div>
            </li>
            <li>
              <el-icon><Timer /></el-icon>
              <div>
                <div class="f-title">SLA 计时</div>
                <div class="f-desc">工作时长精准计量，超时提醒与违约追踪</div>
              </div>
            </li>
            <li>
              <el-icon><Bell /></el-icon>
              <div>
                <div class="f-title">实时通知</div>
                <div class="f-desc">全节点消息触达，一键直达待办事项</div>
              </div>
            </li>
          </ul>

          <div class="brand-footer">企业级 IT 服务台 · 让每一次请求都有回应</div>
        </div>
      </aside>

      <!-- 右侧：登录卡片 -->
      <main class="form-side">
        <div class="form-box">
          <div class="form-head">
            <h1 class="form-title">欢迎登录</h1>
            <p class="form-sub">请输入账号和密码</p>
          </div>

          <!-- 账号输入 -->
          <el-input
            v-model="userId"
            placeholder="请输入用户ID（如 U_EMP01）"
            size="large"
            class="uid-input"
            @keyup.enter="doLogin"
          >
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>

          <!-- 密码输入 -->
          <el-input
            v-model="password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            class="pwd-input"
            @keyup.enter="doLogin"
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>

          <el-alert v-if="loginError" :title="loginError" type="error" :closable="false" class="login-error" />

          <el-button
            type="primary"
            size="large"
            :loading="loading"
            :disabled="!userId.trim()"
            class="login-btn"
            @click="doLogin"
          >
            {{ loading ? '登录中…' : '登 录' }}
          </el-button>

          <div class="form-foot">
            <el-link type="primary" :underline="false" @click="forgotVisible = true">忘记密码？</el-link>
          </div>
        </div>
      </main>
    </div>

    <!-- 忘记密码弹窗 -->
    <el-dialog v-model="forgotVisible" title="忘记密码 · 身份验证" width="420px" :close-on-click-modal="false">
      <el-alert type="info" :closable="false" class="forgot-tip"
        title="请输入账号信息进行身份验证，验证通过后可设置新密码" />
      <el-form :model="forgotForm" label-width="90px" class="forgot-form">
        <el-form-item label="用户ID" required>
          <el-input v-model="forgotForm.userId" placeholder="如 U_EMP01" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="forgotForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="员工号" required>
          <el-input v-model="forgotForm.employeeNo" placeholder="如 E1001" />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="forgotForm.newPassword" type="password" show-password placeholder="6-32位，含字母和数字" />
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User, Promotion, Timer, Bell } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'

const userId = ref('')
const password = ref('')
const loading = ref(false)
const loginError = ref('')
const router = useRouter()
const userStore = useUserStore()

const forgotVisible = ref(false)
const forgotLoading = ref(false)
const forgotForm = ref({ userId: '', name: '', employeeNo: '', newPassword: '' })

async function doForgot() {
  const f = forgotForm.value
  if (!f.userId || !f.name || !f.employeeNo || !f.newPassword) {
    ElMessage.warning('请填写完整的身份验证信息和新密码')
    return
  }
  forgotLoading.value = true
  try {
    await userApi.forgotPassword(f)
    ElMessage.success('密码已重置，请使用新密码登录')
    forgotVisible.value = false
    forgotForm.value = { userId: '', name: '', employeeNo: '', newPassword: '' }
    password.value = ''
  } catch (e) {
    ElMessage.error(e.message || '重置失败')
  } finally {
    forgotLoading.value = false
  }
}

async function doLogin() {
  loading.value = true
  loginError.value = ''
  try {
    if (!userId.value.trim() || !password.value) {
      loginError.value = '请输入用户ID和密码'
      return
    }
    const res = await userApi.login({ userId: userId.value.trim(), password: password.value })
    userStore.setLogin(res.data.user, res.data.token)
    ElMessage.success(`欢迎，${res.data.user.name}`)
    const roleRoute = { EMPLOYEE: '/employee', ENGINEER: '/engineer', PLATFORM_ADMIN: '/supervisor', KB_ADMIN: '/supervisor' }
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
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: #f0f2f5;
}
html.dark .login-page { background: #101418; }

/* 双栏面板 */
.login-panel {
  display: flex;
  width: 920px;
  max-width: 100%;
  min-height: 560px;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 12px 48px rgba(31, 45, 61, 0.12);
}
html.dark .login-panel { background: #1b2129; box-shadow: 0 12px 48px rgba(0,0,0,.5); }

/* ===== 左侧品牌区：深蓝商务 ===== */
.brand-side {
  width: 380px;
  flex-shrink: 0;
  background: linear-gradient(160deg, #1e3a5f 0%, #16324f 55%, #12283f 100%);
  color: #fff;
  display: flex;
  align-items: center;
  padding: 48px 40px;
}
.brand-inner { width: 100%; }

.brand-logo { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.logo-mark {
  font-size: 30px;
  width: 52px; height: 52px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,.12);
  border-radius: 12px;
}
.logo-name { font-size: 20px; font-weight: 700; letter-spacing: 1px; }
.brand-slogan { font-size: 14px; color: rgba(255,255,255,.75); margin: 0 0 40px; letter-spacing: 2px; }

.feature-list { list-style: none; margin: 0 0 40px; padding: 0; }
.feature-list li { display: flex; gap: 14px; align-items: flex-start; margin-bottom: 26px; }
.feature-list .el-icon {
  font-size: 20px; color: #7ec1ff; flex-shrink: 0; margin-top: 2px;
}
.f-title { font-size: 15px; font-weight: 600; margin-bottom: 3px; }
.f-desc { font-size: 12px; color: rgba(255,255,255,.6); line-height: 1.5; }

.brand-footer {
  font-size: 12px; color: rgba(255,255,255,.45);
  padding-top: 22px; border-top: 1px solid rgba(255,255,255,.12);
  letter-spacing: 1px;
}

/* ===== 右侧登录表单 ===== */
.form-side { flex: 1; display: flex; align-items: center; padding: 48px 48px; }
.form-box { width: 100%; max-width: 360px; margin: 0 auto; }

.form-head { margin-bottom: 26px; }
.form-title { font-size: 26px; font-weight: 700; color: var(--el-text-color-primary); margin: 0 0 6px; }
.form-sub { font-size: 13px; color: var(--el-text-color-secondary); margin: 0; }


.uid-input { margin-bottom: 12px; }
.pwd-input { margin-bottom: 12px; }
.login-error { margin-bottom: 12px; }
.login-btn { width: 100%; letter-spacing: 6px; font-weight: 600; }

.form-foot { margin-top: 16px; text-align: center; }

.forgot-tip { margin-bottom: 16px; }
.forgot-form :deep(.el-form-item) { margin-bottom: 18px; }

/* 响应式：窄屏隐藏品牌区 */
@media (max-width: 768px) {
  .brand-side { display: none; }
  .login-panel { width: 100%; }
}
</style>
