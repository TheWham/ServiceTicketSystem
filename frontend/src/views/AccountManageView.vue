<template>
  <div class="account-page">
    <header class="page-head">
      <div><h1>账号管理</h1><p>管理成员身份、访问角色与登录凭据。</p></div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新建账号</el-button>
    </header>
    <section class="account-section" aria-label="账号列表">
      <div class="account-toolbar">
        <el-input v-model="search" clearable :prefix-icon="Search" placeholder="搜索姓名、账号、员工号或部门" aria-label="搜索账号" class="account-search" />
        <el-select v-model="roleFilter" clearable placeholder="全部角色" aria-label="按角色筛选" class="role-filter">
          <el-option v-for="(label, code) in roleMap" :key="code" :label="label" :value="code" />
        </el-select>
        <span v-if="!loading && !loadError" class="result-count" role="status">{{ filteredAccounts.length }} / {{ accounts.length }} 个账号</span>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </div>
      <div v-if="loadError" class="error-state" role="alert">
        <el-alert :title="loadError" type="error" :closable="false" show-icon />
        <el-button @click="load">重试加载</el-button>
      </div>
      <el-table :data="filteredAccounts" v-loading="loading" v-if="!loadError" row-key="user_id" :empty-text="loading ? '正在加载账号…' : (search || roleFilter ? '没有符合条件的账号，请调整搜索或角色' : '暂无账号，点击新建账号添加成员')">
        <el-table-column prop="user_id" label="用户ID" width="110" />
        <el-table-column prop="employee_no" label="员工号" width="100" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="department" label="部门" width="120">
          <template #default="{ row }">{{ row.department || row.department_id || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="140">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small" effect="plain">{{ roleMap[row.role] || row.role }}</el-tag>
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
    </section>

    <!-- 新建账号弹窗 -->
    <el-dialog v-model="createVisible" title="新建账号" width="min(460px, calc(100vw - 32px))" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="用户ID" required>
          <el-input v-model="createForm.user_id" placeholder="登录账号，如 U_EMP02" />
        </el-form-item>
        <el-form-item label="员工号" required>
          <el-input v-model="createForm.employee_no" placeholder="如 E1002" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="createForm.name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="createForm.department_id" placeholder="如 D_IT" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="createForm.role_code" placeholder="选择角色" style="width: 100%">
            <el-option label="员工" value="EMPLOYEE" />
            <el-option label="工程师" value="ENGINEER" />
            <el-option label="平台管理员" value="PLATFORM_ADMIN" />
            <el-option label="知识库管理员" value="KNOWLEDGE_ADMIN" />
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
      <el-form label-width="90px">
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
      <el-form label-width="90px">
        <el-form-item label="当前角色">
          <el-tag>{{ roleLabel(roleTarget?.role) }}</el-tag>
        </el-form-item>
        <el-form-item label="新角色" required>
          <el-select v-model="roleForm.role_code" placeholder="选择新角色" style="width: 100%">
            <el-option label="员工" value="EMPLOYEE" />
            <el-option label="工程师" value="ENGINEER" />
            <el-option label="平台管理员" value="PLATFORM_ADMIN" />
            <el-option label="知识库管理员" value="KNOWLEDGE_ADMIN" />
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { userApi } from '../api/index.js'

const roleMap = { EMPLOYEE: '员工', ENGINEER: '工程师', PLATFORM_ADMIN: '平台管理员', KNOWLEDGE_ADMIN: '知识库管理员' }
const roleTagType = (r) => ({ EMPLOYEE: 'success', ENGINEER: 'primary', PLATFORM_ADMIN: 'warning', KNOWLEDGE_ADMIN: 'danger' }[r] || 'info')

const accounts = ref([])
const loading = ref(false)
const loadError = ref('')
const search = ref('')
const roleFilter = ref('')
let loadRequest = 0
const filteredAccounts = computed(() => {
  const keyword = search.value.trim().toLocaleLowerCase()
  return accounts.value.filter(account => (!roleFilter.value || account.role === roleFilter.value) &&
    (!keyword || [account.user_id, account.employee_no, account.name, account.department, account.department_id]
      .some(value => String(value || '').toLocaleLowerCase().includes(keyword))))
})

const createVisible = ref(false)
const creating = ref(false)
const createForm = ref({ user_id: '', employee_no: '', name: '', department_id: '', role_code: '', password: '' })

const resetVisible = ref(false)
const resetting = ref(false)
const resetTarget = ref(null)
const resetPwd = ref('')

async function load() {
  const request = ++loadRequest
  loading.value = true
  loadError.value = ''
  accounts.value = []
  try {
    const res = await userApi.listAccounts()
    if (request !== loadRequest) return
    if (!Array.isArray(res?.data)) throw new Error('账号数据格式异常，请重试')
    accounts.value = res.data
  } catch (e) {
    if (request === loadRequest) loadError.value = e.message || '账号加载失败'
  } finally {
    if (request === loadRequest) loading.value = false
  }
}

function openCreate() {
  createForm.value = { user_id: '', employee_no: '', name: '', department_id: '', role_code: '', password: '' }
  createVisible.value = true
}

async function doCreate() {
  if (creating.value) return
  const f = createForm.value
  if (!f.user_id || !f.employee_no || !f.name || !f.role_code || !f.password) {
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
  if (resetting.value) return
  if (!resetPwd.value) {
    ElMessage.warning('请输入新密码')
    return
  }
  resetting.value = true
  try {
    await userApi.resetPassword(resetTarget.value.user_id, { new_password: resetPwd.value })
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
const roleForm = ref({ role_code: '', reason: '' })

function openRole(row) {
  roleTarget.value = row
  roleForm.value = { role_code: row.role, reason: '' }
  roleVisible.value = true
}

async function doChangeRole() {
  if (roleSaving.value) return
  if (!roleForm.value.role_code) {
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
onUnmounted(() => { ++loadRequest })
</script>

<style scoped>
.account-page { color: var(--el-text-color-primary); min-width: 0; }
.page-head, .account-toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.page-head { justify-content: space-between; margin-bottom: 24px; }
h1 { margin: 0; font-size: 24px; letter-spacing: -.6px; }
.page-head p { margin: 8px 0 0; color: var(--el-text-color-secondary); font-size: 14px; }
.account-section { border-top: 1px solid var(--el-border-color); }
.account-toolbar { padding: 18px 0; }
.account-search { width: min(380px, 100%); }
.role-filter { width: 170px; }
.result-count { margin-left: auto; color: var(--el-text-color-secondary); font-size: 13px; }
.error-state { display: flex; align-items: center; gap: 12px; padding: 16px 0; }
.account-page :deep(.el-table) { --el-table-header-bg-color: var(--el-fill-color-light); }
@media (max-width: 640px) {
  h1 { font-size: 21px; }
  .account-search { width: 100%; }
  .role-filter { flex: 1; }
  .result-count { margin-left: 0; }
  .error-state { flex-wrap: wrap; }
}
</style>
