<template>
  <div class="consultation-chat">
    <!-- 初始化:自动恢复进行中的咨询,没有则新开 AI 会话(进去就是对话框) -->
    <div v-if="booting" v-loading="true" element-loading-text="正在进入对话…"
         class="booting"></div>

    <!-- ===== 聊天面板 ===== -->
    <el-card v-else-if="session" shadow="never" class="panel chat-panel">
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
                <div class="msg-text">{{ msg.content }}</div>

                <!-- 通用能力回答标识(冷启动放宽策略:无知识库依据,提示可沉淀) -->
                <div v-if="msg.generalAnswer" class="general-answer-note">
                  <el-icon><MagicStick /></el-icon>
                  这条回答基于 AI 通用知识，暂无知识库依据。点击「已解决」可保存有帮助反馈，供后续知识整理与审核参考。
                </div>

                <!-- 有知识依据时展示经过校验的真实引用 -->
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
                               :disabled="closing || cancelingQueue" @click="resolveAnswer(msg)">✅ 已解决</el-button>
                    <el-button size="small" type="warning" :disabled="msg.feedbackPending || closing || cancelingQueue"
                               @click="markUnresolved(msg)">❌ 未解决</el-button>
                  </template>
                  <span v-else-if="msg.feedback === 'resolved'" class="feedback-resolved">✅ 已标记为解决</span>
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

        <!-- 输入区 -->
        <div v-if="!isTerminal" class="chat-input">
          <div class="input-toolbar">
            <el-button text type="danger" :icon="Close" :loading="closing"
                       :disabled="cancelingQueue || transferring" @click="closeSession">
              结束对话
            </el-button>
          </div>
          <el-input ref="inputRef" v-model="draft" type="textarea" :rows="3" resize="none"
                    :maxlength="inputMaxLength" show-word-limit
                    :placeholder="inputPlaceholder" :disabled="sending || aiThinking || inputDisabled || closing || cancelingQueue"
                    @keydown.enter.exact.prevent="send" />
          <div class="chat-actions">
            <div class="chat-actions-left">
              <!-- PRD 8.1:AI 对话中必须始终提供转人工和提交工单入口 -->
              <el-button v-if="canTransfer" :icon="Service" :disabled="closing || cancelingQueue" @click="openTransfer()">转人工</el-button>
              <el-button :icon="Tickets" @click="goCreateTicket">提交工单</el-button>
            </div>
            <el-button type="primary" :icon="Promotion" :loading="sending || aiThinking"
                       :disabled="!draft.trim() || inputDisabled || closing || cancelingQueue" @click="send">
              发送
            </el-button>
          </div>
        </div>

        <!-- 终态:开新会话 -->
        <div v-else class="new-topic">
          <el-button type="primary" :icon="ChatDotRound" :loading="creating" @click="startAi">
            开始新咨询
          </el-button>
        </div>
      </el-card>

    <!-- 转人工对话框 -->
    <el-dialog v-model="transferVisible" title="转人工咨询" width="460px" append-to-body
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
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound, Service, Close, Promotion, Tickets,
  Document, WarningFilled, CircleCheck, RefreshLeft, MagicStick
} from '@element-plus/icons-vue'
import {
  consultationApi, REFUSAL_REASON, TERMINAL_STATUS, TICKET_ENTRY_MESSAGE
} from '../api/consultation.js'

/**
 * 员工侧智能客服聊天面板(无外部布局假设):
 * 既挂在 App.vue 的全局抽屉里(对话框入口),也挂在 /consultation 整页路由上。
 * 状态、消息、转人工的领域规则全部在组件内部闭环。
 */

const emit = defineEmits(['navigate'])

const router = useRouter()

// 分类取自 it_consultation.category 种子数据的末级可路由分类
const categories = [
  { id: 'CAT-IT-DEVICE', name: '办公设备' },
  { id: 'CAT-IT-NETWORK', name: '网络访问' },
  { id: 'CAT-IT-ACCOUNT', name: '账号与权限' }
]

const session = ref(null)
const messages = ref([])
const draft = ref('')
const creating = ref(false)
const sending = ref(false)
const aiThinking = ref(false)
const loadingMessages = ref(false)
const booting = ref(false)
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
const canTransfer = computed(() => isAiHandling.value)
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
  try {
    await loadResumable()
    if (resumable.value.length) {
      await resumeSession(resumable.value[0])
    } else {
      await startAi()
    }
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    booting.value = false
    focusInput()
  }
}

/** 挂载时拉取本人进行中的咨询(OpenAPI 05 listConsultations,后端按 creator 过滤)。 */
async function loadResumable() {
  try {
    const page = await consultationApi.list(1, 20)
    resumable.value = (page?.items || [])
      .filter(s => !TERMINAL_STATUS.includes(s.status))
      .slice(0, 5)
  } catch (e) {
    // 列表失败不阻塞,按无进行中咨询处理
    resumable.value = []
  }
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
  } finally {
    creating.value = false
  }
}

async function startAi() {
  if (creating.value) return
  creating.value = true
  try {
    session.value = await consultationApi.create('AI')
    sessionRevision++
    draft.value = ''
    sending.value = false
    aiThinking.value = false
    queueStatus.value = { assigned: false, waitingCount: 0 }
    messages.value = []
    messages.value.push(createGreeting())
    scrollToBottom()
    startPolling()
  } catch (e) {
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
    ElMessage.error(e.message)
  } finally {
    loadingMessages.value = false
    scrollToBottom()
  }
}

/** 把服务端消息投影转成本地渲染结构。拒答消息由 AI 侧的固定话术标识。 */
function toLocalMessage(item) {
  return {
    id: item.message_id,
    serverId: item.message_id,
    senderType: item.sender_type || 'SYSTEM',
    content: item.content,
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

function pushLocal(senderType, content, extra = {}) {
  messages.value.push({
    id: `local-${++localSeq}`,
    senderType,
    content,
    ...(senderType === 'AI' ? { feedback: null } : {}),
    sentAt: new Date().toISOString(),
    ...extra
  })
  scrollToBottom()
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

async function send() {
  const text = draft.value.trim()
  if (!text || !session.value || isTerminal.value || inputDisabled.value || sending.value || aiThinking.value || closing.value || cancelingQueue.value) return
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
        if (!hasCitations) {
          pushLocal('SYSTEM', '这条回答来自 AI 的通用知识（暂无知识库依据）。如果对你有帮助，请点「已解决」，它会进入知识库审核队列，帮助更多同事。')
        } else if (res.suggestTransfer) {
          pushLocal('SYSTEM', '这个回答的把握不高，如果没解决问题建议转人工。')
        }
      }
    } catch (e) {
      if (!stillActive()) return
      // AI 故障不阻塞主链路:提示并保留转人工/提单入口(RD-013)
      pushLocal('SYSTEM', `AI 暂时不可用（${e.message}）。你可以转人工或直接提交工单。`)
    } finally {
      if (revision === sessionRevision) aiThinking.value = false
    }
    return
  }

  // 人工咨询消息
  sending.value = true
  try {
    await consultationApi.sendMessage(sessionId, text)
    if (!stillActive()) return
    pushLocal('EMPLOYEE', text)
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
      if (items.length !== messages.value.filter(m => m.serverId).length) {
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

function scrollToBottom() {
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
</style>
