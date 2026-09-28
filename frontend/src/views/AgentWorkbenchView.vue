<template>
  <div class="agent-workbench">
    <el-tabs v-model="tab" class="view-tabs">
      <el-tab-pane name="queue">
        <template #label>
          💬 会话队列
          <el-badge v-if="waitingCount" :value="waitingCount" :max="99" class="tab-badge" />
        </template>
      </el-tab-pane>
      <el-tab-pane name="knowledge">
        <template #label>📚 知识库管理</template>
      </el-tab-pane>
    </el-tabs>

    <!-- ================= 会话队列 ================= -->
    <el-row v-if="tab === 'queue'" :gutter="12">
      <!-- 左侧:会话列表 -->
      <el-col :span="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <span>待接入 / 处理中</span>
              <el-button size="small" text type="primary" @click="loadQueue">刷新</el-button>
            </div>
          </template>
          <el-empty v-if="!queue.length" description="暂无待处理会话" :image-size="60" />
          <div
            v-for="s in queue"
            :key="s.id"
            class="session-item"
            :class="{ active: selected?.id === s.id }"
            @click="selectSession(s)"
          >
            <div class="session-head">
              <el-tag size="small" :type="s.status === 'WAITING_HUMAN' ? 'danger' : 'warning'" effect="dark">
                {{ s.status === 'WAITING_HUMAN' ? '待接入' : '处理中' }}
              </el-tag>
              <span class="session-user">{{ s.user_id }}</span>
              <span class="session-time">{{ formatTime(s.update_time) }}</span>
            </div>
            <div class="session-summary">{{ s.summary || '(无摘要)' }}</div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧:对话窗口 -->
      <el-col :span="16">
        <el-card shadow="never" class="panel chat-panel">
          <template v-if="!selected">
            <el-empty description="选择左侧会话查看详情" />
          </template>
          <template v-else>
            <div class="chat-head">
              <span>会话 #{{ selected.id }} · {{ selected.user_id }}</span>
              <el-tag size="small" :type="statusTagType(selected.status)">{{ statusLabel(selected.status) }}</el-tag>
            </div>

            <!-- 消息记录 -->
            <div ref="msgBoxRef" class="msg-box">
              <template v-for="(m, i) in messages" :key="i">
                <div v-if="m.sender_type === 'SYSTEM'" class="sys-msg">{{ m.content }}</div>
                <div v-else-if="m.sender_type === 'AGENT'" class="msg-row right">
                  <div class="bubble agent">{{ m.content }}</div>
                </div>
                <div v-else class="msg-row left">
                  <div class="sender-name">{{ m.sender_type === 'AI' ? '🤖 AI' : '👤 员工' }}</div>
                  <div class="bubble" :class="m.sender_type === 'AI' ? 'ai' : 'user'">{{ m.content }}</div>
                </div>
              </template>
            </div>

            <!-- 待接入:接入按钮 -->
            <div v-if="selected.status === 'WAITING_HUMAN'" class="action-bar">
              <el-button type="primary" :loading="acting" @click="onAccept">接入会话</el-button>
            </div>

            <!-- 处理中(本人):聊天 + 处置动作 -->
            <template v-if="selected.status === 'HUMAN_HANDLING' && selected.agent_id === userStore.userId">
              <div class="input-bar">
                <el-input
                  v-model="input"
                  type="textarea"
                  :rows="2"
                  resize="none"
                  placeholder="回复员工,回车发送…"
                  @keydown.enter.exact.prevent="onSend"
                />
                <el-button type="primary" :disabled="!input.trim()" @click="onSend">发送</el-button>
              </div>
              <div class="action-bar">
                <el-button type="success" size="small" @click="onResolve">✅ 标记已解决</el-button>
                <el-button type="primary" size="small" @click="ticketDialog = true">📋 转工单</el-button>
                <el-button type="danger" size="small" plain @click="rejectDialog = true">🚫 驳回</el-button>
              </div>
            </template>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <!-- ================= 知识库管理 ================= -->
    <el-row v-if="tab === 'knowledge'" :gutter="12">
      <el-col :span="9">
        <el-card shadow="never" class="panel">
          <template #header><span>录入知识（FAQ / SOP）</span></template>
          <el-form label-position="top">
            <el-form-item label="标题" required>
              <el-input v-model="kForm.title" maxlength="100" placeholder="如:VPN 连接失败排查指引" />
            </el-form-item>
            <el-form-item label="分类">
              <el-select v-model="kForm.category" style="width:100%">
                <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="知识内容" required>
              <el-input
                v-model="kForm.content"
                type="textarea"
                :rows="8"
                maxlength="5000"
                placeholder="把解决步骤写清楚,录入后会自动切片并向量化,立即参与 AI 检索"
              />
            </el-form-item>
            <el-button type="primary" :loading="kSaving" @click="onAddKnowledge">录入知识库</el-button>
          </el-form>
        </el-card>
      </el-col>
      <el-col :span="15">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <span>知识列表</span>
              <el-radio-group v-model="kSourceType" size="small" @change="loadKnowledge(1)">
                <el-radio-button value="">全部</el-radio-button>
                <el-radio-button value="MANUAL">手工录入</el-radio-button>
                <el-radio-button value="TICKET">工单回流</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <el-table :data="kList" size="small" stripe>
            <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
            <el-table-column prop="category" label="分类" width="80" />
            <el-table-column label="来源" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.source_type === 'TICKET' ? 'success' : 'primary'" effect="plain">
                  {{ row.source_type === 'TICKET' ? '工单回流' : row.source_type === 'MANUAL' ? '手工' : row.source_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="content" label="内容" min-width="220" show-overflow-tooltip />
            <el-table-column label="操作" width="70">
              <template #default="{ row }">
                <el-button size="small" text type="danger" @click="onDeleteKnowledge(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="kPage"
            :page-size="10"
            :total="kTotal"
            layout="total, prev, pager, next"
            class="pagination"
            @current-change="loadKnowledge"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 驳回弹窗 ===== -->
    <el-dialog v-model="rejectDialog" title="驳回会话" width="420px">
      <el-input
        v-model="rejectReason"
        type="textarea"
        :rows="3"
        maxlength="200"
        placeholder="驳回原因(必填),如:重复问题,参考知识库已有指引 / 员工已自行解决"
      />
      <template #footer>
        <el-button @click="rejectDialog = false">取消</el-button>
        <el-button type="danger" :loading="acting" @click="onReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- ===== 转工单弹窗 ===== -->
    <el-dialog v-model="ticketDialog" title="生成工单" width="520px">
      <el-form label-position="top">
        <el-form-item label="工单标题">
          <el-input v-model="tForm.title" maxlength="50" placeholder="留空则使用会话摘要" />
        </el-form-item>
        <el-form-item label="问题分类" required>
          <el-radio-group v-model="tForm.category">
            <el-radio-button v-for="c in categories" :key="c" :value="c">{{ c }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="优先级">
          <el-radio-group v-model="tForm.priority">
            <el-radio-button value="高">高</el-radio-button>
            <el-radio-button value="中">中</el-radio-button>
            <el-radio-button value="低">低</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="问题描述">
          <el-input
            v-model="tForm.description"
            type="textarea"
            :rows="5"
            maxlength="500"
            placeholder="留空则自动用对话记录生成"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ticketDialog = false">取消</el-button>
        <el-button type="primary" :loading="acting" :disabled="!tForm.category" @click="onToTicket">确认生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentApi, knowledgeApi } from '../api/index.js'
import { useUserStore } from '../stores/user.js'

const userStore = useUserStore()
const tab = ref('queue')
const categories = ['硬件', '软件', '网络', '账号', '其他']

// ================= 会话队列 =================
const queue = ref([])
const selected = ref(null)
const messages = ref([])
const input = ref('')
const acting = ref(false)
const msgBoxRef = ref(null)
let ws = null

const waitingCount = computed(() => queue.value.filter(s => s.status === 'WAITING_HUMAN').length)

const STATUS_LABELS = {
  WAITING_HUMAN: '待接入', HUMAN_HANDLING: '人工处理中',
  RESOLVED: '已解决', TO_TICKET: '已转工单', REJECTED: '已驳回', CLOSED: '已结束'
}
const statusLabel = (s) => STATUS_LABELS[s] || s
const statusTagType = (s) => ({ WAITING_HUMAN: 'danger', HUMAN_HANDLING: 'warning', RESOLVED: 'success', TO_TICKET: 'success' }[s] || 'info')

function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '' }

async function loadQueue() {
  try {
    const res = await agentApi.queue()
    queue.value = res.data || []
    // 选中项状态同步(如被其他客服接入)
    if (selected.value) {
      selected.value = queue.value.find(s => s.id === selected.value.id) || selected.value
    }
  } catch (e) {
    ElMessage.error(e.message || '加载队列失败')
  }
}

async function selectSession(s) {
  selected.value = s
  const res = await agentApi.messages(s.id)
  messages.value = res.data || []
  scrollToBottom()
}

// ---- 客服动作 ----
async function onAccept() {
  acting.value = true
  try {
    const res = await agentApi.accept(selected.value.id)
    ElMessage.success('已接入,可以开始沟通')
    selected.value = res.data
    await selectSession(res.data)
    loadQueue()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    acting.value = false
  }
}

async function onResolve() {
  await ElMessageBox.confirm('确认员工问题已解决？会话将关闭。', '标记已解决', { type: 'success' })
  await agentApi.resolve(selected.value.id)
  ElMessage.success('已标记解决')
  finishSession('RESOLVED')
}

async function onReject() {
  if (!rejectReason.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  acting.value = true
  try {
    await agentApi.reject(selected.value.id, { reason: rejectReason.value.trim() })
    ElMessage.success('已驳回')
    rejectDialog.value = false
    rejectReason.value = ''
    finishSession('REJECTED')
  } finally {
    acting.value = false
  }
}

const rejectDialog = ref(false)
const rejectReason = ref('')
const ticketDialog = ref(false)
const tForm = ref({ title: '', category: '', priority: '中', description: '' })

async function onToTicket() {
  acting.value = true
  try {
    const res = await agentApi.toTicket(selected.value.id, {
      title: tForm.value.title || undefined,
      category: tForm.value.category,
      priority: tForm.value.priority,
      description: tForm.value.description || undefined
    })
    ElMessage.success(`已生成工单 ${res.data?.ticket_id || ''}`)
    ticketDialog.value = false
    tForm.value = { title: '', category: '', priority: '中', description: '' }
    finishSession('TO_TICKET')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    acting.value = false
  }
}

// 会话终态处理:刷新队列与选中态
function finishSession(status) {
  if (selected.value) selected.value = { ...selected.value, status }
  loadQueue()
}

// ---- WebSocket:接收队列提醒 + 对方发言 ----
function connectWs() {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${scheme}://${location.host}/ws/ai/chat?token=${encodeURIComponent(userStore.token)}`)
  ws.onmessage = (event) => {
    let data
    try { data = JSON.parse(event.data) } catch { return }
    if (data.type === 'queue') {
      loadQueue()
    } else if (data.type === 'msg' && selected.value && data.session_id === selected.value.id) {
      messages.value.push(data)
      scrollToBottom()
    } else if (data.type === 'sys' && selected.value && data.session_id === selected.value.id) {
      messages.value.push({ sender_type: 'SYSTEM', content: data.content })
      loadQueue()
      scrollToBottom()
    }
  }
  ws.onclose = () => {
    ws = null
    // 简单重连:5 秒后重试(页面关闭时静默失败)
    setTimeout(() => { if (tab.value !== undefined) connectWs() }, 5000)
  }
}

function onSend() {
  const content = input.value.trim()
  if (!content || !selected.value) return
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    ElMessage.warning('连接已断开,正在重连…')
    connectWs()
    return
  }
  ws.send(JSON.stringify({ type: 'msg', session_id: selected.value.id, content }))
  messages.value.push({ sender_type: 'AGENT', content })
  input.value = ''
  scrollToBottom()
}

// ================= 知识库管理 =================
const kForm = ref({ title: '', category: '其他', content: '' })
const kSaving = ref(false)
const kList = ref([])
const kTotal = ref(0)
const kPage = ref(1)
const kSourceType = ref('')

async function onAddKnowledge() {
  if (!kForm.value.title.trim() || kForm.value.content.trim().length < 10) {
    ElMessage.warning('请填写标题和至少 10 个字的知识内容')
    return
  }
  kSaving.value = true
  try {
    const res = await knowledgeApi.add(kForm.value)
    ElMessage.success(`录入成功,已切分为 ${res.data?.chunks || 1} 片`)
    kForm.value = { title: '', category: '其他', content: '' }
    loadKnowledge(1)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    kSaving.value = false
  }
}

async function loadKnowledge(page = kPage.value) {
  kPage.value = page
  const res = await knowledgeApi.list({ page, page_size: 10, source_type: kSourceType.value || undefined })
  kList.value = res.data?.records || []
  kTotal.value = res.data?.total || 0
}

async function onDeleteKnowledge(row) {
  await ElMessageBox.confirm(`删除知识「${row.title}」?`, '删除确认', { type: 'warning' })
  await knowledgeApi.remove(row.id)
  ElMessage.success('已删除')
  loadKnowledge()
}

// ================= 生命周期 =================
onMounted(() => {
  loadQueue()
  loadKnowledge(1)
  connectWs()
})

onUnmounted(() => {
  if (ws) ws.close()
})

function scrollToBottom() {
  nextTick(() => {
    if (msgBoxRef.value) msgBoxRef.value.scrollTop = msgBoxRef.value.scrollHeight
  })
}
</script>

<style scoped>
.view-tabs { margin-bottom: 4px; }
.panel { min-height: 300px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; }
.session-item {
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  margin-bottom: 6px;
}
.session-item:hover { background: var(--el-fill-color-light); }
.session-item.active { border-color: var(--el-color-primary); background: var(--el-color-primary-light-9); }
.session-head { display: flex; align-items: center; gap: 8px; }
.session-user { font-weight: 600; }
.session-time { margin-left: auto; font-size: 12px; color: var(--el-text-color-secondary); }
.session-summary {
  margin-top: 4px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chat-panel { display: flex; flex-direction: column; }
.chat-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 8px;
  font-weight: 600;
}
.msg-box {
  height: calc(100vh - 420px);
  min-height: 260px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-fill-color-lighter);
  margin-bottom: 8px;
}
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
  white-space: pre-wrap;
}
.bubble.user { background: #fff; border: 1px solid var(--el-border-color-lighter); }
.bubble.ai { background: #f4f4f5; }
.bubble.agent { background: var(--el-color-primary); color: #fff; }
html.dark .bubble.user { background: var(--el-bg-color-overlay); }
html.dark .bubble.ai { background: var(--el-fill-color); }
.sys-msg { text-align: center; font-size: 12px; color: var(--el-text-color-secondary); margin: 8px 0; }
.input-bar { display: flex; gap: 8px; align-items: flex-end; margin-bottom: 8px; }
.action-bar { display: flex; gap: 8px; }
.pagination { margin-top: 10px; justify-content: flex-end; }
.tab-badge { margin-left: 4px; }
</style>
