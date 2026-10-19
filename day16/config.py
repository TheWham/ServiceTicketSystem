# -*- coding: utf-8 -*-
"""day16 运行参数（本层运行参数 + 真实业务库连接；LLM 配置出自 .env 的 load_llm_config）。

Day16 是「单 Agent 工具交付」：Function Calling 协议 + 安全 Text2SQL + 外部 API 网关。
Text2SQL 查询的是企业真实业务库 it_ticket_system（IT 服务工单系统，MySQL 8），
与 RAG 检索内核（rag_pipeline/rag_service）无耦合。

环境变量：
  DAY16_HOST / DAY16_PORT     — 服务绑定地址（默认 127.0.0.1:8321，与 day15 的 8320 错开）
  DAY16_OFFLINE=1             — 强制沙箱：跳过一切 LLM Function Calling 调用（断网演示用）
  DAY16_LLM_TIMEOUT           — 单次 LLM 调用超时秒数（默认 30）
  DAY16_LLM_RETRIES           — LLM 调用重试次数（默认 2）
  DAY16_REPORT_DIR            — 验收报告落盘目录（默认 artifacts/day16）
  DAY16_DB_HOST / _PORT / _NAME / _USER / _PASSWORD   — 真实业务库连接（默认对齐 it_ticket_system）
"""

import os
from pathlib import Path

from rag_pipeline.config import REPO_ROOT


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


HOST = os.environ.get("DAY16_HOST", "127.0.0.1")
PORT = int(os.environ.get("DAY16_PORT", "8321"))

OFFLINE = _env_bool("DAY16_OFFLINE", False)

LLM_TIMEOUT = float(os.environ.get("DAY16_LLM_TIMEOUT", "30"))
LLM_RETRIES = int(os.environ.get("DAY16_LLM_RETRIES", "2"))

# Agent 推理模型：空 = 取 .env 的 LLM_CLEAN_MODEL（默认 deepseek-v4-flash）
AGENT_MODEL = os.environ.get("DAY16_AGENT_MODEL", "")

REPORT_DIR = Path(os.environ.get("DAY16_REPORT_DIR")
                  or (REPO_ROOT / "artifacts" / "day16"))

# ---- 真实业务库连接（IT 服务工单系统 MySQL）----
DB_HOST = os.environ.get("DAY16_DB_HOST", "120.92.138.195")
DB_PORT = int(os.environ.get("DAY16_DB_PORT", "3306"))
DB_NAME = os.environ.get("DAY16_DB_NAME", "it_ticket_system")
DB_USER = os.environ.get("DAY16_DB_USER", "root")
DB_PASSWORD = os.environ.get("DAY16_DB_PASSWORD", "clt123456")
