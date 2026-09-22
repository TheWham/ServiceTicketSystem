<template>
  <div class="supervisor-view">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">
          <el-icon><DataAnalysis /></el-icon> 主管看板
        </h2>
        <p class="page-sub">全局工单管理 · 派单 · 催办 · 改派</p>
      </div>
      <el-button :icon="Refresh" circle @click="loadTickets" />
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="12" class="stat-row">
      <el-col v-for="s in stats" :key="s.label" :xs="12" :sm="8" :md="4">
        <el-card shadow="hover" class="stat-card">
          <el-statistic :value="s.count" :title="s.label">
            <template #suffix>
              <el-icon v-if="s.icon" :color="s.color"><component :is="s.icon" /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

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
            <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
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
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
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
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="priorityTagType(row.priority)" size="small" effect="plain">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="80" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="creator_name" label="提单人" width="90" />
        <el-table-column label="处理人" width="90">
          <template #default="{ row }">{{ row.assignee_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === '待处理'"
              type="primary"
              size="small"
              @click.stop="showAssign(row)"
            >派单</el-button>
            <el-button
              v-if="['处理中','待外部'].includes(row.status)"
              size="small"
              @click.stop="showReassign(row)"
            >改派</el-button>
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
          <el-descriptions-item label="分类">{{ detailTicket.category }}</el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="priorityTagType(detailTicket.priority)" size="small">{{ detailTicket.priority }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(detailTicket.status)" size="small">{{ detailTicket.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提单人">{{ detailTicket.creator_name }}</el-descriptions-item>
          <el-descriptions-item label="处理人">{{ detailTicket.assignee_name || '未分配' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(detailTicket.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="问题描述" :span="2">{{ detailTicket.description }}</el-descriptions-item>
        </el-descriptions>

        <!-- 主管强制恢复 -->
        <el-card v-if="detailTicket.status === '待外部'" shadow="never" class="action-card">
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
              :key="f.log_id"
              :timestamp="formatTime(f.created_at)"
              :type="flowTimelineType(f.to_status)"
            >
              <div class="flow-content">
                <el-tag size="small" effect="plain">{{ f.to_status || f.from_status }}</el-tag>
                <span class="flow-operator">{{ f.operator_name }}</span>
                <span class="flow-remark">{{ f.remark }}</span>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DataAnalysis, Refresh, RefreshRight,
  Clock, Loading, CircleCheck, Finished, Document
} from '@element-plus/icons-vue'
import { ticketApi, userApi } from '../api/index.js'

const categories = ['硬件', '软件', '网络', '账号', '其他']
const statuses = ['待处理', '处理中', '待补充', '待外部', '待验收', '已完成', '已取消']

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
    { label: '待处理', count: counts['待处理'], icon: Clock, color: '#e6a23c' },
    { label: '处理中', count: counts['处理中'], icon: Loading, color: '#409eff' },
    { label: '待验收', count: counts['待验收'], icon: CircleCheck, color: '#13c2c2' },
    { label: '已完成', count: counts['已完成'], icon: Finished, color: '#67c23a' },
    { label: '全部', count: total.value, icon: Document, color: '#909399' }
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
const detailVisible = ref(false)

function statusTagType(s) {
  const map = {
    '待处理': 'warning', '处理中': 'primary', '待补充': 'info',
    '待外部': 'info', '待验收': 'primary', '已完成': 'success', '已取消': 'info'
  }
  return map[s] || 'info'
}

function priorityTagType(p) {
  const map = { '高': 'danger', '中': 'warning', '低': 'info' }
  return map[p] || 'info'
}

function flowTimelineType(status) {
  const map = {
    '已完成': 'success', '待验收': 'primary', '处理中': 'primary',
    '待处理': 'warning', '已取消': 'info'
  }
  return map[status] || 'primary'
}

function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '' }

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
    ElMessage.success(assignTicket.value.assignee_id ? '改派成功！' : '派单成功！')
    assignVisible.value = false
    loadTickets()
  } catch (e) { ElMessage.error(e.message) }
}

async function openDetail(ticket) {
  try {
    const res = await ticketApi.detail(ticket.ticket_id)
    detailTicket.value = res.data.ticket
    detailFlows.value = res.data.flow_logs
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

onMounted(() => {
  loadEngineers()
  loadTickets()
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

/* 统计卡片 */
.stat-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-card :deep(.el-statistic__head) {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.stat-card :deep(.el-statistic__content) {
  font-size: 28px;
  font-weight: 700;
}

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
