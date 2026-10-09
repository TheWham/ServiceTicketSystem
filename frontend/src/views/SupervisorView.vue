<template>
  <div class="supervisor-view">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <span class="page-eyebrow">SERVICE OPERATIONS</span><h1 class="page-title">工单管理</h1>
        <p class="page-sub">查看工单进度，分配处理工程师，跟进需要协调的问题</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadTickets">刷新工单</el-button>
    </div>

    <p class="scope-note">统计仅涵盖当前筛选下已加载的 {{ tickets.length }} 张工单；符合筛选的工单共 {{ total }} 张。</p>
    <div class="stat-row">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-icon" :class="s.tone">
          <el-icon :size="20"><component :is="s.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ s.count }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="filter-card">
      <el-form inline>
        <el-form-item label="状态">
          <el-select
            v-model="filter.status"
            placeholder="全部状态"
            clearable
            style="width: 140px"
            @change="applyFilters"
          >
            <el-option v-for="s in statuses" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select
            v-model="filter.category"
            placeholder="全部分类"
            clearable
            style="width: 140px"
            @change="applyFilters"
          >
            <el-option v-for="c in categories" :key="c.categoryId" :label="c.name" :value="c.categoryId" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理人">
          <el-select
            v-model="filter.assignee"
            placeholder="全部处理人"
            clearable
            style="width: 140px"
            @change="applyFilters"
          >
            <el-option v-for="e in engineers" :key="e.user_id" :label="e.name" :value="e.user_id" />
          </el-select>
        </el-form-item>
        <el-form-item class="filter-total">
          <el-text type="info">共 {{ total }} 张工单</el-text>
        </el-form-item>
      </el-form>
    </el-card>

    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false" class="page-error"><el-button link type="primary" @click="loadTickets">重新加载</el-button></el-alert>
    <!-- 工单列表 -->
    <el-card shadow="never">
      <template #header><span class="section-title">工单列表</span></template>
      <el-table
        v-loading="loading"
        :empty-text="loadError ? '工单加载失败，请重试' : '当前筛选下暂无工单'"
        :data="tickets"
        stripe
        highlight-current-row
        @row-click="openDetail"
        style="width: 100%"
      >
        <el-table-column prop="ticket_id" label="工单号" width="180">
          <template #default="{ row }">
            <el-button link type="primary" class="ticket-id" @click.stop="openDetail(row)">{{ row.ticket_id }}</el-button>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="priorityTagType(row.priority)" size="small" effect="plain">{{ priorityLabel(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category_name" label="分类" width="90" show-overflow-tooltip />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="creator_name" label="提单人" width="90" />
        <el-table-column label="处理人" width="90">
          <template #default="{ row }">{{ row.assignee_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="SLA" width="110">
          <template #default="{ row }">
            <SlaBadge :ticket-id="row.ticket_id" mode="card" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="['NEW','ASSIGNED','IN_PROGRESS','PENDING_EXTERNAL'].includes(row.status)"
              size="small"
              @click.stop="showReassign(row)"
            >改派</el-button>
            <el-button
              size="small"
              type="danger"
              plain
              @click.stop="deleteTicket(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        class="pagination"
        @current-change="loadTickets"
      />
    </el-card>

    <!-- ===== 派单/改派弹窗 ===== -->
    <el-dialog
      v-model="assignVisible"
      :title="assignTicket?.assignee_id ? '改派工单' : '派单'"
      width="min(480px, calc(100vw - 32px))"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template v-if="assignTicket">
        <el-alert :closable="false" class="assign-info">
          <template #title>
            <div class="assign-ticket-id">{{ assignTicket.ticket_id }}</div>
            <div class="assign-ticket-title">{{ assignTicket.title }}</div>
          </template>
        </el-alert>

        <el-form label-position="top">
          <el-form-item label="选择处理工程师" required>
            <el-select v-model="selectedEngineer" placeholder="-- 请选择 --" style="width: 100%">
              <el-option
                v-for="e in engineers"
                :key="e.user_id"
                :label="`${e.name} (${e.department})`"
                :value="e.user_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-if="assignTicket.assignee_id" label="改派原因">
            <el-input
              v-model="reassignReason"
              placeholder="请说明改派原因"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!selectedEngineer"
          :loading="assigning"
          @click="doAssign"
        >确认{{ assignTicket?.assignee_id ? '改派' : '派单' }}</el-button>
      </template>
    </el-dialog>

    <!-- ===== 工单详情弹窗 ===== -->
    <el-dialog
      v-model="detailVisible"
      :title="`工单详情 · ${detailTicket?.ticket_id || ''}`"
      width="min(720px, calc(100vw - 32px))"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template v-if="detailTicket">
        <el-descriptions :column="2" border class="detail-desc">
          <el-descriptions-item label="标题" :span="2">{{ detailTicket.title }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ detailTicket.category_name }}</el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="priorityTagType(detailTicket.priority)" size="small">{{ priorityLabel(detailTicket.priority) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(detailTicket.status)" size="small">{{ statusLabel(detailTicket.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提单人">{{ detailTicket.creator_name }}</el-descriptions-item>
          <el-descriptions-item label="处理人">{{ detailTicket.assignee_name || '未分配' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(detailTicket.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="问题描述" :span="2">{{ detailTicket.description }}</el-descriptions-item>
          <el-descriptions-item label="影响情况" :span="2">{{ detailTicket.impact_description }}</el-descriptions-item>
          <el-descriptions-item label="紧急说明" :span="2">{{ detailTicket.urgency_description }}</el-descriptions-item>
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

        <!-- 主管强制恢复 -->
        <el-card v-if="detailTicket.status === 'PENDING_EXTERNAL'" shadow="never" class="action-card">
          <template #header><span class="action-title">主管操作</span></template>
          <el-button type="warning" :icon="RefreshRight" @click="forceResolve(detailTicket)">
            强制恢复处理中
          </el-button>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DataAnalysis, Refresh, RefreshRight,
  Clock, Loading, CircleCheck, Finished, Document
} from '@element-plus/icons-vue'
import { ticketApi, userApi, categoryApi } from '../api/index.js'
import { loadPhotoUrls, revokePhotoUrls } from '../utils/attachmentPhotos.js'
import SlaBadge from '../components/SlaBadge.vue'

// 状态/优先级映射（PRD §9.2 九态 + HIGH/MEDIUM/LOW）
const STATUS_LABEL = {
  NEW: '新建', ASSIGNED: '已分配', IN_PROGRESS: '处理中',
  PENDING_SUPPLEMENT: '待补充', PENDING_EXTERNAL: '外部等待',
  PENDING_ACCEPTANCE: '待验收', COMPLETED: '已完成',
  CANCELLED: '已撤回', CLOSED: '已关闭'
}
const STATUS_TYPE = {
  NEW: 'warning', ASSIGNED: 'primary', IN_PROGRESS: 'primary',
  PENDING_SUPPLEMENT: 'info', PENDING_EXTERNAL: 'info',
  PENDING_ACCEPTANCE: 'primary', COMPLETED: 'success',
  CANCELLED: 'info', CLOSED: 'info'
}
const PRIORITY_LABEL = { HIGH: '高', MEDIUM: '中', LOW: '低' }
const PRIORITY_TYPE = { HIGH: 'danger', MEDIUM: 'warning', LOW: 'info' }
function statusLabel(s) { return STATUS_LABEL[s] || s }
function priorityLabel(p) { return PRIORITY_LABEL[p] || p }

const categories = ref([])
const statuses = Object.keys(STATUS_LABEL)

const loading = ref(false)
const loadError = ref('')
const assigning = ref(false)
const tickets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 15
const filter = ref({ status: '', category: '', assignee: '' })
const engineers = ref([])

// 统计
const stats = computed(() => {
  const counts = {}
  statuses.forEach(s => counts[s] = tickets.value.filter(t => t.status === s).length)
  return [
    { label: '处理中', count: (counts['ASSIGNED'] || 0) + (counts['IN_PROGRESS'] || 0), icon: Loading, tone: 'primary' },
    { label: '待验收', count: counts['PENDING_ACCEPTANCE'], icon: CircleCheck, tone: 'warning' },
    { label: '已完成', count: counts['COMPLETED'], icon: Finished, tone: 'success' },
    { label: '当前页工单', count: tickets.value.length, icon: Document, tone: 'neutral' }
  ]
})

// 派单
const assignTicket = ref(null)
const assignVisible = ref(false)
const selectedEngineer = ref('')
const reassignReason = ref('')

// 详情
const detailTicket = ref(null)
const detailFlows = ref([])
const detailPhotos = ref([])
const detailVisible = ref(false)

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

async function loadEngineers() {
  try {
    const res = await userApi.listUsers({ role: 'engineer' })
    engineers.value = res.data
  } catch (e) { console.error(e) }
}

function applyFilters() {
  page.value = 1
  loadTickets()
}

let ticketRequest = 0
async function loadTickets() {
  const request = ++ticketRequest
  loading.value = true
  loadError.value = ''
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filter.value.status) params.status = filter.value.status
    if (filter.value.category) params.category = filter.value.category
    if (filter.value.assignee) params.assignee_id = filter.value.assignee
    const res = await ticketApi.list(params)
    if (request !== ticketRequest) return
    tickets.value = res.data.list
    total.value = res.data.total
  } catch (e) {
    if (request === ticketRequest) loadError.value = e.message || '工单加载失败，请稍后重试'
  } finally {
    if (request === ticketRequest) loading.value = false
  }
}

// 删除工单（PLATFORM_ADMIN）：物理删除不可恢复，需二次确认
async function deleteTicket(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除工单 ${row.ticket_id}（${row.title}）吗？删除后不可恢复，流转记录与附件将一并清除。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  try {
    await ticketApi.remove(row.ticket_id)
    ElMessage.success('工单已删除')
    if (detailTicket.value?.ticket_id === row.ticket_id) detailVisible.value = false
    await loadTickets()
  } catch (e) { ElMessage.error(e.message || '删除失败') }
}
function showAssign(ticket) {
  assignTicket.value = { ...ticket }
  selectedEngineer.value = ''
  reassignReason.value = ''
  assignVisible.value = true
}
function showReassign(ticket) {
  assignTicket.value = { ...ticket }
  selectedEngineer.value = ''
  reassignReason.value = ''
  assignVisible.value = true
}

async function doAssign() {
  if (assigning.value) return
  assigning.value = true
  try {
    await ticketApi.assign(assignTicket.value.ticket_id, {
      assignee_id: selectedEngineer.value,
      reason: reassignReason.value || undefined
    })
    ElMessage.success('改派成功！')
    assignVisible.value = false
    loadTickets()
  } catch (e) { ElMessage.error(e.message) }
  finally { assigning.value = false }
}

async function openDetail(ticket) {
  try {
    const res = await ticketApi.detail(ticket.ticket_id)
    detailTicket.value = res.data.ticket
    detailFlows.value = res.data.flow_logs
    revokePhotoUrls(detailPhotos.value)
    detailPhotos.value = await loadPhotoUrls(res.data.ticket.attachments)
    detailVisible.value = true
  } catch (e) { ElMessage.error('加载详情失败：' + e.message) }
}

async function forceResolve(ticket) {
  try {
    await ElMessageBox.confirm('确认强制解除外部挂起状态？', '强制恢复', {
      confirmButtonText: '确认恢复',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch { return }

  try {
    await ticketApi.action(ticket.ticket_id, { action: 'external_resolved', remark: '主管强制恢复' })
    ElMessage.success('已恢复处理中')
    detailVisible.value = false
    loadTickets()
  } catch (e) { ElMessage.error(e.message) }
}

const route = useRoute()

onMounted(async () => {
  loadEngineers()
  try {
    const res = await categoryApi.leaf()
    categories.value = res.data || []
  } catch (e) { console.error('加载分类失败', e) }
  await loadTickets()
  // 通知跳转：URL 带 ?ticket=xxx 时自动打开该工单详情
  if (route.query.ticket) {
    openDetail({ ticket_id: route.query.ticket })
  }
})

// 同页点击通知只改 query，组件不重挂载——watch query 变化自动打开详情
watch(() => route.query.ticket, (tid) => {
  if (tid) openDetail({ ticket_id: tid })
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

/* 筛选 */
.filter-card { margin-bottom: 16px; }
.filter-card :deep(.el-form-item) { margin-bottom: 0; margin-right: 16px; }
.filter-total { margin-left: auto; }

/* 表格 */
.ticket-id {
  font-family: monospace;
  color: var(--el-color-primary);
  font-weight: 600;
  font-size: 13px;
}

.pagination { margin-top: 16px; justify-content: center; }

/* 弹窗 */
.assign-info { margin-bottom: 16px; }
.assign-ticket-id { font-family: monospace; color: var(--el-color-primary); font-weight: 600; }
.assign-ticket-title { margin-top: 4px; color: var(--el-text-color-regular); }

.detail-desc { margin-bottom: 16px; }

.action-card { margin-bottom: 16px; background: var(--el-fill-color-light); }
.action-title { font-weight: 600; }

.flow-card { background: var(--el-fill-color-light); }
.flow-content {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.flow-operator { font-size: 13px; color: var(--el-text-color-secondary); }
.flow-remark { font-size: 13px; color: var(--el-text-color-regular); }

.page-head { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:24px; }
.page-eyebrow { display:block; color:var(--el-color-primary); font-size:12px; font-weight:700; letter-spacing:1.4px; margin-bottom:8px; }
.page-title { margin:0; font-size:28px; line-height:1.3; color:var(--el-text-color-primary); }
.page-sub { margin:8px 0 0; font-size:14px; line-height:1.6; color:var(--el-text-color-secondary); }
.section-title { font-size:18px; font-weight:650; color:var(--el-text-color-primary); }
.scope-note { margin:8px 0 16px; font-size:13px; color:var(--el-text-color-secondary); line-height:1.6; }
.page-error { margin-bottom:16px; }
:deep(.el-card) { border-radius:16px; }
:deep(.el-table .cell) { line-height:1.6; }
:deep(.el-dialog) { max-width:calc(100vw - 32px); border-radius:16px; }
:deep(.el-form-item__label) { color:var(--el-text-color-regular); }
@media(max-width:767px) {
  .page-head { flex-wrap:wrap; margin-bottom:20px; }
  .page-title { font-size:24px; }
  :deep(.el-card__body) { padding:16px; }
  :deep(.el-dialog) { margin-top:5vh; }
  :deep(.el-pagination) { flex-wrap:wrap; gap:8px; justify-content:center; }
}

.stat-icon.primary { color:var(--el-color-primary); background:var(--el-color-primary-light-9); }
.stat-icon.warning { color:var(--el-color-warning); background:var(--el-color-warning-light-9); }
.stat-icon.success { color:var(--el-color-success); background:var(--el-color-success-light-9); }
.stat-icon.neutral { color:var(--el-text-color-secondary); background:var(--el-fill-color-light); }
.filter-card :deep(.el-form) { display:flex; flex-wrap:wrap; gap:16px; }
.filter-card :deep(.el-form-item) { margin:0; }
@media(max-width:767px) {
  .stat-row { grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
  .stat-card { padding:14px; gap:10px; }
  .stat-icon { width:36px; height:36px; }
  .filter-card :deep(.el-form-item) { width:100%; }
  .filter-card :deep(.el-form-item__content), .filter-card :deep(.el-select) { width:100% !important; }
  .filter-total { margin-left:0; }
}
</style>
