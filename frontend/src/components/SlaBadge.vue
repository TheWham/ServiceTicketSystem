<template>
  <button v-if="loadError" class="sla-retry" :title="loadError" @click.stop="load" :disabled="loading">时效加载失败 · 重试</button>
  <span v-else-if="sla && showBadge" class="sla-badge" :class="badgeClass">
    <el-icon class="sla-icon"><Clock /></el-icon>{{ countdownText }}
  </span>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Clock } from '@element-plus/icons-vue'
import { slaApi } from '../api/index.js'

const props = defineProps({
  ticketId: { type: String, required: true },
  // 卡片精简模式：只显示倒计时；详情模式显示更完整
  mode: { type: String, default: 'card' } // card | detail
})

const sla = ref(null)
const remaining = ref(0) // 剩余工作秒（服务端基准，本地递减）
let timer = null
let refreshTimer = null
let requestVersion = 0
const loadError = ref('')
const loading = ref(false)

// 仅计时中的工单显示徽章（PRD：SLA 只对工作时长计时，暂停/完成/违约不递减）
const breachedAt = computed(() => sla.value && Object.hasOwn(sla.value, 'breach_at') ? sla.value.breach_at : sla.value?.breached_at)
const isBreached = computed(() => !!breachedAt.value || sla.value?.status === 'BREACHED')
const showBadge = computed(() => sla.value && (isBreached.value || ['RUNNING', 'PAUSED'].includes(sla.value.status)))

const badgeClass = computed(() => {
  if (!sla.value) return ''
  if (isBreached.value) return 'breached'
  if (sla.value.status === 'PAUSED') return 'paused'
  // 剩余 < 20% 目标视为临近超时
  return remaining.value < 3600 ? 'near' : 'normal'
})

const countdownText = computed(() => {
  if (!sla.value) return ''
  if (isBreached.value) return '已违约'
  if (sla.value.status === 'PAUSED') return '已暂停'
  const s = Math.max(0, remaining.value)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (h >= 8) return `剩 ${Math.floor(h / 8)} 工作日`
  if (h > 0) return `剩 ${h}h${m}m`
  return `剩 ${m}m`
})

async function load() {
  const version = ++requestVersion
  loading.value = true
  loadError.value = ''
  try {
    const res = await slaApi.byTicket(props.ticketId)
    if (version !== requestVersion) return
    sla.value = res.data
    if (sla.value) remaining.value = sla.value.remaining_work_seconds || 0
  } catch (e) {
    if (version === requestVersion) loadError.value = e.message || '服务时效加载失败'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

watch(() => props.ticketId, () => { sla.value = null; load() })
onMounted(() => {
  load()
  refreshTimer = setInterval(load, 30000)
  // 本地每秒递减（仅 RUNNING 状态）；每 30s 重新拉一次服务端基准，防漂移
  timer = setInterval(() => {
    if (sla.value?.status === 'RUNNING' && remaining.value > 0) remaining.value--
  }, 1000)
})
onUnmounted(() => { requestVersion++; clearInterval(timer); clearInterval(refreshTimer) })

defineExpose({ load })
</script>

<style scoped>
.sla-retry { border: 0; background: transparent; color: var(--el-color-warning); font-size: 11px; cursor: pointer; padding: 0; }
.sla-badge {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 12px; padding: 1px 7px; border-radius: 10px;
  font-variant-numeric: tabular-nums;
}
.sla-icon { font-size: 12px; }
.sla-badge.normal { background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.sla-badge.near { background: var(--el-color-warning-light-9); color: var(--el-color-warning); }
.sla-badge.paused { background: var(--el-fill-color-light); color: var(--el-text-color-secondary); }
.sla-badge.breached { background: var(--el-color-danger-light-9); color: var(--el-color-danger); font-weight: 600; }
</style>
