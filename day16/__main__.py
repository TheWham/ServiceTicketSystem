# -*- coding: utf-8 -*-
"""入口：python -m day16

默认 127.0.0.1:8321、单进程 uvicorn（与 day15 的 8320 错开）。
环境变量：DAY16_HOST / DAY16_PORT / DAY16_OFFLINE / RAG_HOME。
"""

import os
import sys
from pathlib import Path


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # Windows 控制台 GBK → UTF-8
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    # RAG_HOME 缺省回退包上级目录（仓库根）；必须在 import rag_pipeline 之前设置。
    os.environ.setdefault("RAG_HOME", str(Path(__file__).resolve().parents[1]))

    from . import config as dcfg

    import uvicorn

    from .api import create_app

    uvicorn.run(create_app(), host=dcfg.HOST, port=dcfg.PORT, workers=1,
                log_level=os.environ.get("DAY16_LOG_LEVEL", "info"))


if __name__ == "__main__":
    main()
