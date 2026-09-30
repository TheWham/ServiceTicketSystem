<template>
  <div class="dispatch-view">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h1 class="page-title">工单调度</h1>
        <p class="page-sub">分配处理人，跟进工单进展。</p>
      </div>
      <el-button :icon="Refresh" :loading="listLoading" aria-label="刷新工单" circle @click="loadTickets" />
    </div>

    <div class="dispatch-summary" aria-label="当前列表摘要">
      <span>筛选结果 <strong>{{ listLoading || listError ? '—' : total }}</strong></span>
      <span v-for="s in stats" :key="s.label">{{ s.label }} <strong>{{ listLoading || listError ? '—' : s.count }}</strong></span>
    </div>

    <!-- 筛选栏 -->
    <section class="filter-card">
      <el-form inline>
        <el-form-item label="搜索本页">
          <el-input v-model="search" clearable placeholder="工单号、标题或人员" :prefix-icon="Search" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filter.status"
            placeholder="全部状态"
            clearable
            style="width: 140px"
            @change="resetFilters"
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
            @change="resetFilters"
          >
            <el-option v-for="c in categories" :key="c.category_id" :label="c.name" :value="c.category_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理人">
          <el-select
            v-model="filter.assignee"
            placeholder="全部处理人"
            clearable
            style="width: 140px"
            @change="resetFilters"
          >
            <el-option v-for="e in engineers" :key="e.user_id" :label="e.name" :value="e.user_id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!listLoading && !listError" class="filter-total">
          <el-text type="info">共 {{ total }} 张工单</el-text>
        </el-form-item>
      </el-form>
    </section>
    <div v-if="referenceError" class="error-state" role="alert">{{ referenceError }} <el-button @click="loadReferences">重试选项</el-button></div>

    <!-- 工单列表 -->
    <section class="ticket-list" :aria-busy="listLoading">
      <div v-if="listError" class="error-state" role="alert">{{ listError }} <el-button @click="loadTickets">重试</el-button></div>
      <el-table
        v-if="!listError"
        :data="filteredTickets"
        v-loading="listLoading"
        :empty-text="listLoading ? '正在加载工单…' : search.trim() ? '本页没有匹配的工单' : '暂无符合条件的工单'"
        row-key="ticket_id"
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
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="['NEW','ASSIGNED','IN_PROGRESS','PENDING_EXTERNAL'].includes(row.status)"
              size="small"
              @click.stop="showReassign(row)"
            >{{ row.assignee_id ? '改派' : '派单' }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="!listError && total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        class="pagination"
        @current-change="loadTickets"
      />
    </section>

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
          :loading="assignLoading"
          @click="doAssign"
        >确认{{ assignTicket?.assignee_id ? '改派' : '派单' }}</el-button>
      </template>
    </el-dialog>

    <!-- 工单详情 -->
    <el-drawer
      :model-value="detailVisible"
      @update:model-value="value => { if (!value) closeDetail() }"
      :title="`工单详情 · ${detailTicket?.ticket_id || ''}`"
      size="min(720px, 100vw)"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-if="detailLoading" role="status"><el-skeleton :rows="6" animated /></div>
      <div v-else-if="detailError" class="error-state" role="alert">{{ detailError }} <el-button @click="loadDetail(selectedTicketId)">重试</el-button></div>
      <template v-else-if="detailTicket">
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
        </el-descriptions>

        <!-- 平台管理员强制恢复 -->
        <el-card v-if="detailTicket.status === 'PENDING_EXTERNAL'" shadow="never" class="action-card">
          <template #header><span class="action-title">平台管理员操作</span></template>
          <el-button type="warning" :icon="RefreshRight" :loading="resolveLoading" @click="forceResolve(detailTicket)">
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
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, RefreshRight, Search } from '@element-plus/icons-vue'
import { ticketApi, userApi, categoryApi } from '../api/index.js'
import SlaBadge from '../components/SlaBadge.vue'

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


const route = useRoute()
const router = useRouter()
const categories = ref([])
const engineers = ref([])
const statuses = Object.keys(STATUS_LABEL)
const tickets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 15
const filter = ref({ status: '', category: '', assignee: '' })
const search = ref('')
const listLoading = ref(false)
const listError = ref('')
const referenceError = ref('')
let listRequest = 0
let referenceRequest = 0
let disposed = false
const filteredTickets = computed(() => {
  const keyword = search.value.trim().toLocaleLowerCase()
  return tickets.value.filter(t => !keyword || [t.ticket_id, t.title, t.creator_name, t.assignee_name]
    .some(value => String(value || '').toLocaleLowerCase().includes(keyword)))
})
const stats = computed(() => [
  { label: '本页待分配', count: tickets.value.filter(t => t.status === 'NEW').length },
  { label: '本页处理中', count: tickets.value.filter(t => ['ASSIGNED', 'IN_PROGRESS'].includes(t.status)).length },
  { label: '本页待验收', count: tickets.value.filter(t => t.status === 'PENDING_ACCEPTANCE').length }
])
const assignTicket = ref(null)
const assignVisible = ref(false)
const selectedEngineer = ref('')
const reassignReason = ref('')
const assignLoading = ref(false)
const resolveLoading = ref(false)
const detailTicket = ref(null)
const detailFlows = ref([])
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const selectedTicketId = ref('')
let detailRequest = 0
let detailPromise = Promise.resolve()

function statusTagType(s) { return STATUS_TYPE[s] || 'info' }
function priorityTagType(p) { return PRIORITY_TYPE[p] || 'info' }
function flowTimelineType(status) { return STATUS_TYPE[status] || 'primary' }
function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '' }
function operatorLabel(id) { return id === 'SYSTEM' ? '系统' : (id || '—') }

async function loadReferences() {
  const request = ++referenceRequest
  referenceError.value = ''
  const results = await Promise.allSettled([userApi.listUsers({ role: 'engineer' }), categoryApi.leaf()])
  if (request !== referenceRequest) return
  const errors = []
  for (const [index, result] of results.entries()) {
    const target = index === 0 ? engineers : categories
    if (result.status === 'fulfilled' && Array.isArray(result.value?.data)) {
      target.value = index === 0 ? result.value.data : result.value.data.filter(category => category.status === 'ACTIVE')
    }
    else {
      target.value = []
      errors.push(result.reason?.message || (index === 0 ? '工程师选项加载失败' : '分类选项加载失败'))
    }
  }
  referenceError.value = errors.join('；')
}

async function loadTickets() {
  const request = ++listRequest
  listLoading.value = true
  listError.value = ''
  tickets.value = []
  total.value = 0
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filter.value.status) params.status = filter.value.status
    if (filter.value.category) params.category = filter.value.category
    if (filter.value.assignee) params.assignee_id = filter.value.assignee
    const res = await ticketApi.list(params)
    if (request !== listRequest) return
    if (!Array.isArray(res?.data?.list) || !Number.isFinite(res.data.total)) throw new Error('工单列表数据异常')
    tickets.value = res.data.list
    total.value = res.data.total
  } catch (e) {
    if (request === listRequest) listError.value = e.message || '工单加载失败'
  } finally {
    if (request === listRequest) listLoading.value = false
  }
}
function resetFilters() {
  page.value = 1
  return loadTickets()
}
function showReassign(ticket) {
  if (assignLoading.value) return
  assignTicket.value = { ...ticket }
  selectedEngineer.value = ''
  reassignReason.value = ''
  assignVisible.value = true
}
async function doAssign() {
  if (assignLoading.value || !assignTicket.value || !selectedEngineer.value) return
  const id = assignTicket.value.ticket_id
  assignLoading.value = true
  try {
    await ticketApi.assign(id, { assignee_id: selectedEngineer.value, reason: reassignReason.value || undefined })
    if (disposed) return
    ElMessage.success('分配成功')
    assignVisible.value = false
    await loadTickets()
    if (detailVisible.value && selectedTicketId.value === id) await loadDetail(id)
  } catch (e) { if (!disposed) ElMessage.error(e.message || '分配失败') }
  finally { assignLoading.value = false }
}
async function openDetail(ticket) {
  const id = ticket.ticket_id
  if (!id || disposed) return
  const navigate = route.query.ticket ? router.replace : router.push
  await navigate({ query: { ...route.query, ticket: id } })
  if (!disposed && route.query.ticket === id) return detailPromise
}
async function loadDetail(id) {
  if (!id || disposed) return
  const request = ++detailRequest
  selectedTicketId.value = id
  detailVisible.value = true
  detailTicket.value = null
  detailFlows.value = []
  detailError.value = ''
  detailLoading.value = true
  try {
    const res = await ticketApi.detail(id)
    if (request !== detailRequest) return
    if (!res?.data?.ticket) throw new Error('工单详情数据异常')
    detailTicket.value = res.data.ticket
    detailFlows.value = res.data.flow_logs || []
  } catch (e) {
    if (request === detailRequest) detailError.value = e.message || '加载详情失败'
  } finally {
    if (request === detailRequest) detailLoading.value = false
  }
}
function resetDetail() {
  ++detailRequest
  selectedTicketId.value = ''
  detailVisible.value = false
  detailTicket.value = null
  detailFlows.value = []
  detailError.value = ''
  detailLoading.value = false
}
async function closeDetail() {
  resetDetail()
  const query = { ...route.query }
  delete query.ticket
  await router.replace({ query })
}
async function forceResolve(ticket) {
  if (resolveLoading.value) return
  const id = ticket.ticket_id
  resolveLoading.value = true
  try {
    await ElMessageBox.confirm('确认强制解除外部挂起状态？', '强制恢复', {
      confirmButtonText: '确认恢复', cancelButtonText: '取消', type: 'warning'
    })
  } catch { resolveLoading.value = false; return }
  if (disposed) { resolveLoading.value = false; return }
  try {
    await ticketApi.action(id, { action: 'external_resolved', remark: '平台管理员强制恢复' })
    if (disposed) return
    ElMessage.success('已恢复处理中')
    await loadTickets()
    if (detailVisible.value && selectedTicketId.value === id) await loadDetail(id)
  } catch (e) { if (!disposed) ElMessage.error(e.message || '恢复失败') }
  finally { resolveLoading.value = false }
}
onMounted(() => {
  loadReferences()
  loadTickets()
})
watch(() => route.query.ticket, id => {
  if (typeof id === 'string' && id) detailPromise = loadDetail(id)
  else resetDetail()
}, { immediate: true, flush: 'sync' })
onUnmounted(() => {
  disposed = true
  ++listRequest
  ++referenceRequest
  resetDetail()
})
</script>

<style scoped>
.dispatch-view { min-width: 0; color: var(--ws-ink); }
.page-head { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; }
.page-title { margin: 0; font-size: 24px; font-weight: 600; }
.page-sub { color: var(--ws-muted); font-size: 13px; margin: 8px 0 0; }
.dispatch-summary { display: flex; flex-wrap: wrap; gap: 14px 28px; padding: 16px 0; border-block: 1px solid var(--ws-line); color: var(--ws-muted); font-size: 12px; }
.dispatch-summary strong { color: var(--ws-ink); font-size: 17px; margin-left: 8px; font-weight: 600; }
.filter-card { padding: 20px 0 4px; }
.filter-card :deep(.el-form) { display: flex; flex-wrap: wrap; }
.filter-card :deep(.el-form-item) { margin: 0 16px 16px 0; }
.filter-total { margin-left: auto; }
.error-state { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; padding: 20px 0; color: var(--el-color-danger); }
.ticket-id { font-family: monospace; font-size: 12px; }
.pagination { margin-top: 20px; justify-content: flex-end; }
.assign-info, .detail-desc, .action-card { margin-bottom: 20px; }
.assign-ticket-title { margin-top: 6px; }
.action-title { font-weight: 600; }
.flow-card { border: 0; border-top: 1px solid var(--ws-line); border-radius: 0; }
.flow-content { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.flow-operator, .flow-remark { color: var(--ws-muted); font-size: 12px; }
@media (max-width: 640px) { .page-title { font-size: 21px; } .dispatch-summary { gap: 12px 18px; } }
</style>
