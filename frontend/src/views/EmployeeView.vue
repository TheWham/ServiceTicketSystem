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

      <!-- 咨询转工单预填横幅(PRD 9.1:预填标题/分类/描述/会话摘要,员工确认后提交) -->
      <el-alert v-if="sourceSession" type="info" :closable="false" class="draft-alert">
        <template #title>
          🔗 从咨询 {{ sourceSession }} 转入：表单已按会话内容预填，请检查修改后提交；
          提交成功后咨询将转为正式工单并关联完整上下文。
        </template>
      </el-alert>

      <!-- 本地草稿横幅(PRD 10.4:服务端保存失败时暂存浏览器本地,恢复网络后可恢复) -->
      <el-alert v-if="localDraftBanner" type="warning" :closable="false" class="draft-alert">
        <template #title>
          ⚠️ 检测到网络中断时暂存在本地的草稿，
          <el-link type="primary" @click="restoreLocalDraft">点击恢复</el-link>
          <el-link type="info" style="margin-left:12px" @click="clearLocalDraft">忽略</el-link>
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
            <span class="char-count">{{ form.title.length }}/100</span>
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
          <!-- 工单性质(PRD 10.2 必填:INCIDENT/SERVICE_REQUEST) -->
          <el-col :span="12">
            <el-form-item prop="ticket_nature" label="工单性质">
              <el-radio-group v-model="form.ticket_nature">
                <el-radio-button value="INCIDENT">故障报修</el-radio-button>
                <el-radio-button value="SERVICE_REQUEST">服务申请</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>

          <!-- 末级分类(PRD 10.1:仅末级可提交工单) -->
          <el-col :span="12">
            <el-form-item prop="category_id" label="问题分类">
              <el-select v-model="form.category_id" placeholder="请选择分类" style="width:100%">
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
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
            :rows="5"
            maxlength="5000"
            show-word-limit
            placeholder="请详细描述问题：何时开始、报错原文、已尝试的操作..."
          />
        </el-form-item>

        <!-- 影响情况(PRD 10.2 必填,供工程师确认影响范围) -->
        <el-form-item prop="impact_description">
          <template #label>
            影响情况 <span class="required">*</span>
            <span class="char-count">{{ form.impact_description.length }}/2000</span>
          </template>
          <el-input
            v-model="form.impact_description"
            type="textarea"
            :rows="2"
            maxlength="2000"
            show-word-limit
            placeholder="影响多少人/哪个部门、是否阻塞业务、有无替代方案..."
          />
        </el-form-item>

        <!-- 紧急说明(PRD 10.2 必填,供工程师确认紧急程度) -->
        <el-form-item prop="urgency_description">
          <template #label>
            紧急说明 <span class="required">*</span>
            <span class="char-count">{{ form.urgency_description.length }}/2000</span>
          </template>
          <el-input
            v-model="form.urgency_description"
            type="textarea"
            :rows="2"
            maxlength="2000"
            show-word-limit
            placeholder="为什么紧急、期望何时处理、是否涉及安全或数据风险..."
          />
        </el-form-item>

        <el-row :gutter="16">
          <!-- 办公地点(硬件现场服务建议填写) -->
          <el-col :span="8">
            <el-form-item label="办公地点">
              <el-input v-model="form.location" maxlength="255" placeholder="如：3 号楼 402（选填）" clearable />
            </el-form-item>
          </el-col>
          <!-- 本次联系方式(默认来自身份源) -->
          <el-col :span="8">
            <el-form-item label="本次联系方式">
              <el-input v-model="form.contact" maxlength="255" placeholder="默认取你的姓名，可修改" clearable />
            </el-form-item>
          </el-col>
          <!-- 资产编号(硬件分类建议填写) -->
          <el-col :span="8">
            <el-form-item label="资产编号">
              <el-input v-model="form.asset_id" maxlength="64" placeholder="如：PC-00381（选填）" clearable />
            </el-form-item>
          </el-col>
        </el-row>

        <el-alert type="info" :closable="false" class="priority-note">
          <template #title>
            优先级由系统按影响情况和紧急程度矩阵确认（新工单暂按中优先级计时，工程师接单时核定），
            无需你手动选择。
          </template>
        </el-alert>

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
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  EditPen, List, WarningFilled, SuccessFilled, CircleCheck, CircleClose
} from '@element-plus/icons-vue'
import { ticketApi, draftApi } from '../api/index.js'
import { consultationApi } from '../api/consultation.js'
import { useUserStore } from '../stores/user.js'

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const tab = ref('create')
// 末级分类(it_ticket.ticket_category 种子,PRD 10.1)
const categories = [
  { id: 'CAT-HW', name: '硬件' },
  { id: 'CAT-SW', name: '软件' },
  { id: 'CAT-NW', name: '网络' },
  { id: 'CAT-ACCT', name: '账号权限' },
  { id: 'CAT-OTH', name: '其他' }
]
const statuses = ['待处理', '处理中', '待补充', '待外部', '待验收', '已完成', '已取消']

// 咨询分类 → 工单末级分类(咨询转工单预填)
const CONSULT_CATEGORY_MAP = {
  'CAT-IT-DEVICE': 'CAT-HW',
  'CAT-IT-NETWORK': 'CAT-NW',
  'CAT-IT-ACCOUNT': 'CAT-ACCT'
}

function emptyForm() {
  return {
    ticket_nature: 'INCIDENT',
    category_id: '',
    title: '',
    description: '',
    impact_description: '',
    urgency_description: '',
    location: '',
    contact: userStore.currentUser?.name || '',
    asset_id: ''
  }
}

const form = ref(emptyForm())
const formRef = ref(null)
const submitting = ref(false)
const draftBanner = ref(false)
const draftSaved = ref(false)
const draftTime = ref('')
let draftTimer = null

// 咨询转工单:来源会话(PRD 9.1,提交时写入 source_session_id)
const sourceSession = ref('')
// 本地草稿横幅(PRD 10.4:服务端保存失败时暂存浏览器本地)
const localDraftBanner = ref(false)
const LOCAL_DRAFT_KEY = 'ticket_draft_local'

// Element Plus 表单校验规则(spec 05 TicketCreate:必填六项 + 长度约束)
const formRules = {
  ticket_nature: [{ required: true, message: '请选择工单性质', trigger: 'change' }],
  category_id: [{ required: true, message: '请选择问题分类', trigger: 'change' }],
  title: [
    { required: true, message: '请填写工单标题', trigger: 'blur' },
    { max: 100, message: '工单标题不能超过 100 个字符', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请填写问题描述', trigger: 'blur' },
    { min: 10, message: '请至少填写 10 个字，说明何时开始、报错原文、已尝试的操作', trigger: 'blur' },
    { max: 5000, message: '问题描述不能超过 5000 个字符', trigger: 'blur' }
  ],
  impact_description: [
    { required: true, message: '请填写影响情况（影响范围、有无替代方案）', trigger: 'blur' },
    { max: 2000, message: '影响情况不能超过 2000 个字符', trigger: 'blur' }
  ],
  urgency_description: [
    { required: true, message: '请填写紧急说明（为什么紧急、期望何时处理）', trigger: 'blur' },
    { max: 2000, message: '紧急说明不能超过 2000 个字符', trigger: 'blur' }
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

// 未满足条件时的实时提示(spec 05 TicketCreate 必填六项)
const submitHint = computed(() => {
  if (submitting.value) return ''
  const missing = []
  if (!form.value.ticket_nature) missing.push('工单性质')
  if (!form.value.category_id) missing.push('问题分类')
  const tLen = form.value.title.trim().length
  if (tLen === 0) missing.push('工单标题')
  else if (tLen > 100) missing.push('标题需在 100 字以内')
  const dLen = form.value.description.trim().length
  if (dLen === 0) missing.push('问题描述')
  else if (dLen < 10) missing.push(`问题描述（还需 ${10 - dLen} 字）`)
  else if (dLen > 5000) missing.push('问题描述需在 5000 字以内')
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
    // spec 05 TicketCreate:必填六项 + 选填;幂等键走 Idempotency-Key 头(RD-002/AC-07)
    await ticketApi.create({
      ticket_nature: form.value.ticket_nature,
      category_id: form.value.category_id,
      title: form.value.title.trim(),
      description: form.value.description.trim(),
      impact_description: form.value.impact_description.trim(),
      urgency_description: form.value.urgency_description.trim(),
      location: form.value.location.trim() || null,
      contact: form.value.contact.trim() || null,
      asset_id: form.value.asset_id.trim() || null,
      // 咨询转工单:来源咨询会话,后端建单成功后回调咨询侧转 CONVERTED_TO_TICKET
      source_session_id: sourceSession.value || null
    }, { headers: { 'Idempotency-Key': formToken.value } })
    form.value = emptyForm()
    formToken.value = genClientToken()
    draftApi.delete(draftApi.ensureDraftId()).catch(() => {})
    clearLocalDraft()
    draftBanner.value = false
    draftSaved.value = false
    if (sourceSession.value) {
      // 咨询转单:工单侧回调成功后咨询转 CONVERTED_TO_TICKET(终态,不可恢复)
      sourceSession.value = ''
      router.replace({ query: {} })
      ElMessage.success('工单提交成功，原咨询已转为正式工单！')
    } else {
      ElMessage.success('工单提交成功！')
    }
    tab.value = 'list'
    loadTickets()
  } catch (e) {
    ElMessage.error('提交失败：' + e.message)
  } finally {
    submitting.value = false
  }
}

// 草稿(spec 05 saveTicketDraft:PUT /ticket-drafts/{id},残缺字段也允许保存)
function draftPayload() {
  return {
    ticket_nature: form.value.ticket_nature,
    category_id: form.value.category_id,
    title: form.value.title,
    description: form.value.description,
    impact_description: form.value.impact_description,
    urgency_description: form.value.urgency_description,
    location: form.value.location,
    contact: form.value.contact,
    asset_id: form.value.asset_id,
    source_session_id: sourceSession.value || null
  }
}

async function saveDraft() {
  try {
    await draftApi.save(draftApi.ensureDraftId(), { payload: draftPayload() })
    draftSaved.value = true
    draftTime.value = new Date().toLocaleTimeString('zh-CN')
    // 服务端保存成功,本地暂存不再需要
    localStorage.removeItem(LOCAL_DRAFT_KEY)
  } catch (e) {
    // PRD 10.4:服务端保存失败时暂存浏览器本地,恢复网络后可恢复
    try {
      localStorage.setItem(LOCAL_DRAFT_KEY, JSON.stringify(draftPayload()))
      localDraftBanner.value = true
    } catch (storageError) { /* 本地存储不可用则放弃 */ }
  }
}

/** 把草稿 payload 应用到表单(残缺字段容错)。 */
function applyDraftPayload(p) {
  form.value = {
    ticket_nature: ['INCIDENT', 'SERVICE_REQUEST'].includes(p.ticket_nature) ? p.ticket_nature : 'INCIDENT',
    category_id: categories.some(c => c.id === p.category_id) ? p.category_id : '',
    title: p.title || '',
    description: p.description || '',
    impact_description: p.impact_description || '',
    urgency_description: p.urgency_description || '',
    location: p.location || '',
    contact: p.contact || userStore.currentUser?.name || '',
    asset_id: p.asset_id || ''
  }
  if (p.source_session_id) sourceSession.value = p.source_session_id
}

async function restoreDraft() {
  try {
    const body = await draftApi.get(draftApi.ensureDraftId())
    if (body?.data?.payload) applyDraftPayload(body.data.payload)
    draftBanner.value = false
  } catch (e) {
    ElMessage.error('恢复草稿失败：' + e.message)
  }
}

function clearDraft() {
  draftApi.delete(draftApi.ensureDraftId()).catch(() => {})
  draftBanner.value = false
}

// 咨询转工单预填(OpenAPI 05 getTicketDraftFromConsultation)
async function loadConsultPrefill(sessionId) {
  try {
    const draft = await consultationApi.ticketDraft(sessionId)
    form.value.title = draft.title || ''
    form.value.description = draft.description || ''
    form.value.impact_description = draft.summary ? `来自咨询会话摘要：\n${draft.summary}` : ''
    form.value.category_id = CONSULT_CATEGORY_MAP[draft.category_id] || ''
    sourceSession.value = sessionId
    draftBanner.value = false // 咨询预填优先于服务端草稿
    tab.value = 'create'
    if (!draft.convert_allowed) {
      ElMessage.warning('该咨询已结束，仅预填会话内容供参考')
    }
  } catch (e) {
    ElMessage.error('加载咨询预填失败：' + e.message)
  }
}

// 本地草稿(PRD 10.4:暂存/恢复)
function readLocalDraft() {
  try {
    return JSON.parse(localStorage.getItem(LOCAL_DRAFT_KEY) || 'null')
  } catch (e) {
    return null
  }
}
function restoreLocalDraft() {
  const d = readLocalDraft()
  if (d) applyDraftPayload(d)
  clearLocalDraft()
}
function clearLocalDraft() {
  localStorage.removeItem(LOCAL_DRAFT_KEY)
  localDraftBanner.value = false
}

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
  if (route.query.session) {
    // 咨询转工单:从智能客服/工程师快捷入口跳入,带会话预填
    await loadConsultPrefill(String(route.query.session))
  } else {
    // PRD 10.4:登录过期后重新登录应提示恢复草稿
    try {
      const body = await draftApi.get(draftApi.ensureDraftId())
      if (body?.data?.payload && (body.data.payload.description || body.data.payload.title)) {
        draftBanner.value = true
      } else if (readLocalDraft()) {
        localDraftBanner.value = true
      }
    } catch (e) {
      // 服务端草稿不可用时仍提示本地暂存(PRD 10.4)
      if (readLocalDraft()) localDraftBanner.value = true
    }
  }
  loadTickets()
})

// 悬浮客服对话框在 /employee 页面内再次点击提单入口时,仅 query 变化
watch(() => route.query.session, (v) => {
  if (v && v !== sourceSession.value) loadConsultPrefill(String(v))
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
.priority-note { margin-bottom: 8px; }

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
