# -*- coding: utf-8 -*-
"""入口：python -m agent_service

默认 127.0.0.1:8320、单进程 uvicorn。
环境变量：AGENT_SERVICE_HOST / AGENT_SERVICE_PORT / AGENT_SERVICE_LOG_LEVEL / RAG_HOME。
"""

import os
import sys
from pathlib import Path


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")     # Windows 控制台 GBK → UTF-8
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    # RAG_HOME 缺省回退包上级目录（services/python-retrieval）；须在业务模块导入前设置。
    os.environ.setdefault("RAG_HOME", str(Path(__file__).resolve().parents[1]))

    from . import config as acfg

    import uvicorn

    from .app import create_app

    uvicorn.run(create_app(), host=acfg.HOST, port=acfg.PORT, workers=1,
                log_level=os.environ.get("AGENT_SERVICE_LOG_LEVEL", "info"))


if __name__ == "__main__":
    main()