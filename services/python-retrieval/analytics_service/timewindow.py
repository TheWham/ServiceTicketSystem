# -*- coding: utf-8 -*-
"""时间窗解析（"本季度" / "近 90 天" → 具体日期区间）。

两条分工，先说清楚免得后来人把边界挪掉：

1. **模型只给语义槽位，日期算术一律在本模块完成。** 提问里的时间说法由 Node A 的
   模型抽成 `kind/anchor/year/quarter/amount/unit` 这类槽位（见 classifier.Slots），
   `start/end` 由这里算。理由是模型算错季度边界**不会报错**，只会安静地给一个错误
   的分母 —— 这是全链路里最难查的一类失败。唯一的例外是 `EXPLICIT_RANGE`（用户原话
   给了日期），那里模型复述两个 ISO 日期，由本模块校验格式、次序与量程。
2. **正则解析保留为兜底与对照**（`parse_window`）：模型不可用、超时、槽位不可信时
   用它；两者都跑时还能做交叉核对（见 `resolve_window` 的冲突判定）。

正则侧的三个必须守住的点：

1. **季度按自然日历切，不用 `service_calendar`** —— 后者是"SLA 计时用的工作时间
   日历"（每天 9:00-18:00、跳过午休与周末），拿它算季度边界必然出错；
2. **无时间词时不默认全量** —— 落入 `DEFAULT_WINDOW_DAYS` 并在回答首句明示口径，
   绝不能把"本季度"悄悄当成"全部时间"，那会让用户以为看到的是季度数据；
3. **只输出 ISO 日期**，由 Java 侧解析；解析失败即弃用该槽位，不让非法值进 SQL。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

# 未指定时间范围时的默认窗口。给一个明确区间 + 在回答里声明口径，
# 比默认全量诚实 —— 全量会让"最近三个月"与"三年"给出同一个数字。
DEFAULT_WINDOW_DAYS = 90

SOURCE_PARSED = "规则解析"
SOURCE_DEFAULT = "默认最近90天"
SOURCE_MODEL = "模型抽取"


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    label: str
    source: str

    @property
    def start_iso(self) -> str:
        return self.start.isoformat()

    @property
    def end_iso(self) -> str:
        return self.end.isoformat()

    def as_dict(self) -> dict:
        return {"label": self.label, "start": self.start_iso, "end": self.end_iso,
                "source": self.source}

    def days(self) -> int:
        return (self.end - self.start).days + 1


def _today(now: Optional[datetime]) -> date:
    ref = now or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    return ref.astimezone(timezone.utc).date()


def quarter_of(d: date) -> int:
    """自然季度序号 1~4。**按自然日历切**，与 SLA 的 `service_calendar` 无关。"""
    return (d.month - 1) // 3 + 1


def quarter_bounds(year: int, quarter: int) -> tuple:
    """自然季度的首末日（闭区间）。

    末日统一用"下季首日减一天"（12 月特判）而不是硬编码各月天数 —— 闰年与月份
    长度的边界只在这里写一次，不散到调用方。
    """
    start_month = (quarter - 1) * 3 + 1
    start = date(year, start_month, 1)
    end_month = start_month + 2
    if end_month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, end_month + 1, 1) - timedelta(days=1)
    return start, end


def month_bounds(year: int, month: int) -> tuple:
    """自然月的首末日（闭区间）。末日算法同 `quarter_bounds`：下月首日减一天。"""
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def parse_window(text: str, now: Optional[datetime] = None) -> Window:
    """解析时间范围。识别不了就返回默认窗口 —— 调用方据 `source` 决定是否声明口径。

    识别不了的**不报错**：分析型提问常带各种口语时间词，为每个没见过的说法抛异常
    会让整条链路变得脆。但必须通过 `source` 让上游知道"这是默认值不是用户意图"。
    """
    raw = (text or "")
    t = raw.lower()
    today = _today(now)
    q = quarter_of(today)

    # ---- 季度 ----
    if "上一季度" in raw or "上个季度" in raw or "上季度" in raw:
        py, pq = (today.year - 1, 4) if q == 1 else (today.year, q - 1)
        s, e = quarter_bounds(py, pq)
        return Window(s, e, f"{py} Q{pq}", SOURCE_PARSED)

    m_q = re.search(r"\bq([1-4])\b", t)
    if m_q:
        qn = int(m_q.group(1))
        yr = today.year
        m_y = re.search(r"(20\d{2})", t)
        if m_y:
            yr = int(m_y.group(1))
        s, e = quarter_bounds(yr, qn)
        return Window(s, e, f"{yr} Q{qn}", SOURCE_PARSED)

    if "本季度" in raw or "这个季度" in raw or "这季度" in raw or "当季" in raw:
        s, _ = quarter_bounds(today.year, q)
        return Window(s, today, f"{today.year} Q{q}（至今）", SOURCE_PARSED)

    # ---- 月份 ----
    if "上个月" in raw or "上月" in raw:
        py, pm = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        s, e = month_bounds(py, pm)
        return Window(s, e, f"{py}-{pm:02d}", SOURCE_PARSED)

    if "本月" in raw or "这个月" in raw:
        s, _ = month_bounds(today.year, today.month)
        return Window(s, today, f"{today.year}-{today.month:02d}（至今）", SOURCE_PARSED)

    # ---- 相对天数 ----
    # 区间**闭区间且含今天**：`近 N 天` = 含今天往前数 N 天，故起点是 today-(N-1)。
    # 写成 today-N 会多算一天 —— 这个偏差不报错、只让口径悄悄变，最难查。
    m_days = re.search(r"(?:近|最近|过去|前)\s*(\d+)\s*(?:天|日)", raw)
    if m_days:
        n = max(1, min(int(m_days.group(1)), 3650))
        return Window(today - timedelta(days=n - 1), today, f"近 {n} 天", SOURCE_PARSED)

    m_weeks = re.search(r"(?:近|最近|过去|前)\s*(\d+)\s*(?:周|个?星期)", raw)
    if m_weeks:
        n = max(1, min(int(m_weeks.group(1)), 520))
        return Window(today - timedelta(days=n * 7 - 1), today, f"近 {n} 周", SOURCE_PARSED)

    m_months = re.search(r"(?:近|最近|过去|前)\s*(\d+)\s*个?月", raw)
    if m_months:
        n = max(1, min(int(m_months.group(1)), 120))
        # 按月数 × 30 天折算（近似值，口径在 label 里如实写作「近 N 个月」）。
        # 刻意不做日历月推演：提问里的"近 3 个月"本就是口语，硬套日历边界反而
        # 会与用户预期不符。
        return Window(today - timedelta(days=n * 30), today, f"近 {n} 个月", SOURCE_PARSED)

    # ---- 年月（必须是本分支先于「年份」，否则会被它截胡）----
    # "2026年10月" 里含 "2026年"，而年份分支排在后面就会把它整年吞掉 —— 那是**错答案**
    # 而不只是口径粗：用户问的是一个月的工单，系统给了一整年的统计。
    # 月份越界（如 "2026年13月"）不在此处报错，落回下方年份分支按"2026 年"处理。
    m_ym = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月", raw)
    if m_ym:
        yr, mo = int(m_ym.group(1)), int(m_ym.group(2))
        if 1 <= mo <= 12:
            s, e = month_bounds(yr, mo)
            return Window(s, e, f"{yr}-{mo:02d}", SOURCE_PARSED)

    # ---- 年份 ----
    if "今年" in raw or "本年" in raw:
        return Window(date(today.year, 1, 1), today, f"{today.year} 年（至今）", SOURCE_PARSED)

    m_year = re.search(r"(20\d{2})\s*年", raw)
    if m_year:
        yr = int(m_year.group(1))
        return Window(date(yr, 1, 1), date(yr, 12, 31), f"{yr} 年", SOURCE_PARSED)

    # ---- 默认 ----
    return Window(today - timedelta(days=DEFAULT_WINDOW_DAYS - 1), today,
                  f"近 {DEFAULT_WINDOW_DAYS} 天", SOURCE_DEFAULT)


def is_explicit(text: str, now: Optional[datetime] = None) -> bool:
    """提问里是否显式给了时间范围（用于决定要不要回问澄清）。"""
    return parse_window(text, now).source == SOURCE_PARSED


# ==================================================================== 槽位 → 日期
#
# 以下全部由代码完成日期算术。模型给的是 kind/anchor/quarter/amount 这类语义槽位，
# 到这里才落成 start/end —— 分工的理由见模块头注释。

_VALID_KINDS = {"QUARTER", "MONTH", "YEAR", "RELATIVE", "SINCE", "EXPLICIT_RANGE"}
_VALID_ANCHORS = {"CURRENT", "PREVIOUS", "LAST_YEAR_SAME", "ABSOLUTE"}
_VALID_UNITS = {"DAY", "WEEK", "MONTH"}

# 相对窗口的上限，与 parse_window 的各分支一致 —— 两处限幅不一样就会让"同一个提问
# 走模型还是走正则拿到不同的区间"，而这不是用户能看见的差异。
_MAX_DAYS, _MAX_WEEKS, _MAX_MONTHS = 3650, 520, 120

# 显式日期区间的合理量程。下限挡住"1970-01-01"这类明显误填，上限给未来留一点余地
# （提问里可能出现"下个月"这类边界），跨度上限挡住"2000 年到今天"这种把量程撑爆的值。
_MIN_EXPLICIT_DATE = date(2015, 1, 1)
_MAX_SPAN_DAYS = 3650
_FUTURE_SLACK_DAYS = 31


@dataclass(frozen=True)
class WindowResolution:
    """时间口径的最终结论，以及**它是怎么定下来的**。

    `note` / `rejected` / `conflict` / `model_missed` 都要进 trace 或 findings：
    "这题的统计区间是谁定的"必须可解释 —— 它是结论能不能用的前提，藏在服务端日志
    里等于没披露。
    """

    window: Window
    note: str = ""
    # 模型与规则**都从字面命中**却给出不同区间
    conflict: bool = False
    # 模型给了槽位但不可用的原因；空串表示没有槽位被弃用
    rejected: str = ""
    # 模型说"没有时间词"，而正则从字面命中了
    model_missed: bool = False

    @property
    def from_model(self) -> bool:
        return self.window.source == SOURCE_MODEL


def _as_int(value: Any) -> Optional[int]:
    """把槽位里的数字字段收敛成 int；模型常把 3 写成 "3" 或 "第3季度"。"""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    m = re.search(r"\d+", str(value))
    return int(m.group(0)) if m else None


def _iso(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except (TypeError, ValueError):
        return None


def _evidence_ok(question: str, raw: Any) -> bool:
    """`rawText` 必须是提问的字面子串。

    与 Node E「数字必须可溯源」同构的一道闸：模型编一个用户根本没说过的"最近30天"
    会被当场拦下。它**管不了**"模型看见了但理解错"，那种情况由正则对照与口径行
    披露兜住 —— 一道闸只解决一类问题，不要指望它包打一切。
    """
    text = str(raw or "").strip()
    if not text:
        return False
    return text.lower() in (question or "").lower()


def _anchor_of(slot: Dict[str, Any]) -> str:
    """归一 anchor。缺省时按"有没有给出具体序号/年份"推断，而不是一律当 CURRENT。"""
    raw = str(slot.get("anchor") or "").strip().upper().replace("-", "_")
    if raw in _VALID_ANCHORS:
        return raw
    if any(_as_int(slot.get(k)) is not None for k in ("year", "quarter", "month")):
        return "ABSOLUTE"
    return "CURRENT"


def _latest_started_quarter(today: date, quarter: int) -> int:
    """`ABSOLUTE` 但没写年份时，取**最近一个已经开始的**该季度的年份。

    一月里问"第三季度"，人指的是**去年** Q3 —— 用 `today.year` 会答成十个月之后
    的事，而那个区间里一张工单都不会有（统计结果为空，却看不出哪里错了）。
    """
    return today.year if quarter <= quarter_of(today) else today.year - 1


def _latest_started_month(today: date, month: int) -> int:
    return today.year if month <= today.month else today.year - 1


def _prev_quarter(today: date) -> Tuple[int, int]:
    q = quarter_of(today)
    return (today.year - 1, 4) if q == 1 else (today.year, q - 1)


def _one_period(kind: str, anchor: str, slot: Dict[str, Any],
                today: date) -> Tuple[Optional[Window], str]:
    """整周期（QUARTER / MONTH / YEAR）的槽位 → 窗口。"""
    year = _as_int(slot.get("year"))
    quarter = _as_int(slot.get("quarter"))
    month = _as_int(slot.get("month"))

    if kind == "QUARTER":
        # 序号按 anchor 解：CURRENT/PREVIOUS/LAST_YEAR_SAME 的季号由"今天"推出来，
        # 模型不必也不该给（"本季度"里没有任何序号，硬要它填只会逼出编造）。
        # 只有 ABSOLUTE 才真的需要模型给出 quarter。
        if anchor == "PREVIOUS":
            py, pq = _prev_quarter(today)
            s, e = quarter_bounds(py, pq)
            return Window(s, e, f"{py} Q{pq}", SOURCE_MODEL), ""
        if anchor == "LAST_YEAR_SAME":
            q = quarter if quarter is not None else quarter_of(today)
            if not 1 <= q <= 4:
                return None, f"quarter 不是 1~4：{q}"
            yr = today.year - 1
            s, e = quarter_bounds(yr, q)
            return Window(s, e, f"{yr} Q{q}", SOURCE_MODEL), ""
        if anchor == "CURRENT":
            q = quarter if quarter is not None else quarter_of(today)
            if not 1 <= q <= 4:
                return None, f"quarter 不是 1~4：{q}"
            s, _ = quarter_bounds(today.year, q)
            return Window(s, today, f"{today.year} Q{q}（至今）", SOURCE_MODEL), ""
        if quarter is None or not 1 <= quarter <= 4:
            return None, "kind=QUARTER 且 anchor=ABSOLUTE 时必须给出 1~4 的 quarter"
        yr = year if year is not None else _latest_started_quarter(today, quarter)
        s, e = quarter_bounds(yr, quarter)
        return Window(s, e, f"{yr} Q{quarter}", SOURCE_MODEL), ""

    if kind == "MONTH":
        if anchor == "PREVIOUS":
            py, pm = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
            s, e = month_bounds(py, pm)
            return Window(s, e, f"{py}-{pm:02d}", SOURCE_MODEL), ""
        if anchor == "LAST_YEAR_SAME":
            mo = month if month is not None else today.month
            if not 1 <= mo <= 12:
                return None, f"month 不是 1~12：{mo}"
            s, e = month_bounds(today.year - 1, mo)
            return Window(s, e, f"{today.year - 1}-{mo:02d}", SOURCE_MODEL), ""
        if anchor == "CURRENT":
            mo = month if month is not None else today.month
            if not 1 <= mo <= 12:
                return None, f"month 不是 1~12：{mo}"
            s, _ = month_bounds(today.year, mo)
            return Window(s, today, f"{today.year}-{mo:02d}（至今）", SOURCE_MODEL), ""
        if month is None or not 1 <= month <= 12:
            return None, "kind=MONTH 且 anchor=ABSOLUTE 时必须给出 1~12 的 month"
        yr = year if year is not None else _latest_started_month(today, month)
        s, e = month_bounds(yr, month)
        return Window(s, e, f"{yr}-{month:02d}", SOURCE_MODEL), ""

    # kind == "YEAR"
    if anchor == "CURRENT":
        return Window(date(today.year, 1, 1), today, f"{today.year} 年（至今）", SOURCE_MODEL), ""
    yr = today.year - 1 if anchor in ("PREVIOUS", "LAST_YEAR_SAME") else \
        (year if year is not None else today.year)
    return Window(date(yr, 1, 1), date(yr, 12, 31), f"{yr} 年", SOURCE_MODEL), ""


def _relative(slot: Dict[str, Any], today: date) -> Tuple[Optional[Window], str]:
    """近 N 天/周/月。日期算法与 `parse_window` 对应分支**逐日一致**。

    `近 N 天` 是闭区间且含今天，起点是 `today-(N-1)`；写成 `today-N` 会多算一天，
    这个偏差不报错、只让口径悄悄变，最难查。周与月的折算方式也照抄正则分支。
    """
    amount = _as_int(slot.get("amount"))
    unit = str(slot.get("unit") or "").strip().upper()
    if amount is None or amount < 1:
        return None, "kind=RELATIVE 但 amount 缺失或小于 1"
    if unit not in _VALID_UNITS:
        return None, f"kind=RELATIVE 但 unit 不是 {'/'.join(sorted(_VALID_UNITS))}"
    if unit == "DAY":
        n = min(amount, _MAX_DAYS)
        return Window(today - timedelta(days=n - 1), today, f"近 {n} 天", SOURCE_MODEL), ""
    if unit == "WEEK":
        n = min(amount, _MAX_WEEKS)
        return Window(today - timedelta(days=n * 7 - 1), today, f"近 {n} 周", SOURCE_MODEL), ""
    n = min(amount, _MAX_MONTHS)
    return Window(today - timedelta(days=n * 30), today, f"近 {n} 个月", SOURCE_MODEL), ""


def _since(slot: Dict[str, Any], today: date) -> Tuple[Optional[Window], str]:
    """「自 X 以来」：起点固定，终点是今天（半开区间的右端取当前）。

    正则接不住这类说法，而它很常见。**不能**当成整月处理 —— "自9月以来"若算成
    9月1日~9月30日，10 月的数据会被整个漏掉，而统计结果看上去完全正常。
    """
    year = _as_int(slot.get("year"))
    month = _as_int(slot.get("month"))
    if month is None:
        yr = year if year is not None else today.year
        return Window(date(yr, 1, 1), today, f"{yr} 年（至今）", SOURCE_MODEL), ""
    if not 1 <= month <= 12:
        return None, "kind=SINCE 但 month 不是 1~12"
    yr = year if year is not None else _latest_started_month(today, month)
    return Window(date(yr, month, 1), today, f"{yr}年{month}月至今", SOURCE_MODEL), ""


def _explicit(slot: Dict[str, Any], today: date) -> Tuple[Optional[Window], str]:
    """显式日期区间：模型复述用户写下的两个日期，这里只做校验。

    格式、次序、量程三道都要过。放宽任何一道，一个被模型记错的日期就会变成一个
    看上去完全正常的错误区间 —— 日期区间错了不会报错，只会安静地改变分母。
    """
    start = _iso(slot.get("startDate"))
    end = _iso(slot.get("endDate"))
    if start is None or end is None:
        return None, "kind=EXPLICIT_RANGE 缺少合法的 startDate/endDate（格式 YYYY-MM-DD）"
    if start > end:
        return None, f"起止日期次序颠倒（{start} > {end}）"
    if start < _MIN_EXPLICIT_DATE:
        return None, f"起始日期 {start} 早于 {_MIN_EXPLICIT_DATE}"
    if end > today + timedelta(days=_FUTURE_SLACK_DAYS):
        return None, f"结束日期 {end} 超出合理范围"
    if (end - start).days > _MAX_SPAN_DAYS:
        return None, f"区间跨度超过 {_MAX_SPAN_DAYS} 天"
    return Window(start, end, f"{start.isoformat()} ~ {end.isoformat()}", SOURCE_MODEL), ""


def window_from_slots(slot: Optional[Dict[str, Any]], question: str = "",
                      now: Optional[datetime] = None) -> Tuple[Optional[Window], str]:
    """把模型给出的时间槽位落成 `Window`。返回 `(窗口或 None, 不可用的原因)`。

    原因只用于说明与留痕 —— 调用方一律退回正则，不因槽位有问题而中断链路。
    """
    if not isinstance(slot, dict) or not slot:
        return None, ""
    kind = str(slot.get("kind") or "").strip().upper().replace("-", "_")
    if not kind:
        return None, "模型未给出 timeWindow.kind"
    if kind == "NONE":
        # 明确表示"提问里没有时间表达"，是合法结论而非错误 —— 不记 rejected，
        # 由调用方按"模型说没有 / 正则有没有字面命中"另行裁决。
        return None, ""
    if kind not in _VALID_KINDS:
        return None, f"未知的时间类型 {kind}"
    if not _evidence_ok(question, slot.get("rawText")):
        return None, f"rawText「{str(slot.get('rawText') or '').strip()}」未在提问中原样出现，槽位不可信"

    today = _today(now)
    if kind == "QUARTER" or kind == "MONTH" or kind == "YEAR":
        return _one_period(kind, _anchor_of(slot), slot, today)
    if kind == "RELATIVE":
        return _relative(slot, today)
    if kind == "SINCE":
        return _since(slot, today)
    return _explicit(slot, today)


def _said_none(slot: Optional[Dict[str, Any]]) -> bool:
    return isinstance(slot, dict) and \
        str(slot.get("kind") or "").strip().upper() == "NONE"


def resolve_window(question: str, slot: Optional[Dict[str, Any]] = None,
                   now: Optional[datetime] = None) -> WindowResolution:
    """定下这次统计的时间口径：模型槽位优先，正则兜底与对照。

    **冲突判定必须带前置条件**：`parse_window` 在正则没命中时返回的是
    `SOURCE_DEFAULT`（默认 90 天）而**不是 None**。若不加区分地拿它和模型窗口比区间，
    每一条**靠模型立功救回来**的提问（"第三季度""自9月以来"）都会误报冲突 ——
    恰好把最该看见的那批信号淹没在噪声里。所以只有**两边都从字面命中**才谈得上冲突。
    """
    rule = parse_window(question, now)
    model, rejected = window_from_slots(slot, question, now)

    if model is not None:
        if rule.source == SOURCE_PARSED and (rule.start, rule.end) != (model.start, model.end):
            note = (f"时间口径由模型抽取：{model.label}（{model.start_iso} ~ {model.end_iso}）；"
                    f"规则解析为 {rule.label}（{rule.start_iso} ~ {rule.end_iso}）——"
                    f"两者均从提问字面命中，采用模型")
            return WindowResolution(model, note, conflict=True)
        return WindowResolution(model, f"时间口径由模型抽取：{model.label}"
                                       f"（{model.start_iso} ~ {model.end_iso}）")

    # ---- 模型没给出可用窗口 ----
    if slot is None:
        # 压根没跑模型（未配置，或 ANALYTICS_MODEL_ROUTING=0）。这是配置选择，
        # 不是异常，不记任何"槽位被弃用"的痕迹。
        return WindowResolution(rule, f"时间口径来自{rule.source}：{rule.label}")

    if _said_none(slot):
        if rule.source == SOURCE_PARSED:
            # 提问里明明写着"本季度"，模型却说没有时间词 —— 字面命中是硬证据，采信规则。
            return WindowResolution(
                rule, f"模型未抽出时间，但提问字面命中规则解析：{rule.label}", model_missed=True)
        return WindowResolution(rule, f"提问未指明时间范围，按「{rule.label}」统计")

    return WindowResolution(rule, f"模型时间槽位不可用（{rejected}），改用规则：{rule.label}",
                            rejected=rejected)