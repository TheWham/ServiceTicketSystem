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
            <div class="header-actions">
              <el-tag :type="sessionStatus.type" effect="light" round class="session-status-tag">{{ sessionStatus.label }}</el-tag>
              <el-button size="small" :icon="Plus" plain type="primary" :disabled="isAiHandling && aiThinking" @click="handleStartNewSession">
                开启新咨询
              </el-button>
              <el-button size="small" :icon="Clock" plain @click="openHistoryDrawer">
                历史会话<span v-if="recentSessions.length" class="history-count">({{ recentSessions.length }})</span>
              </el-button>
            </div>
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
                <!-- 思考过程卡片 (参考 Claude / Codex / DeepSeek R1 交互标准) -->
                <div v-if="msg.senderType === 'AI' && ((msg.thoughtStages && msg.thoughtStages.length) || msg.reasoningContent || msg.isThinking)" class="thought-container">
                  <div class="thought-header" role="button" tabindex="0" @click="toggleThought(msg)" @keydown.enter="toggleThought(msg)">
                    <span class="thought-status">
                      <el-icon v-if="msg.isThinking" class="is-loading"><Loading /></el-icon>
                      <el-icon v-else class="thought-done-icon"><Check /></el-icon>
                      <span class="thought-title">{{ msg.isThinking ? '思考中…' : `已深度思考 (${msg.thinkingDuration || 1}s)` }}</span>
                    </span>
                    <span class="thought-toggle">
                      <span>{{ msg.thoughtCollapsed ? '展开思考过程' : '收起' }}</span>
                      <el-icon :class="{ 'is-rotated': !msg.thoughtCollapsed }"><ArrowDown /></el-icon>
                    </span>
                  </div>

                  <div v-show="!msg.thoughtCollapsed" class="thought-content">
                    <!-- 编排时序节点 -->
                    <div v-if="msg.thoughtStages && msg.thoughtStages.length" class="thought-stages">
                      <div v-for="(st, idx) in msg.thoughtStages" :key="idx" class="thought-stage-item">
                        <span class="stage-dot"></span>
                        <span class="stage-text">{{ st }}</span>
                      </div>
                    </div>
                    <!-- 模型思维链流式内容 (Reasoning Content) -->
                    <div v-if="msg.reasoningContent" class="thought-reasoning">
                      <pre class="reasoning-text">{{ msg.reasoningContent }}</pre>
                    </div>
                  </div>
                </div>

                <div v-if="msg.content || msg.isStreaming" class="msg-text" :class="{ 'markdown-body': msg.senderType === 'AI' || msg.senderType === 'ENGINEER' }">
                  <div v-if="msg.senderType === 'AI' || msg.senderType === 'ENGINEER'" class="markdown-content" v-html="renderMarkdown(msg.content)"></div>
                  <template v-else>{{ msg.content }}</template>
                  <span v-if="msg.isStreaming" class="stream-cursor">▌</span>
                </div>
                <ChatMessageAttachments v-if="msg.attachments?.length" :session-id="session.sessionId" :attachments="msg.attachments" />

                <!-- 通用能力回答标识(冷启动放宽策略:无知识库依据) -->
                <div v-if="msg.generalAnswer" class="general-answer-note">
                  <el-icon><MagicStick /></el-icon>
                  这条回答基于 AI 通用知识，暂无知识库依据。
                </div>

                <!-- Model Router 动态选模与成本治理调用链路胶囊 (DeepSeek Harness) -->
                <div v-if="hasGovTrace(msg)" class="governance-trace-badge-bar">
                  <div class="governance-pill" role="button" tabindex="0"
                       :title="'点击展开 ' + (getGovTrace(msg).chosenModel || '大模型') + ' 动态选模决策与调用链路'"
                       @click="showGovTrace(msg)" @keydown.enter="showGovTrace(msg)">
                    <span class="gov-pill-icon"><el-icon><Cpu /></el-icon></span>
                    <span class="gov-pill-tier" :class="'tier-' + getGovTrace(msg).chosenTier.toLowerCase()">{{ getGovTrace(msg).chosenTier }}</span>
                    <span class="gov-pill-model">{{ getGovTrace(msg).chosenModel }}</span>
                    <span class="gov-pill-tokens">{{ getGovTrace(msg).totalTokens }}T</span>
                    <span class="gov-pill-cost">{{ formatCostRmb(getGovTrace(msg).actualCostRmb) }}</span>
                    <span v-if="getGovTrace(msg).savingsRatePercent > 0" class="gov-pill-savings">
                      省{{ getGovTrace(msg).savingsRatePercent.toFixed(0) }}%
                    </span>
                    <span class="gov-pill-link">调用链路 <el-icon><ArrowRight /></el-icon></span>
                  </div>
                </div>

                <!-- 知识图谱思维链路高光角标（当命中 GraphRAG 多跳因果推导时激活） -->
                <div v-if="hasGraph(msg)" class="graph-reasoning-badge-bar">
                  <div class="graph-reasoning-pill" role="button" tabindex="0"
                       title="点击展开 Neo4j 拓扑演绎链路与根因分析"
                       @click="showGraphReasoning(msg)" @keydown.enter="showGraphReasoning(msg)">
                    <span class="graph-pill-icon"><el-icon><Connection /></el-icon></span>
                    <span class="graph-pill-title">知识图谱因果推导</span>
                    <span class="graph-pill-link">查看思维链路 <el-icon><ArrowRight /></el-icon></span>
                  </div>
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

                <!-- AI 建单草稿（人机回环）：AI 只起草、不落库，员工确认后才真正建单 -->
                <div v-if="msg.ticketDraft" class="ticket-draft-card">
                  <div class="ticket-draft-head">
                    <el-icon><Tickets /></el-icon>
                    <span>AI 拟好的工单草稿 <em>（确认前不会创建工单）</em></span>
                  </div>
                  <div class="ticket-draft-body">
                    <div class="ticket-draft-row"><span class="k">标题</span><span class="v">{{ msg.ticketDraft.title }}</span></div>
                    <div class="ticket-draft-row"><span class="k">分类</span><span class="v">{{ msg.ticketDraft.category || '—' }}</span></div>
                    <div class="ticket-draft-row"><span class="k">优先级</span><span class="v">{{ msg.ticketDraft.priority || 'MEDIUM' }}</span></div>
                    <div class="ticket-draft-row"><span class="k">描述</span><span class="v">{{ msg.ticketDraft.description }}</span></div>
                  </div>
                  <div class="ticket-draft-actions">
                    <template v-if="draftTicketIdOf(msg)">
                      <el-tag type="success" size="small">已创建工单 {{ draftTicketIdOf(msg) }}</el-tag>
                    </template>
                    <template v-else>
                      <el-button type="primary" size="small" :icon="Tickets"
                                 :loading="msg.draftSubmitting" @click="submitTicketDraft(msg)">
                        确认建单
                      </el-button>
                      <!-- 不满意 AI 拟的字段就先去提单表单改：那里有完整校验与草稿保存，
                           聊天里内联编辑等于把整套表单逻辑再复制一份 -->
                      <el-button size="small" :icon="Edit"
                                 :disabled="msg.draftSubmitting" @click="editTicketDraft(msg)">
                        编辑
                      </el-button>
                    </template>
                  </div>
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
          <label for="support-message" class="sr-only">描述你的问题</label>
          <el-input id="support-message" ref="inputRef" v-model="draft" type="textarea"
                    :autosize="{ minRows: 1, maxRows: 3 }" resize="none"
                    :maxlength="inputMaxLength" show-word-limit
                    :placeholder="inputPlaceholder" :disabled="sending || aiThinking || inputDisabled || closing || cancelingQueue"
                    @keydown.enter.exact="send" />
          <ChatAttachmentUploader v-if="canAttach" :key="session.sessionId" ref="attachmentUploaderRef"
                                  v-model="attachmentDrafts" :session-id="session.sessionId" :disabled="attachmentDisabled" />
          <div class="chat-actions">
            <div class="chat-actions-left">
              <!-- PRD 8.1:AI 对话中必须始终提供转人工和提交工单入口 -->
              <el-button v-if="canTransfer" size="small" :icon="Service" :disabled="closing || cancelingQueue" @click="openTransfer()">转人工</el-button>
              <el-button size="small" :icon="Tickets" @click="goCreateTicket">提交工单</el-button>
              <span class="input-inline-tip">Enter 发送 · Shift+Enter 换行 · {{ isAiHandling ? 'AI 建议仅供参考' : '支持拖拽附件' }}</span>
            </div>
            <div class="chat-actions-right">
              <el-button text type="danger" size="small" :icon="Close" :loading="closing"
                         :disabled="cancelingQueue || transferring" @click="closeSession">
                结束对话
              </el-button>
              <el-button type="primary" size="small" :icon="Promotion" :loading="sending || aiThinking"
                         :disabled="(!draft.trim() && !attachmentDrafts.length) || attachmentBlocked || inputDisabled || closing || cancelingQueue" @click="send">
                发送
              </el-button>
            </div>
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

    <!-- 知识图谱思维链路详情抽屉 -->
    <GraphReasoningDrawer
      v-model="graphDrawerVisible"
      :reasoning="activeGraphReasoning"
    />

    <!-- Model Router 成本治理与决策链路详情抽屉 -->
    <TraceGovernanceDrawer
      v-model="govDrawerVisible"
      :trace="activeGovTrace"
    />

    <!-- 最近1个月历史会话抽屉 -->
    <el-drawer
      v-model="historyDrawerVisible"
      title="最近咨询会话 (近1个月)"
      size="min(440px, 92vw)"
      direction="rtl"
      class="consultation-history-drawer"
      :append-to-body="true"
    >
      <div class="history-drawer-content">
        <div class="history-filter-tip">
          <el-icon><Clock /></el-icon>
          <span>仅展示最近 30 天内的咨询记录，点击卡片可快速切换查看完整历史。</span>
        </div>

        <div v-loading="loadingHistory" class="history-list">
          <el-empty
            v-if="!loadingHistory && recentSessions.length === 0"
            description="最近一个月暂无咨询记录"
            :image-size="64"
          />

          <div
            v-for="s in recentSessions"
            :key="s.session_id"
            class="history-card"
            :class="{ active: s.session_id === session?.sessionId }"
            role="button"
            tabindex="0"
            @click="switchSession(s)"
            @keydown.enter="switchSession(s)"
          >
            <div class="history-card-header">
              <span class="history-session-id">会话 {{ s.session_id }}</span>
              <el-tag
                :type="CONSULTATION_STATUS[s.status]?.type || 'info'"
                size="small"
                effect="light"
                round
              >
                {{ CONSULTATION_STATUS[s.status]?.label || s.status }}
              </el-tag>
            </div>

            <div class="history-preview">
              {{ historyPreviews[s.session_id] || '点击加载对话详情…' }}
            </div>

            <div class="history-card-footer">
              <span class="history-time">{{ formatHistoryTime(s.created_at) }}</span>
              <span v-if="s.session_id === session?.sessionId" class="history-current-badge">
                当前进行中
              </span>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
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
  Monitor, Connection, Message, Printer, ArrowRight, Edit, Loading, Check, ArrowDown, Plus, Clock
} from '@element-plus/icons-vue'
import {
  consultationApi, REFUSAL_REASON, TERMINAL_STATUS, TICKET_ENTRY_MESSAGE, CONSULTATION_STATUS
} from '../api/consultation.js'
import { saveAiTicketDraft } from '../utils/aiTicketDraft.js'
import { renderMarkdown } from '../utils/markdown.js'
import GraphReasoningDrawer from './GraphReasoningDrawer.vue'
import TraceGovernanceDrawer from './TraceGovernanceDrawer.vue'
import { hasGovernanceTrace, parseGovernanceTrace, formatCostRmb } from '../utils/governanceTrace.js'
import { Cpu } from '@element-plus/icons-vue'
import { hasGraphReasoning, parseGraphReasoning } from '../utils/graphReasoning.js'

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
const graphDrawerVisible = ref(false)
const activeGraphReasoning = ref(null)
const govDrawerVisible = ref(false)
const activeGovTrace = ref(null)

function hasGovTrace(msg) {
  return hasGovernanceTrace(msg)
}

function getGovTrace(msg) {
  return parseGovernanceTrace(msg)
}

function showGovTrace(msg) {
  const trace = parseGovernanceTrace(msg)
  if (trace) {
    activeGovTrace.value = trace
    govDrawerVisible.value = true
  }
}

function toggleThought(msg) {
  msg.thoughtCollapsed = !msg.thoughtCollapsed
}

function hasGraph(msg) {
  return hasGraphReasoning(msg)
}

function showGraphReasoning(msg) {
  const parsed = parseGraphReasoning(msg)
  if (parsed) {
    activeGraphReasoning.value = parsed
    graphDrawerVisible.value = true
  }
}
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

// ===== 最近1个月历史会话抽屉 =====
const historyDrawerVisible = ref(false)
const recentSessions = ref([])
const loadingHistory = ref(false)
const historyPreviews = ref({})

async function openHistoryDrawer() {
  historyDrawerVisible.value = true
  await loadRecentSessions()
}

async function loadRecentSessions() {
  loadingHistory.value = true
  try {
    const page = await consultationApi.list(1, 50)
    recentSessions.value = page?.items || []
    recentSessions.value.slice(0, 15).forEach(s => {
      if (!historyPreviews.value[s.session_id]) {
        loadHistoryPreview(s.session_id)
      }
    })
  } catch (e) {
    ElMessage.error(e.message || '加载历史会话失败')
  } finally {
    loadingHistory.value = false
  }
}

async function loadHistoryPreview(sessionId) {
  try {
    const page = await consultationApi.listMessages(sessionId)
    const items = (page?.items || []).filter(m => m.sender_type !== 'SYSTEM')
    if (items.length > 0) {
      const firstUser = items.find(m => m.sender_type === 'EMPLOYEE') || items[0]
      let text = firstUser.content || ''
      if (!text && firstUser.attachments?.length) {
        text = '[附件] ' + firstUser.attachments[0].file_name
      }
      historyPreviews.value[sessionId] = text.slice(0, 60) + (text.length > 60 ? '…' : '')
    } else {
      historyPreviews.value[sessionId] = '暂无对话消息'
    }
  } catch {
    historyPreviews.value[sessionId] = '暂无对话消息'
  }
}

async function switchSession(s) {
  if (s.session_id === session.value?.sessionId) {
    historyDrawerVisible.value = false
    return
  }
  historyDrawerVisible.value = false
  await resumeSession(s)
  ElMessage.success(`已切换至会话 ${s.session_id}`)
}

async function handleStartNewSession() {
  if (isAiHandling.value && aiThinking.value) {
    ElMessage.warning('AI 正在回答中，请稍候…')
    return
  }
  await startAi()
  ElMessage.success('已开启新咨询会话')
  loadRecentSessions()
}

function formatHistoryTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    if (isNaN(d.getTime())) return isoStr
    const now = new Date()
    const diffMs = now - d
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return '刚刚'
    if (diffMin < 60) return `${diffMin} 分钟前`
    const diffHours = Math.floor(diffMin / 60)
    const pad = n => String(n).padStart(2, '0')
    if (diffHours < 24 && d.getDate() === now.getDate()) {
      return `今天 ${pad(d.getHours())}:${pad(d.getMinutes())}`
    }
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return isoStr
  }
}

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
  const govTrace = item.governance_trace || item.governanceTrace || null
  const stages = []
  if (govTrace && Array.isArray(govTrace.stages)) {
    govTrace.stages.forEach(s => {
      const name = s.name || s.stageId || ''
      const summary = s.summary || s.status || ''
      stages.push(name ? `${name}：${summary}` : summary)
    })
  }

  const persistedStages = item.thought_stages || item.thoughtStages || item.metadata?.thought_stages
  const persistedDuration = item.thinking_duration || item.thinkingDuration || 1

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
    // AI 建单草稿随消息落库，所以**刷新后草稿卡还在**（服务端元数据里的 ticketDraft）
    ticketDraft: item.ticket_draft || null,
    governanceTrace: govTrace,
    thoughtStages: (persistedStages && persistedStages.length) ? persistedStages : stages,
    reasoningContent: item.reasoning_content || item.reasoningContent || item.metadata?.reasoning_content || '',
    thinkingDuration: persistedDuration,
    thoughtCollapsed: true,
    isThinking: false,
    isStreaming: false,
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
  const msg = {
    id: `local-${++localSeq}`,
    senderType,
    content,
    ...(senderType === 'AI' ? { feedback: null } : {}),
    sentAt: new Date().toISOString(),
    ...extra
  }
  messages.value.push(msg)
  scrollToBottom(senderType === 'EMPLOYEE')
  return messages.value[messages.value.length - 1]
}

const GREETING_TEXT = '你好，我是 IT 智能助手小 T 👋 我可以帮你解决 VPN 连不上、邮箱收不到邮件、打印机故障、账号权限等常见 IT 问题。请描述你遇到的情况，我会先尝试帮你解决；如果解决不了，可以随时转接人工客服。'

/**
 * 确认 AI 拟好的建单草稿 —— 人机回环第二步。
 * 草稿此前只存在于回答里，服务端没有写任何工单；这一步才真正创建，归属由服务端绑定当前员工。
 */
async function submitTicketDraft(msg) {
  if (msg.draftSubmitting || msg.draftTicketId) return
  const sid = session.value?.sessionId
  if (!sid) return
  msg.draftSubmitting = true
  try {
    const res = await consultationApi.confirmTicketDraft(sid, msg.ticketDraft)
    msg.draftTicketId = res.ticketId
    pushLocal('SYSTEM', `已为你创建工单 ${res.ticketId}，可在「我的工单」中跟进；工程师接单后会有通知。`)
  } catch (e) {
    ElMessage.error(e.message || '建单失败，请重试')
  } finally {
    msg.draftSubmitting = false
  }
}

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
    aiThinking.value = false
    let thinkingTimer = null
    const startTime = Date.now()

    let aiMsg = pushLocal('AI', '', {
      isStreaming: true,
      isThinking: true,
      thoughtStages: ['正在规划排障链路与模型资源…'],
      reasoningContent: '',
      thoughtCollapsed: false,
      thinkingDuration: 1,
      citations: [],
      governanceTrace: null
    })

    thinkingTimer = setInterval(() => {
      if (aiMsg && aiMsg.isThinking) {
        aiMsg.thinkingDuration = Math.max(1, Math.floor((Date.now() - startTime) / 1000))
      }
    }, 500)
    try {
      await consultationApi.aiMessageStream(sessionId, text, {
        onStage: (stageData) => {
          if (!stillActive() || !isAiHandling.value || !aiMsg) return
          let desc = ''
          if (stageData.stage === 'ROUTED') {
            desc = `模型路由：已匹配 ${stageData.tier || '标准'} 档位 (${stageData.model || ''})`
          } else if (stageData.message) {
            desc = stageData.message
          } else if (stageData.reason) {
            desc = stageData.reason
          }
          if (desc && !aiMsg.thoughtStages.includes(desc)) {
            aiMsg.thoughtStages.push(desc)
            scrollToBottom()
          }
        },
        onReasoning: (reasoningChunk) => {
          if (!stillActive() || !isAiHandling.value || !aiMsg) return
          aiMsg.reasoningContent += reasoningChunk
          scrollToBottom()
        },
        onDelta: (delta) => {
          if (!stillActive() || !isAiHandling.value || !aiMsg) return
          if (aiMsg.isThinking) {
            aiMsg.isThinking = false
            aiMsg.thoughtCollapsed = true
            if (thinkingTimer) {
              clearInterval(thinkingTimer)
              thinkingTimer = null
            }
          }
          aiMsg.content += delta
          scrollToBottom()
        },
        onCitation: (citations) => {
          if (aiMsg) {
            aiMsg.citations = citations || []
          }
        },
        onCompleted: (res) => {
          if (thinkingTimer) {
            clearInterval(thinkingTimer)
            thinkingTimer = null
          }
          if (!stillActive() || !isAiHandling.value || !aiMsg) return
          aiMsg.isThinking = false
          aiMsg.isStreaming = false
          const hasCitations = (res.citations || []).length > 0
          if (res.replyType === 'REFUSE') {
            aiMsg.content = ''
            aiMsg.refusalReason = res.refusalReason
            aiMsg.governanceTrace = res.governanceTrace || null
          } else {
            aiMsg.content = res.answer || res.answerText || aiMsg.content
            aiMsg.citations = res.citations || []
            aiMsg.interactionId = res.interactionId
            aiMsg.suggestTransfer = res.suggestTransfer
            aiMsg.replyType = res.replyType
            aiMsg.generalAnswer = res.replyType === 'ANSWER' && !hasCitations
            aiMsg.ticketDraft = res.ticketDraft || null
            aiMsg.governanceTrace = res.governanceTrace || null
          }
          if (res.replyType === 'ANSWER' && !hasCitations) {
            pushLocal('SYSTEM', '这条回答暂无知识库依据，仅供排查参考。你可以继续补充问题、反馈是否解决，或转人工处理。')
          } else if (res.suggestTransfer) {
            pushLocal('SYSTEM', '这个回答的把握不高，如果没解决问题建议转人工。')
          }
          scrollToBottom()
        },
        onError: (e) => {
          if (thinkingTimer) {
            clearInterval(thinkingTimer)
            thinkingTimer = null
          }
          if (!stillActive()) return
          if (aiMsg) {
            aiMsg.isThinking = false
            aiMsg.isStreaming = false
          }
          draft.value = text
          pushLocal('SYSTEM', `AI 暂时不可用（${e.message}）。你可以转人工或直接提交工单。`)
        }
      })
    } catch (e) {
      if (thinkingTimer) {
        clearInterval(thinkingTimer)
        thinkingTimer = null
      }
      if (!stillActive()) return
      draft.value = text
      pushLocal('SYSTEM', `AI 暂时不可用（${e.message}）。你可以转人工或直接提交工单。`)
    } finally {
      if (thinkingTimer) {
        clearInterval(thinkingTimer)
        thinkingTimer = null
      }
      if (aiMsg) {
        aiMsg.isThinking = false
        aiMsg.isStreaming = false
      }
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
  pushToCreateForm({})
}

/**
 * 「编辑」AI 拟好的建单草稿 —— 人机回环的第三条路：不在聊天里落库，而是带着**这份草稿**
 * 跳到提单表单，预填好、员工改完再手动提交（提交时经 source_session_id 回写会话归属）。
 *
 * **必须把卡片上这份草稿本身带过去**，不能让提单页自己从会话推导：那边的
 * `GET /consultations/{id}/ticket-draft` 是「按整条会话时间线起草」（标题取员工说过的第一句、
 * 描述取整段对话摘要），与 agent 按当前这句话拟的草稿不是一回事 —— 复用会让员工点完
 * 「编辑」看到一串与卡片无关的旧对话内容（实测踩到过）。详见 utils/aiTicketDraft.js。
 *
 * 多带 autofill=1，让提单页到达时直接填入；其余「提交工单」入口不带这个标志，
 * 仍靠那里的「填入并关联咨询」按钮显式触发 —— 那条路径下表单里可能已有员工正在写的内容。
 */
function editTicketDraft(msg) {
  saveAiTicketDraft(session.value?.sessionId, msg?.ticketDraft)
  pushToCreateForm({ autofill: '1' })
}

/**
 * 这张草稿卡对应的工单号，用来决定显示「已创建工单」还是两个按钮。
 *
 * 先看消息本地态（本次会话里刚点的确认），刷新之后本地态没了，就取会话上的
 * `converted_ticket_id` —— 否则刷新后卡片会退回「确认建单」，员工以为没建成会再点一次。
 * （服务端 confirmTicketDraft 有幂等守卫兜底，但界面上不该制造这种困惑。）
 */
function draftTicketIdOf(msg) {
  return msg?.draftTicketId || session.value?.converted_ticket_id || ''
}

/** 跳到提单页并带上会话让提单页拉取咨询预填(PRD 9.1)。 */
function pushToCreateForm(extraQuery) {
  emit('navigate')
  if (session.value?.sessionId && !isTerminal.value) {
    router.push({
      path: '/employee',
      query: { from: 'consultation', session: session.value.sessionId, ...extraQuery }
    })
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

onMounted(async () => {
  await autoStart()
  loadRecentSessions()
})
onUnmounted(stopPolling)
</script>

<style scoped>
.chat-input { position: relative; }
.attachment-dragging { outline: 2px dashed var(--el-color-primary); outline-offset: -4px; }
.attachment-drop-hint { position: absolute; inset: 8px; z-index: 5; display: grid; place-items: center; border: 2px dashed var(--el-color-primary); border-radius: 10px; background: var(--el-color-primary-light-9); color: var(--el-text-color-primary); pointer-events: none; font-weight: 600; }
.consultation-chat { width: 100%; height: 100%; flex: 1; display: flex; flex-direction: column; min-height: 0; }
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

.msg-main { display: flex; flex-direction: column; max-width: 88%; }
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

/* 知识图谱思维链路角标 */
.graph-reasoning-badge-bar {
  margin-top: 10px;
  margin-bottom: 4px;
}
.graph-reasoning-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(168, 85, 247, 0.15) 100%);
  border: 1px solid rgba(99, 102, 241, 0.35);
  padding: 6px 12px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.12);
}
.graph-reasoning-pill:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(168, 85, 247, 0.25) 100%);
  border-color: rgba(99, 102, 241, 0.6);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.22);
}
.graph-pill-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #6366f1;
  color: #fff;
  font-size: 12px;
}
.graph-pill-title {
  font-size: 12px;
  font-weight: 700;
  color: #4f46e5;
  letter-spacing: 0.3px;
}
.graph-pill-link {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 600;
  color: #7c3aed;
  margin-left: 4px;
}

/* 引用 */
.citations { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--el-border-color); }
/* AI 建单草稿：视觉上刻意做成「待确认的草稿」而非已成立的工单 */
.ticket-draft-card {
  margin-top: 10px; padding: 10px 12px; border-radius: 8px;
  border: 1px dashed var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}
.ticket-draft-head {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 600; color: var(--el-color-primary);
  margin-bottom: 8px;
}
.ticket-draft-head em { font-style: normal; font-weight: 400; color: var(--el-text-color-secondary); font-size: 12px; }
.ticket-draft-body { display: flex; flex-direction: column; gap: 4px; }
.ticket-draft-row { display: flex; gap: 8px; font-size: 13px; line-height: 1.6; }
.ticket-draft-row .k { flex: 0 0 48px; color: var(--el-text-color-secondary); }
.ticket-draft-row .v { flex: 1; word-break: break-word; }
.ticket-draft-actions { margin-top: 10px; display: flex; align-items: center; gap: 10px; }
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

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* 独立客服页面：对话流滚动，操作区保持可见。 */
.chat-panel { border-radius: 14px; display: flex; flex-direction: column; flex: 1; min-height: 0; height: 100%; }
.chat-panel :deep(.el-card__header) { padding: 10px 20px; flex-shrink: 0; }
.chat-panel :deep(.el-card__body) { display: flex; flex-direction: column; padding: 0; flex: 1; min-height: 0; height: 100%; }
.new-message-cue { align-self: center; flex-shrink: 0; padding: 6px 14px; margin: 4px 0 8px; border: 1px solid var(--el-color-primary-light-7); border-radius: 20px; color: var(--el-color-primary); background: var(--el-color-primary-light-9); font: inherit; font-size: 12px; cursor: pointer; }
.conversation-header, .conversation-identity { display: flex; align-items: center; gap: 10px; }
.conversation-header { justify-content: space-between; }
.small-assistant { display: grid; place-items: center; width: 34px; height: 34px; background: var(--el-color-primary-light-9); color: var(--el-color-primary); border-radius: 10px; font-size: 19px; }
.conversation-identity strong { font-size: 14px; font-weight: 600; display: inline-block; }
.conversation-identity span { margin-left: 8px; font-size: 12px; color: var(--el-text-color-secondary); display: inline-block; }
.state-banner { flex-shrink: 0; margin: 8px 16px 0; width: auto; }
.chat-body { flex: 1; min-height: 0; height: auto; border-radius: 0; padding: 14px 20px; background: var(--el-bg-color); overscroll-behavior: contain; }
.chat-welcome { max-width: 860px; margin: 0 auto; padding: 10px 14px; text-align: center; }
.welcome-mark { width: 38px; height: 38px; display: grid; place-items: center; margin: 0 auto 8px; border-radius: 12px; color: var(--el-color-primary); background: var(--el-color-primary-light-9); font-size: 20px; }
.chat-welcome h2 { margin: 0 0 8px; font-size: 20px; font-weight: 600; color: var(--el-text-color-primary); }
.chat-welcome p { margin: 0; color: var(--el-text-color-regular); font-size: 13px; line-height: 1.6; }
.suggestion-label { margin: 12px 0 8px; font-size: 12px; text-align: left; color: var(--el-text-color-regular); }
.suggestion-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
@media (min-width: 1200px) {
  .suggestion-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
.suggestion-card { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border: 1px solid var(--el-border-color-lighter); border-radius: 10px; background: var(--el-fill-color-extra-light); color: var(--el-text-color-primary); text-align: left; cursor: pointer; font-family: inherit; transition: border-color .2s, background .2s; }
.suggestion-card:hover { border-color: var(--el-color-primary); background: var(--el-color-primary-light-9); }
.suggestion-card:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 3px; }
.suggestion-card > .el-icon { color: var(--el-color-primary); font-size: 18px; flex-shrink: 0; }
.suggestion-card span { flex: 1; min-width: 0; }
.suggestion-card strong { display: block; font-size: 13px; font-weight: 500; }
.suggestion-card small { display: block; margin-top: 4px; font-size: 11px; line-height: 1.4; color: var(--el-text-color-regular); }
.suggestion-card > .suggestion-arrow { color: var(--el-text-color-secondary); font-size: 12px; }
.avatar-ai { background: var(--el-color-primary); border-radius: 10px; }
.avatar-employee { background: var(--el-color-primary-light-9); color: var(--el-color-primary); border-radius: 10px; }
.msg-main { max-width: 88%; min-width: 0; }
.msg-bubble { padding: 10px 16px; font-size: 15px; line-height: 1.68; border-radius: 12px; }
.bubble-ai { background: var(--el-fill-color-light); border-color: transparent; }
.msg-time { font-size: 11px; color: var(--el-text-color-placeholder); }
.chat-input { flex-shrink: 0; margin: 0; padding: 6px 16px 8px; border-top: 1px solid var(--el-border-color-lighter); background: var(--el-bg-color); }
.chat-input :deep(.el-textarea__inner) {
  border-radius: 8px;
  padding: 7px 12px 18px;
  font-family: inherit;
  font-size: 14px;
  min-height: 38px;
  line-height: 1.5;
}
.chat-input :deep(.el-input__count) {
  bottom: 2px;
  right: 10px;
  font-size: 11px;
  background: transparent;
  color: var(--el-text-color-placeholder);
}
.chat-actions {
  margin-top: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.chat-actions-left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}
.chat-actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.input-inline-tip {
  margin-left: 6px;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.new-topic { flex-shrink: 0; border-top: 1px solid var(--el-border-color-lighter); padding: 12px; margin: 0; }
.startup-error, .booting { flex: 1; min-height: 360px; height: 100%; border: 1px solid var(--el-border-color-lighter); border-radius: 14px; background: var(--el-bg-color); }
.startup-error { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; text-align: center; box-sizing: border-box; }
.error-icon { color: var(--el-color-warning); font-size: 38px; }
.startup-error h2 { font-size: 20px; margin: 20px 0 10px; }
.startup-error p { font-size: 14px; line-height: 1.7; color: var(--el-text-color-regular); margin-bottom: 24px; overflow-wrap: anywhere; }
@media (max-width: 760px) {
  .chat-panel :deep(.el-card__header) { padding: 10px 12px; }
  .chat-panel :deep(.el-card__body) { height: 100%; flex: 1; min-height: 0; }
  .conversation-header { gap: 8px; }
  .conversation-identity { gap: 8px; }
  .conversation-identity span { display: none; }
  .conversation-identity strong { font-size: 13px; }
  .small-assistant { width: 30px; height: 30px; }
  .conversation-header > .el-tag { font-size: 11px; }
  .chat-body { padding: 12px 10px; }
  .chat-welcome { padding: 4px; }
  .chat-welcome h2 { font-size: 18px; margin-bottom: 8px; }
  .chat-welcome p { font-size: 12px; line-height: 1.6; }
  .welcome-mark { display: none; }
  .suggestion-label { margin: 12px 0 8px; }
  .suggestion-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .suggestion-card { padding: 10px 8px; gap: 7px; min-height: 48px; }
  .suggestion-card strong { font-size: 12px; }
  .suggestion-card small, .suggestion-card .suggestion-arrow { display: none; }
  .msg-row { padding: 0; gap: 6px; }
  .msg-avatar { width: 28px; height: 28px; font-size: 11px; }
  .msg-main { max-width: calc(100% - 34px); }
  .chat-input { padding: 6px 10px 8px; }
  .chat-actions { flex-wrap: wrap; gap: 6px; }
  .chat-actions-left { flex-wrap: wrap; gap: 4px; }
  .chat-actions-right { flex-wrap: wrap; gap: 6px; }
  .chat-actions .el-button { padding: 6px 8px; min-height: 28px; font-size: 12px; }
  .input-inline-tip { display: none; }
  .refusal-actions { flex-wrap: wrap; }
  .citation-tag { max-width: 100%; height: auto; min-height: 28px; white-space: normal; }
}
@media (prefers-reduced-motion: reduce) {
  .dot { animation: none; opacity: .7; }
  .suggestion-card { transition: none; }
}

/* 思考过程卡片 (参考 Claude / Codex / DeepSeek R1 交互标准) */
.thought-container {
  margin-bottom: 12px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  font-size: 13px;
  transition: all 0.2s ease;
}

.thought-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f1f5f9;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  color: #475569;
  transition: background 0.15s ease;
}
.thought-header:hover {
  background: #e2e8f0;
}

.thought-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.thought-status .is-loading {
  color: var(--el-color-primary);
  animation: rotating 1.5s linear infinite;
}

.thought-status .thought-done-icon {
  color: #10b981;
}

.thought-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #64748b;
  font-size: 11px;
}

.thought-toggle .el-icon {
  transition: transform 0.2s ease;
}
.thought-toggle .el-icon.is-rotated {
  transform: rotate(180deg);
}

.thought-content {
  padding: 10px 12px;
  border-top: 1px solid #e2e8f0;
}

.thought-stages {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 8px;
}

.thought-stage-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #334155;
}

.thought-stage-item .stage-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3b82f6;
  flex-shrink: 0;
}

.thought-reasoning {
  max-height: 180px;
  overflow-y: auto;
  background: #0f172a;
  color: #94a3b8;
  padding: 8px 10px;
  border-radius: 6px;
  margin-top: 6px;
}

.reasoning-text {
  margin: 0;
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Markdown 排版样式 (适配 v-html 深度作用域，间隙紧凑优雅) */
.markdown-body {
  font-size: 13.5px;
  line-height: 1.55;
  color: inherit;
  word-break: break-word;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin-top: 10px;
  margin-bottom: 4px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--el-text-color-primary);
}
.markdown-body :deep(h1:first-child),
.markdown-body :deep(h2:first-child),
.markdown-body :deep(h3:first-child),
.markdown-body :deep(h4:first-child) {
  margin-top: 0;
}
.markdown-body :deep(h1) { font-size: 16px; border-bottom: 1px solid var(--el-border-color-lighter); padding-bottom: 2px; }
.markdown-body :deep(h2) { font-size: 15px; border-bottom: 1px solid var(--el-border-color-lighter); padding-bottom: 2px; }
.markdown-body :deep(h3) { font-size: 14px; }
.markdown-body :deep(h4) { font-size: 13.5px; }

.markdown-body :deep(p) {
  margin-top: 0;
  margin-bottom: 5px;
  line-height: 1.55;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 18px;
  margin-top: 2px;
  margin-bottom: 5px;
}
.markdown-body :deep(li) {
  margin-bottom: 2px;
  line-height: 1.55;
}
.markdown-body :deep(code) {
  font-family: monospace;
  font-size: 12px;
  padding: 1px 4px;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  color: var(--el-color-danger);
}
.markdown-body :deep(pre) {
  padding: 8px 10px;
  border-radius: 6px;
  background: #1e293b;
  color: #e2e8f0;
  overflow-x: auto;
  font-size: 12px;
  line-height: 1.45;
  margin: 6px 0;
}
.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}
.markdown-body :deep(blockquote) {
  margin: 4px 0;
  padding: 4px 10px;
  border-left: 3px solid var(--el-color-primary);
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
}
.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--el-border-color-lighter);
  margin: 6px 0;
}
.stream-cursor {
  display: inline-block;
  color: var(--el-color-primary);
  font-weight: bold;
  animation: cursor-blink 1s step-start infinite;
  margin-left: 2px;
}
@keyframes cursor-blink {
  50% { opacity: 0; }
}

/* Model Router 治理调用链路胶囊 */
.governance-trace-badge-bar {
  margin-top: 8px;
  margin-bottom: 4px;
}
.governance-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, rgba(8, 117, 140, 0.08) 0%, rgba(36, 93, 206, 0.12) 100%);
  border: 1px solid rgba(8, 117, 140, 0.35);
  padding: 4px 10px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(8, 117, 140, 0.08);
}
.governance-pill:hover {
  background: linear-gradient(135deg, rgba(8, 117, 140, 0.16) 0%, rgba(36, 93, 206, 0.22) 100%);
  border-color: rgba(8, 117, 140, 0.6);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(8, 117, 140, 0.18);
}
.gov-pill-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #08758C;
  color: #fff;
  font-size: 11px;
}
.gov-pill-tier {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}
.gov-pill-tier.tier-lite {
  background: #E6F4EA;
  color: #137333;
  border: 1px solid rgba(19, 115, 51, 0.25);
}
.gov-pill-tier.tier-standard {
  background: #FEF7E0;
  color: #B06000;
  border: 1px solid rgba(176, 96, 0, 0.25);
}
.gov-pill-tier.tier-premium {
  background: #FCE8E6;
  color: #C5221F;
  border: 1px solid rgba(197, 34, 31, 0.25);
}
.gov-pill-model {
  font-size: 11px;
  font-weight: 600;
  color: #1E293B;
  font-family: monospace;
}
.gov-pill-tokens, .gov-pill-cost {
  font-size: 11px;
  color: #64748B;
  font-family: monospace;
}
.gov-pill-savings {
  font-size: 10px;
  font-weight: 700;
  color: #059669;
  background: #ECFDF5;
  border: 1px solid rgba(5, 150, 105, 0.25);
  padding: 1px 5px;
  border-radius: 4px;
}
.gov-pill-link {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 600;
  color: #08758C;
  margin-left: 2px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.history-count {
  font-size: 11px;
  margin-left: 2px;
  opacity: 0.8;
}
.consultation-history-drawer :deep(.el-drawer__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color-page);
}
.history-drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.history-filter-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 12px;
  border-bottom: 1px solid var(--el-color-primary-light-8);
}
.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.history-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all .2s ease;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.history-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}
.history-card.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.history-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.history-session-id {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.history-preview {
  font-size: 12px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.history-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--el-text-color-secondary);
}
.history-current-badge {
  color: var(--el-color-primary);
  font-weight: 500;
}
</style>
