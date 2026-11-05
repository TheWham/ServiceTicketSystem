# -*- coding: utf-8 -*-
"""cost_governance.py

企业级 IT Service Desk 成本治理与 Model Router 动态选模核心控制引擎。
将 Day 29 的生产级成本治理与 DeepSeek Harness 全景调用链路追踪整合进 agent_service。

包含核心能力：
1. 模型分级画像与定价基准 (MODEL_CATALOG)：LITE, STANDARD, PREMIUM
2. 动态分词预估 (estimate_tokens) 与财务计费 (estimate_cost)
3. 智能模型路由器 (ModelRouter)：意图分析、复杂度打分、生产安全底线 (min_tier) 与启发式兜底
4. 三级两阶段 Token 预算池 (TokenBudgetManager)：单次/日/月预算、原子预扣、真实结算与异常释放
5. 成本总控引擎 (CostGovernor)：端到端规划、自适应级联降档、429 生产安全熔断与 5 阶段 Harness Trace 生成
"""
from dataclasses import dataclass, field
from enum import Enum
import json
import math
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI


class ModelTier(str, Enum):
    """模型梯队档位枚举"""
    LITE = "lite"          # 轻量快速模型：标准 IT FAQ、密码重置、基础操作指引 (qwen3.7-flash)
    STANDARD = "standard"  # 中档云端模型：网络架构对比、故障排查、复杂配置解读 (qwen3.7-plus)
    PREMIUM = "premium"    # 旗舰推理模型：生产库提权特批、高危权限审批、跨系统安全审计 (qwen3.8-max)


@dataclass(frozen=True)
class ModelProfile:
    """单个模型的基准配置画像与计费凭据"""
    tier: ModelTier
    model_name: str
    price_per_1k_input: float   # 元 / 1K 输入 Token
    price_per_1k_output: float  # 元 / 1K 输出 Token
    max_output_tokens: int


# 【模型梯队物理目录】：对齐生产实际定价与容量基准
MODEL_CATALOG: Dict[ModelTier, ModelProfile] = {
    ModelTier.LITE: ModelProfile(
        tier=ModelTier.LITE,
        model_name="qwen3.7-flash",
        price_per_1k_input=0.0002,   # ¥0.0002 / 1K tokens
        price_per_1k_output=0.0006,  # ¥0.0006 / 1K tokens
        max_output_tokens=1024,
    ),
    ModelTier.STANDARD: ModelProfile(
        tier=ModelTier.STANDARD,
        model_name="qwen3.7-plus",
        price_per_1k_input=0.0008,   # ¥0.0008 / 1K tokens
        price_per_1k_output=0.0020,  # ¥0.0020 / 1K tokens
        max_output_tokens=2560,
    ),
    ModelTier.PREMIUM: ModelProfile(
        tier=ModelTier.PREMIUM,
        model_name="qwen3.8-max",
        price_per_1k_input=0.0024,   # ¥0.0024 / 1K tokens
        price_per_1k_output=0.0096,  # ¥0.0096 / 1K tokens
        max_output_tokens=3072,
    ),
}

TIER_ORDER: List[ModelTier] = [ModelTier.LITE, ModelTier.STANDARD, ModelTier.PREMIUM]
SYSTEM_PROMPT_RESERVE = 200


def estimate_tokens(text: str) -> int:
    """中英文混合动态 Token 极速估算算法"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return cjk + math.ceil((len(text) - cjk) / 4)


def estimate_cost(model: ModelProfile, input_tokens: int, output_tokens: int) -> float:
    """计算模型实际或预估调用的财务费用（人民币：元）"""
    cost = (input_tokens / 1000.0 * model.price_per_1k_input) + (
        output_tokens / 1000.0 * model.price_per_1k_output
    )
    return round(cost, 6)


@dataclass
class RouteDecision:
    """模型路由器的裁决结果封装"""
    tier: ModelTier
    min_tier: ModelTier
    score: int
    reasons: List[str] = field(default_factory=list)
    risk_hits: List[str] = field(default_factory=list)
    hop_hits: List[str] = field(default_factory=list)
    risk_level: str = "LOW"


ROUTER_SYSTEM_PROMPT = """你是一个企业级 IT Service Desk 的智能模型路由器 (Model Router)。
你的任务是深度理解用户的 IT 运维咨询或操作请求，自主评估意图复杂度与安全风险，做出模型档位裁决：

【模型档位分类】：
1. lite: 标准常见 FAQ、Wi-Fi 密码、网络准入指引、通用软件操作、基础密码重置等（对应 qwen3.7-flash）。
2. standard: 架构方案对比、性能与延迟排查、拓扑链路分析、常规配置解读等（对应 qwen3.7-plus）。
3. premium: 生产环境数据库 (DROP/ALTER/DELETE) 高危变更特批、root/管理员高危提权审批、安全合规审计裁决等（对应 qwen3.8-max）。

【安全底线 min_tier 核心规则】：
- 若涉及生产数据库操作、核心生产表 ALTER/DROP、高危特批审批、越权安全审计，min_tier 必须锁定为 standard（预算不足时严禁使用轻量小模型，宁可 429 熔断转人工）。
- 普通网络咨询、标准 FAQ 的 min_tier 设定为 lite。

输出且仅输出合法 JSON 格式，禁止添加任何代码块反引号：
{
  "tier": "lite" | "standard" | "premium",
  "min_tier": "lite" | "standard",
  "score": 1到5的整数,
  "reasons": ["依据1", "依据2"],
  "risk_level": "LOW" | "MEDIUM" | "HIGH"
}"""


class ModelRouter:
    """智能模型路由器实现类"""

    def __init__(self, client: Optional[OpenAI] = None, router_model: str = "qwen3.7-flash"):
        self.client = client
        self.router_model = router_model

    def route(self, query: str, history_turns: int = 0) -> RouteDecision:
        """执行路由裁决流程：优先小模型 AI 判决，异常快速回退至启发式兜底"""
        if self.client:
            try:
                resp = self.client.chat.completions.create(
                    model=self.router_model,
                    messages=[
                        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                        {"role": "user", "content": f"用户提问：{query}\n历史对话轮次：{history_turns}"},
                    ],
                    max_tokens=250,
                    temperature=0.0,
                )
                raw = resp.choices[0].message.content.strip()
                if raw.startswith("```"):
                    raw = raw.strip("`").strip("json").strip()
                data = json.loads(raw)

                tier_str = str(data.get("tier", "lite")).lower()
                min_tier_str = str(data.get("min_tier", "lite")).lower()

                tier = ModelTier.PREMIUM if tier_str == "premium" else (
                    ModelTier.STANDARD if tier_str == "standard" else ModelTier.LITE
                )
                min_tier = ModelTier.STANDARD if min_tier_str == "standard" else ModelTier.LITE

                return RouteDecision(
                    tier=tier,
                    min_tier=min_tier,
                    score=int(data.get("score", 1)),
                    reasons=data.get("reasons", ["模型自主意图判决"]),
                    risk_hits=["高危特批/生产变更"] if min_tier == ModelTier.STANDARD else [],
                    hop_hits=["深度架构/对比分析"] if tier == ModelTier.STANDARD else [],
                    risk_level=data.get("risk_level", "LOW"),
                )
            except Exception:
                pass

        # 启发式规则兜底分析
        is_high_risk = any(k in query for k in ["特批", "审批", "提权", "核心生产库", "生产环境", "DROP", "ALTER", "删库"])
        is_multi_hop = any(k in query for k in ["对比", "架构", "方案", "链路", "区别", "分析"])

        if is_high_risk:
            tier, min_tier, score = ModelTier.PREMIUM, ModelTier.STANDARD, 5
            reasons = ["识别到生产环境高危变更与特批审批，安全底线锁定为旗舰模型承接"]
        elif is_multi_hop or estimate_tokens(query) > 100:
            tier, min_tier, score = ModelTier.STANDARD, ModelTier.LITE, 3
            reasons = ["识别到网络方案对比或长文本多跳分析，由中档推理模型承接"]
        else:
            tier, min_tier, score = ModelTier.LITE, ModelTier.LITE, 1
            reasons = ["识别为标准 IT 常见 FAQ 咨询，由极速轻量模型直出"]

        return RouteDecision(
            tier=tier,
            min_tier=min_tier,
            score=score,
            reasons=reasons,
            risk_hits=["生产高危"] if is_high_risk else [],
            hop_hits=["架构对比"] if is_multi_hop else [],
            risk_level="HIGH" if is_high_risk else "LOW",
        )


class BudgetExceeded(Exception):
    """预算耗尽异常"""
    def __init__(self, scope: str, detail: str, is_circuit_breaker: bool = False):
        super().__init__(f"[{scope}] {detail}")
        self.scope = scope
        self.detail = detail
        self.is_circuit_breaker = is_circuit_breaker


@dataclass
class BudgetAccount:
    """预算账户实体数据模型"""
    limit: int
    used: int = 0
    reserved: int = 0

    @property
    def available(self) -> int:
        return max(0, self.limit - self.used - self.reserved)


class TokenBudgetManager:
    """三级 Token 预算两阶段管控中心"""

    def __init__(
        self,
        per_request_cap: int = 16000,
        user_daily_limit: int = 100000,
        dept_monthly_limit: int = 2000000,
    ):
        self.per_request_cap = int(os.environ.get("AGENT_BUDGET_PER_REQUEST", str(per_request_cap)))
        self.user_daily_limit = int(os.environ.get("AGENT_BUDGET_USER_DAILY", str(user_daily_limit)))
        self.dept_monthly_limit = int(os.environ.get("AGENT_BUDGET_DEPT_MONTHLY", str(dept_monthly_limit)))
        self._accounts: Dict[str, BudgetAccount] = {}
        self._reservations: Dict[str, Tuple[List[str], int]] = {}
        self._lock = threading.Lock()

    def _scopes(self, user_id: str, dept_id: str) -> List[Tuple[str, int]]:
        day = time.strftime("%Y%m%d")
        month = time.strftime("%Y%m")
        return [
            (f"user:{user_id}:{day}", self.user_daily_limit),
            (f"dept:{dept_id}:{month}", self.dept_monthly_limit),
        ]

    def reserve(self, request_id: str, user_id: str, dept_id: str, estimated: int) -> None:
        """阶段一：两阶段预扣冻结"""
        if estimated > self.per_request_cap:
            raise BudgetExceeded(
                "request",
                f"单次请求预估 {estimated} Token 超过单次硬上限 {self.per_request_cap}",
            )
        with self._lock:
            accounts = [
                (k, self._accounts.setdefault(k, BudgetAccount(limit)))
                for k, limit in self._scopes(user_id, dept_id)
            ]
            for key, acc in accounts:
                if acc.available < estimated:
                    raise BudgetExceeded(
                        key,
                        f"账户 [{key}] 剩余额度仅 {acc.available} Token，不足以覆盖预估预扣 {estimated} Token",
                    )
            for _, acc in accounts:
                acc.reserved += estimated
            self._reservations[request_id] = ([k for k, _ in accounts], estimated)

    def settle(self, request_id: str, actual_tokens: int) -> None:
        """阶段二：真实结算与多退少补"""
        with self._lock:
            res = self._reservations.pop(request_id, None)
            if not res:
                return
            keys, estimated = res
            for key in keys:
                acc = self._accounts.get(key)
                if acc:
                    acc.reserved = max(0, acc.reserved - estimated)
                    acc.used += actual_tokens

    def release(self, request_id: str) -> None:
        """异常撤销：全额解冻归还"""
        with self._lock:
            res = self._reservations.pop(request_id, None)
            if not res:
                return
            keys, estimated = res
            for key in keys:
                acc = self._accounts.get(key)
                if acc:
                    acc.reserved = max(0, acc.reserved - estimated)

    def snapshot(self, user_id: str, dept_id: str) -> Dict[str, Dict[str, int]]:
        """获取用户与部门的实时预算健康快照"""
        with self._lock:
            res = {}
            for key, limit in self._scopes(user_id, dept_id):
                acc = self._accounts.setdefault(key, BudgetAccount(limit))
                res[key] = {
                    "limit": acc.limit,
                    "used": acc.used,
                    "reserved": acc.reserved,
                    "available": acc.available,
                }
            return res


@dataclass
class CostPlan:
    """模型执行与预算核准计划"""
    request_id: str
    model: ModelProfile
    routed_tier: ModelTier
    min_tier: ModelTier
    estimated_tokens: int
    degraded: bool
    reasons: List[str]
    score: int
    decision: RouteDecision
    start_time: float = field(default_factory=time.perf_counter)


class CostGovernor:
    """成本与安全总控器"""

    def __init__(self, router: ModelRouter, budget: TokenBudgetManager):
        self.router = router
        self.budget = budget

    def plan(
        self,
        request_id: str,
        query: str,
        user_id: str,
        dept_id: str,
        history_turns: int = 0,
        extra_prompt_tokens: int = 0,
    ) -> CostPlan:
        """执行总控规划决策：路由 -> 估算 -> 尝试预扣 -> 级联降级 -> 安全熔断"""
        decision = self.router.route(query, history_turns)
        input_tokens = estimate_tokens(query) + extra_prompt_tokens + SYSTEM_PROMPT_RESERVE

        hi = TIER_ORDER.index(decision.tier)
        lo = TIER_ORDER.index(decision.min_tier)
        last_error: Optional[BudgetExceeded] = None

        for idx in range(hi, lo - 1, -1):
            model = MODEL_CATALOG[TIER_ORDER[idx]]
            estimated = input_tokens + model.max_output_tokens
            try:
                self.budget.reserve(request_id, user_id, dept_id, estimated)
                reasons = list(decision.reasons)
                is_degraded = (idx != hi)
                if is_degraded:
                    reasons.append(
                        f"⚠️ 预算预扣不足触发自适应降档：{decision.tier.value} → {model.tier.value}"
                    )
                return CostPlan(
                    request_id=request_id,
                    model=model,
                    routed_tier=decision.tier,
                    min_tier=decision.min_tier,
                    estimated_tokens=estimated,
                    degraded=is_degraded,
                    reasons=reasons,
                    score=decision.score,
                    decision=decision,
                )
            except BudgetExceeded as exc:
                last_error = exc

        # 若降到 min_tier 依然无法满足预算要求
        if decision.min_tier != ModelTier.LITE:
            raise BudgetExceeded(
                scope=last_error.scope if last_error else "budget",
                detail=(
                    f"【安全熔断 429】当前请求涉及高危生产特批（min_tier 锁定为 "
                    f"{decision.min_tier.value}），预算不足且严禁降级至轻量小模型；"
                    f"请求已自动熔断拦截，请联系平台管理员或转人工审核。"
                ),
                is_circuit_breaker=True,
            )
        raise last_error or BudgetExceeded("unknown", "预算不足且降级失败")

    def build_trace(
        self,
        plan: CostPlan,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        stages_extra: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """构建 DeepSeek Harness 风格的 5 阶段完整调用链路追踪数据"""
        total_tokens = prompt_tokens + completion_tokens
        actual_cost_rmb = estimate_cost(plan.model, prompt_tokens, completion_tokens)

        # 以顶配 PREMIUM (qwen3.8-max) 作为基准对比线
        premium_model = MODEL_CATALOG[ModelTier.PREMIUM]
        baseline_cost_rmb = estimate_cost(premium_model, prompt_tokens, completion_tokens)
        saved_vs_premium_rmb = max(0.0, round(baseline_cost_rmb - actual_cost_rmb, 6))
        savings_rate = (
            round((saved_vs_premium_rmb / baseline_cost_rmb) * 100.0, 1)
            if baseline_cost_rmb > 0
            else 0.0
        )

        stages: List[Dict[str, Any]] = [
            {
                "stageId": "01_FEATURE_SCORING",
                "name": "特征提取与意图打分",
                "status": "SUCCESS",
                "durationMs": round(latency_ms * 0.05, 1),
                "summary": f"意图识别: {plan.decision.risk_level} 风险 (评分 {plan.score}/5)",
                "details": {
                    "score": plan.score,
                    "riskLevel": plan.decision.risk_level,
                    "riskHits": plan.decision.risk_hits,
                    "hopHits": plan.decision.hop_hits,
                },
            },
            {
                "stageId": "02_MODEL_ROUTING",
                "name": "Model Router 动态选模",
                "status": "SUCCESS",
                "durationMs": round(latency_ms * 0.1, 1),
                "summary": f"推荐梯队 {plan.routed_tier.value.upper()}，获准调度 {plan.model.tier.value.upper()} ({plan.model.model_name})",
                "details": {
                    "routedTier": plan.routed_tier.value,
                    "chosenTier": plan.model.tier.value,
                    "minTier": plan.min_tier.value,
                    "chosenModel": plan.model.model_name,
                    "reasons": plan.reasons,
                },
            },
            {
                "stageId": "03_BUDGET_RESERVATION",
                "name": "两阶段 Token 预算审查",
                "status": "DEGRADED" if plan.degraded else "SUCCESS",
                "durationMs": round(latency_ms * 0.05, 1),
                "summary": f"成功预扣 {plan.estimated_tokens} Token" + (" (触发自适应降档)" if plan.degraded else " (预算充足)"),
                "details": {
                    "estimatedTokens": plan.estimated_tokens,
                    "degraded": plan.degraded,
                    "perRequestCap": self.budget.per_request_cap,
                    "maxOutputReserve": plan.model.max_output_tokens,
                },
            },
            {
                "stageId": "04_LLM_GENERATION",
                "name": "大模型真实生成执行",
                "status": "SUCCESS",
                "durationMs": round(latency_ms * 0.75, 1),
                "summary": f"{plan.model.model_name} 产出 {completion_tokens} Tokens，输入 {prompt_tokens} Tokens",
                "details": {
                    "model": plan.model.model_name,
                    "promptTokens": prompt_tokens,
                    "completionTokens": completion_tokens,
                    "totalTokens": total_tokens,
                    "latencyMs": latency_ms,
                },
            },
            {
                "stageId": "05_COST_SETTLEMENT",
                "name": "费用精算与敞口释放",
                "status": "SUCCESS",
                "durationMs": round(latency_ms * 0.05, 1),
                "summary": f"结算实费 ¥{actual_cost_rmb:.6f}，较顶配节省 {savings_rate}%",
                "details": {
                    "actualCostRmb": actual_cost_rmb,
                    "baselinePremiumCostRmb": baseline_cost_rmb,
                    "savedVsPremiumRmb": saved_vs_premium_rmb,
                    "savingsRatePercent": savings_rate,
                    "releasedTokens": max(0, plan.estimated_tokens - total_tokens),
                },
            },
        ]

        if stages_extra:
            stages.extend(stages_extra)

        return {
            "traceId": plan.request_id,
            "chosenTier": plan.model.tier.value.upper(),
            "chosenModel": plan.model.model_name,
            "routingReason": "；".join(plan.reasons),
            "riskScore": float(plan.score),
            "intent": plan.decision.risk_level,
            "totalTokens": total_tokens,
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "totalLatencyMs": latency_ms,
            "actualCostRmb": actual_cost_rmb,
            "savedVsPremiumRmb": saved_vs_premium_rmb,
            "savingsRatePercent": savings_rate,
            "isDegraded": plan.degraded,
            "degradationReason": next((r for r in plan.reasons if "降档" in r), None) if plan.degraded else None,
            "stages": stages,
        }
