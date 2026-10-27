# AI 链路配置清单

> 本文覆盖「AI 客服 + RAG 检索」整条链路**所有需要配置的地方**：改哪里、改成什么、缺了的症状。
> 密钥一律不入库，本文只写变量名与掩码值；真实值在本地 `.env` / 环境变量里。

---

## 一、链路全貌

```
【知识入库·写路径】
  knowledge-admin 页 → rag-service:8302 ──Embedding API──→ ES knowledge_chunk（1024 维）
  (离线 CLI) rag_pipeline.pipelines.indexing ──Embedding API──→ chroma 向量库（4096 维，产物随仓库走）

【问答·读路径】
  前端:5175 → gateway → consultation-service:8301
                            │
                            ├─ 领域四态判定（纯规则，不调模型）
                            │    OFFICE_IT / OFF_TOPIC / HIGH_RISK / UNCERTAIN
                            │
                            ├─ 检索：consultation → rag-service:8302 → python rag_service:8310
                            │                                            ├ Embedding：问句向量化
                            │                                            ├ Rerank：精排
                            │                                            └ LLM：查询改写
                            │
                            └─ 生成：AI_AGENT_ENABLED=true → agent_service:8320 → LLM + tools
                                      AI_AGENT_ENABLED=false → consultation 自己调 LLM（单轮强制 JSON）
                                      
                               工具回跳：agent_service → ticket-service:8201（查本人工单 / 产建单草稿）
                                                     → consultation:8301（补搜知识）
```

【分析·读路径】（Day21 跨工单聚合归纳，走同一问答入口）
  前端:5175 → gateway → consultation-service:8301
                            │
                            ├─ 意图判定：SemanticRequestClassifier（LLM）/ KeywordRequestClassifier（兜底）
                            │    判为 ANALYTICS → AnalyticsClient
                            │    其余 → 原 ragPipeline（上面那条读路径）
                            │
                            └─ analytics_service:8340（确定性节点链）
                                 ├ 请求理解（意图判定 + 时间/范围/维度槽位抽取）
                                 ├ 取数：ticket-service:8201 只读投影扫描（★不 GROUP BY、不跨库）
                                 ├ 时间口径：模型给语义槽位 → Python 算具体日期区间
                                 ├ 聚合：纯 Python 词表抽取 + 占比/覆盖率/小样本闸门/备件决策表
                                 ├ 模型：只做归因叙事（拿不到原始工单，只有已算好的事实）
                                 └ 门禁：verify_numbers / verify_ticket_ids（数字与单号必须可溯源）
```

**要点**：三个模型角色（对话生成 / Embedding / Rerank）可以各自独立配 base_url 与 key，互不影响。
分析链路的模型调用点有两处（请求理解、归因叙事），**数字由 Python 算、日期由 Python 算，
模型一处也改不到**。

---

## 二、配置点总表（速查）

| # | 位置 | 端口 | 关键变量 | 我本机的值 | 在库里？ |
|---|---|---|---|---|---|
| ① | consultation-service 生成模型 | 8301 | `AI_PROVIDER` `AI_BASE_URL` `AI_API_KEY` `AI_MODEL` | `openai-compatible` / kspmas / `sk-kGEN…` / `deepseek-v4-flash` | 默认值在库，**真值不在** |
| ② | consultation-service 智能体开关 | 8301 | `AI_AGENT_ENABLED` `AGENT_SERVICE_BASE_URL` `TICKET_SERVICE_BASE_URL` `RAG_BASE_URL` | `true` / `:8320` / `:8201` / `:8302` | 默认值在库，真值不在 |
| ③ | agent_service 生成模型 | 8320 | `AGENT_LLM_BASE_URL` `AGENT_LLM_API_KEY` `AGENT_LLM_MODEL` `AGENT_SERVICE_PORT` `RAG_HOME` | kspmas / `sk-kGEN…` / `deepseek-v4-flash` / `8320` / `services/python-retrieval` | 默认值在库，真值不在 |
| ④ | rag-service 向量模型 | 8302 | `EMBEDDING_BASE_URL` `EMBEDDING_API_KEY` `EMBEDDING_MODEL` `EMBEDDING_DIMENSIONS` | kspmas / `sk-kGEN…` / `qwen3-embedding-8b` / `1024` | 默认值在库，真值不在 |
| ⑤ | python 检索内核 | 8310 | `EMBED_*` `RERANK_*` `LLM_*` `RAG_HOME` | **空（降级中）** / `RAG_HOME=services/python-retrieval` | **不在库** |
| ⑥ | rag-service 检索路由 | 8302 | `RAG_RETRIEVAL_PROVIDER` `RAG_PYTHON_BASE_URL` | `python` / `http://127.0.0.1:8310` | 默认值在库 |
| ⑦ | 离线入库流水线 | — | `EMBED_*` + `configs/pipeline.yaml` | — | 产物在库 |
| ⑧ | workflow_demo（Day17 demo） | 8330 | `AGENT_LLM_*` → 回退 `LLM_*` | 同 ③ | 默认值在库 |
| ⑨ | analytics_service（Day21 分析链路） | 8340 | `ANALYTICS_TICKET_BASE_URL` `ANALYTICS_LLM_*` → 回退 `LLM_*` | 同 ②③ | 默认值在库 |
| ⑨' | consultation → 分析链路分流（Java 侧） | 8301 | `AI_ANALYTICS_ENABLED` `ANALYTICS_SERVICE_BASE_URL` | `true` / `:8340` | 默认值在库 |

**唯一凭据**：一把 key + 一个 base_url，其余都是模型名与开关。

---

## 三、逐处详解

### ① consultation-service · 生成模型

**文件**：[application.yml:89-99](it-ticket-cloud/consultation-service/src/main/resources/application.yml:89)

```yaml
itticket.consultation.ai:
  provider: ${AI_PROVIDER:openai-compatible}
  base-url: ${AI_BASE_URL:}
  api-key:  ${AI_API_KEY:}
  model:    ${AI_MODEL:deepseek-v4-flash}
```

**备用入口**：`ai-secrets.yml`（`AI_SECRETS_FILE` 指向的路径），Spring 以
`optional:file:${AI_SECRETS_FILE:./ai-secrets.yml}` 导入，文件不存在静默跳过。
模板见 [ai-secrets.example.yml](it-ticket-cloud/ai-secrets.example.yml)。

> **本机实际用法**：没用 `ai-secrets.yml`，全部走环境变量。两种方式二选一即可，不要同时用
> （同时用会打架：文件里写死的字面量会覆盖环境变量）。

**缺失症状**：`api-key` 为空 → AI 问答降级为 `NOT_CONFIGURED` 结构化拒答 +
`suggestTransfer=true`（RD-006）；知识搜索、人工咨询、转人工不受影响。

---

### ② consultation-service · 开关与工具地址

| 变量 | 默认 | 作用 | 我本机 |
|---|---|---|---|
| `AI_AGENT_ENABLED` | `false` | 生成侧是否下沉 Python 智能体 | `true` |
| `AGENT_SERVICE_BASE_URL` | `http://127.0.0.1:8320` | Python 智能体地址 | 同默认 |
| `TICKET_SERVICE_BASE_URL` | `http://127.0.0.1:8201` | 确认建单用 | 同默认 |
| `RAG_BASE_URL` | `http://127.0.0.1:8302` | 检索走 rag-service | 同默认 |
| `AI_RETRIEVAL_PROVIDER` | `rag-service` | 检索提供方 | 同默认 |

**同段里写死、但决定行为的参数**（要改只能改 yml）：

| 参数 | 值 | 说明 |
|---|---|---|
| `temperature` | `0.0` | **硬编码**。所以模型必须接受 temperature=0 |
| `answer-enabled` | `true` | 总开关，评测不达标时置 false 只关 AI 综合回答 |
| `max-output-tokens` | `8192` | thinking 模型的推理 token 也计在内，给小了会出现推理占满、content 为空 |
| `rag-citation-min-score` | `0.70` | 引用分数阈值（可用 `RAG_CONFIDENCE_THRESHOLD` 覆盖） |
| `request-timeout-ms` | `120000` | 端到端 12s 级的回答留足了余量 |

**`AI_AGENT_ENABLED=false` 的后果**：能答知识问题，但不会查工单、不会产建单草稿（人机回环那套全没了）。

---

### ③ agent_service · 生成模型（Python）

**文件**：[agent_service/config.py](services/python-retrieval/agent_service/config.py)

| 变量 | 默认 | 我本机 |
|---|---|---|
| `AGENT_LLM_BASE_URL` | 空 | `https://kspmas.ksyun.com/v1` |
| `AGENT_LLM_API_KEY` | 空 | `sk-kGEN…` |
| `AGENT_LLM_MODEL` | `deepseek-v4-flash` | `deepseek-v4-flash` |
| `AGENT_SERVICE_PORT` | `8320` | `8320` |
| `AGENT_MAX_STEPS` | `5` | 默认（ReAct 轮次熔断） |
| `AGENT_LLM_TIMEOUT` | `120` | 默认 |
| `AGENT_TEMPERATURE` | 空 | 默认（不传，走模型默认值） |
| `RAG_HOME` | 包上级目录 | `services/python-retrieval` |

**工具地址**（两个都可选，不配则该工具返回明确错误）：

| 变量 | 我本机 |
|---|---|
| `TICKET_SERVICE_BASE_URL` | `http://127.0.0.1:8201` |
| `KNOWLEDGE_SEARCH_BASE_URL` | `http://127.0.0.1:8301` |

**自检**：`GET http://127.0.0.1:8320/api/health` → 期望 `model_configured:true`、
`ticket_service_configured:true`、`knowledge_search_configured:true`。

> ⚠️ `AGENT_LLM_MODEL` 必须是**支持原生 tools**的对话模型，且别顺手用 `.env` 里的
> `LLM_CHAT_MODEL`（那是 `kimi-k3` 思考型模型，单次问答 14~60s，比 `deepseek-v4-flash` 慢一个数量级）。

---

### ④ rag-service · 向量模型

**文件**：[application.yml:66-70](it-ticket-cloud/rag-service/src/main/resources/application.yml:66)

```yaml
rag.embedding:
  base-url:   ${EMBEDDING_BASE_URL:}
  model:      ${EMBEDDING_MODEL:qwen3.7-text-embedding}
  api-key:    ${EMBEDDING_API_KEY:}
  dimensions: ${EMBEDDING_DIMENSIONS:1024}
```

**备用入口**：`ai-secrets.yml`（`RAG_SECRETS_FILE`）。

**用途**：文档入库时的向量化（写 ES）、ES 检索路径的查询向量化。
`dimensions=1024` 会作为 `dimensions` 参数传给 Embedding API（截断），**必须与 ES 里现有索引维度一致**。

**缺失症状**：向量化按依赖不可用降级（RD-006），知识入库失败或检索弱化。

---

### ⑤ python 检索内核（AI 配置最密的一处）

**文件**：[rag_pipeline/config.py](services/python-retrieval/rag_pipeline/config.py) —
优先级：**进程环境变量 > `RAG_HOME/.env` > 默认值**

| 变量 | 用途 | 我本机 |
|---|---|---|
| `EMBED_BASE_URL` / `EMBED_API_KEY` / `EMBED_MODEL` | 问句向量化 | **空 → 降级** |
| `RERANK_BASE_URL` / `RERANK_API_KEY` / `RERANK_MODEL` | 精排 | **空 → 降级** |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_CHAT_MODEL` / `LLM_CLEAN_MODEL` | 查询改写（用 clean 模型） | **空** |
| `RAG_HOME` | 决定读哪个 `.env`、哪个向量库 | `services/python-retrieval` |

**配套配置文件** [configs/pipeline.yaml](services/python-retrieval/configs/pipeline.yaml)（已入库，全链路唯一真源）：

| 段 | 关键项 | 值 |
|---|---|---|
| `chunking` | 切块策略 | `parent_child`，child_size 512 |
| `embedding` | 模型 / 缓存 | `qwen3-embedding-8b` / `artifacts/indexing/.emb_cache` |
| `store` | 向量库 | `artifacts/indexing/chroma_wiki_structured` |
| `retrieval` | `top_k` / `rough_top_k` | `3` / `15` |
| `retrieval` | `query_rewrite` / `rewrite_model` | `true` / 空=取 `LLM_CLEAN_MODEL` |
| `retrieval` | `reject_threshold` / `heuristic_reject_threshold` | `0.40` / `0.25`（低置信拒答） |
| `reranker` | `model` / `backend` | `qwen3-reranker-8b` / `dashscope` |

**降级症状**：`GET http://127.0.0.1:8310/api/health` 里 `rerankAvailable:false`、
`rerankDegradedCount` 持续增长；检索退化为 BM25 + 启发式打分。
**答案仍能出，但排序质量不是最优。**（本机现状即是如此——`RAG_HOME/.env` 不存在。）

---

### ⑥ rag-service · 检索路由

[application.yml:84-89](it-ticket-cloud/rag-service/src/main/resources/application.yml:84)

```yaml
rag.retrieval:
  provider: ${RAG_RETRIEVAL_PROVIDER:python}          # python | es
  python-base-url: ${RAG_PYTHON_BASE_URL:http://127.0.0.1:8310}
```

> ⚠️ 默认取 `python`，且 **python 分支失败不静默回落到 ES**。
> 也就是说 8310 没起，每次检索都会以「依赖不可用」收场 → AI 客服全量拒答。
> 回滚是零代码的：设 `RAG_RETRIEVAL_PROVIDER=es`（前提是 ES:9200 起着）。

---

### ⑦ 离线入库流水线（重建向量库时才会用到）

```bash
cd services/python-retrieval
export RAG_HOME=$PWD
python -m rag_pipeline.pipelines.indexing     # 用 EMBED_* + configs/pipeline.yaml
```

产物写入 `artifacts/indexing/chroma_wiki_structured/`，`manifest.json` 记录
`config_fingerprint`（切块+embedding 两节的哈希）与 `embedding_engine`。
检索侧加载前会比对指纹，切片参数变更自动判旧库失效。

**本机现状**：向量库已随仓库提交，**不需要重建**即可跑通问答。

---

### ⑧ workflow_demo（Day17 演示，不在主链路）

[workflow_demo/config.py](services/python-retrieval/workflow_demo/config.py) —
`AGENT_LLM_BASE_URL/API_KEY/MODEL` 优先，回退到 `LLM_BASE_URL/API_KEY/LLM_CHAT_MODEL`。
只有普通对话补全，不需要原生 tools，所以这里用 `kimi-k3` 也行。
**只有跑 `uvicorn workflow_demo.app:app`（:8330）时才需要。**

---

### ⑨ analytics_service（Day21 跨工单聚合归纳）

**两侧都要配**：Python 侧是服务本身，Java 侧是「要不要把请求分流过去」。

[consultation-service/application.yml](it-ticket-cloud/consultation-service/src/main/resources/application.yml) —
`AI_ANALYTICS_ENABLED`（**默认 `true`**）+ `ANALYTICS_SERVICE_BASE_URL`（默认 `http://127.0.0.1:8340`）。
判定为 ANALYTICS 的请求由 `ComposedRagAdapter` 在**领域门禁之后、知识检索之前**分流过去；
前端另有专用看板 `/analytics`（**仅工程师**）。

> ⚠️ **默认开着 = analytics_service 成了硬依赖**。它没启动时，判定为分析型的提问会
> 返回 `503 AI_UNAVAILABLE`（如实拒绝，**不静默回退成知识问答**——回退会让统计请求
> 收到一份单卡答案，那正是这条链路要消灭的答非所问）。
> 只跑其余链路时设 `AI_ANALYTICS_ENABLED=false` 即可关掉分流。
> 这与仓库既有约定一致：`retrieval-provider=rag-service` 同样是默认值，同样要求依赖在线。

[analytics_service/config.py](services/python-retrieval/analytics_service/config.py) —
`ANALYTICS_LLM_BASE_URL/API_KEY/MODEL` 优先，回退到 `LLM_BASE_URL/API_KEY/LLM_CHAT_MODEL`。
`ANALYTICS_TICKET_BASE_URL` 指向 ticket-service 内部接口（默认 `http://127.0.0.1:8201`），
**只走只读投影扫描 `GET /api/internal/tickets/analytics/scan`，不跨库读 ticket 表**（架构 8.1）。

该服务是**确定性节点链**，不是 ReAct：请求理解（意图判定 + 时间/范围/维度槽位抽取）→
投影扫描取数 → **纯 Python 词表抽取 + 聚合**（占比/覆盖率/小样本闸门/备件数量，全部不调
模型）→ 模型只做归因叙事与建议方向 → 数字/单号/标签门禁。模型不可用时走确定性模板，
链路照走。

**两个入口的意图归属不同**：看板入口**不预设** `upstreamIntent`，由分析链路自行判定，
判为非分析型即**熔断**（`REFUSE` / `refusalReason=OUT_OF_SCOPE`，正文指路去智能客服，
只留 2 个 span、不取数）；客服入口由 Java 分类器先定性并透传 `upstreamIntent=ANALYTICS`，
分析链路据此锁死意图、不翻案。**两个入口都不回退成知识问答** —— 回退会让同一个 HTTP
入口按措辞切换成两套链路，答复类型随措辞漂移。

**模型给的是语义槽位，日期与数字都由代码算**：模型输出「本季度」「网络设备」这类槽位，
时间区间由 `timewindow` 算（模型算错季度边界不会报错，只会静默给一个错误的分母）；
槽位里的 `rawText` 必须在提问里字面出现，否则整段作废、退回正则。

三个请求理解开关：`ANALYTICS_MODEL_ROUTING`（置 `0` 则 Node A 不调模型，纯规则+正则，
**回归基线与确定性演示走它**）、`ANALYTICS_ROUTER_MAX_OUTPUT_TOKENS`（默认 2048）、
`ANALYTICS_ROUTER_TIMEOUT`（默认 60s，须小于 `ANALYTICS_LLM_TIMEOUT`）。
**代价：每次分析请求多一次模型调用**（改造前规则命中时是 0 次）。

**两份外置配置**，都参与配置指纹（改了口径就不可复现）：
[configs/taxonomy.yaml](services/python-retrieval/configs/taxonomy.yaml) 是受控词表，
[configs/analytics.yaml](services/python-retrieval/configs/analytics.yaml) 是备件系数
（⚠️ 系数是**演示值**，真实场景应改用历史备件消耗数据反推）。

**只有跑 `python -m analytics_service`（:8340）时才需要。**

---

## 四、三个「同一件事要配两遍」的坑

| # | 坑 | 说明 |
|---|---|---|
| 1 | **命名不一致** | Java 侧读 `EMBEDDING_BASE_URL/API_KEY`，Python 侧读 `EMBED_BASE_URL/API_KEY` —— 同一把 key 写两遍 |
| 2 | **模型选型不一致** | `.env` 的 `LLM_CHAT_MODEL=kimi-k3` 是给 workflow_demo 的；consultation 硬编码 `temperature=0.0` + `response_format=json_object`，kimi-k3 只接受 `temperature=1`，会被网关 400 → 全量 `MODEL_UNAVAILABLE` 拒答（且 `costMs=0`，很误导）。**主链路统一 `deepseek-v4-flash`** |
| 3 | **两套向量库两套维度** | ES 侧 1024 维（Java 请求带 `dimensions=1024` 截断）；chroma 侧 4096 维（Python 不传，取模型原生维度）。**设计如此，别去"统一"** |

---

## 五、最小配置集

密钥只有 **2 个值**（同一个网关的 base_url + 一把 key）：

```bash
# ---- 唯一凭据 ----
MODEL_BASE_URL=https://kspmas.ksyun.com/v1
MODEL_API_KEY=sk-your-key

# ---- consultation-service（:8301）----
AI_PROVIDER=openai-compatible
AI_BASE_URL=$MODEL_BASE_URL
AI_API_KEY=$MODEL_API_KEY
AI_MODEL=deepseek-v4-flash           # 不能用 kimi-k3（temperature=0 + json_object 会被 400）
AI_AGENT_ENABLED=true                # 关闭则失去查工单/建单草稿能力
AGENT_SERVICE_BASE_URL=http://127.0.0.1:8320
RAG_BASE_URL=http://127.0.0.1:8302
TICKET_SERVICE_BASE_URL=http://127.0.0.1:8201

# ---- rag-service（:8302）----
EMBEDDING_BASE_URL=$MODEL_BASE_URL
EMBEDDING_API_KEY=$MODEL_API_KEY
EMBEDDING_MODEL=qwen3-embedding-8b
EMBEDDING_DIMENSIONS=1024
RAG_RETRIEVAL_PROVIDER=python        # 8310 必须起着，否则不回落 ES
RAG_PYTHON_BASE_URL=http://127.0.0.1:8310

# ---- agent_service（:8320）----
AGENT_LLM_BASE_URL=$MODEL_BASE_URL
AGENT_LLM_API_KEY=$MODEL_API_KEY
AGENT_LLM_MODEL=deepseek-v4-flash
AGENT_SERVICE_PORT=8320
KNOWLEDGE_SEARCH_BASE_URL=http://127.0.0.1:8301

# ---- python 检索内核（:8310）—— 命名与 Java 侧不同 ----
EMBED_BASE_URL=$MODEL_BASE_URL
EMBED_API_KEY=$MODEL_API_KEY
EMBED_MODEL=qwen3-embedding-8b
RERANK_BASE_URL=$MODEL_BASE_URL
RERANK_API_KEY=$MODEL_API_KEY
RERANK_MODEL=qwen3-reranker-8b
LLM_BASE_URL=$MODEL_BASE_URL
LLM_API_KEY=$MODEL_API_KEY

# ---- 路径 ----
RAG_HOME=<仓库>/services/python-retrieval
```

现成的可执行版本：`handoff-ai-config/ai-env.ps1`（PowerShell）、`ai-env.sh`（bash）。

---

## 六、启动顺序与自检

**顺序不能乱**（后面的依赖前面的）：

```
py-rag(8310) → agent(8320) → rag-service(8302) → consultation(8301)
前置：Redis(6379) + Nacos(8848)；MySQL 用 yml 内置的远程库，不用起

分析链路另有两条依赖（默认开关 AI_ANALYTICS_ENABLED=true，所以要一起起）：
  ticket-service(8201)  ← 投影扫描取数来源
  analytics_service(8340) ← 建议最后起，它反过来依赖 8201
```

**自检**（第一步不过就别往下走）：

```bash
curl http://127.0.0.1:8320/api/health   # model_configured:true, ticket/knowledge_configured:true
curl http://127.0.0.1:8310/api/health   # status:UP, chunkCount:144
curl http://127.0.0.1:8302/api/health   # status:UP
curl http://127.0.0.1:8340/api/health   # status:UP, taxonomy v1.2, policy v1.0
IT_GATEWAY_URL=http://127.0.0.1:28080 node acceptance/ai-rag-smoke.mjs
```

最后一条期望四行全 PASS：`OFF_TOPIC` 拒答 / `HIGH_RISK` 拒答 / `UNCERTAIN` 澄清 / 真答案 `ANSWER` + 引用。

分析链路单独验一条（需 ticket-service 在线）：

```bash
curl -s "http://127.0.0.1:8201/api/internal/tickets/analytics/scan?created_after=2026-10-01&created_before=2026-10-26" \
  -H "X-User-Id: U_ENG01" -H "X-User-Role: ENGINEER" -o /dev/null -w "HTTP %{http_code}\n"   # 期望 200
```

---

## 七、改哪一处会影响什么（影响矩阵）

| 改动 | 影响面 | 需要重启 |
|---|---|---|
| `AI_MODEL` 换成 temperature≠0 的模型 | **全部 AI 问答失效**（400 → MODEL_UNAVAILABLE 拒答） | consultation |
| `AI_AGENT_ENABLED` 关掉 | 失去查工单 / 建单草稿 / 补搜知识 | consultation |
| `EMBEDDING_*` 改动 | 知识入库与 ES 检索；**不影响** chroma 主检索路径 | rag-service |
| `EMBED_*` / `RERANK_*` 改动 | 主检索路径的向量化与精排质量 | python 8310 |
| `RAG_RETRIEVAL_PROVIDER=es` | 检索改走 ES 双路（需 ES:9200） | rag-service |
| `pipeline.yaml` 的切块/embedding 段 | 向量库指纹失效 → **需重建索引** | 重建 |
| `rag-citation-min-score` / `reject_threshold` | 引用门槛与拒答率，直接影响"答不答" | 对应服务 |

---

## 八、部署侧（生产）另有一套注入路径

本地开发**不用碰**，但要知道存在：

- [it-ticket-cloud/deploy/.env.example](it-ticket-cloud/deploy/.env.example) → 服务器上的 `.env`
- [docker-compose.yml:167-230](it-ticket-cloud/deploy/docker-compose.yml:167) 注入同一批变量，容器名互访
  （`RAG_BASE_URL=http://rag-service:8302`、`AGENT_SERVICE_BASE_URL=http://agent-service:8320`）
- 差异：agent-service 的 `AGENT_LLM_*` 直接复用 `AI_BASE_URL` / `AI_API_KEY`，模型用 `AI_AGENT_MODEL`
- 镜像需单独构建：`docker build -t <PREFIX>/it-ticket-python-ai services/python-retrieval`
- `ai-secrets.yml` 在镜像内被 `.dockerignore` 排除，`optional:file:` 缺失静默跳过

**Nacos 覆盖**（可选）：`NACOS_CONFIG_ENABLED=true` 时，
`consultation-service-dev.yaml` / `common-config.yaml` 可覆盖上述变量。本机未启用（Nacos 内 0 条配置）。

---

## 九、相邻但不算 AI 配置

配错了也会让"AI 客服有问题"，排查时别漏：

| 项 | 默认 | 说明 |
|---|---|---|
| `frontend/.env.local` 的 `API_PROXY_TARGET` | 无（`.env.example` 写 28080） | 前端代理目标，**不含 AI 密钥**；端口与网关必须一致 |
| 网关端口 | `8080` | 本机被 Dify 占用，实际跑 `--server.port=28080` |
| `ES_HOST` / `ES_PORT` | `localhost:9200` | 只有走 ES 检索或知识入库才需要 |
| MySQL 地址 | yml 内置远程库 `120.92.138.195` | 不用额外配 |
| `JWT_SECRET` | dev 内置默认 | 生产必须注入 |
