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
          <input type="text" v-model="form.title" placeholder="请简要概括问题（1-50字）" maxlength="50" :class="{ error: errors.title }" @input="onTitleInput" />
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

        <!-- 资产编号 -->
        <div class="form-group">
          <label>资产编号</label>
          <input type="text" v-model="form.asset_id" placeholder="IT-PC-20260901" @blur="onAssetBlur" />
          <span v-if="assetInfo" class="hint-text">📦 {{ assetInfo.model }} / 责任人：{{ assetInfo.owner_name }}</span>
          <span v-if="assetError" class="error-text">{{ assetError }}</span>
        </div>

        <!-- 截图附件 -->
        <div class="form-group full-width">
          <label>截图附件（选填，jpg/png，单张≤5MB，最多3张）</label>
          <input type="file" ref="fileInput" accept="image/jpeg,image/png" multiple @change="onFileChange" />
          <div v-if="form.attachment_urls.length" class="attachment-list">
            <div v-for="(url, i) in form.attachment_urls" :key="i" class="attachment-item">
              <span class="attachment-name">{{ fileName(url) }}</span>
              <button type="button" class="attachment-del" @click="removeAttachment(i)">删除</button>
            </div>
          </div>
        </div>

        <!-- 知识库推荐 -->
        <div v-if="kbShow" class="form-group full-width kb-card">
          <div class="kb-header">💡 知识库推荐</div>
          <div v-for="a in kbList" :key="a.article_id" class="kb-item" @click="showSolution(a)">
            <span class="kb-title">{{ a.title }}</span>
            <span class="kb-score">相似度 {{ Math.round(a.similarity_score * 100) }}%</span>
          </div>
        </div>

        <!-- 提交 -->
        <div class="form-group full-width">
          <button class="btn-submit" :disabled="!canSubmit || submitting" @click="submitTicket">
            {{ submitting ? '提交中...' : '提交工单' }}
          </button>
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ticketApi, draftApi, assetApi, kbApi, uploadApi } from '../api/index.js'
import { useUserStore } from '../stores/user.js'

const userStore = useUserStore()
const tab = ref('create')
const categories = ['硬件', '软件', '网络', '账号', '其他']
const priorities = ['高', '中', '低']
const statuses = ['待处理', '处理中', '待补充', '待外部', '待验收', '已完成', '已取消']

const form = ref({ title: '', category: '', description: '', priority: '中', expected_finish_time: '', asset_id: '', attachment_urls: [] })
const errors = ref({})
const submitting = ref(false)
const draftBanner = ref(false)
const draftSaved = ref(false)
const draftTime = ref('')
let draftTimer = null

// 资产校验
const assetInfo = ref(null)
const assetError = ref('')
const assetIdRegex = /^[A-Za-z0-9-]+$/

// 附件
const fileInput = ref(null)

// 知识库推荐
const kbList = ref([])
const kbShow = ref(false)
let kbTimer = null

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

const minDate = computed(() => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16))

function statusClass(s) {
  const map = { '待处理': 'pending', '处理中': 'processing', '待补充': 'need-info', '待外部': 'external', '待验收': 'acceptance', '已完成': 'done', '已取消': 'cancelled' }
  return map[s] || ''
}

function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '' }

const canSubmit = computed(() => form.value.category && form.value.description.trim().length >= 10 && form.value.description.trim().length <= 500 && !submitting.value)

// 提交工单
async function submitTicket() {
  errors.value = {}
  if (!form.value.title.trim()) errors.value.title = '请填写工单标题'
  else if (form.value.title.trim().length > 50) errors.value.title = '工单标题不能超过50字'
  if (!form.value.category) errors.value.category = '请选择问题分类'
  if (form.value.description.trim().length < 10) errors.value.description = '请至少填写10个字，说明何时开始、报错原文、已尝试的操作'
  if (Object.keys(errors.value).length) return

  submitting.value = true
  try {
    const clientToken = crypto.randomUUID()
    await ticketApi.create({
      title: form.value.title.trim(),
      category: form.value.category,
      description: form.value.description.trim(),
      priority: form.value.priority,
      expected_finish_time: form.value.expected_finish_time || null,
      attachment_urls: form.value.attachment_urls,
      asset_id: form.value.asset_id || null,
      client_token: clientToken
    })
    // 清空表单和草稿
    form.value = { title: '', category: '', description: '', priority: '中', expected_finish_time: '', asset_id: '', attachment_urls: [] }
    await draftApi.delete().catch(() => {})
    draftBanner.value = false
    alert('工单提交成功！')
    tab.value = 'list'
    loadTickets()
  } catch (e) {
    alert('提交失败：' + e.message)
  }
  submitting.value = false
}

// 草稿
async function saveDraft() {
  await draftApi.save({
    title: form.value.title,
    category: form.value.category,
    description: form.value.description,
    priority: form.value.priority,
    expected_finish_time: form.value.expected_finish_time || null,
    asset_id: form.value.asset_id || null,
    attachment_urls: form.value.attachment_urls
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
        expected_finish_time: res.data.expected_finish_time ? res.data.expected_finish_time.slice(0, 16) : '',
        asset_id: res.data.asset_id || '',
        attachment_urls: res.data.attachment_urls || []
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

function onTitleInput() {
  errors.value.title = ''
}

// 资产编号失焦校验
async function onAssetBlur() {
  assetInfo.value = null
  assetError.value = ''
  const id = form.value.asset_id.trim()
  if (!id) return
  if (!assetIdRegex.test(id)) {
    assetError.value = '资产编号格式不正确'
    return
  }
  try {
    const res = await assetApi.detail(id)
    if (res.code === 0 && res.data) {
      assetInfo.value = res.data
    } else {
      assetError.value = '未在资产库中找到该编号'
    }
  } catch (e) {
    assetError.value = '未在资产库中找到该编号'
  }
}

// 附件上传
async function onFileChange(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  // 校验数量
  if (form.value.attachment_urls.length + files.length > 3) {
    alert('最多上传3张截图')
    e.target.value = ''
    return
  }
  for (const f of files) {
    if (!['image/jpeg', 'image/png'].includes(f.type)) {
      alert('仅支持 jpg/png 图片：' + f.name)
      e.target.value = ''
      return
    }
    if (f.size > 5 * 1024 * 1024) {
      alert('单张图片不能超过5MB：' + f.name)
      e.target.value = ''
      return
    }
  }
  const fd = new FormData()
  files.forEach(f => fd.append('files', f))
  try {
    const res = await uploadApi.upload(fd)
    if (res.code === 0 && res.data && res.data.urls) {
      form.value.attachment_urls.push(...res.data.urls)
    } else {
      alert('上传失败，请重试')
    }
  } catch (err) {
    alert('上传失败：' + err.message)
  }
  e.target.value = ''
}

function removeAttachment(i) {
  form.value.attachment_urls.splice(i, 1)
}

function fileName(url) {
  const parts = (url || '').split('/')
  return parts[parts.length - 1] || url
}

// 知识库推荐
function showSolution(a) {
  alert(a.solution_summary || a.title)
}

function fetchRecommend() {
  if (!form.value.category || !form.value.description.trim()) {
    kbShow.value = false
    return
  }
  // 2s 超时保护：超时或异常时静默隐藏，不阻塞提单
  const timeout = new Promise(resolve => setTimeout(() => resolve(null), 2000))
  Promise.race([kbApi.recommend({ category: form.value.category, description: form.value.description }), timeout])
    .then(res => {
      if (res && res.code === 0 && res.data && res.data.has_recommendation) {
        kbList.value = res.data.recommend_list || []
        kbShow.value = kbList.value.length > 0
      } else {
        kbShow.value = false
      }
    })
    .catch(() => { kbShow.value = false })
}

// 监听分类与描述触发知识库推荐（描述 300ms 防抖）
watch(() => form.value.category, () => {
  clearTimeout(kbTimer)
  kbTimer = setTimeout(fetchRecommend, 300)
})
watch(() => form.value.description, () => {
  clearTimeout(kbTimer)
  kbTimer = setTimeout(fetchRecommend, 300)
})

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

onUnmounted(() => { clearTimeout(draftTimer); clearTimeout(kbTimer) })
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
.draft-banner { background: #fff3cd; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
.draft-status { margin-left: 16px; font-size: 13px; color: #52c41a; }

/* 附件 */
.attachment-list { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.attachment-item { display: flex; align-items: center; justify-content: space-between; background: #f5f5f5; padding: 6px 12px; border-radius: 6px; font-size: 13px; }
.attachment-name { color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.attachment-del { border: none; background: none; color: #e74c3c; cursor: pointer; font-size: 13px; }
.attachment-del:hover { text-decoration: underline; }

/* 知识库推荐卡 */
.kb-card { background: #f0f7ff; border: 1px solid #bae0ff; border-radius: 8px; padding: 12px 16px; }
.kb-header { font-weight: 600; font-size: 14px; color: #096dd9; margin-bottom: 8px; }
.kb-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #d6e4ff; cursor: pointer; font-size: 14px; }
.kb-item:last-child { border-bottom: none; }
.kb-item:hover .kb-title { color: #1a73e8; }
.kb-title { color: #333; flex: 1; }
.kb-score { color: #52c41a; font-size: 12px; margin-left: 12px; white-space: nowrap; }

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