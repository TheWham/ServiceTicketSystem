<template>
  <div class="login-page">
    <div class="login-panel">
      <aside class="brand-side" aria-label="IT 服务工单系统">
        <div class="brand-logo"><span class="logo-mark" aria-hidden="true">&gt;_</span><span>IT 服务工单系统</span></div>
        <div class="brand-story">
          <p class="brand-eyebrow">IT SERVICE DESK / 工作空间</p>
          <h1>每一个问题，<br>都有下一步。</h1>
          <p class="brand-intro">从一次咨询到问题解决，<br>在同一个工作台，找到支持与回应。</p>
          <div class="service-lines">
            <div><span>01</span><p><strong>描述问题</strong>向 IT 服务助手咨询，或提交服务请求。</p></div>
            <div><span>02</span><p><strong>协同处理</strong>与工程师保持沟通，补充问题细节。</p></div>
            <div><span>03</span><p><strong>跟进结果</strong>查看处理进度，确认问题是否解决。</p></div>
          </div>
        </div>
        <p class="brand-footer">咨询 · 工单 · 知识</p>
      </aside>

      <main class="form-side">
        <div class="form-box">
          <p class="form-eyebrow">欢迎回来</p>
          <h2 class="form-title">登录工作台</h2>
          <p class="form-sub">使用你的工作账号，继续今天的工作。</p>
          <el-alert v-if="userStore.sessionError" :title="userStore.sessionError" type="warning" :closable="false" class="login-error">
            <el-button v-if="userStore.token" text type="primary" :loading="restoringSession" @click="retrySession">重新核验登录身份</el-button>
          </el-alert>
          <form class="login-form" @submit.prevent="doLogin">
            <label for="login-account" class="field-label">账号</label>
            <el-input id="login-account" v-model="selectedId" name="username" autocomplete="username"
                      placeholder="请输入账号" size="large" :disabled="loading" />
            <div class="account-options" :aria-busy="optionsLoading">
              <p v-if="optionsLoading" role="status">正在加载可用账号…</p>
              <div v-else-if="optionsError" class="options-error" role="status">
                <span>账号列表加载失败：{{ optionsError }}。仍可输入账号登录。</span>
                <el-button text type="primary" size="small" @click="loadOptions">重新加载</el-button>
              </div>
              <el-select v-else-if="users.length" v-model="selectedId" placeholder="或从可用账号中选择" filterable
                         aria-label="选择已有账号" :disabled="loading" class="account-select">
                <el-option v-for="user in users" :key="user.user_id" :value="user.user_id"
                           :label="`${user.name || user.user_id} · ${roleMap[user.role] || user.role} · ${user.user_id}`" />
              </el-select>
              <p v-else>暂无可选账号，可直接输入账号登录。</p>
            </div>
            <label for="login-password" class="field-label">密码</label>
            <el-input id="login-password" v-model="password" name="password" type="password" autocomplete="current-password"
                      placeholder="请输入密码" size="large" show-password :disabled="loading">
              <template #prefix><el-icon><Lock /></el-icon></template>
            </el-input>
            <el-alert v-if="loginError" :title="loginError" type="error" :closable="false" show-icon class="login-error" />
            <el-button type="primary" native-type="submit" size="large" :loading="loading"
                       :disabled="!selectedId.trim() || !password" class="login-btn">
              {{ loading ? '正在登录…' : '登录工作台' }}
            </el-button>
          </form>
          <div class="form-foot"><el-button text type="primary" @click="forgotVisible = true">忘记密码？</el-button></div>
          <p class="login-note">账号由管理员分配。如需开通账号，请联系 IT 服务团队。</p>
        </div>
      </main>
    </div>

    <el-dialog v-model="forgotVisible" title="找回密码" width="min(440px, 94vw)" :close-on-click-modal="false"
               :close-on-press-escape="!forgotLoading" :show-close="!forgotLoading" @closed="resetForgot">
      <el-alert type="info" :closable="false" class="forgot-tip" title="核对账号信息后，为你的账号设置新密码。" />
      <el-form :model="forgotForm" label-position="top" @submit.prevent="doForgot">
        <el-form-item label="账号" required><el-input v-model="forgotForm.user_id" autocomplete="username" :disabled="forgotLoading" /></el-form-item>
        <el-form-item label="姓名" required><el-input v-model="forgotForm.name" autocomplete="name" :disabled="forgotLoading" /></el-form-item>
        <el-form-item label="员工号" required><el-input v-model="forgotForm.employee_no" :disabled="forgotLoading" /></el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="forgotForm.new_password" type="password" autocomplete="new-password" show-password
                    placeholder="6–32 位，包含字母和数字" :disabled="forgotLoading" />
        </el-form-item>
        <div class="forgot-actions">
          <el-button :disabled="forgotLoading" @click="forgotVisible = false">取消</el-button>
          <el-button type="primary" native-type="submit" :loading="forgotLoading">重置密码</el-button>
        </div>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'

const roleMap = { EMPLOYEE: '员工', ENGINEER: '工程师', PLATFORM_ADMIN: '平台管理员', KNOWLEDGE_ADMIN: '知识库管理员' }
const roleRoute = { EMPLOYEE: '/employee', ENGINEER: '/engineer', PLATFORM_ADMIN: '/dispatch', KNOWLEDGE_ADMIN: '/knowledge-admin' }
const users = ref([])
const selectedId = ref('')
const password = ref('')
const loading = ref(false)
const loginError = ref('')
const optionsLoading = ref(false)
const optionsError = ref('')
const restoringSession = ref(false)
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const forgotVisible = ref(false)
const forgotLoading = ref(false)
const forgotForm = ref({ user_id: '', name: '', employee_no: '', new_password: '' })

async function retrySession() {
  if (restoringSession.value) return
  restoringSession.value = true
  try {
    await userStore.restoreSession(userApi.getMe)
    if (userStore.currentUser) router.push({ path: roleRoute[userStore.currentUser.role], query: route.query })
  } finally { restoringSession.value = false }
}

function resetForgot() {
  forgotForm.value = { user_id: '', name: '', employee_no: '', new_password: '' }
}

async function doForgot() {
  if (forgotLoading.value) return
  const f = forgotForm.value
  if (!f.user_id.trim() || !f.name.trim() || !f.employee_no.trim() || !f.new_password) {
    ElMessage.warning('请填写完整的身份验证信息和新密码')
    return
  }
  forgotLoading.value = true
  try {
    await userApi.forgotPassword({ user_id: f.user_id.trim(), name: f.name.trim(), employee_no: f.employee_no.trim(), new_password: f.new_password })
    ElMessage.success('密码已重置，请使用新密码登录')
    forgotVisible.value = false
    resetForgot()
    password.value = ''
  } catch (e) {
    ElMessage.error(e.message || '重置失败，请重试')
  } finally {
    forgotLoading.value = false
  }
}

async function loadOptions() {
  if (optionsLoading.value) return
  optionsLoading.value = true
  optionsError.value = ''
  try {
    const res = await userApi.loginOptions()
    users.value = res.data || []
  } catch (e) {
    users.value = []
    optionsError.value = e.message || '服务暂不可用'
  } finally {
    optionsLoading.value = false
  }
}
onMounted(loadOptions)

async function doLogin() {
  if (loading.value) return
  loginError.value = ''
  if (!selectedId.value.trim() || !password.value) {
    loginError.value = '请输入账号和密码'
    return
  }
  loading.value = true
  try {
    const res = await userApi.login({ user_id: selectedId.value.trim(), password: password.value })
    userStore.setLogin(res.data.user, res.data.token)
    ElMessage.success(`欢迎，${res.data.user.name}`)
    if (!roleRoute[res.data.user.role]) throw new Error('登录身份不可用，请联系管理员。')
    const path = roleRoute[res.data.user.role]
    router.push(route.query.ticket ? { path, query: { ticket: route.query.ticket } } : path)
  } catch (e) {
    loginError.value = e.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100dvh; display: grid; place-items: center; padding: clamp(16px, 4vw, 56px); background: var(--el-bg-color-page); color: var(--el-text-color-primary); }
.login-panel { display: grid; grid-template-columns: 1fr 1fr; width: min(1080px, 100%); min-height: 680px; border: 1px solid var(--el-border-color); border-radius: 10px; overflow: hidden; background: var(--el-bg-color); }
.brand-side { display: flex; flex-direction: column; padding: clamp(28px, 4vw, 52px); background: var(--ws-nav); border-right: 1px solid var(--el-border-color); box-shadow: inset 0 3px 0 var(--el-color-primary); }
.brand-logo { display: flex; align-items: center; gap: 12px; font-size: 15px; font-weight: 600; }
.logo-mark { width: 36px; height: 36px; border: 1px solid var(--el-color-primary); border-radius: 5px; display: grid; place-items: center; color: var(--el-color-primary); background: var(--ws-accent-soft); font: 600 17px var(--ws-font-mono); }
.brand-story { margin: auto 0; padding: 48px 0 32px; }
.brand-eyebrow, .form-eyebrow { color: var(--el-color-primary); font: 12px var(--ws-font-mono); letter-spacing: .06em; margin: 0 0 20px; }
.brand-story h1 { font-size: clamp(32px, 3.5vw, 44px); line-height: 1.35; letter-spacing: -.03em; font-weight: 600; margin: 0 0 22px; }
.brand-intro { font-size: 14px; color: var(--el-text-color-regular); line-height: 1.9; margin-bottom: 34px; }
.service-lines { border-top: 1px solid var(--el-border-color); }
.service-lines > div { display: flex; gap: 18px; padding: 14px 0; border-bottom: 1px solid var(--el-border-color); }
.service-lines > div > span { color: var(--el-color-primary); font: 12px var(--ws-font-mono); padding-top: 3px; font-variant-numeric: tabular-nums; }
.service-lines p { margin: 0; font-size: 12px; line-height: 1.7; color: var(--el-text-color-regular); }
.service-lines strong { display: block; color: var(--el-text-color-primary); font-size: 13px; font-weight: 600; margin-bottom: 2px; }
.brand-footer { color: var(--el-text-color-secondary); font-size: 12px; margin: 0; letter-spacing: .14em; }
.form-side { display: grid; place-items: center; padding: clamp(24px, 4vw, 56px); }
.form-box { width: 100%; max-width: 360px; }
.form-eyebrow { margin-bottom: 12px; }
.form-title { font-size: 28px; letter-spacing: -.03em; font-weight: 600; margin: 0 0 10px; }
.form-sub { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.7; margin: 0 0 30px; }
.field-label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 9px; }
.account-options { min-height: 40px; margin: 10px 0 22px; font-size: 12px; color: var(--el-text-color-secondary); line-height: 1.6; }
.account-options p { margin: 0; }
.account-select { width: 100%; }
.options-error { color: var(--el-text-color-regular); }
.options-error .el-button { padding-left: 0; }
.login-error { margin-top: 16px; }
.login-btn { width: 100%; margin-top: 24px; font-weight: 600; }
.form-foot { margin-top: 8px; text-align: right; }
.login-note { border-top: 1px solid var(--el-border-color-lighter); margin: 24px 0 0; padding-top: 20px; font-size: 12px; line-height: 1.8; color: var(--el-text-color-secondary); }
.forgot-tip { margin-bottom: 20px; }
.forgot-actions { display: flex; justify-content: flex-end; gap: 8px; }
@media (max-width: 760px) {
  .login-page { padding: 16px; }
  .login-panel { grid-template-columns: 1fr; min-height: auto; border-radius: 10px; }
  .brand-side { border-right: 0; border-bottom: 1px solid var(--el-border-color-lighter); padding: 22px 24px; }
  .brand-story, .brand-footer { display: none; }
  .form-side { padding: 32px 24px; }
}
</style>
