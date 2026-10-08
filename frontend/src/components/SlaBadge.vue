<template>
  <span v-if="sla && showBadge" class="sla-badge" :class="badgeClass">
    <el-icon class="sla-icon"><Clock /></el-icon>{{ countdownText }}
  </span>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

// 仅计时中的工单显示徽章（PRD：SLA 只对工作时长计时，暂停/完成/违约不递减）
const showBadge = computed(() => sla.value && ['RUNNING', 'PAUSED'].includes(sla.value.status))

const badgeClass = computed(() => {
  if (!sla.value) return ''
  if (sla.value.status === 'PAUSED') return 'paused'
  if (sla.value.breach_at) return 'breached'
  // 剩余 < 20% 目标视为临近超时
  return remaining.value < 3600 ? 'near' : 'normal'
})

const countdownText = computed(() => {
  if (!sla.value) return ''
  if (sla.value.status === 'PAUSED') return '已暂停'
  if (sla.value.breach_at) return '已违约'
  const s = Math.max(0, remaining.value)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (h >= 24) return `剩 ${Math.floor(h / 24)} 工作日`
  if (h > 0) return `剩 ${h}h${m}m`
  return `剩 ${m}m`
})

async function load() {
  try {
    const res = await slaApi.byTicket(props.ticketId)
    sla.value = res.data
    if (sla.value) remaining.value = sla.value.remaining_work_seconds || 0
  } catch (e) {
    sla.value = null
  }
}

onMounted(() => {
  load()
  // 本地每秒递减（仅 RUNNING 状态）；每 30s 重新拉一次服务端基准，防漂移
  timer = setInterval(() => {
    if (sla.value?.status === 'RUNNING' && remaining.value > 0) remaining.value--
  }, 1000)
})
onUnmounted(() => clearInterval(timer))

defineExpose({ load })
</script>

<style scoped>
.sla-badge {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 12px; padding: 1px 7px; border-radius: 10px;
  font-variant-numeric: tabular-nums;
}
.sla-icon { font-size: 12px; }
.sla-badge.normal { background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.sla-badge.near { background: var(--el-color-warning-light-9); color: var(--el-color-warning); }
.sla-badge.paused { background: var(--el-fill-color); color: var(--el-text-color-secondary); }
.sla-badge.breached { background: var(--el-color-danger-light-9); color: var(--el-color-danger); font-weight: 600; }
</style>
