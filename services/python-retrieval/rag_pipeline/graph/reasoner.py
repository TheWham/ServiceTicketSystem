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

GENERIC_COARSE_TERMS: Set[str] = {"VPN", "网络", "系统", "客户端", "服务", "服务器", "平台"}


def extract_query_entities(
    query: str,
    candidate_nodes: Optional[Any] = None,
    kg: Optional[Any] = None,
    known_entities: Optional[Any] = None,
) -> List[str]:
    """【链路二 · 步骤 2 种子实体提取与泛化去噪】extract_query_entities(query, candidate_nodes, kg)
    
    输入：自然语言查询 query，以及动态实体候选池 candidate_nodes（源自 Neo4j 数据库）。
    动作：
      1. 正则匹配：抓取提问中的知识卡片编号（如 ITKB-VPN-001）；
      2. 倒序长词匹配：基于 Neo4j 动态实体词池进行最大前向长词扫描；
      3. 别名消歧归一：反查 ENTITY_ALIAS_MAP 映射为规范实体（如 '691' -> 'VPN错误691'）；
      4. 泛化实体去噪剪枝：识别到具体故障（如 'VPN错误691'）时，自动剥离无意义粗粒度词（如 'VPN'、'网络'）；
      5. 优先级排序：特化故障与关键症状排在前面。
    返回：精准、去噪后的种子实体列表（如 ['VPN错误691']）。
    """
    found_entities: Set[str] = set()

    # 步骤 2.1: 提取 ITKB 卡片编号（如 ITKB-VPN-001）
    for cid in CARD_ID_PATTERN.findall(query):
        found_entities.add(cid)

    # 步骤 2.2: 动态候选池解析：优先使用传入的 candidate_nodes，其次尝试从 kg 实例动态获取
    pool_source = candidate_nodes if candidate_nodes is not None else known_entities
    if pool_source is None and kg is not None and hasattr(kg, "get_all_node_names"):
        pool_source = kg.get_all_node_names()

    dict_pool = set(pool_source or [])

    # 步骤 2.3: 匹配业务动态节点池（按长度倒序，长词优先匹配）
    for term in sorted(dict_pool, key=len, reverse=True):
        if not term:
            continue
        if term.lower() in query.lower():
            canon = canonicalize_entity(term)
            found_entities.add(canon)

    # 步骤 2.4: 别名消歧反查：若口语别名出现在提问中，映射至标准规范实体
    from .schema import ENTITY_ALIAS_MAP
    for alias, target in sorted(ENTITY_ALIAS_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if alias.lower() in query.lower():
            if not dict_pool or target in dict_pool:
                found_entities.add(target)

    # 步骤 2.5: 泛化实体剪枝去噪：若存在具体故障（如 VPN错误691），移除粗粒度泛化词（如 VPN、网络）
    specific_entities = {e for e in found_entities if e not in GENERIC_COARSE_TERMS}
    active_entities = specific_entities if specific_entities else found_entities

    # 步骤 2.6: 优先级排序：特化故障与关键症状优先排在前面
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
        """【链路二 · 步骤 3 双轨检索器】retrieve_multihop_context(query, seed_entities, max_hops)
        
        输入：用户提问 query，种子实体列表 seed_entities，最大跳数 max_hops（默认2）。
        动作：
          1. 确定种子：调用 extract_query_entities 获取精准种子实体；
          2. 轨 A（图谱拓扑事实）：调用 kg.extract_subgraph_facts 执行 Cypher 2-Hop 遍历与 is_deprecated 剪枝；
          3. 轨 B（顺藤摸瓜回溯父卡）：调用 kg.get_associated_card_ids 获取子图涉及的 ITKB 卡号；
          4. 联动拉取正文：调用 docstore.mget 批量从 MySQL Docstore 中取出完整父卡未切片正文。
        返回：包含 graph_facts, associated_card_ids, docstore_cards 的综合上下文字典。
        """
        # 步骤 3.1: 确定查询种子实体
        seeds = seed_entities or extract_query_entities(query, kg=self.kg)

        # 步骤 3.2【轨 A】: Neo4j Cypher 原生 1~2 Hop 拓扑遍历与废弃版本剪枝
        graph_facts = self.kg.extract_subgraph_facts(
            seeds, max_hops=max_hops, prune_deprecated=True
        )

        # 步骤 3.3【轨 B】: 从子图命中的节点中反查关联的知识卡片编号 (ITKB-xxx)
        associated_card_ids = self.kg.get_associated_card_ids(
            seeds, max_hops=max_hops, prune_deprecated=True
        )

        # 步骤 3.4: 联动 MySQL Docstore 批量拉取完整父卡未切片正文 (解决 Chunk 碎片问题)
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
