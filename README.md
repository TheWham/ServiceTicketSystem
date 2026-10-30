# IT 服务工单系统

> 企业级 IT 服务工单管理系统，覆盖**提单 → 自动路由 → 处理 → 验收 → 评价**完整闭环，并内置 **RAG 智能客服**（知识检索 → 受约束生成 → 引用复核 → 转人工）。
> 后端 Spring Cloud 微服务（5 个 Java 服务 + 2 个 Python AI 服务），前端 Vue 3 + Element Plus，业务规则对齐 [PRD-Ultimate 2.2](docs/IT服务工单系统PRD-Ultimate.md)。

---

## 架构总览

```
                     ┌──────────────────────────────┐
      浏览器(:5175)   │  Vue3 + Element Plus 前端     │
            │         └──────────────────────────────┘
            │  /api/**  (vite proxy → 8080)
            ▼
 ┌──────────────────────┐   lb:// (Nacos 服务发现)
 │   gateway  :8080     │─────────────────────────────┐
 │  JWT 统一鉴权/路由/   │  透传 X-User-Id/Name/Role/Dept
 │  CORS/白名单         │──────────┬──────────────────┤
 └──────────────────────┘          ▼                  ▼
        ┌──────────────┬───────────────┬─────────────────────┐
        ▼              ▼               ▼                     ▼
 ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐ ┌─────────────┐
 │ user-service│ │ ticket-service│ │ consultation-    │ │ rag-service │
 │   :8101     │ │   :8201      │ │ service :8301    │ │   :8302     │
 │ 登录/JWT/   │ │ 工单/状态机/  │ │ AI 咨询/转人工/  │ │ 知识入库/   │
 │ 账号/草稿   │ │ 路由/SLA/    │ │ 知识搜索/反馈    │ │ 生命周期/   │
 │             │ │ 通知/异常队列 │ │   ▲ HTTP 检索/生成│ │ ES 复核/编排│
 └──────┬──────┘ └─────┬────────┘ └──────┬─────┬─────┘ └──────┬──────┘
        │  Feign /internal   │  Feign /internal│     │              │
        └───────────┬────────┴─────────────────┘     │              │
                    ▼                                │ HTTP         │ HTTP
      ┌──────────────────────────────┐               ▼              ▼
      │ MySQL it_ticket_system :3306 │   ┌──────────────────┐ ┌──────────────────┐
      │ 单库 42 张表（默认远程库）    │   │ rag_service      │ │ agent_service    │
      └──────────────────────────────┘   │ :8310 (Python)   │ │ :8320 (Python)   │
      ┌──────────────────────────────┐   │ 向量化+双路召回   │ │ ReAct+函数调用   │
      │ Elasticsearch :9200          │   │ RRF+精排+拒答    │ │ 白名单工具       │
      │ 知识向量/全文混合检索         │   └──────────────────┘ └──────────────────┘
      └──────────────────────────────┘    （共用 KSP OpenAI 兼容模型网关：对话/embedding/rerank）
      ┌──────────────────────────────┐        ┌──────────────────────────┐
      │ Nacos :8848 注册/配置中心     │        │ Redis :6379 反馈幂等缓存  │
      └──────────────────────────────┘        └──────────────────────────┘
```

| 服务 | 端口 | 职责 |
|:---|:---|:---|
| gateway | 8080 | 唯一入口：JWT 校验（白名单）、校验用户 ACTIVE、剥离/注入 `X-User-*` 透传头、路由、CORS |
| user-service | 8101 | 登录（BCrypt+JWT）、忘记/修改密码、账号管理（建号/改角色/重置密码）、用户查询、提单草稿 |
| ticket-service | 8201 | 工单全业务：提单（幂等）、自动路由、9 态状态机、优先级矩阵、SLA 计时、通知、异常队列、照片附件、**派单草案（HITL 写操作门禁）** |
| consultation-service | 8301 | 智能客服编排：AI 咨询（问答/澄清/拒答）、知识搜索、转人工与人工会话、咨询附件、AI 反馈、**确认建单（人机回环）** |
| rag-service | 8302 | RAG 编排：知识生命周期状态机、文档入库、检索结果 ④ MySQL PUBLISHED 复核、AI 反馈沉淀知识；检索内核默认下沉 Python `rag_service`（provider 可切 `es` 回滚） |
| rag_service（Python） | 8310 | 检索内核：自适应意图路由 + 向量/BM25 双路召回 + RRF + Cross-Encoder 精排 + GraphRAG (Neo4j 多跳因果推导 + Docstore 回溯) + 版本消歧 `/api/v1/policy/resolve` |
| agent_service（Python） | 8320 | 生成侧：Function Calling（ReAct 循环 + 白名单工具：查本人工单/产建单草稿/补搜知识），带 Trace→Span→Generation 链路追踪；`AI_AGENT_ENABLED=true` 时由 consultation-service 调用 |
| Neo4j 图数据库 | 7687 / 7474 | 知识图谱：全量 38 篇 IT 卡片实体三元组拓扑存储、2-Hop 关联推导与废止剪枝（Bolt: 7687，控制台: 7474） |
| common / common-web | — | 统一 Result/错误码/JWT 工具；全局异常、`UserContext` 透传头解析、时间格式 |

> 职责边界：consultation-service 不做检索与模型托管（检索在 rag-service/Python，对话状态在本服务）；rag-service 不做大模型生成（生成在 consultation-service/agent_service）；Python 侧不落业务库（工单是 ticket-service 事实源，知识以 MySQL PUBLISHED 为准，Java 侧复核后才可信）。模型端点统一走 OpenAI 兼容网关（对话 + embedding + rerank）。

## 技术栈

| 层 | 技术 |
|:---|:---|
| 前端 | Vue 3.4 + Vite 5 + Pinia + Vue Router 4 + Element Plus 2.8 + Axios（+ reka-ui 命令面板） |
| 后端 | Java 17 + Spring Boot 3.2.5 + Spring Cloud 2023.0.1 + Spring Cloud Alibaba 2023.0.1.2 |
| ORM / 认证 | MyBatis-Plus 3.5.7；JWT(HS256) + BCrypt，网关统一鉴权 |
| AI 服务 | Python ≥ 3.11 + FastAPI + Pydantic v2：rag_service（检索内核）+ agent_service（ReAct 智能体） |
| 数据库 | MySQL 8，统一单库 `it_ticket_system`（42 张表，含 `dispatch_draft`），持久化时间统一 UTC |
| 中间件 | Nacos 2.3.2（注册中心 + 可选配置中心）、Redis 8.2.9（AI 反馈幂等标记）、Elasticsearch 8.11.3（知识向量/BM25 混合检索） |
| AI 模型 | OpenAI 兼容端点：对话模型（判定 + 受约束生成 + Function Calling）+ embedding（1024 维）+ rerank（Cross-Encoder） |

## 项目结构

```
it-ticket-system/
├── it-ticket-cloud/          # Spring Cloud 微服务后端（父 POM）
│   ├── gateway/              # 网关 :8080 —— AuthGlobalFilter + 路由（ticket 路由含 /ticket-drafts、/dispatch-drafts）
│   ├── user-service/         # :8101 —— 认证/账号/提单草稿（+ /api/internal/users Feign 接口）
│   ├── ticket-service/       # :8201 —— 工单/状态机/路由/SLA/通知/异常/附件/派单草案门禁
│   ├── consultation-service/ # :8301 —— AI 咨询编排/确认建单/转人工/知识搜索（RAG-INTEGRATION.md）
│   ├── rag-service/          # :8302 —— 知识生命周期/入库/复核；检索 provider=python|es（INTEGRATION.md）
│   ├── common/               # Result/错误码/JwtUtil（纯 Java，gateway 可引用）
│   ├── common-web/           # 全局异常、UserContext 透传头解析、时间序列化
│   ├── db/                   # init/ 建表+种子(42 表) | migration/ V2.0~V2.5 版本化迁移 | tools/ schema 与语料构建脚本
│   ├── nacos-config/         # Nacos 配置中心 DataId 样例 + 导入 zip + 说明（可选开关）
│   ├── scripts/              # Windows 脚本：init-db/start-all/start-nacos/start-redis/start-ai（一键起 4 个 AI 服务）/ai-env
│   ├── redis/                # 本地 Redis 便携包说明与 redis.conf
│   ├── deploy/               # 服务器部署：docker-compose.yml（7 服务）+ .env.example + README（GHCR 流程）
│   ├── docker-compose.yml    # 本地基础设施：nacos + mysql + redis
│   ├── ai-secrets.example.yml# 模型密钥模板（复制为 ai-secrets.yml，已 gitignore）
│   └── README.md             # 微服务版详细技术文档 ⭐
├── frontend/                 # Vue 3 前端（dev :5175，Playwright 测试 :5176）
│   └── src/
│       ├── api/              # Axios 封装（自动注入 Bearer；咨询侧独立实例 + Idempotency-Key）
│       ├── router/           # 路由 + 角色守卫（EMPLOYEE/ENGINEER/PLATFORM_ADMIN/KNOWLEDGE_ADMIN）
│       ├── views/            # 员工服务台 / 智能客服 / 工程师工作台 / 主管派单(含 HITL 草案裁决) / 账号管理 / 知识管理
│       ├── components/       # ConsultationChat、NotificationBell、SlaBadge/SlaTimer、WorkspaceSearch...
│       └── styles/           # service-desk.css + future-desk.css（见 design-system/）
├── acceptance/               # 验收评测：pytest 27 项用例（提单链路 P0）+ ai-rag-smoke.mjs RAG 冒烟
├── services/
│   └── python-retrieval/     # Python AI 服务（单目录两个服务 + 共享内核）
│       ├── rag_service/      # 检索服务 :8310 —— /api/v1/rag/retrievals、/api/v1/policy/resolve、/api/health
│       ├── agent_service/    # ReAct 智能体 :8320 —— /api/v1/agent/chat、/api/health（见其 README.md）
│       ├── rag_pipeline/     # 共享内核：config/chunking/embedding/store/retrieval/policy/observability/evaluation
│       ├── configs/          # pipeline.yaml 检索唯一配置源
│       ├── artifacts/        # wiki 语料卡片 + chroma 向量库（manifest 指纹校验）
│       ├── tools/            # sync 灌库 / check_contract 契约校验 / run_service_regression 回归 / freeze 基线
│       ├── Dockerfile        # 单镜像承载两个服务（EXPOSE 8310 8320）
│       └── docs/runbook-python-retrieval.md  # 运维手册 ⭐
├── design-system/            # it-service-desk 已实施设计规范（MASTER.md）
├── db/                       # 根级单文件初始化脚本 it_ticket_system_init_v2.sql（41 表，可能落后于 db/init，以 db/init/00-schema.sql 为准）
├── docs/                     # PRD、需求归因文档、技术 SPEC、验收协议 V2、specs/ 契约 01-11、superpowers/ 设计与计划
├── .github/workflows/        # docker-ghcr.yml：构建 7 个镜像推 GHCR
└── README.md                 # 本文档
```

## 快速开始

**环境要求**：JDK 17、Maven（无 wrapper，需自装）、Node.js（≥18，Vite 5）、Python ≥ 3.11（AI 全链路需要）、MySQL 8（默认连远程库，可免本地安装）。Windows 下中间件可用 Docker 或项目自带脚本。

### 0. 初始化数据库（首次）

数据库默认连远程库（主机经 `MYSQL_HOST` 覆盖，库名 `it_ticket_system`），无需本地起 MySQL：

```bash
cd it-ticket-cloud
scripts\init-db.cmd        # 建表 + 种子；用 MYSQL_HOST/PORT/USERNAME/PASSWORD 覆盖目标库
```

> 脚本仅用于**空库**。存量库请走 `db/migration` 的版本化迁移说明（V2.0~V2.5，最新含 `dispatch_draft`），勿用空库脚本覆盖数据。根目录 `db/it_ticket_system_init_v2.sql` 为旧生成器产物（41 表），**以 `it-ticket-cloud/db/init/00-schema.sql`（42 表）为准**。

### 1. 起中间件

| 中间件 | 有 Docker | 无 Docker（Windows） |
|:---|:---|:---|
| Nacos :8848 | `docker compose up -d nacos`（在 it-ticket-cloud/） | `scripts\start-nacos.cmd` |
| Redis :6379 | `docker compose up -d redis` | `scripts\start-redis.ps1` |
| Elasticsearch :9200 | 在 `rag-service/` 下 `docker compose up -d` | `scripts\start-elasticsearch.ps1` |

> MySQL 默认连远程库，不用起；`scripts\start-mysql-local.cmd` 可选。只用工单核心链路（不起 AI 咨询）时可跳过 Redis 和 ES。

### 2. 构建并启动后端（5 个 Java 服务）

```bash
cd it-ticket-cloud
mvn package -DskipTests

# 推荐顺序：user → rag → consultation → ticket → gateway
java -jar user-service/target/it-ticket-user-service-1.0.0.jar
java -jar rag-service/target/it-ticket-rag-service-1.0.0.jar
java -jar consultation-service/target/it-ticket-consultation-service-1.0.0.jar
java -jar ticket-service/target/it-ticket-ticket-service-1.0.0.jar
java -jar gateway/target/it-ticket-gateway-1.0.0.jar
```

也可在 IDEA 中分别启动 5 个 Application（IDE 编译需 `-parameters`，父 POM 已配置）。`scripts\start-all.cmd` 一键起 Redis/MySQL/Nacos + gateway/user/ticket 三个核心服务。

**AI 全链路（两个 Python 服务 + 两个 AI Java 服务）**：`scripts\start-ai.ps1` 一键按依赖顺序启动 rag_service(8310) → agent_service(8320) → rag-service(8302) → consultation-service(8301)（模型凭据集中在 `scripts/ai-env.ps1` 注入）；也可手动：

```bash
cd services/python-retrieval
pip install -r rag_service/requirements.txt -r agent_service/requirements.txt

# ① 检索内核（配置 EMBED_*/RERANK_*/LLM_* 从服务目录 .env 兜底，裸启动即可；进程环境变量仍可覆盖）
python -m rag_service                        # 127.0.0.1:8310

# ② ReAct 智能体（需支持原生 tools 的生成模型；凭据同样可写入服务目录 .env，与 ① 共享）
export AGENT_LLM_BASE_URL=... AGENT_LLM_API_KEY=... AGENT_LLM_MODEL=deepseek-v4-flash
export TICKET_SERVICE_BASE_URL=http://127.0.0.1:8201
export KNOWLEDGE_SEARCH_BASE_URL=http://127.0.0.1:8301
python -m agent_service                      # 127.0.0.1:8320
```

Java 侧开关：`rag-service` 检索 provider 默认 `python`（`RAG_PYTHON_BASE_URL=http://127.0.0.1:8310`，回滚 ES 设 `RAG_RETRIEVAL_PROVIDER=es`）；consultation-service 生成侧下沉默认关闭（`AI_AGENT_ENABLED=true` + `AGENT_SERVICE_BASE_URL=http://127.0.0.1:8320` 开启）。

**先灌库（Python 检索联调先决）**：Java rag-service 启动后，先跑 `python tools/sync_wiki_to_rag_service.py` 把 Wiki 卡灌进 rag-service 的 MySQL+ES 并产出 `data/wiki_article_mapping.json`——否则 Python 返回的 articleId 过不了 Java 侧 ④ MySQL PUBLISHED 复核，items 恒为空（表现为 8310 有结果、8302 空）。详见 [services/python-retrieval/docs/runbook-python-retrieval.md](services/python-retrieval/docs/runbook-python-retrieval.md)。

**模型凭据**：`it-ticket-cloud/` 下复制 `ai-secrets.yml` 为 `ai-secrets.yml`（已 gitignore），`AI_SECRETS_FILE`/`RAG_SECRETS_FILE` 指向它；也可用 `AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL`/`EMBEDDING_*` 环境变量注入。密钥缺失时仅 AI 问答降级（NOT_CONFIGURED），知识搜索/人工咨询/工单链路不受影响。

> ⚠️ **`./ai-secrets.yml` 相对运行工作目录解析**——IDEA 默认工作目录是 `$MODULE_WORKING_DIR$`（模块根），
> 但若运行配置的工作目录指到了项目根或仓库根，模块根的文件就读不到，表现为 AI 问答一律
> 「服务暂时不可用」（日志 `errorClass=NOT_CONFIGURED`，costMs=0）。两种解法：把文件放到
> 工作目录所在的那层；或在运行配置里把 Working directory 固定为 `$MODULE_WORKING_DIR$`。
> 排查入口：先看日志里是不是 `NOT_CONFIGURED`——它意味着凭据为空（文件没读到或环境变量没设），
> 而不是服务连不通。`agent.enabled: true`（或环境变量 `AI_AGENT_ENABLED=true`）也在同一文件里，
> 缺了它 Function Calling 智能体（查工单/建单）整体不可用。

**验证**：各服务健康检查均为 `GET /api/health`，如 `curl http://127.0.0.1:8080/api/health`。

### 3. 起前端

```bash
cd frontend
npm install
echo API_PROXY_TARGET=http://127.0.0.1:8080 > .env.local   # 重要：缺省 28080 是过时值
npm run dev                                                # http://127.0.0.1:5175
```

### 4. 登录

种子账号 4 个，**默认密码均为 `123456`**，角色为 PRD §5.1 大写枚举（忘记密码三要素 = 账号 + 姓名 + 员工号）：

| 用户ID | 员工号 | 姓名 | 角色 | 主页 |
|:---|:---|:---|:---|:---|
| U_EMP01 | E1001 | 演示员工 | EMPLOYEE | `/employee`（服务台 + 智能客服） |
| U_ENG01 | E2001 | 演示工程师 | ENGINEER | `/engineer`（工单池/任务/人工咨询） |
| U_ADM01 | E3001 | 平台管理员 | PLATFORM_ADMIN | `/supervisor`（派单草案裁决/账号管理） |
| U_KBA02 | E4002 | 知识库管理员 | KNOWLEDGE_ADMIN | `/knowledge-admin`（文档导入/知识审核发布） |

## 核心功能

### 工单闭环（ticket-service）

- **提单**：七字段校验（标题 ≤50、五分类、优先级、描述 10~500 字、附件 jpg/png 单张 ≤5MB 最多 3 张、期望完成时间、资产编号 CMDB 回显）、`Idempotency-Key` 幂等防重、3s 防抖、工单号 `TK+日期+流水`、服务端草稿（`/api/v1/ticket-drafts`，登录后可恢复）。
- **自动路由（F-06）+ HITL 派单门禁**：按分类路由规则（`category_route`）定位支持组，组内按加权负载选工程师；**路由不再直接写 assignment，而是产出 `dispatch_draft`（PENDING，带 expires_at）**，管理员在 `/supervisor` 认领（防双人同裁）→ 核对载荷 → approve（工单 NEW→ASSIGNED 并通知工程师）/ reject（工单保持 NEW）后生效；超时未确认由定时任务自动 EXPIRED 并通知重新路由。路由无候选人时留在 NEW 并进异常队列。
- **9 态状态机（F-07）**：NEW / ASSIGNED / IN_PROGRESS / PENDING_SUPPLEMENT / PENDING_EXTERNAL / PENDING_ACCEPTANCE / COMPLETED / CANCELLED / CLOSED，声明式流转边 + 角色/业务守卫三重校验；每次流转写只追加的 `ticket_transition`。
- **自动流转**：响应超时自动转派、72h 未补充自动关闭、48h 未验收自动通过、7 日内复发自动重开；员工撤销、管理员异常关闭/标记重复单。
- **SLA（F-08）**：HIGH 4 工作小时 / MEDIUM 1 工作日 / LOW 3 工作日，按工作日历只计工作时间，补充/外部等待暂停计时，超时自动转异常处理；前端 SlaBadge/SlaTimer 以服务端剩余工作秒为基准倒计时。
- **通知（F-10）**：流转事件驱动，按 `event_id+receiver+channel` 生命周期幂等去重；前端 NotificationBell 轮询未读数，点击跳转对应工作台并自动打开工单详情。
- **其他**：接单时「影响×紧急」3×3 矩阵定优先级并触发 SLA 重算、提单人编辑重新提交、照片上传与三端预览、评价 1-5 星、主管删除工单、主管改用户角色。

### AI 咨询与 RAG（consultation-service + rag-service + Python AI 服务）

- **检索内核（rag_service :8310，rag-service 的默认 provider）**：向量化 + BM25 双路召回 → RRF 融合 → Cross-Encoder 精排 → 低置信拒答；LLM 查询改写（原查询+改写查询四路召回，超时回落原查询）；另有 `POST /api/v1/policy/resolve` 版本消歧（解析某时刻有效规约版本，`RESOLVED/NO_EFFECTIVE_VERSION/UNDATED/NO_MATCH` 四态）。python 分支失败**不静默回退 ES**；回滚零代码：`RAG_RETRIEVAL_PROVIDER=es`。
- **检索编排（rag-service :8302）**：文档上传（≤20MB）→ 解析 → 切片 → embedding → ES `knowledge_chunk` 索引，四阶段流水线带全链路 trace；Python 返回的 articleId/versionId 必须经 ④ MySQL PUBLISHED 复核才可信；知识生命周期状态机 DRAFT → PENDING_REVIEW → PUBLISHED → OFFLINE（作者不得自审 AC-25，发布后写 ES 失败标 PENDING_COMPENSATION 可补偿重建）。
- **领域四态判定**：`OFFICE_IT`（正常回答）/ `OFF_TOPIC`（拒答）/ `HIGH_RISK`（14 个高危关键词，拒答 + 引导人工）/ `UNCERTAIN`（追问澄清），先于检索、独立判定。
- **受约束生成（双轨）**：默认单轮受约束生成；开启 `AI_AGENT_ENABLED` 后生成侧下沉 Python `agent_service`——ReAct 循环 + 白名单工具（`search_knowledge` 查已发布知识 / `query_my_tickets` 查本人工单 / `prepare_ticket` 只产建单草稿不落库），6 键结构化 JSON 返回，Trace→Span→Generation 全链追踪（traceId 复用 `X-Request-Id`）。
- **人机回环（确认建单）**：AI 无法自行建单——`prepare_ticket` 草稿随响应返回；前端会跳转新建工单页并自动预填，员工编辑确认后走正常建单接口。
- **引用双重复核**：生成前锁定读复核 PUBLISHED 版本，生成后 AiAnswerGuard 复核；引用由服务端从实际资料重建，模型编造 versionId 即整次输出无效。引用分数阈值 0.70。
- **降级语义（RD-006）**：模型/检索故障统一表达为结构化拒答 + `suggestTransfer=true`，不静默回退、不把服务故障解释为"无命中"；密钥缺失仅 AI 问答降级，知识搜索/人工咨询不受影响。
- **转人工**：加权负载选工程师（候选上限 8）→ 10 工作分钟响应 SLA → 人工会话 → 提交结论 → 员工确认 → 24h 内可重开；可一键转工单（预填标题/描述，经 ticket-service 建单后回写 `CONVERTED_TO_TICKET`）。
- **AI 反馈沉淀**：员工对 AI 回答点"已解决"后，反馈经脱敏自动沉淀为待审核知识文章（Redis 幂等标记，5s 扫描 `ai_interaction`），审核发布后进入检索。
- **知识图谱因果推导（GraphRAG，Neo4j 双轨检索）**：
  - **自适应意图路由（Adaptive Query Router）**：单维事实（0ms 纯向量/BM25 检索）vs 多维并发级联故障（触发 GraphRAG 多跳因果推导），内置规则自愈兜底，毫秒级自适应分流。
  - **Neo4j 生产级图数据库（:7687）**：存储 38 篇 IT 卡片抽取出的刚性因果拓扑三元组（实体/关系/属性），支持 2-Hop BFS 关系路径遍历、废止规则替代（REPLACES）、CMDB 资产与网络依赖追溯。
  - **双轨事实抽取与全文回溯**：轨 A 图谱 BFS 提取关联实体与因果三元组（因果关系/排查动作优先排序，截断保真），轨 B 由 MySQL Docstore 自动回溯父块全文，彻底解决纯向量检索在多症状并发、断连孤岛与根因定界上的缺陷。
  - **思维链路徽标与全景拓扑大屏（Vis.js）**：AI 客服回答前置注入 `【知识图谱因果推导】` 提示块，前端自动挂载【🔍 知识图谱因果推导 | 查看思维链路】徽标；点击即开 Vis.js 物理力导向抽屉，并支持一键开启 **「⛶ 大屏全屏显示」**（100vw × 100vh 交互式拓扑画布，支持实体节点拖拽、视角复位、按领域动态染色与实时图谱探索）。
  - **多跳对比评测 Web 工作台（:8350）**：`python tools/run_compare_ui.py` 一键启动，预置 VPN/AD 域并发锁死、CMDB 资产级联、制度废止替代等典型用例，提供纯向量 vs GraphRAG 同屏对照评测。

## API 一览

统一经网关访问 `http://localhost:8080/api/v1/**`。工单/用户等服务响应为 `{code, msg, data}`（`code=0` 成功）；咨询/知识服务为 PRD 21.1 包络 `{code: "SUCCESS", message, request_id, data}`。常用入口：

| 方法 | 路径 | 说明 | 权限 |
|:---|:---|:---|:---|
| GET | /api/health | 健康检查（5 个 Java 服务 + 2 个 Python 服务各自提供） | 免认证 |
| POST | /api/v1/users/login | 登录 `{userId,password}` → `{token,user}` | 免认证 |
| GET | /api/v1/users/login-options | 可登录用户列表 | 免认证 |
| POST | /api/v1/users/forgot-password | 忘记密码（三要素自助重置） | 免认证 |
| GET/POST/DELETE | /api/v1/users/drafts | 提单草稿（每用户一条） | 登录 |
| GET/PUT/DELETE | /api/v1/ticket-drafts/:id | 提单草稿恢复/保存/清理（spec 05） | 登录 |
| GET/POST/PUT/DELETE | /api/v1/users/accounts... | 账号管理（列表/建号/改角色/重置密码） | PLATFORM_ADMIN/KNOWLEDGE_ADMIN |
| GET | /api/v1/categories/leaf | 叶子分类（提单表单下拉） | 登录 |
| POST | /api/v1/tickets | 创建工单（Idempotency-Key 幂等，创建后自动路由产草案） | 登录 |
| GET | /api/v1/tickets | 列表（status/category/assignee/priority/unassigned 等筛选 + 分页） | 登录 |
| POST | /api/v1/tickets/:id/assign | 派单/改派 | PLATFORM_ADMIN |
| POST | /api/v1/tickets/:id/claim | 接单（矩阵确认影响×紧急） | ENGINEER |
| POST | /api/v1/tickets/:id/actions | 状态操作（route/accept/request_supplement/supply_info/external_wait/submit_resolution/reject/cancel/abnormal_close/reopen...） | 状态机校验 |
| POST | /api/v1/tickets/:id/rating | 评价 1-5 星（仅已完成） | 登录 |
| POST | /api/v1/tickets/attachments/upload | 照片上传（另有 /:id/content 下载、DELETE 撤回） | 登录 |
| GET | /api/v1/sla/:ticketId | SLA 计时（剩余工作秒，前端倒计时基准） | 登录 |
| GET | /api/v1/notifications、/pending-count | 通知列表 / 未读数（前端轮询） | 登录 |
| GET | /api/v1/exceptions、/pending-count | 异常队列（路由失败工单） | 管理员 |
| GET | /api/v1/dispatch-drafts | 待确认派单草案列表（管理员待办） | PLATFORM_ADMIN |
| GET | /api/v1/dispatch-drafts/:draftId | 草案详情（核对载荷后裁决） | PLATFORM_ADMIN |
| POST | /api/v1/dispatch-drafts/:draftId/claim | 认领草案（防双人同裁） | PLATFORM_ADMIN |
| POST | /api/v1/dispatch-drafts/:draftId/decide | 裁决草案 approve/reject（门禁放行点） | PLATFORM_ADMIN |
| POST | /api/v1/consultations | 创建咨询会话（AI / 转人工） | 登录 |
| POST | /api/v1/consultations/:id/ai-messages | AI 问答（ANSWER/CLARIFY/REFUSE） | 登录 |
| GET | /api/v1/consultations/:id/ticket-draft | 查看建单草稿 | 登录 |
| POST | /api/v1/consultations/:id/ticket-draft/confirm | 程序化确认建单（人机回环放行点） | 登录 |
| POST | /api/v1/consultations/:id/transfer | 转人工（幂等触发自动分配） | 登录 |
| POST | /api/v1/consultations/:id/messages | 人工会话消息 | 参与者 |
| GET | /api/v1/knowledge/search | 知识搜索（仅 PUBLISHED） | 登录 |
| POST | /api/v1/rag/documents/upload | 文档上传入库（解析→切片→向量化→ES） | 知识管理 |
| POST | /api/v1/rag/retrievals | RAG 检索（Top-K 切片 + 领域判定） | 登录 |
| POST | /api/v1/rag/articles/:id/submit · publish · reject · offline | 知识审核流（按状态/角色守卫） | 知识管理/管理员 |
| POST | /api/v1/agent/chat | ReAct 生成（agent_service，Java 侧经此调用） | 内部（X-User-* 透传） |
| POST | /api/v1/policy/resolve | 版本消歧查询（rag_service） | 内部 |

完整接口契约见 [docs/specs/05-http-api-openapi.yaml](docs/specs/05-http-api-openapi.yaml)（非 AI）与 [docs/specs/02-ai-api-json-schema.md](docs/specs/02-ai-api-json-schema.md)（AI）；错误码与状态机细节见 [it-ticket-cloud/README.md](it-ticket-cloud/README.md)。核心错误码：`40001` 参数校验、`40100/40101` 未登录/禁用、`40300` 权限不足、`40901` 幂等冲突、`40910` 非法状态转移、`40911/40912` 不可领取/已被他人领取、`5031` Python 检索锁超时。

## 测试与验收

| 套件 | 位置 | 命令 | 状态 |
|:---|:---|:---|:---|
| 提单链路验收（pytest，27 项：TC-01~10 + M-01~09 + 状态机/守卫） | `acceptance/` | `python -m pytest -v`；`python scripts/run.py` 生成评测报告 | 27/27 通过（2026-10-08 报告，V2 §4.2 综合判定通过） |
| RAG/AI 咨询端到端冒烟（Node） | `acceptance/ai-rag-smoke.mjs` | `node acceptance/ai-rag-smoke.mjs [--require-answer]`（需网关 + consultation + rag + Python 服务已启动） | 验证领域判定/拒答/引用/持久化 |
| 后端单元/集成测试（JUnit，61 个测试类） | `it-ticket-cloud/*/src/test` | `mvn -pl consultation-service,rag-service -am test`（或按模块） | RAG 集成范围 262 项通过（consultation 206 / rag 48 / gateway 2，见 spec 记录） |
| Python 检索与智能体单测（pytest，70 项） | `services/python-retrieval/{rag_service,agent_service}/tests` | `cd services/python-retrieval && python -m pytest rag_service/tests agent_service/tests -q` | 70/70 通过（2026-10-22 实测；rag_service 68 + agent_service 2） |
| Python 检索 HTTP 契约与回归 | `services/python-retrieval/tools/` | `python tools/check_contract.py`（85 项不变量）；`python tools/run_service_regression.py --pace 1.5`（黄金集 20 题 vs 冻结基线） | 黄金集基线仅对 `query_rewrite=true` 成立 |
| 前端单元/契约测试 | `frontend/tests/*.test.mjs` | `npm test`（node --test，20 个文件） | — |
| 前端浏览器测试（Playwright，8 个 spec） | `frontend/tests/browser/` | `npm run test:browser`（端口 5176） | — |

## 生产部署

镜像经 GitHub Actions（`.github/workflows/docker-ghcr.yml`）构建并推送 GHCR，共 7 个：5 个 Java 服务 + `it-ticket-python-ai`（单镜像承载 rag_service/agent_service，按启动命令区分）+ `it-ticket-frontend`。

```bash
cd it-ticket-cloud/deploy
cp .env.example .env      # 填 IMAGE_PREFIX(ghcr.io/<用户名小写>)、JWT_SECRET、AI_API_KEY、EMBEDDING_*、MYSQL_*、CORS_ORIGINS 等
                          # AI_AGENT_ENABLED 默认 false；开启还需 AGENT 相关变量（见 .env.example 注释）
# 服务器上：
docker compose up -d      # 见 deploy/README.md：镜像 pull、启动顺序、验证、日常更新
```

生产编排（`deploy/docker-compose.yml`）含 **7 个应用服务**（gateway/user/ticket/rag/consultation/agent-service/frontend nginx :10086）+ 自建 Nacos/Redis/ES；MySQL 沿用远程库；基础设施经容器名互访（`RAG_BASE_URL=http://rag-service:8302`、`AGENT_SERVICE_BASE_URL=http://agent-service:8320`）；密钥全部由服务器本地 `.env` 注入，不进镜像不进 git。详见 [deploy/README.md](it-ticket-cloud/deploy/README.md)。

> 旧的一键打包脚本 `pack-local.ps1` + `upgrade-server.sh` 已由 GHCR 镜像流取代，不再维护。

## 配置与环境变量

配置分层：`application.yml`（启动项）→ `application-{profile}.yml`（默认 dev）→ Nacos 可选覆盖（`NACOS_CONFIG_ENABLED=true`，见 [nacos-config/配置管理说明.md](it-ticket-cloud/nacos-config/配置管理说明.md)）。

常用变量（均可在 dev 环境省略，见 `scripts/dotenv-example.env` 与 `deploy/.env.example`）：

| 变量 | 默认 | 说明 |
|:---|:---|:---|
| `MYSQL_HOST/PORT/DB/USERNAME/PASSWORD` | 远程库 / 3306 / it_ticket_system | 数据库连接 |
| `NACOS_ADDR` | 127.0.0.1:8848 | 注册中心 |
| `JWT_SECRET` | dev 内置默认 | **生产必须注入**，缺失启动失败 |
| `RAG_BASE_URL` | http://127.0.0.1:8302 | consultation → rag 检索地址 |
| `RAG_RETRIEVAL_PROVIDER` | python | rag-service 检索内核（`es` 为零代码回滚开关） |
| `RAG_PYTHON_BASE_URL` | http://127.0.0.1:8310 | Python 检索服务地址 |
| `AI_BASE_URL / AI_API_KEY / AI_MODEL` | — | OpenAI 兼容对话模型端点 |
| `EMBEDDING_BASE_URL / EMBEDDING_API_KEY / EMBEDDING_MODEL` | — | embedding 模型（1024 维） |
| `AI_AGENT_ENABLED` | false | 生成侧下沉 Python agent_service（`agent_service/README.md`） |
| `AGENT_SERVICE_BASE_URL` | http://127.0.0.1:8320 | agent_service 地址（开启 AI_AGENT 后生效） |
| `AGENT_LLM_BASE_URL / AGENT_LLM_API_KEY / AGENT_LLM_MODEL` | — | agent_service 生成模型凭据（须支持原生 tools，勿用思考型模型，见 runbook） |
| `TICKET_SERVICE_BASE_URL / KNOWLEDGE_SEARCH_BASE_URL` | — | agent_service 工具依赖（查工单/补搜知识） |
| `AI_SECRETS_FILE / RAG_SECRETS_FILE` | ./ai-secrets.yml | 密钥文件路径（已 gitignore，模板在 it-ticket-cloud/ai-secrets.example.yml） |
| `ES_HOST/PORT/ES_KNOWLEDGE_INDEX` | localhost / 9200 / knowledge_chunk | Elasticsearch |
| `API_PROXY_TARGET` | ~~http://127.0.0.1:28080~~（过时） | **前端代理，请设为 http://127.0.0.1:8080** |

## 文档地图

| 文档 | 说明 |
|:---|:---|
| [docs/IT服务工单系统PRD-Ultimate.md](docs/IT服务工单系统PRD-Ultimate.md) | 业务基线 PRD 2.2（状态机/SLA/通知/路由的唯一依据；根目录同名文件为占位指针） |
| [it-ticket-cloud/README.md](it-ticket-cloud/README.md) | 微服务版详细技术文档（架构/接口/错误码/状态机/数据库/排查指南）⭐ |
| [docs/specs/](docs/specs/README.md) | 一期契约 01~11：数据模型 / AI Schema / 状态机 / 韧性 / OpenAPI / DDL / 事件 / 权限与 SLA / 追溯矩阵 / 模型与 RAG |
| [docs/superpowers/specs/](docs/superpowers/) | 设计文档存档（RAG 咨询组合设计、服务台 UI 设计等）与实施计划 |
| [docs/IT服务工单系统-需求归因文档.md](docs/IT服务工单系统-需求归因文档.md) | HITL 派单门禁等需求归因（「强制人机确认」条目） |
| [services/python-retrieval/docs/runbook-python-retrieval.md](services/python-retrieval/docs/runbook-python-retrieval.md) | Python 检索/智能体运维手册（启动/灌库/联调/已知行为/agent_service）⭐ |
| [services/python-retrieval/agent_service/README.md](services/python-retrieval/agent_service/README.md) | ReAct 智能体：分工边界/白名单工具/人机回环/部署 |
| [services/python-retrieval/README.md](services/python-retrieval/README.md) | rag_service 启动指南（.env/启动/验证/常见问题） |
| [docs/IT服务工单系统-验收评测协议书-V2.md](docs/IT服务工单系统-验收评测协议书-V2.md) | 验收评测协议（指标/用例/判定规则）；实测报告在 `acceptance/reports/` |
| [it-ticket-cloud/consultation-service/RAG-INTEGRATION.md](it-ticket-cloud/consultation-service/RAG-INTEGRATION.md) / [rag-service/INTEGRATION.md](it-ticket-cloud/rag-service/INTEGRATION.md) | RAG 集成契约（检索/引用/阈值/反馈沉淀） |
| [design-system/it-service-desk/MASTER.md](design-system/it-service-desk/MASTER.md) | 已实施的前端设计规范（深空蓝黑 + 电光青，亮/暗双主题） |
| [工单提交流程讲解.md](工单提交流程讲解.md) | 提单链路讲解（AI 预审 → 前置校验 → 后置生成，面向答辩/演示） |
| [AGENTS.md](AGENTS.md) | 工程协作约束（接口变更同步迁移调用方、不做静默回退等） |

## 仓库

- **主仓库（GitHub）**：https://github.com/TheWham/ServiceTicketSystem
- **镜像（Gitee）**：https://gitee.com/early-rise/it-ticket-system
