<template>
  <div class="engineer-view">
    <h2>🔧 工程师工作台</h2>
    <p class="sub">已分配工单 · 看板视图</p>

    <div class="kanban">
      <div v-for="col in columns" :key="col.status" class="kanban-col">
        <div class="col-header" :class="col.color">
          {{ col.label }}
          <span class="count">{{ col.tickets.length }}</span>
        </div>
        <div v-if="col.tickets.length === 0" class="empty-col">暂无</div>
        <div v-for="t in col.tickets" :key="t.ticket_id" class="kanban-card" :class="{ high: t.priority === '高' }" @click="openDetail(t)">
          <div class="card-top">
            <span class="card-id">{{ t.ticket_id }}</span>
            <span class="priority-dot" :class="t.priority">{{ t.priority }}</span>
          </div>
          <div class="card-title">{{ t.title }}</div>
          <div class="card-meta">
            <span>{{ t.creator_name }}</span>
            <span>{{ t.category }}</span>
          </div>
          <div class="card-time">{{ formatTime(t.created_at) }}</div>
        </div>
      </div>
    </div>

    <!-- ===== 工单详情弹窗 ===== -->
    <div v-if="detail" class="modal-overlay" @click.self="detail = null">
      <div class="modal">
        <button class="modal-close" @click="detail = null">✕</button>
        <h3>工单处理 · {{ detail.ticket_id }}</h3>

        <div class="detail-grid">
          <div><b>标题：</b>{{ detail.title }}</div>
          <div><b>分类：</b>{{ detail.category }} | <b>优先级：</b>{{ detail.priority }}</div>
          <div><b>状态：</b><span class="status-tag" :class="statusClass(detail.status)">{{ detail.status }}</span></div>
          <div><b>提单人：</b>{{ detail.creator_name }}</div>
          <div><b>描述：</b>{{ detail.description }}</div>
          <div v-if="detail.expected_finish_time"><b>期望完成：</b>{{ formatTime(detail.expected_finish_time) }}</div>
          <div><b>创建：</b>{{ formatTime(detail.created_at) }}</div>
        </div>

        <!-- 状态操作按钮 -->
        <div class="action-section">
          <!-- 处理中 → 记录进展 -->
          <div v-if="detail.status === '处理中'" class="action-row">
            <input v-model="progressRemark" placeholder="请输入说明（记录进展≥5字；转外部支持≥10字）" />
            <button class="btn-action" @click="doAction('progress')">📝 记录进展</button>
            <button class="btn-action warn" @click="doAction('need_info')">❓ 申请补充</button>
            <button class="btn-action warn" @click="doAction('external')">🔗 需外部支持</button>
          </div>

          <!-- 待补充 → 已补回 -->
          <div v-if="detail.status === '待补充'" class="action-row">
            <span class="hint">等待员工补充信息中...</span>
          </div>

          <!-- 待外部 → 外部解除 -->
          <div v-if="detail.status === '待外部'" class="action-row">
            <span class="hint">等待外部支持中...</span>
            <button class="btn-action success" @click="doAction('external_resolved')">✅ 外部已解除</button>
          </div>

          <!-- 处理中 → 提交方案 -->
          <div v-if="detail.status === '处理中'" class="action-row submit-row">
            <button class="btn-action success big" :disabled="!canDone" @click="doAction('done')">
              ✅ 提交解决方案
            </button>
            <span v-if="!canDone" class="hint">请先记录至少一条处理进展</span>
          </div>

          <!-- 待验收 → 等待中 -->
          <div v-if="detail.status === '待验收'" class="action-row">
            <span class="hint">⏳ 已提交方案，等待员工验收...</span>
          </div>
        </div>
        <span v-if="actionError" class="error-text">{{ actionError }}</span>

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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ticketApi } from '../api/index.js'
import { useUserStore } from '../stores/user.js'

const userStore = useUserStore()
const allTickets = ref([])
const detail = ref(null)
const detailFlows = ref([])
const progressRemark = ref('')
const actionError = ref('')
let pollTimer = null

const columns = computed(() => {
  const statusMap = {
    '待处理':   { label: '待处理', color: 'yellow' },
    '处理中':   { label: '处理中', color: 'blue' },
    '待补充':   { label: '待补充', color: 'purple' },
    '待外部':   { label: '待外部', color: 'orange' },
    '待验收':   { label: '待验收', color: 'cyan' },
    '已完成':   { label: '已完成', color: 'green' },
    '已取消':   { label: '已取消', color: 'gray' }
  }
  const result = Object.keys(statusMap).map(s => ({ status: s, ...statusMap[s], tickets: [] }))
  allTickets.value.forEach(t => {
    const col = result.find(c => c.status === t.status)
    if (col) col.tickets.push(t)
  })
  return result
})

const canDone = computed(() => {
  // 至少有一条处理进展（非提交工单的log）
  return detailFlows.value.some(f => f.remark && f.remark !== '提交工单' && f.operator_id === userStore.userId)
})

function statusClass(s) {
  const map = { '待处理': 'pending', '处理中': 'processing', '待补充': 'need-info', '待外部': 'external', '待验收': 'acceptance', '已完成': 'done', '已取消': 'cancelled' }
  return map[s] || ''
}
function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '' }

async function loadTickets() {
  try {
    const res = await ticketApi.list({ assignee_id: userStore.userId, page_size: 100 })
    allTickets.value = res.data.list
  } catch (e) { console.error(e) }
}

async function openDetail(t) {
  try {
    const res = await ticketApi.detail(t.ticket_id)
    detail.value = res.data.ticket
    detailFlows.value = res.data.flow_logs
    progressRemark.value = ''
    actionError.value = ''
  } catch (e) { console.error(e) }
}

async function doAction(action) {
  actionError.value = ''
  const input = progressRemark.value.trim()

  // 各操作对备注的要求
  const needRemark = { progress: 5, need_info: 5, external: 10 }
  if (needRemark[action]) {
    if (input.length < needRemark[action]) {
      actionError.value = action === 'external'
        ? `外部依赖说明至少${needRemark[action]}个字符`
        : `说明至少${needRemark[action]}个字符`
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
    alert('操作成功！')
    detail.value = null
    loadTickets()
  } catch (e) { actionError.value = e.message }
}

onMounted(() => {
  loadTickets()
  // 15s 轮询看板
  pollTimer = setInterval(loadTickets, 15000)
})
onUnmounted(() => clearInterval(pollTimer))
</script>

<style scoped>
.sub { color: #999; margin-bottom: 20px; }
.kanban { display: flex; gap: 12px; overflow-x: auto; }
.kanban-col { min-width: 220px; flex: 1; background: #f5f5f5; border-radius: 10px; padding: 12px; }
.col-header { font-weight: 700; font-size: 14px; padding: 6px 10px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; }
.col-header.yellow { background: #fffbe6; color: #ad6800; }
.col-header.blue { background: #e6f7ff; color: #096dd9; }
.col-header.purple { background: #f9f0ff; color: #722ed1; }
.col-header.orange { background: #fff7e6; color: #d46b08; }
.col-header.cyan { background: #e6fffb; color: #08979c; }
.col-header.green { background: #f6ffed; color: #389e0d; }
.col-header.gray { background: #fafafa; color: #999; }
.count { background: rgba(255,255,255,.7); padding: 0 8px; border-radius: 10px; font-size: 12px; }
.empty-col { text-align: center; color: #ccc; padding: 20px; font-size: 13px; }
.kanban-card { background: #fff; border-radius: 8px; padding: 12px; margin-bottom: 8px; cursor: pointer; border-left: 3px solid #1890ff; transition: box-shadow .2s; }
.kanban-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.kanban-card.high { border-left-color: #e74c3c; }
.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.card-id { font-family: monospace; font-size: 12px; color: #1a73e8; }
.priority-dot { font-size: 11px; padding: 1px 6px; border-radius: 4px; }
.priority-dot.高 { background: #fff1f0; color: #e74c3c; }
.priority-dot.中 { background: #fffbe6; color: #faad14; }
.priority-dot.低 { background: #f0f0f0; color: #999; }
.card-title { font-size: 14px; font-weight: 500; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-meta { font-size: 12px; color: #999; display: flex; gap: 8px; }
.card-time { font-size: 11px; color: #bbb; margin-top: 4px; }

/* 弹窗 */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 12px; padding: 32px; width: 700px; max-height: 80vh; overflow-y: auto; position: relative; }
.modal-close { position: absolute; top: 12px; right: 16px; border: none; background: none; font-size: 20px; cursor: pointer; color: #999; }
.modal h3 { margin-bottom: 16px; }
.detail-grid { display: grid; gap: 10px; margin-bottom: 20px; }
.status-tag { padding: 2px 8px; border-radius: 10px; font-size: 12px; color: #fff; }
.status-tag.pending { background: #faad14; }
.status-tag.processing { background: #1890ff; }
.status-tag.need-info, .status-tag.external { background: #722ed1; }
.status-tag.acceptance { background: #13c2c2; }
.status-tag.done { background: #52c41a; }
.status-tag.cancelled { background: #999; }
.action-section { background: #f9f9f9; padding: 16px; border-radius: 8px; margin-bottom: 16px; }
.action-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.action-row input { flex: 1; min-width: 200px; padding: 8px; border: 1px solid #d9d9d9; border-radius: 6px; font-size: 14px; }
.btn-action { padding: 8px 16px; border: 1px solid #d9d9d9; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; white-space: nowrap; }
.btn-action:hover { border-color: #1890ff; color: #1890ff; }
.btn-action.success { background: #52c41a; color: #fff; border-color: #52c41a; }
.btn-action.warn { background: #fff7e6; border-color: #faad14; color: #d48806; }
.btn-action.big { padding: 10px 24px; font-size: 15px; }
.submit-row { margin-top: 12px; }
.hint { font-size: 13px; color: #999; }
.error-text { color: #e74c3c; font-size: 13px; margin-top: 8px; display: block; }
.flow-log { border-top: 1px solid #e8e8e8; padding-top: 16px; }
.flow-log h4 { margin-bottom: 10px; }
.flow-item { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px dashed #f0f0f0; font-size: 13px; }
.flow-time { color: #999; white-space: nowrap; }
.flow-status { padding: 1px 6px; border-radius: 4px; background: #e8f0fe; color: #1a73e8; font-size: 12px; }
.flow-remark { color: #666; }
</style>