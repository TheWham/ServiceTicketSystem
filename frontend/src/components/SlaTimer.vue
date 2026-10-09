<template>
  <el-alert v-if="loadError" type="warning" :closable="false" :title="loadError"><el-button text @click="load" :loading="loading">重新加载服务时效</el-button></el-alert>
  <el-card v-else-if="sla" shadow="never" class="sla-card">
    <template #header>
      <div class="sla-header">
        <span class="sla-title">
          <el-icon><Timer /></el-icon> 服务时效
        </span>
        <el-tag :type="statusTagType" size="small" effect="dark">{{ statusLabel }}</el-tag>
      </div>
    </template>

    <div class="sla-body">
      <div class="sla-row">
        <span class="sla-label">处理优先级</span>
        <span class="sla-value">{{ priorityLabel }}</span>
      </div>
      <div class="sla-row">
        <span class="sla-label">目标时刻</span>
        <span class="sla-value">{{ formatDateTime(sla.target_at) }}</span>
      </div>
      <div class="sla-row">
        <span class="sla-label">已用工时</span>
        <span class="sla-value">{{ formatDuration(sla.elapsed_work_seconds) }}</span>
      </div>
      <div class="sla-row" v-if="sla.status === 'RUNNING'">
        <span class="sla-label">剩余工时</span>
        <span class="sla-value remaining" :class="{ near: isNear, breach: isBreached }">
          {{ formatDuration(remaining) }}
        </span>
      </div>
      <div class="sla-row" v-if="breachedAt">
        <span class="sla-label">违约时间</span>
        <span class="sla-value breach">{{ formatDateTime(breachedAt) }}</span>
      </div>

      <!-- 进度条 -->
      <div class="sla-progress">
        <el-progress
          :percentage="progressPct"
          :status="progressStatus"
          :stroke-width="10"
        />
        <div class="sla-progress-tip">{{ progressTip }}</div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Timer } from '@element-plus/icons-vue'
import { slaApi } from '../api/index.js'

const props = defineProps({
  ticketId: { type: String, required: true }
})

const sla = ref(null)
const remaining = ref(0)
const targetTotal = ref(0)
let timer = null
let refreshTimer = null
let requestVersion = 0
const loadError = ref('')
const loading = ref(false)

const statusLabel = computed(() => ({
  RUNNING: '计时中', PAUSED: '已暂停', MET: '已达标', CANCELLED: '已取消', BREACHED: '已违约'
}[sla.value?.status] || sla.value?.status || '—'))

const statusTagType = computed(() => ({
  RUNNING: 'primary', PAUSED: 'info', MET: 'success', CANCELLED: 'info', BREACHED: 'danger'
}[sla.value?.status] || 'info'))

const priorityLabel = computed(() => ({
  HIGH: '高（4工作小时）', MEDIUM: '中（1工作日）', LOW: '低（3工作日）'
}[sla.value?.priority_snapshot] || sla.value?.priority_snapshot || '—'))

const breachedAt = computed(() => sla.value && Object.hasOwn(sla.value, 'breach_at') ? sla.value.breach_at : sla.value?.breached_at)
const isBreached = computed(() => !!breachedAt.value || sla.value?.status === 'BREACHED')
const isNear = computed(() => sla.value?.status === 'RUNNING' && !isBreached.value && remaining.value < 3600)

const progressPct = computed(() => {
  if (!sla.value || targetTotal.value <= 0) return 0
  return Math.min(100, Math.round((sla.value.elapsed_work_seconds / targetTotal.value) * 100))
})

const progressStatus = computed(() => {
  if (isBreached.value) return 'exception'
  if (isNear.value) return 'warning'
  return ''
})

const progressTip = computed(() => {
  if (isBreached.value) return '已超出服务时效，记录已保留'
  if (sla.value?.status === 'PAUSED') return '计时已暂停（补充/外部等待期间不计入 SLA）'
  if (sla.value?.status === 'MET') return '已达到 SLA 完成目标'
  if (sla.value?.status === 'CANCELLED') return '工单已取消，停止计时'
  return `目标 ${formatDuration(targetTotal.value)} 工作时长`
})

async function load() {
  const version = ++requestVersion
  loading.value = true
  loadError.value = ''
  try {
    const res = await slaApi.byTicket(props.ticketId)
    if (version !== requestVersion) return
    sla.value = res.data
    if (sla.value) {
      remaining.value = sla.value.remaining_work_seconds || 0
      targetTotal.value = (sla.value.elapsed_work_seconds || 0) + remaining.value
    }
  } catch (e) {
    if (version === requestVersion) loadError.value = e.message || '服务时效加载失败'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

function formatDuration(sec) {
  if (sec == null) return '—'
  const s = Math.max(0, Number(sec))
  const d = Math.floor(s / 28800) // 1 工作日 = 8h
  const h = Math.floor((s % 28800) / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (d > 0) return `${d} 工作日 ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function formatDateTime(t) {
  if (!t) return '—'
  const d = new Date(t)
  return `${d.getMonth() + 1}-${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

watch(() => props.ticketId, () => { sla.value = null; load() })
onMounted(() => {
  load()
  refreshTimer = setInterval(load, 30000)
  timer = setInterval(() => {
    if (sla.value?.status === 'RUNNING' && remaining.value > 0) {
      remaining.value--
      if (sla.value.elapsed_work_seconds != null) sla.value.elapsed_work_seconds++
    }
  }, 1000)
})
onUnmounted(() => { requestVersion++; clearInterval(timer); clearInterval(refreshTimer) })

defineExpose({ load })
</script>

<style scoped>
.sla-card { margin-top: 12px; }
.sla-header { display: flex; justify-content: space-between; align-items: center; }
.sla-title { font-weight: 600; font-size: 14px; display: inline-flex; align-items: center; gap: 5px; }
.sla-body { padding-top: 4px; }
.sla-row {
  display: flex; justify-content: space-between; padding: 5px 0;
  font-size: 13px; border-bottom: 1px dashed var(--el-border-color-extra-light);
}
.sla-label { color: var(--el-text-color-secondary); }
.sla-value { color: var(--el-text-color-primary); font-variant-numeric: tabular-nums; }
.sla-value.remaining { font-weight: 600; color: var(--el-color-primary); }
.sla-value.remaining.near { color: var(--el-color-warning); }
.sla-value.remaining.breach, .sla-value.breach { color: var(--el-color-danger); font-weight: 600; }
.sla-progress { margin-top: 12px; }
.sla-progress-tip { font-size: 11px; color: var(--el-text-color-placeholder); margin-top: 4px; }
</style>
