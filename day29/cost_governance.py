# -*- coding: utf-8 -*-
"""cost_governance.py

Day 29 生产级 Model Router 动态选模与 Token 三级预算控制引擎。
契合企业级 IT Service Desk（IT 服务台与智能运维）场景：
1. 模型分级目录：接入新一代模型梯队 (qwen3.7-flash, qwen3.7-plus, qwen3.8-max)；
2. 动态路由：规则打分（高危提权/特批 +4，多跳架构/排查 +2，长输入 +2，长轮次 +1）；
3. 安全底线 (min_tier)：高危生产权限请求严禁降级到 LITE 本地小模型，宁可 429 熔断转人工；
4. Token 预算管理：单次上限 + 用户日预算 + 部门月预算，“预扣 -> 结算 -> 归还”两阶段记账。
"""

import math
import sys
import threading
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ==============================================================================
# 1. 模型分级目录与单价（元 / 1K Token）
# ==============================================================================

class ModelTier(str, Enum):
    LITE = "lite"          # 轻量快速模型：标准 IT FAQ、密码重置、基础操作指引
    STANDARD = "standard"  # 中档云端模型：网络架构对比、故障排查、复杂配置解读
    PREMIUM = "premium"    # 旗舰推理模型：生产库提权特批、高危权限审批、跨系统安全审计


@dataclass(frozen=True)
class ModelProfile:
    tier: ModelTier
    model_name: str
    price_per_1k_input: float   # 元 / 1K 输入 Token
    price_per_1k_output: float  # 元 / 1K 输出 Token
    max_output_tokens: int


MODEL_CATALOG: Dict[ModelTier, ModelProfile] = {
    ModelTier.LITE: ModelProfile(
        tier=ModelTier.LITE,
        model_name="qwen3.7-flash",
        price_per_1k_input=0.0002,
        price_per_1k_output=0.0006,
        max_output_tokens=512,
    ),
    ModelTier.STANDARD: ModelProfile(
        tier=ModelTier.STANDARD,
        model_name="qwen3.7-plus",
        price_per_1k_input=0.0008,
        price_per_1k_output=0.0020,
        max_output_tokens=1024,
    ),
    ModelTier.PREMIUM: ModelProfile(
        tier=ModelTier.PREMIUM,
        model_name="qwen3.8-max",
        price_per_1k_input=0.0024,
        price_per_1k_output=0.0096,
        max_output_tokens=2048,
    ),
}

TIER_ORDER: List[ModelTier] = [ModelTier.LITE, ModelTier.STANDARD, ModelTier.PREMIUM]
SYSTEM_PROMPT_RESERVE = 600  # 系统提示词与检索上下文的 Token 预留


def estimate_tokens(text: str) -> int:
    """粗估 Token：中文字符约 1 字 ≈ 1 Token，非中文字符约 4 个字符 ≈ 1 Token"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return cjk + math.ceil((len(text) - cjk) / 4)


def estimate_cost(model: ModelProfile, input_tokens: int, output_tokens: int) -> float:
    """计算模型调用费用（元）"""
    cost = (input_tokens / 1000.0 * model.price_per_1k_input) + (
        output_tokens / 1000.0 * model.price_per_1k_output
    )
    return round(cost, 6)


# ==============================================================================
# 2. Model Router：基于 IT 运维规则打分的复杂度与风险路由
# ==============================================================================

@dataclass
class RouteDecision:
    tier: ModelTier
    min_tier: ModelTier          # 降级下限：高危请求绝不允许降到本地/轻量小模型
    score: int
    reasons: List[str] = field(default_factory=list)
    risk_hits: List[str] = field(default_factory=list)
    hop_hits: List[str] = field(default_factory=list)


class ModelRouter:
    """按 IT 服务台场景特征进行规则打分"""

    # 高风险/高权限关键词 (+4分，锁定 min_tier=STANDARD)
    HIGH_RISK_KEYWORDS = [
        "特批", "审批", "提权", "核心生产库", "生产环境", "root权限",
        "驳回", "高危", "违规", "越权", "安全审计", "DROP", "ALTER", "删库", "数据库特批"
    ]

    # 多跳推理/复杂排查/架构对比关键词 (+2分)
    MULTI_HOP_KEYWORDS = [
        "对比", "根因", "排查", "链路", "拓扑", "跨网段", "汇总",
        "为什么", "依据", "分析", "架构", "方案", "区别", "同时"
    ]

    def route(self, query: str, history_turns: int = 0) -> RouteDecision:
        score = 0
        reasons: List[str] = []

        tokens = estimate_tokens(query)
        if tokens > 120:
            score += 2
            reasons.append(f"长输入({tokens} Token) +2")

        risk_hits = [k for k in self.HIGH_RISK_KEYWORDS if k in query]
        if risk_hits:
            score += 4
            reasons.append(f"命中高危生产/特批审计语义 {risk_hits} +4")

        hop_hits = [k for k in self.MULTI_HOP_KEYWORDS if k in query]
        if hop_hits:
            score += 2
            reasons.append(f"命中多跳架构/排查信号 {hop_hits} +2")

        if history_turns >= 5:
            score += 1
            reasons.append(f"长对话上下文({history_turns} 轮) +1")

        if not reasons:
            reasons.append("标准 IT FAQ 问法，无升级信号")

        if score >= 4:
            tier = ModelTier.PREMIUM
        elif score >= 2:
            tier = ModelTier.STANDARD
        else:
            tier = ModelTier.LITE

        # 核心防线：命中高危财务/权限特批语义，禁止降级到 LITE
        min_tier = ModelTier.STANDARD if risk_hits else ModelTier.LITE
        return RouteDecision(
            tier=tier,
            min_tier=min_tier,
            score=score,
            reasons=reasons,
            risk_hits=risk_hits,
            hop_hits=hop_hits,
        )


# ==============================================================================
# 3. Token 预算管理器：三级额度与“预扣 -> 结算 -> 归还”两阶段记账
# ==============================================================================

class BudgetExceeded(Exception):
    def __init__(self, scope: str, detail: str, is_circuit_breaker: bool = False):
        super().__init__(f"[{scope}] {detail}")
        self.scope = scope
        self.detail = detail
        self.is_circuit_breaker = is_circuit_breaker


@dataclass
class BudgetAccount:
    limit: int
    used: int = 0
    reserved: int = 0

    @property
    def available(self) -> int:
        return max(0, self.limit - self.used - self.reserved)


class TokenBudgetManager:
    """进程内线程安全预算管理器（支持实时模拟调参）"""

    def __init__(
        self,
        per_request_cap: int = 4000,
        user_daily_limit: int = 20000,
        dept_monthly_limit: int = 500000,
    ):
        self.per_request_cap = per_request_cap
        self.user_daily_limit = user_daily_limit
        self.dept_monthly_limit = dept_monthly_limit
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
        """两阶段预扣：所有层级均充足方可放行，任一层级不足立即拒绝"""
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
        """结算：释放预扣，按实际模型使用量入账"""
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
        """异常归还：请求失败时全额撤销预扣"""
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
        """获取当前账户实时快照"""
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

    def set_budget_simulation(self, user_id: str, dept_id: str, daily_available: int) -> None:
        """演示专用：一键调整用户今日可用预算，便于立即演示降档与 429 熔断"""
        with self._lock:
            day = time.strftime("%Y%m%d")
            key = f"user:{user_id}:{day}"
            acc = self._accounts.setdefault(key, BudgetAccount(self.user_daily_limit))
            acc.reserved = 0
            if daily_available <= 0:
                acc.used = acc.limit
            else:
                acc.used = max(0, acc.limit - daily_available)

    def reset_budget(self, user_id: str, dept_id: str) -> None:
        """重置账户额度"""
        with self._lock:
            for key, limit in self._scopes(user_id, dept_id):
                acc = self._accounts.setdefault(key, BudgetAccount(limit))
                acc.used = 0
                acc.reserved = 0


# ==============================================================================
# 4. 成本总控器：路由 -> 预扣 -> 逐级降档 -> 触底 429 熔断
# ==============================================================================

@dataclass
class CostPlan:
    request_id: str
    model: ModelProfile
    routed_tier: ModelTier
    min_tier: ModelTier
    estimated_tokens: int
    degraded: bool
    reasons: List[str]
    score: int


class CostGovernor:
    """串联路由判决与预算管控两道闸门"""

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
    ) -> CostPlan:
        decision = self.router.route(query, history_turns)
        input_tokens = estimate_tokens(query) + SYSTEM_PROMPT_RESERVE

        hi = TIER_ORDER.index(decision.tier)
        lo = TIER_ORDER.index(decision.min_tier)
        last_error: Optional[BudgetExceeded] = None

        # 从路由裁决档位逐级向下尝试预扣，但绝不低于 min_tier
        for idx in range(hi, lo - 1, -1):
            model = MODEL_CATALOG[TIER_ORDER[idx]]
            estimated = input_tokens + model.max_output_tokens
            try:
                self.budget.reserve(request_id, user_id, dept_id, estimated)
                reasons = list(decision.reasons)
                is_degraded = (idx != hi)
                if is_degraded:
                    reasons.append(
                        f"⚠️ 预算预扣不足触发自动降档：{decision.tier.value} → {model.tier.value}"
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
                )
            except BudgetExceeded as exc:
                last_error = exc

        # 若降到 min_tier 依然无法满足预算要求
        if decision.min_tier != ModelTier.LITE:
            raise BudgetExceeded(
                scope=last_error.scope if last_error else "budget",
                detail=(
                    f"【安全熔断 429】当前请求涉及高危生产特批（min_tier 强制锁定为 "
                    f"{decision.min_tier.value}），预算已不足且严禁降级至本地轻量小模型；"
                    f"请求已自动熔断拦截，请联系平台管理员或转人工运维审核。"
                ),
                is_circuit_breaker=True,
            )
        raise last_error or BudgetExceeded("unknown", "预算不足且降级失败")


# ==============================================================================
# 5. 本地 CLI 自检测试
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("🛠️ Day 29 IT Service Desk 场景：Model Router 动态路由与预算熔断自检")
    print("=" * 80)

    # 初始化总控器，将日预算设置为 4500 以测试降档与熔断
    budget_mgr = TokenBudgetManager(user_daily_limit=4500)
    governor = CostGovernor(ModelRouter(), budget_mgr)

    test_cases = [
        ("公司访客 WiFi 密码是多少？如何配置？", 0, "LITE 极低成本"),
        ("对比公司内网直连与异地 SSL-VPN 接入方案的链路延迟、安全性与配置差异", 0, "STANDARD 多跳对比"),
        ("申请核心生产库 MySQL 生产环境 DROP/ALTER 表结构特批提权，工单号 IT-8802", 0, "PREMIUM 生产高危特批"),
        ("申请核心生产库 MySQL 生产环境 DROP/ALTER 表结构特批提权，工单号 IT-8802", 0, "触发降档测试"),
        ("申请核心生产库 MySQL 生产环境 DROP/ALTER 表结构特批提权，工单号 IT-8802", 0, "触底 429 熔断测试"),
    ]

    for i, (q, turns, desc) in enumerate(test_cases, 1):
        rid = f"test-req-{i:03d}"
        print(f"\n[{rid}] 测试用例：{desc}")
        print(f"提问: {q}")
        try:
            plan = governor.plan(rid, q, user_id="U-TECH-01", dept_id="DEPT-OPS", history_turns=turns)
            # 模拟模型输出消耗
            actual_in = estimate_tokens(q) + 300
            actual_out = plan.model.max_output_tokens // 2
            governor.budget.settle(rid, actual_in + actual_out)
            cost = estimate_cost(plan.model, actual_in, actual_out)
            flag = "⬇️ 触发降档" if plan.degraded else "✅ 原档直出"
            print(f"  ➔ 路由档位: {plan.routed_tier.value:8} | 实际模型: {plan.model.model_name} | {flag}")
            print(f"  ➔ 裁决依据: {'; '.join(plan.reasons)}")
            print(f"  ➔ 预扣: {plan.estimated_tokens} Token | 实耗: {actual_in + actual_out} Token | 估费: ¥{cost}")
        except BudgetExceeded as exc:
            print(f"  ➔ ⛔ 触发 HTTP 429 预算熔断拦截: {exc}")

    print("\n" + "-" * 60)
    for scope, info in governor.budget.snapshot("U-TECH-01", "DEPT-OPS").items():
        print(f"• 账户 {scope:24}: 已用 {info['used']:>5} / 上限 {info['limit']:>6} | 剩余 {info['available']}")
    print("=" * 80)
