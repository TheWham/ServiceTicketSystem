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
cd /path/to/demos/services/python-retrieval
pip install -r rag_service/requirements.txt   # fastapi / uvicorn[standard] / pydantic>=2
python -m rag_service                         # 默认 127.0.0.1:8310
```

> ✅ **`.env` 已就位（2026-10-22）**：服务目录下放了一份 `.env`（gitignore 忽略，不入库），
> `RAG_HOME` 缺省即包上级目录 → `configs/`、`artifacts/`、`.env` 三者同根，
> **裸启动即可**，无需导出环境变量。`.env` 失效时（键为空）嵌入/精排会静默降级为
> 本地 hash 兜底与启发式打分，检索质量下降且不报错——`/api/health` 的
> `configFingerprint` 可对照排查。
>
> 环境变量优先级：进程环境变量 > `.env` > 默认。部署到别处时设 `RAG_HOME`
> 指向含 `configs/`、`artifacts/`、`.env` 的目录即可。

环境变量：

| 变量 | 默认 | 说明 |
|---|---|---|
| `RAG_HOME` | 包上级目录 | 仓库根（定位 configs/artifacts/.env） |
| `RAG_SERVICE_HOST` / `RAG_SERVICE_PORT` | `127.0.0.1` / `8310` | 监听地址 |
| `RAG_MAPPING_PATH` | `$RAG_HOME/data/wiki_article_mapping.json` | wiki→Java id 映射 |
| `RAG_SERIALIZE_SEARCH` | `true` | 检索串行化（取锁超时 → HTTP 503 code=5031） |
| `RAG_LOCK_WAIT_SECONDS` | `1.0` | 锁等待上限，超时快速失败（不排队） |
| `RAG_DISABLE_QUERY_REWRITE` | `false` | `true` 关闭在线查询改写 |
| `RAG_REWRITE_TIMEOUT` | `2.0` | 单次改写调用超时（秒）。网关实测延迟 0.8~2.1s（中位 1.7s）；SDK 自带重试已关闭（`max_retries=0`），超时即回落原查询。预算倒推：Java 客户端 4.2s = 改写 T + 向量/BM25 ~0.7s + 精排 ≤1.5s ⇒ T ≤ 2.0s |
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

## Java 侧默认值与回滚

**默认 `provider=python`**，定义在两处，改的时候两处都要动：
`RagRetrievalProperties.provider` 与 `rag-service/src/main/resources/application.yml` 的
`${RAG_RETRIEVAL_PROVIDER:...}`。启动通常只需给地址：

```bash
RAG_PYTHON_BASE_URL=http://127.0.0.1:8310 \
  RAG_PYTHON_TIMEOUT_MS=4200 RAG_PYTHON_CONNECT_TIMEOUT_MS=500 \
  mvn -pl rag-service spring-boot:run
```

回滚到 ES 是零代码的：

```bash
RAG_RETRIEVAL_PROVIDER=es mvn -pl rag-service spring-boot:run
```

- ⚠️ **默认取 python 之后，Python 检索服务必须可访问**：python 分支异常 → 依赖不可用
  （`MODEL_UNAVAILABLE`），**不**静默回 ES。这是刻意的——静默回退会把「Python 挂了」
  表现成「检索结果变差」，没人会发现。
- `provider=es` 与本次改动前的行为完全一致。
- 改动默认值时要同步看两个测试：`RagRetrievalServiceTest` 已显式钉住 `es`（专测 ES 路径，
  不再依赖默认值），`RagRetrievalServicePythonProviderTest.pythonIsDefaultProvider` 断言默认值。

> 注：本文档早先写的 `./mvnw` 在本仓库并不存在（没有 maven wrapper），已改为 `mvn`。

## 验证

```bash
python -m pytest rag_service/tests -q            # 纯逻辑单测（68 例，含版本消歧与端点契约）
python -m rag_service &                          # 裸启动后：
python tools/check_contract.py                  # HTTP 黑盒契约不变量 85 项
                                                #（对 Java 的检索契约 + 锁超时 5031 + health 不抢锁
                                                #  + 版本消歧的分水岭与四态）
python tools/run_service_regression.py --pace 1.5   # 20 题 vs artifacts/evals/day14_baseline.json
# Java 侧（worktree 或合并后）：
mvn -pl rag-service -am test                    # 85 tests（含 python 分支 15 例）
```

重建基线（装配改动后）：`python tools/freeze_day14_baseline.py`（需远程 rerank，约 1-2 分钟）。

## 三服务联调（已实测通过）

链路：`consultation-service(:8301) → rag-service(:8302, provider=python) → Python 检索服务(:8310)`

前置：Nacos(:8848)/Redis(:6379)/ES(:9200) 起来（`it-ticket-cloud/docker-compose.yml` 的前三者 +
`rag-service/docker-compose.yml` 的 ES）；rag-service 的向量化凭据经 `EMBEDDING_BASE_URL/API_KEY/MODEL`
注入（网关 `qwen3-embedding-8b` 支持 `dimensions=1024`，与 ES mapping 的 1024 维一致）。

```bash
# rag-service 用 python 内核 + 向量化凭据
RAG_RETRIEVAL_PROVIDER=python RAG_PYTHON_BASE_URL=http://127.0.0.1:8310 \
EMBEDDING_BASE_URL=... EMBEDDING_API_KEY=... EMBEDDING_MODEL=qwen3-embedding-8b \
EMBEDDING_DIMENSIONS=1024 java -jar rag-service/target/it-ticket-rag-service-1.0.0.jar
```

实测结论（20 题里的代表用例）：
- 「员工忘了密码登不进系统怎么办」→ `ANSWER` + 1 条引用（`art-…` 可反查映射表）、confidence 0.9、约 6.6s；
- 「VPN 连不上怎么办」「打印机脱机无法打印」→ `ANSWER` + 引用，confidence 0.95；
- 「今天天气怎么样的」→ Java 侧 `OFF_TOPIC` 短路，**不触达 Python**（4ms）；
- 端到端时延 2.4~12s（含远程 LLM 生成，consultation 侧 `request-timeout-ms=120000` 足够）。

**联调踩坑（重要）**：
1. consultation 的模型客户端硬编码 `temperature=0.0` + `response_format=json_object`。
   **`kimi-k3` 只接受 `temperature=1`**，用它会被网关 400 拒绝（表现为 `PERMANENT_HTTP` → 全量
   `MODEL_UNAVAILABLE` 拒答，且 `costMs=0` 很迷惑）。联调/上线须选支持 `temperature∈[0,1]` 的模型
   （实测 `deepseek-v4-flash` 可用）；`qwen3-vl-32b-thinking` 在本网关未开通（403）。
2. consultation 的 `ai-secrets.yml` 里 `rag-base-url` 是**字面量**，会覆盖 `RAG_BASE_URL` 环境变量——
   改地址要直接改该文件（或在其中写成 `${RAG_BASE_URL:http://127.0.0.1:8302}`）。
3. 会话带 `categoryId` 时，检索会按该类目过滤（Python 侧 `_metadata_filter` 反查中文类目）——
   跨类目提问会被过滤成低置信拒答（**预期行为**），联调提问要注意会话类目与问题匹配。
4. 请求须带 `X-Request-Id` + `Idempotency-Key` 头，否则 consultation 侧 400。

## agent_service（Function Calling 智能体）

生成侧下沉到 Python：ReAct 循环 + 白名单工具（查本人工单 / 产建单草稿 / 补搜知识），
由 Java consultation-service 经 `POST /api/v1/agent/chat` 调用（开关 `AI_AGENT_ENABLED`）。
职责边界与工具语义见 `agent_service/README.md`。

```bash
cd services/python-retrieval
# .env 兜底已接（LLM_BASE_URL/LLM_API_KEY/LLM_CLEAN_MODEL），仓库根有 .env 时裸启动即可：
python -m agent_service                                 # 默认 127.0.0.1:8320
# 环境变量仍可覆盖（优先级：环境变量 > .env > 默认）：
export AGENT_LLM_BASE_URL=... AGENT_LLM_API_KEY=...    # 生成模型凭据
export AGENT_LLM_MODEL=deepseek-v4-flash               # ← 必须是支持原生 tools 的对话模型
export TICKET_SERVICE_BASE_URL=http://127.0.0.1:8201   # 查工单 / 建单（默认 8201，可不设）
export KNOWLEDGE_SEARCH_BASE_URL=http://127.0.0.1:8301 # 补搜知识（默认 8301，可不设）
```

> ⚠️ **`AGENT_LLM_MODEL` 别顺手用 `LLM_CHAT_MODEL` 代。**
> `.env` 的 `LLM_CHAT_MODEL=kimi-k3` 是**思考型模型**——每次回答前先输出一大段推理：
> 实测直连问一句「你好」，单次 `completion_tokens=90`，其中 `reasoning_content` 323 字、
> 真正的回答只有 22 字。拿它跑 ReAct 时，系统提示词（规则 + 工具 schema + JSON 契约）
> 会把这段推理放大数倍，再叠上多轮往返，单次问答要 14~60s。

模型选了思考型时，延迟差一个数量级（本地全栈实测）：

| 场景 | kimi-k3（思考型） | deepseek-v4-flash |
| --- | --- | --- |
| 「你好」 | 14.4s | 4.5s |
| 带材料的知识问答 | 30.4s | 2.3s |
| 查本人工单（1 次工具调用） | 25.6s | 9.3s |

两者的原生 tools 能力无差异（都实测能正确触发 `query_my_tickets` / `prepare_ticket`），
差别只在延迟。**`config.py`、`docker-compose.yml`、`agent_service/README.md` 里的默认值
本来就是 `deepseek-v4-flash`**，只有手工启动时才容易被 `LLM_CHAT_MODEL` 覆盖掉。

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
3. **冷查询延迟**：改写缓存命中时全程 ~0.5-2.6s；缓存**未命中**时改写真实调用网关
   （实测 0.8~2.1s，超时上限 `RAG_REWRITE_TIMEOUT=2.0`，超时回落原查询），
   全链路约 1.5~4s，通常仍在 Java 侧 `python-timeout-ms=4200` 以内；
   叠加网关限流时可能超预算（Java 侧按 `MODEL_UNAVAILABLE` 降级）。
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

## 版本消歧查询（`rag_pipeline.policy`）

回答「在某个时间点，哪一版规约有效」，产出该版本的溯源角标与条文。

### HTTP 出口

`POST /api/v1/policy/resolve`（与 `/api/v1/rag/retrievals` 同款 Result 包络与错误映射）

```bash
curl -s -X POST http://127.0.0.1:8310/api/v1/policy/resolve \
  -H 'Content-Type: application/json' \
  -d '{"query":"域账号锁定 解锁","at":"2024-01-15","topK":6}'
```

```json
{"code":0,"msg":"success","data":{
  "status":"RESOLVED",
  "citation":"[来源: ITKB-LEG-ACC-001@v0.9 《域账号锁定处理（旧版·宽松策略，已废止）》]",
  "articleId":"ITKB-LEG-ACC-001","version":"v0.9",
  "effectiveDate":"2022-01-01","supersededAt":"2024-03-01",
  "replacedArticles":[],"content":"…","reason":"2024-01-15 时刻适用 …",
  "undatedArticles":[],"chain":[…],"candidates":[…]}}
```

请求字段：`query`（必填）、`at`（`YYYY-MM-DD`，留空取当天 UTC）、`topK`（1..20，默认 8）。
错误映射沿用服务既有约定：参数非法 400/4000、检索锁繁忙 503/5031、兜底 500/5000。

> `UNDATED`（无生效日期、无法判定）是**结论不是错误**，返回 HTTP 200 + code 0。
> 把它当成失败去重试或告警都是误读。

### 库内直接调用

```python
from rag_service.assembly import ServiceAssembly
from rag_pipeline.policy import PolicyResolver

asm = ServiceAssembly()
res = PolicyResolver(asm.retriever).resolve("域账号锁定 解锁", at="2024-01-15")
# 或复用装配（与 search() 共用同一把检索锁）：
res = asm.resolve_policy("域账号锁定 解锁", at="2024-01-15")
```

### 与 `default_exclude` 的分工（别把两者混为一谈）

| | 用途 | 召回行为 |
|---|---|---|
| `retrieval.default_exclude` | 别把**废止做法**教给员工 | 召回**前置**物理屏蔽 `wiki_status ∈ {已废止, 已下线}` |
| `rag_pipeline.policy` | 判断**某时刻哪一版有效** | 必须**看得见**废止卡（`include_excluded=True`），否则无从消歧 |

两者需求相反，所以 `IndustrialHybridRetriever` 的三个检索方法新增了
`include_excluded: bool = False` 形参。**默认值保持改前行为**——普通检索路径仍然屏蔽废止卡。

### 四种结论，不互相冒充

| status | 含义 |
|---|---|
| `RESOLVED` | 选中该时刻有效的一版（沿命中主题的 `replaces` 版本链选，不是全局取日期最大值） |
| `NO_EFFECTIVE_VERSION` | 相关规约在该时刻**尚未生效** |
| `UNDATED` | 命中的版本链上没有任何一张带 `effective_date`，**无法**做时间判定 —— 不猜 |
| `NO_MATCH` | 检索零命中 |

`UNDATED` 是最要紧的一态：39 张卡里只有 6 张带生效日期，其余 33 张没有。
对没日期的卡唯一诚实的回答是「无法判定」，不能默认它永远有效。

### 演示用的版本数据是**构造**的（重跑语料会丢）

源文档 `IT常见问题RAG知识库.docx` 里**没有任何日期**（连版本号都没有），
清洗中间产物同样为 0 个日期。所以分水岭消歧的日期是为了演示**显式构造**的：

| 版本链 | 生效日 | `replaces` |
|---|---|---|
| `ITKB-LEG-ACC-001` (v0.9, 已废止) → `ITKB-ACC-001` (v1.0) | 2022-01-01 → 2024-03-01 | 新版声明取代旧版 |
| `ITKB-LEG-NET-004` (v0.9, 已废止) → `ITKB-NET-004` (v1.0) | 同上 | 同上 |
| `ITKB-LEG-VPN-001` (v0.9, 已废止) → `ITKB-VPN-001` (v1.0) | 同上 | 同上 |

这 6 张卡的 frontmatter 里带 `effective_date_source: "demo-constructed"` 标明来源——
不是模型抽取的，也不是从源文档读到的。这与 `llm_synthesizer` 的「不得编造日期」铁律
不冲突：铁律管的是**自动抽取环节**不许幻觉；人工声明的演示数据是另一回事，只要标明白。

> ⚠️ **重跑 `wiki_generator` 流水线会丢掉这些字段**（它只渲染 `llm_synthesizer` 给出的
> `effective_date`）。`rag_service/tests/test_policy.py` 末尾的
> `test_real_corpus_keeps_the_three_demo_version_chains` 就是那个提醒用例。

### 改动语料后必须重建索引

`manifest.json` 的 `wiki_fingerprint` 按**原始字节**算（`chunking/fingerprint.py`），
改一张卡就会漂移，`ServiceAssembly` 加载时 fail-fast：
「向量库与当前 Wiki 卡片不一致，请重建索引」。

```bash
cd services/python-retrieval
RAG_HOME=$PWD python -m rag_pipeline.pipelines.indexing \
    --wiki-dir artifacts/output/wiki --output-dir artifacts/indexing
```

**行尾必须是 LF**（`.gitattributes` 已固定）。CRLF 会改变字节级指纹，让 fresh clone 启动失败。

### 跑一次服务就会把索引文件改脏（正常，别提交）

`artifacts/indexing/chroma_wiki_structured/` 是**活库**，被入库了。只要 `ServiceAssembly`
打开过它，Chroma 就会做 SQLite 页面重排与 HNSW 同步计数，`chroma.sqlite3` 与
`length.bin` 的字节随之变化 —— 而**数据一行没变**（实测 `embeddings` 144 行、
`embedding_metadata` 3216 行，前后一致）。

所以：跑完服务看到这两个文件显示为 modified 是预期的，直接

```bash
git checkout -- services/python-retrieval/artifacts/indexing
```

回滚即可，不要提交这类噪音。判断「是不是真变了」用行数比对，别看 `git status`。

## 存储两阶段规划

- **本轮（双真源同步）**：Git 仓库 `artifacts/output/wiki/*.md` 为编辑真源；
  sync 脚本灌入 Java MySQL+ES 为运行时权威；映射表 `data/wiki_article_mapping.json` 建议入库。
- **生产演进（后续）**：Java MySQL/OSS 为唯一真源，Python 增加 `/api/v1/rag/index/sync`
  热更新端点，卡片由后台发布流驱动，消除映射表手工维护。
