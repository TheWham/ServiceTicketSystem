<template>
  <el-dialog
    :model-value="modelValue"
    title="修改密码"
    width="min(440px, 94vw)"
    :close-on-click-modal="false"
    :close-on-press-escape="!loading"
    :show-close="!loading"
    @update:model-value="$emit('update:modelValue', $event)"
    @closed="resetForm"
  >
    <p class="password-help">设置 6–32 位新密码，包含字母和数字。</p>
    <el-form :model="form" label-position="top" @submit.prevent="submit">
      <el-form-item label="当前密码" required>
        <el-input v-model="form.oldPassword" type="password" autocomplete="current-password" :disabled="loading" show-password placeholder="请输入当前密码" />
      </el-form-item>
      <el-form-item label="新密码" required>
        <el-input v-model="form.newPassword" type="password" autocomplete="new-password" :disabled="loading" show-password placeholder="请输入新密码" />
      </el-form-item>
      <el-form-item label="确认新密码" required>
        <el-input v-model="form.confirm" type="password" autocomplete="new-password" :disabled="loading" show-password placeholder="再次输入新密码" />
      </el-form-item>
      <div class="password-actions">
        <el-button :disabled="loading" @click="close">取消</el-button>
        <el-button type="primary" native-type="submit" :loading="loading">确认修改</el-button>
      </div>
    </el-form>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { userApi } from '../api/index.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const form = ref({ oldPassword: '', newPassword: '', confirm: '' })

function close() {
  emit('update:modelValue', false)
  resetForm()
}

function resetForm() {
  form.value = { oldPassword: '', newPassword: '', confirm: '' }
}

async function submit() {
  if (loading.value) return
  const f = form.value
  if (!f.oldPassword || !f.newPassword || !f.confirm) {
    ElMessage.warning('请填写完整')
    return
  }
  if (f.newPassword !== f.confirm) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  loading.value = true
  try {
    await userApi.changePassword({ old_password: f.oldPassword, new_password: f.newPassword })
    ElMessage.success('密码修改成功')
    close()
  } catch (e) {
    ElMessage.error(e.message || '修改失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.password-help { margin: 0 0 20px; font-size: 13px; line-height: 1.7; color: var(--el-text-color-secondary); }
.password-actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 8px; }
</style>
