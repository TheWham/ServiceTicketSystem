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
| `RAG_REWRITE_TIMEOUT` | `3.5` | 单次改写调用超时（秒）。SDK 自带重试已关闭（`max_retries=0`），超时即回落原查询。测试预算放宽：Java 客户端 5s = 改写 T + 向量/BM25 ~0.7s + 精排 ≤1.5s ⇒ T ≤ 3.5s |
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

## analytics_service（跨工单聚合归纳）

回答「请根据全部网络与打印设备工单，总结本季度共性根因并给出备件建议」这类
**跨多记录宏观归纳**问题。与既有 RAG 链路是两条独立链路——`retrieval.top_k=3` 的
单卡口径物理上凑不齐跨数十条记录的材料，且**工单从不进入知识库**。
职责边界、五段链路与设计取舍见 `analytics_service/README.md`。

> ⚠️ **consultation-service 默认会往这条链路分流**（`AI_ANALYTICS_ENABLED` 默认 `true`）。
> 所以本服务未启动时，判定为分析型的提问会返回 `503 AI_UNAVAILABLE` ——
> 这是**如实拒绝，不是故障**；它也**不会静默回退成知识问答**（回退会让统计请求收到
> 一份单卡答案，那正是这条链路要消灭的答非所问）。
> 只跑其余链路、不想起本服务时，在 consultation 侧设 `AI_ANALYTICS_ENABLED=false`。
>
> 本服务反过来依赖 ticket-service（:8201）取数，**启动顺序上排在它之后**。

```bash
cd services/python-retrieval
# 启动 HTTP 服务（默认 127.0.0.1:8340）：
python -m analytics_service
# 环境变量（优先级：环境变量 > .env > 默认）：
export ANALYTICS_LLM_MODEL=deepseek-v4-flash            # 归因叙事模型，缺省回退 LLM_*
export ANALYTICS_TICKET_BASE_URL=http://127.0.0.1:8201  # 工单投影扫描来源
export ANALYTICS_MIN_UNIVERSE=20                        # 全库样本下限（低于则整体拒答）
export ANALYTICS_MIN_DENOM=10                           # 条目分母下限（低于则只给计数不给占比）
export ANALYTICS_MIN_LABEL_HITS=5                       # 条目命中下限
export ANALYTICS_MODEL_ROUTING=0                        # 关掉模型路由与抽槽（纯规则+正则）
```

**模型未配置时链路照走**：聚合、闸门、覆盖率全部不受影响，只有归因叙事退回确定性模板，
token 标 `estimated`。所以这个服务可以在没有模型凭据的环境里完整演示。

### 请求理解：模型给槽位，代码算日期

Node A 一次调用同时产出**意图**与**槽位**（时间窗 / 范围限定 / 关注维度）。时间区间由
`timewindow` 从槽位算出来，不由模型算 —— 模型算错季度边界不会报错，只会安静地给一个
错误的分母，这是全链路里最难查的一类失败。

排障时看两处：

- **`WINDOW_SOURCE`**（每条分析请求都有）：这次的时间口径是谁定的（模型抽取 / 规则解析 /
  默认最近90天）。前端「统计口径」卡片上也有同一份来源标签。
- **`WINDOW_CONFLICT` / `WINDOW_SLOT_REJECTED` / `WINDOW_MODEL_MISSED`**（只在异常时出现）：
  模型与规则**都从字面命中**却给出不同区间 / 槽位被弃用（附原因，最常见是 `rawText` 没在
  提问里原样出现）/ 模型说"没有时间词"而正则字面命中。

### 判为非分析型 → 熔断（不回退）

看板入口（`/api/v1/analytics/query`）收到一个不属于跨工单统计的问题时，链路**熔断**：

```
Trace 只有 2 个 span：A.Intent_Router → A.Short_Circuit
响应：verdict=REFUSED  replyType=REFUSE  refusalReason=OUT_OF_SCOPE
      analyticsFacts=null（未取数、未聚合、未调叙事模型）
```

正文会指路（引导去智能客服），**不会**静默换成知识问答 —— 回退会让同一个 HTTP 入口
按措辞切换成两套链路，答复类型随措辞漂移。

**客服入口不熔断**：它由 Java 分类器先定性（透传 `upstreamIntent=ANALYTICS`），本链路
据此锁死意图、不翻案。两个入口的差别是刻意的。

> ⚠️ 若看到看板入口对任何问题都照样跑完 5 个 span，先查 Java 侧是不是又给看板
> 传了 `upstreamIntent`。`upstreamIntent=ANALYTICS` 会锁死意图，使熔断永远不触发 ——
> 这是排查"熔断为什么不生效"的第一个检查点。

> ⚠️ 判 `WINDOW_CONFLICT` 时**必须带前置条件**：`parse_window` 在正则没命中时返回的是
> **默认窗口而不是 `None`**。不加区分地拿它和模型窗口比区间，每一条靠模型立功救回来的
> 提问（"第三季度""自9月以来"）都会误报冲突，恰好把最该看见的信号淹没。

三个开关：

| 键 | 默认 | 说明 |
|---|---|---|
| `ANALYTICS_MODEL_ROUTING` | `1` | 置 `0` 则 Node A 不调模型：意图走规则、时间走正则、子域走词表匹配 |
| `ANALYTICS_ROUTER_MAX_OUTPUT_TOKENS` | `2048` | 路由调用输出预算。原来是 `max_tokens=16`，而本端点的模型是推理模型，思维链会先吃掉额度 |
| `ANALYTICS_ROUTER_TIMEOUT` | `60` | 路由调用独立超时，**须小于** `ANALYTICS_LLM_TIMEOUT`（180）；超时即退回正则 |

**代价**：每次分析请求多一次模型调用（改造前规则命中时是 0 次）。要零调用就设
`ANALYTICS_MODEL_ROUTING=0`。

### 评测：与检索评测**分成两套**

```bash
# 聚合题（跨工单宏观归纳，7 项指标）
python -m rag_pipeline.pipelines.aggregate_evaluation --fixture analytics_service/tests/fixtures/tickets_q4.json
# 确定性基线：关掉模型，规则与正则全权决策
python -m rag_pipeline.pipelines.aggregate_evaluation --fixture analytics_service/tests/fixtures/tickets_q4.json --no-model
# 检索题（原有 5 项指标，不受影响）
python -m rag_pipeline.pipelines.golden_evaluation
```

两者由黄金集的 `is_aggregate_check` 字段分流，共用一个 JSON 文件：`golden_evaluation`
会**跳过**聚合题并在控制台打印跳过条数——聚合题没有"该命中哪张卡"这回事
（`reference_chunk_ids` 为空），若按单卡口径评分会恒判未命中，把召回率整体拉下去。

`--fixture` 用真实库 Q4 窗口快照离线跑（55 张原始单，已脱敏，无姓名与联系方式）；
不传 `--fixture` 则走 ticket-service 的真实投影扫描接口。

### 词表维护（这是本服务唯一需要人工照看的东西）

受控词表在 `configs/taxonomy.yaml`，**外置且版本化**——词表一改，历史统计口径就不可复现，
所以版本号参与配置指纹，与索引配置同等对待。

```bash
# 未命中回捞：把没命中任何标签的工单落盘 + 给出词频候选
python -m analytics_service.pipelines.unmatched_report --fixture analytics_service/tests/fixtures/tickets_q4.json
```

输出 `artifacts/analytics/unmatched_<窗口>.jsonl` 与候选词。**打标本身只由词典完成**——
LLM 可以提候选，不参与判定，否则口径不可复现。`taxonomy_coverage_rate` 是这项工作的
验收指标（门槛 ≥ 80%）。

> ⚠️ **别把泛化词写成独立关键词。** `无反应` / `无法调节` 这类词单独出现时不构成症状判据：
> 实测「打印机再次脱机」的描述里同时有"打印机"和"无反应"，「电脑音量无法调节」的描述里
> 也有"无反应"——任何一条裸泛化词都会把它们从各自的正确标签下抢走（截胡，已实测复现）。
> 加载时校验，违规直接抛错而不是静默降级。

### 已知限制（如实登记，不是待办）

- **根因维度可用，但数据是演示数据**：`ticket_resolution` 已由
  `tools/seed_ticket_resolutions.py` 写入 **28 条**处置记录，根因维度因此可归纳
  （实测：电源故障 6 单 25.0% / 驱动缺陷 6 单 25.0% / 内存故障 5 单 20.8%）。
  ⚠️ **这 28 条是按工单实际症状写的演示数据，不是真实业务沉淀**——主键 `DEMO-RES-<ticket_id>`
  前缀，`--rollback` 可一键撤销。删掉它们，本维度会如实退回「无解决方案记录，不可归纳」。
  另外：**服务端没有任何代码写这张表**（Java 侧零引用），真实数据得由业务侧沉淀。
- **样本量小**：Q4 窗口内有效工单 24 单（原始 55 张中 31 张被判定为联调噪声/测试串/标注忽略）。
  子域限定后往往只剩个位数，会按设计走「只给计数不给占比」。
- **不改 `00-schema.sql`**：`validate_schema.py` 会断言列集合全等，所有 DDL 走
  `db/migration/V2_7__*.sql` / `V2_8__*.sql`（纯增量、幂等）。

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
   （超时上限 `RAG_REWRITE_TIMEOUT=3.5`，超时回落原查询），
   全链路约 1.5~5s，控制在 Java 侧 `python-timeout-ms=5000` 以内；
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
