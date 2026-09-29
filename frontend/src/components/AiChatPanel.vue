<template>
  <div class="ai-chat-panel">
    <!-- ===== 会话状态条 ===== -->
    <div class="status-bar">
      <el-tag :type="statusTagType" size="small" effect="light">{{ statusLabel }}</el-tag>
      <el-button
        v-if="sessionId"
        size="small"
        text
        type="primary"
        @click="resetSession"
      >发起新咨询</el-button>
    </div>

    <!-- ===== 消息区 ===== -->
    <div ref="msgBoxRef" class="msg-box">
      <div v-if="messages.length === 0" class="empty-tip">
        👋 你好，我是 IT 智能助手。请描述你遇到的问题（如：VPN 连不上、邮箱收不到邮件），我会先尝试帮你解决。
      </div>
      <template v-for="(m, i) in messages" :key="i">
        <!-- 系统提示:居中灰条 -->
        <div v-if="m.sender_type === 'SYSTEM'" class="sys-msg">{{ m.content }}</div>
        <!-- 员工本人:右侧气泡 -->
        <div v-else-if="m.sender_type === 'USER'" class="msg-row right">
          <div class="bubble user">{{ m.content }}</div>
        </div>
        <!-- AI / 客服:左侧气泡 -->
        <div v-else class="msg-row left">
          <div class="sender-name">{{ m.sender_type === 'AI' ? '🤖 AI 助手' : '👨‍💼 ' + (m.sender_name || '客服') }}</div>
          <div class="bubble" :class="m.sender_type === 'AI' ? 'ai' : 'agent'">
            <span style="white-space: pre-wrap">{{ m.content }}</span>
            <!-- AI 回答的参考资料 -->
            <div v-if="m.sources && m.sources.length" class="sources">
              <el-tag
                v-for="s in m.sources"
                :key="s.id"
                size="small"
                type="info"
                effect="plain"
              >📄 {{ s.title }}</el-tag>
            </div>
          </div>
        </div>
      </template>
      <div v-if="sending" class="msg-row left">
        <div class="bubble ai">AI 正在思考…</div>
      </div>
    </div>

    <!-- ===== AI 反馈按钮(AI 解答后:已解决 / 转人工 / 直接结束) ===== -->
    <div v-if="status === 'AI_HANDLING' && lastIsAi && !sending" class="feedback-bar">
      <span class="feedback-tip">以上方案是否解决了你的问题？</span>
      <el-button type="success" size="small" @click="onResolve">✅ 已解决</el-button>
      <el-button type="warning" size="small" @click="onEscalate">❌ 未解决，转人工</el-button>
      <el-button size="small" text @click="onClose">直接结束</el-button>
    </div>

    <!-- ===== 结束态提示 ===== -->
    <el-alert v-if="endedTip" :title="endedTip" type="info" :closable="false" class="ended-alert" />

    <!-- ===== 输入区 ===== -->
    <div class="input-bar">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        resize="none"
        :placeholder="inputPlaceholder"
        :disabled="inputDisabled"
        @keydown.enter.exact.prevent="onSend"
      />
      <el-button
        type="primary"
        :loading="sending"
        :disabled="inputDisabled || !input.trim()"
        @click="onSend"
      >发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { aiApi } from '../api/index.js'
import { useUserStore } from '../stores/user.js'

const userStore = useUserStore()

// ---- 会话状态 ----
const sessionId = ref(null)
const status = ref('')          // AI_HANDLING / WAITING_HUMAN / HUMAN_HANDLING / RESOLVED / TO_TICKET / REJECTED / CLOSED
const messages = ref([])
const input = ref('')
const sending = ref(false)
const msgBoxRef = ref(null)
let ws = null

const STATUS_LABELS = {
  AI_HANDLING: 'AI 解答中',
  WAITING_HUMAN: '排队等待客服',
  HUMAN_HANDLING: '人工客服沟通中',
  RESOLVED: '已解决',
  TO_TICKET: '已转工单',
  REJECTED: '客服已关闭',
  CLOSED: '已结束'
}
const statusLabel = computed(() => STATUS_LABELS[status.value] || '新咨询')
const statusTagType = computed(() => ({
  AI_HANDLING: 'primary', WAITING_HUMAN: 'warning', HUMAN_HANDLING: 'warning',
  RESOLVED: 'success', TO_TICKET: 'success', REJECTED: 'info', CLOSED: 'info'
}[status.value] || 'info'))

// 最后一条消息是 AI 回答时才显示反馈按钮
const lastIsAi = computed(() => messages.value.length > 0
  && messages.value[messages.value.length - 1].sender_type === 'AI')

// 结束态提示文案
const endedTip = computed(() => {
  if (status.value === 'RESOLVED') return '🎉 问题已解决，本次咨询结束。可点击右上角「发起新咨询」。'
  if (status.value === 'TO_TICKET') return '📋 已生成工单，工程师会尽快处理，可在「我的工单」中查看进度。'
  if (status.value === 'REJECTED') return '本次咨询已被客服关闭。如有其他问题可「发起新咨询」。'
  if (status.value === 'CLOSED') return '本次咨询已结束。'
  return ''
})

// 输入框:AI 阶段与人工阶段可输入,排队中禁用;CLOSED 允许继续输入以发起新咨询
const inputDisabled = computed(() =>
  sending.value || ['WAITING_HUMAN', 'RESOLVED', 'TO_TICKET', 'REJECTED'].includes(status.value))
const inputPlaceholder = computed(() => {
  if (status.value === 'WAITING_HUMAN') return '客服尚未接入，请稍候…'
  if (status.value === 'HUMAN_HANDLING') return '与客服沟通中，回车发送…'
  if (status.value === 'CLOSED') return '咨询已结束，输入内容可发起新咨询…'
  if (inputDisabled.value) return '本次咨询已结束，请发起新咨询'
  return '描述你的 IT 问题，回车发送…'
})

// ---- 初始化:尝试恢复最近一个进行中的会话 ----
onMounted(async () => {
  try {
    const res = await aiApi.mySessions()
    const active = (res.data || []).find(s =>
      ['AI_HANDLING', 'WAITING_HUMAN', 'HUMAN_HANDLING'].includes(s.status))
    if (active) {
      sessionId.value = active.id
      status.value = active.status
      const msgRes = await aiApi.messages(active.id)
      messages.value = msgRes.data || []
      maybeConnectWs()
      scrollToBottom()
    }
  } catch (e) {
    console.warn('恢复会话失败', e)
  }
})

onUnmounted(() => closeWs())

// ---- 发送消息 ----
async function onSend() {
  const question = input.value.trim()
  if (!question) return
  // 结束态:自动重置为新会话再发送
  if (['CLOSED', 'RESOLVED', 'TO_TICKET', 'REJECTED'].includes(status.value)) {
    resetSession()
  }
  // 人工阶段:走 WebSocket 实时聊天
  if (status.value === 'HUMAN_HANDLING') {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'msg', session_id: sessionId.value, content: question }))
      messages.value.push({ sender_type: 'USER', content: question })
      input.value = ''
      scrollToBottom()
    } else {
      ElMessage.warning('连接已断开，请刷新页面重试')
    }
    return
  }
  // AI 阶段:走 REST 问答
  sending.value = true
  messages.value.push({ sender_type: 'USER', content: question })
  input.value = ''
  scrollToBottom()
  try {
    const res = await aiApi.chat({ session_id: sessionId.value, question })
    sessionId.value = res.data.session_id
    status.value = res.data.status
    messages.value.push({ sender_type: 'AI', content: res.data.answer, sources: res.data.sources })
  } catch (e) {
    ElMessage.error(e.message || 'AI 服务暂不可用')
    messages.value.push({ sender_type: 'SYSTEM', content: '发送失败：' + (e.message || '网络错误') })
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

// ---- 反馈动作 ----
async function onResolve() {
  await aiApi.resolve(sessionId.value)
  status.value = 'RESOLVED'
  // 人工阶段 WS 在线时由服务端实时推送系统消息,避免重复;AI 阶段无 WS 需本地追加
  if (!ws) messages.value.push({ sender_type: 'SYSTEM', content: '员工确认问题已解决，会话结束' })
}

async function onEscalate() {
  await ElMessageBox.confirm('将转接人工客服，客服会看到本次对话记录。确认转人工？', '转人工', {
    confirmButtonText: '转人工', cancelButtonText: '再想想', type: 'warning'
  })
  await aiApi.escalate(sessionId.value)
  status.value = 'WAITING_HUMAN'
  messages.value.push({ sender_type: 'SYSTEM', content: '已转接人工客服，请稍候，客服接入后可直接在此对话' })
  connectWs()
}

async function onClose() {
  await aiApi.close(sessionId.value)
  status.value = 'CLOSED'
  messages.value.push({ sender_type: 'SYSTEM', content: '员工已结束本次咨询' })
}

// ---- WebSocket(人工阶段) ----
function maybeConnectWs() {
  if (['WAITING_HUMAN', 'HUMAN_HANDLING'].includes(status.value)) connectWs()
}

function connectWs() {
  closeWs()
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${scheme}://${location.host}/ws/ai/chat?token=${encodeURIComponent(userStore.token)}&sessionId=${sessionId.value}`)
  ws.onmessage = async (event) => {
    let data
    try { data = JSON.parse(event.data) } catch { return }
    if (data.type === 'msg') {
      // 客服发言
      messages.value.push(data)
      scrollToBottom()
    } else if (data.type === 'sys') {
      // 系统提示(客服接入/已解决/已转工单等),刷新会话状态
      messages.value.push({ sender_type: 'SYSTEM', content: data.content })
      scrollToBottom()
      await refreshStatus()
    }
  }
  ws.onclose = () => { ws = null }
}

function closeWs() {
  if (ws) { ws.close(); ws = null }
}

// 会话状态刷新(客服接入/驳回/转工单后同步本地状态)
async function refreshStatus() {
  try {
    const res = await aiApi.mySessions()
    const current = (res.data || []).find(s => s.id === sessionId.value)
    if (current) status.value = current.status
  } catch (e) { /* 忽略,下条系统消息会再次触发 */ }
}

// ---- 新咨询 ----
function resetSession() {
  closeWs()
  sessionId.value = null
  status.value = ''
  messages.value = []
  input.value = ''
}

function scrollToBottom() {
  nextTick(() => {
    if (msgBoxRef.value) msgBoxRef.value.scrollTop = msgBoxRef.value.scrollHeight
  })
}
</script>

<style scoped>
.ai-chat-panel {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 220px);
  min-height: 420px;
}
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.msg-box {
  flex: 1;
  overflow-y: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-fill-color-lighter);
}
.empty-tip { color: var(--el-text-color-secondary); text-align: center; margin-top: 40px; line-height: 1.8; }
.msg-row { display: flex; margin-bottom: 10px; }
.msg-row.right { justify-content: flex-end; }
.msg-row.left { flex-direction: column; align-items: flex-start; }
.sender-name { font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 2px; }
.bubble {
  max-width: 72%;
  padding: 8px 12px;
  border-radius: 10px;
  line-height: 1.6;
  word-break: break-word;
}
.bubble.user { background: var(--el-color-primary); color: #fff; }
.bubble.ai { background: #fff; border: 1px solid var(--el-border-color-lighter); }
.bubble.agent { background: #fdf6ec; border: 1px solid #f5dab1; }
html.dark .bubble.ai { background: var(--el-bg-color-overlay); }
html.dark .bubble.agent { background: #2b2111; }
.sys-msg {
  text-align: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 8px 0;
}
.sources { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px; }
.feedback-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 4px;
}
.feedback-tip { font-size: 13px; color: var(--el-text-color-secondary); }
.ended-alert { margin: 8px 0; }
.input-bar { display: flex; gap: 8px; margin-top: 8px; align-items: flex-end; }
</style>
