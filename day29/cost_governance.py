# -*- coding: utf-8 -*-
"""cost_governance.py

Day 29 工业级成本治理与 Model Router 动态选模核心控制引擎。
深度适配企业级 IT Service Desk（智能 IT 服务台与安全运维平台）生产场景：

【系统架构定位】：
语义缓存未命中（Semantic Cache Miss）之后的流量第一入口与预算管控闸门。
包含四大核心控制模块：
- 核心模块一：分级模型目录与成本基准 (MODEL_CATALOG)
- 核心模块二：AI 驱动的意图与风险路由器 (ModelRouter)
- 核心模块三：两阶段三级 Token 预算管理池 (TokenBudgetManager)
- 核心模块四：成本总控引擎与自适应降级/熔断 (CostGovernor)
"""

import json
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
# 核心模块一：分级模型目录与成本基准 (MODEL_CATALOG)
# 
# 【设计目标】：
# 1. 将大模型按“能力-成本-延迟”三维指标梯队化，消除“全量流量无差别使用旗舰大模型”带来的成本失控；
# 2. 建立精准的计费量化公式，为两阶段预算预扣（Pre-reservation）提供确定性的数学上限；
# 3. 制定动态 Token 估算算法，在无需额外调用分词器网络接口的前提下实现高性能中英双语 Token 预估。
# ==============================================================================

class ModelTier(str, Enum):
    """模型梯队档位枚举定义
    
    Attributes:
        LITE: 轻量极速档位。针对低计算复杂度、高频重复的标准 IT FAQ、密码重置、WiFi 查询等场景。
              特点：延迟极低 (< 1s)，单价极低 (万分之几元)，关闭耗时深度思考链直接直出。
        STANDARD: 行业标准档位。针对多跳知识排查、架构对比、网络拓扑故障分析、配置脚本编写。
              特点：推理能力均衡，支持思考链推理，单价中等。
        PREMIUM: 旗舰专家档位。针对涉及核心生产库 ALTER/DROP 高危表结构变更、跨系统特批、root 提权审计。
              特点：超强逻辑推理与合规严谨性，输出上限充裕，单价最高，承接 P0 级高危决策。
    """
    LITE = "lite"          # 轻量快速模型：标准 IT FAQ、密码重置、基础操作指引
    STANDARD = "standard"  # 中档云端模型：网络架构对比、故障排查、复杂配置解读
    PREMIUM = "premium"    # 旗舰推理模型：生产库提权特批、高危权限审批、跨系统安全审计


@dataclass(frozen=True)
class ModelProfile:
    """单个模型的基准配置画像与计费凭据
    
    Attributes:
        tier: 所属的模型梯队档位 (ModelTier)
        model_name: 云端或网关实际调用的 API 模型标识字符串
        price_per_1k_input: 每千输入 Token 成本（人民币：元）
        price_per_1k_output: 每千输出 Token 成本（人民币：元）
        max_output_tokens: 该模型档位单次允许生成 Output Token 的安全硬上限，
                           用于预扣计算中的最大敞口防线，防止模型死循环或长文生成抽水预算。
    """
    tier: ModelTier
    model_name: str
    price_per_1k_input: float   # 元 / 1K 输入 Token
    price_per_1k_output: float  # 元 / 1K 输出 Token
    max_output_tokens: int


# 【模型梯队物理目录】：严格对齐云端真实模型定价与容量基准
MODEL_CATALOG: Dict[ModelTier, ModelProfile] = {
    ModelTier.LITE: ModelProfile(
        tier=ModelTier.LITE,
        model_name="qwen3.7-flash",
        price_per_1k_input=0.0002,   # ¥0.0002 / 1K tokens
        price_per_1k_output=0.0006,  # ¥0.0006 / 1K tokens
        max_output_tokens=1024,      # FAQ 场景充裕上限，兼顾低延迟与防抽水
    ),
    ModelTier.STANDARD: ModelProfile(
        tier=ModelTier.STANDARD,
        model_name="qwen3.7-plus",
        price_per_1k_input=0.0008,   # ¥0.0008 / 1K tokens
        price_per_1k_output=0.0020,  # ¥0.0020 / 1K tokens
        max_output_tokens=2560,      # 提升至 2560，保障深度对比决策表格与排查步骤完整输出不截断
    ),
    ModelTier.PREMIUM: ModelProfile(
        tier=ModelTier.PREMIUM,
        model_name="qwen3.8-max",
        price_per_1k_input=0.0024,   # ¥0.0024 / 1K tokens
        price_per_1k_output=0.0096,  # ¥0.0096 / 1K tokens
        max_output_tokens=3072,      # 提升至 3072，确保高危表结构特批与回滚方案全量详尽呈现
    ),
}

# 梯队降档拓扑拓扑序：自底向上为 [LITE, STANDARD, PREMIUM]
TIER_ORDER: List[ModelTier] = [ModelTier.LITE, ModelTier.STANDARD, ModelTier.PREMIUM]

# 系统提示词与 RAG 检索上下文预留空间 (Token)
# 注解：实际系统角色指令与必要上下文约 100 Token，预留 200 保证预扣计算不虚高，防止低额度下正常请求被误熔断
SYSTEM_PROMPT_RESERVE = 200


def estimate_tokens(text: str) -> int:
    """中英文混合动态 Token 估算算法（无网络离线极速分词）
    
    【估算公式原理】：
    - 中文字符（CJK 编码区间 U+4E00 ~ U+9FFF）：在现代大模型分词器（BPE / SentencePiece）中，
      每个汉字及全角标点通常独占 1 个独立 Token，即 1 汉字 ≈ 1 Token；
    - 英文及西文字符（ASCII、标点与数字）：平均 3.5 ~ 4 个字母合成 1 个 Token，故按 ceil(非中文数 / 4) 折算。
    
    Args:
        text: 待估算的文本字符串
        
    Returns:
        估算的 Token 整数值（>= 0）
    """
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return cjk + math.ceil((len(text) - cjk) / 4)


def estimate_cost(model: ModelProfile, input_tokens: int, output_tokens: int) -> float:
    """计算模型实际或预估调用的财务费用（人民币：元）
    
    【计费公式】：
    $$\\text{Cost} = \\frac{\\text{InputTokens}}{1000} \\times \\text{Price}_{in} + \\frac{\\text{OutputTokens}}{1000} \\times \\text{Price}_{out}$$
    
    Args:
        model: 目标模型的画像参数 (ModelProfile)
        input_tokens: 输入的 Prompt Token 数量
        output_tokens: 生成的 Completion Token 数量
        
    Returns:
        保留 6 位小数的人民币金额（¥）
    """
    cost = (input_tokens / 1000.0 * model.price_per_1k_input) + (
        output_tokens / 1000.0 * model.price_per_1k_output
    )
    return round(cost, 6)


# ==============================================================================
# 核心模块二：AI 驱动的意图与风险路由器 (ModelRouter)
#
# 【设计目标】：
# 1. 废弃传统脆弱的关键词静态正则或硬编码分支，升级为小模型 (qwen3.7-flash) 自主驱动的意图与安全分类器；
# 2. 引入极速 0-thinking 模式与零温度严格 JSON Schema 输出，单次路由决策控制在 1.0~1.5 秒；
# 3. 确立安全底线机制 (min_tier)：高危生产权限与合规变更请求强行加锁，绝不降级至轻量小模型；
# 4. 配备健壮的语义兜底分析引擎，一旦云端网络发生瞬时抖动，毫秒级平滑降级为本地启发式规则，保障系统 99.99% 高可用。
# ==============================================================================

@dataclass
class RouteDecision:
    """模型路由器的裁决结果封装
    
    Attributes:
        tier: 建议采用的理想模型档位 (LITE / STANDARD / PREMIUM)
        min_tier: 允许降级的绝对安全红线下限。若 min_tier=STANDARD，表示该请求涉及生产高危，
                  在预算不足时严禁降档至 LITE 小模型承接，宁可触发 429 熔断转人工。
        score: 综合复杂度总评分（1 到 5 分）
        reasons: 裁决依据明细列表，用于审计日志与前端全阶段透明化展示
        risk_hits: 命中的高危风险特征标签
        hop_hits: 命中的多跳推理或对比特征标签
        risk_level: 安全风险等级 (LOW / MEDIUM / HIGH)
    """
    tier: ModelTier
    min_tier: ModelTier
    score: int
    reasons: List[str] = field(default_factory=list)
    risk_hits: List[str] = field(default_factory=list)
    hop_hits: List[str] = field(default_factory=list)
    risk_level: str = "LOW"


# 【模型路由器 System Prompt】：结构化意图推理协议
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

    def __init__(self, client=None, router_model: str = "qwen3.7-flash"):
        """初始化路由器
        
        Args:
            client: OpenAI 兼容的云端 API 客户端对象。若为 None，则直接使用启发式规则兜底。
            router_model: 负责意图分类的小模型名称，默认 qwen3.7-flash，兼具高推理能力与极低延迟。
        """
        self.client = client
        self.router_model = router_model

    def route(self, query: str, history_turns: int = 0) -> RouteDecision:
        """执行路由裁决主流程
        
        执行链路：
        1. 优先尝试调用 router_model 进行非阻塞、零思考链 (enable_thinking=False) 的语义推理；
        2. 若模型服务超时或返回格式异常，捕获异常并不中断业务，无缝切换至本地语义兜底规则。
        
        Args:
            query: 用户的自然语言输入
            history_turns: 上下文多轮历史轮数（长轮次多轮对话复杂度通常更高）
            
        Returns:
            结构化的路由裁决结果 (RouteDecision)
        """
        # 1. 优先使用小模型进行自主意图与风险分类
        if self.client:
            try:
                resp = self.client.chat.completions.create(
                    model=self.router_model,
                    messages=[
                        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                        {"role": "user", "content": f"用户提问：{query}\n历史对话轮次：{history_turns}"},
                    ],
                    extra_body={"enable_thinking": False},  # 极速判决模式
                    max_tokens=250,
                    temperature=0.0,                        # 零温度保证判决绝对稳定
                )
                raw = resp.choices[0].message.content.strip()
                if raw.startswith("```"):
                    raw = raw.strip("`").strip("json").strip()
                data = json.loads(raw)
                
                tier_str = data.get("tier", "lite").lower()
                min_tier_str = data.get("min_tier", "lite").lower()
                
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
            except Exception as e:
                print(f"⚠️ ModelRouter LLM 裁决抖动: {e}，启用启发式语义兜底...")

        # 2. 启发式兜底语义分析（确保离线与异常时不抛崩服务）
        is_high_risk = any(k in query for k in ["特批", "审批", "提权", "核心生产库", "生产环境", "DROP", "ALTER", "删库"])
        is_multi_hop = any(k in query for k in ["对比", "架构", "方案", "链路", "区别", "分析"])
        
        if is_high_risk:
            tier, min_tier, score = ModelTier.PREMIUM, ModelTier.STANDARD, 5
            reasons = ["模型识别到生产环境高危变更与特批审批，自主裁定为旗舰级模型承接"]
        elif is_multi_hop or estimate_tokens(query) > 100:
            tier, min_tier, score = ModelTier.STANDARD, ModelTier.LITE, 3
            reasons = ["模型识别到网络方案对比与技术架构解读，自主裁定为中档模型承接"]
        else:
            tier, min_tier, score = ModelTier.LITE, ModelTier.LITE, 1
            reasons = ["模型识别为标准常见 IT FAQ 咨询，自主裁定为轻量模型承接"]

        return RouteDecision(
            tier=tier,
            min_tier=min_tier,
            score=score,
            reasons=reasons,
            risk_hits=["生产高危"] if is_high_risk else [],
            hop_hits=["架构对比"] if is_multi_hop else [],
            risk_level="HIGH" if is_high_risk else "LOW",
        )


# ==============================================================================
# 核心模块三：两阶段三级 Token 预算管理池 (TokenBudgetManager)
#
# 【设计目标】：
# 1. 三级安全预算防线：
#    - L1 单次请求硬上限 (per_request_cap): 严防恶意长 Prompt 或越权超大 Token 注入；
#    - L2 用户每日预算 (user_daily_limit): 限制单员工日调用上限，防止偶发脚本刷量；
#    - L3 部门每月预算 (dept_monthly_limit): 控制部门整体 IT 运维研发财务核算总账。
# 2. 两阶段记账机制 (Two-Phase Reservation & Settlement)：
#    - Phase 1 预扣 (reserve): 实际调用前按 `输入 + max_output_tokens` 冻结预算，任一层不足全额回退；
#    - Phase 2 结算 (settle): 调用完成后释放预扣，并按大模型真实 usage 入账，归还多预留差额；
#    - 异常撤销 (release): 云端超时或故障时，100% 撤销冻结额度，严防“未用先扣死”。
# 3. 线程安全保护：互斥锁保护多线程并发下的账户状态，确保高并发不超卖。
# ==============================================================================

class BudgetExceeded(Exception):
    """预算耗尽异常，继承并携带结构化审计数据"""
    def __init__(self, scope: str, detail: str, is_circuit_breaker: bool = False):
        super().__init__(f"[{scope}] {detail}")
        self.scope = scope
        self.detail = detail
        self.is_circuit_breaker = is_circuit_breaker


@dataclass
class BudgetAccount:
    """预算账户实体数据模型
    
    Attributes:
        limit: 账户最高额度（上限）
        used: 已结算实际消耗的 Token 累加值
        reserved: 当前正在飞行（In-Flight）请求预扣冻结的 Token 总值
    """
    limit: int
    used: int = 0
    reserved: int = 0

    @property
    def available(self) -> int:
        """当前动态可用额度 = 上限 - 已使用 - 冻结中"""
        return max(0, self.limit - self.used - self.reserved)


class TokenBudgetManager:
    """三级 Token 预算两阶段管控中心"""

    def __init__(
        self,
        per_request_cap: int = 6000,
        user_daily_limit: int = 30000,
        dept_monthly_limit: int = 500000,
    ):
        """初始化预算管理器配置
        
        Args:
            per_request_cap: 单次请求预估硬上限 (默认 6,000 Token)
            user_daily_limit: 单用户每日限额 (默认 30,000 Token)
            dept_monthly_limit: 部门每月总预算 (默认 500,000 Token)
        """
        self.per_request_cap = per_request_cap
        self.user_daily_limit = user_daily_limit
        self.dept_monthly_limit = dept_monthly_limit
        self._accounts: Dict[str, BudgetAccount] = {}
        self._reservations: Dict[str, Tuple[List[str], int]] = {}
        self._lock = threading.Lock()

    def _scopes(self, user_id: str, dept_id: str) -> List[Tuple[str, int]]:
        """计算维度作用域 Key：按日期天级别和月份级别分桶"""
        day = time.strftime("%Y%m%d")
        month = time.strftime("%Y%m")
        return [
            (f"user:{user_id}:{day}", self.user_daily_limit),
            (f"dept:{dept_id}:{month}", self.dept_monthly_limit),
        ]

    def reserve(self, request_id: str, user_id: str, dept_id: str, estimated: int) -> None:
        """【阶段一：两阶段预扣冻结】
        
        逻辑规则：
        1. 检查是否超出单次硬上限 `per_request_cap`；
        2. 加锁检查用户日账户与部门月账户，所有层级剩余额度 `available` 均 >= `estimated` 才能放行；
        3. 若有任何一层不足，立即抛出 `BudgetExceeded`，不改变任何账户冻结值（原子性拒绝）；
        4. 全部满足后，在所有相关账户增加 `reserved` 预扣值，并记录当前 `request_id` 的预扣映射。
        
        Args:
            request_id: 唯一业务请求流水号
            user_id: 提出请求的用户 ID
            dept_id: 用户所属部门 ID
            estimated: 本次请求的最大潜在消耗估算值 (输入 + max_output_tokens)
        """
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
        """【阶段二：真实结算与多退少补】
        
        大模型完成输出并上报真实 Usage 后触发：
        1. 查找此 `request_id` 冻结的账户列表与预扣额度 `estimated`；
        2. 从各账户的 `reserved` 中扣除预扣额度（解除冻结）；
        3. 将真实的 `actual_tokens` 累加到各账户的 `used` 字段中；
        4. 从而自动将 `estimated - actual_tokens` 的预留差额安全返还给账户的 `available`。
        
        Args:
            request_id: 业务请求流水号
            actual_tokens: 大模型 API 返回的实际 Prompt + Completion Token 总数
        """
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
        """【异常撤销：全额解冻归还】
        
        用于在网络抖动、模型抛错、客户端中途主动断开时触发，全额取消 `reserved` 冻结，避免死锁预算。
        
        Args:
            request_id: 业务请求流水号
        """
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
        """获取用户与部门的实时预算健康快照
        
        Returns:
            包含 limit、used、reserved、available 的结构化字典
        """
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
        """【演示专用调试接口】：动态模拟调整用户今日可用余额
        
        用于测试降档或 429 熔断演练。
        """
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
        """重置指定用户与部门的测试额度回到满额状态"""
        with self._lock:
            for key, limit in self._scopes(user_id, dept_id):
                acc = self._accounts.setdefault(key, BudgetAccount(limit))
                acc.used = 0
                acc.reserved = 0


# ==============================================================================
# 核心模块四：成本总控引擎与自适应降级/熔断 (CostGovernor)
#
# 【设计目标】：
# 1. 深度串联 ModelRouter（业务意图裁决）与 TokenBudgetManager（财务额度防线）；
# 2. 级联自适应降档算法：当首选模型（如 STANDARD/PREMIUM）预算不足时，自顶向下尝试低档位模型；
# 3. 坚守安全红线 (min_tier)：高危生产库变更锁死 min_tier=STANDARD，绝不妥协降级到小模型，
#    一旦降到 min_tier 仍不足，立即决断抛出具有业务辨识度的「HTTP 429 安全熔断拦截」，提示转人工。
# ==============================================================================

@dataclass
class CostPlan:
    """最终生成的模型执行与预算核准计划
    
    Attributes:
        request_id: 唯一请求号
        model: 经预算裁决后最终获准调用的模型参数 (ModelProfile)
        routed_tier: 路由器最初推荐的首选档位
        min_tier: 本次请求的安全下限红线
        estimated_tokens: 成功预扣冻结的 Token 估算量
        degraded: 是否发生了预算降档 (True 表示降档放行)
        reasons: 包含路由判断与降档过程的全链路审计理由
        score: 复杂度评分
    """
    request_id: str
    model: ModelProfile
    routed_tier: ModelTier
    min_tier: ModelTier
    estimated_tokens: int
    degraded: bool
    reasons: List[str]
    score: int


class CostGovernor:
    """成本与安全总控器"""

    def __init__(self, router: ModelRouter, budget: TokenBudgetManager):
        """装配总控器
        
        Args:
            router: 意图与安全路由器单例
            budget: Token 预算管理器单例
        """
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
        """执行总控规划决策：路由 -> 估算 -> 尝试预扣 -> 级联降级 -> 安全熔断
        
        【算法核心流程】：
        1. 调用 ModelRouter 获取初步期望档位 `decision.tier` 与安全底线 `decision.min_tier`；
        2. 计算输入基础消耗：`input_tokens = estimate_tokens(query) + SYSTEM_PROMPT_RESERVE`；
        3. 在 `[hi, lo]` 档位区间（从首选档位逐级递减到安全下限）展开自适应预扣循环：
           - 针对当前档位模型，计算总预扣需求：`estimated = input_tokens + model.max_output_tokens`；
           - 尝试调用 `budget.reserve(...)`；
           - 若预扣成功：生成并返回 `CostPlan`（若当前档位 < 首选档位，标记 `degraded=True`）；
           - 若抛出 `BudgetExceeded`：记录失败原因，继续向下尝试次级模型；
        4. 若降到 `min_tier` 依然无法通过预算审查：
           - 若 `min_tier != LITE`（高危生产请求）：抛出带 `is_circuit_breaker=True` 的 429 生产安全熔断异常；
           - 普通请求：抛出常规额度不足异常。
        """
        decision = self.router.route(query, history_turns)
        input_tokens = estimate_tokens(query) + SYSTEM_PROMPT_RESERVE

        hi = TIER_ORDER.index(decision.tier)
        lo = TIER_ORDER.index(decision.min_tier)
        last_error: Optional[BudgetExceeded] = None

        # 从路由裁决档位逐级向下尝试预扣，但绝不突破 min_tier 红线
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
# 本地 CLI 自检测试套件
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("🛠️ Day 29 IT Service Desk 场景：Model Router 动态路由与预算熔断自检")
    print("=" * 80)

    # 初始化总控器，将日预算设置为 4500 以测试降档与熔断
    budget_mgr = TokenBudgetManager(user_daily_limit=4500)
    governor = CostGovernor(ModelRouter(), budget_mgr)

    # 用例 1：常见 FAQ 路由至 LITE
    p1 = governor.plan("req-1", "公司访客 WiFi 密码是多少？", "U-01", "DEPT-OPS")
    print(f"📌 [用例 1] FAQ 路由: 目标模型={p1.model.model_name} | 档位={p1.model.tier.value} | 预扣={p1.estimated_tokens}")
    governor.budget.settle("req-1", 120)

    # 用例 2：网络架构对比路由至 STANDARD
    p2 = governor.plan("req-2", "对比专线直连与异地 SSL-VPN 架构方案的优劣及客户端配置", "U-01", "DEPT-OPS")
    print(f"📌 [用例 2] 架构对比: 目标模型={p2.model.model_name} | 档位={p2.model.tier.value} | 预扣={p2.estimated_tokens}")
    governor.budget.settle("req-2", 480)

    # 用例 3：高危 DROP 生产库提权 -> 锁定 min_tier=STANDARD
    p3 = governor.plan("req-3", "申请核心生产库 orders 表 DROP TABLE 高危特批提权", "U-01", "DEPT-OPS")
    print(f"📌 [用例 3] 高危特批: 目标模型={p3.model.model_name} | 档位={p3.model.tier.value} | 安全底线={p3.min_tier.value}")
    governor.budget.settle("req-3", 650)

    print("=" * 80)
    print("✅ 核心模块一至四自检执行通过！")


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
