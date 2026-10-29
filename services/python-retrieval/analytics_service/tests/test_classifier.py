# -*- coding: utf-8 -*-
"""意图路由的单测：规则判定 + 模型输出收窄 + 仲裁表。

仲裁表是本链路唯一偏离仓库既有范式的地方（第 5 条走澄清），
所以五条分支逐条钉死。
"""

from __future__ import annotations

import json

import pytest

from analytics_service import classifier as clf
from analytics_service import taxonomy as tx
from analytics_service.contract import (INTENT_ANALYTICS, INTENT_CLARIFY,
                                        INTENT_NOT_ANALYTICS)


# ---------------------------------------------------------------- 规则判定

@pytest.mark.parametrize("question", [
    "请根据全部网络与打印设备工单，总结本季度共性根因",
    "统计一下各类故障的占比",
    "本季度工单的故障分布情况",
    "给出下季度的备件采购建议",
    "分析一下近 90 天的趋势",
])
def test_分析型问题规则命中(question, taxonomy):
    hit, detail = clf.rule_route(question, taxonomy)
    assert hit is True, detail


@pytest.mark.parametrize("question", [
    "我的 VPN 连不上怎么办",
    "打印机脱机了怎么处理",
    "帮我建一张工单",
    "电脑蓝屏怎么排查",
    "你好",
])
def test_具体问题规则不命中(question, taxonomy):
    hit, detail = clf.rule_route(question, taxonomy)
    assert hit is False, detail


def test_规则判定给出可解释依据(taxonomy):
    """规则判完不给理由，排查时只能靠猜。"""
    _, detail = clf.rule_route("总结本季度全部工单的分布", taxonomy)
    assert "得分" in detail and "阈值" in detail


# ---------------------------------------------------------------- 模型输出收窄

def test_收敛英文标签():
    assert clf.normalize_model_intent("ANALYTICS") == INTENT_ANALYTICS
    assert clf.normalize_model_intent("NOT_ANALYTICS") == INTENT_NOT_ANALYTICS


def test_NOT_ANALYTICS不被ANALYTICS子串误判():
    """NOT_ANALYTICS 里含有 ANALYTICS 子串，判断顺序错了就会全判成分析型。"""
    assert clf.normalize_model_intent("not_analytics") == INTENT_NOT_ANALYTICS
    assert clf.normalize_model_intent("NOT ANALYTICS") == INTENT_NOT_ANALYTICS


def test_收敛中文与序号输出():
    assert clf.normalize_model_intent("1") == INTENT_ANALYTICS
    assert clf.normalize_model_intent("2") == INTENT_NOT_ANALYTICS
    assert clf.normalize_model_intent("非分析") == INTENT_NOT_ANALYTICS
    assert clf.normalize_model_intent("宏观归纳") == INTENT_ANALYTICS


@pytest.mark.parametrize("raw", ["", "   ", "我不确定", "maybe", "42"])
def test_无法收敛返回None交由规则兜底(raw):
    assert clf.normalize_model_intent(raw) is None


# ---------------------------------------------------------------- 仲裁表

def test_仲裁1_模型不可用时规则兜底_命中():
    intent, note = clf.resolve_analytics_intent(None, rule_hit=True)
    assert intent == INTENT_ANALYTICS and "规则" in note


def test_仲裁2_模型不可用时规则兜底_未命中():
    intent, note = clf.resolve_analytics_intent(None, rule_hit=False)
    assert intent == INTENT_NOT_ANALYTICS and "规则" in note


@pytest.mark.parametrize("model_intent,rule_hit,expected", [
    (INTENT_ANALYTICS, True, INTENT_ANALYTICS),
    (INTENT_NOT_ANALYTICS, False, INTENT_NOT_ANALYTICS),
])
def test_仲裁3_双方一致则采信(model_intent, rule_hit, expected):
    intent, note = clf.resolve_analytics_intent(model_intent, rule_hit)
    assert intent == expected and "一致" in note


def test_仲裁4_分歧且规则命中时采信模型():
    """与 workflow_demo/nodes.resolve_intent 同构：分歧时模型胜，规则兜底。"""
    intent, note = clf.resolve_analytics_intent(INTENT_NOT_ANALYTICS, rule_hit=True)
    assert intent == INTENT_NOT_ANALYTICS
    assert "采信模型" in note


def test_仲裁5_分歧且规则未命中时走澄清():
    """唯一偏离：跨服务边界误判代价不对称，先问一句再决定。"""
    intent, note = clf.resolve_analytics_intent(INTENT_ANALYTICS, rule_hit=False)
    assert intent == INTENT_CLARIFY
    assert "澄清" in note


def test_澄清文案给出可执行的下一步():
    assert "时间范围" in clf.CLARIFY_TEXT or "回复" in clf.CLARIFY_TEXT

# ============================================================ 槽位解析（parse_route）

def test_裸标签仍然只当意图用():
    """旧行为要保住：假模型与"只输出一个标签"的端点都只给四个字。"""
    intent, slots = clf.parse_route("ANALYTICS")
    assert intent == INTENT_ANALYTICS and slots is None


def test_截断的JSON片段不被当成意图():
    """`{"intent": "ANALYTICS"` 里含 ANALYTICS，按子串收下会把一次失败的调用当成功 ——
    而它连槽位都没抽完。宁可判不出，退回规则。"""
    intent, slots = clf.parse_route('{"intent": "ANALYTICS"')
    assert intent is None and slots is None


def test_解析完整JSON(taxonomy):
    content = json.dumps({
        "intent": "ANALYTICS",
        "timeWindow": {"kind": "QUARTER", "anchor": "ABSOLUTE", "quarter": 3,
                       "rawText": "第三季度"},
        "domains": ["网络与打印设备"],
        "focusAxis": "ROOT_CAUSE",
    }, ensure_ascii=False)
    intent, slots = clf.parse_route(content, taxonomy)
    assert intent == INTENT_ANALYTICS
    assert slots.has_time and slots.time_window["quarter"] == 3
    assert slots.domains == ["网络与打印设备"]
    assert slots.focus_axis == "ROOT_CAUSE"


def test_代码块包裹也能解析(taxonomy):
    content = "```json\n" + json.dumps({"intent": "NOT_ANALYTICS", "focusAxis": "SYMPTOM"}) + "\n```"
    intent, slots = clf.parse_route(content, taxonomy)
    assert intent == INTENT_NOT_ANALYTICS
    assert slots.focus_axis == "SYMPTOM"


def test_意图与槽位互不连坐(taxonomy):
    """模型把 intent 写成乱码但槽位抽对了，槽位照样可用。

    合成一个"要么全要要么全不要"的结果，会让一个字段的失误把另外三个一起废掉。
    """
    content = json.dumps({"intent": "嗯……我看看", "focusAxis": "DEVICE",
                          "domains": ["终端设备"]}, ensure_ascii=False)
    intent, slots = clf.parse_route(content, taxonomy)
    assert intent is None, "意图收敛不了，交由规则"
    assert slots.focus_axis == "DEVICE" and slots.domains == ["终端设备"]


@pytest.mark.parametrize("raw,expected", [
    ("NONE", ""), ("", ""), (None, ""), ("SYMPTOM", "SYMPTOM"),
    ("symptom", "SYMPTOM"), ("共性根因", "ROOT_CAUSE"), ("设备分布", "DEVICE"),
])
def test_focus轴归一(raw, expected):
    assert clf._norm_focus(raw) == expected


def test_不存在的子域名被丢弃(taxonomy):
    """造出来的名字进不来 —— 地名错只是范围限定少生效一项，不该让链路失败。"""
    intent, slots = clf.parse_route(json.dumps({
        "intent": "ANALYTICS", "domains": ["打印设备", "量子计算设备", " 网络设备 "],
    }, ensure_ascii=False), taxonomy)
    assert slots.domains == ["打印设备", "网络设备"]


def test_重复子域名去重(taxonomy):
    _, slots = clf.parse_route(json.dumps({
        "intent": "ANALYTICS", "domains": ["外设", "外设"],
    }, ensure_ascii=False), taxonomy)
    assert slots.domains == ["外设"]


def test_组合子域与它的子域只留一个(taxonomy):
    """词表里"网络与打印设备"与"网络设备""打印设备"并存，三者成员相同。

    模型可能都给出 —— 全留着只会让页面上的"范围限定"出现重复项。
    """
    got = tx.resolve_domain_names(["网络与打印设备", "网络设备", "打印设备"], taxonomy)
    assert [d.name for d in got] == ["网络与打印设备"]


def test_域名归一后按词表校验(taxonomy):
    got = tx.resolve_domain_names(["「外设」", "外设"], taxonomy)
    assert [d.name for d in got] == ["外设"]


def test_slots的简报只含可展示字段(taxonomy):
    _, slots = clf.parse_route(json.dumps({
        "intent": "ANALYTICS",
        "timeWindow": {"kind": "MONTH", "anchor": "PREVIOUS", "rawText": "上个月"},
        "focusAxis": "SYMPTOM",
    }, ensure_ascii=False), taxonomy)
    assert set(slots.brief()) == {"timeWindow", "domains", "focusAxis"}
