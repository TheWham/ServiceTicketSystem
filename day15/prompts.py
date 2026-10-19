# -*- coding: utf-8 -*-
"""day15 受约束生成（grounding）提示词与拒答文案。

STRICT_GROUNDING_PROMPT 三大军规（对齐 docs/Day15 第三节）：
  1. 严格事实绑定 —— 只依据给定参考片段作答，不得引入任何外部知识；
  2. 诚实拒答     —— 参考片段未记载则明说，绝不编造；
  3. 精准溯源     —— 关键结论后紧跟 [来源: 卡片id - 章节名] 角标。
"""

from typing import Dict, List

STRICT_GROUNDING_PROMPT = """你是企业 IT 服务台的知识库问答助手。你只能依据下面提供的【参考片段】回答用户问题，并严格遵守三条铁律：

【铁律一 · 严格事实绑定】
- 只使用【参考片段】中出现的事实、步骤、命令、参数、数值、错误码作答，不得引入任何片段之外的知识，不得凭常识推测或补全。

【铁律二 · 诚实拒答】
- 若【参考片段】中没有能回答该问题的内容，直接回答：「抱歉，当前知识库中未记载相关内容，建议咨询相关主管部门。」不得强行作答。

【铁律三 · 精准溯源】
- 每给出一个关键结论或处置步骤，就在该结论后紧跟角标：[来源: 卡片id - 章节名]。
- 角标中的「卡片id」必须**逐字符照抄**参考片段标注的卡片 id（含 ASCII 连字符，如 ITKB-ACC-002），
  严禁改用「ITKB · ACC-002」这类带空格/圆点的变体或被改写的大小写。
- 「章节名」取自片段中的二级标题（如 常见根因、员工自助排查）。
- 正确示例：[来源: ITKB-ACC-002 - 常见根因]。
- 不得虚构卡片 id 或章节名；一个结论可附多个角标。

输出要求：使用简洁的中文、可用 Markdown 列点；不要输出与问题无关的寒暄。"""


def build_user_message(question: str, contexts: List[Dict[str, str]]) -> str:
    """把命中的父卡片段拼装成 user message。

    contexts 每项：{card_id, title, version, status, source_file, content}
    """
    blocks = []
    for i, c in enumerate(contexts, 1):
        head = (f"【参考片段 {i}】卡片id: {c.get('card_id', '')} | 标题: {c.get('title', '')}"
                f" | 版本: {c.get('version', '')} | 状态: {c.get('status', '')}"
                f" | 来源文件: {c.get('source_file', '')}")
        blocks.append(f"{head}\n{c.get('content', '').strip()}")
    body = "\n\n".join(blocks)
    return (f"以下是知识库检索到的参考片段：\n\n{body}\n\n"
            f"请仅依据以上参考片段回答用户问题，并按格式附上角标，"
            f"卡片 id 逐字符照抄（如 [来源: ITKB-ACC-002 - 常见根因]）。\n\n"
            f"用户问题：{question}")


REFUSAL_TEXT = "抱歉，当前知识库中未记载相关内容，建议咨询相关主管部门。"

OFFLINE_TEXT = ("⚠️ 离线模式：LLM 生成不可用，仅返回检索命中的知识片段（下方来源列表），"
                "未生成自由文本答案，避免编造内容。")
