<template>
  <el-dialog
    :model-value="modelValue"
    title="修改密码"
    width="420px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-form :model="form" label-width="90px">
      <el-form-item label="旧密码" required>
        <el-input v-model="form.oldPassword" type="password" show-password placeholder="请输入当前密码" />
      </el-form-item>
      <el-form-item label="新密码" required>
        <el-input v-model="form.newPassword" type="password" show-password placeholder="6-32位，含字母和数字" />
      </el-form-item>
      <el-form-item label="确认新密码" required>
        <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入新密码" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">确认修改</el-button>
    </template>
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
  form.value = { oldPassword: '', newPassword: '', confirm: '' }
}

async function submit() {
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
    await userApi.changePassword({ oldPassword: f.oldPassword, newPassword: f.newPassword })
    ElMessage.success('密码修改成功')
    close()
  } catch (e) {
    ElMessage.error(e.message || '修改失败')
  } finally {
    loading.value = false
  }
}
</script>
