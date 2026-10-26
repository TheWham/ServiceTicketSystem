# -*- coding: utf-8 -*-
"""意图路由：模型主判 + 规则兜底 + 仲裁。

与 `workflow_demo/nodes.route_intent` 同构 —— 仓库里已有两处先例都是这个形态
（Python 侧 `route_intent` + rules.rule_route；Java 侧 `SemanticRequestClassifier`
+ `KeywordRequestClassifier`），本模块照做，不另创一套。

规则先跑有两个用途：无模型时的路由依据，以及模型判完之后的对照基线。

**唯一的偏离**在 `resolve_analytics_intent` 的第 5 条（分歧且规则未命中 → 澄清）。
理由见该函数的 docstring：`workflow_demo` 的四个意图是同一条链路的平行分支，判错
只是分支选错；而这里的 `NOT_ANALYTICS` 意味着**跨服务边界**交给既有 RAG 链路，
误判代价不对称。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from . import taxonomy as tx
from .contract import (INTENT_ANALYTICS, INTENT_CLARIFY, INTENT_NOT_ANALYTICS,
                       AnalyticsState)
from .model_client import ModelClient, ModelUnavailable

# ---- 规则词表 ----
# 强信号：出现其一基本就是分析型提问，单独即可定性。
_STRONG_TERMS = (
    "共性根因", "共性问题", "采购建议", "巡检建议", "全面总结", "综合分析",
    "占比", "分布情况", "趋势分析", "规律", "盘点", "横向对比",
)
# 弱信号：单独出现不算数（"帮我总结一下这个报错"不是分析题），需多个或叠加语境。
_WEAK_TERMS = (
    "总结", "归纳", "汇总", "统计", "分布", "趋势", "根因", "分析", "建议", "展望",
)
# 时间范围词
_WINDOW_TERMS = ("本季度", "这个季度", "这季度", "上季度", "上一季度", "上个季度",
                 "本月", "这个月", "上个月", "上月", "今年", "本年", "当季")
_WINDOW_RE = re.compile(r"(?:近|最近|过去|前)\s*\d+\s*(?:天|日|周|个?星期|个?月)|"
                        r"\bq[1-4]\b|20\d{2}\s*年")
# 集合词：明确要求跨越多条记录，是分析型提问最本质的特征。
_COLLECTIVE_TERMS = ("全部", "所有", "各", "整体", "跨", "数十", "大批", "汇总",
                     "一共", "总共", "都有哪些", "哪些类型")
_COLLECTIVE_RE = re.compile(r"全部|所有|整体|跨\s*\d|数十|各大类")

# 规则判定阈值：达到即认为规则侧"命中"。
_RULE_THRESHOLD = 3
_STRONG_SCORE = 3
_WEAK_SCORE = 1
_CONTEXT_SCORE = 1


def rule_route(question: str, taxonomy: Optional[tx.Taxonomy] = None) -> Tuple[bool, str]:
    """规则侧判定："这是不是分析型提问"，附判定依据。

    返回 `(是否命中, 依据说明)`。依据会写进 findings 与 trace —— 规则判完不给理由，
    排查时只能靠猜。
    """
    q = question or ""
    lowered = q.lower()
    score = 0
    reasons: List[str] = []

    strong = [t for t in _STRONG_TERMS if t in q]
    if strong:
        score += _STRONG_SCORE * len(strong)
        reasons.append(f"强信号词 {strong[:3]}")

    weak = [t for t in _WEAK_TERMS if t in q]
    if weak:
        score += _WEAK_SCORE * len(weak)
        reasons.append(f"弱信号词 {weak[:3]}")

    has_window = any(t in q for t in _WINDOW_TERMS) or bool(_WINDOW_RE.search(q))
    if has_window:
        score += _CONTEXT_SCORE
        reasons.append("含时间范围")

    collective = [t for t in _COLLECTIVE_TERMS if t in q]
    if collective or _COLLECTIVE_RE.search(q):
        score += _CONTEXT_SCORE
        reasons.append("含集合范围词")

    domains = tx.resolve_domains(q, taxonomy)
    if domains:
        score += _CONTEXT_SCORE
        reasons.append(f"含子域限定 {[d.name for d in domains]}")

    hit = score >= _RULE_THRESHOLD
    detail = (f"得分 {score}（阈值 {_RULE_THRESHOLD}）：" + "；".join(reasons)) if reasons \
        else f"得分 0（阈值 {_RULE_THRESHOLD}）：未命中任何分析型信号"
    return hit, detail


# ---- 模型判定 ----

_ROUTER_PROMPT = """你是企业 IT 服务台的请求分类器。判断用户的问题属于哪一类，**只输出标签本身**，不要任何解释或标点：

ANALYTICS        —— 需要对**多条工单做跨记录的宏观归纳**（如"总结本季度网络设备的共性根因""统计各类故障占比""给出下季度备件采购建议"）。特征是要求"把很多条记录合起来看"。
NOT_ANALYTICS    —— 其他一切：询问单个故障怎么排查、怎么操作、查自己的工单进度、要求建单等。

判断依据只有一条：**用户要的是"很多条记录合起来看"的结论，还是"这一件事怎么办"的答案。**
提到"总结/分析"但对象是单个报错（如"帮我总结一下这个报错"）属于 NOT_ANALYTICS。

用户问题：{question}
标签："""


def normalize_model_intent(raw: str) -> Optional[str]:
    """把模型输出的自由文本收敛成二选一枚举；无法收敛返回 None（交由规则兜底）。

    这是「模型 → 链路」的收窄口：模型只被允许产出两个标签之一，收敛失败就退回
    规则结果，**绝不让自由文本流进 state.intent**。
    """
    text = (raw or "").strip().upper()
    if not text:
        return None
    # 先查"不是"——避免 "NOT_ANALYTICS" 里含 "ANALYTICS" 被误判为 ANALYTICS
    if "NOT_ANALYTICS" in text or "NOT ANALYTICS" in text:
        return INTENT_NOT_ANALYTICS
    if "ANALYTICS" in text:
        return INTENT_ANALYTICS
    # 容忍模型输出中文标签或序号（与 workflow_demo/rules.normalize_model_intent 同款容错）
    if any(t in text for t in ("非分析", "不是分析", "不分析", "其他")):
        return INTENT_NOT_ANALYTICS
    if any(t in text for t in ("分析型", "宏观归纳", "聚合", "统计归纳")):
        return INTENT_ANALYTICS
    if re.fullmatch(r"\s*2\s*", text):
        return INTENT_NOT_ANALYTICS
    if re.fullmatch(r"\s*1\s*", text):
        return INTENT_ANALYTICS
    return None


def classify_with_model(model: ModelClient, question: str,
                        trace_id: Optional[str] = None) -> Tuple[Optional[str], str, Dict[str, Any]]:
    """调模型做二分类。返回 `(意图或 None, 说明, token 记录)`。"""
    if not model.available:
        return None, "模型未配置，跳过模型判定", {"tokens_source": "none"}
    prompt = _ROUTER_PROMPT.format(question=question)
    try:
        reply = model.complete([{"role": "user", "content": prompt}],
                               max_tokens=16, trace_id=trace_id)
    except ModelUnavailable as e:
        return None, f"模型调用失败，改用规则判定：{e}", {"tokens_source": "none"}
    intent = normalize_model_intent(reply.content)
    note = f"模型原始输出：{reply.content.strip()[:40]!r}" if intent \
        else f"模型输出无法收敛到枚举（{reply.content.strip()[:40]!r}），改用规则判定"
    return intent, note, {"tokens_in": reply.tokens_in, "tokens_out": reply.tokens_out,
                          "tokens_source": reply.tokens_source}


# ---- 仲裁 ----

def resolve_analytics_intent(model_intent: Optional[str], rule_hit: bool) -> Tuple[str, str]:
    """仲裁模型判定与规则判定。前 4 条与 `workflow_demo/nodes.resolve_intent` 完全同构。

    | # | 情形 | 结果 |
    |---|---|---|
    | 1 | 安全闸命中           | 拒答，**模型无翻案权**（在调用前处理，见 nodes） |
    | 2 | 模型不可用 / 收敛失败 | 规则兜底 |
    | 3 | 双方一致             | 采信 |
    | 4 | 分歧且规则命中        | 采信模型 |
    | 5 | **分歧且规则未命中**  | **澄清** ← 唯一偏离 |

    第 5 条为什么偏离：`workflow_demo` 的四个意图是同一条链路的平行分支，判错只是
    分支选错；而这里的 `NOT_ANALYTICS` 意味着**跨服务边界**交给既有 RAG 链路，
    误判代价不对称 ——

      · 漏判（真分析题 → NOT_ANALYTICS）：走 RAG 捞 3 张卡给个平庸答案，**不危险**；
      · 误判（普通问题 → ANALYTICS）：用户问"我 VPN 连不上怎么办"，系统回一份
        季度工单分布统计，**答非所问**。

    所以分歧且规则没背书时不直接进链路，回问一句 —— 对齐 `workflow_demo/nodes.py`
    「信息不足不是违规，正解是把问题问清楚」。
    """
    if model_intent is None:
        if rule_hit:
            return INTENT_ANALYTICS, "模型不可用或无法收敛，采用规则判定（命中分析型信号）"
        return INTENT_NOT_ANALYTICS, "模型不可用或无法收敛，采用规则判定（未命中分析型信号）"

    model_hit = model_intent == INTENT_ANALYTICS
    if model_hit == rule_hit:
        return (INTENT_ANALYTICS if model_hit else INTENT_NOT_ANALYTICS), \
               "模型与规则判定一致"

    if rule_hit and not model_hit:
        # 分歧，但规则有依据 → 采信模型（同 resolve_intent）
        return INTENT_NOT_ANALYTICS, \
               "模型判为非分析、规则判为分析：采信模型（与 resolve_intent 同构）"

    # 模型判为分析、规则未命中 → 不直接进链路，先澄清
    return INTENT_CLARIFY, \
           "模型判为分析但规则未命中依据：跨服务边界误判代价高，先澄清再决定"

CLARIFY_TEXT = ("你是想让我把这批工单**合起来做统计归纳**（比如看本季度各类故障的"
                "分布、共性问题）吗？如果是，回复「是的」并告诉我时间范围与设备范围；"
                "如果你是想问某个具体故障怎么处理，我直接按常规排查答复你。")