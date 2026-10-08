<template>
  <div class="login-page">
    <div class="login-panel">
      <aside class="brand-side">
        <div class="brand-logo"><span class="logo-mark"><el-icon aria-hidden="true"><Service /></el-icon></span><span class="logo-name">IT 服务台</span></div>
        <div class="brand-content">
          <span class="brand-eyebrow">YOUR EVERYDAY IT SUPPORT</span>
          <h2 class="brand-title">让工作顺畅，<br />让问题有回应。</h2>
          <p class="brand-slogan">从一次咨询到问题解决，<br />在同一个工作台连接每一步。</p>
          <div class="login-core-stage"><OrbitalCore /><div class="core-service-flow"><span>01 / 咨询</span><i></i><span>02 / 协同</span><i></i><span>03 / 解决</span></div></div>
        </div>
        <div class="brand-footer">统一求助入口 · 连接服务与知识</div>
      </aside>

      <main class="form-side">
        <div class="form-box">
          <div class="form-head"><span class="form-eyebrow">欢迎回来</span><h1 class="form-title">登录工作台</h1><p class="form-sub">使用您的企业账号，继续处理今天的工作。</p></div>
          <form class="login-form" @submit.prevent="doLogin" :aria-busy="loading">
            <div class="field-group"><label for="login-user-id">账号</label>
              <el-input id="login-user-id" v-model="userId" name="username" autocomplete="username" placeholder="请输入用户 ID" size="large" :aria-invalid="!!loginError" :aria-describedby="loginError ? 'login-error' : undefined"><template #prefix><el-icon aria-hidden="true"><User /></el-icon></template></el-input>
            </div>
            <div class="field-group"><div class="password-label"><label for="login-password">密码</label><button type="button" class="forgot-link" @click="forgotError = ''; forgotVisible = true">忘记密码？</button></div>
              <el-input id="login-password" v-model="password" name="password" type="password" autocomplete="current-password" placeholder="请输入密码" size="large" show-password :aria-invalid="!!loginError" :aria-describedby="loginError ? 'login-error' : undefined"><template #prefix><el-icon aria-hidden="true"><Lock /></el-icon></template></el-input>
            </div>
            <el-alert v-if="loginError" id="login-error" :title="loginError" type="error" show-icon :closable="false" class="login-error" role="alert" />
            <el-button native-type="submit" type="primary" size="large" :loading="loading" :disabled="!userId.trim()" class="login-btn">{{ loading ? '正在登录…' : '登录工作台' }}</el-button>
          </form>
          <p class="form-foot"><el-icon aria-hidden="true"><Lock /></el-icon>登录后将进入您所属角色的工作空间</p>
        </div>
        <span class="form-footer">IT 服务台 · 企业服务工作空间</span>
      </main>
    </div>

    <el-dialog v-model="forgotVisible" title="找回密码" width="min(440px, calc(100vw - 32px))" :close-on-click-modal="false">
      <el-alert type="info" :closable="false" show-icon class="forgot-tip" title="填写账号信息完成身份验证，验证通过后可设置新密码" />
      <el-form :model="forgotForm" label-position="top" class="forgot-form">
        <el-form-item label="账号" required><el-input v-model="forgotForm.userId" autocomplete="username" placeholder="请输入用户 ID" /></el-form-item>
        <el-form-item label="姓名" required><el-input v-model="forgotForm.name" autocomplete="name" placeholder="请输入姓名" /></el-form-item>
        <el-form-item label="员工号" required><el-input v-model="forgotForm.employeeNo" placeholder="请输入员工号" /></el-form-item>
        <el-form-item label="新密码" required><el-input v-model="forgotForm.newPassword" type="password" autocomplete="new-password" show-password placeholder="6–32 位，包含字母和数字" /></el-form-item>
        <el-alert v-if="forgotError" :title="forgotError" type="error" show-icon :closable="false" role="alert" />
      </el-form>
      <template #footer><el-button @click="forgotVisible = false">取消</el-button><el-button type="primary" :loading="forgotLoading" @click="doForgot">重置密码</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User, Service } from '@element-plus/icons-vue'
import OrbitalCore from '../components/OrbitalCore.vue'
import { useUserStore } from '../stores/user.js'
import { userApi } from '../api/index.js'
import { roleHome } from '../utils/navigation.js'

const userId = ref('')
const password = ref('')
const loading = ref(false)
const loginError = ref('')
const router = useRouter()
const userStore = useUserStore()

const forgotVisible = ref(false)
const forgotLoading = ref(false)
const forgotError = ref('')
const forgotForm = ref({ userId: '', name: '', employeeNo: '', newPassword: '' })

async function doForgot() {
  if (forgotLoading.value) return
  forgotError.value = ''
  const f = forgotForm.value
  if (!f.userId || !f.name || !f.employeeNo || !f.newPassword) {
    forgotError.value = '请填写完整的身份验证信息和新密码'
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
    forgotError.value = e.message || '重置失败，请稍后重试'
  } finally {
    forgotLoading.value = false
  }
}

async function doLogin() {
  if (loading.value) return
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
    router.push(roleHome(res.data.user.role))
  } catch (e) {
    loginError.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height:100vh; min-height:100dvh; display:grid; place-items:center; padding:40px 24px; background:var(--el-bg-color-page); }
.login-panel { display:grid; grid-template-columns:1fr 1fr; width:min(1080px,100%); min-height:680px; overflow:hidden; border-radius:24px; background:var(--el-bg-color); border:1px solid var(--el-border-color-lighter); box-shadow:0 24px 72px rgba(18,34,61,.1); }
.brand-side { position:relative; display:flex; flex-direction:column; justify-content:space-between; padding:40px 48px 32px; background:linear-gradient(145deg,#1E40AF 0%,#2563EB 64%,#1D4ED8 100%); color:#fff; overflow:hidden; }
.brand-side::before { content:''; position:absolute; width:380px; height:380px; border:1px solid rgba(255,255,255,.12); border-radius:50%; right:-210px; top:-150px; box-shadow:0 0 0 56px rgba(255,255,255,.035),0 0 0 112px rgba(255,255,255,.025); pointer-events:none; }
.brand-logo { display:flex; align-items:center; gap:12px; position:relative; }
.logo-mark { display:grid; place-items:center; width:40px; height:40px; font-size:24px; background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.2); border-radius:12px; }
.logo-name { font-size:20px; font-weight:700; letter-spacing:1px; }
.brand-content { position:relative; margin:40px 0 36px; }
.brand-eyebrow { font-size:11px; font-weight:650; letter-spacing:1.8px; color:#DBEAFE; }
.brand-title { margin:16px 0; font-size:36px; line-height:1.45; letter-spacing:1px; font-weight:650; }
.brand-slogan { margin:0; font-size:15px; line-height:1.8; color:#DBEAFE; }
.brand-footer { font-size:12px; color:#DBEAFE; border-top:1px solid rgba(255,255,255,.18); padding-top:20px; }
.form-side { position:relative; display:flex; align-items:center; padding:56px; }
.form-box { width:100%; max-width:360px; margin:auto; }
.form-head { margin-bottom:32px; }
.form-eyebrow { font-size:13px; color:var(--el-color-primary); font-weight:600; }
.form-title { margin:10px 0 12px; font-size:30px; line-height:1.35; color:var(--el-text-color-primary); font-weight:700; }
.form-sub { margin:0; font-size:14px; line-height:1.7; color:var(--el-text-color-secondary); }
.field-group { margin-bottom:22px; }
.field-group label { display:block; margin-bottom:10px; font-size:14px; font-weight:600; color:var(--el-text-color-primary); }
.password-label { display:flex; justify-content:space-between; align-items:baseline; gap:12px; }
.forgot-link { min-height:44px; padding:4px 0; border:0; background:none; color:var(--el-color-primary); font:inherit; font-size:13px; cursor:pointer; }
.forgot-link:hover { text-decoration:underline; }
.forgot-link:focus-visible { outline:2px solid var(--el-color-primary); outline-offset:4px; border-radius:4px; }
.login-form :deep(.el-input__wrapper) { min-height:48px; border-radius:10px; }
.login-error { margin-bottom:20px; }
.login-btn { width:100%; min-height:48px; border-radius:10px; font-size:16px; font-weight:600; }
.form-foot { display:flex; justify-content:center; align-items:center; gap:6px; margin:22px 0 0; color:var(--el-text-color-secondary); font-size:12px; line-height:1.6; }
.form-footer { position:absolute; bottom:28px; left:24px; right:24px; text-align:center; color:var(--el-text-color-secondary); font-size:12px; }
.forgot-tip { margin-bottom:20px; }
.forgot-form :deep(.el-form-item) { margin-bottom:18px; }
@media(max-width:1023px) { .brand-side { padding:32px; } .form-side { padding:40px 32px; } .brand-title { font-size:30px; } }
@media(max-width:767px) {
  .login-page { padding:20px 16px; align-items:start; }
  .login-panel { grid-template-columns:1fr; min-height:0; border-radius:20px; }
  .brand-side { padding:24px; }
  .brand-logo { gap:10px; }
  .logo-mark { width:36px; height:36px; font-size:22px; }
  .logo-name { font-size:18px; }
  .brand-content { margin:22px 0 0; }
  .brand-eyebrow, .brand-footer { display:none; }
  .brand-title { margin:0 0 10px; font-size:26px; line-height:1.45; }
  .brand-title br { display:none; }
  .brand-slogan { font-size:13px; }
  .brand-slogan br { display:none; }
  .form-side { padding:32px 24px 64px; }
  .form-title { font-size:26px; }
  .form-head { margin-bottom:26px; }
  .forgot-link { min-height:44px; display:flex; align-items:center; }
  .field-group { margin-bottom:18px; }
  .password-label { align-items:center; }
  .password-label label { margin-bottom:0; }
  .form-footer { bottom:20px; }
}
</style>
