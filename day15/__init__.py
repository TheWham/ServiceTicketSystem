# -*- coding: utf-8 -*-
"""day15 — 企业知识库服务层：检索 + 受约束生成（grounding）+ 结构化溯源。

检索底座完全复用 rag_service.assembly.ServiceAssembly（同一条装配路径：
rag_pipeline.config.load_config → build_chunker → 指纹校验 → IndustrialHybridRetriever），
本层只在其上加：STRICT_GROUNDING_PROMPT 生成、Citation 角标抽取、Web 演示出口。
"""

from .service import EnterpriseKnowledgeService

__all__ = ["EnterpriseKnowledgeService"]
