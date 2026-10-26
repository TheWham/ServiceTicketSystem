# -*- coding: utf-8 -*-
"""链路端到端的单测：短路出口、降级出口、门禁拦截。

重点是**短路**：如果非分析型请求还跑完聚合，用户问"我 VPN 连不上怎么办"就会收到
一份季度统计报告 —— 那正是整条链路要防的"答非所问"，所以必须逐条验证它真的没跑。
"""

from __future__ import annotations

import json

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
    """可编排的假模型：给定回复内容，验证链路对模型输出的处理。"""

    def __init__(self, content: str = "", *, available: bool = True,
                 finish_reason: str = "stop", raises: bool = False):
        self._content = content
        self._available = available
        self._finish = finish_reason
        self._raises = raises
        self.calls = 0

    @property
    def available(self) -> bool:
        return self._available

    def complete(self, messages, max_tokens=None, temperature=None, trace_id=None):
        self.calls += 1
        if self._raises:
            from analytics_service.model_client import ModelUnavailable
            raise ModelUnavailable("模拟模型故障")
        return ModelReply(self._content, 10, 20, "reported", self._finish)


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

def test_非分析型请求短路不跑聚合(ds, relaxed):
    """这是本条链路最重要的行为断言：普通问题不能被当成统计题作答。"""
    r = AnalyticsWorkflow(ds=ds, model=NullModelClient()).run(PLAIN_Q, role="ENGINEER")
    assert r["intent"] == INTENT_NOT_ANALYTICS
    assert r["replyType"] == "NOT_ANALYTICS"
    assert r["analyticsFacts"] is None, "短路路径不应产生任何统计结果"
    assert _spans(r) == ["A.Intent_Router", "A.Short_Circuit"]


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


def test_上游已指定意图时不重复调模型(ds, relaxed):
    """Java 侧已判过一次，Python 侧不该再花一次推理费。"""
    model = FakeModel(content="ANALYTICS")
    r = AnalyticsWorkflow(ds=ds, model=model).run(
        "本季度工单的分布", role="ENGINEER", upstream_intent=INTENT_ANALYTICS)
    assert r["intent"] == INTENT_ANALYTICS
    router = next(s for s in r["trace"]["spans"] if s["spanName"] == "A.Intent_Router")
    assert router["output"]["modelCalled"] is False


def test_规则命中时不调模型(ds, relaxed):
    model = FakeModel(content="ANALYTICS")
    r = AnalyticsWorkflow(ds=ds, model=model).run(ANALYTICS_Q, role="ENGINEER")
    router = next(s for s in r["trace"]["spans"] if s["spanName"] == "A.Intent_Router")
    assert router["output"]["modelCalled"] is False


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