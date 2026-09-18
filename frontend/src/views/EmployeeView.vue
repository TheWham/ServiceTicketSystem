<template>
  <div class="employee-view">
    <div class="tab-bar">
      <button :class="{ active: tab === 'create' }" @click="tab = 'create'">📝 提交工单</button>
      <button :class="{ active: tab === 'list' }" @click="tab = 'list'">📋 我的工单 ({{ total }})</button>
    </div>

    <!-- ===== 提单表单 ===== -->
    <div v-if="tab === 'create'" class="form-card">
      <h2>提交新工单</h2>
      <div v-if="draftBanner" class="draft-banner">
        ⚠️ 检测到未提交的草稿，
        <a href="#" @click.prevent="restoreDraft">点击恢复</a>
        <span style="color:#999;margin-left:8px;cursor:pointer" @click="clearDraft">忽略</span>
      </div>

      <div class="form-grid">
        <!-- 工单标题 -->
        <div class="form-group full-width">
          <label>工单标题 <span class="required">*</span><span class="count">{{ form.title.length }}/50</span></label>
          <input type="text" v-model="form.title" placeholder="一句话概括问题，如：市场部打印机无法连接"
            maxlength="50" :class="{ error: errors.title }" @blur="validateTitle" @input="errors.title = ''" />
          <span v-if="errors.title" class="error-text">{{ errors.title }}</span>
        </div>

        <!-- 分类 -->
        <div class="form-group">
          <label>问题分类 <span class="required">*</span></label>
          <div class="chip-group">
            <span v-for="c in categories" :key="c" class="chip" :class="{ active: form.category === c }" @click="form.category = c">{{ c }}</span>
          </div>
          <span v-if="errors.category" class="error-text">{{ errors.category }}</span>
        </div>

        <!-- 优先级 -->
        <div class="form-group">
          <label>优先级 <span class="required">*</span></label>
          <div class="chip-group">
            <span v-for="p in priorities" :key="p" class="chip" :class="{ active: form.priority === p, high: p === '高' }" @click="form.priority = p">{{ p }}</span>
          </div>
          <span v-if="form.priority === '高'" class="hint-text">⚠ 高优先级将同步短信通知，请确认确为紧急故障</span>
        </div>

        <!-- 问题描述 -->
        <div class="form-group full-width">
          <label>问题描述 <span class="required">*</span><span class="count">{{ form.description.length }}/500</span></label>
          <textarea v-model="form.description" placeholder="请详细描述问题：何时开始、报错原文、已尝试的操作..."
            :class="{ error: errors.description }" maxlength="500" rows="5" @input="onDescInput"></textarea>
          <span v-if="errors.description" class="error-text">{{ errors.description }}</span>
        </div>

        <!-- 期望完成时间 -->
        <div class="form-group">
          <label>期望完成时间</label>
          <input type="datetime-local" v-model="form.expected_finish_time" :min="minDate" />
        </div>

        <!-- 提交 -->
        <div class="form-group full-width">
          <button class="btn-submit" :disabled="submitting" @click="submitTicket">
            {{ submitting ? '提交中...' : '提交工单' }}
          </button>
          <span class="submit-hint" v-if="submitHint">{{ submitHint }}</span>
          <span class="draft-status" v-if="draftSaved">✅ 草稿已自动保存 {{ draftTime }}</span>
        </div>
      </div>
    </div>

    <!-- ===== 我的工单列表 ===== -->
    <div v-if="tab === 'list'" class="list-section">
      <div class="filter-bar">
        <select v-model="filter.status" @change="loadTickets">
          <option value="">全部状态</option>
          <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
        </select>
      </div>

      <div v-if="tickets.length === 0" class="empty">暂无工单</div>

      <div v-for="t in tickets" :key="t.ticket_id" class="ticket-card" @click="openDetail(t)">
        <div class="ticket-header">
          <span class="ticket-id">{{ t.ticket_id }}</span>
          <span class="status-tag" :class="statusClass(t.status)">{{ t.status }}</span>
          <span class="priority-tag" :class="t.priority">{{ t.priority }}</span>
        </div>
        <div class="ticket-title">{{ t.title }}</div>
        <div class="ticket-meta">
          <span>{{ t.category }}</span>
          <span v-if="t.assignee_name">处理人：{{ t.assignee_name }}</span>
          <span>{{ formatTime(t.created_at) }}</span>
        </div>
      </div>

      <div class="pagination" v-if="total > pageSize">
        <button :disabled="page <= 1" @click="page--; loadTickets()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button :disabled="page * pageSize >= total" @click="page++; loadTickets()">下一页</button>
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
          <div v-if="detailTicket.expected_finish_time"><b>期望完成：</b>{{ formatTime(detailTicket.expected_finish_time) }}</div>
          <div><b>创建时间：</b>{{ formatTime(detailTicket.created_at) }}</div>
        </div>

        <!-- 验收/评价操作 -->
        <div v-if="detailTicket.status === '待验收'" class="action-section">
          <h4>验收工单</h4>
          <button class="btn-success" @click="acceptTicket(detailTicket)">✅ 确认解决</button>
          <div class="reject-row">
            <input v-model="rejectReason" placeholder="驳回原因（至少10个字符）" />
            <button class="btn-danger" @click="rejectTicket(detailTicket)">❌ 驳回</button>
          </div>
          <span v-if="rejectError" class="error-text">{{ rejectError }}</span>
        </div>

        <!-- 已完成工单可评价 -->
        <div v-if="detailTicket.status === '已完成' && !detailTicket.rating_score" class="action-section">
          <h4>满意度评价</h4>
          <div class="star-row">
            <span v-for="s in 5" :key="s" class="star" :class="{ active: ratingScore >= s }" @click="ratingScore = s">★</span>
          </div>
          <textarea v-model="ratingComment" placeholder="补充评价（选填，≤200字）" maxlength="200"></textarea>
          <button class="btn-submit" :disabled="!ratingScore" @click="submitRating(detailTicket)">提交评价</button>
        </div>
        <div v-if="detailTicket.rating_score" class="rating-display">
          ⭐ {{ detailTicket.rating_score }} 分 {{ detailTicket.rating_comment ? '— ' + detailTicket.rating_comment : '' }}
        </div>

        <!-- 流转日志 -->
        <div class="flow-log">
          <h4>流转记录</h4>
          <div v-if="detailFlows.length === 0" class="empty">暂无记录</div>
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ticketApi, draftApi } from '../api/index.js'
import { useUserStore } from '../stores/user.js'

const userStore = useUserStore()
const tab = ref('create')
const categories = ['硬件', '软件', '网络', '账号', '其他']
const priorities = ['高', '中', '低']
const statuses = ['待处理', '处理中', '待补充', '待外部', '待验收', '已完成', '已取消']

const form = ref({ title: '', category: '', description: '', priority: '中', expected_finish_time: '' })
const errors = ref({})
const submitting = ref(false)
const draftBanner = ref(false)
const draftSaved = ref(false)
const draftTime = ref('')
let draftTimer = null

// 工单列表
const tickets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const filter = ref({ status: '' })

// 详情
const detailTicket = ref(null)
const detailFlows = ref([])
const rejectReason = ref('')
const rejectError = ref('')
const ratingScore = ref(0)
const ratingComment = ref('')

const minDate = computed(() => new Date().toISOString().slice(0, 16))

function statusClass(s) {
  const map = { '待处理': 'pending', '处理中': 'processing', '待补充': 'need-info', '待外部': 'external', '待验收': 'acceptance', '已完成': 'done', '已取消': 'cancelled' }
  return map[s] || ''
}

function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '' }

const canSubmit = computed(() => !submitHint.value && !submitting.value)

// 未满足条件时的实时提示（代替“按钮置灰但不说原因”的死锁）
const submitHint = computed(() => {
  if (submitting.value) return ''
  const missing = []
  const tLen = form.value.title.trim().length
  if (tLen === 0) missing.push('工单标题')
  else if (tLen > 50) missing.push('标题需在 50 字以内')
  if (!form.value.category) missing.push('问题分类')
  const dLen = form.value.description.trim().length
  if (dLen < 10) missing.push(`问题描述（还需 ${10 - dLen} 字）`)
  else if (dLen > 500) missing.push('问题描述需在 500 字以内')
  if (!missing.length) return ''
  return '还差：' + missing.join('、')
})

function validateTitle() {
  const t = form.value.title.trim()
  if (!t) errors.value.title = '请填写工单标题'
  else if (t.length > 50) errors.value.title = '工单标题不能超过 50 个字符'
  else errors.value.title = ''
}

// 兼容非安全上下文（crypto.randomUUID 在 http 非 localhost 下不可用）
function genClientToken() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'tk-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10)
}

// 幂等令牌：同一表单会话内保持不变，双击/重试只会命中后端幂等而不会重复建单
const formToken = ref('')
const lastSubmitAt = ref(0)

// 提交工单
async function submitTicket() {
  if (submitting.value) return
  // PRD §3.2：防重复点击 Debounce 3 秒
  if (Date.now() - lastSubmitAt.value < 3000) return

  errors.value = {}
  validateTitle()
  if (!form.value.category) errors.value.category = '请选择问题分类'
  const desc = form.value.description.trim()
  if (desc.length < 10) errors.value.description = '请至少填写10个字，说明何时开始、报错原文、已尝试的操作'
  else if (desc.length > 500) errors.value.description = '问题描述不能超过 500 个字符'

  if (Object.keys(errors.value).some(k => errors.value[k])) {
    nextTick(() => {
      const el = document.querySelector('.error-text')
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
    return
  }

  if (!formToken.value) formToken.value = genClientToken()
  submitting.value = true
  lastSubmitAt.value = Date.now()
  try {
    await ticketApi.create({
      title: form.value.title.trim(),
      category: form.value.category,
      description: desc,
      priority: form.value.priority,
      expected_finish_time: form.value.expected_finish_time || null,
      client_token: formToken.value
    })
    // 清空表单和草稿
    form.value = { title: '', category: '', description: '', priority: '中', expected_finish_time: '' }
    formToken.value = genClientToken()
    await draftApi.delete().catch(() => {})
    draftBanner.value = false
    draftSaved.value = false
    alert('工单提交成功！')
    tab.value = 'list'
    loadTickets()
  } catch (e) {
    alert('提交失败：' + e.message)
  } finally {
    submitting.value = false
  }
}

// 草稿
async function saveDraft() {
  await draftApi.save({
    title: form.value.title,
    category: form.value.category,
    description: form.value.description,
    priority: form.value.priority,
    expected_finish_time: form.value.expected_finish_time || null
  })
  draftSaved.value = true
  draftTime.value = new Date().toLocaleTimeString('zh-CN')
}

function restoreDraft() {
  draftApi.get().then(res => {
    if (res.data) {
      form.value = {
        title: res.data.title || '',
        category: res.data.category || '',
        description: res.data.description || '',
        priority: res.data.priority || '中',
        expected_finish_time: res.data.expected_finish_time ? res.data.expected_finish_time.slice(0, 16) : ''
      }
      draftBanner.value = false
    }
  })
}
function clearDraft() { draftApi.delete().catch(() => {}); draftBanner.value = false }

// 加载工单列表
async function loadTickets() {
  try {
    const params = { creator_id: userStore.userId, page: page.value, page_size: pageSize }
    if (filter.value.status) params.status = filter.value.status
    const res = await ticketApi.list(params)
    tickets.value = res.data.list
    total.value = res.data.total
  } catch (e) { console.error(e) }
}

// 查看详情
async function openDetail(ticket) {
  try {
    const res = await ticketApi.detail(ticket.ticket_id)
    detailTicket.value = res.data.ticket
    detailFlows.value = res.data.flow_logs
    rejectReason.value = ''
    rejectError.value = ''
    ratingScore.value = 0
    ratingComment.value = ''
  } catch (e) { console.error(e) }
}

// 验收通过
async function acceptTicket(t) {
  if (!confirm('确认此工单已解决？')) return
  try {
    await ticketApi.action(t.ticket_id, { action: 'accept' })
    alert('验收通过！')
    detailTicket.value = null
    loadTickets()
  } catch (e) { alert(e.message) }
}

// 驳回
async function rejectTicket(t) {
  rejectError.value = ''
  if (!rejectReason.value || rejectReason.value.length < 10) {
    rejectError.value = '驳回原因至少10个字符'
    return
  }
  try {
    await ticketApi.action(t.ticket_id, { action: 'reject', remark: rejectReason.value })
    alert('已驳回，工单退回处理中')
    detailTicket.value = null
    loadTickets()
  } catch (e) { alert(e.message) }
}

// 评价
async function submitRating(t) {
  try {
    await ticketApi.rating(t.ticket_id, { score: ratingScore.value, comment: ratingComment.value })
    alert('评价成功！')
    detailTicket.value = null
    loadTickets()
  } catch (e) { alert(e.message) }
}

function onDescInput() {
  errors.value.description = ''
}

// 自动保存草稿：每30s
watch(form, () => {
  if (!form.value.description.trim()) return
  clearTimeout(draftTimer)
  draftTimer = setTimeout(saveDraft, 30000)
}, { deep: true })

onMounted(async () => {
  try {
    const draft = await draftApi.get()
    if (draft.data) draftBanner.value = true
  } catch (e) {}
  loadTickets()
})

onUnmounted(() => clearTimeout(draftTimer))
</script>

<style scoped>
.tab-bar { display: flex; gap: 8px; margin-bottom: 24px; }
.tab-bar button { padding: 10px 24px; border: 1px solid #d9d9d9; background: #fff; border-radius: 8px; cursor: pointer; font-size: 15px; }
.tab-bar button.active { background: #1a73e8; color: #fff; border-color: #1a73e8; }
.form-card, .list-section { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.form-card h2 { margin-bottom: 20px; font-size: 18px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-group.full-width { grid-column: 1 / -1; }
.form-group label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 14px; }
.required { color: #e74c3c; }
.count { float: right; font-weight: 400; color: #999; }
.chip-group { display: flex; gap: 8px; }
.chip { padding: 6px 16px; border: 1px solid #d9d9d9; border-radius: 20px; cursor: pointer; font-size: 14px; background: #fff; transition: all .2s; }
.chip:hover { border-color: #1a73e8; }
.chip.active { background: #1a73e8; color: #fff; border-color: #1a73e8; }
.chip.high.active { background: #e74c3c; border-color: #e74c3c; }
textarea, input[type="datetime-local"], select, input[type="text"] { width: 100%; padding: 10px 12px; border: 1px solid #d9d9d9; border-radius: 8px; font-size: 14px; font-family: inherit; }
textarea.error { border-color: #e74c3c; }
.error-text { color: #e74c3c; font-size: 12px; margin-top: 4px; display: block; }
.hint-text { color: #e67e22; font-size: 12px; margin-top: 4px; display: block; }
.btn-submit { padding: 12px 40px; background: #1a73e8; color: #fff; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
.btn-submit:disabled { opacity: .5; cursor: not-allowed; }
.submit-hint { margin-left: 16px; font-size: 13px; color: #e67e22; }
.draft-banner { background: #fff3cd; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
.draft-status { margin-left: 16px; font-size: 13px; color: #52c41a; }

/* 列表 */
.filter-bar { margin-bottom: 16px; }
.filter-bar select { width: 200px; }
.ticket-card { border: 1px solid #e8e8e8; border-radius: 8px; padding: 16px; margin-bottom: 12px; cursor: pointer; transition: box-shadow .2s; }
.ticket-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.ticket-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ticket-id { font-family: monospace; color: #1a73e8; font-weight: 600; }
.ticket-title { font-size: 15px; font-weight: 500; margin-bottom: 6px; }
.ticket-meta { font-size: 13px; color: #999; display: flex; gap: 16px; }
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
.empty { text-align: center; color: #999; padding: 40px; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 16px; }
.pagination button { padding: 6px 16px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; cursor: pointer; }
.pagination button:disabled { opacity: .4; cursor: not-allowed; }

/* 弹窗 */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 12px; padding: 32px; width: 700px; max-height: 80vh; overflow-y: auto; position: relative; }
.modal-close { position: absolute; top: 12px; right: 16px; border: none; background: none; font-size: 20px; cursor: pointer; color: #999; }
.modal h3 { margin-bottom: 16px; }
.detail-grid { display: grid; gap: 10px; margin-bottom: 20px; }
.action-section { background: #f9f9f9; padding: 16px; border-radius: 8px; margin-bottom: 16px; }
.action-section h4 { margin-bottom: 10px; }
.btn-success, .btn-danger { padding: 8px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; color: #fff; }
.btn-success { background: #52c41a; margin-right: 12px; }
.btn-danger { background: #e74c3c; }
.reject-row { display: flex; gap: 8px; margin-top: 12px; }
.reject-row input { flex: 1; padding: 8px; border: 1px solid #d9d9d9; border-radius: 6px; }
.star-row { font-size: 32px; margin-bottom: 10px; cursor: pointer; }
.star { color: #ddd; transition: color .2s; }
.star.active { color: #faad14; }
.rating-display { background: #f6ffed; padding: 10px; border-radius: 6px; margin-bottom: 16px; }
.flow-log { border-top: 1px solid #e8e8e8; padding-top: 16px; }
.flow-log h4 { margin-bottom: 10px; }
.flow-item { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px dashed #f0f0f0; font-size: 13px; }
.flow-time { color: #999; white-space: nowrap; }
.flow-status { padding: 1px 6px; border-radius: 4px; background: #e8f0fe; color: #1a73e8; font-size: 12px; }
.flow-remark { color: #666; }
</style>