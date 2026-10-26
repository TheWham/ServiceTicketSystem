# -*- coding: utf-8 -*-
"""确定性规则层：**这些判断绝不交给模型**。

大模型是概率生成器，不是计算器也不是权限系统。凡是"会不会发生什么"的判定
（分到哪个组、SLA 多久、算不算重复单、能不能碰敏感操作、引用的版本是否真的检索到），
一律由本模块的纯函数决定，模型只负责把结论写成员工读得懂的话。

规则口径来源：
- 分类/路由：项目种子库 category / category_route
- SLA：docs/IT服务工单系统PRD-Ultimate.md 11.2 / 11.3
- 敏感操作：agent_service 系统提示词第 5 条 + .agents/skills/ai-agent-guard
"""

# ------------------------------------------------------------------ 链路调用点
# 本模块全是纯函数，没有状态也不写 Trace；节点在下面这些位置调用它们，
# 换句话说：**这一层就是链路里所有「判定」的实际发生地**。
#
#   Node 1 route_intent
#     ├─ rule_route()             规则路由 —— 无模型时的依据，也是模型结果的校验基线
#     ├─ guard_sensitive()        前置安全闸 —— 命中即写 refusal_reason=HIGH_RISK_TOPIC
#     └─ normalize_model_intent() 把模型的自由文本收敛成四选一枚举
#
#   Node 3 evaluate_and_synthesize（前半段：裁决）
#     ├─ infer_category()         分类（有知识命中时被检索结果盖过）
#     ├─ infer_priority()         优先级        ┐
#     ├─ calc_sla()               SLA 查表      ├─ 仅建单路径
#     ├─ duplicate_finding()      重复单结论    ┘
#     └─ clean_text()             短字段的空白清理
#
#   Node 3 _synthesize（后半段：终审）
#     └─ verify_citation()        引用守卫 —— 模型声称的依据必须在本次检索结果里
#
# 注意分工：Node 1/3 的模型调用只影响「分类标签」和「措辞」，
# 上面这些函数的结论（要不要拦、分给谁、几天 SLA）模型一概碰不到。

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .contract import KnowledgeItem, RuleFinding

# ---------------------------------------------------------------- 分类推断（确定性）

# 顺序即优先级：先匹配到的先算（如"打印机"应先于"电脑"）
_CATEGORY_PATTERNS: List[Tuple[str, Tuple[str, ...]]] = [
    ("C_HW_PR", ("打印机", "打印", "扫描仪", "复印件", "色带", "墨盒", "外设")),
    ("C_NET", ("vpn", "网络", "wifi", "无线", "网速", "上网", "断网", "网线", "路由器", "拨号")),
    ("C_ACC", ("账号", "账户", "密码", "权限", "邮箱", "登录", "鉴权", "域账号")),
    ("C_HW_PC", ("笔记本", "台式机", "电脑", "开机", "蓝屏", "死机", "显示器", "键盘", "鼠标", "主机")),
    ("C_SW", ("软件", "office", "办公软件", "客户端", "系统", "应用", "程序", "安装包")),
]


def infer_category(question: str) -> Tuple[str, str]:
    """问题 → 分类 ID。命中哪条规则一并返回，便于审计。返回 (category_id, 命中依据)。

    Node 3 调用。注意它的结果**可能被检索结果盖过**：知识库有高置信命中时，
    分类以命中文章自己的 category_id 为准 —— 这里是兜底，不是唯一依据。
    """
    text = question.lower()
    for category_id, patterns in _CATEGORY_PATTERNS:
        for p in patterns:
            if p in text:
                return category_id, f"命中分类关键词「{p}」→ {category_id}"
    return "C_OTH", "未命中任何分类关键词，兜底归入 C_OTH"


# ---------------------------------------------------------------- 敏感操作拦截

# 敏感操作拦截。
#
# 判定是「红线关键词 且 带动手语气」的合取，不是单纯的关键词命中：
# 「帮我重置管理员密码」要拦，但「VPN 需要管理员权限吗」是正常咨询，不该拦。
# 纯关键词匹配会把后者误伤，而误伤会让员工直接绕过 AI 去找人。
_ACTION_VERBS = ("帮我", "给我", "替我", "麻烦你", "重置", "改成", "改为", "提升", "开通",
                 "绕过", "跳过", "破解", "恢复", "删除", "清空", "拆", "drop", "rm -rf")

# (规则码, 关键词组, 说明)。命中即 Block，不给模型任何翻案机会。
_SENSITIVE_RULES: List[Tuple[str, Tuple[str, ...], str]] = [
    ("PRIVILEGE_ESCALATION", ("提权", "提升权限", "管理员权限", "超级管理员", "root 权限", "root权限",
                              "改成管理员", "加管理员", "开通管理员"),
     "涉及权限提升，必须走正式权限申请与审批，AI 不得代为操作"),
    ("BYPASS_SECURITY", ("绕过", "跳过审批", "规避", "破解", "免密", "破解密码", "绕过检测"),
     "涉及绕过安全控制，属于红线操作"),
    ("DATA_RECOVERY", ("数据恢复", "找回删除", "恢复删除", "恢复数据", "找回丢失的数据"),
     "涉及数据丢失恢复，属于高风险操作，须转人工"),
    ("HIGH_RISK_COMMAND", ("删库", "格式化硬盘", "清空数据库", "rm -rf", "drop table", "删除所有数据"),
     "涉及高危命令/破坏性操作"),
    ("HARDWARE_DISASSEMBLY", ("拆机", "拆开主机", "自行拆", "拆修", "换主板"),
     "涉及硬件拆修，须由硬件支持组现场处理"),
]

# 越界问题特征（与 IT 服务无关）
_OFF_TOPIC_MARKERS = ("贷款", "买房", "购房", "公积金", "工资", "薪资", "股票", "基金", "彩票",
                      "天气", "星座", "讲个笑话", "写诗", "小说", "旅游攻略", "怎么做菜")

# IT 服务范围关键词：命中即可判定"在服务范围内"
_IT_SCOPE_KEYWORDS = (
    "电脑", "笔记本", "台式机", "打印机", "扫描仪", "显示器", "键盘", "鼠标", "主机", "开机", "蓝屏",
    "网络", "vpn", "wifi", "无线", "网速", "断网", "网线", "路由器", "拨号", "上网",
    "邮箱", "账号", "账户", "密码", "权限", "登录", "域账号", "软件", "office", "系统", "客户端",
    "工单", "建单", "提单", "报修", "故障", "办公", "电脑", "it", "云盘", "共享盘", "远程",
)


def guard_sensitive(question: str) -> Optional[Tuple[str, str]]:
    """敏感操作拦截：命中返回 (规则码, 说明)，未命中返回 None。

    必须同时满足「红线关键词」与「带动手语气」，理由见 `_ACTION_VERBS` 的注释。

    Node 1 调用，且**在模型调用之前** —— 命中即写 refusal_reason=HIGH_RISK_TOPIC，
    后面的 skip_model 因此成立，这条请求不会产生任何模型费用。
    """
    text = question.lower()
    if not any(v in text for v in _ACTION_VERBS):
        return None
    for code, keywords, message in _SENSITIVE_RULES:
        for kw in keywords:
            if kw in text:
                return code, f"{message}（命中词：{kw}）"
    return None


def is_off_topic(question: str) -> bool:
    """是否越出 IT 服务范围。先看明确越界词，再看有无 IT 关键词。

    被 rule_route 调用；判真即路由为 UNSUPPORTED，进而让 Node 1 短路整条链路 ——
    所以这里的误判代价是「一次本该给答案的请求被拒」，宁可保守也别放宽。
    """
    text = question.lower()
    if any(m in text for m in _OFF_TOPIC_MARKERS):
        return True
    return not any(k in text for k in _IT_SCOPE_KEYWORDS)


# ---------------------------------------------------------------- 意图路由（规则兜底）

_CREATE_MARKERS = ("建单", "报修", "帮我建", "帮我提", "提交工单", "提个工单", "申请工单", "开个工单", "创建工单")
_TICKET_QUERY_MARKERS = ("我的工单", "我提的", "我提交的", "工单状态", "工单进度", "处理到哪", "到哪一步", "进度如何")


def rule_route(question: str) -> Tuple[str, str]:
    """无模型时的确定性路由，同时也是模型路由结果的校验基线。返回 (意图, 依据)。

    Node 1 的**第一步**就调它，所以「模型还没被调用，链路已经有了一个兜底结论」。
    这个顺序很关键：越界与红线请求在这里就能判死，不必花钱问模型。
    """
    from .contract import (INTENT_CREATE_TICKET, INTENT_KNOWLEDGE, INTENT_MY_TICKETS,
                           INTENT_UNSUPPORTED)

    text = question.lower()
    if is_off_topic(question):
        return INTENT_UNSUPPORTED, "问题不含 IT 服务关键词或命中越界词"
    for m in _CREATE_MARKERS:
        if m in text:
            return INTENT_CREATE_TICKET, f"命中建单意图词「{m}」"
    for m in _TICKET_QUERY_MARKERS:
        if m in text:
            return INTENT_MY_TICKETS, f"命中查工单意图词「{m}」"
    return INTENT_KNOWLEDGE, "含 IT 服务关键词，按知识问答处理"


def normalize_model_intent(raw: str) -> Optional[str]:
    """把模型输出的自由文本收敛成四选一枚举；无法收敛返回 None（交由规则兜底）。

    由 Node 1 调用，是「模型 → 链路」的收窄口：模型只被允许产出一个标签，
    收敛失败就退回 rule_route 的结果，绝不让自由文本流进 state.intent。
    """
    from .contract import (INTENT_CREATE_TICKET, INTENT_KNOWLEDGE, INTENT_MY_TICKETS,
                           INTENT_UNSUPPORTED)

    text = (raw or "").strip().upper()
    for intent in (INTENT_CREATE_TICKET, INTENT_MY_TICKETS, INTENT_UNSUPPORTED, INTENT_KNOWLEDGE):
        if intent in text:
            return intent
    # 容忍模型输出中文标签或序号
    mapping = (("1", INTENT_KNOWLEDGE), ("2", INTENT_MY_TICKETS),
               ("3", INTENT_CREATE_TICKET), ("4", INTENT_UNSUPPORTED),
               ("知识", INTENT_KNOWLEDGE), ("工单状态", INTENT_MY_TICKETS),
               ("建单", INTENT_CREATE_TICKET), ("越界", INTENT_UNSUPPORTED))
    for token, intent in mapping:
        if token in text:
            return intent
    return None


# ---------------------------------------------------------------- SLA 决策表

def format_work_seconds(seconds: int, workday_seconds: int) -> str:
    """把秒数翻译成「N 个工作日 / N 个工作小时」的读法。"""
    if workday_seconds <= 0:
        return f"{seconds} 秒"
    if seconds % workday_seconds == 0:
        return f"{seconds // workday_seconds} 个工作日"
    if seconds % 3600 == 0:
        return f"{seconds // 3600} 个工作小时"
    if seconds % 60 == 0:
        return f"{seconds // 60} 个工作分钟"
    return f"{seconds} 秒"


def calc_sla(sla_targets: Dict[str, Dict[str, int]], priority: str,
             calendar: Dict[str, Any]) -> Dict[str, Any]:
    """查决策表得到 SLA 目标（纯查表，不做任何推算）。

    Node 3 建单路径调用；两个表（sla_target + service_calendar）都来自数据源，
    这里只把它们拼成人话，不引入任何自己的计算 —— 数值口径必须和产品侧一致。
    """
    target = sla_targets.get(priority)
    if not target:
        return {}
    workday = int(calendar.get("workdaySeconds", 28800))
    response_s = int(target["responseTargetSeconds"])
    completion_s = int(target["completionTargetSeconds"])
    return {
        "priority": priority,
        "responseTargetSeconds": response_s,
        "completionTargetSeconds": completion_s,
        "responseTargetText": format_work_seconds(response_s, workday),
        "completionTargetText": format_work_seconds(completion_s, workday),
        "nearBreachThreshold": 0.8,   # PRD 11.3：消耗到 80% 提醒
        "calendar": {
            "workWeek": calendar.get("workWeek"),
            "workStart": calendar.get("workStart"),
            "workEnd": calendar.get("workEnd"),
            "lunchPause": f"{calendar.get('lunchStart')}~{calendar.get('lunchEnd')}",
        },
    }


# ---------------------------------------------------------------- 优先级判定

_URGENCY_HIGH = ("全员", "整个部门", "所有同事", "多人", "无法办公", "影响办公", "影响工作",
                 "紧急", "马上", "立刻", "宕机", "断网了", "开不了机", "无法开机")
_URGENCY_LOW = ("不急", "有空", "方便时", "顺便", "咨询一下")


def infer_priority(question: str) -> Tuple[str, str]:
    """问题 → 优先级。保守起见默认 MEDIUM（对齐项目字段默认值）。

    Node 3 建单路径调用；结果直接决定 SLA 档位，改这里的特征词等于改 SLA 承诺。
    """
    text = question.lower()
    for m in _URGENCY_HIGH:
        if m in text:
            return "HIGH", f"命中紧急特征「{m}」"
    for m in _URGENCY_LOW:
        if m in text:
            return "LOW", f"命中低优先特征「{m}」"
    return "MEDIUM", "未命中紧急或低优特征，按默认 MEDIUM"


# ---------------------------------------------------------------- 引用守卫

def verify_citation(used_version_ids: List[str],
                    retrieved: List[KnowledgeItem]) -> Tuple[List[str], List[str]]:
    """引用守卫：模型声称依据的 versionId 必须在**本次检索结果**里。

    返回 (保留的, 被剔除的)。被剔除的说明模型编造了依据来源 —— 项目要求此时
    不得声称"依据公司规定"。

    由 Node 3 终审（`_synthesize`）在拿到模型输出后立刻调用，
    是**模型输出流回链路前的最后一道闸**：文案可以听模型的，依据只能听检索的。
    """
    allowed = {item.version_id for item in retrieved}
    kept = [v for v in used_version_ids if v in allowed]
    dropped = [v for v in used_version_ids if v not in allowed]
    return kept, dropped


def duplicate_finding(tickets: List, within_hours: int) -> RuleFinding:
    """重复单拦截的规则结论（文案与工单号一并给出，便于人工复核）。

    Node 3 建单路径调用，产出的是一条 severity=BLOCK 的 finding；
    它和「字段不全」是裁决段里仅有的两个拦截来源。
    """
    ids = "、".join(t.ticket_id for t in tickets[:3])
    return RuleFinding(
        code="DUPLICATE_TICKET",
        message=(f"检测到 {within_hours} 小时内已有同一分类的未结束工单（{ids}），"
                 f"重复建单会被合并，请在该工单下补充信息"),
        severity="BLOCK",
    )


_FILLER = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """去掉模型输出里常见的空白噪声，用于标题等短字段。

    Node 3 生成草稿标题、以及判断描述是否过短时调用；
    输入可能来自模型，所以这里的清理是防御性的，不是格式化。
    """
    return _FILLER.sub(" ", (text or "").strip())