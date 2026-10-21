# ==============================================================================
# Python AI 服务镜像：一个镜像承载 agent_service（Function Calling 智能体）。
# 用 command 切换入口（rag_service 走 .env 里 RAG_RETRIEVAL_PROVIDER=python 时另起）；
#   docker build -t it-ticket-python-ai services/python-retrieval
#   docker run --rm -p 8320:8320 it-ticket-python-ai python -m agent_service
#
# agent_service 只依赖 fastapi/uvicorn/pydantic/openai/httpx（见其 requirements.txt），
# 不导入 rag_pipeline，因此镜像保持精简。
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    RAG_HOME=/app

# 依赖先装（层缓存：需求不变则不重装）
COPY agent_service/requirements.txt /app/agent_service/requirements.txt
RUN pip install --no-cache-dir -r /app/agent_service/requirements.txt

# 源码（含 rag_service.contract 的包络定义与 agent_service 本体）
COPY . /app

EXPOSE 8310 8320

# 默认入口：Function Calling 智能体（绑定 0.0.0.0 由 AGENT_SERVICE_HOST 注入）
CMD ["python", "-m", "agent_service"]