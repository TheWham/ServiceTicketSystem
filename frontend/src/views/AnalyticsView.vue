<template>
  <div class="analytics-page">
    <div class="page-head">
      <div>
        <span class="page-eyebrow">CROSS-TICKET ANALYTICS</span>
        <h1 class="page-title">跨工单分析</h1>
        <p class="page-sub">
          对一批工单做宏观归纳：现象分布、共性根因、备件与巡检建议。
          数字全部由系统统计得出，可逐条下钻到源工单。
        </p>
      </div>
      <div class="heading-actions">
        <el-tag type="info" effect="plain" size="small">仅工程师</el-tag>
      </div>
    </div>

    <el-card shadow="never" class="ask-card">
      <el-form @submit.prevent="run">
        <el-form-item label="分析问题" class="ask-item">
          <el-input
            v-model="question"
            type="textarea"
            :rows="2"
            maxlength="2000"
            show-word-limit
            placeholder="例如：请根据全部网络与打印设备工单，总结本季度共性根因并给出备件采购建议"
            @keydown.ctrl.enter="run"
          />
        </el-form-item>
        <div class="ask-actions">
          <div class="samples">
            <span class="samples-label">示例：</span>
            <el-button
              v-for="s in samples"
              :key="s"
              link
              type="primary"
              size="small"
              @click="question = s"
            >{{ s }}</el-button>
          </div>
          <el-button type="primary" :loading="loading" :disabled="!question.trim()" @click="run">
            开始分析
          </el-button>
        </div>
      </el-form>
    </el-card>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="page-error"
    />

    <template v-if="result">
      <!-- 结论 -->
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span class="section-title">分析结论</span>
            <div class="header-tags">
              <el-tag v-if="result.replyType" size="small" :type="replyTagType(result.replyType, result.refusalReason)">
                {{ replyLabel(result.replyType, result.refusalReason) }}
              </el-tag>
              <el-tag v-if="result.refusalReason" size="small" effect="plain" type="info">
                {{ refusalLabel(result.refusalReason) }}
              </el-tag>
              <el-tag v-if="result.confidence != null" size="small" effect="plain">
                置信度 {{ Number(result.confidence).toFixed(2) }}
              </el-tag>
            </div>
          </div>
        </template>

        <el-alert
          v-if="result.degradedReason"
          :title="degradedLabel(result.degradedReason)"
          type="warning"
          show-icon
          :closable="false"
          class="degrade-note"
        />

        <pre class="answer">{{ result.answerText }}</pre>

        <!-- 闸门：BLOCK 必须显眼，它是"这个结论能不能用"的判据 -->
        <div v-if="(result.analyticsFacts?.gates || []).length" class="gate-list">
          <el-alert
            v-for="g in result.analyticsFacts.gates"
            :key="g.code + g.message"
            :title="g.message"
            :type="g.severity === 'BLOCK' ? 'error' : 'warning'"
            show-icon
            :closable="false"
          >
            <template #default><span class="gate-code">{{ g.code }}</span></template>
          </el-alert>
        </div>
      </el-card>

      <!-- 统计口径 -->
      <el-card v-if="result.analyticsFacts" shadow="never">
        <template #header><span class="section-title">统计口径</span></template>
        <el-descriptions :column="4" border size="small" class="metric-strip">
          <el-descriptions-item label="时间范围">
            {{ result.analyticsFacts.window?.label || '—' }}
            <span class="muted">
              （{{ result.analyticsFacts.window?.start }} ~ {{ result.analyticsFacts.window?.end }}）
            </span>
            <!-- 口径来源要看得见：区间可能是模型抽的语义槽位算出来的，也可能是
                 正则解析或默认值。读者得知道"这个区间是谁定的"。 -->
            <el-tag v-if="result.analyticsFacts.window?.source" size="small" effect="plain"
                    :type="windowSourceTag(result.analyticsFacts.window.source)">
              {{ result.analyticsFacts.window.source }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="范围限定">
            {{ (result.analyticsFacts.scope?.domains || []).join('、') || '全库' }}
          </el-descriptions-item>
          <el-descriptions-item label="纳入统计">
            {{ result.analyticsFacts.universe?.scoped }} / 有效
            {{ result.analyticsFacts.universe?.total }} 单
          </el-descriptions-item>
          <el-descriptions-item label="标签覆盖率">
            {{ result.analyticsFacts.coverage?.ratio }}%
          </el-descriptions-item>
        </el-descriptions>

        <!-- 覆盖率必须披露被排除的部分：未覆盖 ≠ 没有发生 -->
        <div v-if="excludedRows.length" class="excluded">
          <span class="muted">已排除的非有效工单：</span>
          <el-tag v-for="row in excludedRows" :key="row.name" size="small" type="info" effect="plain">
            {{ row.name }} {{ row.count }} 单
          </el-tag>
        </div>
      </el-card>

      <!-- 分布明细：读 facts，不读模型写的正文 -->
      <el-card
        v-for="dim in result.analyticsFacts?.dimensions || []"
        :key="dim.axis"
        shadow="never"
      >
        <template #header>
          <div class="card-header">
            <span class="section-title">{{ axisLabel(dim.axis) }}</span>
            <span v-if="dim.unmatchedCount" class="muted">
              未归入任何标签 {{ dim.unmatchedCount }} 单
            </span>
          </div>
        </template>

        <el-empty
          v-if="!dim.entries.length"
          :description="dim.axis === 'ROOT_CAUSE'
            ? '工单未记录解决方案，无法归纳根因'
            : '该维度无可用数据'"
          :image-size="60"
        />
        <el-table v-else :data="dim.entries" size="small" stripe>
          <el-table-column prop="label" label="项目" min-width="160" />
          <el-table-column prop="count" label="命中单数" width="100" align="right" />
          <el-table-column label="占本维度" width="120" align="right">
            <template #default="{ row }">
              <span v-if="row.ratio != null">{{ row.ratio }}%</span>
              <el-tag v-else size="small" type="info" effect="plain">样本不足</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="占全部工单" width="130" align="right">
            <template #default="{ row }">
              <span v-if="row.ratioOfAll != null">{{ row.ratioOfAll }}%</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="可下钻源工单" min-width="240">
            <template #default="{ row }">
              <template v-if="(row.sampleTicketIds || []).length">
                <el-tag
                  v-for="id in row.sampleTicketIds"
                  :key="id"
                  size="small"
                  effect="plain"
                  class="ticket-chip"
                >{{ id }}</el-tag>
              </template>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 建议分组展示：读者必须能分清哪部分是统计结论、哪部分是模型归纳 -->
      <el-card v-if="ruleRecs.length || modelRecs.length" shadow="never">
        <template #header>
          <div class="card-header">
            <span class="section-title">处置建议</span>
            <span class="muted">两类来源分开列出，不混在一起</span>
          </div>
        </template>

        <div v-if="ruleRecs.length" class="rec-group">
          <div class="rec-group-title">
            <el-tag size="small" type="info" effect="dark">系统算出</el-tag>
            <span class="muted">备件数量由命中单量 × 固定系数得出，口径可复核</span>
          </div>
          <ul class="rec-list">
            <li v-for="(rec, i) in ruleRecs" :key="`r${i}`">
              <el-tag size="small" :type="rec.kind === '备件' ? 'warning' : 'info'">{{ rec.kind }}</el-tag>
              <span>{{ rec.text }}</span>
            </li>
          </ul>
        </div>

        <div v-if="modelRecs.length" class="rec-group">
          <div class="rec-group-title">
            <el-tag size="small" type="primary" effect="dark">AI 归纳</el-tag>
            <span class="muted">模型在上述统计事实上归纳的方向，每条注明依据；已校验不含数据之外的数字</span>
          </div>
          <ul class="rec-list">
            <li v-for="(rec, i) in modelRecs" :key="`m${i}`">
              <el-tag size="small" type="primary" effect="plain">{{ rec.kind }}</el-tag>
              <span>{{ rec.text }}</span>
              <span v-if="rec.basisLabel" class="muted">（依据：{{ rec.basisLabel }}）</span>
            </li>
          </ul>
        </div>
      </el-card>

      <!-- 判定依据：结论必须可解释 -->
      <el-collapse v-if="(result.findings || []).length" class="findings">
        <el-collapse-item :title="`判定依据与链路（${result.findings.length} 条）`" name="f">
          <el-table :data="result.findings" size="small">
            <el-table-column prop="severity" label="级别" width="90" />
            <el-table-column prop="code" label="代码" width="220" />
            <el-table-column prop="message" label="说明" min-width="300" />
          </el-table>
          <div v-if="result.trace" class="trace-line">
            <span class="muted">链路：</span>
            <el-tag
              v-for="s in result.trace.spans"
              :key="s.spanName"
              size="small"
              effect="plain"
              :type="s.status === 'FAILED' ? 'danger' : (s.status === 'SKIPPED' ? 'info' : 'success')"
            >{{ s.spanName }}</el-tag>
            <span class="muted">耗时 {{ result.trace.totalLatencyMs }}ms</span>
          </div>
        </el-collapse-item>
      </el-collapse>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { analyticsApi } from '../api/index.js'

const samples = [
  '统计本季度全部工单的故障现象分布',
  '请根据全部网络与打印设备工单，总结本季度共性根因并给出备件采购建议',
  '本季度工单的共性根因是什么？',
]

const question = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)

const AXIS_LABEL = { SYMPTOM: '故障现象分布', DEVICE: '设备分布', ROOT_CAUSE: '共性根因' }
const REPLY_LABEL = { ANSWER: '已作答', CLARIFY: '需澄清', REFUSE: '已拒答', NOT_ANALYTICS: '非分析请求' }
const DEGRADED_LABEL = {
  MODEL_NOT_CONFIGURED: '未配置归因模型，以下为确定性统计文案（数字仍由系统算出）',
  MODEL_CALL_FAILED: '归因模型调用失败，已降级为确定性统计文案',
  MODEL_OUTPUT_UNPARSABLE: '模型输出不可用，已降级为确定性统计文案',
  MODEL_TRUNCATED: '模型输出被截断，已降级为确定性统计文案',
}

const axisLabel = (axis) => AXIS_LABEL[axis] || axis
const degradedLabel = (r) => DEGRADED_LABEL[r] || `已降级：${r}`
// 拒答原因要说人话、并且**要指路**：工程师在统计工作台上被拒，最需要的不是"失败了"，
// 而是"这问题该去哪问"。
const REFUSAL_LABEL = {
  OUT_OF_SCOPE: '不属于跨工单统计，请到智能客服提问',
  POLICY_BLOCKED: '权限不足',
  MODEL_UNAVAILABLE: '分析服务暂不可用',
  NO_RELIABLE_KNOWLEDGE: '样本不足以支撑结论',
}
const refusalLabel = (r) => REFUSAL_LABEL[r] || r
const REPLY_TAG_TYPE = { ANSWER: 'success', CLARIFY: 'warning', REFUSE: 'danger' }
// 熔断（OUT_OF_SCOPE）不是错误，别染成红色：工程师只是问错了地方，不是系统出问题。
// 另外它比裸的"已拒答"更能说明发生了什么，所以复用这一格显示。
const replyLabel = (t, reason) =>
  (t === 'REFUSE' && reason === 'OUT_OF_SCOPE' ? '不在本页范围' : REPLY_LABEL[t]) || t
const replyTagType = (t, reason) =>
  (t === 'REFUSE' && reason === 'OUT_OF_SCOPE' ? 'warning' : REPLY_TAG_TYPE[t] || 'info')
// 时间口径的来源：模型抽的槽位 / 正则解析 / 默认值。只有"模型抽取"值得高亮 ——
// 另外两种是既有行为，不该抢注意力。
const windowSourceTag = (s) => (s === '模型抽取' ? 'success' : 'info')

const excludedRows = computed(() => {
  const excluded = result.value?.analyticsFacts?.coverage?.excluded || {}
  return Object.entries(excluded).map(([name, count]) => ({ name, count }))
})

// 建议按来源分组：rule = 代码按固定系数算出（数字口径可复核），
// model = 模型在统计事实上归纳的方向（带依据标签）。分开列出，读者才分得清。
const allRecs = computed(() => result.value?.analyticsFacts?.recommendations || [])
const ruleRecs = computed(() => allRecs.value.filter(r => r.source !== 'model'))
const modelRecs = computed(() => allRecs.value.filter(r => r.source === 'model'))

async function run() {
  const q = question.value.trim()
  if (!q || loading.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await analyticsApi.query(q)
    // ApiEnvelope：{ code:'success', message, request_id, data }
    result.value = res?.data || null
    if (!result.value) error.value = '分析服务返回了空结果'
  } catch (e) {
    result.value = null
    error.value = e?.message || '分析失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.analytics-page { display: flex; flex-direction: column; gap: 16px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.page-eyebrow { font-size: 12px; letter-spacing: .12em; color: var(--el-text-color-secondary); }
.page-title { margin: 4px 0 6px; font-size: 22px; }
.page-sub { margin: 0; color: var(--el-text-color-secondary); font-size: 13px; max-width: 720px; }
.ask-card .ask-item { margin-bottom: 8px; }
.ask-actions { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.samples { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.samples-label { color: var(--el-text-color-secondary); font-size: 12px; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.header-tags { display: flex; gap: 6px; }
.section-title { font-weight: 600; }
.muted { color: var(--el-text-color-secondary); font-size: 12px; }
.answer { white-space: pre-wrap; margin: 0; font-family: inherit; line-height: 1.75; font-size: 14px; }
.degrade-note { margin-bottom: 12px; }
.gate-list { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.gate-code { font-size: 11px; letter-spacing: .06em; opacity: .8; }
.metric-strip :deep(.el-descriptions__label) { width: 96px; }
.excluded { margin-top: 10px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.ticket-chip { margin-right: 4px; }
.rec-list { margin: 0; padding-left: 18px; line-height: 2; }
.rec-group + .rec-group { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--el-border-color-lighter); }
.rec-group-title { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.findings { margin-top: 4px; }
.trace-line { margin-top: 10px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.page-error { margin-bottom: 4px; }
</style>