/**
 * Model Router 动态选模与成本治理 (DeepSeek Harness 架构) 数据解析与格式化工具
 */

export function parseGovernanceTrace(msg) {
  if (!msg) return null
  const trace = msg.governanceTrace || msg.governance_trace
  if (!trace || typeof trace !== 'object') return null

  // 统一字段命名规范（支持 camelCase 与 snake_case）
  const chosenTier = (trace.chosenTier || trace.chosen_tier || 'LITE').toUpperCase()
  const chosenModel = trace.chosenModel || trace.chosen_model || 'qwen3.7-flash'
  const routingReason = trace.routingReason || trace.routing_reason || ''
  const riskScore = Number(trace.riskScore ?? trace.risk_score ?? 1)
  const intent = trace.intent || 'LOW'
  const totalTokens = Number(trace.totalTokens ?? trace.total_tokens ?? 0)
  const promptTokens = Number(trace.promptTokens ?? trace.prompt_tokens ?? 0)
  const completionTokens = Number(trace.completionTokens ?? trace.completion_tokens ?? 0)
  const totalLatencyMs = Number(trace.totalLatencyMs ?? trace.total_latency_ms ?? 0)
  const actualCostRmb = Number(trace.actualCostRmb ?? trace.actual_cost_rmb ?? 0)
  const savedVsPremiumRmb = Number(trace.savedVsPremiumRmb ?? trace.saved_vs_premium_rmb ?? 0)
  const savingsRatePercent = Number(trace.savingsRatePercent ?? trace.savings_rate_percent ?? 0)
  const isDegraded = Boolean(trace.isDegraded ?? trace.is_degraded)
  const degradationReason = trace.degradationReason || trace.degradation_reason || null

  const rawStages = Array.isArray(trace.stages) ? trace.stages : []
  const stages = rawStages.map((s, idx) => ({
    stageId: s.stageId || s.stage_id || `stage_${idx + 1}`,
    name: s.name || `阶段 ${idx + 1}`,
    status: s.status || 'SUCCESS',
    durationMs: Number(s.durationMs ?? s.duration_ms ?? 0),
    summary: s.summary || '',
    details: s.details || {}
  }))

  return {
    traceId: trace.traceId || trace.trace_id || '',
    chosenTier,
    chosenModel,
    routingReason,
    riskScore,
    intent,
    totalTokens,
    promptTokens,
    completionTokens,
    totalLatencyMs,
    actualCostRmb,
    savedVsPremiumRmb,
    savingsRatePercent,
    isDegraded,
    degradationReason,
    stages,
    raw: trace
  }
}

export function hasGovernanceTrace(msg) {
  return parseGovernanceTrace(msg) !== null
}

export function formatTierBadge(tier) {
  const t = (tier || '').toUpperCase()
  if (t === 'PREMIUM') return { label: 'PREMIUM 旗舰', type: 'danger', tagClass: 'tier-premium' }
  if (t === 'STANDARD') return { label: 'STANDARD 均衡', type: 'warning', tagClass: 'tier-standard' }
  return { label: 'LITE 极速', type: 'success', tagClass: 'tier-lite' }
}

export function formatCostRmb(val) {
  if (typeof val !== 'number' || isNaN(val)) return '¥0.000000'
  return `¥${val.toFixed(6)}`
}
