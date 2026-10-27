# -*- coding: utf-8 -*-
"""入口：python -m analytics_service

默认 127.0.0.1:8340、单进程 uvicorn。
环境变量：ANALYTICS_SERVICE_HOST / ANALYTICS_SERVICE_PORT /
          ANALYTICS_SERVICE_LOG_LEVEL / RAG_HOME。
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

    from . import config as cfg

    import uvicorn

    from .app import create_app

    print(f"analytics-service 启动中 → http://{cfg.HOST}:{cfg.PORT}")
    if not cfg.model_configured():
        print("  · 未配置 ANALYTICS_LLM_* / LLM_*，归因叙事将走确定性模板"
              "（token 标记为 estimated），聚合与门禁不受影响")
    print(f"  · 词表：{cfg.TAXONOMY_PATH}")
    print(f"  · 工单取数：{cfg.TICKET_SERVICE_BASE_URL}"
          f"/api/internal/tickets/analytics/scan")

    uvicorn.run(create_app(), host=cfg.HOST, port=cfg.PORT, workers=1,
                log_level=os.environ.get("ANALYTICS_SERVICE_LOG_LEVEL", "info"))


if __name__ == "__main__":
    main()