<template>
  <div class="engineer-view">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <span class="page-eyebrow">ENGINEER WORKSPACE</span>
        <h1 class="page-title">{{ viewTitle }}</h1>
        <p class="page-sub">{{ viewDescription }}</p>
      </div>
      <div class="head-actions" v-if="activeView !== 'consultations'">
        <el-input
          v-model="keyword"
          placeholder="工单号、标题或提单人"
          aria-label="搜索已加载工单"
          :prefix-icon="Search"
          clearable
          class="head-search"
        />
        <el-button :icon="Refresh" :loading="ticketsLoading" aria-label="刷新工单" @click="loadTickets">刷新</el-button>
      </div>
    </div>

    <nav class="view-tabs" aria-label="工单视图">
      <router-link v-for="item in views" :key="item.key" :to="{ path: '/engineer', query: { view: item.key } }" :class="{ active: activeView === item.key }" :aria-current="activeView === item.key ? 'page' : undefined">{{ item.label }}</router-link>
    </nav>
    <template v-if="activeView !== 'consultations'">
    <p class="scope-note">统计范围：已加载的 {{ allTickets.length }} 条本人及待领取工单（最多 100 条） · 每 15 秒刷新</p>
    <!-- 统计卡片条 -->
    <div class="stat-row">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-icon" >
          <el-icon :size="20"><component :is="s.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <el-alert v-if="ticketsError" type="error" :closable="false" class="load-error" role="alert">
      <template #title>{{ ticketsError }}</template>
      <el-button size="small" @click="loadTickets">重试加载</el-button>
    </el-alert>
    <div v-if="ticketsLoading && !allTickets.length" class="loading-state" role="status"><el-skeleton :rows="5" animated /></div>
    <el-empty v-else-if="!ticketsError && !filteredTickets.length" :description="keyword ? '未找到匹配的工单，试试其他关键词' : '当前视图暂无工单'" :image-size="90" />
    <div v-else-if="allTickets.length" class="kanban" :aria-busy="ticketsLoading">
      <div v-for="col in columns" :key="col.status" class="kanban-col">
        <div class="col-header">
          <span class="col-dot"  :class="'dot-' + col.status.toLowerCase()"></span>
          <span class="col-label">{{ col.label }}</span>
          <span class="col-count">{{ col.tickets.length }}</span>
        </div>
        <el-scrollbar class="col-body">
          <el-empty
            v-if="col.tickets.length === 0"
            description="暂无"
            :image-size="48"
          />
          <el-card
            v-for="t in col.tickets"
            :key="t.ticket_id"
            shadow="hover"
            class="kanban-card"
            :class="{ high: t.priority === 'HIGH' }"
            tabindex="0"
            role="button"
            :aria-label="`查看工单 ${t.ticket_id}：${t.title}`"
            @click="openDetail(t)"
            @keydown.enter.self.prevent="openDetail(t)"
            @keydown.space.self.prevent="openDetail(t)"
          >
            <div class="card-top">
              <span class="card-id">{{ t.ticket_id }}</span>
              <el-tag :type="priorityTagType(t.priority)" size="small" effect="plain">{{ priorityLabel(t.priority) }}</el-tag>
            </div>
            <div class="card-title">{{ t.title }}</div>
            <div class="card-meta">
              <el-tag size="small" type="info" effect="plain">{{ t.category_name }}</el-tag>
              <span>{{ t.creator_name }}</span>
            </div>
            <div class="card-time">
              <span>{{ formatTime(t.created_at) }}</span>
              <SlaBadge :ticket-id="t.ticket_id" mode="card" />
            </div>
            <el-button
              v-if="t.status === 'ASSIGNED'"
              type="success"
              size="small"
              class="claim-btn"
              :icon="Pointer"
              @click.stop="openClaimDialog(t)"
            >接单</el-button>
          </el-card>
        </el-scrollbar>
      </div>
    </div>

    </template>
    <section v-else class="consultation-entry">
      <el-icon :size="36"><ChatDotRound /></el-icon>
      <h2>人工咨询工作区</h2>
      <p>查看员工与 AI 的对话上下文，回复咨询并提交解决结论。</p>
      <el-button type="primary" :icon="ChatDotRound" @click="consultationVisible = true">打开咨询工作区</el-button>
    </section>
    <EngineerConsultation v-model:visible="consultationVisible" />
    <!-- ===== 工单详情弹窗 ===== -->
    <el-dialog
      v-model="detailVisible"
      :title="`工单处理 · ${detail?.ticket_id || ''}`"
      width="min(720px, calc(100vw - 32px))"
      :close-on-click-modal="false"
      destroy-on-close
    >
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
          <el-descriptions-item v-if="detailPhotos.length" label="照片附件" :span="2">
            <el-image
              v-for="(u, i) in detailPhotos"
              :key="i"
              :src="u"
              :preview-src-list="detailPhotos"
              :initial-index="i"
              fit="cover"
              preview-teleported
              style="width:96px;height:96px;margin-right:8px;border-radius:4px"
            />
          </el-descriptions-item>
        </el-descriptions>

        <!-- SLA 计时 -->
        <SlaTimer :ticket-id="detail.ticket_id" />

        <!-- 状态操作 -->
        <el-card shadow="never" class="action-card">
          <template #header><span class="action-title">工单操作</span></template>

          <!-- 已分配（待接单）→ 接单 -->
          <div v-if="detail.status === 'ASSIGNED'" class="action-row">
            <el-button type="success" :icon="Pointer" @click="openClaimDialog(detail)">接单</el-button>
            <el-text type="info" size="small">接单需确认影响范围与紧急程度（确定优先级）</el-text>
          </div>

          <!-- 处理中 → 记录进展 -->
          <div v-if="detail.status === 'IN_PROGRESS'" class="action-row">
            <el-input
              v-model="progressRemark"
              placeholder="请输入说明（至少 5 字）"
              class="remark-input"
              maxlength="200"
              show-word-limit
            />
            <el-button-group>
              <el-button type="primary" :disabled="acting" @click="doAction('progress')">记录进展</el-button>
              <el-button type="warning" :disabled="acting" @click="doAction('need_info')">申请补充</el-button>
              <el-button type="warning" :disabled="acting" @click="doAction('external')">需外部支持</el-button>
            </el-button-group>
          </div>

          <!-- 待补充 → 等待员工 -->
          <el-alert v-if="detail.status === 'PENDING_SUPPLEMENT'" type="info" :closable="false">
            <template #title>等待员工补充信息中...</template>
          </el-alert>

          <!-- 外部等待 → 外部解除 -->
          <div v-if="detail.status === 'PENDING_EXTERNAL'" class="action-row">
            <el-text type="info" size="small">等待外部支持中...</el-text>
            <el-button type="success" :disabled="acting" :icon="CircleCheck" @click="doAction('external_resolved')">
              外部已解除
            </el-button>
          </div>

          <!-- 处理中 → 提交方案 -->
          <div v-if="detail.status === 'IN_PROGRESS'" class="action-row submit-row">
            <el-button
              type="success"
              size="large"
              :disabled="!canDone || acting"
              :icon="Promotion"
              @click="doAction('done')"
            >
              提交解决方案
            </el-button>
            <el-text v-if="!canDone" type="warning" size="small">
              请先记录至少一条处理进展
            </el-text>
          </div>

          <!-- 待验收 -->
          <el-alert v-if="detail.status === 'PENDING_ACCEPTANCE'" type="warning" :closable="false">
            <template #title>已提交方案，等待员工验收（48h 未操作自动验收）...</template>
          </el-alert>

          <el-text v-if="actionError" type="danger" size="small" class="action-error">
            {{ actionError }}
          </el-text>
        </el-card>

        <!-- 流转日志 -->
        <el-card shadow="never" class="flow-card">
          <template #header><span class="action-title">流转记录</span></template>
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
        </el-card>
      </template>
    </el-dialog>

    <!-- ===== 接单确认（影响×紧急矩阵）弹窗 ===== -->
    <el-dialog
      v-model="claimDialogVisible"
      title="接单确认 · 优先级矩阵"
      width="min(520px, calc(100vw - 32px))"
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Refresh, Pointer, CircleCheck, Promotion, Search, Loading, Tickets, ChatDotRound
} from '@element-plus/icons-vue'
import { ticketApi } from '../api/index.js'
import { loadPhotoUrls, revokePhotoUrls } from '../utils/attachmentPhotos.js'
import { useUserStore } from '../stores/user.js'
import EngineerConsultation from '../components/EngineerConsultation.vue'
import { engineerView, engineerStatuses, filterEngineerTickets } from '../utils/engineerViews.js'
import SlaBadge from '../components/SlaBadge.vue'
import SlaTimer from '../components/SlaTimer.vue'

const userStore = useUserStore()
const allTickets = ref([])
const detail = ref(null)
const detailFlows = ref([])
const detailPhotos = ref([])
const detailVisible = ref(false)
const progressRemark = ref('')
const actionError = ref('')
const acting = ref(false)
let pollTimer = null

// 搜索关键词
const keyword = ref('')

const route = useRoute()
const router = useRouter()
const activeView = computed(() => engineerView(route.query.view))
const views = [{ key: 'pool', label: '工单池' }, { key: 'tasks', label: '我的任务' }, { key: 'completed', label: '已完成' }, { key: 'consultations', label: '人工咨询' }]
const viewTitle = computed(() => views.find(v => v.key === activeView.value)?.label || '工程师工作台')
const viewDescription = computed(() => ({ pool: '确认影响与紧急程度，领取待处理工单', tasks: '跟进处理进度、补充材料与员工验收', completed: '检索已完成、已取消和已关闭的工单', consultations: '保留对话上下文，协助员工解决问题', all: '查看本人任务与待领取工单' }[activeView.value]))
const ticketsLoading = ref(false)
const ticketsError = ref('')
const consultationVisible = computed({ get: () => activeView.value === 'consultations', set: open => { if (!open && activeView.value === 'consultations') router.push({ path: '/engineer', query: { ...route.query, view: 'tasks' } }) } })
const filteredTickets = computed(() => filterEngineerTickets(allTickets.value, activeView.value, keyword.value))

const columns = computed(() => {
  const statusMap = {
    'ASSIGNED':           { label: '已分配 / 待接单', dotColor: '#e6a23c' },
    'IN_PROGRESS':        { label: '处理中', dotColor: '#409eff' },
    'PENDING_SUPPLEMENT': { label: '待补充', dotColor: '#909399' },
    'PENDING_EXTERNAL':   { label: '外部等待', dotColor: '#b88230' },
    'PENDING_ACCEPTANCE': { label: '待验收', dotColor: '#13a8a8' },
    'COMPLETED':          { label: '已完成', dotColor: '#67c23a' },
    'CANCELLED':          { label: '已取消', dotColor: '#c0c4cc' },
    'CLOSED':             { label: '已关闭', dotColor: '#c0c4cc' }
  }
  const result = engineerStatuses(activeView.value).map(s => ({ status: s, ...statusMap[s], tickets: [] }))
  filteredTickets.value.forEach(t => {
    const col = result.find(c => c.status === t.status)
    if (col) col.tickets.push(t)
  })
  return result
})

// 统计卡片（基于全部工单，不受搜索影响）
const stats = computed(() => {
  const t = allTickets.value
  const count = (s) => t.filter(x => x.status === s).length
  const active = t.filter(x => ['ASSIGNED','IN_PROGRESS','PENDING_SUPPLEMENT','PENDING_EXTERNAL','PENDING_ACCEPTANCE'].includes(x.status)).length
  return [
    { label: '待接单', value: count('ASSIGNED'), icon: Pointer },
    { label: '处理中', value: count('IN_PROGRESS'), icon: Loading },
    { label: '待验收', value: count('PENDING_ACCEPTANCE'), icon: CircleCheck },
    { label: '进行中合计', value: active, icon: Tickets }
  ]
})

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
  if (ticketsLoading.value) return
  ticketsLoading.value = true
  try {
    const res = await ticketApi.list({ mine_or_pool: userStore.userId, page_size: 100 })
    allTickets.value = res.data.list || []
    ticketsError.value = ''
  } catch (e) { ticketsError.value = '工单加载失败，请重试。' }
  finally { ticketsLoading.value = false }
}

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
  claimTarget.value = t
  claimForm.value = { impact_scope: '', urgency_level: '' }
  claimDialogVisible.value = true
}

async function confirmClaim() {
  if (!claimTarget.value) return
  claiming.value = true
  try {
    await ticketApi.claim(claimTarget.value.ticket_id, {
      impact_scope: claimForm.value.impact_scope,
      urgency_level: claimForm.value.urgency_level
    })
    ElMessage.success(`接单成功，优先级：${priorityLabel(claimPriority.value)}`)
    claimDialogVisible.value = false
    await loadTickets()
    if (detailVisible.value && detail.value?.ticket_id === claimTarget.value.ticket_id) {
      await openDetail({ ticket_id: claimTarget.value.ticket_id })
    }
  } catch (e) {
    ElMessage.error('接单失败：' + e.message)
  } finally {
    claiming.value = false
  }
}

async function openDetail(t) {
  try {
    const res = await ticketApi.detail(t.ticket_id)
    detail.value = res.data.ticket
    detailFlows.value = res.data.flow_logs
    revokePhotoUrls(detailPhotos.value)
    detailPhotos.value = await loadPhotoUrls(res.data.ticket.attachments)
    progressRemark.value = ''
    actionError.value = ''
    detailVisible.value = true
  } catch (e) { ElMessage.error('加载详情失败：' + e.message) }
}

async function doAction(action) {
  if (acting.value || !detail.value) return
  actionError.value = ''
  const input = progressRemark.value.trim()

  const needRemark = { progress: 5, need_info: 5, external: 5 }
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

  acting.value = true
  try {
    await ticketApi.action(detail.value.ticket_id, { action, remark: remarkMap[action] })
    await loadTickets()

    if (action === 'progress') {
      progressRemark.value = ''
      await openDetail({ ticket_id: detail.value.ticket_id })
    } else {
      ElMessage.success('操作成功！')
      detailVisible.value = false
    }
  } catch (e) { actionError.value = e.message }
  finally { acting.value = false }
}

onMounted(async () => {
  await loadTickets()
  // 通知跳转：URL 带 ?ticket=xxx 时自动打开该工单详情
  if (route.query.ticket) {
    openDetail({ ticket_id: route.query.ticket })
  }
  pollTimer = setInterval(loadTickets, 15000)
})
onUnmounted(() => { clearInterval(pollTimer); revokePhotoUrls(detailPhotos.value) })

// 同页点击通知只改 query，组件不重挂载——watch query 变化自动打开详情
watch(() => route.query.ticket, (tid) => {
  if (tid) openDetail({ ticket_id: tid })
})

watch(() => userStore.userId, (id) => {
  allTickets.value = []
  detail.value = null
  detailFlows.value = []
  detailVisible.value = false
  progressRemark.value = ''
  actionError.value = ''
  if (id) loadTickets()
})
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}
.page-sub {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-top: 4px;
}
.head-actions { display: flex; align-items: center; gap: 10px; }
.head-search { width: 240px; }

/* ===== 统计卡片条（简洁商务） ===== */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 16px;
  transition: box-shadow .2s;
}
.stat-card:hover { box-shadow: 0 4px 16px rgba(31,45,61,.08); }
.stat-icon {
  width: 44px; height: 44px;
  border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.stat-value { font-size: 24px; font-weight: 700; color: var(--el-text-color-primary); line-height: 1.1; }
.stat-label { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; }

/* ===== 看板（简洁商务） ===== */
.kanban {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr));
  gap: 16px;
  padding-bottom: 8px;
}
.kanban-col {
  min-width: 0;
  flex: 1;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-extra-light);
  border-radius: 16px;
  padding: 10px;
  display: flex;
  flex-direction: column;
}
.col-header {
  font-weight: 600;
  font-size: 13px;
  padding: 8px 10px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-primary);
}
.col-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.col-label { flex: 1; }
.col-count {
  min-width: 22px; height: 20px;
  padding: 0 6px;
  background: var(--el-fill-color-darker);
  border-radius: 16px;
  font-size: 12px; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
  color: var(--el-text-color-secondary);
}
.col-body { flex: 1; min-height: 200px; max-height: calc(100vh - 320px); }

.kanban-card {
  margin-bottom: 8px;
  cursor: pointer;
  border-left: 3px solid var(--el-color-primary);
  border-radius: 8px;
  transition: box-shadow .18s, transform .18s;
}
.kanban-card:hover { box-shadow: 0 4px 14px rgba(31,45,61,.12); transform: translateY(-1px); }
.kanban-card.high { border-left-color: var(--el-color-danger); }

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.card-id {
  font-family: monospace;
  font-size: 12px;
  color: var(--el-color-primary);
  font-weight: 600;
}
.card-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.card-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  display: flex;
  gap: 8px;
  align-items: center;
}
.card-time {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  margin-top: 6px;
}
.claim-btn { width: 100%; margin-top: 8px; }

/* 弹窗 */
.detail-desc { margin-bottom: 16px; }

.action-card { margin-bottom: 16px; background: var(--el-fill-color-light); }
.action-title { font-weight: 600; }
.action-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.remark-input { flex: 1; min-width: 200px; }
.submit-row {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--el-border-color);
}
.action-error { display: block; margin-top: 8px; }

.flow-card { background: var(--el-fill-color-light); }
.flow-content {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.flow-operator { font-size: 13px; color: var(--el-text-color-secondary); }
.flow-remark { font-size: 13px; color: var(--el-text-color-regular); }

.page-title { margin: 6px 0; }
.page-eyebrow { color: var(--el-color-primary); font-size: 12px; font-weight: 700; letter-spacing: .12em; }
.view-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
.view-tabs a { min-height: 44px; display: inline-flex; align-items: center; padding: 0 16px; border: 1px solid var(--el-border-color); border-radius: 10px; color: var(--el-text-color-regular); text-decoration: none; background: var(--el-bg-color); }
.view-tabs a.active { color: var(--el-color-primary); background: var(--el-color-primary-light-9); border-color: var(--el-color-primary); font-weight: 600; }
.scope-note { font-size: 12px; color: var(--el-text-color-secondary); margin: 0 0 12px; }
.stat-icon { color: var(--el-color-primary); background: var(--el-color-primary-light-9); }
.col-dot { background: var(--el-color-primary); }
.dot-assigned, .dot-pending_external { background: var(--el-color-warning); }
.dot-completed { background: var(--el-color-success); }
.load-error, .loading-state { margin-bottom: 20px; }
.consultation-entry { text-align: center; padding: 48px 24px; background: var(--el-bg-color); border: 1px solid var(--el-border-color); border-radius: 16px; color: var(--el-text-color-primary); }
.consultation-entry p { color: var(--el-text-color-secondary); line-height: 1.6; }
.consultation-entry > .el-icon { color: var(--el-color-primary); }
.kanban-card:focus-visible, .view-tabs a:focus-visible { outline: 3px solid var(--el-color-primary); outline-offset: 3px; }
@media (max-width: 900px) { .stat-row { grid-template-columns: repeat(2, minmax(0, 1fr)); } .page-head { align-items: flex-start; gap: 16px; flex-direction: column; } .head-actions { width: 100%; } .head-search { width: auto; flex: 1; } }
@media (max-width: 540px) { .page-title { font-size: 24px; } .stat-card { gap: 8px; padding: 12px; } .stat-icon { width: 32px; height: 36px; } .stat-value { font-size: 22px; } .card-meta { flex-wrap: wrap; } .col-body { max-height: none; } .remark-input { min-width: 0; flex-basis: 100%; } .action-row :deep(.el-button-group) { display: flex; flex-wrap: wrap; gap: 8px; } .detail-desc :deep(.el-descriptions__label) { word-break: keep-all; } }
@media (prefers-reduced-motion: reduce) { .kanban-card, .stat-card { transition: none; } .kanban-card:hover { transform: none; } }
</style>
