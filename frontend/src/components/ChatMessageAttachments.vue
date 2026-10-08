<template>
  <ul v-if="entries.length" class="chat-message-attachments" aria-label="消息附件">
    <li v-for="entry in entries" :key="entry.attachment.attachment_id" class="message-attachment">
      <div v-if="isSafeAttachmentImage(entry.attachment)" class="message-image-area">
        <button v-if="entry.status === 'ready' && !imageErrors[entry.attachment.attachment_id]" type="button"
          class="message-image-button" :aria-label="`预览图片 ${entry.attachment.file_name}`" @click="openPreview(entry)">
          <img :src="entry.url" :alt="entry.attachment.file_name" loading="lazy" class="message-image"
            @error="imageErrors[entry.attachment.attachment_id] = true" />
          <span class="message-image-caption">点击预览</span>
        </button>
        <span v-else class="message-image-placeholder" role="status">
          <el-icon aria-hidden="true"><Picture /></el-icon>
          {{ entry.status === 'loading' ? '图片加载中…' : '图片暂不可用' }}
        </span>
      </div>
      <div class="message-file-row">
        <el-icon class="message-file-icon" aria-hidden="true"><Document /></el-icon>
        <div class="message-file-info">
          <span class="message-file-name" :title="entry.attachment.file_name">{{ entry.attachment.file_name }}</span>
          <span class="message-file-size">{{ formatAttachmentSize(entry.attachment.size) }}</span>
        </div>
        <button type="button" class="message-attachment-button" :disabled="entry.status === 'loading' || downloading.has(entry.attachment.attachment_id)"
          :aria-label="`下载附件 ${entry.attachment.file_name}`" title="下载附件" @click="download(entry)">
          <el-icon aria-hidden="true"><Download /></el-icon>
        </button>
      </div>
      <div v-if="entry.status === 'error' || imageErrors[entry.attachment.attachment_id] || downloadErrors[entry.attachment.attachment_id]" class="message-attachment-error">
        <span role="alert">{{ entry.error || downloadErrors[entry.attachment.attachment_id] || '图片无法解码，请下载查看。' }}</span>
        <button v-if="entry.status === 'error' || imageErrors[entry.attachment.attachment_id]" type="button" class="message-attachment-button retry-button"
          :aria-label="`重试加载 ${entry.attachment.file_name}`" @click="retry(entry)">
          <el-icon aria-hidden="true"><RefreshRight /></el-icon><span>重试</span>
        </button>
      </div>
      <span v-else-if="entry.status === 'loading' && !isSafeAttachmentImage(entry.attachment)" class="message-load-status" role="status">正在准备下载…</span>
    </li>
    <el-image-viewer v-if="previewUrl" :url-list="[previewUrl]" teleported @close="previewUrl = ''" />
  </ul>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { Document, Download, Picture, RefreshRight } from '@element-plus/icons-vue'
import { consultationApi } from '../api/consultation.js'
import { createAttachmentBlobStore, downloadAttachmentUrl, formatAttachmentSize, isSafeAttachmentImage } from '../utils/chatAttachments.js'

const props = defineProps({
  sessionId: { type: String, default: '' },
  attachments: { type: Array, default: () => [] },
})
const emit = defineEmits(['preview-change'])
const entries = shallowRef([])
const previewUrl = ref('')
watch(previewUrl, value => emit('preview-change', Boolean(value)), { flush: 'sync' })
const imageErrors = ref({})
const downloadErrors = ref({})
const downloading = ref(new Set())
let mounted = false
let revision = 0
const store = createAttachmentBlobStore({
  api: consultationApi,
  onChange: value => { entries.value = value },
})
function sync() {
  revision++
  previewUrl.value = ''
  imageErrors.value = {}
  downloadErrors.value = {}
  downloading.value = new Set()
  store.sync(props.sessionId, props.attachments)
  if (mounted) entries.value.filter(entry => isSafeAttachmentImage(entry.attachment) && entry.status === 'idle')
    .forEach(entry => { void store.load(entry.attachment.attachment_id) })
}
watch(() => [props.sessionId, props.attachments], sync, { deep: true, flush: 'sync' })
onMounted(() => { mounted = true; sync() })
function openPreview(entry) { if (entry.url && isSafeAttachmentImage(entry.attachment)) previewUrl.value = entry.url }
function retry(entry) {
  const id = entry.attachment.attachment_id
  if (!isSafeAttachmentImage(entry.attachment)) return download(entry)
  previewUrl.value = ''
  delete imageErrors.value[id]
  return store.load(id, { reload: true })
}
async function download(entry) {
  const id = entry.attachment.attachment_id
  if (downloading.value.has(id)) return
  const currentRevision = revision
  downloading.value.add(id)
  delete downloadErrors.value[id]
  try {
    const loaded = await store.load(id)
    if (!loaded || currentRevision !== revision || !mounted) return
    downloadAttachmentUrl(loaded.url, loaded.attachment.file_name)
  } catch {
    if (currentRevision === revision && mounted) downloadErrors.value[id] = '下载未能开始，请重新点击下载。'
  } finally {
    if (currentRevision === revision) downloading.value.delete(id)
  }
}
onBeforeUnmount(() => {
  mounted = false
  revision++
  previewUrl.value = ''
  store.dispose()
})
</script>

<style scoped>
.chat-message-attachments { display: grid; gap: 8px; width: min(100%, 340px); min-width: 0; margin: 8px 0 0; padding: 0; list-style: none; color: var(--el-text-color-primary); }
.message-attachment { min-width: 0; overflow: hidden; border: 1px solid var(--el-border-color-light); border-radius: 12px; background: var(--future-surface, var(--el-bg-color)); }
.message-image-area { padding: 8px 8px 0; }
.message-image-button { display: block; position: relative; width: 100%; padding: 0; overflow: hidden; border: 0; border-radius: 8px; background: var(--el-fill-color-light); cursor: zoom-in; }
.message-image { display: block; width: 100%; height: 168px; object-fit: cover; }
.message-image-caption { display: block; padding: 4px 8px; font-size: 12px; line-height: 1.5; color: var(--el-text-color-secondary); background: var(--el-fill-color-light); }
.message-image-placeholder { display: flex; min-height: 120px; justify-content: center; align-items: center; gap: 8px; border-radius: 8px; background: var(--el-fill-color-light); color: var(--el-text-color-secondary); font-size: 12px; }
.message-file-row { display: flex; align-items: center; gap: 8px; padding: 8px; }
.message-file-icon { flex: 0 0 28px; width: 28px; font-size: 24px; color: var(--future-accent, var(--el-color-primary)); }
.message-file-info { display: grid; gap: 4px; min-width: 0; flex: 1; }
.message-file-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; line-height: 1.5; }
.message-file-size, .message-load-status { color: var(--el-text-color-secondary); font-size: 12px; }
.message-load-status { display: block; padding: 0 8px 8px; }
.message-attachment-button { display: inline-flex; gap: 4px; justify-content: center; align-items: center; min-width: 44px; min-height: 44px; flex-shrink: 0; padding: 0 8px; border: 1px solid transparent; border-radius: 8px; color: var(--future-accent, var(--el-color-primary)); background: transparent; font-size: 18px; cursor: pointer; }
.message-attachment-button:disabled { cursor: wait; opacity: .5; }
.message-attachment-button:hover:not(:disabled) { background: var(--el-fill-color-light); border-color: var(--el-border-color-light); }
.message-attachment-button:focus-visible, .message-image-button:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: -2px; }
.message-attachment-error { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 0 8px 8px; color: var(--el-color-danger); font-size: 12px; line-height: 1.5; overflow-wrap: anywhere; }
.retry-button { font-size: 12px; }
</style>
