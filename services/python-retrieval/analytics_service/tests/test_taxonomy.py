# -*- coding: utf-8 -*-
"""词表层的单测。

这里的断言决定统计口径：词表能力一旦回归，所有占比都会悄悄变味，且**不会有任何
报错**。所以每一条都要有断言，尤其是截胡回归 —— 它是实测踩出来的坑。
"""

from __future__ import annotations

import pytest
import yaml

from analytics_service import taxonomy as tx


# ---------------------------------------------------------------- 加载与校验

def test_词表可加载且带版本与指纹(taxonomy):
    assert taxonomy.version
    assert len(taxonomy.fingerprint) == 12
    assert taxonomy.domains, "子域定义不能为空 —— 子域过滤完全依赖它"


def test_泛化词黑名单非空(taxonomy):
    assert taxonomy.generic_denylist, "黑名单是防截胡的唯一硬约束，不能为空"


def _base_data(**kw):
    data = {
        "version": "test",
        "generic_denylist": ["无反应"],
        "SYMPTOM": [{"label": "无法开机", "keywords": ["无法开机"]}],
        "DEVICE": [{"label": "笔记本", "keywords": ["笔记本"]}],
        "ROOT_CAUSE": [{"label": "老化", "keywords": ["老化"]}],
    }
    data.update(kw)
    return data


def test_裸泛化词被拒绝而不是静默降级():
    """泛化词单独出现会截胡更专有的标签，必须加载即失败。"""
    data = _base_data(SYMPTOM=[{"label": "无法开机", "keywords": ["无反应"]}])
    with pytest.raises(tx.TaxonomyError, match="裸泛化词"):
        tx.build_taxonomy(data, "fingerprint")


def test_标注requires_device的泛化词被允许():
    data = _base_data(SYMPTOM=[
        {"label": "无法开机", "keywords": [{"word": "无反应", "requires_device": True}]}])
    tax = tx.build_taxonomy(data, "fingerprint")
    assert tax.keywords[tx.AXIS_SYMPTOM][0].requires_device is True


def test_requires_device的词缺少设备时不计数():
    """标注了 requires_device 的泛化词，没有设备实体共现就不该成立。"""
    data = _base_data(SYMPTOM=[
        {"label": "无法开机", "keywords": [{"word": "无反应", "requires_device": True}]}])
    tax = tx.build_taxonomy(data, "fingerprint")
    assert tx.extract("按了一下无反应", tax).symptom is None
    assert tx.extract("笔记本按了一下无反应", tax).symptom == "无法开机"


def test_引用不存在的子域标签会报错():
    """写错标签名会让子域过滤静默失效，必须加载即拦下。"""
    data = _base_data(DOMAIN=[{"name": "打印", "keywords": ["打印"],
                               "devices": ["不存在的设备"], "symptoms": []}])
    with pytest.raises(tx.TaxonomyError, match="不存在的设备标签"):
        tx.build_taxonomy(data, "fingerprint")


# ---------------------------------------------------------------- 截胡回归
# 以下两条用的是**真实库里触发过问题的原文**，是这个词表最重要的一组护栏。

def test_截胡回归_打印机脱机不被无反应抢走(taxonomy):
    """描述里同时有"打印机"和"无反应"，症状必须是打印机脱机而非无法开机。"""
    title = "打印机再次脱机，重启无效，申请报修"
    desc = ("打印机再次出现脱机故障：发送打印任务无反应，状态显示脱机。"
            "已重启打印机和电脑未解决。请 IT 协助排查。")
    ext = tx.extract_ticket(title, desc, taxonomy)
    assert ext.symptom == "打印机脱机"
    assert ext.device == "打印机"


def test_截胡回归_音量无法调节归外设失灵(taxonomy):
    """描述里的"无反应"是描述按键状态，不能把工单判成无法开机。"""
    title = "电脑音量无法调节"
    desc = ("员工反馈电脑音量无法调节。具体现象（音量键/快捷键是否无反应、"
            "音量滑块是否可拖动但无声音）待工程师受理时进一步确认。")
    ext = tx.extract_ticket(title, desc, taxonomy)
    assert ext.symptom == "外设失灵"


def test_最长命中优先(taxonomy):
    """同时命中「蓝屏」与「无法开机」时取更长的那个。"""
    ext = tx.extract("电脑蓝屏之后就无法开机了", taxonomy)
    assert ext.symptom == "无法开机/电源无反应"


# ---------------------------------------------------------------- 模板剥离

def test_模板剥离按最早的标记切割():
    raw = "员工报障：电脑出现蓝屏。待补充信息：品牌型号、资产编号。"
    assert tx.strip_template(raw) == "员工报障：电脑出现蓝屏。"


def test_模板剥离覆盖等信息待补充变体():
    raw = "开机直接闪退。发生阶段（logo界面/系统加载）、有无报错提示等信息待补充。"
    assert "待补充" not in tx.strip_template(raw)
    assert tx.strip_template(raw).startswith("开机直接闪退")


def test_模板剥离无标记时原样返回():
    raw = "打印机脱机，发送任务无反应。"
    assert tx.strip_template(raw) == raw


def test_模板话术不污染抽取(taxonomy):
    """模板里写着"如 CRITICAL_PROCESS_DIED"这类举例词，剥离后才不会当成现象。"""
    title = "电脑蓝屏"
    desc = ("员工报障：电脑出现蓝屏。待补充信息：蓝屏错误代码或提示"
            "（如 CRITICAL_PROCESS_DIED、MEMORY_MANAGEMENT 等）。")
    ext = tx.extract_ticket(title, desc, taxonomy)
    assert ext.symptom == "蓝屏"


# ---------------------------------------------------------------- 噪声判定

@pytest.mark.parametrize("title,desc,expected", [
    ("test123", "test123", tx.LOW_INFO_JUNK),
    ("123", "1231231233", tx.LOW_INFO_JUNK),
    ("hello", "hello", tx.LOW_INFO_JUNK),
    ("[P0-verify] manual assign path", "Manual dispatch regression check", tx.LOW_INFO_TEST),
    ("[分派探测] C_HW_PC", "探测单据", tx.LOW_INFO_TEST),
    ("【HITL联调测试】办公楼网络中断，请忽略", "联调测试单据，可随时撤销。", tx.LOW_INFO_IGNORE),
    ("【HITL演示】笔记本无法开机", "人机回环演示用单，请忽略。", tx.LOW_INFO_IGNORE),
    ("电脑蓝屏", "", tx.LOW_INFO_EMPTY),
])
def test_噪声判定(title, desc, expected):
    assert tx.low_information_reason(title, desc) == expected


def test_正常工单不是噪声():
    assert tx.low_information_reason("电脑蓝屏", "使用中突然蓝屏，重启后恢复。") is None


def test_请忽略标记优先于其他判定():
    """内容看着真实但标明可撤销的单，必须按"请忽略"归类 —— 否则会污染子域统计。"""
    reason = tx.low_information_reason(
        "【HITL联调测试】办公楼网络中断，请忽略", "Day18 联调测试单据。")
    assert reason == tx.LOW_INFO_IGNORE


# ---------------------------------------------------------------- 子域

def test_子域最长命中_网络与打印不退化为网络设备(taxonomy):
    """「网络与打印设备」含子串「网络」，若退化成网络设备就会把打印机整类丢掉。"""
    doms = tx.resolve_domains("请根据全部网络与打印设备维护工单总结", taxonomy)
    assert [d.name for d in doms] == ["网络与打印设备"]


def test_子域_单独的网络解析为网络设备(taxonomy):
    doms = tx.resolve_domains("统计一下网络类工单", taxonomy)
    assert [d.name for d in doms] == ["网络设备"]


def test_子域_并列两个域时都保留(taxonomy):
    """「打印机和外设」是用户真的并列了两个域；只留最长的一个会答成一份只有打印机的结果。"""
    doms = tx.resolve_domains("统计本季度全部打印机和外设问题各有多少单", taxonomy)
    assert sorted(d.name for d in doms) == ["外设", "打印设备"]


def test_子域_重叠的短关键词被长跨度吸收(taxonomy):
    """「打印设备」是「网络与打印设备」里的片段，不得被单独算成一个域。"""
    doms = tx.resolve_domains("请根据全部网络与打印设备维护工单总结", taxonomy)
    assert [d.name for d in doms] == ["网络与打印设备"]
    assert "打印设备" not in [d.name for d in doms]


def test_无范围限定时不解析出子域(taxonomy):
    assert tx.resolve_domains("总结本季度所有工单的故障分布", taxonomy) == []


def test_子域按设备或症状取并集(taxonomy):
    """打印机那张工单没有症状词「脱机」也有设备词「打印机」，靠并集才能捞到。"""
    dom = tx.resolve_domains("网络与打印设备", taxonomy)[0]
    assert dom.matches(device="打印机", symptom=None) is True
    assert dom.matches(device=None, symptom="VPN连接失败") is True
    assert dom.matches(device=None, symptom=None) is False