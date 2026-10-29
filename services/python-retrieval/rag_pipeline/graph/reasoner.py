# -*- coding: utf-8 -*-
"""拓扑事实与 MySQL Docstore 双轨融合推理器。

支持从提问中抽取核心种子实体、Neo4j 原生 Cypher 拓扑多跳因果链遍历、
关联卡片联动 MySQL Docstore 批量回溯、组装双轨 Prompt 并驱动 LLM 综合逻辑演绎。
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from rag_pipeline.docstore import BaseDocstore, build_docstore
from .engine import CARD_ID_PATTERN, Neo4jKnowledgeGraph
from .schema import canonicalize_entity

logger = logging.getLogger(__name__)

# 预设高频业务名词库（用于从 Query 快速捕获种子实体）
COMMON_ENTITY_TERMS: List[str] = [
    "VPN错误691", "错误代码691", "691", "800", "806", "807", "809", "868",
    "SSL VPN", "L2TP", "IPSec", "PPTP", "IKEv2", "VPN",
    "AD域控制器", "AD域账号锁定", "AD域账号", "AD域", "域账号锁定", "域账号", "域控",
    "连续多次输错密码", "输错密码", "密码错误", "被锁定", "凭据失效", "密码失效", "密码过期",
    "密码重置", "账号锁定", "双因子MFA认证", "MFA", "双因素认证",
    "Outlook", "企业微信", "钉钉", "Teams", "OWA", "网页邮箱",
    "移动端邮件客户端旧密码轮询", "手机企业邮箱", "企业邮箱", "手机邮箱", "邮箱凭据失效", "邮件客户端", "邮件",
    "蓝屏", "死机", "内存溢出", "0x0000007B",
    "财务报销系统", "财务系统", "报销系统", "ERP", "CRM", "OA",
    "网络打印机", "打印机", "DNS", "网关",
    "IT网络基础运维组", "IT系统组", "桌面运维支持组", "网络组", "系统组",
]

GENERIC_COARSE_TERMS: Set[str] = {"VPN", "网络", "系统", "客户端", "服务", "服务器", "平台"}


def extract_query_entities(
    query: str, known_entities: Optional[List[str]] = None
) -> List[str]:
    """从自然语言查询中提取种子实体列表。
    
    具备泛化去噪与特化优先机制：当识别到具体故障现象、错误码或明确系统时，
    自动过滤掉过宽的泛化粗粒度实体（如单独的'VPN'、'网络'），避免图谱遍历被无意义背景组件淹没。
    """
    found_entities: Set[str] = set()

    # 1. 提取 ITKB 卡片编号（如 ITKB-VPN-001）
    for cid in CARD_ID_PATTERN.findall(query):
        found_entities.add(cid)

    # 2. 匹配业务词表（按长度倒序，优先长词匹配）
    dict_pool = known_entities or COMMON_ENTITY_TERMS
    for term in sorted(dict_pool, key=len, reverse=True):
        if term.lower() in query.lower():
            canon = canonicalize_entity(term)
            found_entities.add(canon)

    # 3. 泛化实体剪枝：若存在具体实体（如 VPN错误691），移除粗粒度泛化词（如 VPN）
    specific_entities = {e for e in found_entities if e not in GENERIC_COARSE_TERMS}
    active_entities = specific_entities if specific_entities else found_entities

    # 4. 排序：特化故障与关键症状优先排在前面，长词优先
    def entity_priority(e: str) -> tuple:
        is_error = 0 if any(k in e for k in ["错误", "691", "锁定", "失败", "超时", "轮询"]) else 1
        return (is_error, -len(e), e)

    return sorted(active_entities, key=entity_priority)


HYBRID_SYSTEM_PROMPT = """你是一个具备高级拓扑推理能力的智能 IT 客服专家。
请根据提供的【系统客观拓扑事实】和【关联知识库参考正文】，严谨回答用户的 IT 提问。

【回答守则】：
1. 【系统客观拓扑事实】是最高优先级的刚性约束规则，不可违背、不可篡改。如果存在因果链条（如 A导致B、B代签给C、或新规替代旧规），必须按拓扑路径进行多跳逻辑演绎。
2. 结合【关联知识库参考正文】提供具体操作排查步骤。
3. 结构化输出：
   - 🎯【诊断结论】：直接给出问题根因或终审责任人；
   - 🔗【证据链推导】：分步陈述事实推导步骤（第1跳、第2跳...）；
   - 🛠️【具体处置步骤】：给出明确可执行的修复指南。
"""


class GraphEnhancedReasoner:
    """拓扑事实与 Docstore 双轨融合推理引擎。"""

    def __init__(
        self,
        kg: Neo4jKnowledgeGraph,
        docstore: Optional[BaseDocstore] = None,
        client: Any = None,
        model: str = "deepseek-v4.1-flash",
    ) -> None:
        self.kg = kg
        self.docstore = docstore or build_docstore()
        self.client = client
        self.model = model

    def retrieve_multihop_context(
        self,
        query: str,
        seed_entities: Optional[List[str]] = None,
        max_hops: int = 2,
    ) -> Dict[str, Any]:
        """执行双轨检索：图谱 BFS 事实抽取 + 关联卡片联动 MySQL Docstore 批量回溯。"""
        # 1. 确定种子实体
        seeds = seed_entities or extract_query_entities(query)

        # 2. 轨 A: 图谱子图 BFS 遍历
        graph_facts = self.kg.extract_subgraph_facts(
            seeds, max_hops=max_hops, prune_deprecated=True
        )

        # 3. 轨 B: 从子图中发现所有关联卡片 ID
        associated_card_ids = self.kg.get_associated_card_ids(
            seeds, max_hops=max_hops, prune_deprecated=True
        )

        # 4. 联动 MySQL Docstore 批量拉取父卡全文
        docstore_cards: Dict[str, str] = {}
        if self.docstore and associated_card_ids:
            docstore_cards = self.docstore.mget(associated_card_ids)

        return {
            "query": query,
            "seed_entities": seeds,
            "graph_facts": graph_facts,
            "associated_card_ids": associated_card_ids,
            "docstore_cards": docstore_cards,
        }

    def build_hybrid_prompt(
        self, query: str, context: Dict[str, Any]
    ) -> str:
        """组装包含刚性因果网与参考全文的混合 Prompt。"""
        facts_text = "\n".join(
            f"{i+1}. {f}" for i, f in enumerate(context.get("graph_facts", []))
        )
        if not facts_text:
            facts_text = "(未提取到显式图谱路径，以通用规则为准)"

        cards_sections: List[str] = []
        for cid, content in context.get("docstore_cards", {}).items():
            cards_sections.append(f"### 【卡片 {cid} 参考正文】\n{content}\n")
        cards_text = "\n".join(cards_sections) if cards_sections else "(暂无关联卡片正文)"

        prompt = f"""【系统客观拓扑事实（最高优先级，不可违背）】：
{facts_text}

【关联知识库参考正文】：
{cards_text}

【用户问题】：
{query}

请基于上述拓扑因果与知识卡片，进行多跳逻辑演绎并输出准确答复："""
        return prompt

    def answer_query(
        self,
        query: str,
        seed_entities: Optional[List[str]] = None,
        max_hops: int = 2,
    ) -> Dict[str, Any]:
        """完整端到端多跳推理问答。"""
        context = self.retrieve_multihop_context(
            query, seed_entities=seed_entities, max_hops=max_hops
        )
        prompt = self.build_hybrid_prompt(query, context)

        final_answer = ""
        if self.client:
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": HYBRID_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    timeout=30,
                )
                final_answer = resp.choices[0].message.content
            except Exception as e:
                logger.error("LLM 多跳推理生成异常: %s", e)
                final_answer = f"(推理生成降级，未能获取 LLM 回复: {e})"
        else:
            final_answer = "【模拟推理结果】：已成功抽取图谱事实与关联父卡，因未配置 LLM 客户端跳过终答生成。"

        return {
            "query": query,
            "context": context,
            "prompt": prompt,
            "answer": final_answer,
        }
