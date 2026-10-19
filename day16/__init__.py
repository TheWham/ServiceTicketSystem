# -*- coding: utf-8 -*-
"""day16 — 企业级单 Agent 工具交付：Function Calling + 安全 Text2SQL + 外部 API 网关。

与 RAG 检索内核（rag_pipeline/rag_service）无耦合，只复用 rag_pipeline.config 的
load_llm_config 读取 .env 模型配置。核心构件：
- SafeText2SQLEngine（text2sql.py）：五重安全防线的只读 SQL 拦截器；
- ExternalAPIGateway（gateway.py）：超时 + 指数退避 + 抖动的外部 API 调用网关；
- EnterpriseReActAgent（agent.py）：原生 tools 协议决策中枢 + 确定性沙箱兜底。
"""

from .agent import AGENT_TOOLS_SCHEMA, EnterpriseReActAgent

__all__ = ["EnterpriseReActAgent", "AGENT_TOOLS_SCHEMA"]
