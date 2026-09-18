<template>
  <div class="supervisor-view">
    <h2>📊 主管看板</h2>
    <p class="sub">全局工单管理 · 派单 · 催办 · 改派</p>

    <!-- 统计卡 -->
    <div class="stat-cards">
      <div class="stat-card" v-for="s in stats" :key="s.label">
        <div class="stat-num">{{ s.count }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <select v-model="filter.status" @change="loadTickets">
        <option value="">全部状态</option>
        <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="filter.category" @change="loadTickets">
        <option value="">全部分类</option>
        <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="filter.assignee" @change="loadTickets">
        <option value="">全部处理人</option>
        <option v-for="e in engineers" :key="e.user_id" :value="e.user_id">{{ e.name }}</option>
      </select>
      <span class="total">共 {{ total }} 张工单</span>
    </div>

    <!-- 工单列表 -->
    <div class="ticket-table">
      <div class="table-header">
        <span style="width:180px">工单号</span>
        <span style="width:80px">状态</span>
        <span style="width:60px">优先级</span>
        <span style="width:60px">分类</span>
        <span style="flex:1">标题</span>
        <span style="width:80px">提单人</span>
        <span style="width:80px">处理人</span>
        <span style="width:100px">操作</span>
      </div>
      <div v-for="t in tickets" :key="t.ticket_id" class="table-row" @click="openDetail(t)">
        <span style="width:180px" class="ticket-id">{{ t.ticket_id }}</span>
        <span style="width:80px"><span class="status-tag" :class="statusClass(t.status)">{{ t.status }}</span></span>
        <span style="width:60px"><span class="priority-tag" :class="t.priority">{{ t.priority }}</span></span>
        <span style="width:60px">{{ t.category }}</span>
        <span style="flex:1" class="ellipsis">{{ t.title }}</span>
        <span style="width:80px">{{ t.creator_name }}</span>
        <span style="width:80px">{{ t.assignee_name || '-' }}</span>
        <span style="width:100px">
          <button v-if="t.status === '待处理'" class="btn-sm pri" @click.stop="showAssign(t)">派单</button>
          <button v-if="['处理中','待外部'].includes(t.status)" class="btn-sm" @click.stop="showReassign(t)">改派</button>
        </span>
      </div>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="page--; loadTickets()">上一页</button>
      <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
      <button :disabled="page * pageSize >= total" @click="page++; loadTickets()">下一页</button>
    </div>

    <!-- ===== 派单弹窗 ===== -->
    <div v-if="assignTicket" class="modal-overlay" @click.self="assignTicket = null">
      <div class="modal small">
        <h3>{{ assignTicket.assignee_id ? '改派' : '派单' }} · {{ assignTicket.ticket_id }}</h3>
        <p>{{ assignTicket.title }}</p>
        <label>选择处理工程师</label>
        <select v-model="selectedEngineer">
          <option value="">-- 请选择 --</option>
          <option v-for="e in engineers" :key="e.user_id" :value="e.user_id">{{ e.name }} ({{ e.department }})</option>
        </select>
        <input v-if="assignTicket.assignee_id" v-model="reassignReason" placeholder="改派原因" style="margin-top:8px" />
        <button class="btn-submit" :disabled="!selectedEngineer" @click="doAssign">确认{{ assignTicket.assignee_id ? '改派' : '派单' }}</button>
        <button class="btn-submit" style="background:#999;margin-left:8px" @click="assignTicket = null">取消</button>
      </div>
    </div>

    <!-- ===== 工单详情弹窗 ===== -->
    <div v-if="detailTicket" class="modal-overlay" @click.self="detailTicket = null">
      <div class="modal">
        <button class="modal-close" @click="detailTicket = null">✕</button>
        <h3>工单详情 · {{ detailTicket.ticket_id }}</h3>

        <div class="detail-grid">
          <div><b>标题：</b>{{ detailTicket.title }}</div>
          <div><b>分类：</b>{{ detailTicket.category }} | <b>优先级：</b>{{ detailTicket.priority }}</div>
          <div><b>状态：</b><span class="status-tag" :class="statusClass(detailTicket.status)">{{ detailTicket.status }}</span></div>
          <div><b>提单人：</b>{{ detailTicket.creator_name }}</div>
          <div><b>处理人：</b>{{ detailTicket.assignee_name || '未分配' }}</div>
          <div><b>描述：</b>{{ detailTicket.description }}</div>
          <div><b>创建时间：</b>{{ formatTime(detailTicket.created_at) }}</div>
        </div>

        <!-- 主管对挂起工单的强制恢复 -->
        <div v-if="detailTicket.status === '待外部'" class="action-section">
          <button class="btn-action" @click="forceResolve(detailTicket)">🔄 强制恢复处理中</button>
        </div>

        <!-- 流转日志 -->
        <div class="flow-log">
          <h4>流转记录</h4>
          <div v-for="f in detailFlows" :key="f.log_id" class="flow-item">
            <span class="flow-time">{{ formatTime(f.created_at) }}</span>
            <span class="flow-status">{{ f.to_status || f.from_status }}</span>
            <span>{{ f.operator_name }}</span>
            <span class="flow-remark">{{ f.remark }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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
const statsData = ref({ 待处理: 0, 处理中: 0, 待补充: 0, 待外部: 0, 待验收: 0, 已完成: 0, 已取消: 0, 全部: 0 })

const stats = computed(() => [
  { label: '待处理', count: statsData.value['待处理'] },
  { label: '处理中', count: statsData.value['处理中'] },
  { label: '待验收', count: statsData.value['待验收'] },
  { label: '已完成', count: statsData.value['已完成'] },
  { label: '全部', count: statsData.value['全部'] }
])

// 派单
const assignTicket = ref(null)
const selectedEngineer = ref('')
const reassignReason = ref('')

// 详情
const detailTicket = ref(null)
const detailFlows = ref([])

function statusClass(s) {
  const map = { '待处理': 'pending', '处理中': 'processing', '待补充': 'need-info', '待外部': 'external', '待验收': 'acceptance', '已完成': 'done', '已取消': 'cancelled' }
  return map[s] || ''
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

async function loadStats() {
  try {
    const res = await ticketApi.stats()
    if (res.code === 0 && res.data) {
      statsData.value = { ...statsData.value, ...res.data }
    }
  } catch (e) { console.error(e) }
}

function showAssign(ticket) {
  assignTicket.value = { ...ticket }
  selectedEngineer.value = ''
  reassignReason.value = ''
}
function showReassign(ticket) {
  assignTicket.value = { ...ticket }
  selectedEngineer.value = ''
  reassignReason.value = ''
}

async function doAssign() {
  try {
    await ticketApi.assign(assignTicket.value.ticket_id, {
      assignee_id: selectedEngineer.value,
      reason: reassignReason.value || undefined
    })
    alert(assignTicket.value.assignee_id ? '改派成功！' : '派单成功！')
    assignTicket.value = null
    loadTickets()
  } catch (e) { alert(e.message) }
}

async function openDetail(ticket) {
  try {
    const res = await ticketApi.detail(ticket.ticket_id)
    detailTicket.value = res.data.ticket
    detailFlows.value = res.data.flow_logs
  } catch (e) { console.error(e) }
}

async function forceResolve(ticket) {
  if (!confirm('确认强制解除外部挂起状态？')) return
  try {
    await ticketApi.action(ticket.ticket_id, { action: 'external_resolved', remark: '主管强制恢复' })
    alert('已恢复处理中')
    detailTicket.value = null
    loadTickets()
  } catch (e) { alert(e.message) }
}

onMounted(() => {
  loadEngineers()
  loadTickets()
  loadStats()
})
</script>

<style scoped>
.sub { color: #999; margin-bottom: 20px; }
.stat-cards { display: flex; gap: 12px; margin-bottom: 20px; }
.stat-card { flex: 1; background: #fff; border-radius: 10px; padding: 16px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.stat-num { font-size: 28px; font-weight: 700; color: #1a73e8; }
.stat-label { font-size: 13px; color: #999; margin-top: 4px; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 16px; align-items: center; }
.filter-bar select { padding: 8px 12px; border: 1px solid #d9d9d9; border-radius: 6px; font-size: 14px; }
.total { margin-left: auto; font-size: 14px; color: #666; }
.ticket-table { background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.table-header { display: flex; padding: 12px 16px; background: #fafafa; font-size: 13px; font-weight: 600; color: #666; border-bottom: 1px solid #e8e8e8; }
.table-row { display: flex; align-items: center; padding: 12px 16px; border-bottom: 1px solid #f0f0f0; font-size: 14px; cursor: pointer; transition: background .1s; }
.table-row:hover { background: #f5f8ff; }
.ticket-id { font-family: monospace; color: #1a73e8; font-weight: 600; }
.ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-tag { padding: 2px 8px; border-radius: 10px; font-size: 12px; color: #fff; }
.status-tag.pending { background: #faad14; }
.status-tag.processing { background: #1890ff; }
.status-tag.need-info, .status-tag.external { background: #722ed1; }
.status-tag.acceptance { background: #13c2c2; }
.status-tag.done { background: #52c41a; }
.status-tag.cancelled { background: #999; }
.priority-tag { padding: 2px 8px; border-radius: 4px; font-size: 12px; background: #f0f0f0; }
.priority-tag.高 { color: #e74c3c; }
.priority-tag.中 { color: #faad14; }
.priority-tag.低 { color: #999; }
.btn-sm { padding: 4px 12px; font-size: 12px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-sm.pri { background: #1a73e8; color: #fff; border-color: #1a73e8; }
.btn-sm:hover { border-color: #1a73e8; color: #1a73e8; }
.btn-submit { padding: 10px 24px; background: #1a73e8; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; margin-top: 12px; margin-right: 8px; }
.btn-submit:disabled { opacity: .5; cursor: not-allowed; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 16px; }
.pagination button { padding: 6px 16px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; cursor: pointer; }
.pagination button:disabled { opacity: .4; cursor: not-allowed; }

/* 弹窗 */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 12px; padding: 32px; width: 700px; max-height: 80vh; overflow-y: auto; position: relative; }
.modal.small { width: 480px; }
.modal-close { position: absolute; top: 12px; right: 16px; border: none; background: none; font-size: 20px; cursor: pointer; color: #999; }
.modal h3 { margin-bottom: 12px; }
.modal p { color: #666; margin-bottom: 16px; }
.modal label { display: block; font-weight: 600; margin-bottom: 6px; }
.modal select, .modal input { width: 100%; padding: 8px 12px; border: 1px solid #d9d9d9; border-radius: 6px; font-size: 14px; }
.detail-grid { display: grid; gap: 10px; margin-bottom: 20px; }
.action-section { background: #f9f9f9; padding: 16px; border-radius: 8px; margin-bottom: 16px; }
.btn-action { padding: 8px 16px; border: 1px solid #d9d9d9; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; }
.btn-action:hover { border-color: #faad14; color: #d48806; }
.flow-log { border-top: 1px solid #e8e8e8; padding-top: 16px; }
.flow-log h4 { margin-bottom: 10px; }
.flow-item { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px dashed #f0f0f0; font-size: 13px; }
.flow-time { color: #999; white-space: nowrap; }
.flow-status { padding: 1px 6px; border-radius: 4px; background: #e8f0fe; color: #1a73e8; font-size: 12px; }
.flow-remark { color: #666; }
</style>