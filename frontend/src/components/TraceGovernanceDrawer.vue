<template>
  <el-drawer
    v-model="visible"
    title="🚀 成本治理与 Model Router 调用链路 (DeepSeek Harness)"
    direction="rtl"
    size="680px"
    class="governance-trace-drawer"
    :before-close="handleClose"
  >
    <template #header>
      <div class="drawer-header-custom">
        <div class="header-icon-box">
          <el-icon><Cpu /></el-icon>
        </div>
        <div class="header-title-box">
          <div class="drawer-title">Model Router 动态选模与全景调用链路</div>
          <div class="drawer-subtitle">DeepSeek Harness 架构 · 意图特征打分 · 双阶段 Token 预算池 · 成本精算</div>
        </div>
        <div class="header-close-btn" role="button" tabindex="0" title="关闭" @click="handleClose">
          <el-icon><Close /></el-icon>
        </div>
      </div>
    </template>

    <div v-if="normalizedTrace" class="drawer-body-wrap">
      <!-- 1. 核心看板横幅 -->
      <div class="summary-banner" :class="{ 'banner-degraded': normalizedTrace.isDegraded }">
        <div class="banner-top">
          <div class="banner-badge">
            <span class="pulse-dot" :class="{ 'pulse-warning': normalizedTrace.isDegraded }"></span>
            <span class="banner-tier">{{ tierInfo.label }}</span>
            <span class="banner-model">{{ normalizedTrace.chosenModel }}</span>
          </div>
          <div v-if="normalizedTrace.savingsRatePercent > 0" class="savings-tag">
            <el-icon><Discount /></el-icon> 较顶配节省 {{ normalizedTrace.savingsRatePercent.toFixed(1) }}%
          </div>
        </div>
        <p class="summary-desc">
          {{ normalizedTrace.routingReason || '系统已根据用户问题特征与风险等级自主完成动态模型梯队匹配与两阶段预算审查。' }}
        </p>
        <div v-if="normalizedTrace.isDegraded" class="degraded-alert">
          <el-icon><WarningFilled /></el-icon>
          <span>触发自适应预算降档：{{ normalizedTrace.degradationReason || '当前配额紧张，系统已安全降级至兼容模型执行' }}</span>
        </div>
      </div>

      <!-- 2. 四象限执行指标网格 (Executive KPI Cards) -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-header">
            <span class="kpi-icon"><el-icon><Coin /></el-icon></span>
            <span class="kpi-label">实际结算费用</span>
          </div>
          <div class="kpi-value text-accent">{{ formatCostRmb(normalizedTrace.actualCostRmb) }}</div>
          <div class="kpi-sub">省 {{ formatCostRmb(normalizedTrace.savedVsPremiumRmb) }}</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header">
            <span class="kpi-icon"><el-icon><DataAnalysis /></el-icon></span>
            <span class="kpi-label">总消耗 Token</span>
          </div>
          <div class="kpi-value">{{ normalizedTrace.totalTokens.toLocaleString() }}</div>
          <div class="kpi-sub">入 {{ normalizedTrace.promptTokens }} / 出 {{ normalizedTrace.completionTokens }}</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header">
            <span class="kpi-icon"><el-icon><Timer /></el-icon></span>
            <span class="kpi-label">端到端响应耗时</span>
          </div>
          <div class="kpi-value">{{ Math.round(normalizedTrace.totalLatencyMs) }} ms</div>
          <div class="kpi-sub">{{ throughputText }}</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-header">
            <span class="kpi-icon"><el-icon><Aim /></el-icon></span>
            <span class="kpi-label">意图风险评分</span>
          </div>
          <div class="kpi-value" :class="riskColorClass">{{ normalizedTrace.riskScore }} / 5</div>
          <div class="kpi-sub">{{ normalizedTrace.intent }} 风险等级</div>
        </div>
      </div>

      <!-- 3. 降本对比仪表条 (Cost Comparison Bar) -->
      <div class="cost-comparison-section">
        <div class="section-title">
          <el-icon><TrendCharts /></el-icon>
          <span>多梯队降本成效对比 (Cost Optimization)</span>
        </div>
        <div class="comparison-bar-card">
          <div class="bar-labels">
            <span>实耗费用: {{ formatCostRmb(normalizedTrace.actualCostRmb) }}</span>
            <span class="baseline-label">顶配基准 (Max): {{ formatCostRmb(normalizedTrace.actualCostRmb + normalizedTrace.savedVsPremiumRmb) }}</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: fillPercent + '%' }"></div>
          </div>
          <div class="bar-footer">
            <span class="savings-highlight">已通过 Model Router 削峰降低 {{ normalizedTrace.savingsRatePercent.toFixed(1) }}% 算力开销</span>
          </div>
        </div>
      </div>

      <!-- 4. DeepSeek Harness 五阶段时序调用链路 (Pipeline Stages) -->
      <div class="pipeline-section">
        <div class="section-title">
          <el-icon><Connection /></el-icon>
          <span>五阶段执行时序追踪 (DeepSeek Harness Pipeline)</span>
        </div>

        <div class="stages-timeline">
          <div
            v-for="(stage, idx) in normalizedTrace.stages"
            :key="stage.stageId"
            class="stage-node"
            :class="['status-' + stage.status.toLowerCase()]"
          >
            <!-- 节点指示器 -->
            <div class="stage-marker">
              <span class="stage-seq">0{{ idx + 1 }}</span>
              <div class="marker-line" v-if="idx < normalizedTrace.stages.length - 1"></div>
            </div>

            <!-- 节点主体卡片 -->
            <div class="stage-content">
              <div class="stage-content-head">
                <div class="stage-name-box">
                  <span class="stage-name">{{ stage.name }}</span>
                  <el-tag :type="stageTagType(stage.status)" size="small" effect="plain" class="stage-tag">
                    {{ stage.status }}
                  </el-tag>
                </div>
                <div class="stage-time">
                  <el-icon><Timer /></el-icon>
                  <span>{{ stage.durationMs }}ms</span>
                </div>
              </div>

              <div class="stage-summary">{{ stage.summary }}</div>

              <!-- 阶段明细表格/指标 -->
              <div v-if="hasDetails(stage)" class="stage-details-box">
                <div v-for="(val, key) in stage.details" :key="key" class="detail-row">
                  <span class="detail-k">{{ formatKey(key) }}:</span>
                  <span class="detail-v">{{ formatValue(val) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 5. 原始 Trace 报文审查 (JSON View) -->
      <div class="json-section">
        <div class="json-header" @click="jsonExpanded = !jsonExpanded">
          <div class="json-title">
            <el-icon><Document /></el-icon>
            <span>完整结构化 Trace 审计报文 (Raw JSON)</span>
          </div>
          <div class="json-actions">
            <el-button size="small" type="primary" link @click.stop="copyJson">
              <el-icon><CopyDocument /></el-icon> 复制报文
            </el-button>
            <el-icon class="arrow-icon" :class="{ 'is-expanded': jsonExpanded }"><ArrowDown /></el-icon>
          </div>
        </div>
        <el-collapse-transition>
          <div v-show="jsonExpanded" class="json-pre-wrap">
            <pre class="json-pre"><code>{{ formattedRawJson }}</code></pre>
          </div>
        </el-collapse-transition>
      </div>
    </div>

    <template #footer>
      <div class="drawer-footer">
        <el-button @click="handleClose">关闭</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Cpu,
  Coin,
  DataAnalysis,
  Timer,
  Aim,
  TrendCharts,
  Connection,
  Discount,
  WarningFilled,
  Document,
  CopyDocument,
  ArrowDown,
  Close
} from '@element-plus/icons-vue'
import {
  formatCostRmb,
  formatTierBadge,
  parseGovernanceTrace
} from '../utils/governanceTrace.js'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  trace: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'close'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const jsonExpanded = ref(false)

const normalizedTrace = computed(() => {
  if (!props.trace) return null
  return parseGovernanceTrace({ governanceTrace: props.trace })
})

const tierInfo = computed(() => {
  return formatTierBadge(normalizedTrace.value?.chosenTier)
})

const throughputText = computed(() => {
  if (!normalizedTrace.value) return ''
  const sec = normalizedTrace.value.totalLatencyMs / 1000.0
  if (sec <= 0 || normalizedTrace.value.completionTokens <= 0) return '流式响应'
  const tps = Math.round(normalizedTrace.value.completionTokens / sec)
  return `${tps} tokens/s`
})

const riskColorClass = computed(() => {
  const score = normalizedTrace.value?.riskScore || 1
  if (score >= 4) return 'text-danger'
  if (score >= 3) return 'text-warning'
  return 'text-success'
})

const fillPercent = computed(() => {
  if (!normalizedTrace.value) return 100
  const actual = normalizedTrace.value.actualCostRmb
  const saved = normalizedTrace.value.savedVsPremiumRmb
  const total = actual + saved
  if (total <= 0) return 100
  return Math.max(8, Math.min(100, Math.round((actual / total) * 100)))
})

const formattedRawJson = computed(() => {
  if (!normalizedTrace.value?.raw) return ''
  return JSON.stringify(normalizedTrace.value.raw, null, 2)
})

function stageTagType(status) {
  if (status === 'DEGRADED' || status === 'WARNING') return 'warning'
  if (status === 'FAILED') return 'danger'
  return 'success'
}

function hasDetails(stage) {
  return stage.details && Object.keys(stage.details).length > 0
}

function formatKey(key) {
  const dict = {
    score: '复杂度评分',
    riskLevel: '风险等级',
    riskHits: '高危触发词',
    hopHits: '多跳特征',
    routedTier: '初始裁决档位',
    chosenTier: '实际获准档位',
    minTier: '安全底线档位',
    chosenModel: '物理模型标识',
    reasons: '裁决理由列表',
    estimatedTokens: '预扣冻结 Token',
    degraded: '是否触发降档',
    perRequestCap: '单次请求上限',
    maxOutputReserve: '最大输出敞口',
    model: '模型名称',
    promptTokens: '输入 Tokens',
    completionTokens: '输出 Tokens',
    totalTokens: '合计 Tokens',
    latencyMs: '实际耗时 (ms)',
    actualCostRmb: '结算实费 (¥)',
    baselinePremiumCostRmb: '顶配基准费 (¥)',
    savedVsPremiumRmb: '节省金额 (¥)',
    savingsRatePercent: '降本率 (%)',
    releasedTokens: '释放预算差额'
  }
  return dict[key] || key
}

function formatValue(val) {
  if (Array.isArray(val)) {
    return val.length > 0 ? val.join('；') : '无'
  }
  if (typeof val === 'boolean') {
    return val ? '是' : '否'
  }
  return String(val)
}

function copyJson() {
  if (!formattedRawJson.value) return
  navigator.clipboard.writeText(formattedRawJson.value).then(() => {
    ElMessage.success('Trace 报文已成功复制至剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败，请手动选择复制')
  })
}

function handleClose(done) {
  visible.value = false
  emit('update:modelValue', false)
  emit('close')
  if (typeof done === 'function') {
    done()
  }
}
</script>

<style scoped>
.governance-trace-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(26, 127, 165, 0.16);
  background: #F8FAFC;
}

.drawer-header-custom {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.header-close-btn {
  margin-left: auto;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748B;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.header-close-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #0F172A;
}

.header-icon-box {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: linear-gradient(135deg, #08758C 0%, #245DCE 100%);
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  box-shadow: 0 4px 10px rgba(8, 117, 140, 0.25);
}

.drawer-title {
  font-size: 16px;
  font-weight: 700;
  color: #1E293B;
  letter-spacing: 0.2px;
}

.drawer-subtitle {
  font-size: 12px;
  color: #64748B;
  margin-top: 2px;
}

.drawer-body-wrap {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 4px 0 24px;
}

/* 1. 顶部场景横幅 */
.summary-banner {
  background: linear-gradient(135deg, #EDF8FA 0%, #F4F8FC 100%);
  border: 1px solid rgba(8, 117, 140, 0.2);
  border-radius: 10px;
  padding: 16px;
}

.banner-degraded {
  background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
  border-color: rgba(217, 119, 6, 0.3);
}

.banner-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.banner-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10B981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}

.pulse-warning {
  background: #F59E0B;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2);
}

.banner-tier {
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  background: #08758C;
  color: #FFFFFF;
}

.banner-model {
  font-size: 13px;
  font-weight: 600;
  color: #1E293B;
  font-family: monospace;
}

.savings-tag {
  font-size: 12px;
  font-weight: 600;
  color: #059669;
  background: #ECFDF5;
  border: 1px solid rgba(16, 185, 129, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.summary-desc {
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
  margin: 0;
}

.degraded-alert {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(245, 158, 11, 0.12);
  color: #B45309;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 2. KPI 网格 */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.kpi-card {
  background: #FFFFFF;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 8px;
  padding: 12px 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.kpi-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748B;
  margin-bottom: 6px;
}

.kpi-icon {
  font-size: 14px;
  color: #08758C;
}

.kpi-value {
  font-size: 18px;
  font-weight: 700;
  color: #0F172A;
  font-family: monospace;
}

.kpi-sub {
  font-size: 11px;
  color: #94A3B8;
  margin-top: 2px;
}

.text-accent {
  color: #08758C;
}

.text-success {
  color: #10B981;
}

.text-warning {
  color: #F59E0B;
}

.text-danger {
  color: #EF4444;
}

/* 3. 降本对比条 */
.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #1E293B;
  margin-bottom: 10px;
}

.comparison-bar-card {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 12px 14px;
}

.bar-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  font-family: monospace;
  color: #334155;
  margin-bottom: 6px;
}

.baseline-label {
  color: #94A3B8;
}

.progress-track {
  width: 100%;
  height: 10px;
  background: #E2E8F0;
  border-radius: 5px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #08758C 0%, #10B981 100%);
  border-radius: 5px;
  transition: width 0.4s ease;
}

.bar-footer {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.savings-highlight {
  font-size: 11px;
  font-weight: 600;
  color: #059669;
}

/* 4. 时序流程树 */
.stages-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
}

.stage-node {
  display: flex;
  gap: 12px;
  position: relative;
}

.stage-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 28px;
  flex-shrink: 0;
}

.stage-seq {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #EDF4FA;
  border: 2px solid #08758C;
  color: #08758C;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.marker-line {
  flex: 1;
  width: 2px;
  background: rgba(8, 117, 140, 0.2);
  margin: 4px 0;
}

.status-degraded .stage-seq {
  border-color: #F59E0B;
  color: #F59E0B;
  background: #FEF3C7;
}

.stage-content {
  flex: 1;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 10px 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.stage-content-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.stage-name-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stage-name {
  font-size: 13px;
  font-weight: 700;
  color: #1E293B;
}

.stage-time {
  font-size: 11px;
  color: #64748B;
  display: flex;
  align-items: center;
  gap: 3px;
  font-family: monospace;
}

.stage-summary {
  font-size: 12px;
  color: #475569;
  line-height: 1.4;
  margin-bottom: 6px;
}

.stage-details-box {
  background: #F8FAFC;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 11px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.detail-row {
  display: flex;
  gap: 6px;
}

.detail-k {
  color: #64748B;
  flex-shrink: 0;
}

.detail-v {
  color: #1E293B;
  font-family: monospace;
  word-break: break-all;
}

/* 5. JSON 折叠查看 */
.json-section {
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: #FFFFFF;
  overflow: hidden;
}

.json-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #F8FAFC;
  cursor: pointer;
  user-select: none;
}

.json-title {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 6px;
}

.json-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.arrow-icon {
  font-size: 12px;
  color: #94A3B8;
  transition: transform 0.2s ease;
}

.arrow-icon.is-expanded {
  transform: rotate(180deg);
}

.json-pre-wrap {
  padding: 10px 14px;
  background: #0F172A;
  max-height: 240px;
  overflow: auto;
}

.json-pre {
  margin: 0;
  color: #38BDF8;
  font-family: monospace;
  font-size: 11px;
  line-height: 1.4;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
