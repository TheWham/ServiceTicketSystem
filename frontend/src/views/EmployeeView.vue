<template>
  <div class="employee-view">
    <!-- ===== 顶部 Tabs ===== -->
    <el-tabs v-model="tab" class="view-tabs">
      <el-tab-pane name="create">
        <template #label>
          <el-icon style="vertical-align:-2px;margin-right:4px"><EditPen /></el-icon>提交工单
        </template>
      </el-tab-pane>
      <el-tab-pane name="list">
        <template #label>
          <el-icon style="vertical-align:-2px;margin-right:4px"><List /></el-icon>我的工单
          <el-badge :value="total" :max="99" class="tab-badge" />
        </template>
      </el-tab-pane>
    </el-tabs>

    <!-- ===== 提单表单 ===== -->
    <el-card v-if="tab === 'create'" shadow="never" class="panel">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">提交新工单</span>
        </div>
      </template>

      <!-- 草稿提示 -->
      <el-alert
        v-if="draftBanner"
        type="warning"
        :closable="false"
        class="draft-alert"
      >
        <template #title>
          ⚠️ 检测到未提交的草稿，
          <el-link type="primary" @click="restoreDraft">点击恢复</el-link>
          <el-link type="info" style="margin-left:12px" @click="clearDraft">忽略</el-link>
        </template>
      </el-alert>

      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-position="top"
        class="ticket-form"
      >
        <!-- 工单标题 -->
        <el-form-item prop="title">
          <template #label>
            工单标题 <span class="required">*</span>
            <span class="char-count">{{ form.title.length }}/50</span>
          </template>
          <el-input
            v-model="form.title"
            maxlength="50"
            show-word-limit
            placeholder="一句话概括问题，如：市场部打印机无法连接"
            clearable
          />
        </el-form-item>

        <el-row :gutter="16">
          <!-- 分类 -->
          <el-col :span="12">
            <el-form-item prop="category" label="问题分类">
              <el-radio-group v-model="form.category">
                <el-radio-button v-for="c in categories" :key="c" :value="c">{{ c }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>

          <!-- 优先级 -->
          <el-col :span="12">
            <el-form-item prop="priority" label="优先级">
              <el-radio-group v-model="form.priority">
                <el-radio-button value="高">高</el-radio-button>
                <el-radio-button value="中">中</el-radio-button>
                <el-radio-button value="低">低</el-radio-button>
              </el-radio-group>
              <div v-if="form.priority === '高'" class="priority-hint">
                <el-icon><WarningFilled /></el-icon>
                高优先级将同步短信通知，请确认确为紧急故障
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 问题描述 -->
        <el-form-item prop="description">
          <template #label>
            问题描述 <span class="required">*</span>
            <span class="char-count">{{ form.description.length }}/500</span>
          </template>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="5"
            maxlength="500"
            show-word-limit
            placeholder="请详细描述问题：何时开始、报错原文、已尝试的操作..."
          />
        </el-form-item>

        <el-row :gutter="16">
          <!-- 期望完成时间 -->
          <el-col :span="12">
            <el-form-item label="期望完成时间">
              <el-date-picker
                v-model="form.expected_finish_time"
                type="datetime"
                placeholder="选择期望完成时间（可选）"
                :disabled-date="disablePastDate"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DDTHH:mm"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 提交区 -->
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            :disabled="!!submitHint"
            @click="submitTicket"
          >
            {{ submitting ? '提交中...' : '提交工单' }}
          </el-button>
          <el-text v-if="submitHint" type="warning" size="small" style="margin-left:16px">
            {{ submitHint }}
          </el-text>
          <el-text v-if="draftSaved" type="success" size="small" style="margin-left:16px">
            <el-icon style="vertical-align:-2px"><SuccessFilled /></el-icon>
            草稿已自动保存 {{ draftTime }}
          </el-text>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- ===== 我的工单列表 ===== -->
    <el-card v-if="tab === 'list'" shadow="never" class="panel">
      <template #header>
        <div class="panel-header">
          <span class="panel-title">我的工单</span>
          <el-select
            v-model="filter.status"
            placeholder="全部状态"
            clearable
            style="width: 160px"
            @change="loadTickets"
          >
            <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
          </el-select>
        </div>
      </template>

      <el-empty v-if="tickets.length === 0" description="暂无工单" />

      <div v-else class="ticket-list">
        <el-card
          v-for="t in tickets"
          :key="t.ticket_id"
          shadow="hover"
          class="ticket-card"
          @click="openDetail(t)"
        >
          <div class="ticket-header">
            <span class="ticket-id">{{ t.ticket_id }}</span>
            <el-tag :type="statusTagType(t.status)" size="small">{{ t.status }}</el-tag>
            <el-tag :type="priorityTagType(t.priority)" size="small" effect="plain">{{ t.priority }}</el-tag>
          </div>
          <div class="ticket-title">{{ t.title }}</div>
          <div class="ticket-meta">
            <el-tag size="small" type="info" effect="plain">{{ t.category }}</el-tag>
            <span v-if="t.assignee_name">处理人：{{ t.assignee_name }}</span>
            <span>{{ formatTime(t.created_at) }}</span>
          </div>
        </el-card>
      </div>

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
          <el-descriptions-item v-if="detailTicket.expected_finish_time" label="期望完成" :span="2">
            {{ formatTime(detailTicket.expected_finish_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="问题描述" :span="2">{{ detailTicket.description }}</el-descriptions-item>
        </el-descriptions>

        <!-- 验收操作 -->
        <el-card v-if="detailTicket.status === '待验收'" shadow="never" class="action-card">
          <template #header><span class="action-title">验收工单</span></template>
          <el-space>
            <el-button type="success" :icon="CircleCheck" @click="acceptTicket(detailTicket)">
              确认解决
            </el-button>
          </el-space>
          <el-divider />
          <div class="reject-area">
            <el-input
              v-model="rejectReason"
              placeholder="驳回原因（至少 10 个字符）"
              maxlength="200"
              show-word-limit
            />
            <el-button type="danger" :icon="CircleClose" @click="rejectTicket(detailTicket)">
              驳回
            </el-button>
          </div>
          <el-text v-if="rejectError" type="danger" size="small">{{ rejectError }}</el-text>
        </el-card>

        <!-- 满意度评价 -->
        <el-card
          v-if="detailTicket.status === '已完成' && !detailTicket.rating_score"
          shadow="never"
          class="action-card"
        >
          <template #header><span class="action-title">满意度评价</span></template>
          <el-rate v-model="ratingScore" :max="5" size="large" />
          <el-input
            v-model="ratingComment"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            placeholder="补充评价（选填，≤200 字）"
            style="margin-top:12px"
          />
          <el-button
            type="primary"
            :disabled="!ratingScore"
            style="margin-top:12px"
            @click="submitRating(detailTicket)"
          >
            提交评价
          </el-button>
        </el-card>

        <el-alert
          v-if="detailTicket.rating_score"
          type="success"
          :closable="false"
          style="margin-bottom:16px"
        >
          <template #title>
            <el-rate :model-value="detailTicket.rating_score" :max="5" disabled size="small" />
            <span style="margin-left:8px">{{ detailTicket.rating_comment || '未留言' }}</span>
          </template>
        </el-alert>

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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  EditPen, List, WarningFilled, SuccessFilled, CircleCheck, CircleClose
} from '@element-plus/icons-vue'
import { ticketApi, draftApi } from '../api/index.js'
import { useUserStore } from '../stores/user.js'

const userStore = useUserStore()
const tab = ref('create')
const categories = ['硬件', '软件', '网络', '账号', '其他']
const statuses = ['待处理', '处理中', '待补充', '待外部', '待验收', '已完成', '已取消']

const form = ref({ title: '', category: '', description: '', priority: '中', expected_finish_time: '' })
const formRef = ref(null)
const submitting = ref(false)
const draftBanner = ref(false)
const draftSaved = ref(false)
const draftTime = ref('')
let draftTimer = null

// Element Plus 表单校验规则（保留原有校验语义）
const formRules = {
  title: [
    { required: true, message: '请填写工单标题', trigger: 'blur' },
    { max: 50, message: '工单标题不能超过 50 个字符', trigger: 'blur' }
  ],
  category: [{ required: true, message: '请选择问题分类', trigger: 'change' }],
  description: [
    { required: true, message: '请填写问题描述', trigger: 'blur' },
    { min: 10, message: '请至少填写 10 个字，说明何时开始、报错原文、已尝试的操作', trigger: 'blur' },
    { max: 500, message: '问题描述不能超过 500 个字符', trigger: 'blur' }
  ]
}

// 工单列表
const tickets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const filter = ref({ status: '' })

// 详情
const detailTicket = ref(null)
const detailFlows = ref([])
const detailVisible = ref(false)
const rejectReason = ref('')
const rejectError = ref('')
const ratingScore = ref(0)
const ratingComment = ref('')

function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '' }

function disablePastDate(time) { return time.getTime() < Date.now() - 86400000 }

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

// 未满足条件时的实时提示
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

  // Element Plus 表单校验
  try {
    await formRef.value.validate()
  } catch (e) {
    nextTick(() => {
      const el = document.querySelector('.el-form-item.is-error')
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
      description: form.value.description.trim(),
      priority: form.value.priority,
      expected_finish_time: form.value.expected_finish_time || null,
      client_token: formToken.value
    })
    form.value = { title: '', category: '', description: '', priority: '中', expected_finish_time: '' }
    formToken.value = genClientToken()
    await draftApi.delete().catch(() => {})
    draftBanner.value = false
    draftSaved.value = false
    ElMessage.success('工单提交成功！')
    tab.value = 'list'
    loadTickets()
  } catch (e) {
    ElMessage.error('提交失败：' + e.message)
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
    detailVisible.value = true
  } catch (e) { ElMessage.error('加载详情失败：' + e.message) }
}

// 验收通过
async function acceptTicket(t) {
  try {
    await ElMessageBox.confirm('确认此工单已解决？', '验收确认', {
      confirmButtonText: '确认解决',
      cancelButtonText: '再想想',
      type: 'success'
    })
  } catch { return }

  try {
    await ticketApi.action(t.ticket_id, { action: 'accept' })
    ElMessage.success('验收通过！')
    detailVisible.value = false
    loadTickets()
  } catch (e) { ElMessage.error(e.message) }
}

// 驳回
async function rejectTicket(t) {
  rejectError.value = ''
  if (!rejectReason.value || rejectReason.value.length < 10) {
    rejectError.value = '驳回原因至少 10 个字符'
    return
  }
  try {
    await ticketApi.action(t.ticket_id, { action: 'reject', remark: rejectReason.value })
    ElMessage.success('已驳回，工单退回处理中')
    detailVisible.value = false
    loadTickets()
  } catch (e) { ElMessage.error(e.message) }
}

// 评价
async function submitRating(t) {
  try {
    await ticketApi.rating(t.ticket_id, { score: ratingScore.value, comment: ratingComment.value })
    ElMessage.success('评价成功！')
    detailVisible.value = false
    loadTickets()
  } catch (e) { ElMessage.error(e.message) }
}

// 自动保存草稿：每 30s
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
.view-tabs :deep(.el-tabs__header) { margin-bottom: 16px; }
.tab-badge { margin-left: 6px; }

.panel { border-radius: 8px; }
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.panel-title { font-size: 16px; font-weight: 600; }

.draft-alert { margin-bottom: 16px; }

.ticket-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.required { color: var(--el-color-danger); }
.char-count { float: right; font-weight: 400; color: var(--el-text-color-secondary); font-size: 12px; }

.priority-hint {
  color: var(--el-color-warning);
  font-size: 12px;
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 列表 */
.ticket-list { display: flex; flex-direction: column; gap: 10px; }
.ticket-card {
  cursor: pointer;
  border-left: 3px solid var(--el-color-primary);
  transition: transform .15s ease;
}
.ticket-card:hover { transform: translateY(-1px); }

.ticket-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.ticket-id {
  font-family: monospace;
  color: var(--el-color-primary);
  font-weight: 600;
  font-size: 13px;
}
.ticket-title { font-size: 15px; font-weight: 500; margin-bottom: 6px; color: var(--el-text-color-primary); }
.ticket-meta {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  display: flex;
  gap: 14px;
  align-items: center;
}

.pagination { margin-top: 16px; justify-content: center; }

/* 弹窗 */
.detail-desc { margin-bottom: 16px; }

.action-card { margin-bottom: 16px; background: var(--el-fill-color-light); }
.action-title { font-weight: 600; }

.reject-area {
  display: flex;
  gap: 8px;
}

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
