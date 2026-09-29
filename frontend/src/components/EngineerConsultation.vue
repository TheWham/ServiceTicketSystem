<template>
  <el-drawer :model-value="visible" title="当前咨询" size="760px"
             :append-to-body="true" :close-on-click-modal="false"
             @update:model-value="v => emit('update:visible', v)">
    <div class="eng-consult">
      <!-- ===== 左:咨询列表 ===== -->
      <div class="session-pane">
        <div class="pane-head">
          <span>进行中</span>
          <el-tag size="small" effect="plain" type="primary">{{ activeSessions.length }}</el-tag>
        </div>
        <el-scrollbar class="pane-body">
          <el-empty v-if="activeSessions.length === 0" description="暂无进行中的咨询" :image-size="56" />
          <div v-for="s in activeSessions" :key="s.session_id"
               class="session-item" :class="{ selected: selectedId === s.session_id }"
               @click="openSession(s.session_id)">
            <div class="applicant">{{ applicantLabel(s) }}</div>
            <div class="session-top">
              <span class="session-id">{{ s.session_id }}</span>
              <el-tag :type="statusMeta(s.status).type" size="small" effect="light">
                {{ statusMeta(s.status).label }}
              </el-tag>
            </div>
            <div class="session-preview">{{ previewOf(s.session_id) }}</div>
          </div>

          <template v-if="endedSessions.length">
            <div class="pane-head pane-head-end">
              <span>已结束</span>
              <el-tag size="small" effect="plain" type="info">{{ endedSessions.length }}</el-tag>
            </div>
            <div v-for="s in endedSessions" :key="s.session_id"
                 class="session-item ended" :class="{ selected: selectedId === s.session_id }"
                 @click="openSession(s.session_id)">
              <div class="applicant">{{ applicantLabel(s) }}</div>
              <div class="session-top">
                <span class="session-id">{{ s.session_id }}</span>
                <el-tag :type="statusMeta(s.status).type" size="small" effect="plain">
                  {{ statusMeta(s.status).label }}
                </el-tag>
              </div>
            </div>
          </template>
        </el-scrollbar>
        <div class="pane-tip">列表每 10 秒自动刷新，新分配的咨询会自动出现</div>
      </div>

      <!-- ===== 右:聊天窗 ===== -->
      <div class="chat-pane">
        <template v-if="selected">
          <div class="chat-head">
            <div>
              <div class="applicant">申请人：{{ applicantLabel(selected) }}</div>
              <div class="chat-head-title">
              <span class="session-id">{{ selected.session_id }}</span>
              <el-tag :type="statusMeta(selected.status).type" size="small" effect="light">
                {{ statusMeta(selected.status).label }}
              </el-tag>
              </div>
            </div>
            <el-button text :icon="Refresh" :loading="loadingMessages" @click="reloadSelected" />
          </div>

          <!-- 状态横幅 -->
          <el-alert v-if="selected.status === 'WAITING_ENGINEER'" type="warning" :closable="false"
                    class="state-banner">
            <template #title>
              等待你的首次有效回复：发送第一条消息即完成接入（10 个工作分钟响应 SLA，打开会话不算响应）。
            </template>
          </el-alert>
          <el-alert v-else-if="selected.status === 'PENDING_CONFIRMATION'" type="success" :closable="false"
                    class="state-banner">
            <template #title>
              已提交解决结论，等待员工确认。员工回复未解决时咨询会自动回到处理中。
            </template>
          </el-alert>
          <el-alert v-else-if="selected.status === 'RESOLVED'" type="info" :closable="false"
                    class="state-banner">
            <template #title>员工已确认解决。24 小时内员工可恢复咨询，系统会优先分配给你。</template>
          </el-alert>
          <el-alert v-else-if="selected.status === 'CLOSED'" type="info" :closable="false" class="state-banner">
            <template #title>员工已主动结束对话，会话已断开，仅可查看历史消息。</template>
          </el-alert>
          <el-alert v-else-if="isTerminal" type="info" :closable="false" class="state-banner">
            <template #title>该咨询已结束，仅可查看历史消息。</template>
          </el-alert>

          <!-- 消息流(含员工与 AI 的此前对话,PRD 13.1) -->
          <div ref="scrollRef" class="chat-body" v-loading="loadingMessages">
            <div v-for="msg in messages" :key="msg.id" class="msg-row" :class="rowClass(msg)">
              <div class="msg-avatar" :class="'avatar-' + msg.senderType.toLowerCase()">
                {{ avatarOf(msg.senderType) }}
              </div>
              <div class="msg-main">
                <div class="msg-meta">
                  <span class="msg-sender">{{ senderLabel(msg) }}</span>
                  <span class="msg-time">{{ formatTime(msg.sentAt) }}</span>
                </div>
                <div class="msg-bubble" :class="bubbleClass(msg)">
                  <!-- 工程师提单快捷入口消息,渲染为小卡片 -->
                  <template v-if="isTicketEntry(msg)">
                    <div class="ticket-entry-sent">
                      <el-icon><Tickets /></el-icon>
                      <span>已发送提交工单快捷入口，等待员工确认表单后提交</span>
                    </div>
                  </template>
                  <template v-else>
                    <div class="msg-text">{{ msg.content }}</div>
                    <div v-if="msg.generalAnswer" class="general-answer-note">AI 通用建议 · 无知识库引用</div>
                    <!-- AI 回答的引用来源(人工接手后可查看) -->
                    <div v-if="msg.citations && msg.citations.length" class="citations">
                      <div class="citations-title">
                        <el-icon><Document /></el-icon> 依据以下已发布知识
                      </div>
                      <el-popover v-for="c in msg.citations" :key="c.versionId"
                                  placement="top" :width="340" trigger="hover">
                        <template #reference>
                          <el-tag class="citation-tag" effect="plain" size="small">{{ c.title }}</el-tag>
                        </template>
                        <div class="citation-pop">
                          <div class="citation-pop-title">{{ c.title }}</div>
                          <div class="citation-pop-snippet">{{ c.snippet }}</div>
                        </div>
                      </el-popover>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <!-- 输入区 -->
          <div v-if="!isTerminal" class="chat-input">
            <el-input v-model="draft" type="textarea" :rows="3" resize="none"
                      maxlength="12000" show-word-limit :disabled="sending"
                      :placeholder="inputPlaceholder"
                      @keydown.enter.exact.prevent="send" />
            <div class="chat-actions">
              <div class="chat-actions-left">
                <el-button v-if="selected.status === 'HUMAN_ACTIVE'" type="success"
                           :icon="CircleCheck" :disabled="sending"
                           @click="submitResolution">
                  提交解决结论
                </el-button>
                <!-- PRD 9.1:人工咨询中由工程师发送提单快捷入口,员工确认表单后提交 -->
                <el-button v-if="canSendTicketEntry" :icon="Tickets"
                           :disabled="sending" @click="sendTicketEntry">
                  发送提单入口
                </el-button>
                <span v-if="hint" class="input-hint">{{ hint }}</span>
              </div>
              <el-button type="primary" :icon="Promotion" :loading="sending"
                         :disabled="!draft.trim()" @click="send">
                发送
              </el-button>
            </div>
          </div>
        </template>
        <el-empty v-else description="选择左侧咨询查看完整对话（含此前 AI 对话）" :image-size="80" />
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Promotion, CircleCheck, Document, Tickets } from '@element-plus/icons-vue'
import { userApi } from '../api/index.js'
import {
  consultationApi, TERMINAL_STATUS, TICKET_ENTRY_MESSAGE
} from '../api/consultation.js'

/**
 * 工程师侧「当前咨询」对话窗(PRD 19.2 / SM-CONSULT-001):
 * - 列表来自 GET /consultations,后端按 current_engineer_id = 本人过滤;
 * - WAITING_ENGINEER 下发送首条实际消息 = 首次有效回复 → HUMAN_ACTIVE(打开/已读不算);
 * - HUMAN_ACTIVE 下可提交解决结论 → PENDING_CONFIRMATION,由员工确认。
 */

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible', 'count-change'])

/** 工程师视角的状态标签(与员工侧 CONSULTATION_STATUS 区分) */
const ENGINEER_STATUS = {
  AI_ACTIVE: { label: 'AI 咨询中', type: 'primary' },
  WAITING_ENGINEER: { label: '待首次回复', type: 'danger' },
  HUMAN_ACTIVE: { label: '处理中', type: 'warning' },
  PENDING_CONFIRMATION: { label: '待员工确认', type: 'success' },
  RESOLVED: { label: '已解决', type: 'info' },
  CONVERTED_TO_TICKET: { label: '已转工单', type: 'info' },
  CLOSED: { label: '已结束', type: 'info' }
}

const sessions = ref([])
const previews = ref({})
const selected = ref(null)
const messages = ref([])
const draft = ref('')
const sending = ref(false)
const loadingMessages = ref(false)
const scrollRef = ref(null)
const applicants = ref({})
const finalMessagesLoaded = ref(false)

let listTimer = null
let pollTimer = null

const activeSessions = computed(() => sessions.value.filter(s => !TERMINAL_STATUS.includes(s.status)))
const endedSessions = computed(() => sessions.value.filter(s => TERMINAL_STATUS.includes(s.status)))
const selectedId = computed(() => selected.value?.session_id)
const isTerminal = computed(() => TERMINAL_STATUS.includes(selected.value?.status))
const inputPlaceholder = computed(() => {
  if (selected.value?.status === 'WAITING_ENGINEER') return '发送第一条回复即完成接入，回车发送'
  return '回复员工，回车发送'
})
const hint = computed(() => {
  if (selected.value?.status === 'WAITING_ENGINEER') return '首条回复后即可提交解决结论'
  return ''
})
/** 提单快捷入口只在工程师已接入后提供(WAITING_ENGINEER 下应先首条回复) */
const canSendTicketEntry = computed(() =>
  ['HUMAN_ACTIVE', 'PENDING_CONFIRMATION'].includes(selected.value?.status))

const statusMeta = (s) => ENGINEER_STATUS[s] || { label: s, type: 'info' }

async function loadApplicants() {
  try {
    const res = await userApi.listUsers()
    applicants.value = Object.fromEntries((res.data || []).map(user => [user.user_id, user]))
  } catch (e) {
    // 用户目录暂不可用时仍显示咨询接口提供的申请人账号。
  }
}

function applicantLabel(session) {
  const id = session?.creator_id
  if (!id) return '申请人信息暂不可用'
  const user = applicants.value[id]
  const roles = { employee: '员工', engineer: '工程师', platform_admin: '平台管理员', knowledge_admin: '知识库管理员', kb_admin: '知识库管理员' }
  const role = roles[user?.role?.toLowerCase()] || user?.role || '员工'
  return [user?.name, role, id].filter(Boolean).join(' · ')
}

function updateSelected(detail) {
  if (detail.status !== selected.value.status) {
    applyStatusChange(selected.value.status, detail.status)
    finalMessagesLoaded.value = false
  }
  selected.value = { ...selected.value, ...detail }
  if (isTerminal.value) draft.value = ''
  sessions.value = sessions.value.map(s => s.session_id === detail.session_id ? { ...s, ...detail } : s)
  emit('count-change', activeSessions.value.length)
}

// ---------------------------------------------------------------- 列表

async function loadSessions() {
  const snapshot = selected.value
  try {
    const page = await consultationApi.list(1, 100)
    const items = page?.items || []
    sessions.value = items
    emit('count-change', activeSessions.value.length)

    // 列表刷新时同步当前选中会话的状态(员工确认/结束/回复未解决)
    if (selected.value && selected.value === snapshot) {
      const fresh = items.find(i => i.session_id === selected.value.session_id)
      if (fresh && fresh.status !== selected.value.status) {
        updateSelected(fresh)
        await reloadSelected()
      }
    }
    // 状态先同步，再加载预览，避免消息预览慢时延迟结束通知。
    for (const s of activeSessions.value) {
      if (previews.value[s.session_id] === undefined) await loadPreview(s.session_id)
    }
  } catch (e) {
    // 轮询失败静默,不打断工作
  }
}

async function loadPreview(sessionId) {
  try {
    const page = await consultationApi.listMessages(sessionId)
    const items = (page?.items || []).filter(m => m.sender_type !== 'SYSTEM')
    const last = items[items.length - 1]
    previews.value[sessionId] = last ? last.content : '暂无消息'
  } catch (e) {
    previews.value[sessionId] = ''
  }
}

const previewOf = (id) => {
  const text = previews.value[id] || ''
  return text.length > 42 ? text.slice(0, 42) + '…' : (text || '…')
}

/** 工程师关心的状态变化提示 */
function applyStatusChange(before, after) {
  if (before === 'PENDING_CONFIRMATION' && after === 'HUMAN_ACTIVE') {
    ElMessage.warning('员工回复未解决，咨询已回到处理中')
  } else if (after === 'RESOLVED') {
    ElMessage.success('员工已确认解决')
  } else if (after === 'CLOSED') {
    ElMessage.info('员工已结束对话，会话已断开')
  } else if (after === 'CONVERTED_TO_TICKET') {
    ElMessage.info('该咨询已转为正式工单')
  } else if (before === 'WAITING_ENGINEER' && after === 'HUMAN_ACTIVE') {
    ElMessage.success('已接入，首次有效回复完成')
  }
}

// ---------------------------------------------------------------- 会话与消息

async function openSession(sessionId) {
  if (selectedId.value === sessionId) return
  loadingMessages.value = true
  try {
    const detail = await consultationApi.get(sessionId)
    // 先观察状态，再取历史，确保终态通知已提交后才读取最后一批消息。
    const page = await consultationApi.listMessages(sessionId)
    selected.value = { ...detail, session_id: detail.session_id || sessionId }
    messages.value = (page?.items || []).map(toLocalMessage)
    finalMessagesLoaded.value = isTerminal.value
    draft.value = ''
    scrollToBottom()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loadingMessages.value = false
  }
}

async function reloadSelected() {
  if (!selected.value) return
  const snapshot = selected.value
  loadingMessages.value = true
  try {
    const detail = await consultationApi.get(snapshot.session_id)
    if (selected.value !== snapshot) return
    const page = await consultationApi.listMessages(snapshot.session_id)
    if (selected.value !== snapshot) return
    updateSelected(detail)
    messages.value = (page?.items || []).map(toLocalMessage)
    finalMessagesLoaded.value = isTerminal.value
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loadingMessages.value = false
    scrollToBottom()
  }
}

function toLocalMessage(item) {
  return {
    id: item.message_id,
    serverId: item.message_id,
    senderType: item.sender_type || 'SYSTEM',
    content: item.content,
    citations: item.citations || [],
    generalAnswer: item.general_answer === true,
    sentAt: item.sent_at,
    withdrawnAt: item.withdrawn_at
  }
}

async function send() {
  const text = draft.value.trim()
  if (!text || !selected.value || isTerminal.value || sending.value) return
  const sessionId = selected.value.session_id
  const wasWaiting = selected.value.status === 'WAITING_ENGINEER'
  sending.value = true
  try {
    await consultationApi.sendMessage(sessionId, text)
    if (selected.value?.session_id !== sessionId || isTerminal.value) return
    messages.value.push({
      id: `local-${Date.now()}`,
      senderType: 'ENGINEER',
      content: text,
      sentAt: new Date().toISOString()
    })
    draft.value = ''
    scrollToBottom()
    if (wasWaiting) {
      // SM-CONSULT-001:首次有效回复 → HUMAN_ACTIVE,SLA 计时结束
      selected.value.status = 'HUMAN_ACTIVE'
      ElMessage.success('首次有效回复完成，已接入该咨询')
      await loadSessions()
    }
  } catch (e) {
    ElMessage.error(e.message)
    if (selected.value?.session_id === sessionId && !isTerminal.value) {
      draft.value = text
      await reloadSelected()
    }
  } finally {
    sending.value = false
  }
}

/** 工程师发送的提单快捷入口消息,渲染为小卡片。 */
const isTicketEntry = (msg) =>
  msg.senderType === 'ENGINEER' && msg.content === TICKET_ENTRY_MESSAGE

/**
 * 发送提单快捷入口(PRD 9.1):作为一条工程师消息落库,员工侧聊天时间线
 * 渲染成可点击卡片,点击跳转到提单界面由员工本人确认提交。
 */
async function sendTicketEntry() {
  if (!selected.value || !canSendTicketEntry.value || sending.value) return
  const sessionId = selected.value.session_id
  sending.value = true
  try {
    await consultationApi.sendMessage(sessionId, TICKET_ENTRY_MESSAGE)
    if (selected.value?.session_id !== sessionId || isTerminal.value) return
    messages.value.push({
      id: `local-${Date.now()}`,
      senderType: 'ENGINEER',
      content: TICKET_ENTRY_MESSAGE,
      sentAt: new Date().toISOString()
    })
    scrollToBottom()
    ElMessage.success('已发送提交工单入口')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    sending.value = false
  }
}

async function submitResolution() {
  if (!selected.value || isTerminal.value || sending.value) return
  const sessionId = selected.value.session_id
  let conclusion = ''
  try {
    const { value } = await ElMessageBox.prompt(
      '提交后咨询进入「待员工确认」，员工确认即解决；员工回复未解决会回到处理中。',
      '提交解决结论',
      {
        confirmButtonText: '提交', cancelButtonText: '取消',
        inputType: 'textarea',
        inputValidator: v => (v && v.trim().length > 0) || '解决结论不能为空'
      }
    )
    conclusion = value.trim()
  } catch (e) {
    return
  }
  if (selected.value?.session_id !== sessionId || isTerminal.value) return
  sending.value = true
  try {
    // 当前输入框内容作为结论的补充上下文一并发出
    const extra = draft.value.trim()
    if (extra) {
      await consultationApi.sendMessage(sessionId, extra)
      if (selected.value?.session_id !== sessionId || isTerminal.value) return
      messages.value.push({
        id: `local-${Date.now()}`,
        senderType: 'ENGINEER',
        content: extra,
        sentAt: new Date().toISOString()
      })
      draft.value = ''
    }
    const res = await consultationApi.submitResolution(sessionId, conclusion)
    if (selected.value?.session_id !== sessionId || isTerminal.value) return
    selected.value.status = res.status
    messages.value.push({
      id: `local-${Date.now() + 1}`,
      senderType: 'SYSTEM',
      content: '解决结论已提交，等待员工确认。',
      sentAt: new Date().toISOString()
    })
    scrollToBottom()
    ElMessage.success('解决结论已提交')
    await loadSessions()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    sending.value = false
  }
}

// ---------------------------------------------------------------- 轮询

async function pollSelected() {
  if (!selected.value || (isTerminal.value && finalMessagesLoaded.value)) return
  const snapshot = selected.value
  try {
    const detail = await consultationApi.get(snapshot.session_id)
    if (selected.value !== snapshot) return
    updateSelected(detail)
    const updated = selected.value
    const page = await consultationApi.listMessages(snapshot.session_id)
    if (selected.value !== updated) return
    const items = page?.items || []
    if (items.length !== messages.value.filter(m => m.serverId).length) {
      messages.value = items.map(toLocalMessage)
      scrollToBottom()
    }
    finalMessagesLoaded.value = isTerminal.value
  } catch (e) {
    // 轮询失败静默
  }
}

watch(() => props.visible, (open) => {
  if (open) {
    loadApplicants()
    loadSessions()
    clearInterval(pollTimer)
    pollTimer = setInterval(async () => { await pollSelected(); await loadSessions() }, 5000)
  } else {
    clearInterval(pollTimer)
    pollTimer = null
  }
})

onMounted(() => {
  // 抽屉关闭时也保持低频刷新,让外层徽标反映新分配的咨询
  loadSessions()
  listTimer = setInterval(loadSessions, 10000)
})
onUnmounted(() => {
  clearInterval(listTimer)
  clearInterval(pollTimer)
})

// ---------------------------------------------------------------- 渲染工具

function scrollToBottom() {
  nextTick(() => {
    const el = scrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}
const rowClass = (msg) => (msg.senderType === 'ENGINEER' ? 'row-right' : 'row-left')
const bubbleClass = (msg) => 'bubble-' + msg.senderType.toLowerCase()
const avatarOf = (t) => ({ EMPLOYEE: '员', AI: 'AI', ENGINEER: '我', SYSTEM: '系' }[t] || '?')
const senderLabel = (msg) =>
  ({ EMPLOYEE: applicantLabel(selected.value), AI: 'AI 客服', ENGINEER: '我', SYSTEM: '系统' }[msg.senderType] || msg.senderType)
const formatTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.eng-consult { display: flex; gap: 12px; height: calc(100vh - 110px); }

/* 左:列表 */
.session-pane {
  flex: none; width: 240px; display: flex; flex-direction: column;
  background: var(--el-fill-color-light); border-radius: 8px; padding: 10px;
}
.pane-head {
  display: flex; justify-content: space-between; align-items: center;
  font-weight: 600; font-size: 13px; padding: 4px 6px 8px;
  color: var(--el-text-color-primary);
}
.pane-head-end { margin-top: 14px; border-top: 1px dashed var(--el-border-color); padding-top: 12px; }
.pane-body { flex: 1; }
.pane-tip {
  font-size: 11px; color: var(--el-text-color-placeholder);
  padding-top: 8px; text-align: center;
}
.session-item {
  padding: 8px 10px; border-radius: 6px; cursor: pointer; margin-bottom: 6px;
  background: var(--el-bg-color); border: 1px solid var(--el-border-color-lighter);
  transition: border-color .15s;
}
.session-item:hover { border-color: var(--el-color-primary-light-5); }
.session-item.selected { border-color: var(--el-color-primary); }
.session-item.ended { opacity: .7; }
.applicant { font-size: 13px; font-weight: 600; margin-bottom: 6px; overflow-wrap: anywhere; }
.session-top { display: flex; justify-content: space-between; align-items: center; gap: 6px; }
.session-id {
  font-family: monospace; font-size: 12px;
  color: var(--el-text-color-secondary);
}
.session-preview {
  margin-top: 4px; font-size: 12px; color: var(--el-text-color-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* 右:聊天 */
.chat-pane { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.chat-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.chat-head-title { display: flex; align-items: center; gap: 10px; }
.state-banner { margin-bottom: 10px; }

.chat-body {
  flex: 1; overflow-y: auto; padding: 8px 4px;
  background: var(--el-fill-color-lighter); border-radius: 8px;
}
.msg-row { display: flex; gap: 10px; margin-bottom: 16px; padding: 0 8px; }
.row-right { flex-direction: row-reverse; }
.row-right .msg-main { align-items: flex-end; }
.row-right .msg-meta { flex-direction: row-reverse; }

.msg-avatar {
  flex: none; width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600; color: #fff;
}
.avatar-employee { background: var(--el-color-primary); }
.avatar-ai { background: #7c3aed; }
.avatar-engineer { background: var(--el-color-success); }
.avatar-system { background: var(--el-color-info); }

.msg-main { display: flex; flex-direction: column; max-width: 78%; }
.msg-meta { display: flex; gap: 8px; align-items: center; margin-bottom: 4px; }
.msg-sender { font-size: 12px; color: var(--el-text-color-secondary); }
.msg-time { font-size: 11px; color: var(--el-text-color-placeholder); }

.msg-bubble {
  padding: 10px 14px; border-radius: 10px; line-height: 1.7;
  background: var(--el-bg-color); border: 1px solid var(--el-border-color-lighter);
}
.msg-text { white-space: pre-wrap; word-break: break-word; }
.general-answer-note { margin-top: 8px; font-size: 12px; color: var(--el-text-color-secondary); }
.ticket-entry-sent {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: var(--el-text-color-secondary);
}
.bubble-engineer { background: var(--el-color-success); border-color: var(--el-color-success); color: #fff; }
.bubble-system {
  background: transparent; border: none; color: var(--el-text-color-secondary);
  font-size: 13px; padding: 4px 0;
}

.citations { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--el-border-color); }
.citations-title {
  display: flex; align-items: center; gap: 4px; font-size: 12px;
  color: var(--el-text-color-secondary); margin-bottom: 6px;
}
.citation-tag { margin-right: 6px; cursor: pointer; }
.citation-pop-title { font-weight: 600; margin-bottom: 6px; }
.citation-pop-snippet { font-size: 13px; line-height: 1.6; color: var(--el-text-color-regular); }

/* 输入区 */
.chat-input { margin-top: 12px; }
.chat-actions {
  margin-top: 8px; display: flex; justify-content: space-between; align-items: center; gap: 8px;
}
.chat-actions-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.input-hint { font-size: 12px; color: var(--el-text-color-placeholder); }
</style>
