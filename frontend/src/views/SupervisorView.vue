<template>
  <div class="supervisor-view">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">主管看板</h2>
        <p class="page-sub">全局工单管理 · 派单 · 催办 · 改派</p>
      </div>
      <el-button :icon="Refresh" circle @click="loadTickets" />
    </div>

    <!-- 统计卡片条（简洁商务） -->
    <div class="stat-row">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-icon" :style="{ background: s.bg, color: s.color }">
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
            @change="loadTickets"
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
            @change="loadTickets"
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
            @change="loadTickets"
          >
            <el-option v-for="e in engineers" :key="e.user_id" :label="e.name" :value="e.user_id" />
          </el-select>
        </el-form-item>
        <el-form-item class="filter-total">
          <el-text type="info">共 {{ total }} 张工单</el-text>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 工单列表 -->
    <el-card shadow="never">
      <el-table
        :data="tickets"
        stripe
        highlight-current-row
        @row-click="openDetail"
        style="width: 100%"
      >
        <el-table-column prop="ticket_id" label="工单号" width="180">
          <template #default="{ row }">
            <span class="ticket-id">{{ row.ticket_id }}</span>
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
      width="480px"
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
          @click="doAssign"
        >确认{{ assignTicket?.assignee_id ? '改派' : '派单' }}</el-button>
      </template>
    </el-dialog>

    <!-- ===== 工单详情弹窗 ===== -->
    <el-dialog
      v-model="detailVisible"
      :title="`工单详情 · ${detailTicket?.ticket_id || ''}`"
      width="720px"
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
  CANCELLED: '已取消', CLOSED: '已关闭'
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
    { label: '处理中', count: (counts['ASSIGNED'] || 0) + (counts['IN_PROGRESS'] || 0), icon: Loading, bg: '#ecf5ff', color: '#409eff' },
    { label: '待验收', count: counts['PENDING_ACCEPTANCE'], icon: CircleCheck, bg: '#e6f7f7', color: '#13a8a8' },
    { label: '已完成', count: counts['COMPLETED'], icon: Finished, bg: '#f0f9eb', color: '#67c23a' },
    { label: '全部工单', count: total.value, icon: Document, bg: '#f4f4f5', color: '#909399' }
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

async function loadTickets() {
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filter.value.status) params.status = filter.value.status
    if (filter.value.category) params.category = filter.value.category
    if (filter.value.assignee) params.assignee_id = filter.value.assignee
    const res = await ticketApi.list(params)
    tickets.value = res.data.list
    total.value = res.data.total
  } catch (e) { console.error(e) }
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
  try {
    await ticketApi.assign(assignTicket.value.ticket_id, {
      assignee_id: selectedEngineer.value,
      reason: reassignReason.value || undefined
    })
    ElMessage.success('改派成功！')
    assignVisible.value = false
    loadTickets()
  } catch (e) { ElMessage.error(e.message) }
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
  border-radius: 10px;
  transition: box-shadow .2s;
}
.stat-card:hover { box-shadow: 0 4px 16px rgba(31,45,61,.08); }
.stat-icon {
  width: 44px; height: 44px;
  border-radius: 10px;
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
</style>
