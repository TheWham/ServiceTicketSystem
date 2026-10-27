# -*- coding: utf-8 -*-
"""分析链路的契约层：状态对象 + 事实结构 + 模型输出解析。

两条与 workflow_demo 同源的纪律，在注释里写清楚免得后来人"优化"掉：

1. `AnalyticsFacts` 是**带外字段** —— 前端表格读它，不读模型写的 `answerText`。
   于是"模型编造一个假的 42%"在结构上不可能：它能改的只有措辞。
2. `parse_narrative` 拿不出正文时返回 `ok=False`，**绝不把原始文本当答复回传**。
   推理模型的输出被 max_tokens 截断后是半截 JSON，那是协议碎片，不是给员工看的话。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------- 意图与裁决常量

INTENT_ANALYTICS = "ANALYTICS"
INTENT_NOT_ANALYTICS = "NOT_ANALYTICS"
INTENT_CLARIFY = "CLARIFY"
INTENT_BLOCKED = "BLOCKED"

VERDICT_ANSWERED = "ANSWERED"
VERDICT_CLARIFY = "NEEDS_INFO"
VERDICT_REFUSED = "REFUSED"

REPLY_ANSWER = "ANSWER"
REPLY_CLARIFY = "CLARIFY"
REPLY_REFUSE = "REFUSE"

VERDICT_TO_REPLY_TYPE = {
    VERDICT_ANSWERED: REPLY_ANSWER,
    VERDICT_CLARIFY: REPLY_CLARIFY,
    VERDICT_REFUSED: REPLY_REFUSE,
}

# 拒答原因复用 Java 侧 AiRefusalReason 的枚举取值（docs/specs/02-ai-api-json-schema.md）
REFUSAL_NO_RELIABLE_KNOWLEDGE = "NO_RELIABLE_KNOWLEDGE"
REFUSAL_POLICY_BLOCKED = "POLICY_BLOCKED"
REFUSAL_MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
# 问题不在本链路能力范围内（判为非分析型）。与 NO_RELIABLE_KNOWLEDGE 刻意分开：
# 后者是"数据不足以支撑结论"（该引导转人工），这个是"问题根本不归这条链路管"
# （该引导去智能客服问）—— 两者的下一步动作相反，混用会把工程师引错方向。
REFUSAL_OUT_OF_SCOPE = "OUT_OF_SCOPE"

# 闸门 code
GATE_SMALL_SAMPLE = "SMALL_SAMPLE"
GATE_SMALL_UNIVERSE = "SMALL_UNIVERSE"
GATE_LOW_COVERAGE = "LOW_COVERAGE"
GATE_ROOT_CAUSE_UNAVAILABLE = "ROOT_CAUSE_UNAVAILABLE"
GATE_DEFAULT_WINDOW = "DEFAULT_WINDOW"
GATE_TRUNCATED = "TRUNCATED"

# 建议来源：区分「代码按固定系数算出的」（数字口径可复核）与
# 「模型在统计事实上归纳的」（方向，每条带依据标签）。
SOURCE_RULE = "rule"
SOURCE_MODEL = "model"

SEVERITY_BLOCK = "BLOCK"
SEVERITY_WARN = "WARN"
SEVERITY_INFO = "INFO"

# 降级原因：要能区分「没调模型」「调了但异常」「调了但输出不可用」，
# 否则排查时只看到一句"答复是模板"，猜不出哪一环出的问题。
DEGRADED_NO_MODEL = "MODEL_NOT_CONFIGURED"
DEGRADED_TRUNCATED = "MODEL_TRUNCATED"
DEGRADED_UNPARSABLE = "MODEL_OUTPUT_UNPARSABLE"
DEGRADED_CALL_FAILED = "MODEL_CALL_FAILED"


# ---------------------------------------------------------------- 数据结构

@dataclass
class TicketRow:
    """投影扫描返回的一行工单（已脱敏：无姓名、无联系方式）。"""

    ticket_id: str
    category_id: str
    title: str
    description: str
    created_at: str = ""
    solved_at: str = ""
    first_response_at: str = ""
    completed_at: str = ""
    resolution: str = ""      # ticket_resolution.solution；当前真实库为空

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TicketRow":
        def pick(*keys: str) -> str:
            for k in keys:
                v = d.get(k)
                if v is not None:
                    return str(v)
            return ""

        return TicketRow(
            ticket_id=pick("ticketId", "ticket_id"),
            category_id=pick("categoryId", "category_id"),
            title=pick("title"),
            description=pick("description"),
            created_at=pick("createdAt", "created_at"),
            solved_at=pick("solvedAt", "solved_at"),
            first_response_at=pick("firstResponseAt", "first_response_at"),
            completed_at=pick("completedAt", "completed_at"),
            resolution=pick("resolution", "solution"),
        )


@dataclass
class Entry:
    """一个维度上的一条分布项。

    `ratio` 与 `ratioOfAll` 是**两个不同分母**，都要给：
      - ratio      = count / denominator，分母是"参与该维度统计的工单数"；
      - ratioOfAll = count / universe.total，分母是"时间窗内全部工单数"。
    "打印机故障占 42%"的自然读法是前者，"占本季度全部工单 18%"是后者 ——
    口径不明是宏观归纳最常见的偷换，两个都给，模型只能引用不能选。
    """

    label: str
    count: int
    denominator: int
    universe_total: int
    sample_ticket_ids: List[str] = field(default_factory=list)
    below_threshold: bool = False
    evidence: str = ""

    @property
    def ratio(self) -> Optional[float]:
        if self.below_threshold or self.denominator <= 0:
            return None
        return round(self.count * 100.0 / self.denominator, 1)

    @property
    def ratio_of_all(self) -> Optional[float]:
        if self.below_threshold or self.universe_total <= 0:
            return None
        return round(self.count * 100.0 / self.universe_total, 1)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "count": self.count,
            "denominator": self.denominator,
            "ratio": self.ratio,
            "ratioOfAll": self.ratio_of_all,
            "sampleTicketIds": self.sample_ticket_ids,
            "belowThreshold": self.below_threshold,
            "evidence": self.evidence,
        }


@dataclass
class Dimension:
    """一个聚合维度（SYMPTOM / DEVICE / ROOT_CAUSE）及其分布条目。

    两个"没归入标签"的计数刻意分开，它们回答的是不同问题：

      · `other_count`   —— 设计意图是"该轴有值、但没命中任何标签"的工单数。
                           **当前实现里该值恒为 0**：`_best_hit` 对每个轴、每张单
                           最多只产出一个标签，所以 `labelled_count` 恰好等于各
                           标签计数之和（见 aggregate.build_facts）。字段保留是
                           为了将来支持单工单多标签时不必改契约。
      · `unmatched_count` —— 该轴**完全抽不出标签**的工单数。这是覆盖率披露的
                           原料：它偏大说明词表没覆盖到，而不是"这种事没发生"。

    页面上展示的是 `unmatched_count`（"未归入任何标签 N 单"）。
    """

    axis: str
    entries: List[Entry] = field(default_factory=list)
    other_count: int = 0
    unmatched_count: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "axis": self.axis,
            "entries": [e.as_dict() for e in self.entries],
            "otherCount": self.other_count,
            "unmatchedCount": self.unmatched_count,
        }


@dataclass
class Coverage:
    """标签覆盖率。

    刻意把两个总量分开报，否则子域生效时会读错口径：
      - `total`        ：**纳入统计**的工单数（子域生效时即子域内的数量）；
      - `windowTotal`  ：时间窗内非噪声工单总数（子域过滤**之前**）；
      - `excluded`     ：时间窗内被剔除的噪声单（同样是子域过滤之前的全窗口口径）。

    为什么必须分：`excluded` 统计的是整个时间窗的噪声，若与子域内的 `total` 放在
    一起不加区分，读者会以为"3 张里排除了 35 张"。
    """

    labelled: int = 0
    total: int = 0
    window_total: int = 0
    excluded: Dict[str, int] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        return round(self.labelled * 100.0 / self.total, 1) if self.total else 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {"labelled": self.labelled, "total": self.total,
                "windowTotal": self.window_total, "ratio": self.ratio,
                "excluded": self.excluded, "examples": self.examples}


@dataclass
class Recommendation:
    """一条处置建议。

    `source` 区分**谁产出的**，这个区分是给读者看的，不只是内部标记：
      · `rule`  —— 由代码按配置里的备件系数算出，数字口径固定、可复核；
      · `model` —— 由模型在统计事实上归纳出的排查/巡检方向，带依据标签。
    界面上两类分组展示 —— 读者必须能分清哪部分是统计结论、哪部分是模型归纳。
    """

    kind: str                 # 备件 | 说明 | 排查 | 巡检 | ...
    text: str
    basis_label: str = ""
    basis_count: int = 0
    severity: str = SEVERITY_INFO
    source: str = SOURCE_RULE
    # 备件数量。之所以要结构化存一份而不是只写在 text 里：数字门禁的白名单是按
    # **结构化字段**建的，把它埋在文本里，代码自己算出的数量就会被自己的门禁
    # 当成"无法溯源的数字"剔掉（实测踩到过）。
    qty: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "text": self.text, "basisLabel": self.basis_label,
                "basisCount": self.basis_count, "severity": self.severity,
                "source": self.source, "qty": self.qty}


@dataclass
class Gate:
    """一条统计闸门：**"这次结论能不能用"的可解释判据**。

    `severity` 直接决定后果，不只是展示用的颜色：

      · `BLOCK` —— 结论不可用（如全库样本 < `MIN_UNIVERSE`），`aggregate_facts`
                   据此把 verdict 转成拒答，**不进叙事模型**；
      · `WARN`  —— 结论可用但受限（小样本、低覆盖率、默认时间窗），照常作答，
                   但必须披露、且压低置信度。

    闸门不是日志：它原样进 `facts`（前端逐条渲染）与提示词的「数据限制」段 ——
    **结论的适用范围必须跟着结论一起走**，而不是留在服务端日志里。
    """

    code: str
    severity: str
    message: str

    def as_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass
class AnalyticsFacts:
    """交给模型的全部内容（也是带外回传给前端的结构）。

    模型拿到的是**已算好的结论**：每个数字都由代码算出，条目集合由代码定死。
    """

    window: Dict[str, Any] = field(default_factory=dict)
    scope: Dict[str, Any] = field(default_factory=dict)
    universe: Dict[str, Any] = field(default_factory=dict)
    coverage: Coverage = field(default_factory=Coverage)
    dimensions: List[Dimension] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    gates: List[Gate] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "window": self.window,
            "scope": self.scope,
            "universe": self.universe,
            "coverage": self.coverage.as_dict(),
            "dimensions": [d.as_dict() for d in self.dimensions],
            "recommendations": [r.as_dict() for r in self.recommendations],
            "gates": [g.as_dict() for g in self.gates],
        }

    # ---- 供门禁比对的白名单 ----

    def allowed_numbers(self) -> set:
        """回答里允许出现的数字集合（百分数 + 计数）。

        门禁据此判断"这个数字是不是编的"。刻意把两个分母对应的占比都放进来，
        因为两者都是合法口径；但**未达阈值的条目不给 ratio**，所以它们也不会
        出现在白名单里 —— 模型自然写不出这些占比。
        """
        nums = set()
        for d in self.dimensions:
            for e in d.entries:
                nums.add(str(e.count))
                if e.ratio is not None:
                    nums.add(f"{e.ratio}")
                    nums.add(f"{e.ratio:.1f}")
                if e.ratio_of_all is not None:
                    nums.add(f"{e.ratio_of_all}")
                    nums.add(f"{e.ratio_of_all:.1f}")
        cov = self.coverage
        nums.update({str(cov.labelled), str(cov.total), str(cov.window_total),
                     f"{cov.ratio}", f"{cov.ratio:.1f}"})
        for k, v in (self.universe or {}).items():
            if isinstance(v, int):
                nums.add(str(v))
        for k, v in (self.scope or {}).items():
            if isinstance(v, int):
                nums.add(str(v))
        # 代码算出的备件数量属于"系统结论"，必须可被正文引用 ——
        # 否则模板里的「预备 X 个」会被自己的门禁剔掉。
        # 只收 rule 来源：model 来源的建议已由 verify_suggestions 校验过。
        for r in self.recommendations:
            if r.source == SOURCE_RULE and r.qty > 0:
                nums.add(str(r.qty))
        return nums

    def allowed_ticket_ids(self) -> set:
        """回答里允许出现的单号集合（`rules.verify_ticket_ids` 的白名单）。

        只收**进了分布条目**的单号 —— 它们才是"可下钻核验"的那些。刻意不收
        未命中任何标签的工单号：正文里出现一个没参与统计的单号，读者会以为
        它被算进了分母。
        """
        out = set()
        for d in self.dimensions:
            for e in d.entries:
                out.update(e.sample_ticket_ids)
        return out

    def has_block_gate(self) -> bool:
        return any(g.severity == SEVERITY_BLOCK for g in self.gates)

    def block_messages(self) -> List[str]:
        return [g.message for g in self.gates if g.severity == SEVERITY_BLOCK]


@dataclass
class RuleFinding:
    """一条判定依据，进 `state.findings` 供页面展示与事后排查。

    与 `Gate` 的分工：`Gate` 是**统计结论层面**的约束（进 facts，决定结论能不能用）；
    `RuleFinding` 是**链路执行层面**的记录（谁在什么条件下做了什么决定）。
    两者都会透出到页面，所以 `message` 要写成员工读得懂的话，不能只留内部术语。
    """

    code: str
    message: str
    severity: str = SEVERITY_INFO

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass
class AnalyticsState:
    """链路状态载体：节点只读写它，不在节点之间传参。"""

    question: str
    user_id: str = ""
    role: str = ""
    request_id: str = ""

    intent: str = ""
    rule_intent: str = ""
    model_intent: Optional[str] = None
    scope_domains: List[str] = field(default_factory=list)
    window: Optional[Any] = None
    # Node A 模型抽出的槽位（classifier.Slots）。类型用 Any 是为了不给 contract
    # 反向依赖 classifier —— 契约层不该认识"是谁抽的槽位"，只认识"有这么个槽位"。
    slots: Optional[Any] = None

    tickets: List[TicketRow] = field(default_factory=list)
    facts: Optional[AnalyticsFacts] = None

    verdict: str = ""
    reply_type: str = ""
    refusal_reason: Optional[str] = None
    answer_text: str = ""
    confidence: float = 0.0
    degraded_reason: Optional[str] = None

    findings: List[RuleFinding] = field(default_factory=list)
    # 节点异常降级记录：单点失败不得让整条链路变成"一个没有任何观测数据的 500"
    errors: List[str] = field(default_factory=list)

    def add_finding(self, code: str, message: str, severity: str = SEVERITY_INFO) -> None:
        self.findings.append(RuleFinding(code=code, message=message, severity=severity))


# ---------------------------------------------------------------- 模型输出解析

def parse_narrative(content: str) -> Tuple[str, List[str], List[Dict[str, Any]], bool]:
    """解析归因叙事的 JSON，返回 `(正文, 引用单号, 建议列表, 是否可用)`。

    **拿不出正文时 ok=False，绝不把原始文本当答复回传。** 推理模型的输出一旦被
    max_tokens 截断，回传的就是半截 JSON（`{"answerText": "…`）—— 那是模型内部
    协议的碎片，不是给员工看的分析结论。旧实现的 `return raw` 正是把这段残片
    直接送给了员工，页面上看着像乱码，链路里还记着 SUCCESS。

    建议字段是**软要求**：缺失或为空不算整体不可用 —— 统计结论不依赖它，
    退化成"只有系统算出的备件建议"仍然是一条可用的答复。
    """
    raw = (content or "").strip()
    if not raw:
        return "", [], [], False
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.strip()
    try:
        payload = json.loads(raw)
    except ValueError:
        return "", [], [], False
    if not isinstance(payload, dict):
        return "", [], [], False
    text = str(payload.get("answerText") or "").strip()
    if not text:
        # 结构对但正文为空：同样是"拿不出正文"，交给调用方降级，
        # 不要返回半成品字符串让下游去猜。
        return "", [], [], False
    cited = [v for v in (payload.get("citedTicketIds") or []) if isinstance(v, str)]
    suggestions = [s for s in (payload.get("recommendations") or []) if isinstance(s, dict)]
    return text, cited, suggestions, True


# ---------------------------------------------------------------- 入站请求模型

class AnalyticsRunRequest(BaseModel):
    """HTTP 入站模型。

    身份（`userId` / `role`）由 Java 侧从其认证上下文填入，**不接受前端直传** ——
    与 `agent_service` 的口径一致：跨人聚合的权限不能靠调用方自报。
    """

    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(default="", max_length=8000)
    user_id: str = Field(default="", alias="userId", max_length=64)
    role: str = Field(default="", max_length=32)
    request_id: str = Field(default="", alias="requestId", max_length=64)
    # 上游已判定的意图：非空且为 ANALYTICS 时，Node A 仍然调模型一次抽槽位，
    # 但意图直接采信上游、模型不得推翻（它这一趟不是二次分类）。
    upstream_intent: str = Field(default="", alias="upstreamIntent", max_length=32)