# -*- coding: utf-8 -*-
"""入口：python -m rag_service

默认 127.0.0.1:8310、单进程 uvicorn（workers=1，装配体是进程级单例）。
环境变量：RAG_SERVICE_HOST / RAG_SERVICE_PORT / RAG_SERVICE_LOG_LEVEL / RAG_HOME。
"""

import os
import sys
from pathlib import Path


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # Windows 控制台 GBK → UTF-8
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    # RAG_HOME 缺省回退包上级目录（demo 仓库根）；部署到别处时由外部注入。
    # 必须在 import rag_pipeline 之前设置（config.py 在导入期读取 RAG_HOME）。
    os.environ.setdefault("RAG_HOME", str(Path(__file__).resolve().parents[1]))

    host = os.environ.get("RAG_SERVICE_HOST", "127.0.0.1")
    port = int(os.environ.get("RAG_SERVICE_PORT", "8310"))

    import uvicorn

    from .app import create_app

    uvicorn.run(create_app(), host=host, port=port, workers=1,
                log_level=os.environ.get("RAG_SERVICE_LOG_LEVEL", "info"))


if __name__ == "__main__":
    main()
