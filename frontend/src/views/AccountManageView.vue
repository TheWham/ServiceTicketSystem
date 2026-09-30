<template>
  <div class="account-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">账号管理</span>
          <el-button type="primary" :icon="Plus" @click="openCreate">新建账号</el-button>
        </div>
      </template>

      <el-table :data="accounts" v-loading="loading" border stripe>
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
    <el-dialog v-model="createVisible" title="新建账号" width="460px" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="90px">
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
    <el-dialog v-model="resetVisible" :title="`重置密码 · ${resetTarget?.name || ''}`" width="400px" :close-on-click-modal="false">
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
    <el-dialog v-model="roleVisible" :title="`修改角色 · ${roleTarget?.name || ''}`" width="440px" :close-on-click-modal="false">
      <el-form label-width="90px">
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
import { Plus } from '@element-plus/icons-vue'
import { userApi } from '../api/index.js'

const roleMap = { EMPLOYEE: '员工', ENGINEER: '工程师', PLATFORM_ADMIN: '平台管理员', KB_ADMIN: '知识库管理员' }
const roleTagType = (r) => ({ EMPLOYEE: 'success', ENGINEER: 'primary', PLATFORM_ADMIN: 'warning', KB_ADMIN: 'danger' }[r] || 'info')

const accounts = ref([])
const loading = ref(false)

const createVisible = ref(false)
const creating = ref(false)
const createForm = ref({ userId: '', employeeNo: '', name: '', departmentId: '', roleCode: '', password: '' })

const resetVisible = ref(false)
const resetting = ref(false)
const resetTarget = ref(null)
const resetPwd = ref('')

async function load() {
  loading.value = true
  try {
    const res = await userApi.listAccounts()
    accounts.value = res.data
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
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
.account-page { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: 600; font-size: 16px; }
</style>
