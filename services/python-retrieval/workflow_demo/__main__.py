# -*- coding: utf-8 -*-
"""`python -m workflow_demo` 启动演示服务。"""

import uvicorn

from . import config as cfg


def main() -> None:
    print(f"workflow-demo 启动中 → http://{cfg.HOST}:{cfg.PORT}")
    if not cfg.model_configured():
        print("  · 未配置 AGENT_LLM_BASE_URL / AGENT_LLM_API_KEY，将走确定性兜底"
              "（token 标记为 estimated）")
    uvicorn.run("workflow_demo.app:app", host=cfg.HOST, port=cfg.PORT, log_level="info")


if __name__ == "__main__":
    main()