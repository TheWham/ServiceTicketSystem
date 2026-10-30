# Python 检索服务（rag_service）启动指南

> 端口 `8310`，由 Java rag-service（:8302）通过 HTTP 调用。
> 详细运维与回归见 `docs/runbook-python-retrieval.md`。

## 前置条件

- **Python ≥ 3.11**
- 依赖已在虚拟环境安装：
  ```bash
  pip install -r rag_service/requirements.txt
  # fastapi / uvicorn[standard] / pydantic>=2
  ```
  如需查询改写（LLM）与精排（rerank），还需：
  ```bash
  pip install openai httpx PyYAML
  ```
- **预建产物必须存在**（否则启动 fail-fast）：
  - `artifacts/indexing/chroma_wiki_structured/`（向量库 + manifest）
  - `artifacts/output/wiki/*.md`（语料，指纹须与向量库 manifest 匹配）

## 环境配置

复制 `.env.example`（或向团队要）为 `.env`，填入模型凭据：

```bash
# ---- LLM（对话/清洗，用于查询改写）----
LLM_API_KEY=sk-...
LLM_BASE_URL=https://kspmas.ksyun.com/v1
LLM_CHAT_MODEL=deepseek-v4-flash
LLM_CLEAN_MODEL=deepseek-v4-flash

# ---- Embedding（向量化）----
EMBED_API_KEY=sk-...
EMBED_BASE_URL=https://kspmas.ksyun.com/v1
EMBED_MODEL=qwen3-embedding-8b

# ---- Rerank（重排）----
RERANK_API_KEY=sk-...
RERANK_BASE_URL=https://kspmas.ksyun.com/v1
RERANK_MODEL=qwen3-reranker-8b

# ---- Neo4j 图数据库（GraphRAG，默认 bolt://localhost:7687）----
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j123456
```

> `.env` 在 `services/python-retrieval/` 目录下，`RAG_HOME` 指向这里时自动读取。
> `.env` 已被 `.gitignore` 忽略，不会入库。

## 启动

```bash
cd services/python-retrieval

# 必须在虚拟环境中（激活后）
RAG_HOME=$PWD python -m rag_service
# Windows PowerShell: $env:RAG_HOME = (Get-Location).Path; python -m rag_service
```

服务默认监听 `127.0.0.1:8310`。

启动时依次装配：BM25 倒排索引 → Cross-Encoder 精排 → 查询改写器 → wiki 映射。
启动日志应看到 `✅ [3/3] 双路混合检索与重排引擎装配就绪！`。

## 验证

```bash
# 健康检查（不抢检索锁）
curl http://127.0.0.1:8310/api/health
# 期望 status=UP, chunkCount>0

# 检索冒烟
curl -X POST http://127.0.0.1:8310/api/v1/rag/retrievals \
  -H "Content-Type: application/json" \
  -d '{"question":"打印机无法打印怎么办","topK":3}'
# 期望 code=0, items 非空, reliable=true
```

## 连接 Java rag-service（:8302）

Python 返回的 `articleId` 必须能在 Java MySQL `knowledge_article` 表中查到
`PUBLISHED` 且 `currentVersionId` 匹配。首次部署需要灌库生成映射：

```bash
# Java rag-service 已启动后运行
python tools/sync_wiki_to_rag_service.py
# 产出 data/wiki_article_mapping.json
```

映射缺失时 `/api/health` 显示 `DEGRADED`，Java 复核会滤空所有结果
（表现为 8310 有结果、8302 空）。

## 常见问题

| 现象 | 原因 | 解法 |
|---|---|---|
| 启动报"缺少 manifest" | 向量库未构建或路径错 | 确认 `artifacts/indexing/chroma_wiki_structured/manifest.json` 存在 |
| 启动报"指纹不一致" | Wiki 卡片与向量库不同步 | 重跑 `python -m rag_pipeline.pipelines.indexing` |
| `/api/health` status=DEGRADED | `wiki_article_mapping.json` 缺失 | 跑 `python tools/sync_wiki_to_rag_service.py` |
| 检索返回空（8310 正常 8302 空） | articleId 不匹配（映射未灌） | 同上 |
| 查询改写超时 | LLM 上游延迟 >3.5s | 属预期降级，回落原查询；频繁则换模型或 `RAG_DISABLE_QUERY_REWRITE=true` |
| rerank 降级为启发式 | 网关 429 限流 | 自动降级，不影响可用性；频繁则等或换 key |

## GraphRAG 知识图谱与评测工作台

### 1. 同步知识三元组至 Neo4j

服务启动时若检测到 Neo4j 节点数为 0 会自动触发同步。也可手动执行全量 38 篇 IT 卡片三元组灌库：

```bash
python tools/sync_triples_to_neo4j.py
```

### 2. 启动 GraphRAG vs 纯向量检索 对比评测工作台（:8350）

提供基于 FastAPI + Vis.js 的同屏对比评测工作台：

```bash
python tools/run_compare_ui.py
# 浏览器访问 http://127.0.0.1:8350
```

支持功能：
- **同屏双轨对照**：纯向量检索 vs GraphRAG 多跳因果推导全维度对比（实体、推导链、耗时、切片）
- **Neo4j 拓扑交互可视化**：物理力导向动态布局、节点拖拽、多跳关系标注与废止替代剪枝
- **预置多跳评测集**：一键运行 VPN/AD 域并发锁死、CMDB 资产网络依赖、制度新旧版本消歧等典型级联场景

## 关闭

`Ctrl+C` 即可。无后台连接池、无定时任务，安全退出。
