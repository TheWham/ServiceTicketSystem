<template>
  <div class="engineer-view">
    <header class="page-head">
      <div><p class="eyebrow">服务交付</p><h1 class="page-title">工程师工作台</h1><p class="page-sub">我负责的工单与待领取工单 · 每 15 秒自动刷新</p></div>
      <div class="head-actions"><el-badge :value="consultCount" :hidden="!consultCount" :max="99"><el-button type="primary" :icon="ChatDotRound" @click="consultVisible = true">当前咨询</el-button></el-badge>
        <el-button :icon="Refresh" :loading="loading" @click="loadTickets">刷新</el-button></div>
    </header>
    <el-tabs v-model="activeStatus" class="status-tabs" aria-label="按工单状态筛选" @tab-change="changeStatus">
      <el-tab-pane label="全部工单" name="" /><el-tab-pane v-for="s in statuses" :key="s" :label="statusLabel(s)" :name="s" />
    </el-tabs>
    <section aria-label="工程师工单列表">
      <div class="list-toolbar"><div class="search-field"><label for="engineer-ticket-search">搜索本页工单</label><el-input id="engineer-ticket-search" v-model="keyword" placeholder="搜索工单号 / 标题 / 提单人" :prefix-icon="Search" clearable /></div><p class="list-caption">共 {{ loading || listError ? '—' : total }} 项 · 第 {{ page }} 页<br>搜索仅匹配当前页已加载的工单</p></div>
      <div v-if="loading" class="state-panel" role="status">正在加载工单…</div>
      <div v-else-if="listError" class="state-panel" role="alert"><h2>工单暂时无法加载</h2><p>{{ listError }}</p><el-button @click="loadTickets">重试</el-button></div>
      <div v-else-if="!allTickets.length" class="state-panel"><h2>当前状态下暂无工单</h2><p>新的分配或待领取工单将在这里显示。</p></div>
      <div v-else-if="!filteredTickets.length" class="state-panel"><h2>本页没有匹配的工单</h2><el-button @click="keyword = ''">清除搜索</el-button></div>
      <ul v-else class="ticket-list">
        <li v-for="t in filteredTickets" :key="t.ticket_id" class="ticket-row" :class="{ 'is-selected': selectedTicketId === t.ticket_id }">
          <button class="ticket-open" :aria-pressed="selectedTicketId === t.ticket_id" :aria-label="'查看工单 ' + t.ticket_id + ' ' + t.title" @click="openDetail(t)">
            <span class="ticket-id">{{ t.ticket_id }}</span><span class="ticket-title">{{ t.title }}</span>
            <span class="ticket-meta"><span>{{ t.category_name }}</span><span>提单人：{{ t.creator_name }}</span><time>{{ formatTime(t.created_at) }}</time></span>
          </button>
          <div class="ticket-signals"><el-tag :type="statusTagType(t.status)" size="small">{{ statusLabel(t.status) }}</el-tag><el-tag :type="priorityTagType(t.priority)" size="small" effect="plain">{{ priorityLabel(t.priority) }}优先级</el-tag><SlaBadge :ticket-id="t.ticket_id" mode="card" /></div>
          <el-button v-if="t.status === 'ASSIGNED'" type="primary" plain :icon="Pointer" @click="openClaimDialog(t)">接单</el-button>
          <el-button v-else text :aria-label="'查看工单 ' + t.ticket_id" @click="openDetail(t)">查看 →</el-button>
        </li>
      </ul>
      <el-pagination v-if="total > pageSize" v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" class="pagination" @current-change="loadTickets" />
    </section>

    <!-- 工单详情抽屉；选择状态由路由统一管理。 -->
    <el-drawer :model-value="detailVisible" :before-close="closeDetail" :title="'工单详情 · ' + selectedTicketId" size="min(760px, 100vw)" class="ticket-drawer" destroy-on-close>
      <template #header>
        <div class="drawer-heading"><el-button text @click="closeDetail">← 返回列表</el-button><span>工单详情 · {{ selectedTicketId }}</span></div>
      </template>
      <div v-if="detailLoading" class="state-panel" role="status">正在加载工单详情…</div>
      <div v-else-if="detailError" class="state-panel" role="alert"><p>{{ detailError }}</p><el-button @click="loadDetail()">重试详情</el-button></div>
      <template v-if="detail">
        <el-descriptions :column="2" border class="detail-desc">
          <el-descriptions-item label="标题" :span="2">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ detail.category_name }}</el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="priorityTagType(detail.priority)" size="small">{{ priorityLabel(detail.priority) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提单人">{{ detail.creator_name }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.location" label="位置">{{ detail.location }}</el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ formatTime(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="问题描述" :span="2">{{ detail.description }}</el-descriptions-item>
          <el-descriptions-item label="影响情况" :span="2">{{ detail.impact_description }}</el-descriptions-item>
          <el-descriptions-item label="紧急说明" :span="2">{{ detail.urgency_description }}</el-descriptions-item>
        </el-descriptions>

        <!-- SLA 计时 -->
        <SlaTimer :ticket-id="detail.ticket_id" />

        <!-- 状态操作 -->
        <section class="action-card">
          <h3 class="action-title">工单操作</h3>

          <!-- 已分配（待接单）→ 接单 -->
          <div v-if="detail.status === 'ASSIGNED'" class="action-row">
            <el-button type="success" :icon="Pointer" @click="openClaimDialog(detail)">接单</el-button>
            <el-text type="info" size="small">接单需确认影响范围与紧急程度（确定优先级）</el-text>
          </div>

          <!-- 处理中 → 记录进展 -->
          <div v-if="detail.status === 'IN_PROGRESS'" class="action-row">
            <el-input
              v-model="progressRemark"
              placeholder="请输入说明（记录进展 ≥5 字；转外部支持 ≥10 字）"
              class="remark-input"
              maxlength="200"
              show-word-limit
            />
            <el-button-group>
              <el-button type="primary" :loading="actionBusy" @click="doAction('progress')">记录进展</el-button>
              <el-button type="warning" :loading="actionBusy" @click="doAction('need_info')">申请补充</el-button>
              <el-button type="warning" :loading="actionBusy" @click="doAction('external')">需外部支持</el-button>
            </el-button-group>
          </div>

          <!-- 待补充 → 等待员工 -->
          <el-alert v-if="detail.status === 'PENDING_SUPPLEMENT'" type="info" :closable="false">
            <template #title>等待员工补充信息中...</template>
          </el-alert>

          <!-- 外部等待 → 外部解除 -->
          <div v-if="detail.status === 'PENDING_EXTERNAL'" class="action-row">
            <el-text type="info" size="small">等待外部支持中...</el-text>
            <el-button type="success" :icon="CircleCheck" :loading="actionBusy" @click="doAction('external_resolved')">
              外部已解除
            </el-button>
          </div>

          <!-- 处理中 → 提交方案 -->
          <div v-if="detail.status === 'IN_PROGRESS'" class="action-row submit-row">
            <el-button
              type="success"
              size="large"
              :disabled="!canDone"
              :icon="Promotion"
              :loading="actionBusy" @click="doAction('done')"
            >
              提交解决方案
            </el-button>
            <el-text v-if="!canDone" type="warning" size="small">
              请先记录至少一条处理进展
            </el-text>
          </div>

          <!-- 待验收 -->
          <el-alert v-if="detail.status === 'PENDING_ACCEPTANCE'" type="warning" :closable="false">
            <template #title>⏳ 已提交方案，等待员工验收（48h 未操作自动验收）...</template>
          </el-alert>

          <el-text v-if="actionError" type="danger" size="small" class="action-error">
            {{ actionError }}
          </el-text>
        </section>

        <!-- 流转日志 -->
        <section class="flow-card">
          <h3 class="action-title">流转记录</h3>
          <el-empty v-if="detailFlows.length === 0" description="暂无记录" :image-size="60" />
          <el-timeline v-else>
            <el-timeline-item
              v-for="f in detailFlows"
              :key="f.transition_id"
              :timestamp="formatTime(f.occurred_at)"
              :type="flowTimelineType(f.to_status)"
            >
              <div class="flow-content">
                <el-tag size="small" effect="plain">{{ statusLabel(f.to_status || f.from_status) }}</el-tag>
                <span class="flow-operator">{{ f.operator_name || operatorLabel(f.operator_id) }}</span>
                <span v-if="f.reason" class="flow-remark">{{ f.reason }}</span>
              </div>
            </el-timeline-item>
          </el-timeline>
        </section>
      </template>
    </el-drawer>

    <!-- ===== 接单确认（影响×紧急矩阵）弹窗 ===== -->
    <el-dialog
      v-model="claimDialogVisible"
      title="接单确认 · 优先级矩阵"
      width="min(520px, 94vw)"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-alert type="info" :closable="false" style="margin-bottom:16px">
        <template #title>接单需确认「影响范围 × 紧急程度」，系统按矩阵计算正式优先级</template>
      </el-alert>
      <el-form label-position="top">
        <el-form-item label="影响范围" required>
          <el-radio-group v-model="claimForm.impact_scope">
            <el-radio-button value="SINGLE">单人</el-radio-button>
            <el-radio-button value="DEPARTMENT">部门</el-radio-button>
            <el-radio-button value="CROSS_DEPT">跨部门</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="紧急程度" required>
          <el-radio-group v-model="claimForm.urgency_level">
            <el-radio-button value="LOW">低</el-radio-button>
            <el-radio-button value="MEDIUM">中</el-radio-button>
            <el-radio-button value="HIGH">高</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <div class="matrix-preview">
            计算优先级：
            <el-tag v-if="claimPriority" :type="priorityTagType(claimPriority)" size="large">
              {{ priorityLabel(claimPriority) }}
            </el-tag>
            <el-text v-else type="info">请选择影响范围与紧急程度</el-text>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="claimDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!claimPriority" :loading="claiming" @click="confirmClaim">
          确认接单
        </el-button>
      </template>
    </el-dialog>
    <EngineerConsultation :key="userStore.userId" v-model:visible="consultVisible" @count-change="consultCount = $event" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Refresh, Pointer, CircleCheck, Promotion, Search, ChatDotRound
} from '@element-plus/icons-vue'
import { ticketApi } from '../api/index.js'
import { useUserStore } from '../stores/user.js'
import SlaBadge from '../components/SlaBadge.vue'
import SlaTimer from '../components/SlaTimer.vue'
import EngineerConsultation from '../components/EngineerConsultation.vue'

const userStore = useUserStore()
const route = useRoute()
const allTickets = ref([])
const detail = ref(null)
const detailFlows = ref([])
const router = useRouter()
const selectedTicketId = computed(() => typeof route.query.ticket === 'string' ? route.query.ticket : '')
const detailVisible = computed(() => !!selectedTicketId.value)
const detailLoading = ref(false)
const detailError = ref('')
const loading = ref(true)
const listError = ref('')
let listRequest = 0
let detailRequest = 0
let disposed = false
let identityVersion = 0
const progressRemark = ref('')
const actionError = ref('')
const actionBusy = ref(false)
const consultVisible = ref(false)
const consultCount = ref(0)
let pollTimer = null

// 搜索关键词
const keyword = ref('')

const filteredTickets = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  if (!k) return allTickets.value
  return allTickets.value.filter(t =>
    (t.ticket_id || '').toLowerCase().includes(k) ||
    (t.title || '').toLowerCase().includes(k) ||
    (t.creator_name || '').toLowerCase().includes(k)
  )
})

const page = ref(1)
const total = ref(0)
const pageSize = 20
const activeStatus = ref('')
const statuses = ['ASSIGNED', 'IN_PROGRESS', 'PENDING_SUPPLEMENT', 'PENDING_EXTERNAL', 'PENDING_ACCEPTANCE', 'COMPLETED', 'CANCELLED', 'CLOSED']

// 状态/优先级映射（PRD §9.2 九态 + HIGH/MEDIUM/LOW）
const STATUS_LABEL = {
  NEW: '新建', ASSIGNED: '已分配', IN_PROGRESS: '处理中',
  PENDING_SUPPLEMENT: '待补充', PENDING_EXTERNAL: '外部等待',
  PENDING_ACCEPTANCE: '待验收', COMPLETED: '已完成',
  CANCELLED: '已取消', CLOSED: '已关闭'
}
const STATUS_TYPE = {
  NEW: 'warning', ASSIGNED: 'primary', IN_PROGRESS: 'primary',
  PENDING_SUPPLEMENT: 'info', PENDING_EXTERNAL: 'info',
  PENDING_ACCEPTANCE: 'primary', COMPLETED: 'success',
  CANCELLED: 'info', CLOSED: 'info'
}
function statusLabel(s) { return STATUS_LABEL[s] || s }
const PRIORITY_LABEL = { HIGH: '高', MEDIUM: '中', LOW: '低' }
const PRIORITY_TYPE = { HIGH: 'danger', MEDIUM: 'warning', LOW: 'info' }
function priorityLabel(p) { return PRIORITY_LABEL[p] || p }

const canDone = computed(() => {
  return detailFlows.value.some(f => f.reason && f.reason !== '提交工单' && f.operator_id === userStore.userId)
})

function statusTagType(s) { return STATUS_TYPE[s] || 'info' }

function priorityTagType(p) { return PRIORITY_TYPE[p] || 'info' }

function flowTimelineType(status) {
  const map = {
    COMPLETED: 'success', PENDING_ACCEPTANCE: 'primary', IN_PROGRESS: 'primary',
    NEW: 'warning', ASSIGNED: 'primary', CANCELLED: 'info', CLOSED: 'info'
  }
  return map[status] || 'primary'
}

function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '' }

// 操作人兜底：流转记录里 SYSTEM（系统自动路由）无用户档案，显示为「系统」
function operatorLabel(operatorId) { return operatorId === 'SYSTEM' ? '系统' : (operatorId || '—') }

async function loadTickets() {
  const request = ++listRequest
  loading.value = true
  listError.value = ''
  try {
    const params = { mine_or_pool: userStore.userId, page: page.value, page_size: pageSize }
    if (activeStatus.value) params.status = activeStatus.value
    const res = await ticketApi.list(params)
    if (disposed || request !== listRequest) return
    allTickets.value = res.data.list
    total.value = res.data.total
  } catch (e) {
    if (!disposed && request === listRequest) listError.value = e.message || '工单加载失败'
  } finally {
    if (!disposed && request === listRequest) loading.value = false
  }
}
function changeStatus() { page.value = 1; loadTickets() }

// 接单矩阵确认弹窗
const claimDialogVisible = ref(false)
const claiming = ref(false)
const claimTarget = ref(null)
const claimForm = ref({ impact_scope: '', urgency_level: '' })

// 影响×紧急矩阵 → 优先级（与后端 PriorityMatrix 一致，仅作预览）
const claimPriority = computed(() => {
  const s = claimForm.value.impact_scope, u = claimForm.value.urgency_level
  if (!s || !u) return ''
  const score = { SINGLE: 1, DEPARTMENT: 2, CROSS_DEPT: 3 }[s] + { LOW: 1, MEDIUM: 2, HIGH: 3 }[u]
  return score >= 5 ? 'HIGH' : score >= 4 ? 'MEDIUM' : 'LOW'
})

function openClaimDialog(t) {
  if (claiming.value) return
  claimTarget.value = t
  claimForm.value = { impact_scope: '', urgency_level: '' }
  claimDialogVisible.value = true
}

async function confirmClaim() {
  if (disposed || !claimTarget.value || claiming.value || !claimPriority.value) return
  const ticketId = claimTarget.value.ticket_id
  const userId = userStore.userId
  const identity = identityVersion
  const request = detailRequest
  claiming.value = true
  try {
    await ticketApi.claim(ticketId, {
      impact_scope: claimForm.value.impact_scope,
      urgency_level: claimForm.value.urgency_level
    })
    if (disposed || userId !== userStore.userId || identity !== identityVersion) return
    ElMessage.success(`接单成功，优先级：${priorityLabel(claimPriority.value)}`)
    claimDialogVisible.value = false
    await loadTickets()
    if (!disposed && identity === identityVersion && selectedTicketId.value === ticketId && request === detailRequest) {
      await loadDetail(ticketId)
    }
  } catch (e) {
    if (!disposed && identity === identityVersion) ElMessage.error('接单失败：' + e.message)
  } finally {
    if (!disposed && identity === identityVersion) claiming.value = false
  }
}

function openDetail(ticket) {
  if (selectedTicketId.value === ticket.ticket_id) return loadDetail(ticket.ticket_id)
  return router.push({ query: { ...route.query, ticket: ticket.ticket_id } })
}
function closeDetail() {
  if (!selectedTicketId.value) return
  const { ticket, ...query } = route.query
  return router.replace({ query })
}
async function loadDetail(id = selectedTicketId.value) {
  const request = ++detailRequest
  detail.value = null
  detailFlows.value = []
  detailError.value = ''
  detailLoading.value = !!id
  progressRemark.value = ''; actionError.value = ''
  if (!id) return
  try {
    const res = await ticketApi.detail(id)
    if (disposed || request !== detailRequest || selectedTicketId.value !== id) return
    detail.value = res.data.ticket
    detailFlows.value = res.data.flow_logs || []
  } catch (e) {
    if (!disposed && request === detailRequest) detailError.value = e.message || '详情加载失败'
  } finally {
    if (!disposed && request === detailRequest) detailLoading.value = false
  }
}
watch(selectedTicketId, id => loadDetail(id), { immediate: true, flush: 'sync' })

async function doAction(action) {
  if (disposed || actionBusy.value || !detail.value || selectedTicketId.value !== detail.value.ticket_id) return
  const ticketId = detail.value.ticket_id
  const userId = userStore.userId
  const identity = identityVersion
  const request = detailRequest
  actionError.value = ''
  const input = progressRemark.value.trim()

  const needRemark = { progress: 5, need_info: 5, external: 10 }
  if (needRemark[action]) {
    if (input.length < needRemark[action]) {
      actionError.value = action === 'external'
        ? `外部依赖说明至少 ${needRemark[action]} 个字符`
        : `说明至少 ${needRemark[action]} 个字符`
      return
    }
  }

  const remarkMap = {
    progress: input,
    need_info: input,
    external: input,
    external_resolved: '外部问题已解决',
    done: input || '已完成处理'
  }

  actionBusy.value = true
  try {
    await ticketApi.action(ticketId, { action, remark: remarkMap[action] })
    if (disposed || userId !== userStore.userId || identity !== identityVersion) return
    ElMessage.success('操作成功！')
    if (selectedTicketId.value === ticketId && request === detailRequest) await loadDetail(ticketId)
    loadTickets()
  } catch (e) {
    if (!disposed && selectedTicketId.value === ticketId && request === detailRequest) actionError.value = e.message
  } finally { if (!disposed && identity === identityVersion) actionBusy.value = false }
}



onMounted(() => {
  loadTickets()
  pollTimer = setInterval(() => { if (!loading.value) loadTickets() }, 15000)
})
onUnmounted(() => { disposed = true; ++listRequest; ++detailRequest; clearInterval(pollTimer) })

watch(() => userStore.userId, (id) => {
  ++identityVersion
  ++listRequest
  ++detailRequest
  claimDialogVisible.value = false
  claimTarget.value = null
  claiming.value = false
  actionBusy.value = false
  consultVisible.value = false
  consultCount.value = 0
  allTickets.value = []
  total.value = 0
  page.value = 1
  detail.value = null
  detailFlows.value = []
  closeDetail()
  progressRemark.value = ''
  actionError.value = ''
  if (id) loadTickets()
}, { flush: 'sync' })
</script>

<style scoped>

.page-head { display:flex; align-items:center; justify-content:space-between; gap:20px; margin-bottom:28px; }
.eyebrow { margin:0 0 8px; color:var(--el-color-primary); font-size:12px; font-weight:650; letter-spacing:.12em; }
.page-title { margin:0; font-size:clamp(25px, 2.6vw, 34px); font-weight:650; letter-spacing:-.035em; color:var(--el-text-color-primary); }
.page-sub { margin:10px 0 0; font-size:14px; line-height:1.6; color:var(--el-text-color-secondary); }
.head-actions { display:flex; align-items:center; gap:12px; }
.list-toolbar { display:flex; align-items:flex-end; gap:16px; padding:18px 0; }
.search-field { width:min(360px, 100%); }
.filter-field { width:180px; }
.list-toolbar label { display:block; margin-bottom:7px; font-size:12px; font-weight:600; color:var(--el-text-color-regular); }
.list-caption { color:var(--el-text-color-secondary); font-size:12px; line-height:1.7; margin:0 0 14px; }
.ticket-list { padding:0; margin:0; list-style:none; border-top:1px solid var(--el-border-color); }
.ticket-row { display:flex; align-items:center; gap:20px; padding:20px 12px; border-bottom:1px solid var(--el-border-color-lighter); transition:background .15s; }
.ticket-row:hover, .ticket-row:focus-within { background:var(--el-fill-color-light); }
.ticket-row.is-selected { background:var(--el-color-primary-light-9); box-shadow:inset 3px 0 var(--el-color-primary); }
.ticket-row:focus-visible, .ticket-open:focus-visible { outline:2px solid var(--el-color-primary); outline-offset:3px; border-radius:4px; }
.ticket-main, .ticket-open { flex:1; min-width:0; }
.ticket-open { display:block; border:0; padding:0; background:transparent; font:inherit; text-align:left; cursor:pointer; color:inherit; }
.ticket-id { color:var(--el-color-primary); font-family:ui-monospace,monospace; font-size:12px; font-weight:600; }
.ticket-title { display:block; margin:7px 0; font-size:15px; font-weight:600; line-height:1.5; overflow-wrap:anywhere; color:var(--el-text-color-primary); }
.ticket-meta { display:flex; gap:8px 18px; flex-wrap:wrap; color:var(--el-text-color-secondary); font-size:12px; line-height:1.6; }
.ticket-signals { display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-end; gap:8px; max-width:280px; }
.row-arrow { color:var(--el-color-primary); }
.state-panel { padding:54px 20px; text-align:center; border-block:1px solid var(--el-border-color-lighter); color:var(--el-text-color-secondary); font-size:14px; line-height:1.7; }
.state-panel h2 { margin:0 0 8px; font-size:18px; font-weight:600; color:var(--el-text-color-primary); }
.state-panel p { margin:8px 0 20px; overflow-wrap:anywhere; }
.pagination { padding-top:22px; justify-content:flex-end; overflow-x:auto; }
.status-tabs :deep(.el-tabs__item) { font-size:13px; }
.drawer-heading { display:flex; gap:12px; align-items:center; flex-wrap:wrap; font-size:13px; color:var(--el-text-color-secondary); }
.detail-desc { margin-bottom:22px; }
.detail-desc :deep(.el-descriptions__cell) { overflow-wrap:anywhere; white-space:pre-wrap; }
.action-card, .flow-card { margin-top:24px; padding-top:22px; border-top:1px solid var(--el-border-color); }
.action-title { margin:0 0 16px; color:var(--el-text-color-primary); font-size:16px; font-weight:600; }
.action-row { display:flex; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px; }
.remark-input { flex:1; min-width:200px; }
.submit-row { margin-top:20px; }
.action-error { display:block; margin-top:10px; }
.flow-content { display:flex; gap:10px; flex-wrap:wrap; align-items:center; font-size:13px; }
.flow-operator { color:var(--el-text-color-secondary); }
.flow-remark { overflow-wrap:anywhere; }
.create-section { max-width:960px; border-top:1px solid var(--el-border-color); padding-top:24px; }
.draft-alert { margin-bottom:18px; }
.ticket-form :deep(.el-form-item__label) { font-weight:600; }
.required { color:var(--el-color-danger); }
.char-count { margin-left:10px; font-size:12px; font-weight:400; color:var(--el-text-color-secondary); }
.reject-area { display:flex; gap:10px; }
@media (max-width:760px) {
  .page-head { align-items:flex-start; flex-wrap:wrap; margin-bottom:20px; gap:16px; }
  .head-actions { flex-wrap:wrap; }
  .list-toolbar { flex-wrap:wrap; gap:12px; }
  .search-field { width:100%; }
  .filter-field { flex:1; }
  .ticket-row { gap:12px; padding:16px 4px; flex-wrap:wrap; }
  .ticket-main, .ticket-open { flex-basis:100%; }
  .ticket-signals { justify-content:flex-start; max-width:none; flex:1; }
  .ticket-meta { gap:6px 12px; }
  .action-row :deep(.el-button-group) { display:flex; flex-wrap:wrap; gap:8px; }
  .reject-area { flex-wrap:wrap; }
  .drawer-heading { gap:6px; }
}
@media (prefers-reduced-motion:reduce) { .ticket-row { transition:none; } }

</style>
