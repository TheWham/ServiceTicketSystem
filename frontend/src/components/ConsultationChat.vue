<template>
  <div class="consultation-chat">
    <!-- 初始化:自动恢复进行中的咨询,没有则新开 AI 会话(进去就是对话框) -->
    <div v-if="booting" v-loading="true" element-loading-text="正在进入对话…"
         class="booting"></div>

    <div v-else-if="startupError" class="startup-error" role="alert">
      <el-icon class="error-icon"><WarningFilled /></el-icon>
      <h2>暂时无法连接客服</h2>
      <p>{{ startupError }}</p>
      <div><el-button type="primary" :icon="RefreshLeft" @click="autoStart">重新连接</el-button><el-button :icon="Tickets" @click="goCreateTicket">提交工单</el-button></div>
    </div>

    <!-- ===== 聊天面板 ===== -->
    <el-card v-else-if="session" shadow="never" class="panel chat-panel">
        <template #header>
          <div class="conversation-header">
            <div class="conversation-identity"><div class="small-assistant"><el-icon><Service /></el-icon></div><div><strong>IT 智能助手</strong><span>办公遇到的问题，在这里聊聊</span></div></div>
            <el-tag :type="sessionStatus.type" effect="light" round>{{ sessionStatus.label }}</el-tag>
          </div>
        </template>
        <!-- 等待工程师的提示 -->
        <el-alert v-if="isWaitingHuman" type="warning" :closable="false"
                  class="state-banner">
          <template #title>
            已转人工，正在为你分配工程师{{ assignmentTip }}。工程师需要在 10 个工作分钟内首次回复。
            <span v-if="queueStatus.assigned" class="queue-count">
              当前排队 <strong>{{ queueCount }}</strong> 人
            </span>
          </template>
          <div class="banner-actions">
            <el-button size="small" type="danger" plain :loading="cancelingQueue" :disabled="closing" @click="cancelQueue">
              取消排队
            </el-button>
          </div>
        </el-alert>
        <el-alert v-else-if="session.status === 'PENDING_CONFIRMATION'" type="success" :closable="false"
                  class="state-banner">
          <template #title>工程师已给出解决结论，请确认问题是否已解决。</template>
          <div class="banner-actions">
            <el-button type="success" size="small" :icon="CircleCheck" @click="confirmResolved">
              问题已解决
            </el-button>
            <el-button size="small" @click="focusInput">还没解决，我再说明一下</el-button>
          </div>
        </el-alert>
        <el-alert v-else-if="session.status === 'RESOLVED'" type="success" :closable="false"
                  class="state-banner">
          <template #title>本次咨询已结束。24 小时内如果问题复发，可以恢复原咨询。</template>
          <div class="banner-actions">
            <el-button size="small" :icon="RefreshLeft" @click="reopenSession">恢复咨询</el-button>
          </div>
        </el-alert>
        <el-alert v-else-if="session.status === 'CONVERTED_TO_TICKET'" type="info" :closable="false"
                  class="state-banner">
          <template #title>本咨询已转为正式工单，后续请在工单里跟进处理进度。</template>
        </el-alert>
        <el-alert v-else-if="session.status === 'CLOSED'" type="info" :closable="false"
                  class="state-banner">
          <template #title>本次对话已结束，会话已断开。</template>
        </el-alert>

        <!-- 消息流 -->
        <div ref="scrollRef" class="chat-body" v-loading="loadingMessages" role="log" aria-label="客服对话记录" aria-live="polite" :aria-busy="aiThinking" @scroll="onChatScroll">
          <div v-if="showWelcome" class="chat-welcome">
            <OrbitalCore class="welcome-core" />
            <h2>你好，有什么可以帮你？</h2>
            <p>电脑、网络、邮箱或办公软件遇到问题，<br>告诉我具体情况，我们一步步排查。</p>
            <div class="suggestion-label">你可以从这些问题开始</div>
            <div class="suggestion-grid">
              <button v-for="item in suggestions" :key="item.title" class="suggestion-card" type="button" @click="useSuggestion(item.question)">
                <el-icon><component :is="item.icon" /></el-icon><span><strong>{{ item.title }}</strong><small>{{ item.description }}</small></span><el-icon class="suggestion-arrow"><ArrowRight /></el-icon>
              </button>
            </div>
          </div>
          <div v-for="msg in visibleMessages" :key="msg.id" class="msg-row" :class="rowClass(msg)">
            <div class="msg-avatar" :class="'avatar-' + msg.senderType.toLowerCase()">
              {{ avatarOf(msg.senderType) }}
            </div>
            <div class="msg-main">
              <div class="msg-meta">
                <span class="msg-sender">{{ senderLabel(msg) }}</span>
                <span class="msg-time">{{ formatTime(msg.sentAt) }}</span>
              </div>

              <!-- 拒答气泡 -->
              <div v-if="msg.refusalReason" class="msg-bubble bubble-refusal">
                <div class="refusal-head">
                  <el-icon><WarningFilled /></el-icon>
                  <span>AI 无法回答这个问题</span>
                </div>
                <div class="refusal-reason">{{ refusalText(msg.refusalReason) }}</div>
                <div class="refusal-actions">
                  <el-button type="primary" size="small" :icon="Service" @click="openTransfer()">
                    转人工
                  </el-button>
                  <el-button size="small" :icon="Tickets" @click="goCreateTicket">直接提交工单</el-button>
                </div>
              </div>

              <!-- 工程师提单快捷入口(PRD 9.1:人工咨询中由工程师发送,员工确认表单后提交) -->
              <div v-else-if="isTicketEntry(msg)" class="msg-bubble bubble-ticket-entry">
                <div class="ticket-entry-head">
                  <el-icon><Tickets /></el-icon>
                  <span>工程师邀请你提交正式工单</span>
                </div>
                <div class="ticket-entry-desc">
                  如果这个问题需要上门维修、设备更换、持续跟踪或正式留痕，请提交工单。
                  提交前你可以检查并修改表单内容。
                </div>
                <div class="ticket-entry-actions">
                  <el-button type="primary" size="small" :icon="Tickets" @click="goCreateTicket">
                    前往提交工单
                  </el-button>
                </div>
              </div>

              <!-- 普通气泡 -->
              <div v-else class="msg-bubble" :class="bubbleClass(msg)">
                <div v-if="msg.content" class="msg-text">{{ msg.content }}</div>
                <ChatMessageAttachments v-if="msg.attachments?.length" :session-id="session.sessionId" :attachments="msg.attachments" />

                <!-- 通用能力回答标识(冷启动放宽策略:无知识库依据) -->
                <div v-if="msg.generalAnswer" class="general-answer-note">
                  <el-icon><MagicStick /></el-icon>
                  这条回答基于 AI 通用知识，暂无知识库依据。
                </div>

                <!-- 有知识依据时展示经过校验的真实引用 -->
                <div v-if="msg.citations && msg.citations.length" class="citations">
                  <div class="citations-title">
                    <el-icon><Document /></el-icon> 依据以下已发布知识
                  </div>
                  <el-popover v-for="c in msg.citations" :key="c.versionId"
                              placement="top" :width="280" trigger="click">
                    <template #reference>
                      <el-button class="citation-tag" plain size="small">{{ c.title }}</el-button>
                    </template>
                    <div class="citation-pop">
                      <div class="citation-pop-title">{{ c.title }}</div>
                      <div class="citation-pop-snippet">{{ c.snippet }}</div>
                      <div class="citation-pop-meta">
                        版本 {{ c.versionId }} · 相关度 {{ c.score }}
                      </div>
                    </div>
                  </el-popover>
                </div>

                <!-- 解决反馈只挂在最后一条非本地 AI 回复的气泡底部 -->
                <div v-if="showAnswerFeedback(msg)" class="answer-feedback">
                  <template v-if="msg.feedback === null">
                    <span class="answer-feedback-label">这个回答解决你的问题了吗？</span>
                    <el-button size="small" type="success" :loading="msg.feedbackPending"
                               :disabled="closing || cancelingQueue" @click="resolveAnswer(msg)">已解决</el-button>
                    <el-button size="small" type="warning" :disabled="msg.feedbackPending || closing || cancelingQueue"
                               @click="markUnresolved(msg)">未解决</el-button>
                  </template>
                  <span v-else-if="msg.feedback === 'resolved'" class="feedback-resolved"><el-icon aria-hidden="true"><CircleCheck /></el-icon> 已标记为解决</span>
                  <div v-else class="feedback-unresolved">
                    <template v-if="msg.transferSubmitted">
                      <span>已提交转人工申请</span>
                    </template>
                    <template v-else>
                      <span>抱歉没能帮到你，</span>
                      <el-link type="primary" @click="openTransfer(msg)">转接人工客服 →</el-link>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- AI 正在思考 -->
          <div v-if="aiThinking && !isTerminal" class="msg-row row-left">
            <div class="msg-avatar avatar-ai">AI</div>
            <div class="msg-main">
              <div class="msg-bubble bubble-ai thinking">
                <span class="dot" /><span class="dot" /><span class="dot" />
                <span class="thinking-text">正在分析你的 IT 问题…（可能需要几十秒）</span>
              </div>
            </div>
          </div>
        </div>

        <button v-if="hasUnreadMessages" type="button" class="new-message-cue" @click="scrollToBottom(true)">有新消息 · 查看最新 ↓</button>
        <!-- 输入区 -->
        <div v-if="!isTerminal" class="chat-input" :class="{ 'attachment-dragging': attachmentDragDepth > 0 }"
             @dragenter="onAttachmentDragEnter" @dragover="onAttachmentDragOver"
             @drop.capture="attachmentDragDepth = 0"
             @dragleave="attachmentDragDepth = Math.max(0, attachmentDragDepth - 1)" @drop="onAttachmentDrop">
          <div v-if="attachmentDragDepth > 0" class="attachment-drop-hint" role="status">松开即可上传图片或文件</div>
          <div class="input-toolbar">
            <label for="support-message">描述你的问题</label>
            <el-button text type="danger" :icon="Close" :loading="closing"
                       :disabled="cancelingQueue || transferring" @click="closeSession">
              结束对话
            </el-button>
          </div>
          <el-input id="support-message" ref="inputRef" v-model="draft" type="textarea" :rows="3" resize="none"
                    :maxlength="inputMaxLength" show-word-limit
                    :placeholder="inputPlaceholder" :disabled="sending || aiThinking || inputDisabled || closing || cancelingQueue"
                    @keydown.enter.exact="send" />
          <ChatAttachmentUploader v-if="canAttach" :key="session.sessionId" ref="attachmentUploaderRef"
                                  v-model="attachmentDrafts" :session-id="session.sessionId" :disabled="attachmentDisabled" />
          <div class="chat-actions">
            <div class="chat-actions-left">
              <!-- PRD 8.1:AI 对话中必须始终提供转人工和提交工单入口 -->
              <el-button v-if="canTransfer" :icon="Service" :disabled="closing || cancelingQueue" @click="openTransfer()">转人工</el-button>
              <el-button :icon="Tickets" @click="goCreateTicket">提交工单</el-button>
            </div>
            <el-button type="primary" :icon="Promotion" :loading="sending || aiThinking"
                       :disabled="(!draft.trim() && !attachmentDrafts.length) || attachmentBlocked || inputDisabled || closing || cancelingQueue" @click="send">
              发送
            </el-button>
          </div>
          <div class="input-hint">Enter 发送 · Shift + Enter 换行<span>{{ isAiHandling ? 'AI 建议仅供排查参考' : '支持拖拽图片、文件 · 单个不超过 20MB' }}</span></div>
        </div>

        <!-- 终态:开新会话 -->
        <div v-else class="new-topic">
          <el-button type="primary" :icon="ChatDotRound" :loading="creating" @click="startAi">
            开始新咨询
          </el-button>
        </div>
      </el-card>

    <!-- 转人工对话框 -->
    <el-dialog v-model="transferVisible" title="转人工咨询" width="min(460px, calc(100vw - 32px))" append-to-body
               @closed="pendingTransferMessage = null">
      <el-form label-width="90px">
        <el-form-item label="问题类型" required>
          <el-radio-group v-model="transferForm.categoryId" class="category-options">
            <el-radio v-for="(c, index) in categories" :key="c.id" :value="c.id" border>
              <span class="category-number">{{ index + 1 }}</span>
              {{ c.name }}
            </el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <el-alert type="info" :closable="false">
        <template #title>
          系统会按分类和负载分配给一名工程师，只有被分配的工程师会看到待回复咨询。
        </template>
      </el-alert>
      <template #footer>
        <el-button @click="transferVisible = false">取消</el-button>
        <el-button type="primary" :loading="transferring"
                   :disabled="!transferForm.categoryId" @click="doTransfer">
          确认转人工
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import ChatAttachmentUploader from './ChatAttachmentUploader.vue'
import ChatMessageAttachments from './ChatMessageAttachments.vue'
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import OrbitalCore from './OrbitalCore.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound, Service, Close, Promotion, Tickets,
  Document, WarningFilled, CircleCheck, RefreshLeft, MagicStick,
  Monitor, Connection, Message, Printer, ArrowRight
} from '@element-plus/icons-vue'
import {
  consultationApi, REFUSAL_REASON, TERMINAL_STATUS, TICKET_ENTRY_MESSAGE, CONSULTATION_STATUS
} from '../api/consultation.js'

/**
 * 员工侧智能客服聊天面板(无外部布局假设):
 * 由 /consultation 整页路由承载。
 * 状态、消息、转人工的领域规则全部在组件内部闭环。
 */

const emit = defineEmits(['navigate'])

const router = useRouter()

// 分类取自 it_consultation.category 种子数据的末级可路由分类
const categories = [
  { id: 'C_HW_PC', name: '电脑故障' },
  { id: 'C_HW_PR', name: '打印机故障' },
  { id: 'C_SW', name: '软件故障' },
  { id: 'C_NET', name: '网络访问' },
  { id: 'C_ACC', name: '账号与权限' },
  { id: 'C_OTH', name: '其他服务' }
]

const session = ref(null)
const messages = ref([])
const draft = ref('')
const attachmentDrafts = ref([])
const attachmentUploaderRef = ref(null)
const attachmentDragDepth = ref(0)
const pendingHumanSend = ref(null)
const creating = ref(false)
const sending = ref(false)
const aiThinking = ref(false)
const loadingMessages = ref(false)
const booting = ref(false)
const startupError = ref('')
const closing = ref(false)
const scrollRef = ref(null)
const inputRef = ref(null)

const transferVisible = ref(false)
const transferring = ref(false)
const cancelingQueue = ref(false)
const transferForm = ref({ categoryId: '' })
const pendingTransferMessage = ref(null)
const assignmentSeconds = ref(null)
const queueStatus = ref({ assigned: false, waitingCount: 0 })

/** 本人进行中(非终态)的咨询,入口页展示以便继续对话 */
const resumable = ref([])

let pollTimer = null
let localSeq = 0
let sessionRevision = 0

const isTerminal = computed(() => TERMINAL_STATUS.includes(session.value?.status))
/** AI-004.4 的转人工只在 AI_ACTIVE 下合法;已在人工流程里不再重复转 */
const isAiHandling = computed(() => ['AI_ACTIVE', 'AI_HANDLING'].includes(session.value?.status))
const isWaitingHuman = computed(() => ['WAITING_ENGINEER', 'WAITING_HUMAN'].includes(session.value?.status))
const inputDisabled = computed(() => isWaitingHuman.value)
const canAttach = computed(() => ['HUMAN_ACTIVE', 'HUMAN_HANDLING', 'PENDING_CONFIRMATION'].includes(session.value?.status))
const attachmentBlocked = computed(() => attachmentDrafts.value.some(file => file.status !== 'ready' || !file.attachment_id))
const attachmentDisabled = computed(() => sending.value || aiThinking.value || inputDisabled.value || closing.value || cancelingQueue.value || transferring.value || loadingMessages.value)

function onAttachmentDragEnter(event) {
  if (!Array.from(event.dataTransfer?.types || []).includes('Files')) return
  event.preventDefault()
  if (canAttach.value && !attachmentDisabled.value) attachmentDragDepth.value++
}
function onAttachmentDragOver(event) {
  if (!Array.from(event.dataTransfer?.types || []).includes('Files')) return
  event.preventDefault()
  event.dataTransfer.dropEffect = canAttach.value && !attachmentDisabled.value ? 'copy' : 'none'
}
function onAttachmentDrop(event) {
  event.preventDefault()
  attachmentDragDepth.value = 0
  if (!canAttach.value || attachmentDisabled.value) return
  attachmentUploaderRef.value?.addFiles(Array.from(event.dataTransfer?.files || []))
}
const canTransfer = computed(() => isAiHandling.value)
const sessionStatus = computed(() => CONSULTATION_STATUS[session.value?.status] || { label: '咨询中', type: 'info' })
const showWelcome = computed(() => isAiHandling.value && messages.value.every(m => m.isGreeting))
const visibleMessages = computed(() => showWelcome.value ? [] : messages.value)
const suggestions = [
  { title: '网络与 VPN', description: '无法联网、连接中断', icon: Connection, question: '我的 VPN 无法连接，应该如何排查？' },
  { title: '电脑运行异常', description: '卡顿、黑屏、启动失败', icon: Monitor, question: '电脑最近运行很卡，应该如何排查？' },
  { title: '邮箱收发问题', description: '收不到邮件、发送失败', icon: Message, question: '我的办公邮箱收不到邮件，应该如何排查？' },
  { title: '打印机故障', description: '无法打印、设备离线', icon: Printer, question: '打印机显示离线，无法打印，应该如何排查？' }
]
function useSuggestion(question) {
  draft.value = question
  focusInput()
}
const inputMaxLength = computed(() => (isAiHandling.value ? 8000 : 12000))
const inputPlaceholder = computed(() => {
  if (isAiHandling.value) return '描述你遇到的问题，回车发送'
  if (isWaitingHuman.value) return '正在等待客服接入，请稍候'
  return '和工程师继续沟通，回车发送'
})
const assignmentTip = computed(() =>
  assignmentSeconds.value != null ? `（预计等待 ${Math.ceil(assignmentSeconds.value / 60)} 分钟内）` : '')
const queueCount = computed(() => queueStatus.value.waitingCount)

// ---------------------------------------------------------------- 会话

/**
 * 打开即进入对话:有进行中的咨询就恢复最近一次(连续时间线,PRD 13.1),
 * 没有则新开 AI 会话并由 AI 客服先做自我介绍。
 */
async function autoStart() {
  booting.value = true
  startupError.value = ''
  try {
    await loadResumable()
    if (resumable.value.length) {
      await resumeSession(resumable.value[0])
    } else {
      await startAi()
    }
  } catch (e) {
    startupError.value = e.message || '服务连接失败，请稍后重试'
    ElMessage.error(e.message)
  } finally {
    booting.value = false
    focusInput()
  }
}

/** 挂载时拉取本人进行中的咨询(OpenAPI 05 listConsultations,后端按 creator 过滤)。 */
async function loadResumable() {
    const page = await consultationApi.list(1, 20)
    resumable.value = (page?.items || [])
      .filter(s => !TERMINAL_STATUS.includes(s.status))
      .slice(0, 5)
}

/** 继续一个进行中的咨询:恢复完整时间线(含此前 AI 对话,PRD 13.1)。 */
async function resumeSession(s) {
  creating.value = true
  try {
    session.value = { ...s, sessionId: s.session_id }
    await reload()
    await refreshQueueStatus()
    startPolling()
  } catch (e) {
    ElMessage.error(e.message)
    session.value = null
    startupError.value = e.message || '恢复咨询失败，请重试'
  } finally {
    creating.value = false
  }
}

async function startAi() {
  if (creating.value) return
  creating.value = true
  startupError.value = ''
  try {
    session.value = await consultationApi.create('AI')
    sessionRevision++
    draft.value = ''
    attachmentDrafts.value = []
    pendingHumanSend.value = null
    attachmentDragDepth.value = 0
    sending.value = false
    aiThinking.value = false
    queueStatus.value = { assigned: false, waitingCount: 0 }
    messages.value = []
    messages.value.push(createGreeting())
    nextTick(() => { if (scrollRef.value) scrollRef.value.scrollTop = 0 })
    startPolling()
  } catch (e) {
    startupError.value = e.message || '创建咨询失败，请重试'
    ElMessage.error(e.message)
  } finally {
    creating.value = false
  }
}

async function reload() {
  if (!session.value) return
  loadingMessages.value = true
  try {
    const [detail, page] = await Promise.all([
      consultationApi.get(session.value.sessionId),
      consultationApi.listMessages(session.value.sessionId)
    ])
    session.value = { ...session.value, ...detail,
                      sessionId: detail.session_id || session.value.sessionId,
                      status: detail.status }
    messages.value = withGreeting((page?.items || []).map(toLocalMessage))
  } catch (e) {
    throw e
  } finally {
    loadingMessages.value = false
    scrollToBottom(true)
  }
}

/** 把服务端消息投影转成本地渲染结构。拒答消息由 AI 侧的固定话术标识。 */
function toLocalMessage(item) {
  return {
    id: item.message_id,
    serverId: item.message_id,
    senderType: item.sender_type || 'SYSTEM',
    content: item.content,
    attachments: item.attachments || [],
    citations: item.citations || [],
    interactionId: item.interaction_id || null,
    replyType: item.reply_type || null,
    refusalReason: item.refusal_reason || null,
    generalAnswer: item.general_answer === true,
    feedback: null,
    local: false,
    sentAt: item.sent_at,
    withdrawnAt: item.withdrawn_at
  }
}

// ---------------------------------------------------------------- 消息

function upsertServerMessage(item) {
  const index = messages.value.findIndex(message => message.serverId === item.message_id)
  const message = toLocalMessage(item)
  if (index < 0) messages.value.push(message)
  else messages.value[index] = message
}

function pushLocal(senderType, content, extra = {}) {
  messages.value.push({
    id: `local-${++localSeq}`,
    senderType,
    content,
    ...(senderType === 'AI' ? { feedback: null } : {}),
    sentAt: new Date().toISOString(),
    ...extra
  })
  scrollToBottom(senderType === 'EMPLOYEE')
}

const GREETING_TEXT = '你好，我是 IT 智能助手小 T 👋 我可以帮你解决 VPN 连不上、邮箱收不到邮件、打印机故障、账号权限等常见 IT 问题。请描述你遇到的情况，我会先尝试帮你解决；如果解决不了，可以随时转接人工客服。'

function createGreeting() {
  return {
    id: `local-greeting-${++localSeq}`,
    senderType: 'AI',
    content: GREETING_TEXT,
    local: true,
    isGreeting: true,
    feedback: null,
    sentAt: new Date().toISOString()
  }
}

function withGreeting(items) {
  return items.some(item => item.local && item.isGreeting)
    ? items
    : [createGreeting(), ...items]
}

async function send(event) {
  if (event?.isComposing || event?.keyCode === 229) return
  event?.preventDefault?.()
  const text = draft.value.trim()
  if ((!text && !attachmentDrafts.value.length) || attachmentBlocked.value || !session.value || isTerminal.value || inputDisabled.value || sending.value || aiThinking.value || closing.value || cancelingQueue.value) return
  if (isAiHandling.value && (!text || attachmentDrafts.value.length)) return
  const sessionId = session.value.sessionId
  const revision = sessionRevision
  const stillActive = () => revision === sessionRevision && session.value?.sessionId === sessionId && !isTerminal.value
  draft.value = ''

  if (isAiHandling.value) {
    pushLocal('EMPLOYEE', text)
    aiThinking.value = true
    try {
      const res = await consultationApi.aiMessage(sessionId, text)
      if (!stillActive() || !isAiHandling.value) return
      if (res.replyType === 'REFUSE') {
        pushLocal('AI', '', { refusalReason: res.refusalReason, interactionId: res.interactionId })
      } else {
        const hasCitations = (res.citations || []).length > 0
        pushLocal('AI', res.answerText, {
          citations: res.citations || [],
          interactionId: res.interactionId,
          suggestTransfer: res.suggestTransfer,
          replyType: res.replyType,
          generalAnswer: res.replyType === 'ANSWER' && !hasCitations
        })
        if (res.replyType === 'ANSWER' && !hasCitations) {
          pushLocal('SYSTEM', '这条回答暂无知识库依据，仅供排查参考。你可以继续补充问题、反馈是否解决，或转人工处理。')
        } else if (res.suggestTransfer) {
          pushLocal('SYSTEM', '这个回答的把握不高，如果没解决问题建议转人工。')
        }
      }
    } catch (e) {
      if (!stillActive()) return
      // AI 故障不阻塞主链路:提示并保留转人工/提单入口(RD-013)
      draft.value = text
      pushLocal('SYSTEM', `AI 暂时不可用（${e.message}）。你可以转人工或直接提交工单。`)
    } finally {
      if (revision === sessionRevision) aiThinking.value = false
    }
    return
  }

  // 人工咨询消息
  const attachmentIds = attachmentDrafts.value.map(file => file.attachment_id)
  const signature = JSON.stringify([sessionId, text, attachmentIds])
  if (pendingHumanSend.value?.signature !== signature) {
    pendingHumanSend.value = { signature, id: `cmsg-${Date.now()}-${Math.random().toString(36).slice(2)}` }
  }
  const attempt = pendingHumanSend.value
  sending.value = true
  try {
    const message = await consultationApi.sendMessage(sessionId, text, attempt.id, attachmentIds)
    if (!stillActive()) return
    const attachments = message?.attachments || attachmentDrafts.value.map(({ attachment_id, file_name, size, content_type, is_image }) => ({ attachment_id, file_name, size, content_type, is_image }))
    if (message?.message_id) upsertServerMessage(message)
    else pushLocal('EMPLOYEE', text, { attachments })
    attachmentUploaderRef.value?.clear()
    attachmentDrafts.value = []
    pendingHumanSend.value = null
    scrollToBottom(true)
    await refreshStatus()
  } catch (e) {
    if (!stillActive()) return
    ElMessage.error(e.message)
    draft.value = text
  } finally {
    if (revision === sessionRevision) sending.value = false
  }
}

// ---------------------------------------------------------------- 转人工与收尾

function openTransfer(msg = null) {
  if (!canTransfer.value || closing.value || cancelingQueue.value) return
  pendingTransferMessage.value = msg
  transferForm.value.categoryId = ''
  transferVisible.value = true
}

async function doTransfer() {
  if (!transferForm.value.categoryId || transferring.value || closing.value || cancelingQueue.value || !canTransfer.value) return
  transferring.value = true
  try {
    const res = await consultationApi.transfer(
      session.value.sessionId, transferForm.value.categoryId)
    const assignmentId = res?.assignmentId || res?.assignment_id
    const selectedCategory = categories.find(c => c.id === transferForm.value.categoryId)
    session.value.status = res?.status || 'WAITING_ENGINEER'
    assignmentSeconds.value = res?.estimatedWaitSeconds ?? res?.estimated_wait_seconds ?? null
    if (pendingTransferMessage.value) pendingTransferMessage.value.transferSubmitted = true
    transferVisible.value = false
    pendingTransferMessage.value = null
    await refreshQueueStatus()
    pushLocal('SYSTEM', assignmentId
      ? `已按“${selectedCategory?.name || '所选分类'}”进入人工客服队列，工程师会尽快接入。`
      : `已按“${selectedCategory?.name || '所选分类'}”提交转人工申请，但当前没有可用工程师，已进入异常队列等待处理。`)
    startPolling()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    transferring.value = false
  }
}

async function resolveAnswer(msg) {
  if (msg.feedbackPending || !isAiHandling.value || closing.value || cancelingQueue.value) return
  const sessionId = session.value.sessionId
  const revision = sessionRevision
  const stillActive = () => revision === sessionRevision && session.value?.sessionId === sessionId && isAiHandling.value
  msg.feedbackPending = true
  try {
    await saveAnswerFeedback(sessionId, msg, 'HELPFUL')
    if (!stillActive()) return
    const res = await consultationApi.confirm(sessionId)
    if (!stillActive()) return
    msg.feedback = 'resolved'
    finishSession(res?.status || 'RESOLVED')
    pushLocal('SYSTEM', '员工确认问题已解决，会话结束')
  } catch (e) {
    if (stillActive()) ElMessage.error(e.message || '反馈或确认未保存，请重试')
  } finally {
    msg.feedbackPending = false
  }
}

async function saveAnswerFeedback(sessionId, msg, feedback) {
  // 历史旧消息可能没有交互 ID，不伪造关联；新消息反馈失败时保留按钮供重试。
  if (!msg.interactionId || msg.recordedFeedback === feedback) return
  const res = await consultationApi.feedback(sessionId, msg.interactionId, feedback)
  if (!res?.accepted) throw new Error('反馈未保存，请重试')
  msg.recordedFeedback = feedback
}

async function confirmResolved() {
  try {
    const res = await consultationApi.confirm(session.value.sessionId)
    session.value.status = res?.status || 'RESOLVED'
    pushLocal('SYSTEM', '已确认解决，本次咨询结束。')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function markUnresolved(msg) {
  if (msg.feedbackPending || !isAiHandling.value || closing.value || cancelingQueue.value) return
  const sessionId = session.value.sessionId
  const revision = sessionRevision
  msg.feedbackPending = true
  try {
    await saveAnswerFeedback(sessionId, msg, 'NOT_HELPFUL')
    if (revision !== sessionRevision || session.value?.sessionId !== sessionId || !isAiHandling.value) return
    msg.feedback = 'unresolved'
  } catch (e) {
    if (revision === sessionRevision) ElMessage.error(e.message || '反馈未保存，请重试')
  } finally {
    msg.feedbackPending = false
  }
}

async function cancelQueue() {
  if (cancelingQueue.value || closing.value || isTerminal.value || !session.value?.sessionId) return
  cancelingQueue.value = true
  try {
    const res = await consultationApi.close(session.value.sessionId, '员工取消人工客服排队')
    finishSession(res?.status || 'CLOSED')
    pushLocal('SYSTEM', '员工已取消人工客服排队，本次咨询结束')
  } catch (e) {
    ElMessage.error(e.message || '取消排队失败')
  } finally {
    cancelingQueue.value = false
  }
}

async function reopenSession() {
  try {
    const { value } = await ElMessageBox.prompt('请说明问题复发的情况', '恢复咨询', {
      confirmButtonText: '恢复', cancelButtonText: '取消',
      inputValidator: v => (v && v.trim().length > 0) || '恢复原因必填'
    })
    const res = await consultationApi.reopen(session.value.sessionId, value.trim())
    session.value.status = res.status
    queueStatus.value = { assigned: false, waitingCount: 0 }
    pushLocal('SYSTEM', '咨询已恢复，正在重新分配工程师。')
    startPolling()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.message || '恢复失败')
  }
}

async function closeSession() {
  if (closing.value || cancelingQueue.value || transferring.value || isTerminal.value || !session.value?.sessionId) return
  closing.value = true
  try {
    const res = await consultationApi.close(session.value.sessionId, '员工主动结束咨询')
    finishSession(res?.status || 'CLOSED')
    pushLocal('SYSTEM', '员工已结束对话，会话已断开。')
  } catch (e) {
    ElMessage.error(e.message || '结束失败')
  } finally {
    closing.value = false
  }
}

function finishSession(status) {
  sessionRevision++
  session.value.status = status
  draft.value = ''
  attachmentDrafts.value = []
  pendingHumanSend.value = null
  attachmentDragDepth.value = 0
  transferVisible.value = false
  pendingTransferMessage.value = null
  assignmentSeconds.value = null
  sending.value = false
  aiThinking.value = false
  resetQueueStatus()
  stopPolling()
}

function goCreateTicket() {
  // 跳到提单页(默认落在“提交工单” tab);带 session 让提单页拉取咨询预填(PRD 9.1)
  emit('navigate')
  if (session.value?.sessionId && !isTerminal.value) {
    router.push({ path: '/employee', query: { from: 'consultation', session: session.value.sessionId } })
  } else {
    router.push('/employee')
  }
}

/** 工程师发送的提单快捷入口消息,渲染成可点击卡片。 */
const isTicketEntry = (msg) =>
  msg.senderType === 'ENGINEER' && msg.content === TICKET_ENTRY_MESSAGE

// ---------------------------------------------------------------- 一轮对话后的解决确认

/** 最近一条 AI 实际回答(欢迎语与拒答不算):解决确认只挂在这一条下面。 */
const lastAiAnswer = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i]
    if (m.senderType === 'AI' && !m.local && !m.refusalReason && m.replyType !== 'CLARIFY' && m.content) return m
  }
  return null
})

const showAnswerFeedback = (msg) =>
  msg.senderType === 'AI' && !msg.local && msg.id === lastAiAnswer.value?.id &&
  !sending.value && !aiThinking.value && (msg.feedback !== null || isAiHandling.value)

function resetQueueStatus() {
  queueStatus.value = { assigned: false, waitingCount: 0 }
}

async function refreshQueueStatus() {
  if (!session.value?.sessionId || !isWaitingHuman.value) {
    resetQueueStatus()
    return
  }
  try {
    const res = await consultationApi.queueStatus(session.value.sessionId)
    queueStatus.value = {
      assigned: res?.assigned === true,
      waitingCount: Number(res?.waitingCount ?? res?.waiting_count ?? 0)
    }
  } catch (e) {
    // 排队人数只是辅助信息，接口失败时隐藏，不能阻断聊天状态轮询。
    resetQueueStatus()
  }
}

// ---------------------------------------------------------------- 轮询与工具

async function refreshStatus() {
  if (!session.value || isTerminal.value) return
  const sessionId = session.value.sessionId
  const revision = sessionRevision
  const isCurrent = () => session.value?.sessionId === sessionId && revision === sessionRevision
  try {
    const detail = await consultationApi.get(sessionId)
    if (!isCurrent() || isTerminal.value || closing.value || cancelingQueue.value) return
    if (detail.status !== session.value.status) {
      const before = session.value.status
      session.value.status = detail.status
      session.value.current_engineer_id = detail.current_engineer_id
      if (before === 'WAITING_ENGINEER' && detail.status === 'HUMAN_ACTIVE') {
        ElMessage.success('工程师已接入')
      } else if (detail.status === 'PENDING_CONFIRMATION') {
        ElMessage.success('工程师已提交解决结论，请确认')
      }
    }
    await refreshQueueStatus()
    if (!isCurrent()) return
    // 人工阶段轮询拉取新消息,工程师回复无需手动刷新
    if (!isAiHandling.value) {
      const page = await consultationApi.listMessages(sessionId)
      if (!isCurrent()) return
      const items = page?.items || []
      const existing = messages.value.filter(m => m.serverId)
      if (items.length !== existing.length || items.some((item, index) =>
        item.message_id !== existing[index]?.serverId || item.content !== existing[index]?.content ||
        item.withdrawn_at !== existing[index]?.withdrawnAt ||
        JSON.stringify(item.attachments || []) !== JSON.stringify(existing[index]?.attachments || []))) {
        messages.value = withGreeting(items.map(toLocalMessage))
        scrollToBottom()
      }
    }
    if (isTerminal.value) finishSession(session.value.status)
  } catch (e) {
    // 轮询失败静默,不打断对话
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(refreshStatus, 5000)
}
function stopPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
}

const followLatest = ref(true)
const hasUnreadMessages = ref(false)
function onChatScroll() {
  const el = scrollRef.value
  if (!el) return
  followLatest.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80
  if (followLatest.value) hasUnreadMessages.value = false
}
function scrollToBottom(force = false) {
  if (!force && !followLatest.value) {
    hasUnreadMessages.value = true
    return
  }
  hasUnreadMessages.value = false
  followLatest.value = true
  nextTick(() => {
    const el = scrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}
function focusInput() {
  nextTick(() => inputRef.value?.focus())
}

const rowClass = (msg) => (msg.senderType === 'EMPLOYEE' ? 'row-right' : 'row-left')
const bubbleClass = (msg) => 'bubble-' + msg.senderType.toLowerCase()
const avatarOf = (t) => ({ EMPLOYEE: '我', AI: 'AI', ENGINEER: '工', SYSTEM: '系' }[t] || '?')
const senderLabel = (msg) =>
  ({ EMPLOYEE: '我', AI: 'AI 客服', ENGINEER: '工程师', SYSTEM: '系统' }[msg.senderType] || msg.senderType)
const refusalText = (reason) => REFUSAL_REASON[reason] || reason
const formatTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

onMounted(autoStart)
onUnmounted(stopPolling)
</script>

<style scoped>
.chat-input { position: relative; }
.attachment-dragging { outline: 2px dashed var(--el-color-primary); outline-offset: -4px; }
.attachment-drop-hint { position: absolute; inset: 8px; z-index: 5; display: grid; place-items: center; border: 2px dashed var(--el-color-primary); border-radius: 10px; background: var(--el-color-primary-light-9); color: var(--el-text-color-primary); pointer-events: none; font-weight: 600; }
.consultation-chat { width: 100%; }
.panel { border-radius: 10px; }

/* 初始化 */
.booting { min-height: 520px; border-radius: 10px; }

.state-banner { margin-bottom: 12px; }
.banner-actions { margin-top: 8px; display: flex; gap: 8px; }
.queue-count { margin-left: 8px; color: var(--el-color-primary); }
.queue-count strong { font-weight: 700; }

/* 转人工分类 */
.category-options { display: grid; grid-template-columns: 1fr; gap: 8px; width: 100%; }
.category-options :deep(.el-radio) { margin-right: 0; width: 100%; }
.category-options :deep(.el-radio__label) { display: flex; align-items: center; gap: 8px; }
.category-number {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 50%;
  color: var(--el-color-primary); background: var(--el-color-primary-light-9);
  font-size: 12px; font-weight: 600;
}

/* 消息流 */
.chat-body {
  height: 460px; overflow-y: auto; padding: 8px 4px;
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
.bubble-employee { background: var(--el-color-primary); border-color: var(--el-color-primary); color: #fff; }
.bubble-system {
  background: transparent; border: none; color: var(--el-text-color-secondary);
  font-size: 13px; padding: 4px 0;
}
.bubble-refusal { background: var(--el-color-warning-light-9); border-color: var(--el-color-warning-light-5); }
.refusal-head { display: flex; align-items: center; gap: 6px; font-weight: 600; color: var(--el-color-warning); }
.refusal-reason { margin: 8px 0 12px; }
.refusal-actions { display: flex; gap: 8px; }

/* 工程师提单快捷入口卡片 */
.bubble-ticket-entry {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-7);
}
.ticket-entry-head {
  display: flex; align-items: center; gap: 6px;
  font-weight: 600; color: var(--el-color-primary);
}
.ticket-entry-desc { margin: 8px 0 12px; font-size: 13px; color: var(--el-text-color-regular); }
.ticket-entry-actions { display: flex; gap: 8px; }

/* 引用 */
.citations { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--el-border-color); }
.general-answer-note {
  margin-top: 8px; padding: 6px 10px; border-radius: 6px;
  background: var(--el-color-info-light-9);
  font-size: 12px; color: var(--el-text-color-secondary);
  display: flex; align-items: center; gap: 6px;
}
.citations-title {
  display: flex; align-items: center; gap: 4px; font-size: 12px;
  color: var(--el-text-color-secondary); margin-bottom: 6px;
}
.citation-tag { margin-right: 6px; cursor: pointer; }
.citation-pop-title { font-weight: 600; margin-bottom: 6px; }
.citation-pop-snippet { font-size: 13px; line-height: 1.6; color: var(--el-text-color-regular); }
.citation-pop-meta {
  margin-top: 8px; font-size: 11px; color: var(--el-text-color-placeholder); font-family: monospace;
}

/* 解决反馈 */
.answer-feedback {
  margin-top: 10px; padding-top: 10px;
  border-top: 1px dashed var(--el-border-color);
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.answer-feedback-label { font-size: 12px; color: var(--el-text-color-secondary); }
.feedback-resolved,
.feedback-unresolved { font-size: 12px; color: var(--el-text-color-secondary); }
.feedback-unresolved { display: inline-flex; align-items: center; gap: 2px; }
.feedback-unresolved :deep(.el-link) { font-size: 12px; }

/* 终态:开始新咨询 */
.new-topic { margin-top: 12px; text-align: center; padding: 8px 0; }

/* 思考动画 */
.thinking { display: flex; align-items: center; gap: 4px; }
.thinking-text { margin-left: 6px; font-size: 13px; color: var(--el-text-color-secondary); }
.dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--el-color-primary);
  animation: blink 1.4s infinite both;
}
.dot:nth-child(2) { animation-delay: .2s; }
.dot:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0%, 80%, 100% { opacity: .25; } 40% { opacity: 1; } }

/* 输入区 */
.chat-input { margin-top: 12px; }
.input-toolbar { display: flex; justify-content: flex-end; margin-bottom: 4px; }
.chat-actions { margin-top: 8px; display: flex; justify-content: space-between; align-items: center; }
.chat-actions-left { display: flex; gap: 8px; }

/* 独立客服页面：对话流滚动，操作区保持可见。 */
.chat-panel { border-radius: 16px; }
.chat-panel :deep(.el-card__header) { padding: 18px 24px; }
.chat-panel :deep(.el-card__body) { display: flex; flex-direction: column; padding: 0; height: clamp(500px, calc(100dvh - 325px), 1000px); }
.new-message-cue { align-self: center; flex-shrink: 0; padding: 8px 16px; margin: 4px 0 10px; border: 1px solid var(--el-color-primary-light-7); border-radius: 20px; color: var(--el-color-primary); background: var(--el-color-primary-light-9); font: inherit; font-size: 12px; cursor: pointer; }
.conversation-header, .conversation-identity { display: flex; align-items: center; gap: 12px; }
.conversation-header { justify-content: space-between; }
.small-assistant { display: grid; place-items: center; width: 40px; height: 40px; background: var(--el-color-primary-light-9); color: var(--el-color-primary); border-radius: 12px; font-size: 23px; }
.conversation-identity strong { display: block; font-size: 15px; font-weight: 600; }
.conversation-identity span { display: block; margin-top: 5px; font-size: 12px; color: var(--el-text-color-regular); }
.state-banner { flex-shrink: 0; margin: 12px 16px 0; width: auto; }
.chat-body { flex: 1; min-height: 0; height: auto; border-radius: 0; padding: 24px 20px; background: var(--el-bg-color); overscroll-behavior: contain; }
.chat-welcome { max-width: 600px; margin: 0 auto; padding: 0 12px 12px; text-align: center; }
.welcome-mark { width: 44px; height: 44px; display: grid; place-items: center; margin: 0 auto 12px; border-radius: 14px; color: var(--el-color-primary); background: var(--el-color-primary-light-9); font-size: 25px; }
.chat-welcome h2 { margin: 0 0 12px; font-size: 25px; font-weight: 600; color: var(--el-text-color-primary); }
.chat-welcome p { margin: 0; color: var(--el-text-color-regular); font-size: 14px; line-height: 1.8; }
.suggestion-label { margin: 20px 0 12px; font-size: 12px; text-align: left; color: var(--el-text-color-regular); }
.suggestion-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.suggestion-card { display: flex; align-items: center; gap: 12px; padding: 16px 14px; border: 1px solid var(--el-border-color-lighter); border-radius: 10px; background: var(--el-fill-color-extra-light); color: var(--el-text-color-primary); text-align: left; cursor: pointer; font-family: inherit; transition: border-color .2s, background .2s; }
.suggestion-card:hover { border-color: var(--el-color-primary); background: var(--el-color-primary-light-9); }
.suggestion-card:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 3px; }
.suggestion-card > .el-icon { color: var(--el-color-primary); font-size: 20px; flex-shrink: 0; }
.suggestion-card span { flex: 1; min-width: 0; }
.suggestion-card strong { display: block; font-size: 13px; font-weight: 500; }
.suggestion-card small { display: block; margin-top: 6px; font-size: 12px; line-height: 1.5; color: var(--el-text-color-regular); }
.suggestion-card > .suggestion-arrow { color: var(--el-text-color-secondary); font-size: 13px; }
.avatar-ai { background: var(--el-color-primary); border-radius: 10px; }
.avatar-employee { background: var(--el-color-primary-light-9); color: var(--el-color-primary); border-radius: 10px; }
.msg-main { max-width: 85%; min-width: 0; }
.msg-bubble { padding: 12px 16px; font-size: 16px; }
.bubble-ai { background: var(--el-fill-color-light); border-color: transparent; }
.msg-time { font-size: 12px; color: var(--el-text-color-regular); }
.chat-input { flex-shrink: 0; margin: 0; padding: 10px 24px 16px; border-top: 1px solid var(--el-border-color-lighter); }
.input-toolbar { justify-content: space-between; align-items: center; margin-bottom: 6px; }
.input-toolbar label { font-size: 12px; color: var(--el-text-color-regular); }
.chat-input :deep(.el-textarea__inner) { border-radius: 10px; padding: 12px 14px 24px; font-family: inherit; font-size: 16px; }
.chat-actions { margin-top: 12px; gap: 10px; }
.chat-actions .el-button { min-height: 36px; }
.chat-actions-left { gap: 0; flex-wrap: wrap; }
.input-hint { display: flex; justify-content: space-between; gap: 8px; margin-top: 12px; font-size: 12px; color: var(--el-text-color-regular); }
.new-topic { flex-shrink: 0; border-top: 1px solid var(--el-border-color-lighter); padding: 16px; margin: 0; }
.startup-error, .booting { min-height: 560px; border: 1px solid var(--el-border-color-lighter); border-radius: 16px; background: var(--el-bg-color); }
.startup-error { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; text-align: center; box-sizing: border-box; }
.error-icon { color: var(--el-color-warning); font-size: 38px; }
.startup-error h2 { font-size: 20px; margin: 20px 0 10px; }
.startup-error p { font-size: 14px; line-height: 1.7; color: var(--el-text-color-regular); margin-bottom: 24px; overflow-wrap: anywhere; }
@media (max-width: 760px) {
  .chat-panel :deep(.el-card__header) { padding: 14px 12px; }
  .chat-panel :deep(.el-card__body) { height: max(390px, calc(100dvh - 365px)); }
  .conversation-header { gap: 8px; }
  .conversation-identity { gap: 8px; }
  .conversation-identity span { display: none; }
  .conversation-identity strong { font-size: 13px; }
  .small-assistant { width: 32px; height: 32px; }
  .conversation-header > .el-tag { font-size: 11px; }
  .chat-body { padding: 16px 10px; }
  .chat-welcome { padding: 4px; }
  .chat-welcome h2 { font-size: 18px; margin-bottom: 8px; }
  .chat-welcome p { font-size: 12px; line-height: 1.6; }
  .welcome-mark { display: none; }
  .suggestion-label { margin: 14px 0 8px; }
  .suggestion-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .suggestion-card { padding: 10px 8px; gap: 7px; min-height: 48px; }
  .suggestion-card strong { font-size: 12px; }
  .suggestion-card small, .suggestion-card .suggestion-arrow { display: none; }
  .msg-row { padding: 0; gap: 6px; }
  .msg-avatar { width: 28px; height: 28px; font-size: 11px; }
  .msg-main { max-width: calc(100% - 34px); }
  .chat-input { padding: 8px 12px 12px; }
  .chat-actions { flex-wrap: wrap; }
  .chat-actions .el-button { padding: 8px 10px; min-height: 44px; }
  .input-hint { flex-direction: column; font-size: 11px; }
  .refusal-actions { flex-wrap: wrap; }
  .citation-tag { max-width: 100%; height: auto; min-height: 28px; white-space: normal; }
}
@media (prefers-reduced-motion: reduce) {
  .dot { animation: none; opacity: .7; }
  .suggestion-card { transition: none; }
}
</style>
