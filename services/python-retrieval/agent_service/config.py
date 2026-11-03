# -*- coding: utf-8 -*-
"""agent_service 运行配置（环境变量驱动，与 Java consultation-service 的 tools.* 对齐）。

生成模型：OpenAI 兼容端点（base_url / api_key / model），Day16 实测 deepseek-v4-flash 支持 tools。
工具依赖：ticket-service 内部接口（查工单/建单）、consultation-service 知识搜索接口（查知识库）。
"""

import os
from pathlib import Path
from typing import Dict

# RAG_HOME 缺省回退包上级目录（services/python-retrieval）；须在业务模块导入前设置。
REPO_ROOT = Path(os.environ.get("RAG_HOME", "") or Path(__file__).resolve().parents[1])


def _load_dotenv() -> Dict[str, str]:
    """解析 REPO_ROOT/.env（与 rag_pipeline/config.py 同一约定）：进程环境变量优先，.env 兜底。"""
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return {}
    kv: Dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        kv[k.strip()] = v.strip().strip('"').strip("'")
    return kv


_DOTENV = _load_dotenv()


def _cfg(name: str, dotenv_key: str = "", default: str = "") -> str:
    """取值顺序：环境变量 > .env > 默认。"""
    return os.environ.get(name) or (_DOTENV.get(dotenv_key, "") if dotenv_key else "") or default


HOST = os.environ.get("AGENT_SERVICE_HOST", "127.0.0.1")
PORT = int(os.environ.get("AGENT_SERVICE_PORT", "8320"))

# ---- 生成模型（OpenAI 兼容）----
# .env 回退用的是仓库根通用的 LLM_* 键（LLM_CLEAN_MODEL 即 deepseek，与 rag_pipeline 同源），
# 所以 rag_service 与 agent_service 共享一份 .env，无需各自维护。
LLM_BASE_URL = _cfg("AGENT_LLM_BASE_URL", "LLM_BASE_URL")
LLM_API_KEY = _cfg("AGENT_LLM_API_KEY", "LLM_API_KEY")
LLM_MODEL = _cfg("AGENT_LLM_MODEL", "LLM_CLEAN_MODEL", "deepseek-v4-flash")
LLM_TIMEOUT = float(os.environ.get("AGENT_LLM_TIMEOUT", "120"))
MAX_OUTPUT_TOKENS = int(os.environ.get("AGENT_MAX_OUTPUT_TOKENS", "8192"))
# kimi-k3 不接受 temperature；deepseek 接受。默认不传，走模型默认值。
TEMPERATURE = os.environ.get("AGENT_TEMPERATURE", "")

# ---- 智能体编排模式 (supervisor: 主从多智能体与安全护栏 | react: 经典单智能体循环) ----
AGENT_MODE = os.environ.get("AGENT_MODE", "supervisor").strip().lower()

# ---- ReAct 循环 ----
MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "5"))

# ---- 工具依赖 ----
# ticket-service 内部接口基址（工单是 ticket-service 事实源，咨询域不跨库读）
# 默认对齐标准部署拓扑（ticket:8201 / consultation:8301），环境变量可覆盖。
TICKET_SERVICE_BASE_URL = _cfg("TICKET_SERVICE_BASE_URL", default="http://127.0.0.1:8201")
# consultation-service 知识搜索接口基址（GET /api/v1/knowledge/search）
KNOWLEDGE_SEARCH_BASE_URL = _cfg("KNOWLEDGE_SEARCH_BASE_URL", default="http://127.0.0.1:8301")
TOOL_TIMEOUT = float(os.environ.get("AGENT_TOOL_TIMEOUT", "8"))
SEARCH_MAX_RESULTS = int(os.environ.get("AGENT_SEARCH_MAX_RESULTS", "5"))
DRAFT_TITLE_MAX = int(os.environ.get("AGENT_DRAFT_TITLE_MAX", "100"))
DRAFT_DESC_MAX = int(os.environ.get("AGENT_DRAFT_DESC_MAX", "2000"))


def model_configured() -> bool:
    """生成模型是否已配置（缺失时接口返回明确的未配置错误）。"""
    return bool(LLM_BASE_URL and LLM_API_KEY)
# ---- Langfuse APM（可关闭；不配置时零依赖降级，不阻塞业务） ----
def _langfuse_bool(name: str, default: bool) -> bool:
    return _cfg(name, name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _langfuse_host() -> str:
    # 兼容两类常见变量名：SDK 文档用 LANGFUSE_HOST，项目 .env 用 LANGFUSE_BASE_URL。
    return (os.environ.get("LANGFUSE_HOST")
            or _DOTENV.get("LANGFUSE_HOST", "")
            or os.environ.get("LANGFUSE_BASE_URL")
            or _DOTENV.get("LANGFUSE_BASE_URL", "")
            or "https://cloud.langfuse.com")


LANGFUSE_ENABLED = _langfuse_bool("LANGFUSE_ENABLED", False)
LANGFUSE_HOST = _langfuse_host()
LANGFUSE_PUBLIC_KEY = _cfg("LANGFUSE_PUBLIC_KEY", "LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = _cfg("LANGFUSE_SECRET_KEY", "LANGFUSE_SECRET_KEY")
LANGFUSE_ENV = _cfg("LANGFUSE_ENV", "LANGFUSE_ENV",
                    default=os.environ.get("SPRING_PROFILES_ACTIVE", "dev"))
LANGFUSE_TIMEOUT_SECONDS = float(
    _cfg("LANGFUSE_TIMEOUT_SECONDS", "LANGFUSE_TIMEOUT_SECONDS", "5"))
# 默认 false：只上报指标与状态，不上传 prompt/回答/知识正文。
LANGFUSE_INCLUDE_CONTENT = _langfuse_bool("LANGFUSE_INCLUDE_CONTENT", False)
