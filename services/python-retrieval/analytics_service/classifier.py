# -*- coding: utf-8 -*-
"""请求理解：意图判定 + 槽位抽取（时间窗 / 范围限定 / 关注维度）。

与 `workflow_demo/nodes.route_intent` 同构 —— 仓库里已有两处先例都是这个形态
（Python 侧 `route_intent` + rules.rule_route；Java 侧 `SemanticRequestClassifier`
+ `KeywordRequestClassifier`），本模块照做，不另创一套。

规则先跑有两个用途：无模型时的路由依据，以及模型判完之后的对照基线。

**唯一的偏离**在 `resolve_analytics_intent` 的第 5 条（分歧且规则未命中 → 澄清）。
理由见该函数的 docstring：`workflow_demo` 的四个意图是同一条链路的平行分支，判错
只是分支选错；而这里的 `NOT_ANALYTICS` 意味着**跨服务边界**交给既有 RAG 链路，
误判代价不对称。

---- 槽位抽取（本次新增）----

模型这一次调用**同时**产出意图与槽位：时间窗、范围限定、关注维度。三者在改造前
分别由 `timewindow.parse_window`、`taxonomy.resolve_domains`、`nodes._focus_axis`
的关键词表决定 —— 正则对"第三季度""自9月以来""这半年"这类说法无能为力，而它们
在真实提问里很常见。

但**模型只给语义槽位，日期算术一律留在 `timewindow.py`**：模型算错季度边界不会
报错，只会安静地给一个错误的分母，这正是本仓库反复防的那类失败。所以模型输出的是
`kind/anchor/quarter/amount`，`Window.start/end` 仍由代码算。

槽位的数据结构与解析放在本模块而不是 `contract.py`（`parse_narrative` 在那里）：
叙事 JSON 是**链路对外的输出契约**，由 engine/app 共用；槽位是 **Node A 内部的
理解产物**，schema 与这段提示词同生共死，改一处必改另一处，放一起才不会脱节。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import config as cfg
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

    与模型判定是**两条独立的证据**，本函数只负责给出规则这一条，不做任何仲裁：
    最终的采信/澄清由 `resolve_analytics_intent` 决定。这样拆开的好处是规则可以单独
    跑、单独测（见 `tests/test_classifier.py`），也不需要在规则里预判模型会说什么。

    打分规则（各项累加，`>= _RULE_THRESHOLD` 即命中）：

    | 信号               | 分值 | 说明                                        |
    |---|---|---|
    | 强信号词 `_STRONG_TERMS`   | +3/个 | 「共性根因」「采购建议」等，单独一个就够定案 |
    | 弱信号词 `_WEAK_TERMS`     | +1/个 | 「总结」「分析」等，单独出现不算数           |
    | 时间范围           | +1   | 「本季度」或 `近30天`/`Q3`/`2025年`          |
    | 集合范围词         | +1   | 「全部」「各」「跨」—— 要跨多条记录看         |
    | 子域限定           | +1   | 交由 `taxonomy.resolve_domains` 解析        |

    阈值取 3 的意思是「一个强信号，或三个弱信号，或弱信号叠加语境」。调这个词表和
    阈值就等于调规则的召回率，**改之前先跑 golden 集看回归**。

    聚合式打分而非关键词一票制，是因为分析型提问的本质特征不是某个词，而是
    **"要看很多条记录"这个诉求**——「总结一下这个报错」（单条）与「总结本季度所有
    报错」（跨条）用词几乎一样，只能靠集合词、时间范围这些语境项区分。`_WEAK_TERMS`
    里"分析/总结"被刻意降级为弱信号，就是为这个场景。

    `taxonomy` 不传时由 `resolve_domains` 自己兜底加载（见其 docstring）。传进来是
    为了避免整条链路每个节点都重新加载一遍词表。

    调用方是 `nodes.route_intent`（Node A 的第一步），在那里命中会直接
    `skip_model=True` —— 也就是**规则命中能替用户省一次模型调用**，这正是把规则放在
    模型前面的原因之一。相应地，规则误报的代价是「一个普通问题被直接当分析题处理」，
    所以宁可阈值偏保守，也别为了召回率把弱信号抬上去。
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

_ROUTE_PROMPT = """你是企业 IT 服务台的请求理解器。对下面这一个用户问题，同时完成两件事：判定意图，以及抽取参数槽位。

【一、判定意图】
ANALYTICS      —— 需要对**多条工单做跨记录的宏观归纳**（如"总结本季度网络设备的共性根因""统计各类故障占比""给出下季度备件采购建议"）。特征是要求"把很多条记录合起来看"。
NOT_ANALYTICS  —— 其他一切：询问单个故障怎么排查、怎么操作、查自己的工单进度、要求建单等。
判断依据只有一条：**用户要的是"很多条记录合起来看"的结论，还是"这一件事怎么办"的答案。**
提到"总结/分析"但对象是单个报错（如"帮我总结一下这个报错"）属于 NOT_ANALYTICS。

【二、抽取槽位】
⚠️ **意图判定与槽位抽取相互独立。** 无论你把意图判为 ANALYTICS 还是 NOT_ANALYTICS，
只要问题字面出现了时间、设备领域或关注维度，就必须如实填写 timeWindow、domains、focusAxis。
**严禁因为判成 NOT_ANALYTICS 就把它们一律填成 NONE 或空数组。**

timeWindow —— 问题里表示时间范围的那段话：
· rawText：**原样抄写**问题里那段文字，一个字都不要改（它是核对依据，写错整段作废）
· kind：
    QUARTER / MONTH / YEAR   整季度、整月、整年，要配 anchor
    RELATIVE                 近 N 天 / N 周 / N 个月，要配 amount 与 unit
    SINCE                    某个起点"以来 / 起"，区间是起点到今天，要配 year（或 year+month）
    EXPLICIT_RANGE           问题里直接写了两个日期，要配 startDate 与 endDate
    NONE                     问题里根本没有时间表达
· anchor（只配 QUARTER / MONTH / YEAR）：
    CURRENT         本季度 / 本月 / 今年
    PREVIOUS        上一季度 / 上个月 / 去年
    LAST_YEAR_SAME  去年同期 / 去年这个季度
    ABSOLUTE        指明了具体序号或年份，如"第三季度""2026年10月""Q3"
· year / quarter / month：ABSOLUTE 时填；序号一律用阿拉伯数字（"第三季度" → quarter=3）；
  年份没写明就省略 year 字段，由系统按当前日期推断
· amount / unit：unit 取 DAY / WEEK / MONTH；"近两周" → amount=2, unit=WEEK
· startDate / endDate：**只有 EXPLICIT_RANGE 才填**，格式 YYYY-MM-DD

⛔ **不要自己计算任何具体日期。** 除 EXPLICIT_RANGE 外，startDate / endDate 一律不要出现 ——
   季度边界、月份天数由系统计算，你算错不会有任何提示。

domains —— 问题限定的设备范围，**只能从下面这份清单里原样挑选**，一个都不能自造：
{domains}
若问题同时涉及多个领域，拆成数组里的多个枚举项，形如 {domains_example}。
问题没有限定范围就留空数组 []。

focusAxis —— 问题最关注哪个维度，只能取这四个值之一：
SYMPTOM（故障现象 / 症状 / 表现）、DEVICE（设备 / 机型）、ROOT_CAUSE（根因 / 原因 / 故障成因）、NONE（没有明确侧重）

【输出】只输出一个 JSON 对象，不要代码块标记、不要解释、不要输出推理过程：
{{"intent": "ANALYTICS",
  "timeWindow": {{"kind": "QUARTER", "anchor": "CURRENT", "rawText": "本季度"}},
  "domains": [],
  "focusAxis": "ROOT_CAUSE"}}

用户问题：{question}
JSON："""

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


# focusAxis 的归一表：模型可能给出小写、连字符或中文维度名。
_FOCUS_ALIASES = {
    "SYMPTOM": "SYMPTOM", "SYMPTOMS": "SYMPTOM", "现象": "SYMPTOM", "症状": "SYMPTOM",
    "故障现象": "SYMPTOM", "故障现象分布": "SYMPTOM", "表现": "SYMPTOM",
    "DEVICE": "DEVICE", "DEVICES": "DEVICE", "设备": "DEVICE", "机型": "DEVICE",
    "设备分布": "DEVICE", "硬件类型": "DEVICE",
    "ROOT_CAUSE": "ROOT_CAUSE", "ROOTCAUSE": "ROOT_CAUSE", "ROOT CAUSE": "ROOT_CAUSE",
    "根因": "ROOT_CAUSE", "共性根因": "ROOT_CAUSE", "原因": "ROOT_CAUSE",
    "故障原因": "ROOT_CAUSE", "故障成因": "ROOT_CAUSE",
}


@dataclass
class Slots:
    """一次请求理解抽出的槽位。全部字段都可能为空 —— 模型漏抽是常态，不是异常。

    `time_window` 刻意保持 dict 而非 dataclass：它的字段随 `kind` 变化（RELATIVE
    用 amount/unit，EXPLICIT_RANGE 用 startDate/endDate），定成结构体只会多出一堆
    "这个 kind 下该字段有没有意义"的分支。真正的取值校验在 `timewindow` 里做，
    那里才知道每种 kind 需要什么。
    """

    time_window: Dict[str, Any] = field(default_factory=dict)
    domains: List[str] = field(default_factory=list)
    focus_axis: str = ""
    # 模型原始 JSON，留档用（trace 里能看见它到底答了什么）
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_time(self) -> bool:
        """模型是否真的给了一个时间槽位（`NONE` 与"没给"一视同仁）。"""
        kind = str(self.time_window.get("kind") or "").strip().upper()
        return bool(kind) and kind != "NONE"

    def brief(self) -> Dict[str, Any]:
        """进 trace 的摘要 —— 页面上要能一眼看到模型抽了什么。"""
        return {"timeWindow": self.time_window, "domains": self.domains,
                "focusAxis": self.focus_axis}


def _norm_focus(raw: Any) -> str:
    key = str(raw or "").strip().upper().replace("-", "_")
    if key in ("", "NONE", "NULL", "无"):
        return ""
    if key in _FOCUS_ALIASES:
        return _FOCUS_ALIASES[key]
    # 兜底：模型写了"ROOT_CAUSE 根因"这类带中文的串，按子串再收一次
    for alias, axis in _FOCUS_ALIASES.items():
        if alias in key:
            return axis
    return ""


def _norm_domains(raw: Any, taxonomy: Optional[tx.Taxonomy]) -> List[str]:
    """收敛模型给的子域名：只留词表里真实存在的名字，其余静默丢弃。

    丢弃而不是报错 —— 模型多写一个不存在的领域，后果只是范围限定少生效一项，
    退回全库统计；为它中断整条链路是本末倒置。真正的范围解析仍由
    `taxonomy.resolve_domain_names` 校验（名字 → Domain），这里只做归一与去重。
    """
    if not isinstance(raw, list):
        return []
    known = {d.name for d in (taxonomy.domains if taxonomy else ())}
    out: List[str] = []
    for item in raw:
        name = str(item or "").strip().strip("「」【】\"'")
        if not name:
            continue
        if known and name not in known:
            continue
        if name not in out:
            out.append(name)
    return out


def _strip_fence(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.strip()
    return text


def parse_route(content: str, taxonomy: Optional[tx.Taxonomy] = None
                ) -> Tuple[Optional[str], Optional[Slots]]:
    """解析路由调用的输出，返回 `(意图或 None, 槽位或 None)`。

    **两者独立解析，互不连坐**：模型把 intent 写成乱码但槽位抽对了，槽位照样可用
    （反之亦然）。合并成一个"要么全要要么全不要"的结果，会让一个字段的失误把
    另外三个字段一起废掉。

    两条容错路径：

      · 合法 JSON   —— 正常路径；
      · 裸标签      —— 只有短、且不含 `{` 的文本才当作裸意图标签收下。这既兼容
                       "只输出一个标签"的旧行为（测试里的假模型就是这么写的），
                       **又刻意不接受被截断的 JSON 片段** ——
                       `{"intent": "ANALYTICS"` 里含 `ANALYTICS`，按子串收下会把
                       一次失败的调用当成成功，而它连槽位都没抽完。
    """
    text = _strip_fence(content)
    if not text:
        return None, None

    payload: Any = None
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except ValueError:
            payload = None
    if not isinstance(payload, dict):
        if "{" not in text and len(text) <= 32:
            return normalize_model_intent(text), None
        return None, None

    intent = normalize_model_intent(str(payload.get("intent") or ""))

    win = payload.get("timeWindow") or payload.get("time_window") or {}
    slots = Slots(
        time_window=dict(win) if isinstance(win, dict) else {},
        domains=_norm_domains(payload.get("domains"), taxonomy),
        focus_axis=_norm_focus(payload.get("focusAxis") or payload.get("focus_axis")),
        raw=payload,
    )
    return intent, slots


def _domain_lines(names: Sequence[str]) -> str:
    return "\n".join(f"  · {n}" for n in names) if names else "  （词表当前没有可选的子域，一律留空数组）"


def _domain_example(domains: Sequence[Any]) -> str:
    """示例里的域名也取自词表 —— 写死的示例会在词表变动后变成错的示范。

    刻意挑一对**互不包含**的域。词表里既有组合域（`网络与打印设备`）又有它的子域
    （`打印设备`），顺手取前两个恰好命中这种包含关系，等于拿一个"两个都要写"的
    反面范例教模型 —— 代码虽然会去重，但示例本身不该是错的示范。
    """
    def key(d: Any) -> Tuple[frozenset, frozenset]:
        return frozenset(d.devices), frozenset(d.symptoms)

    picked: List[Any] = []
    for dom in domains:
        k = key(dom)
        if any(k <= key(o) or key(o) <= k for o in picked):
            continue
        picked.append(dom)
        if len(picked) == 2:
            break
    if len(picked) < 2:                       # 词表小到挑不出两个，退回前两个
        picked = list(domains[:2])
    return json.dumps([d.name for d in picked], ensure_ascii=False) if picked else "[]"


def route_with_model(model: ModelClient, question: str,
                     taxonomy: Optional[tx.Taxonomy] = None,
                     trace_id: Optional[str] = None
                     ) -> Tuple[Optional[str], Optional[Slots], str, Dict[str, Any]]:
    """一次调用同时拿到意图与槽位。返回 `(意图, 槽位, 说明, token 记录)`。

    失败一律返回 `(None, None, ...)` 而不是抛异常：调用方据此退回规则判定与正则
    解析，整条链路照走 —— 与 Node D 的降级口径一致。
    """
    if not model.available:
        return None, None, "模型未配置，跳过模型判定，改用规则与正则", {"tokens_source": "none"}
    domains = list(taxonomy.domains) if taxonomy else []
    prompt = _ROUTE_PROMPT.format(question=question,
                                  domains=_domain_lines([d.name for d in domains]),
                                  domains_example=_domain_example(domains))
    try:
        reply = model.complete([{"role": "user", "content": prompt}],
                               max_tokens=cfg.ROUTER_MAX_OUTPUT_TOKENS,
                               timeout=cfg.ROUTER_TIMEOUT, trace_id=trace_id)
    except ModelUnavailable as e:
        return None, None, f"模型调用失败，改用规则与正则：{e}", {"tokens_source": "none"}

    intent, slots = parse_route(reply.content, taxonomy)
    tokens = {"tokens_in": reply.tokens_in, "tokens_out": reply.tokens_out,
              "tokens_source": reply.tokens_source}
    head = reply.content.strip()[:60]
    notes = [f"模型原始输出：{head!r}" if intent else
             f"模型意图无法收敛到枚举（{head!r}）"]
    if reply.finish_reason == "length":
        notes.append("模型输出被 max_tokens 截断，槽位可能不完整")
    if slots is not None and slots.has_time:
        notes.append(f"抽出时间槽位 {slots.time_window.get('kind')}")
    return intent, slots, "；".join(notes), tokens


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