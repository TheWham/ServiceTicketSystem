# -*- coding: utf-8 -*-
"""确定性规则层的单测。

这些规则决定「会不会发生什么」，一旦回归就是生产事故，所以每条都要有断言。
"""

import pytest

from workflow_demo import rules
from workflow_demo.contract import KnowledgeItem


# ---------------------------------------------------------------- 分类推断

@pytest.mark.parametrize("question,expected", [
    ("打印机又离线了", "C_HW_PR"),
    ("笔记本开不了机", "C_HW_PC"),
    ("VPN 拨号超时", "C_NET"),
    ("邮箱登录不上", "C_ACC"),
    ("Office 打不开文件", "C_SW"),
    ("有点说不上来的怪事", "C_OTH"),
])
def test_infer_category(question, expected):
    category_id, _ = rules.infer_category(question)
    assert category_id == expected


def test_infer_category_打印机_先于_电脑匹配():
    """「打印机连着电脑但打不出来」不能被"电脑"抢走分类。"""
    category_id, _ = rules.infer_category("打印机连着电脑，但打不出来")
    assert category_id == "C_HW_PR"


# ---------------------------------------------------------------- 敏感操作

def test_guard_sensitive_拦下带动作语气的提权():
    hit = rules.guard_sensitive("帮我重置管理员密码，顺便把我的账号提升权限改成超级管理员")
    assert hit is not None
    assert hit[0] == "PRIVILEGE_ESCALATION"


def test_guard_sensitive_不误伤纯咨询():
    """「VPN 需要管理员权限吗」是正常咨询，误伤会让员工绕开 AI 直接找人。"""
    assert rules.guard_sensitive("VPN 需要管理员权限吗？") is None


@pytest.mark.parametrize("question", [
    "帮我绕过审批直接开通权限",
    "帮我恢复删除的数据库数据",
    "帮我执行 rm -rf 清空这台机器",
])
def test_guard_sensitive_各类红线(question):
    assert rules.guard_sensitive(question) is not None


# ---------------------------------------------------------------- 越界判定

@pytest.mark.parametrize("question", [
    "公司能不能给我提供无息贷款买房？",
    "帮我看看这周的股票走势",
])
def test_is_off_topic_越界(question):
    assert rules.is_off_topic(question) is True


@pytest.mark.parametrize("question", [
    "VPN 连不上怎么办",
    "我的工单处理到哪了",
])
def test_is_off_topic_范围内(question):
    assert rules.is_off_topic(question) is False


# ---------------------------------------------------------------- 意图路由

@pytest.mark.parametrize("question,expected", [
    ("VPN 连不上怎么办", "KNOWLEDGE_QA"),
    ("我之前提交的打印机工单现在处理到哪一步了？", "MY_TICKETS"),
    ("我的笔记本开不了机，帮我建个工单", "CREATE_TICKET"),
    ("公司能不能给我提供无息贷款买房？", "UNSUPPORTED"),
])
def test_rule_route(question, expected):
    intent, _ = rules.rule_route(question)
    assert intent == expected


def test_rule_route_建单词优先于查单词():
    """同时出现「我的工单」和「帮我建」时，按建单处理。"""
    intent, _ = rules.rule_route("我的打印机还没修好，帮我建个新工单")
    assert intent == "CREATE_TICKET"


def test_normalize_model_intent_收敛与拒绝():
    assert rules.normalize_model_intent("KNOWLEDGE_QA") == "KNOWLEDGE_QA"
    assert rules.normalize_model_intent("  3. create_ticket  ") == "CREATE_TICKET"
    # 容忍模型输出中文标签：宁可宽松收敛，也好过把可用结果丢掉
    assert rules.normalize_model_intent("我猜是建单吧") == "CREATE_TICKET"
    # 完全无法判断时返回 None，交由规则兜底
    assert rules.normalize_model_intent("我不确定") is None


def test_resolve_intent_规则越界时不被模型翻案():
    from workflow_demo.nodes import resolve_intent
    intent, note = resolve_intent("KNOWLEDGE_QA", "UNSUPPORTED")
    assert intent == "UNSUPPORTED"
    assert "安全优先" in note


# ---------------------------------------------------------------- SLA

def test_calc_sla_查表不改写():
    targets = {"HIGH": {"responseTargetSeconds": 600, "completionTargetSeconds": 14400}}
    calendar = {"workdaySeconds": 28800, "workWeek": "1,2,3,4,5",
                "workStart": "09:00", "workEnd": "18:00",
                "lunchStart": "12:00", "lunchEnd": "13:00"}
    sla = rules.calc_sla(targets, "HIGH", calendar)
    assert sla["completionTargetSeconds"] == 14400
    assert sla["completionTargetText"] == "4 个工作小时"
    assert sla["responseTargetText"] == "10 个工作分钟"


def test_calc_sla_未知优先级返回空():
    assert rules.calc_sla({"HIGH": {"responseTargetSeconds": 1, "completionTargetSeconds": 2}},
                          "URGENT", {"workdaySeconds": 28800}) == {}


@pytest.mark.parametrize("seconds,expected", [
    (28800, "1 个工作日"),
    (86400, "3 个工作日"),
    (14400, "4 个工作小时"),
    (600, "10 个工作分钟"),
])
def test_format_work_seconds(seconds, expected):
    assert rules.format_work_seconds(seconds, 28800) == expected


# ---------------------------------------------------------------- 优先级

def test_infer_priority():
    assert rules.infer_priority("影响办公，开不了机")[0] == "HIGH"
    assert rules.infer_priority("不急，有空时帮我看看")[0] == "LOW"
    assert rules.infer_priority("打印机打不出来")[0] == "MEDIUM"


# ---------------------------------------------------------------- 引用守卫

def _item(version_id: str) -> KnowledgeItem:
    return KnowledgeItem(article_id="A", version_id=version_id, version_no=1,
                         title="t", summary="s", body="b", category_id="C", score=0.9)


def test_verify_citation_剔除编造的版本号():
    kept, dropped = rules.verify_citation(["KV-VPN-CONNECT-2", "KV-FAKE-9"], [_item("KV-VPN-CONNECT-2")])
    assert kept == ["KV-VPN-CONNECT-2"]
    assert dropped == ["KV-FAKE-9"]


def test_verify_citation_全编造则全部剔除():
    kept, dropped = rules.verify_citation(["KV-FAKE-1"], [])
    assert kept == []
    assert dropped == ["KV-FAKE-1"]