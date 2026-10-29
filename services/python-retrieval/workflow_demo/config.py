# -*- coding: utf-8 -*-
"""workflow_demo 运行配置（环境变量驱动）。

模型凭据的读取顺序，与项目既有约定保持一致（`rag_pipeline.config` 同款）：
    进程环境变量 > 仓库 .env
键名两套都认：项目全局的 `LLM_*`（.env 里配的就是这套）优先于
`agent_service` 专用的 `AGENT_LLM_*`。这样同一台机器上配一次，三个服务都能用。
"""

import os
from functools import lru_cache
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent           # <repo>/services/python-retrieval/workflow_demo
SERVICE_ROOT = PKG_DIR.parent                       # <repo>/services/python-retrieval
REPO_ROOT = Path(os.environ.get("RAG_HOME", "") or SERVICE_ROOT.parent.parent)  # 仓库根
# .env 可能落在服务目录或仓库根（本仓库是后者）；两处都找
_DOTENV_CANDIDATES = (REPO_ROOT / ".env", SERVICE_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@lru_cache(maxsize=1)
def _load_dotenv() -> dict:
    """解析 .env 键值（.env 已被 .gitignore 忽略，key 绝不入库）。"""
    for env_file in _DOTENV_CANDIDATES:
        if not env_file.exists():
            continue
        kv: dict = {}
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip().strip('"').strip("'")
        if kv:
            return kv
    return {}


def _resolve(*names: str, default: str = "") -> str:
    """按名字依次取：进程环境变量 > .env > 默认值。"""
    dotenv = _load_dotenv()
    for name in names:
        value = os.environ.get(name) or dotenv.get(name, "")
        if value:
            return value
    return default


# ---- HTTP 服务 ----
HOST = os.environ.get("WORKFLOW_DEMO_HOST", "127.0.0.1")
PORT = int(os.environ.get("WORKFLOW_DEMO_PORT", "8330"))

# ---- 生成模型（OpenAI 兼容）----
# 本 demo 只需要普通对话补全，不需要原生 tools，所以直接用 LLM_CHAT_MODEL
LLM_BASE_URL = _resolve("AGENT_LLM_BASE_URL", "LLM_BASE_URL")
LLM_API_KEY = _resolve("AGENT_LLM_API_KEY", "LLM_API_KEY")
LLM_MODEL = _resolve("AGENT_LLM_MODEL", "LLM_CHAT_MODEL", default="deepseek-v4-flash")
LLM_TIMEOUT = float(os.environ.get("AGENT_LLM_TIMEOUT", "60"))
MAX_OUTPUT_TOKENS = int(os.environ.get("AGENT_MAX_OUTPUT_TOKENS", "1024"))
# 有的模型（如 kimi-k3）不接受 temperature。默认不传，走模型默认值；
# 要固定随机性再显式设置（与 agent_service 的处理一致）。
TEMPERATURE = _resolve("AGENT_TEMPERATURE", "WORKFLOW_DEMO_TEMPERATURE")

# ---- 本地种子库 ----
DB_PATH = Path(os.environ.get("WORKFLOW_DEMO_DB", "") or (PKG_DIR / "workflow_demo.db"))
SCHEMA_PATH = PKG_DIR / "schema.sql"

# ---- 业务规则参数 ----
# 重复单判定窗口：同一个人、同一分类、窗口内未关闭的工单视为重复
DUPLICATE_WINDOW_HOURS = int(os.environ.get("WORKFLOW_DEMO_DUPLICATE_WINDOW_HOURS", "24"))
RETRIEVAL_TOP_K = int(os.environ.get("WORKFLOW_DEMO_TOP_K", "3"))

# ---- 链路追踪 ----
# 费率必须按实际模型定价改，默认值只是占位（Day17 讲义沿用价）。
# 成本 = 输入token/1e6 * PRICE_IN + 输出token/1e6 * PRICE_OUT
PRICE_INPUT_PER_M = float(os.environ.get("TRACE_PRICE_INPUT_PER_M", "0.15"))
PRICE_OUTPUT_PER_M = float(os.environ.get("TRACE_PRICE_OUTPUT_PER_M", "0.60"))
# 单个 span 的 input/output 摘要在响应里保留的最大字符数（避免把整段 prompt 塞给前端）
BRIEF_MAX_CHARS = int(os.environ.get("TRACE_BRIEF_MAX_CHARS", "240"))

# ---- 模型调用的输出长度上限 ----
# 注意：`max_tokens` 限制的是**思维链 + 正文的总和**，不只是正文。
# 推理模型（如 kimi-k3）的 reasoning_content 会先吃掉大部分额度，按非推理模型的
# 直觉取值会把正文挤没：实测 16 时模型每次都返回空串（路由静默退回规则路由）、
# 512 时 JSON 被拦腰截断（员工拿到半截 JSON）。这里按「思维链留够 + 正文够用」给。
ROUTER_MAX_OUTPUT_TOKENS = int(os.environ.get("WORKFLOW_DEMO_ROUTER_MAX_TOKENS", "512"))
# 终审文案：答复本身要求 200 字以内，但额度得容得下思维链与 JSON 外壳
SYNTH_MAX_OUTPUT_TOKENS = int(os.environ.get("WORKFLOW_DEMO_SYNTH_MAX_TOKENS", "4096"))

# 请求体里 question 的最大长度（对齐 rag_service 契约的 8000）
QUESTION_MAX_CHARS = 8000


def model_configured() -> bool:
    """生成模型是否已配置；未配置时工作流走确定性兜底并如实标注估算 token。"""
    return bool(LLM_BASE_URL and LLM_API_KEY)