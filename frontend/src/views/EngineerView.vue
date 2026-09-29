<template>
  <div class="engineer-view">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">
          <el-icon><Tools /></el-icon> 工程师工作台
        </h2>
        <p class="page-sub">我负责的工单 + 待领取工单 · 看板视图（每 15 秒自动刷新）</p>
      </div>
      <el-button :icon="Refresh" circle @click="loadTickets" />
    </div>

    <!-- 看板 -->
    <div class="kanban">
      <div v-for="col in columns" :key="col.status" class="kanban-col">
        <div class="col-header" :class="col.color">
          <span class="col-label">{{ col.label }}</span>
          <el-badge :value="col.tickets.length" :type="col.badgeType" :max="99" />
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
            @click="openDetail(t)"
          >
            <div class="card-top">
              <span class="card-id">{{ t.ticket_id }}</span>
              <el-tag :type="priorityTagType(t.priority)" size="small" effect="plain">{{ priorityLabel(t.priority) }}</el-tag>
            </div>
            <div class="card-title">{{ t.title }}</div>
            <div class="card-meta">
              <el-tag size="small" type="info" effect="plain">{{ t.category_snapshot }}</el-tag>
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

    <!-- ===== 工单详情弹窗 ===== -->
    <el-dialog
      v-model="detailVisible"
      :title="`工单处理 · ${detail?.ticket_id || ''}`"
      width="720px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template v-if="detail">
        <el-descriptions :column="2" border class="detail-desc">
          <el-descriptions-item label="标题" :span="2">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ detail.category_snapshot }}</el-descriptions-item>
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
              placeholder="请输入说明（记录进展 ≥5 字；转外部支持 ≥10 字）"
              class="remark-input"
              maxlength="200"
              show-word-limit
            />
            <el-button-group>
              <el-button type="primary" @click="doAction('progress')">记录进展</el-button>
              <el-button type="warning" @click="doAction('need_info')">申请补充</el-button>
              <el-button type="warning" @click="doAction('external')">需外部支持</el-button>
            </el-button-group>
          </div>

          <!-- 待补充 → 等待员工 -->
          <el-alert v-if="detail.status === 'PENDING_SUPPLEMENT'" type="info" :closable="false">
            <template #title>等待员工补充信息中...</template>
          </el-alert>

          <!-- 外部等待 → 外部解除 -->
          <div v-if="detail.status === 'PENDING_EXTERNAL'" class="action-row">
            <el-text type="info" size="small">等待外部支持中...</el-text>
            <el-button type="success" :icon="CircleCheck" @click="doAction('external_resolved')">
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
            <template #title>⏳ 已提交方案，等待员工验收（48h 未操作自动验收）...</template>
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
              :key="f.log_id"
              :timestamp="formatTime(f.created_at)"
              :type="flowTimelineType(f.to_status)"
            >
              <div class="flow-content">
                <el-tag size="small" effect="plain">{{ statusLabel(f.to_status || f.from_status) }}</el-tag>
                <span class="flow-operator">{{ f.operator_name }}</span>
                <span class="flow-remark">{{ f.remark }}</span>
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
      width="520px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-alert type="info" :closable="false" style="margin-bottom:16px">
        <template #title>接单需确认「影响范围 × 紧急程度」，系统按矩阵计算正式优先级（PRD §11.4）</template>
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
import { ElMessage } from 'element-plus'
import {
  Tools, Refresh, Pointer, CircleCheck, Promotion
} from '@element-plus/icons-vue'
import { ticketApi } from '../api/index.js'
import { useUserStore } from '../stores/user.js'
import SlaBadge from '../components/SlaBadge.vue'
import SlaTimer from '../components/SlaTimer.vue'

const userStore = useUserStore()
const allTickets = ref([])
const detail = ref(null)
const detailFlows = ref([])
const detailVisible = ref(false)
const progressRemark = ref('')
const actionError = ref('')
let pollTimer = null

const columns = computed(() => {
  const statusMap = {
    'ASSIGNED':           { label: '已分配 / 待接单', color: 'yellow', badgeType: 'warning' },
    'IN_PROGRESS':        { label: '处理中', color: 'blue', badgeType: 'primary' },
    'PENDING_SUPPLEMENT': { label: '待补充', color: 'purple', badgeType: 'info' },
    'PENDING_EXTERNAL':   { label: '外部等待', color: 'orange', badgeType: 'warning' },
    'PENDING_ACCEPTANCE': { label: '待验收', color: 'cyan', badgeType: 'primary' },
    'COMPLETED':          { label: '已完成', color: 'green', badgeType: 'success' },
    'CANCELLED':          { label: '已取消', color: 'gray', badgeType: 'info' },
    'CLOSED':             { label: '已关闭', color: 'gray', badgeType: 'info' }
  }
  const result = Object.keys(statusMap).map(s => ({ status: s, ...statusMap[s], tickets: [] }))
  allTickets.value.forEach(t => {
    const col = result.find(c => c.status === t.status)
    if (col) col.tickets.push(t)
  })
  return result
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
  return detailFlows.value.some(f => f.remark && f.remark !== '提交工单' && f.operator_id === userStore.userId)
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

async function loadTickets() {
  try {
    const res = await ticketApi.list({ mine_or_pool: userStore.userId, page_size: 100 })
    allTickets.value = res.data.list
  } catch (e) { console.error(e) }
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
    progressRemark.value = ''
    actionError.value = ''
    detailVisible.value = true
  } catch (e) { ElMessage.error('加载详情失败：' + e.message) }
}

async function doAction(action) {
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
}

onMounted(() => {
  loadTickets()
  pollTimer = setInterval(loadTickets, 15000)
})
onUnmounted(() => clearInterval(pollTimer))

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
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-sub {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-top: 4px;
}

/* 看板 */
.kanban {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
}
.kanban-col {
  min-width: 240px;
  flex: 1;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
}
.col-header {
  font-weight: 700;
  font-size: 14px;
  padding: 8px 10px;
  border-radius: 6px;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
}
.col-header.yellow { background: #b88230; }
.col-header.blue   { background: #337ecc; }
.col-header.purple { background: #722ed1; }
.col-header.orange { background: #c4562d; }
.col-header.cyan   { background: #13a8a8; }
.col-header.green  { background: #529b2e; }
.col-header.gray   { background: #6b6b6b; }
.col-label { flex: 1; }
.col-body { flex: 1; min-height: 200px; max-height: calc(100vh - 220px); }

.kanban-card {
  margin-bottom: 8px;
  cursor: pointer;
  border-left: 3px solid var(--el-color-primary);
}
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
  font-size: 11px;
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
</style>
