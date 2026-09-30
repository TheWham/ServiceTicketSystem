<template>
  <div class="employee-view">
    <header class="page-head">
      <div><p class="eyebrow">服务工作台</p><h1 class="page-title">{{ tab === 'create' ? '提交新工单' : '我的工单' }}</h1>
        <p class="page-sub">{{ tab === 'create' ? '描述问题与影响，服务团队将为你跟进。' : '查看处理进度，补充信息并确认解决结果。' }}</p></div>
      <el-button v-if="tab === 'list'" type="primary" :icon="EditPen" @click="setView('create')">提交新工单</el-button>
      <el-button v-else @click="setView('list')">← 返回我的工单</el-button>
    </header>
    <section v-if="tab === 'create'" class="create-section" aria-label="提交新工单">
      <el-alert v-if="categoryError" type="error" :closable="false" class="draft-alert"><template #title>{{ categoryError }} <el-button text @click="loadCategories">重试分类</el-button></template></el-alert>
      <el-alert v-if="prefillError" type="error" :closable="false" class="draft-alert"><template #title>{{ prefillError }} <el-button text @click="loadConsultPrefill(route.query.session)">重试预填</el-button></template></el-alert>
      <el-alert v-if="sourceSession" type="info" :closable="false" class="draft-alert" title="已载入咨询内容，请确认并补充后提交。" />
      <el-alert v-if="draftError" type="warning" :closable="false" class="draft-alert" :title="draftError" />
      <el-alert v-if="localDraftBanner" type="warning" :closable="false" class="draft-alert"><template #title>此设备有未提交的本地草稿。<el-button text @click="restoreLocalDraft">恢复本地草稿</el-button></template></el-alert>
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
        :disabled="submitting"
        label-position="top"
        class="ticket-form"
      >
        <!-- 工单标题 -->
        <el-form-item prop="title">
          <template #label>
            工单标题 <span class="required">*</span>
            <span class="char-count">{{ form.title.length }}/100</span>
          </template>
          <el-input
            v-model="form.title"
            maxlength="100"
            show-word-limit
            placeholder="一句话概括问题，如：市场部打印机无法连接"
            clearable
          />
        </el-form-item>

        <el-row :gutter="16">
          <!-- 工单性质 -->
          <el-col :xs="24" :sm="12">
            <el-form-item prop="nature" label="工单性质">
              <el-radio-group v-model="form.nature">
                <el-radio-button v-for="n in natures" :key="n.value" :value="n.value">{{ n.label }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>

          <!-- 末级分类 -->
          <el-col :xs="24" :sm="12">
            <el-form-item prop="category_id" label="问题分类">
              <el-select v-model="form.category_id" placeholder="选择末级分类" style="width:100%" filterable>
                <el-option v-for="c in filteredCategories" :key="c.category_id" :value="c.category_id" :label="c.name" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 问题描述 -->
        <el-form-item prop="description">
          <template #label>
            问题描述 <span class="required">*</span>
            <span class="char-count">{{ form.description.length }}/5000</span>
          </template>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            maxlength="5000"
            show-word-limit
            placeholder="请详细描述问题：何时开始、报错原文、已尝试的操作..."
          />
        </el-form-item>

        <el-row :gutter="16">
          <!-- 影响情况 -->
          <el-col :xs="24" :sm="12">
            <el-form-item prop="impact_description">
              <template #label>
                影响情况 <span class="required">*</span>
                <span class="char-count">{{ form.impact_description.length }}/2000</span>
              </template>
              <el-input v-model="form.impact_description" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="影响了哪些人/业务？如：本人无法打印 / 全部门网络中断" />
            </el-form-item>
          </el-col>

          <!-- 紧急说明 -->
          <el-col :xs="24" :sm="12">
            <el-form-item prop="urgency_description">
              <template #label>
                紧急说明 <span class="required">*</span>
                <span class="char-count">{{ form.urgency_description.length }}/2000</span>
              </template>
              <el-input v-model="form.urgency_description" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="为什么紧急？如：下午有重要会议需投屏" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <!-- 位置（选填） -->
          <el-col :xs="24" :sm="8">
            <el-form-item label="位置">
              <el-input v-model="form.location" maxlength="200" placeholder="如：3号楼 502 室（选填）" />
            </el-form-item>
          </el-col>
          <!-- 本次联系方式（选填） -->
          <el-col :xs="24" :sm="8">
            <el-form-item label="本次联系方式">
              <el-input v-model="form.contact" maxlength="64" placeholder="手机/座机（选填，不反写档案）" />
            </el-form-item>
          </el-col>
          <!-- 资产编号（选填） -->
          <el-col :xs="24" :sm="8">
            <el-form-item label="资产编号">
              <el-input v-model="form.asset_id" maxlength="64" placeholder="如 PC-2024-001（选填）" />
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
    </section>

    <section v-if="tab === 'list'" aria-label="我的工单列表">
      <div class="list-toolbar">
        <div class="search-field"><label for="employee-ticket-search">搜索本页工单</label>
          <el-input id="employee-ticket-search" v-model="keyword" placeholder="搜索工单号 / 标题 / 处理人" :prefix-icon="Search" clearable /></div>
        <div class="filter-field"><label for="employee-status">工单状态</label><el-select id="employee-status" v-model="filter.status" placeholder="全部状态" clearable @change="changeStatus">
          <el-option v-for="s in statuses" :key="s" :label="statusLabel(s)" :value="s" /></el-select></div>
        <el-button :icon="Refresh" :loading="loading" @click="loadTickets">刷新</el-button>
      </div>
      <p class="list-caption">共 {{ loading || listError ? '—' : total }} 项 · 第 {{ page }} 页 · 搜索仅匹配当前页已加载的工单</p>
      <div v-if="loading" class="state-panel" role="status">正在加载工单…</div>
      <div v-else-if="listError" class="state-panel" role="alert"><h2>工单暂时无法加载</h2><p>{{ listError }}</p><el-button @click="loadTickets">重试</el-button></div>
      <div v-else-if="!tickets.length" class="state-panel"><h2>{{ filter.status ? '此状态下暂无工单' : '还没有工单' }}</h2><p>提交问题后，可在这里查看进度。</p><el-button type="primary" @click="setView('create')">提交新工单</el-button></div>
      <div v-else-if="!filteredTickets.length" class="state-panel"><h2>本页没有匹配的工单</h2><el-button @click="keyword = ''">清除搜索</el-button></div>
      <ul v-else class="ticket-list">
        <li v-for="t in filteredTickets" :key="t.ticket_id" class="ticket-row" :class="{ 'is-selected': selectedTicketId === t.ticket_id }">
          <button class="ticket-open" :aria-pressed="selectedTicketId === t.ticket_id"
              :aria-label="'查看工单 ' + t.ticket_id + ' ' + t.title" @click="openDetail(t)">
            <span class="ticket-id">{{ t.ticket_id }}</span><span class="ticket-title">{{ t.title }}</span>
            <span class="ticket-meta"><span>{{ t.category_name }}</span><span>{{ t.assignee_name ? '处理人：' + t.assignee_name : '等待分配' }}</span><time>{{ formatTime(t.created_at) }}</time></span>
          </button>
          <div class="ticket-signals"><el-tag :type="statusTagType(t.status)" size="small">{{ statusLabel(t.status) }}</el-tag><el-tag :type="priorityTagType(t.priority)" size="small" effect="plain">{{ priorityLabel(t.priority) }}优先级</el-tag><SlaBadge :ticket-id="t.ticket_id" mode="card" /></div>
          <span class="row-arrow" aria-hidden="true">→</span>
        </li>
      </ul>
      <el-pagination v-if="total > pageSize" v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" class="pagination" @current-change="loadTickets" />
    </section>

    <!-- 工单详情抽屉；选择状态由路由统一管理。 -->
    <el-drawer :model-value="detailVisible" :before-close="closeDetail" :title="'工单详情 · ' + selectedTicketId" size="min(760px, 100vw)" class="ticket-drawer" destroy-on-close>
      <template #header>
        <div class="drawer-heading"><el-button text @click="closeDetail">← 返回列表</el-button><span>工单详情 · {{ selectedTicketId }}</span></div>
      </template>
      <div v-if="detailLoading" class="state-panel" role="status">正在加载工单详情…</div>
      <div v-else-if="detailError" class="state-panel" role="alert"><p>{{ detailError }}</p><el-button @click="loadDetail()">重试详情</el-button></div>
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
          <el-descriptions-item v-if="detailTicket.location" label="位置">{{ detailTicket.location }}</el-descriptions-item>
          <el-descriptions-item label="问题描述" :span="2">{{ detailTicket.description }}</el-descriptions-item>
          <el-descriptions-item label="影响情况" :span="2">{{ detailTicket.impact_description }}</el-descriptions-item>
          <el-descriptions-item label="紧急说明" :span="2">{{ detailTicket.urgency_description }}</el-descriptions-item>
        </el-descriptions>

        <!-- SLA 计时 -->
        <SlaTimer :ticket-id="detailTicket.ticket_id" />

        <section v-if="detailTicket.status === 'PENDING_SUPPLEMENT'" class="action-card" aria-labelledby="supplement-heading">
          <h3 id="supplement-heading" class="action-title">补充信息</h3>
          <p id="supplement-help" class="list-caption">请根据流转记录中的要求补充信息，提交后工程师将继续处理。</p>
          <label for="supplement-remark" class="supplement-label">补充内容</label>
          <el-input
            id="supplement-remark"
            v-model="supplementRemark"
            type="textarea"
            :rows="4"
            :disabled="actionBusy"
            :aria-invalid="!!supplementError"
            :aria-describedby="supplementError ? 'supplement-help supplement-error' : 'supplement-help'"
            placeholder="填写补充说明、报错内容或排查结果"
          />
          <el-text v-if="supplementError" id="supplement-error" type="danger" role="alert" class="action-error">{{ supplementError }}</el-text>
          <el-button type="primary" :loading="actionBusy" :disabled="actionBusy || !supplementRemark.trim()" class="submit-row" @click="submitSupplement(detailTicket)">
            提交补充信息
          </el-button>
        </section>

        <!-- 验收操作 -->
        <section v-if="detailTicket.status === 'PENDING_ACCEPTANCE'" class="action-card">
          <h3 class="action-title">验收工单</h3>
          <el-space>
            <el-button type="success" :icon="CircleCheck" :loading="actionBusy" @click="acceptTicket(detailTicket)">
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
            <el-button type="danger" :icon="CircleClose" :loading="actionBusy" @click="rejectTicket(detailTicket)">
              驳回
            </el-button>
          </div>
          <el-text v-if="rejectError" type="danger" size="small">{{ rejectError }}</el-text>
        </section>

        <!-- 满意度评价 -->
        <section
          v-if="detailTicket.status === 'COMPLETED' && !detailTicket.rating_score"
          class="action-card"
        >
          <h3 class="action-title">满意度评价</h3>
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
            :disabled="!ratingScore" :loading="actionBusy"
            style="margin-top:12px"
            @click="submitRating(detailTicket)"
          >
            提交评价
          </el-button>
        </section>

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
        <section class="flow-card">
          <h3 class="action-title">流转记录</h3>
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
        </section>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  EditPen, Search, Refresh, SuccessFilled, CircleCheck, CircleClose
} from '@element-plus/icons-vue'
import { ticketApi, draftApi, categoryApi } from '../api/index.js'
import { consultationApi } from '../api/consultation.js'
import { useUserStore } from '../stores/user.js'
import SlaBadge from '../components/SlaBadge.vue'
import SlaTimer from '../components/SlaTimer.vue'

const userStore = useUserStore()
const route = useRoute()
const tab = computed(() => route.query.view === 'create' || (!route.query.view && route.query.session) ? 'create' : 'list')
function setView(view) {
  const { ticket, ...query } = route.query
  return router.push({ query: { ...query, view } })
}
// 末级分类从后端动态加载（PRD §10.1 分类目录）
const categories = ref([])
// 按当前工单性质过滤末级分类（PRD §10.1：分类目录按 nature 分组，SPEC 字段为 nature）
const filteredCategories = computed(() => categories.value.filter(c => c.ticket_nature === form.value.nature && c.status === 'ACTIVE'))
const natures = [
  { value: 'INCIDENT', label: '故障报修' },
  { value: 'SERVICE_REQUEST', label: '服务申请' }
]

const form = ref({
  nature: 'INCIDENT', category_id: '', title: '', description: '',
  impact_description: '', urgency_description: '', location: '', contact: '', asset_id: ''
})
const formRef = ref(null)
const submitting = ref(false)
const draftBanner = ref(false)
const sourceSession = ref('')
const localDraftBanner = ref(false)
const draftError = ref('')
const categoryError = ref('')
const prefillError = ref('')
let prefillRequest = 0
let draftRequest = 0
let applyingDraft = false
const localDraftKey = () => 'ticket_draft_local:' + userStore.userId
const draftSaved = ref(false)
const draftTime = ref('')
let draftTimer = null

// Element Plus 表单校验规则（保留原有校验语义）
const formRules = {
  nature: [{ required: true, message: '请选择工单性质', trigger: 'change' }],
  category_id: [{ required: true, message: '请选择问题分类', trigger: 'change' }],
  title: [
    { required: true, message: '请填写工单标题', trigger: 'blur' },
    { min: 1, max: 100, message: '工单标题 1~100 个字符', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请填写问题描述', trigger: 'blur' },
    { max: 5000, message: '问题描述不能超过 5000 个字符', trigger: 'blur' }
  ],
  impact_description: [
    { required: true, message: '请填写影响情况（接单时供工程师确认优先级）', trigger: 'blur' },
    { max: 2000, message: '影响情况不能超过 2000 个字符', trigger: 'blur' }
  ],
  urgency_description: [
    { required: true, message: '请填写紧急说明', trigger: 'blur' },
    { max: 2000, message: '紧急说明不能超过 2000 个字符', trigger: 'blur' }
  ]
}

// 工单列表
const tickets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10

// 状态筛选项（英文枚举，显示用 statusLabel 转中文）
const statuses = ['NEW', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_SUPPLEMENT', 'PENDING_EXTERNAL', 'PENDING_ACCEPTANCE', 'COMPLETED', 'CANCELLED', 'CLOSED']

const keyword = ref('')
const filteredTickets = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  return tickets.value.filter(t => !k || [t.ticket_id, t.title, t.assignee_name].some(value => String(value || '').toLowerCase().includes(k)))
})
const filter = ref({ status: '' })

// 详情
const detailTicket = ref(null)
const detailFlows = ref([])
const router = useRouter()
const selectedTicketId = computed(() => typeof route.query.ticket === 'string' ? route.query.ticket : '')
const detailVisible = computed(() => !!selectedTicketId.value)
const detailLoading = ref(false)
const detailError = ref('')
const loading = ref(true)
const listError = ref('')
let listRequest = 0
let detailRequest = 0
let disposed = false
let identityVersion = 0
let submitRequest = 0
const rejectReason = ref('')
const rejectError = ref('')
const ratingScore = ref(0)
const ratingComment = ref('')
const actionBusy = ref(false)
const supplementRemark = ref('')
const supplementError = ref('')

function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '' }

// 操作人兜底：流转记录里 SYSTEM（系统自动路由）无用户档案，显示为「系统」
function operatorLabel(operatorId) { return operatorId === 'SYSTEM' ? '系统' : (operatorId || '—') }



// 状态英文枚举 → 中文标签 + 颜色（PRD §9.2 九态）
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
function statusTagType(s) { return STATUS_TYPE[s] || 'info' }

// 优先级英文 → 中文 + 颜色
const PRIORITY_LABEL = { HIGH: '高', MEDIUM: '中', LOW: '低' }
const PRIORITY_TYPE = { HIGH: 'danger', MEDIUM: 'warning', LOW: 'info' }
function priorityLabel(p) { return PRIORITY_LABEL[p] || p }
function priorityTagType(p) { return PRIORITY_TYPE[p] || 'info' }

function flowTimelineType(status) {
  const map = {
    COMPLETED: 'success', PENDING_ACCEPTANCE: 'primary', IN_PROGRESS: 'primary',
    NEW: 'warning', ASSIGNED: 'primary', CANCELLED: 'info', CLOSED: 'info'
  }
  return map[status] || 'primary'
}

// 未满足条件时的实时提示
const submitHint = computed(() => {
  if (submitting.value) return ''
  const missing = []
  if (!form.value.category_id) missing.push('问题分类')
  const tLen = form.value.title.trim().length
  if (tLen === 0) missing.push('工单标题')
  else if (tLen > 100) missing.push('标题需在 100 字以内')
  const dLen = form.value.description.trim().length
  if (dLen < 10) missing.push(`问题描述（还需 ${10 - dLen} 字）`)
  if (!form.value.impact_description.trim()) missing.push('影响情况')
  if (!form.value.urgency_description.trim()) missing.push('紧急说明')
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
  if (disposed || submitting.value || !formRef.value) return
  // PRD §3.2：防重复点击 Debounce 3 秒
  if (Date.now() - lastSubmitAt.value < 3000) return
  const request = ++submitRequest
  const userId = userStore.userId
  const isCurrent = () => !disposed && request === submitRequest && userId === userStore.userId
  submitting.value = true
  clearTimeout(draftTimer)

  // Element Plus 表单校验
  try {
    await formRef.value.validate()
  } catch (e) {
    if (!isCurrent()) return
    submitting.value = false
    nextTick(() => {
      if (!isCurrent()) return
      const el = document.querySelector('.el-form-item.is-error')
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
    return
  }
  if (!isCurrent()) return

  if (!formToken.value) formToken.value = genClientToken()
  lastSubmitAt.value = Date.now()
  try {
    await ticketApi.create({
      nature: form.value.nature,
      category_id: form.value.category_id,
      title: form.value.title.trim(),
      description: form.value.description.trim(),
      impact_description: form.value.impact_description.trim(),
      urgency_description: form.value.urgency_description.trim(),
      location: form.value.location.trim() || null,
      contact: form.value.contact.trim() || null,
      asset_id: form.value.asset_id.trim() || null,
      source_session_id: sourceSession.value || null
    }, { headers: { 'Idempotency-Key': formToken.value } })
    if (!isCurrent()) return
    clearTimeout(draftTimer)
    ++draftRequest
    form.value = {
      nature: 'INCIDENT', category_id: '', title: '', description: '',
      impact_description: '', urgency_description: '', location: '', contact: '', asset_id: ''
    }
    formToken.value = genClientToken()
    sourceSession.value = ''
    try { localStorage.removeItem(localDraftKey()) } catch {}
    try { await draftApi.delete() } catch (e) { if (isCurrent()) ElMessage.warning('工单已提交，但服务端草稿清理失败：' + e.message) }
    if (!isCurrent()) return
    draftBanner.value = false
    localDraftBanner.value = false
    draftError.value = ''
    draftSaved.value = false
    ElMessage.success('工单提交成功！')
    const { session, view, ...query } = route.query
    await router.replace({ query })
    if (!isCurrent()) return
    page.value = 1
    filter.value.status = ''
    loadTickets()
  } catch (e) {
    if (isCurrent()) ElMessage.error('提交失败：' + e.message)
  } finally {
    if (isCurrent()) submitting.value = false
  }
}

// 草稿使用服务端标准 payload；本地保存明确显示失败原因，不伪装服务端成功。
function draftPayload() {
  const { nature, ...fields } = form.value
  return { ...fields, ticket_nature: nature, source_session_id: sourceSession.value || null }
}
function applyDraftPayload(payload) {
  applyingDraft = true
  const nature = payload.ticket_nature || payload.nature || 'INCIDENT'
  form.value = {
    nature, category_id: '', title: payload.title || '', description: payload.description || '',
    impact_description: payload.impact_description || '', urgency_description: payload.urgency_description || '',
    location: payload.location || '', contact: payload.contact || '', asset_id: payload.asset_id || ''
  }
  if (categories.value.some(c => c.category_id === payload.category_id && c.ticket_nature === nature && c.status === 'ACTIVE')) {
    form.value.category_id = payload.category_id
  }
  sourceSession.value = payload.source_session_id || ''
  nextTick(() => { applyingDraft = false })
}
async function saveDraft() {
  if (disposed || submitting.value) return
  const payload = draftPayload()
  const userId = userStore.userId
  const request = ++draftRequest
  const key = localDraftKey()
  try {
    await draftApi.save(payload)
    if (disposed || request !== draftRequest || userId !== userStore.userId) return
    draftSaved.value = true
    draftError.value = ''
    draftTime.value = new Date().toLocaleTimeString('zh-CN')
    try { localStorage.removeItem(key) } catch {}
    localDraftBanner.value = false
  } catch (e) {
    if (disposed || request !== draftRequest || userId !== userStore.userId) return
    draftSaved.value = false
    try {
      localStorage.setItem(key, JSON.stringify(payload))
      localDraftBanner.value = true
      draftError.value = '服务端草稿保存失败：' + e.message + '；已保存在此设备，可恢复后重试。'
    } catch {
      draftError.value = '草稿未保存：' + e.message + '；此设备也无法保存，请保留当前页面。'
    }
  }
}
async function restoreDraft() {
  const userId = userStore.userId
  try {
    const res = await draftApi.get()
    if (disposed || userId !== userStore.userId) return
    if (res.data?.payload) applyDraftPayload(res.data.payload)
    draftBanner.value = false
  } catch (e) { draftError.value = '草稿恢复失败：' + e.message }
}
function restoreLocalDraft() {
  try {
    const payload = JSON.parse(localStorage.getItem(localDraftKey()))
    if (payload) applyDraftPayload(payload)
    localDraftBanner.value = false
  } catch (e) { draftError.value = '本地草稿无法恢复：' + e.message }
}
async function clearDraft() {
  try { await draftApi.delete(); draftBanner.value = false }
  catch (e) { draftError.value = '草稿清理失败：' + e.message }
}
async function loadCategories() {
  const userId = userStore.userId
  categoryError.value = ''
  try {
    const res = await categoryApi.leaf()
    if (!disposed && userId === userStore.userId) categories.value = res.data || []
  } catch (e) {
    if (!disposed && userId === userStore.userId) categoryError.value = '分类加载失败：' + e.message
  }
}
async function loadConsultPrefill(sessionId) {
  if (typeof sessionId !== 'string' || !sessionId) return
  const request = ++prefillRequest
  const userId = userStore.userId
  prefillError.value = ''
  try {
    const data = await consultationApi.ticketDraft(sessionId)
    if (disposed || request !== prefillRequest || userId !== userStore.userId) return
    const category = categories.value.find(c => c.category_id === data.category_id && c.status === 'ACTIVE')
    applyDraftPayload({ ...data, ticket_nature: category?.ticket_nature || 'INCIDENT',
      source_session_id: data.convert_allowed ? sessionId : '' })
  } catch (e) {
    if (!disposed && request === prefillRequest) prefillError.value = '咨询内容加载失败：' + e.message
  }
}

// 加载工单列表
async function loadTickets() {
  const request = ++listRequest
  loading.value = true
  listError.value = ''
  try {
    const params = { creator_id: userStore.userId, page: page.value, page_size: pageSize }
    if (filter.value.status) params.status = filter.value.status
    const res = await ticketApi.list(params)
    if (disposed || request !== listRequest) return
    tickets.value = res.data.list
    total.value = res.data.total
  } catch (e) {
    if (!disposed && request === listRequest) listError.value = e.message || '工单加载失败'
  } finally {
    if (!disposed && request === listRequest) loading.value = false
  }
}
function changeStatus() { page.value = 1; loadTickets() }

// 查看详情
function openDetail(ticket) {
  if (selectedTicketId.value === ticket.ticket_id) return loadDetail(ticket.ticket_id)
  return router.push({ query: { ...route.query, ticket: ticket.ticket_id } })
}
function closeDetail() {
  if (!selectedTicketId.value) return
  const { ticket, ...query } = route.query
  return router.replace({ query })
}
async function loadDetail(id = selectedTicketId.value) {
  const request = ++detailRequest
  detailTicket.value = null
  detailFlows.value = []
  detailError.value = ''
  detailLoading.value = !!id
  rejectReason.value = ''; rejectError.value = ''; ratingScore.value = 0; ratingComment.value = ''
  supplementRemark.value = ''; supplementError.value = ''
  if (!id) return
  try {
    const res = await ticketApi.detail(id)
    if (disposed || request !== detailRequest || selectedTicketId.value !== id) return
    detailTicket.value = res.data.ticket
    detailFlows.value = res.data.flow_logs || []
  } catch (e) {
    if (!disposed && request === detailRequest) detailError.value = e.message || '详情加载失败'
  } finally {
    if (!disposed && request === detailRequest) detailLoading.value = false
  }
}
watch(selectedTicketId, id => loadDetail(id), { immediate: true, flush: 'sync' })

async function runTicketAction(t, action, successMessage) {
  if (disposed || actionBusy.value || detailTicket.value?.ticket_id !== t.ticket_id || selectedTicketId.value !== t.ticket_id) return
  const userId = userStore.userId
  const identity = identityVersion
  const request = detailRequest
  actionBusy.value = true
  try {
    await action()
    if (disposed || userId !== userStore.userId || identity !== identityVersion) return
    ElMessage.success(successMessage)
    if (selectedTicketId.value === t.ticket_id && request === detailRequest) await loadDetail(t.ticket_id)
    loadTickets()
  } catch (e) {
    if (!disposed && identity === identityVersion && request === detailRequest) ElMessage.error(e.message)
  } finally { if (!disposed && identity === identityVersion) actionBusy.value = false }
}
async function submitSupplement(t) {
  if (actionBusy.value || detailTicket.value?.status !== 'PENDING_SUPPLEMENT' || detailTicket.value?.ticket_id !== t.ticket_id) return
  supplementError.value = ''
  const remark = supplementRemark.value.trim()
  if (!remark) { supplementError.value = '请填写补充内容'; return }
  return runTicketAction(t, () => ticketApi.action(t.ticket_id, { action: 'supply_info', remark }), '补充信息已提交，工程师将继续处理')
}
// 验收后保留详情，直接进入评价。
async function acceptTicket(t) {
  if (actionBusy.value) return
  const userId = userStore.userId
  const request = detailRequest
  try {
    await ElMessageBox.confirm('确认此工单已解决？', '验收确认', {
      confirmButtonText: '确认解决', cancelButtonText: '再想想', type: 'success'
    })
  } catch { return }
  if (disposed || userId !== userStore.userId || request !== detailRequest) return
  return runTicketAction(t, () => ticketApi.action(t.ticket_id, { action: 'accept' }), '验收通过，请评价本次服务')
}
async function rejectTicket(t) {
  rejectError.value = ''
  const reason = rejectReason.value.trim()
  if (reason.length < 10) { rejectError.value = '驳回原因至少 10 个字符'; return }
  return runTicketAction(t, () => ticketApi.action(t.ticket_id, { action: 'reject', remark: reason }), '已驳回，工单退回处理中')
}
async function submitRating(t) {
  if (!ratingScore.value) return
  const payload = { score: ratingScore.value, comment: ratingComment.value }
  return runTicketAction(t, () => ticketApi.rating(t.ticket_id, payload), '评价成功！')
}

// 清空/提交表单同时取消旧定时器，避免提交后重新保存空草稿。
watch(form, () => {
  clearTimeout(draftTimer)
  draftSaved.value = false
  if (applyingDraft || submitting.value || !Object.values(form.value).some((v, i) => i > 1 && String(v).trim())) return
  draftTimer = setTimeout(saveDraft, 30000)
}, { deep: true })
watch(() => form.value.nature, () => {
  if (!filteredCategories.value.some(c => c.category_id === form.value.category_id)) form.value.category_id = ''
})
async function initializeForm() {
  const userId = userStore.userId
  await loadCategories()
  if (disposed || userId !== userStore.userId) return
  if (route.query.session) await loadConsultPrefill(route.query.session)
  try {
    const draft = await draftApi.get()
    if (!disposed && userId === userStore.userId) draftBanner.value = !!draft.data?.payload
  } catch (e) {
    if (!disposed && userId === userStore.userId) draftError.value = '无法检查服务端草稿：' + e.message
  }
  try { localDraftBanner.value = !!localStorage.getItem(localDraftKey()) } catch {}
}
onMounted(() => { loadTickets(); initializeForm() })
watch(() => route.query.session, id => {
  ++prefillRequest
  sourceSession.value = ''
  prefillError.value = ''
  if (id) loadConsultPrefill(id)
}, { flush: 'sync' })
watch(() => userStore.userId, () => {
  ++identityVersion; ++submitRequest; ++listRequest; ++detailRequest; ++prefillRequest; ++draftRequest
  submitting.value = false; actionBusy.value = false
  formToken.value = ''; lastSubmitAt.value = 0
  clearTimeout(draftTimer)
  tickets.value = []; total.value = 0; page.value = 1
  detailTicket.value = null; detailFlows.value = []
  draftBanner.value = false; localDraftBanner.value = false; draftError.value = ''
  applyDraftPayload({})
  closeDetail()
  if (userStore.userId) { loadTickets(); initializeForm() }
}, { flush: 'sync' })

onUnmounted(() => { disposed = true; ++listRequest; ++detailRequest; ++prefillRequest; ++draftRequest; clearTimeout(draftTimer) })
</script>

<style scoped>

.page-head { display:flex; align-items:center; justify-content:space-between; gap:20px; margin-bottom:28px; }
.eyebrow { margin:0 0 8px; color:var(--el-color-primary); font-size:12px; font-weight:650; letter-spacing:.12em; }
.page-title { margin:0; font-size:clamp(25px, 2.6vw, 34px); font-weight:650; letter-spacing:-.035em; color:var(--el-text-color-primary); }
.page-sub { margin:10px 0 0; font-size:14px; line-height:1.6; color:var(--el-text-color-secondary); }
.head-actions { display:flex; align-items:center; gap:12px; }
.list-toolbar { display:flex; align-items:flex-end; gap:16px; padding:18px 0; }
.search-field { width:min(360px, 100%); }
.filter-field { width:180px; }
.list-toolbar label { display:block; margin-bottom:7px; font-size:12px; font-weight:600; color:var(--el-text-color-regular); }
.list-caption { color:var(--el-text-color-secondary); font-size:12px; line-height:1.7; margin:0 0 14px; }
.ticket-list { padding:0; margin:0; list-style:none; border-top:1px solid var(--el-border-color); }
.ticket-row { display:flex; align-items:center; gap:20px; padding:20px 12px; border-bottom:1px solid var(--el-border-color-lighter); transition:background .15s; }
.ticket-row:hover, .ticket-row:focus-within { background:var(--el-fill-color-light); }
.ticket-row.is-selected { background:var(--el-color-primary-light-9); box-shadow:inset 3px 0 var(--el-color-primary); }
.ticket-row:focus-visible, .ticket-open:focus-visible { outline:2px solid var(--el-color-primary); outline-offset:3px; border-radius:4px; }
.ticket-main, .ticket-open { flex:1; min-width:0; }
.ticket-open { display:block; border:0; padding:0; background:transparent; font:inherit; text-align:left; cursor:pointer; color:inherit; }
.ticket-id { color:var(--el-color-primary); font-family:ui-monospace,monospace; font-size:12px; font-weight:600; }
.ticket-title { display:block; margin:7px 0; font-size:15px; font-weight:600; line-height:1.5; overflow-wrap:anywhere; color:var(--el-text-color-primary); }
.ticket-meta { display:flex; gap:8px 18px; flex-wrap:wrap; color:var(--el-text-color-secondary); font-size:12px; line-height:1.6; }
.ticket-signals { display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-end; gap:8px; max-width:280px; }
.row-arrow { color:var(--el-color-primary); }
.state-panel { padding:54px 20px; text-align:center; border-block:1px solid var(--el-border-color-lighter); color:var(--el-text-color-secondary); font-size:14px; line-height:1.7; }
.state-panel h2 { margin:0 0 8px; font-size:18px; font-weight:600; color:var(--el-text-color-primary); }
.state-panel p { margin:8px 0 20px; overflow-wrap:anywhere; }
.pagination { padding-top:22px; justify-content:flex-end; overflow-x:auto; }
.status-tabs :deep(.el-tabs__item) { font-size:13px; }
.drawer-heading { display:flex; gap:12px; align-items:center; flex-wrap:wrap; font-size:13px; color:var(--el-text-color-secondary); }
.detail-desc { margin-bottom:22px; }
.detail-desc :deep(.el-descriptions__cell) { overflow-wrap:anywhere; white-space:pre-wrap; }
.action-card, .flow-card { margin-top:24px; padding-top:22px; border-top:1px solid var(--el-border-color); }
.action-title { margin:0 0 16px; color:var(--el-text-color-primary); font-size:16px; font-weight:600; }
.supplement-label { display:block; margin-bottom:8px; font-size:14px; font-weight:600; }
.action-row { display:flex; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px; }
.remark-input { flex:1; min-width:200px; }
.submit-row { margin-top:20px; }
.action-error { display:block; margin-top:10px; }
.flow-content { display:flex; gap:10px; flex-wrap:wrap; align-items:center; font-size:13px; }
.flow-operator { color:var(--el-text-color-secondary); }
.flow-remark { overflow-wrap:anywhere; }
.create-section { max-width:960px; border-top:1px solid var(--el-border-color); padding-top:24px; }
.draft-alert { margin-bottom:18px; }
.ticket-form :deep(.el-form-item__label) { font-weight:600; }
.required { color:var(--el-color-danger); }
.char-count { margin-left:10px; font-size:12px; font-weight:400; color:var(--el-text-color-secondary); }
.reject-area { display:flex; gap:10px; }
@media (max-width:760px) {
  .page-head { align-items:flex-start; flex-wrap:wrap; margin-bottom:20px; gap:16px; }
  .head-actions { flex-wrap:wrap; }
  .list-toolbar { flex-wrap:wrap; gap:12px; }
  .search-field { width:100%; }
  .filter-field { flex:1; }
  .ticket-row { gap:12px; padding:16px 4px; flex-wrap:wrap; }
  .ticket-main, .ticket-open { flex-basis:100%; }
  .ticket-signals { justify-content:flex-start; max-width:none; flex:1; }
  .ticket-meta { gap:6px 12px; }
  .action-row :deep(.el-button-group) { display:flex; flex-wrap:wrap; gap:8px; }
  .reject-area { flex-wrap:wrap; }
  .drawer-heading { gap:6px; }
}
@media (prefers-reduced-motion:reduce) { .ticket-row { transition:none; } }

</style>
