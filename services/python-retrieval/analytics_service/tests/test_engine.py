# -*- coding: utf-8 -*-
"""链路端到端的单测：短路出口、降级出口、门禁拦截。

重点是**短路**：如果非分析型请求还跑完聚合，用户问"我 VPN 连不上怎么办"就会收到
一份季度统计报告 —— 那正是整条链路要防的"答非所问"，所以必须逐条验证它真的没跑。
"""

from __future__ import annotations

import json
from typing import Optional

import pytest

from analytics_service import config as cfg
from analytics_service.contract import (DEGRADED_CALL_FAILED, DEGRADED_NO_MODEL, DEGRADED_TRUNCATED,
                                        DEGRADED_UNPARSABLE,
                                        INTENT_ANALYTICS, INTENT_BLOCKED, INTENT_CLARIFY,
                                        INTENT_NOT_ANALYTICS, TicketRow)
from analytics_service.data_source import FixtureDataSource
from analytics_service.engine import AnalyticsWorkflow
from analytics_service.model_client import ModelReply, NullModelClient

ANALYTICS_Q = "请根据全部网络与打印设备工单，总结本季度共性根因并给出备件采购建议"
PLAIN_Q = "我的 VPN 连不上怎么办"


class FakeModel:
    """可编排的假模型：给定回复内容，验证链路对模型输出的处理。

    链路有**两处**模型调用 —— Node A（意图判定 + 槽位抽取）与 Node D（归因叙事）——
    所以回复要能分开编排：`route` 供前者，`content` 供后者。不传 `route` 时两处
    共用一份，于是"只关心叙事"的老用例不必逐条改写。

    按提示词内容分流而不是按调用次序：次序会随短路路径变化（拒答/澄清时只有 A
    这一次），靠次序判断哪个调用是哪个会让用例随链路结构变动而碎掉。
    """

    def __init__(self, content: str = "", *, route: Optional[str] = None,
                 available: bool = True, finish_reason: str = "stop",
                 raises: bool = False):
        self._content = content
        self._route = content if route is None else route
        self._available = available
        self._finish = finish_reason
        self._raises = raises
        self.calls = 0

    @property
    def available(self) -> bool:
        return self._available

    def complete(self, messages, max_tokens=None, temperature=None, timeout=None,
                 trace_id=None):
        self.calls += 1
        if self._raises:
            from analytics_service.model_client import ModelUnavailable
            raise ModelUnavailable("模拟模型故障")
        prompt = messages[0].get("content") if messages else ""
        content = self._route if "请求理解器" in prompt else self._content
        return ModelReply(content, 10, 20, "reported", self._finish)


@pytest.fixture
def relaxed(monkeypatch):
    monkeypatch.setattr(cfg, "MIN_UNIVERSE", 5)
    monkeypatch.setattr(cfg, "MIN_DENOM", 3)
    monkeypatch.setattr(cfg, "MIN_LABEL_HITS", 2)


def _spans(result):
    return [s["spanName"] for s in result["trace"]["spans"]]


# ---------------------------------------------------------------- 完整链路

def test_完整分析链路跑通(ds, relaxed):
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    assert r["intent"] == INTENT_ANALYTICS
    assert r["verdict"] == "ANSWERED" and r["replyType"] == "ANSWER"
    assert _spans(r) == ["A.Intent_Router", "B.Projection_Scan", "C.Deterministic_Aggregate",
                         "D.Answer_Narrative", "E.Output_Gate"]
    assert r["analyticsFacts"] is not None
    assert r["window"]["label"].startswith("2026")
    assert r["scope"] == ["网络与打印设备"]


def test_facts以带外字段返回(ds, relaxed):
    """前端表格读 analyticsFacts，不读模型写的 answerText —— 结构上杜绝编造数字。"""
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    facts = r["analyticsFacts"]
    assert facts["universe"]["total"] == 11, "窗口内非噪声工单总数"
    assert facts["universe"]["scoped"] == 3, "子域限定后纳入统计的数量"
    # 两个总量刻意分开：excluded 是全窗口口径，total 是纳入统计口径
    assert facts["coverage"]["total"] == 3
    assert facts["coverage"]["windowTotal"] == 11
    assert any(d["axis"] == "SYMPTOM" for d in facts["dimensions"])


# ---------------------------------------------------------------- 短路出口

def test_非分析型请求熔断不跑聚合(ds, relaxed):
    """这是本条链路最重要的行为断言：普通问题不能被当成统计题作答。

    改造后是**熔断**（拒答 + 指路），不再返回 `NOT_ANALYTICS` 让上游回退知识问答 ——
    回退会让同一个 HTTP 入口按用户措辞切换成两套完全不同的链路，答复类型
    （统计结论 / 单卡排查步骤）跟着措辞漂移，前端也无从预期渲染哪一套结构。
    """
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(PLAIN_Q, role="ENGINEER")
    assert r["intent"] == INTENT_NOT_ANALYTICS, "判定结论仍要透出，误判率才统计得出来"
    assert r["verdict"] == "REFUSED"
    assert r["replyType"] == "REFUSE"
    assert r["refusalReason"] == "OUT_OF_SCOPE"
    assert r["analyticsFacts"] is None, "短路路径不应产生任何统计结果"
    assert "智能客服" in r["answerText"], "拒答要指路，不能只说不行"
    assert _spans(r) == ["A.Intent_Router", "A.Short_Circuit"]


def test_客服入口带上游定性时不熔断(ds, relaxed):
    """客服入口由 Java 分类器定性，Python 不翻案 —— 这里连线照跑。

    与看板入口的差别是**故意的**：看板是工程师主动进的统计工作台，判非分析就熔断
    并指路；客服入口若也熔断，用户问的本是能正常回答的问题（只是分类器判错了），
    却会收到一句"无法分析"。
    """
    model = FakeModel(content="", route=json.dumps({"intent": "NOT_ANALYTICS"},
                                                   ensure_ascii=False))
    r = AnalyticsWorkflow(ds=ds, model=model).run(
        PLAIN_Q, role="ENGINEER", upstream_intent=INTENT_ANALYTICS)
    assert r["intent"] == INTENT_ANALYTICS
    assert r["replyType"] == "ANSWER"
    assert r["refusalReason"] is None


def test_越权角色被拒答且不取数(ds, relaxed):
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(ANALYTICS_Q, role="EMPLOYEE")
    assert r["intent"] == INTENT_BLOCKED
    assert r["refusalReason"] == "POLICY_BLOCKED"
    assert "无权调用" in r["answerText"]
    assert r["analyticsFacts"] is None
    assert _spans(r) == ["A.Intent_Router", "A.Short_Circuit"]


def test_越权判定在模型调用之前(monkeypatch, ds, relaxed):
    """红线请求规则就能判死，先调模型再拒绝等于为一个注定被拦的请求付推理费。"""
    model = FakeModel(content="ANALYTICS")
    AnalyticsWorkflow(ds=ds, model=model).run(ANALYTICS_Q, role="EMPLOYEE")
    assert model.calls == 0


def test_模型判分析但规则未命中则澄清(ds, relaxed):
    model = FakeModel(content="ANALYTICS")
    r = AnalyticsWorkflow(ds=ds, model=model).run(
        "这季度设备都怎么了", role="ENGINEER")
    assert r["intent"] == INTENT_CLARIFY
    assert r["replyType"] == "CLARIFY"
    assert r["analyticsFacts"] is None
    assert model.calls == 1


def test_上游已指定意图时模型不推翻上游(ds, relaxed):
    """Java 侧已判过一次，Python 侧的模型没有翻案权 —— 它这一趟只抽槽位。

    "本季度工单的分布"刻意选在规则阈值之下，这样 pinned 只能来自上游，
    才真正测到上游那一条分支。
    """
    model = FakeModel(content="", route=json.dumps({"intent": "NOT_ANALYTICS"},
                                                   ensure_ascii=False))
    r = AnalyticsWorkflow(ds=ds, model=model).run(
        "本季度工单的分布", role="ENGINEER", upstream_intent=INTENT_ANALYTICS)
    assert r["intent"] == INTENT_ANALYTICS
    router = next(s for s in r["trace"]["spans"] if s["spanName"] == "A.Intent_Router")
    assert router["output"]["pinnedBy"] == "upstream"
    assert router["output"]["modelIntent"] == INTENT_NOT_ANALYTICS, "模型判了什么要留痕"


def test_规则命中时模型仍被调用但只抽槽位(ds, relaxed):
    """改造前规则命中会跳过模型，于是"模型主抽槽位"在最常见的那条路径上永不生效。

    现在模型仍然调用（要抽槽位），但意图直接采信规则、模型没有翻案权。
    """
    model = FakeModel(content="", route=json.dumps(
        {"intent": "NOT_ANALYTICS", "focusAxis": "ROOT_CAUSE"}, ensure_ascii=False))
    r = AnalyticsWorkflow(ds=ds, model=model).run(ANALYTICS_Q, role="ENGINEER")

    assert r["intent"] == INTENT_ANALYTICS, "规则已定性时模型判了什么都不该推翻它"
    router = next(s for s in r["trace"]["spans"] if s["spanName"] == "A.Intent_Router")
    assert router["output"]["modelCalled"] is True
    assert router["output"]["pinnedBy"] == "rule"
    assert router["output"]["slots"]["focusAxis"] == "ROOT_CAUSE", "槽位仍要抽出来"


# ---------------------------------------------------------------- 槽位抽取

SLOT_Q = "第三季度网络与打印设备的共性根因是什么"      # 正则接不住"第三季度"


def _slot_route(**over) -> str:
    payload = {"intent": "ANALYTICS",
               "timeWindow": {"kind": "QUARTER", "anchor": "ABSOLUTE", "quarter": 3,
                              "rawText": "第三季度"},
               "domains": ["网络与打印设备"],
               "focusAxis": "ROOT_CAUSE"}
    payload.update(over)
    return json.dumps(payload, ensure_ascii=False)


def test_模型槽位决定时间口径(ds):
    """正则在"第三季度"上会退回默认 90 天，模型把它抽成 2026 Q3。"""
    model = FakeModel(content="", route=_slot_route())
    r = AnalyticsWorkflow(ds=ds, model=model).run(SLOT_Q, role="ENGINEER")

    assert r["window"]["label"] == "2026 Q3"
    assert r["window"]["source"] == "模型抽取"
    # 模型接管的是"默认窗口"，不是与规则字面命中打架 —— 不该报冲突
    assert "WINDOW_CONFLICT" not in {f["code"] for f in r["findings"]}


def test_模型判非分析但槽位照填时槽位仍被采用(ds, relaxed):
    """模型极易"连坐偷懒"：intent 判成 NOT_ANALYTICS 就把后面所有槽位填成 NONE。

    提示词里专门写了"意图与槽位相互独立"来防它；这条验证代码这一侧也不会因为
    意图最终被定性为 ANALYTICS 就把槽位丢掉。
    """
    model = FakeModel(content="", route=_slot_route(intent="NOT_ANALYTICS"))
    r = AnalyticsWorkflow(ds=ds, model=model).run(SLOT_Q, role="ENGINEER")

    assert r["intent"] == INTENT_ANALYTICS
    assert r["window"]["label"] == "2026 Q3", "意图被扭回来的同时，槽位必须还在"


def test_模型槽位rawText无据时退回正则(ds):
    """与数字门禁同构的一道闸：模型编一个用户没说过的"上个月"会被当场拦下。"""
    model = FakeModel(content="", route=_slot_route(
        timeWindow={"kind": "MONTH", "anchor": "PREVIOUS", "rawText": "上个月"}))
    r = AnalyticsWorkflow(ds=ds, model=model).run(SLOT_Q, role="ENGINEER")

    assert r["window"]["source"] == "默认最近90天", "提问里没有时间词，退回默认窗口"
    assert "WINDOW_SLOT_REJECTED" in {f["code"] for f in r["findings"]}


def test_模型调用失败时时间口径退回规则(ds, relaxed):
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(raises=True)).run(ANALYTICS_Q, role="ENGINEER")
    assert r["window"]["source"] == "规则解析", "模型挂了不该连时间口径一起丢"
    assert r["degradedReason"] == DEGRADED_CALL_FAILED, "叙事那一路照旧降级"


def test_关闭模型路由则完全不调模型(ds, relaxed, monkeypatch):
    """ANALYTICS_MODEL_ROUTING=0 是"纯确定性演示"与回归基线的口子。

    关掉的是**路由那一次**调用（意图与槽位全部走规则），Node D 的归因叙事不受影响
    —— 那个开关管的是"请求怎么理解"，不是"结论怎么写"。
    """
    monkeypatch.setattr(cfg, "MODEL_ROUTING_ENABLED", False)
    model = FakeModel(content="ANALYTICS")
    r = AnalyticsWorkflow(ds=ds, model=model).run(ANALYTICS_Q, role="ENGINEER")

    router = next(s for s in r["trace"]["spans"] if s["spanName"] == "A.Intent_Router")
    assert router["output"]["modelCalled"] is False
    assert router["output"]["slots"] is None
    assert model.calls == 1, "只有 Node D 那一次叙事调用"
    assert r["intent"] == INTENT_ANALYTICS
    assert r["window"]["source"] == "规则解析"


# ---------------------------------------------------------------- 降级出口

def test_取数失败如实拒答不用模型知识替代(ds_failing, relaxed):
    r = AnalyticsWorkflow(ds=ds_failing, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    assert r["verdict"] == "REFUSED"
    assert r["refusalReason"] == "MODEL_UNAVAILABLE"
    assert "取不到" in r["answerText"]
    assert r["analyticsFacts"] is None
    assert "SCAN_FAILED" in {f["code"] for f in r["findings"]}


def test_无模型时走模板且标注降级原因(ds, relaxed):
    """没调模型与调了但失败是两回事，盘面上不合并统计。"""
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    assert r["degradedReason"] == DEGRADED_NO_MODEL
    assert "统计口径" in r["answerText"]


def test_模型调用失败退回模板且链路不断(ds, relaxed):
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(raises=True)).run(ANALYTICS_Q, role="ENGINEER")
    assert r["degradedReason"] == DEGRADED_CALL_FAILED
    assert r["verdict"] == "ANSWERED"
    assert "统计口径" in r["answerText"]


def test_模型输出被截断退回模板不回传半截JSON(ds, relaxed):
    """推理模型的思维链会先吃掉 max_tokens，JSON 被拦腰砍断 —— 那是协议碎片，不是答复。"""
    model = FakeModel(content='{"answerText": "蓝屏占比 27', finish_reason="length")
    r = AnalyticsWorkflow(ds=ds, model=model).run(ANALYTICS_Q, role="ENGINEER")
    assert r["degradedReason"] == DEGRADED_TRUNCATED
    assert "answerText" not in r["answerText"]
    narrative = next(s for s in r["trace"]["spans"] if s["spanName"] == "D.Answer_Narrative")
    assert narrative["detail"].get("degradedReason") == DEGRADED_TRUNCATED


def test_叙事JSON不可解析时退回模板(ds, relaxed):
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(content="我觉得吧，情况挺复杂的。")) \
        .run(ANALYTICS_Q, role="ENGINEER")
    assert r["degradedReason"] == DEGRADED_UNPARSABLE
    assert "统计口径" in r["answerText"]


# ---------------------------------------------------------------- 输出门禁

def test_编造数字的叙事被整体退回模板(ds, relaxed):
    """模型写 42%，facts 里根本没有这个数 —— 宁可读起来朴素，也不给一个错数字。"""
    content = json.dumps({"answerText": "打印机故障占比高达 42%，建议立即采购备件。"},
                         ensure_ascii=False)
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(content=content)).run(
        ANALYTICS_Q, role="ENGINEER")
    assert "42%" not in r["answerText"]
    assert "NARRATIVE_FALLBACK" in {f["code"] for f in r["findings"]}
    assert "统计口径" in r["answerText"]


def test_可溯源的叙事被放行(ds, relaxed):
    facts = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(
        ANALYTICS_Q, role="ENGINEER")["analyticsFacts"]
    vpn = next(e for d in facts["dimensions"] if d["axis"] == "SYMPTOM"
               for e in d["entries"] if e["label"] == "VPN连接失败")
    assert vpn["count"] == 1
    content = json.dumps({"answerText": f"VPN 连接失败 {vpn['count']} 单。",
                          "citedTicketIds": vpn["sampleTicketIds"]}, ensure_ascii=False)
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(content=content)).run(
        ANALYTICS_Q, role="ENGINEER")
    assert r["degradedReason"] is None
    assert "VPN 连接失败 1 单" in r["answerText"]


def test_模型建议过守卫后挂进facts(ds, relaxed):
    """建议与代码算出的备件建议同列，由 source 区分 —— 前端据此分组展示。"""
    content = json.dumps({
        "answerText": "蓝屏占比最高，建议先做内存与驱动一致性排查。",
        "recommendations": [
            {"text": "打印机脱机集中在少数设备，建议先排查进纸组件与打印服务", "basisLabels": ["打印机脱机"]},
        ],
    }, ensure_ascii=False)
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(content=content)).run(ANALYTICS_Q, role="ENGINEER")

    recs = r["analyticsFacts"]["recommendations"]
    model_recs = [x for x in recs if x["source"] == "model"]
    rule_recs = [x for x in recs if x["source"] == "rule"]
    assert len(model_recs) == 1
    assert model_recs[0]["kind"] == "排查与巡检"
    assert model_recs[0]["basisLabel"] == "打印机脱机"
    assert rule_recs, "代码算出的备件建议应同时保留"


def test_模型建议引用不存在的标签被剔除并留痕(ds, relaxed):
    content = json.dumps({
        "answerText": "统计口径内建议如下。",
        "recommendations": [
            {"text": "针对主板故障做专项排查", "basisLabels": ["主板故障"]},
        ],
    }, ensure_ascii=False)
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(content=content)).run(ANALYTICS_Q, role="ENGINEER")

    assert not [x for x in r["analyticsFacts"]["recommendations"] if x["source"] == "model"]
    assert "SUGGESTION_REJECTED" in {f["code"] for f in r["findings"]}


def test_叙事被门禁打回时模型建议一并撤掉(ds, relaxed):
    """正文已证明它在编数字，同一轮的建议也不该继续挂着 ——

    留着等于"正文判定不可信，但它的推论照用"。代码算出的备件建议不受影响。
    """
    content = json.dumps({
        "answerText": "蓝屏占比高达 42%，建议立即采购备件。",
        "recommendations": [{"text": "对打印机脱机设备做进纸组件排查", "basisLabels": ["打印机脱机"]}],
    }, ensure_ascii=False)
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(content=content)).run(ANALYTICS_Q, role="ENGINEER")

    assert "NARRATIVE_FALLBACK" in {f["code"] for f in r["findings"]}
    assert not [x for x in r["analyticsFacts"]["recommendations"] if x["source"] == "model"]
    assert [x for x in r["analyticsFacts"]["recommendations"] if x["source"] == "rule"]


def test_无模型时不产出模型建议(ds, relaxed):
    """没调模型就没有它的归纳 —— 建议里只应剩代码算出的备件条目。"""
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    recs = r["analyticsFacts"]["recommendations"]
    assert recs and all(x["source"] == "rule" for x in recs)


def test_模型不给建议不影响作答(ds, relaxed):
    """建议是软要求：缺失只让答复少一块，统计结论不受影响。"""
    content = json.dumps({"answerText": "统计口径内共 11 单。"}, ensure_ascii=False)
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(content=content)).run(ANALYTICS_Q, role="ENGINEER")
    assert r["replyType"] == "ANSWER"
    assert r["degradedReason"] is None
    assert [x for x in r["analyticsFacts"]["recommendations"] if x["source"] == "rule"]


def test_置信度由闸门决定而非模型自称(rows, taxonomy, relaxed):
    """去掉全部 resolution 后根因维度必挂 WARN 闸门，置信度必须被压低。"""
    stripped = FixtureDataSource([t for t in rows if not t.resolution])
    r = AnalyticsWorkflow(ds=stripped, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    assert "ROOT_CAUSE_UNAVAILABLE" in {g["code"] for g in r["analyticsFacts"]["gates"]}
    assert r["confidence"] < 0.85


def test_无闸门时置信度不给折扣(ds, relaxed):
    """子域 + 放宽阈值下没有任何 WARN 闸门，置信度应是基准值而不是被无端压低。"""
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    assert [g["severity"] for g in r["analyticsFacts"]["gates"] if g["severity"] == "WARN"] == []
    assert r["confidence"] == 0.85


def test_模型漏写口径时由代码补上(ds, relaxed):
    """口径是事实不是措辞 —— 实测模型会写出一段漂亮却漏掉时间范围的正文。"""
    facts = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(
        ANALYTICS_Q, role="ENGINEER")["analyticsFacts"]
    label = facts["window"]["label"]
    content = json.dumps({"answerText": "覆盖率为 100%。"}, ensure_ascii=False)
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(content=content)).run(
        ANALYTICS_Q, role="ENGINEER")
    assert r["answerText"].startswith("统计口径：")
    assert label in r["answerText"]


def test_模型已写口径时不重复补(ds, relaxed):
    facts = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(
        ANALYTICS_Q, role="ENGINEER")["analyticsFacts"]
    label = facts["window"]["label"]
    content = json.dumps({"answerText": f"统计口径为 {label}，覆盖率 100%。"},
                         ensure_ascii=False)
    r = AnalyticsWorkflow(ds=ds, model=FakeModel(content=content)).run(
        ANALYTICS_Q, role="ENGINEER")
    assert r["answerText"].count("统计口径") == 1


def test_事实包不泄漏内部字段名(ds, relaxed):
    """模型会照抄它在事实包里看到的键名 —— 那些键名会变成用户可见的词。

    实测踩到过：正文里出现「标签覆盖率 ratio=100.0」「labelled=3，total=3」「来源规则解析」。
    """
    from analytics_service.nodes import _facts_block
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    # 用链路内的 state 构造事实包：直接复用引擎跑出的 facts
    from analytics_service.contract import AnalyticsState
    state = AnalyticsState(question="x")
    state.facts = _facts_from_dict(r["analyticsFacts"])
    block = json.dumps(_facts_block(state), ensure_ascii=False)

    for leaked in ("labelled", "ratio", "windowTotal", "ratioOfAll", "belowThreshold",
                   "sampleTicketIds", "basisLabel", "coverageRatio", "scoped", "applied"):
        assert leaked not in block, f"事实包里泄漏了内部字段名：{leaked}"


def _facts_from_dict(facts):
    """把 HTTP 回传的 facts 还原成对象，供事实包测试使用。"""
    from rag_pipeline.evaluation.aggregate import _facts_to_object
    return _facts_to_object(facts)


def test_提问关注的维度被排到最前(ds, relaxed):
    """实测踩到过：问「共性根因是什么」，模型通篇写现象分布、根因一个字没提。

    正文有长度上限，排在最后的维度会被整个挤掉 —— 所以被问到的那个要排最前。
    """
    from analytics_service.nodes import _facts_block, _focus_axis
    from analytics_service.contract import AnalyticsState

    assert _focus_axis("本季度工单的共性根因是什么？") == "共性根因"
    assert _focus_axis("统计各类故障的现象分布") == "故障现象分布"
    assert _focus_axis("统计一下") is None

    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(
        "本季度工单的共性根因是什么？", role="ENGINEER")
    state = AnalyticsState(question="本季度工单的共性根因是什么？")
    state.facts = _facts_from_dict(r["analyticsFacts"])
    block = _facts_block(state)
    assert block["分布"][0]["维度"] == "共性根因"
    assert block["本次提问关注"] == "共性根因"


def test_未指明关注维度时不加关注字段(ds, relaxed):
    from analytics_service.nodes import _facts_block
    from analytics_service.contract import AnalyticsState
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    state = AnalyticsState(question="统计一下")
    state.facts = _facts_from_dict(r["analyticsFacts"])
    assert "本次提问关注" not in _facts_block(state)


def test_节点异常不中断链路(ds_boom, relaxed):
    """单点失败不得把这次请求变成"一个没有任何观测数据的 500"。"""
    r = AnalyticsWorkflow(ds=ds_boom, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    assert r["success"] is True
    assert r["errors"], "节点异常必须被记录而不是吞掉"
    assert r["answerText"], "异常后仍要给一个可读的答复"

def test_模板文案不泄漏英文轴名(ds, relaxed):
    """降级模板是**用户可见的正文**，`SYMPTOM 分布：…` 这种内部枚举不该出现在里面。

    与事实包那条纪律同源（见 test_事实包不泄漏内部字段名）：内部名一旦流到用户面前，
    页面看着像半成品，排查时还会让人以为是另一个环节的 bug。
    """
    import re
    from analytics_service.engine import AnalyticsWorkflow
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(ANALYTICS_Q, role="ENGINEER")
    assert not re.search(r"\b(SYMPTOM|DEVICE|ROOT_CAUSE)\b", r["answerText"]), r["answerText"][:200]
    assert "故障现象分布" in r["answerText"]
