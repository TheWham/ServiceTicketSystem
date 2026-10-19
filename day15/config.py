# -*- coding: utf-8 -*-
"""day15 运行参数（仅本层运行用；检索参数一律出自 configs/pipeline.yaml，此处不重复）。

环境变量：
  DAY15_HOST / DAY15_PORT     — 服务绑定地址（默认 127.0.0.1:8320，与 rag_service 的 8310 错开）
  DAY15_OFFLINE=1             — 强制离线：跳过一切 LLM 生成调用（彩排断网用）
  DAY15_LLM_TIMEOUT           — 生成调用超时秒数（默认 30）
  DAY15_LLM_RETRIES           — 生成重试次数（默认 2）
  DAY15_ANSWER_CACHE_DIR      — 答案磁盘缓存目录（默认 artifacts/day15/.answer_cache）
  DAY15_REPORT_DIR            — 回归报告落盘目录（默认 artifacts/day15）
"""

import os
from pathlib import Path

from rag_pipeline.config import REPO_ROOT


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


HOST = os.environ.get("DAY15_HOST", "127.0.0.1")
PORT = int(os.environ.get("DAY15_PORT", "8320"))

OFFLINE = _env_bool("DAY15_OFFLINE", False)

LLM_TIMEOUT = float(os.environ.get("DAY15_LLM_TIMEOUT", "30"))
LLM_RETRIES = int(os.environ.get("DAY15_LLM_RETRIES", "2"))

ANSWER_CACHE_DIR = Path(os.environ.get("DAY15_ANSWER_CACHE_DIR")
                        or (REPO_ROOT / "artifacts" / "day15" / ".answer_cache"))
REPORT_DIR = Path(os.environ.get("DAY15_REPORT_DIR")
                  or (REPO_ROOT / "artifacts" / "day15"))
