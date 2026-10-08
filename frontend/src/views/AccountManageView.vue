<template>
  <div class="account-page">
    <div class="page-head">
      <div><span class="page-eyebrow">ACCESS MANAGEMENT</span><h1 class="page-title">账号管理</h1><p class="page-sub">维护员工账号与角色权限，让每位成员进入对应工作台</p></div>
      <div class="heading-actions"><el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button><el-button type="primary" :icon="Plus" @click="openCreate">新建账号</el-button></div>
    </div>
    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false" class="page-error"><el-button link type="primary" @click="load">重新加载</el-button></el-alert>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="section-title">账号列表</span><span class="scope-note">已加载 {{ accounts.length }} 个账号</span>
        </div>
      </template>

      <el-table :data="accounts" v-loading="loading" stripe :empty-text="loadError ? '账号加载失败，请重试' : '暂无账号，可新建成员账号'">
        <el-table-column prop="user_id" label="用户ID" width="110" />
        <el-table-column prop="employee_no" label="员工号" width="100" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="department" label="部门" width="120">
          <template #default="{ row }">{{ row.department || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="140">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small" effect="dark">{{ roleMap[row.role] || row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" size="small">
              {{ row.status === 'ACTIVE' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="warning" size="small" @click="openRole(row)">修改角色</el-button>
            <el-button link type="primary" size="small" @click="openReset(row)">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建账号弹窗 -->
    <el-dialog v-model="createVisible" title="新建账号" width="min(460px, calc(100vw - 32px))" :close-on-click-modal="false">
      <el-form :model="createForm" label-position="top">
        <el-form-item label="用户ID" required>
          <el-input v-model="createForm.userId" placeholder="登录账号，如 U_EMP02" />
        </el-form-item>
        <el-form-item label="员工号" required>
          <el-input v-model="createForm.employeeNo" placeholder="如 E1002" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="createForm.name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="createForm.departmentId" placeholder="如 D_IT" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="createForm.roleCode" placeholder="选择角色" style="width: 100%">
            <el-option label="员工" value="EMPLOYEE" />
            <el-option label="工程师" value="ENGINEER" />
            <el-option label="平台管理员" value="PLATFORM_ADMIN" />
            <el-option label="知识库管理员" value="KB_ADMIN" />
          </el-select>
        </el-form-item>
        <el-form-item label="初始密码" required>
          <el-input v-model="createForm.password" type="password" show-password placeholder="6-32位，含字母和数字" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="resetVisible" :title="`重置密码 · ${resetTarget?.name || ''}`" width="min(400px, calc(100vw - 32px))" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="新密码" required>
          <el-input v-model="resetPwd" type="password" show-password placeholder="6-32位，含字母和数字" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="doReset">确认重置</el-button>
      </template>
    </el-dialog>

    <!-- 修改角色弹窗 -->
    <el-dialog v-model="roleVisible" :title="`修改角色 · ${roleTarget?.name || ''}`" width="min(440px, calc(100vw - 32px))" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="当前角色">
          <el-tag>{{ roleLabel(roleTarget?.role) }}</el-tag>
        </el-form-item>
        <el-form-item label="新角色" required>
          <el-select v-model="roleForm.roleCode" placeholder="选择新角色" style="width: 100%">
            <el-option label="员工 EMPLOYEE" value="EMPLOYEE" />
            <el-option label="工程师 ENGINEER" value="ENGINEER" />
            <el-option label="平台管理员 PLATFORM_ADMIN" value="PLATFORM_ADMIN" />
            <el-option label="知识库管理员 KB_ADMIN" value="KB_ADMIN" />
          </el-select>
        </el-form-item>
        <el-form-item label="修改原因">
          <el-input v-model="roleForm.reason" type="textarea" :rows="2" placeholder="选填，审计追溯用" />
        </el-form-item>
        <el-alert type="warning" :closable="false" show-icon
          title="角色变更在用户下次登录后生效；若降级最后一个平台管理员将被拒绝" />
      </el-form>
      <template #footer>
        <el-button @click="roleVisible = false">取消</el-button>
        <el-button type="warning" :loading="roleSaving" @click="doChangeRole">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { userApi } from '../api/index.js'

const roleMap = { EMPLOYEE: '员工', ENGINEER: '工程师', PLATFORM_ADMIN: '平台管理员', KB_ADMIN: '知识库管理员', KNOWLEDGE_ADMIN: '知识库管理员' }
const roleTagType = (r) => ({ EMPLOYEE: 'success', ENGINEER: 'primary', PLATFORM_ADMIN: 'warning', KB_ADMIN: 'danger', KNOWLEDGE_ADMIN: 'danger' }[r] || 'info')

const accounts = ref([])
const loading = ref(false)
const loadError = ref('')

const createVisible = ref(false)
const creating = ref(false)
const createForm = ref({ userId: '', employeeNo: '', name: '', departmentId: '', roleCode: '', password: '' })

const resetVisible = ref(false)
const resetting = ref(false)
const resetTarget = ref(null)
const resetPwd = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await userApi.listAccounts()
    accounts.value = res.data
  } catch (e) {
    loadError.value = e.message || '账号加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.value = { userId: '', employeeNo: '', name: '', departmentId: '', roleCode: '', password: '' }
  createVisible.value = true
}

async function doCreate() {
  const f = createForm.value
  if (!f.userId || !f.employeeNo || !f.name || !f.roleCode || !f.password) {
    ElMessage.warning('请填写完整的账号信息')
    return
  }
  creating.value = true
  try {
    await userApi.createAccount(f)
    ElMessage.success('账号创建成功')
    createVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

function openReset(row) {
  resetTarget.value = row
  resetPwd.value = ''
  resetVisible.value = true
}

async function doReset() {
  if (!resetPwd.value) {
    ElMessage.warning('请输入新密码')
    return
  }
  resetting.value = true
  try {
    await userApi.resetPassword(resetTarget.value.user_id, { newPassword: resetPwd.value })
    ElMessage.success('密码已重置')
    resetVisible.value = false
  } catch (e) {
    ElMessage.error(e.message || '重置失败')
  } finally {
    resetting.value = false
  }
}

// ---------- 修改角色 ----------
const roleVisible = ref(false)
const roleSaving = ref(false)
const roleTarget = ref(null)
const roleForm = ref({ roleCode: '', reason: '' })

function openRole(row) {
  roleTarget.value = row
  roleForm.value = { roleCode: row.role, reason: '' }
  roleVisible.value = true
}

async function doChangeRole() {
  if (!roleForm.value.roleCode) {
    ElMessage.warning('请选择新角色')
    return
  }
  roleSaving.value = true
  try {
    await userApi.changeRole(roleTarget.value.user_id, roleForm.value)
    ElMessage.success('角色已修改，用户下次登录生效')
    roleVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(e.message || '修改失败')
  } finally {
    roleSaving.value = false
  }
}

const roleLabel = (r) => roleMap[r] || r || '-'

onMounted(load)
</script>

<style scoped>
.account-page { min-width:0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: 600; font-size: 16px; }

.page-head { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:24px; }
.page-eyebrow { display:block; color:var(--el-color-primary); font-size:12px; font-weight:700; letter-spacing:1.4px; margin-bottom:8px; }
.page-title { margin:0; font-size:28px; line-height:1.3; color:var(--el-text-color-primary); }
.page-sub { margin:8px 0 0; font-size:14px; line-height:1.6; color:var(--el-text-color-secondary); }
.section-title { font-size:18px; font-weight:650; color:var(--el-text-color-primary); }
.scope-note { margin:8px 0 16px; font-size:13px; color:var(--el-text-color-secondary); line-height:1.6; }
.page-error { margin-bottom:16px; }
:deep(.el-card) { border-radius:16px; }
:deep(.el-table .cell) { line-height:1.6; }
:deep(.el-dialog) { max-width:calc(100vw - 32px); border-radius:16px; }
:deep(.el-form-item__label) { color:var(--el-text-color-regular); }
@media(max-width:767px) {
  .page-head { flex-wrap:wrap; margin-bottom:20px; }
  .page-title { font-size:24px; }
  :deep(.el-card__body) { padding:16px; }
  :deep(.el-dialog) { margin-top:5vh; }
  :deep(.el-pagination) { flex-wrap:wrap; gap:8px; justify-content:center; }
}

.heading-actions { display:flex; flex-wrap:wrap; gap:8px; }
.heading-actions :deep(.el-button + .el-button) { margin-left:0; }
.card-header { gap:12px; flex-wrap:wrap; }
.card-header .scope-note { margin:0; }
</style>
