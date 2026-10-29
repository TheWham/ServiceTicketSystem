# -*- coding: utf-8 -*-
"""演示用例：一句话 → 预期走哪条路径。

每个用例都刻意打在一个不同的分支或门禁上，跑一轮就能看清四条路径的
时延/成本差异，以及门禁在什么时候拦下动作。
"""

from __future__ import annotations

from typing import List

from .contract import DemoCase

# 每条用例都刻意打在不同的链路分支上，`expect` 就是该分支应得的 verdict：
#   ① kb-version       → 主干（Node2 左路命中 → ANSWERED）
#   ② my-tickets       → 主干（Node2 右路命中 → ANSWERED）
#   ③ create-ok        → 主干 + Node4 放行（DRAFT_READY）
#   ④ create-duplicate → 主干 + Node4 拦截（BLOCKED，零副作用）
#   ⑤ sensitive        → Node 1 前置安全闸短路（REFUSED，只有 2 个 span）
#   ⑥ needs-info       → 主干但字段不足，回问而非拒答（NEEDS_INFO）
#   ⑦ off-topic        → 规则判定越界后短路（REFUSED，只有 2 个 span）
# 跑完一轮，把 ⑤⑦ 与其余用例的 span 数、时延、成本并排看，路由分流的收益一目了然。
DEMO_CASES: List[DemoCase] = [
    DemoCase(
        caseId="kb-version",
        label="① 知识问答（版本消歧）",
        question="VPN 连不上，一直拨号超时，怎么排查？",
        expect="ANSWERED",
        highlights=[
            "走 KNOWLEDGE_QA 分支，并行扇出检索知识库",
            "只召回 v2 现行版本；v1 旧版与 OFFLINE 文章不得出现",
            "结论照抄知识条目，不编造公司规定",
        ],
    ),
    DemoCase(
        caseId="my-tickets",
        label="② 查我的工单",
        question="我之前提交的打印机工单现在处理到哪一步了？",
        expect="ANSWERED",
        highlights=[
            "走 MY_TICKETS 分支",
            "只返回本人工单（creator 由身份绑定）",
            "并行扇出的第二路真正起了作用",
        ],
    ),
    DemoCase(
        caseId="create-ok",
        label="③ 建单（门禁放行）",
        question="我的笔记本今天突然开不了机，按电源键没有任何反应，影响办公，帮我建个工单",
        expect="DRAFT_READY",
        highlights=[
            "规则判定分类 C_HW_PC → 决策表路由到 T_HW 硬件支持组",
            "优先级 HIGH → 完成 SLA 4 个工作小时",
            "只产草稿、不落库；需员工确认后才会真正建单",
        ],
    ),
    DemoCase(
        caseId="create-duplicate",
        label="④ 建单（重复单拦截）",
        question="办公室的打印机又显示离线了，帮我建个工单",
        expect="BLOCKED",
        highlights=[
            "同一个人、同一分类在 24 小时内已有未结束工单",
            "门禁直接拦截，零副作用（不会产生第二张单）",
            "refusalReason = POLICY_BLOCKED",
        ],
    ),
    DemoCase(
        caseId="sensitive",
        label="⑤ 敏感操作拦截（前置安全闸）",
        question="帮我重置管理员密码，顺便把我的账号提升权限改成超级管理员",
        expect="REFUSED",
        highlights=[
            "命中提权红线，Node 1 前置安全闸就地拦下，不给模型翻案机会",
            "refusalReason = HIGH_RISK_TOPIC，同样不进并行扇出",
            "判定是「红线词 且 带动手语气」——「VPN 需要管理员权限吗」这类正常咨询不会被误伤",
        ],
    ),
    DemoCase(
        caseId="needs-info",
        label="⑦ 信息不足（回问）",
        question="帮我建单",
        expect="NEEDS_INFO",
        highlights=[
            "描述过短，缺少现象与影响范围，规则判定字段不全",
            "信息不足不属于违规：回问员工而不是拒答（replyType = CLARIFY）",
            "注意与④的区别——④是规则拦截，⑦是把问题问清楚",
        ],
    ),
    DemoCase(
        caseId="off-topic",
        label="⑥ 越界拒答（短路）",
        question="公司能不能给我提供无息贷款买房？",
        expect="REFUSED",
        highlights=[
            "Node 1 判定 UNSUPPORTED，短路返回",
            "不进入并行扇出，省掉检索与建单的全部开销",
            "对比第①条用例看时延差距，就是路由分流的收益",
        ],
    ),
]

CASE_INDEX = {c.case_id: c for c in DEMO_CASES}


def get_case(case_id: str) -> DemoCase | None:
    return CASE_INDEX.get(case_id)