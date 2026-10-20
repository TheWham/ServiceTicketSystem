# -*- coding: utf-8 -*-
"""agent_service 运行配置（环境变量驱动，与 Java consultation-service 的 tools.* 对齐）。

生成模型：OpenAI 兼容端点（base_url / api_key / model），Day16 实测 deepseek-v4-flash 支持 tools。
工具依赖：ticket-service 内部接口（查工单/建单）、consultation-service 知识搜索接口（查知识库）。
"""

import os
from pathlib import Path

# RAG_HOME 缺省回退包上级目录（services/python-retrieval）；须在业务模块导入前设置。
REPO_ROOT = Path(os.environ.get("RAG_HOME", "") or Path(__file__).resolve().parents[1])


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


HOST = os.environ.get("AGENT_SERVICE_HOST", "127.0.0.1")
PORT = int(os.environ.get("AGENT_SERVICE_PORT", "8320"))

# ---- 生成模型（OpenAI 兼容）----
LLM_BASE_URL = os.environ.get("AGENT_LLM_BASE_URL", "")
LLM_API_KEY = os.environ.get("AGENT_LLM_API_KEY", "")
LLM_MODEL = os.environ.get("AGENT_LLM_MODEL", "deepseek-v4-flash")
LLM_TIMEOUT = float(os.environ.get("AGENT_LLM_TIMEOUT", "120"))
MAX_OUTPUT_TOKENS = int(os.environ.get("AGENT_MAX_OUTPUT_TOKENS", "8192"))
# kimi-k3 不接受 temperature；deepseek 接受。默认不传，走模型默认值。
TEMPERATURE = os.environ.get("AGENT_TEMPERATURE", "")

# ---- ReAct 循环 ----
MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "5"))

# ---- 工具依赖 ----
# ticket-service 内部接口基址（工单是 ticket-service 事实源，咨询域不跨库读）
TICKET_SERVICE_BASE_URL = os.environ.get("TICKET_SERVICE_BASE_URL", "")
# consultation-service 知识搜索接口基址（GET /api/v1/knowledge/search）
KNOWLEDGE_SEARCH_BASE_URL = os.environ.get("KNOWLEDGE_SEARCH_BASE_URL", "")
TOOL_TIMEOUT = float(os.environ.get("AGENT_TOOL_TIMEOUT", "8"))
SEARCH_MAX_RESULTS = int(os.environ.get("AGENT_SEARCH_MAX_RESULTS", "5"))
DRAFT_TITLE_MAX = int(os.environ.get("AGENT_DRAFT_TITLE_MAX", "100"))
DRAFT_DESC_MAX = int(os.environ.get("AGENT_DRAFT_DESC_MAX", "2000"))


def model_configured() -> bool:
    """生成模型是否已配置（缺失时接口返回明确的未配置错误）。"""
    return bool(LLM_BASE_URL and LLM_API_KEY)