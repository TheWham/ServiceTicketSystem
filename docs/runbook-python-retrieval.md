# Runbook — Python 检索内核接入 Java rag-service

本 runbook 描述如何把 `rag_service`（Python 检索内核 HTTP 服务）接入
`ServiceTicketSystem/it-ticket-cloud/rag-service`，替换其检索内核（②向量化 + ③ES 检索），
以及联调、回归与运维注意事项。

## 架构

```
consultation-service ──HTTP──> rag-service (Java, :8302)
                                   │  ① DomainClassifier（不变）
                                   │  ②③ provider=python ──HTTP──> python -m rag_service (:8310)
                                   │       （BM25+Dense 双路 + RRF + Cross-Encoder 精排 + 拒答）
                                   │  ④ MySQL PUBLISHED 复核（不变）
                                   │  ⑤ 透传 Python reliable/拒答；复核滤除后修补 topScore
```

对外契约 `POST /api/v1/rag/retrievals`（`Result<RagRetrievalResponse>`）**零变化**；
consultation-service 不需要任何改动。

## 启动 Python 检索服务

```bash
cd /path/to/demos
pip install -r rag_service/requirements.txt   # fastapi / uvicorn[standard] / pydantic>=2
RAG_HOME=$PWD python -m rag_service           # 默认 127.0.0.1:8310，单进程
```

环境变量：

| 变量 | 默认 | 说明 |
|---|---|---|
| `RAG_HOME` | 包上级目录 | 仓库根（定位 configs/artifacts/.env） |
| `RAG_SERVICE_HOST` / `RAG_SERVICE_PORT` | `127.0.0.1` / `8310` | 监听地址 |
| `RAG_MAPPING_PATH` | `$RAG_HOME/data/wiki_article_mapping.json` | wiki→Java id 映射 |
| `RAG_SERIALIZE_SEARCH` | `true` | 检索串行化（取锁超时 → HTTP 503 code=5031） |
| `RAG_LOCK_WAIT_SECONDS` | `1.0` | 锁等待上限，超时快速失败（不排队） |
| `RAG_DISABLE_QUERY_REWRITE` | `false` | `true` 关闭在线查询改写 |
| `RAG_REWRITE_CACHE_DIR` | `artifacts/evaluation/.llm_cache/rewrite` | 改写磁盘缓存（复用 Day14 暖缓存） |
| `RAG_RERANK_WAIT_BUDGET` | `1.5` | rerank 429 累计等待预算（在线收紧，离线评测为 90） |
| `RAG_RERANK_MAX_RETRIES` | `8` | rerank 每组打分最大请求轮次（离线为 20） |
| `RAG_RERANK_REQUEST_TIMEOUT` | `2.5` | 单次 rerank HTTP 读超时（离线默认 120s；过大会让一次上游挂起占住串行锁） |
| `RAG_WIKI_DIR` / `RAG_CHROMA_DIR` | `artifacts/output/wiki` / `artifacts/indexing/chroma_wiki_structured` | 语料与向量库 |

`GET /api/health`（async，不抢检索锁）回显：`status`（`UP`/`DEGRADED`，映射未加载即
`DEGRADED`）、`rerankWaitBudget`/`rerankMaxRetries`（确认在线预算已收紧）、
`rerankDegradedCount`（限流降级累计）、指纹与映射条目数。

## 灌库（先决：Java rag-service 已启动）

Python 返回的 `articleId/versionId` 必须能通过 Java 侧 ④ MySQL PUBLISHED 复核，
因此先把 35 张现行 Wiki 卡灌进 rag-service：

```bash
# rag-service 依赖：Nacos(:8848)、Redis(:6379)、ES(:9200)、MySQL（默认远程 120.92.138.195:3306）
cd /path/to/ServiceTicketSystem/it-ticket-cloud && docker compose up -d nacos redis
# ES 8.11 需另行提供（ES_HOST/ES_PORT 注入）
python tools/sync_wiki_to_rag_service.py            # 幂等；--force 强制重灌
```

- 排除 `_index.md` 与 `status ∈ {已废止, 已下线}` 的 3 张 LEG 卡；
- 走既有 `POST /api/v1/rag/documents/upload`（`publishNow=true` 直发 PUBLISHED 并写 ES），
  需要 `X-User-Id`/`X-User-Role` 头（脚本默认 `U_KBA01`/`KNOWLEDGE_ADMIN`）；
- 产出 `data/wiki_article_mapping.json`（原子写、逐张落盘）；重灌会生成**新的** articleId；
- 中文类目 → Java 类目编码映射见脚本 `JAVA_CATEGORY_BY_WIKI_CATEGORY`；
- 灌库后重启 Python 服务，`/api/health` 应为 `status=UP, mappingEntries=35`。

## Java 侧启用与回滚

```bash
# 启用 Python 检索内核
RAG_RETRIEVAL_PROVIDER=python RAG_PYTHON_BASE_URL=http://127.0.0.1:8310 \
  RAG_PYTHON_TIMEOUT_MS=4200 RAG_PYTHON_CONNECT_TIMEOUT_MS=500 \
  ./mvnw -pl rag-service spring-boot:run
# 回滚（零代码）：RAG_RETRIEVAL_PROVIDER=es（默认）
```

- `provider=es`（默认）行为与 main 完全一致；
- python 分支异常 → 依赖不可用（`MODEL_UNAVAILABLE`），**不**静默回 ES。

## 验证

```bash
python -m pytest rag_service/tests -q            # 纯逻辑单测（23 例）
RAG_HOME=$PWD python -m rag_service &           # 启动后：
python tools/check_contract.py                  # 契约不变量 69 项（含锁超时 5031、health 不抢锁）
python tools/run_service_regression.py --pace 1.5   # 20 题 vs artifacts/evals/day14_baseline.json
# Java 侧（worktree 或合并后）：
mvn -pl rag-service -am test                    # 82 tests（含 python 分支 13 例）
```

重建基线（装配改动后）：`python tools/freeze_day14_baseline.py`（需远程 rerank，约 1-2 分钟）。

## 已知行为与运维要点

1. **网关限流降级**：KSP 网关 429 密集时，收紧后的在线预算（1.5s/8 次）可能拿不到
   dashscope 后端 → 该次打分降级为启发式（`/api/health` 的 `rerankDegradedCount` 递增、
   日志打印警告）。降级题的第 2/3 位排序可能与离线基线漂移，但 top-1 与**拒答集合不变**。
   压测/回归请带节拍（`--pace 1.5`），避免人为打满限流。
2. **拒答策略（内核 + 服务层双重兜底）**：内核层拒答分两条阈值——远程打分用
   `retrieval.reject_threshold`（0.40），启发式降级时用 `retrieval.heuristic_reject_threshold`
   （0.25，可配置）；服务层另按 `refuse ⇔ 内核拒答 ∨ 无候选 ∨ max(score) < 0.40` 兜底，
   不以"是否走了远程 rerank"为条件，对抗题在降级时也不会泄漏作答。
   代价：降级且启发式分 < 0.25 的正样本会被误拒（可用性损失，方向安全）。
3. **冷查询延迟**：改写缓存命中时全程 ~0.5-2.6s；缓存**未命中**且网关限流时，
   单题可能超过 Java 侧 `python-timeout-ms=4200`（实测超时过一次）。
   - 部署时预热缓存：先跑一遍黄金集（评测或回归脚本都会写入磁盘缓存）；
   - 延迟敏感的联调/压测可临时 `RAG_DISABLE_QUERY_REWRITE=true`
     ——注意：关闭改写会改变召回（改写参与四路召回），质量回归基线（Day14）仅对
     `query_rewrite=true` 成立，关闭后不得以基线比对。
4. **并发**：默认串行（`RAG_SERIALIZE_SEARCH=true`）；锁等待 1.0s 超时返回
   HTTP 503 + `code=5031` 快速失败，不会排队几十秒。`reranker.last_used_remote`
   已线程本地化，理论可关闭串行开关，但未做并发压测前不建议。
5. **content/snippet**：`content` 为整卡全文（parent_content），`snippet` 为其
   空白压缩后前 1000 字符；`chunkId` 为 `ITKB-XXX-NNN#cN` 形态；
   `indexVersion == versionId` 恒成立。
6. **灌库前（映射缺失）**：服务 `DEGRADED`，`articleId` 降级为 wiki 卡 id、
   `versionId` 降级为 `wiki_version`——经 Java ④ 复核 items 必空（全部滤除），
   即"先灌库后联调"。

## 存储两阶段规划

- **本轮（双真源同步）**：Git 仓库 `artifacts/output/wiki/*.md` 为编辑真源；
  sync 脚本灌入 Java MySQL+ES 为运行时权威；映射表 `data/wiki_article_mapping.json` 建议入库。
- **生产演进（后续）**：Java MySQL/OSS 为唯一真源，Python 增加 `/api/v1/rag/index/sync`
  热更新端点，卡片由后台发布流驱动，消除映射表手工维护。
