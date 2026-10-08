<template>
  <div class="chat-attachment-uploader" @dragover.prevent @drop.prevent.stop="onDrop">
    <div class="attachment-toolbar">
      <button class="attachment-icon-button upload-button" type="button" aria-label="上传附件"
        title="上传附件" :disabled="disabled || !sessionId || drafts.length >= MAX_CHAT_ATTACHMENTS" @click="selectFiles">
        <el-icon aria-hidden="true"><Paperclip /></el-icon>
      </button>
      <span class="attachment-hint">附件 {{ drafts.length }}/10 · 每个不超过 20 MB</span>
      <input ref="fileInput" class="attachment-file-input" type="file" multiple tabindex="-1"
        aria-label="选择待发送附件" :disabled="disabled || !sessionId" @change="onFileChange" />
    </div>
    <p v-if="notice" class="attachment-notice" role="alert">{{ notice }}</p>
    <ul v-if="drafts.length" class="attachment-drafts" aria-label="待发送附件">
      <li v-for="item in drafts" :key="item.localId" class="attachment-draft" :class="{ 'has-error': item.status === 'error' }">
        <img v-if="item.preview_url && isSafeAttachmentImage(item)" :src="item.preview_url" class="attachment-thumb" alt="" />
        <span v-else class="attachment-file-icon"><el-icon aria-hidden="true"><Document /></el-icon></span>
        <div class="attachment-details">
          <span class="attachment-name" :title="item.file_name">{{ item.file_name }}</span>
          <span class="attachment-meta">{{ formatAttachmentSize(item.size) }} · {{ statusLabel(item) }}</span>
          <el-progress v-if="item.status === 'uploading'" :percentage="item.progress" :stroke-width="4"
            :show-text="false" :aria-label="`${item.file_name} 上传进度`" />
          <span v-if="item.status === 'error'" class="attachment-error" role="alert">{{ item.error }}</span>
        </div>
        <div class="attachment-actions">
          <button v-if="item.status === 'error'" class="attachment-icon-button" type="button"
            :aria-label="`重试上传 ${item.file_name}`" title="重试上传" :disabled="disabled" @click="retry(item.localId)">
            <el-icon aria-hidden="true"><RefreshRight /></el-icon>
          </button>
          <button class="attachment-icon-button" type="button" :aria-label="`移除附件 ${item.file_name}`"
            title="移除附件" :disabled="disabled" @click="remove(item.localId)">
            <el-icon aria-hidden="true"><Close /></el-icon>
          </button>
        </div>
      </li>
    </ul>
    <span class="attachment-sr-only" role="status" aria-live="polite">{{ uploadSummary }}</span>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, shallowRef, toRaw, watch } from 'vue'
import { Close, Document, Paperclip, RefreshRight } from '@element-plus/icons-vue'
import { consultationApi } from '../api/consultation.js'
import { createAttachmentUploader, formatAttachmentSize, isSafeAttachmentImage, MAX_CHAT_ATTACHMENTS } from '../utils/chatAttachments.js'

const props = defineProps({
  sessionId: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  modelValue: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])
const fileInput = ref(null)
const drafts = shallowRef([])
const notice = ref('')
const controller = createAttachmentUploader({
  sessionId: props.sessionId,
  api: consultationApi,
  disabled: () => props.disabled,
  onChange: value => { drafts.value = value; emit('update:modelValue', value) },
  onNotice: message => { notice.value = message },
})
watch(() => props.sessionId, value => { notice.value = ''; controller.setSession(value) }, { flush: 'sync' })
watch(() => props.modelValue, value => controller.syncModel(toRaw(value)), { immediate: true })
const isUploading = computed(() => drafts.value.some(item => item.status === 'uploading'))
const uploadSummary = computed(() => {
  const errors = drafts.value.filter(item => item.status === 'error').length
  return errors ? `${errors} 个附件上传失败，请重试或移除后发送。`
    : isUploading.value ? '附件上传中，请稍候。' : drafts.value.length ? `${drafts.value.length} 个附件待发送。` : ''
})
function statusLabel(item) {
  return item.status === 'uploading' ? `上传中 ${item.progress}%` : item.status === 'error' ? '上传失败' : '待发送'
}
function addFiles(files) {
  if (props.disabled) return Promise.resolve()
  notice.value = ''
  return controller.addFiles(files)
}
function clear() {
  notice.value = ''
  if (fileInput.value) fileInput.value.value = ''
  controller.clear()
}
function selectFiles() { if (!props.disabled) fileInput.value?.click() }
function onFileChange(event) {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  void addFiles(files)
}
function onDrop(event) { void addFiles(Array.from(event.dataTransfer?.files || [])) }
function retry(id) { notice.value = ''; return controller.retry(id) }
function remove(id) { return controller.remove(id) }
onBeforeUnmount(() => controller.dispose())
defineExpose({ addFiles, clear, isUploading })
</script>

<style scoped>
.chat-attachment-uploader { min-width: 0; color: var(--el-text-color-primary); }
.attachment-toolbar { display: flex; align-items: center; gap: 8px; }
.attachment-icon-button { display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; flex: 0 0 44px; padding: 0; border: 1px solid transparent; border-radius: 8px; color: var(--el-text-color-secondary); background: transparent; font-size: 18px; cursor: pointer; }
.attachment-icon-button:hover:not(:disabled) { color: var(--future-accent, var(--el-color-primary)); background: var(--el-fill-color-light); border-color: var(--el-border-color-light); }
.attachment-icon-button:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 2px; }
.attachment-icon-button:disabled { cursor: not-allowed; opacity: .5; }
.upload-button { color: var(--future-accent, var(--el-color-primary)); }
.attachment-hint, .attachment-meta { color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.5; }
.attachment-file-input { display: none; }
.attachment-drafts { list-style: none; margin: 4px 0 8px; padding: 2px; max-height: 160px; overflow-y: auto; overscroll-behavior: contain; scrollbar-gutter: stable; display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); gap: 8px; }
.attachment-draft { display: flex; align-items: center; gap: 8px; min-width: 0; padding: 8px; border: 1px solid var(--el-border-color-light); border-radius: 12px; background: var(--future-surface, var(--el-bg-color)); }
.attachment-draft.has-error { border-color: var(--el-color-danger); }
.attachment-thumb, .attachment-file-icon { width: 44px; height: 44px; flex: 0 0 44px; border-radius: 8px; object-fit: cover; background: var(--el-fill-color-light); }
.attachment-file-icon { display: grid; place-items: center; color: var(--future-accent, var(--el-color-primary)); font-size: 24px; }
.attachment-details { flex: 1; min-width: 0; display: grid; gap: 4px; }
.attachment-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; line-height: 1.5; }
.attachment-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 4px; max-width: 92px; }
.attachment-error, .attachment-notice { color: var(--el-color-danger); font-size: 12px; line-height: 1.5; overflow-wrap: anywhere; }
.attachment-notice { margin: 0 0 8px; }
.attachment-sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; border: 0; }
@media (max-width: 420px) { .attachment-actions { flex-direction: column; } }
</style>
