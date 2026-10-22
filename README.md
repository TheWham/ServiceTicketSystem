# IT 服务工单系统

> 企业级 IT 服务工单管理系统，覆盖**提单 → 自动路由 → 处理 → 验收 → 评价**完整闭环，并内置 **RAG 智能客服**（知识检索 → 受约束生成 → 引用复核 → 转人工）。
> 后端 Spring Cloud 微服务（5 个服务），前端 Vue 3 + Element Plus，业务规则对齐 [PRD-Ultimate 2.2](docs/IT服务工单系统PRD-Ultimate.md)。

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
 │ 账号/草稿   │ │ 路由/SLA/    │ │ 知识搜索/反馈    │ │ 向量化/     │
 │             │ │ 通知/异常队列 │ │   ▲ HTTP 检索    │ │ ES 混合检索 │
 └──────┬──────┘ └─────┬────────┘ └──────┬───────────┘ └──────┬──────┘
        │  Feign /internal   │  Feign /internal  │              │
        └───────────┬────────┴───────────────────┘              │
                    ▼                                           ▼
      ┌──────────────────────────────┐        ┌──────────────────────────┐
      │ MySQL it_ticket_system :3306 │        │ Elasticsearch :9200      │
      │ 单库 41 张表（默认远程库）     │        │ 知识向量/全文混合检索      │
      └──────────────────────────────┘        └──────────────────────────┘
      ┌──────────────────────────────┐        ┌──────────────────────────┐
      │ Nacos :8848 注册/配置中心     │        │ Redis :6379 反馈幂等缓存  │
      └──────────────────────────────┘        └──────────────────────────┘
```

| 服务 | 端口 | 职责 |
|:---|:---|:---|
| gateway | 8080 | 唯一入口：JWT 校验（白名单）、校验用户 ACTIVE、剥离/注入 `X-User-*` 透传头、路由、CORS |
| user-service | 8101 | 登录（BCrypt+JWT）、忘记/修改密码、账号管理（建号/改角色/重置密码）、用户查询、提单草稿 |
| ticket-service | 8201 | 工单全业务：提单（幂等）、自动路由、9 态状态机、优先级矩阵、SLA 计时、通知、异常队列、照片附件 |
| consultation-service | 8301 | 智能客服：AI 咨询（问答/澄清/拒答）、知识搜索、转人工与人工会话、咨询附件、AI 反馈、转工单预填 |
| rag-service | 8302 | RAG 知识库：文档入库流水线（解析→切片→向量化→ES 索引）、知识生命周期状态机、ES 混合检索、AI 反馈沉淀知识 |
| common / common-web | — | 统一 Result/错误码/JWT 工具；全局异常、`UserContext` 透传头解析、时间格式 |

> consultation-service 不做检索与模型托管（检索在 rag-service、对话状态在本服务）；rag-service 不做大模型生成。两服务共用 OpenAI 兼容端点（对话模型 + embedding 模型）。

## 技术栈

| 层 | 技术 |
|:---|:---|
| 前端 | Vue 3.4 + Vite 5 + Pinia + Vue Router 4 + Element Plus 2.8 + Axios（+ reka-ui 命令面板） |
| 后端 | Java 17 + Spring Boot 3.2.5 + Spring Cloud 2023.0.1 + Spring Cloud Alibaba 2023.0.1.2 |
| ORM / 认证 | MyBatis-Plus 3.5.7；JWT(HS256) + BCrypt，网关统一鉴权 |
| 数据库 | MySQL 8，统一单库 `it_ticket_system`（41 张表），持久化时间统一 UTC |
| 中间件 | Nacos 2.3.2（注册中心 + 可选配置中心）、Redis 8.2.9（AI 反馈幂等标记）、Elasticsearch 8.11.3（知识向量/BM25 混合检索） |
| AI | OpenAI 兼容端点：对话模型（判定 + 受约束生成）+ embedding 模型（1024 维） |

## 项目结构

```
it-ticket-system/
├── it-ticket-cloud/          # Spring Cloud 微服务后端（父 POM）
│   ├── gateway/              # 网关 :8080 —— AuthGlobalFilter + 8 条路由
│   ├── user-service/         # :8101 —— 认证/账号/草稿（+ /api/internal/users Feign 接口）
│   ├── ticket-service/       # :8201 —— 工单/状态机/路由/SLA/通知/异常/附件
│   ├── consultation-service/ # :8301 —— AI 咨询/转人工/知识搜索（RAG-INTEGRATION.md）
│   ├── rag-service/          # :8302 —— 知识入库流水线/生命周期/ES 检索（INTEGRATION.md）
│   ├── common/               # Result/错误码/JwtUtil（纯 Java，gateway 可引用）
│   ├── common-web/           # 全局异常、UserContext 透传头解析、时间序列化
│   ├── db/                   # init/ 建表+种子 | migration/ 版本化迁移 | tools/ schema 与语料构建脚本
│   ├── nacos-config/         # Nacos 配置中心 DataId 样例 + 导入 zip + 说明（可选开关）
│   ├── scripts/              # Windows 一键脚本：start-all/init-db/start-nacos/start-redis/...
│   ├── redis/                # 本地 Redis 便携包说明与 redis.conf
│   ├── deploy/               # 生产部署：pack-local.ps1 打包 + upgrade-server.sh 换版 + docker-compose.prod.yml
│   ├── docker-compose.yml    # nacos + mysql(可选本地) + redis
│   └── README.md             # 微服务版详细技术文档 ⭐
├── frontend/                 # Vue 3 前端（dev :5175，Playwright 测试 :5176）
│   └── src/
<<<<<<< HEAD
│       ├── api/              # Axios 封装（自动注入 Bearer；咨询侧独立实例 + Idempotency-Key）
│       ├── router/           # 路由 + 角色守卫（EMPLOYEE/ENGINEER/PLATFORM_ADMIN/KNOWLEDGE_ADMIN）
│       ├── views/            # 员工服务台 / 智能客服 / 工程师工作台 / 主管派单 / 账号管理 / 知识管理
│       ├── components/       # ConsultationChat、NotificationBell、SlaBadge/SlaTimer、WorkspaceSearch...
│       └── styles/           # service-desk.css + future-desk.css（见 design-system/）
├── acceptance/               # 验收评测：pytest 27 项用例（提单链路 P0）+ ai-rag-smoke.mjs RAG 冒烟
├── services/
│   └── python-retrieval/     # Python RAG 检索内核 + HTTP 服务（rag-service provider=python 的后端）
├── design-system/            # it-service-desk 已实施设计规范（MASTER.md）
├── db/                       # 根级单文件初始化脚本 it_ticket_system_init_v2.sql（41 表，与 db/init 等价）
├── docs/                     # PRD、技术 SPEC、验收协议 V2、specs/ 契约 01-11、superpowers/ 设计与计划
└── README.md                 # 本文档
```

## 快速开始

**环境要求**：JDK 17、Maven（无 wrapper，需自装）、Node.js（≥18，Vite 5）、MySQL 8（默认连远程库，可免本地安装）。Windows 下中间件可用 Docker 或项目自带脚本。

### 0. 初始化数据库（首次）

数据库默认连远程库（主机经 `MYSQL_HOST` 覆盖，库名 `it_ticket_system`），无需本地起 MySQL：

```bash
cd it-ticket-cloud
scripts\init-db.cmd        # 建表 + 种子；用 MYSQL_HOST/PORT/USERNAME/PASSWORD 覆盖目标库
```

> 脚本仅用于**空库**。存量库请走 `db/migration` 的版本化迁移说明，勿用空库脚本覆盖数据。等价入口：根目录 `db/it_ticket_system_init_v2.sql`（同一生成器产物，勿对同一库重复执行）。

### 1. 起中间件

| 中间件 | 有 Docker | 无 Docker（Windows） |
|:---|:---|:---|
| Nacos :8848 | `docker compose up -d nacos`（在 it-ticket-cloud/） | `scripts\start-nacos.cmd` |
| Redis :6379 | `docker compose up -d redis` | `scripts\start-redis.ps1` |
| Elasticsearch :9200 | 在 `rag-service/` 下 `docker compose up -d` | `scripts\start-elasticsearch.ps1` |

> MySQL 默认连远程库，不用起；`scripts\start-mysql-local.cmd` 可选。只用工单核心链路（不起 AI 咨询）时可跳过 Redis 和 ES。

### 2. 构建并启动后端（5 个服务）

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

也可在 IDEA 中分别启动 5 个 Application（IDE 编译需 `-parameters`，父 POM 已配置）。`scripts\start-all.cmd` 一键起中间件 + gateway/user/ticket 三个核心服务。

**AI 配置**：`consultation-service/` 与 `rag-service/` 目录下复制 `ai-secrets.example.yml` 为 `ai-secrets.yml`（已 gitignore），填入模型端点与密钥（`AI_SECRETS_FILE`/`RAG_SECRETS_FILE` 可指向同一文件）；也可用 `AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL`/`EMBEDDING_*` 环境变量注入。

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
| U_ADM01 | E3001 | 平台管理员 | PLATFORM_ADMIN | `/supervisor`（派单/账号管理） |
| U_KBA01 | E4001 | 知识库管理员 | KNOWLEDGE_ADMIN | `/knowledge-admin`（文档导入/知识审核发布） |

## 核心功能

### 工单闭环（ticket-service）

- **提单**：七字段校验（标题 ≤50、五分类、优先级、描述 10~500 字、附件 jpg/png 单张 ≤5MB 最多 3 张、期望完成时间、资产编号 CMDB 回显）、`Idempotency-Key` 幂等防重、3s 防抖、工单号 `TK+日期+流水`、服务端草稿。
- **自动路由（F-06）**：按分类路由规则（`category_route`）定位支持组，组内按加权负载选工程师；无候选人留在 NEW 并进异常队列，由管理员处理。
- **9 态状态机（F-07）**：NEW / ASSIGNED / IN_PROGRESS / PENDING_SUPPLEMENT / PENDING_EXTERNAL / PENDING_ACCEPTANCE / COMPLETED / CANCELLED / CLOSED，声明式流转边 + 角色/业务守卫三重校验；每次流转写只追加的 `ticket_transition`。
- **自动流转**：响应超时自动转派、72h 未补充自动关闭、48h 未验收自动通过、7 日内复发自动重开；员工撤销、管理员异常关闭/标记重复单。
- **SLA（F-08）**：HIGH 4 工作小时 / MEDIUM 1 工作日 / LOW 3 工作日，按工作日历只计工作时间，补充/外部等待暂停计时，超时自动转异常处理；前端 SlaBadge/SlaTimer 以服务端剩余工作秒为基准倒计时。
- **通知（F-10）**：流转事件驱动，按 `event_id+receiver+channel` 生命周期幂等去重；前端 NotificationBell 轮询未读数，点击跳转对应工作台并自动打开工单详情。
- **其他**：接单时「影响×紧急」3×3 矩阵定优先级并触发 SLA 重算、提单人编辑重新提交、照片上传与三端预览、评价 1-5 星、主管删除工单、主管改用户角色。

### AI 咨询与 RAG（consultation-service + rag-service）

- **检索（rag-service）**：文档上传（≤20MB）→ 解析 → 按标题层级/滑动窗口切片 → embedding（1024 维）→ ES `knowledge_chunk` 索引，四阶段流水线带全链路 trace；检索为向量 + BM25 混合排序，引用分数阈值 0.70。
- **领域四态判定**：`OFFICE_IT`（正常回答）/ `OFF_TOPIC`（拒答）/ `HIGH_RISK`（14 个高危关键词，拒答 + 引导人工）/ `UNCERTAIN`（追问澄清），先于检索、独立判定。
- **受约束生成（consultation-service）**：检索依据 → 受约束生成 → **引用双重复核**（生成前锁定读复核 PUBLISHED 版本，生成后 AiAnswerGuard 复核；引用由服务端从实际资料重建，模型编造 versionId 即整次输出无效）。
- **降级语义（RD-006）**：模型/检索故障统一表达为结构化拒答 + `suggestTransfer=true`，不静默回退、不把服务故障解释为"无命中"；密钥缺失仅 AI 问答降级，知识搜索/人工咨询不受影响。
- **转人工**：加权负载选工程师（候选上限 8）→ 10 工作分钟响应 SLA → 人工会话 → 提交结论 → 员工确认 → 24h 内可重开；可一键转工单（预填标题/描述，经 ticket-service 建单后回写 `CONVERTED_TO_TICKET`）。
- **知识生命周期（SM-KNOWLEDGE-001）**：DRAFT → PENDING_REVIEW → PUBLISHED → OFFLINE，作者不得自审（AC-25）、高风险须平台管理员、发布后写 ES（失败标 PENDING_COMPENSATION 可补偿重建）。
- **AI 反馈沉淀**：员工对 AI 回答点"已解决"后，反馈经脱敏自动沉淀为待审核知识文章（Redis 幂等标记，5s 扫描 `ai_interaction`），审核发布后进入检索。

## Python 检索服务（services/python-retrieval）

`rag-service` 的检索内核支持可插拔 provider：**默认 `python`**，由本目录的 Python 检索服务
承担「向量化 + 双路召回 + RRF + Cross-Encoder 精排 + 低置信拒答」，Java 侧只保留领域判定与
MySQL PUBLISHED 复核。对外契约 `POST /api/v1/rag/retrievals` 不变。

> ⚠️ **默认取 python 意味着 Python 检索服务必须可访问**：python 分支失败**不静默回退到 ES**，
> 每次检索都会以依赖不可用收场。回滚是零代码的——设 `RAG_RETRIEVAL_PROVIDER=es` 即可。

此外本服务还提供 **`POST /api/v1/policy/resolve`（版本消歧查询）**：给定主题与时间点，
解析该时刻**有效**的规约版本，输出版本号、生效日、被取代日与溯源角标。它回答的是
「某时刻该用哪一版」，与 `default_exclude` 的「别把废止做法教给员工」是两件事——
因此它**刻意看得见废止卡**（`include_excluded=True`）。四种结论分得很清：
`RESOLVED` / `NO_EFFECTIVE_VERSION` / `UNDATED`（没有生效日期，无法判定，不猜）/ `NO_MATCH`。
详见 [`docs/runbook-python-retrieval.md`](services/python-retrieval/docs/runbook-python-retrieval.md)。

```text
services/python-retrieval/
├── rag_service/             # HTTP 服务层(FastAPI)：/api/v1/rag/retrievals、/api/v1/policy/resolve、/api/health
│   ├── app.py               # 端点定义 + 异常映射(5031 锁超时/4000 参数/5000 兜底)
│   ├── assembly.py          # 进程级装配：配置/语料/向量库/检索器/映射/检索锁；含 resolve_policy 接线
│   ├── contract.py          # 对 Java 的契约镜像(Pydantic, camelCase)
│   ├── mapping.py           # 检索结果 → 契约字段(整卡全文/articleId 反查/拒答判定)
│   ├── requirements.txt     # fastapi / uvicorn[standard] / pydantic
│   └── tests/               # 纯逻辑单测(68 例，含版本消歧与端点契约)
├── rag_pipeline/            # 检索内核库：config/chunking/embedding/store/retrieval/policy/evaluation/ingestion
│   └── policy.py            # 版本消歧：沿 replaces 版本链按时间点解析有效规约版本
├── configs/pipeline.yaml    # 检索唯一配置源(切片/模型/参数/拒答阈值)
├── artifacts/
│   ├── output/wiki/         # 35 张现行 Wiki 卡片(+3 废止) = 检索语料
│   └── indexing/chroma_wiki_structured/   # 向量库(manifest 指纹校验)
├── evals/                   # 黄金问题集(golden_dataset_v1.0.json)
├── tools/                   # sync 灌库 / check_contract 契约校验 / run_service_regression 回归 / freeze 基线
├── rag_pipeline/…           # 内核含评测：python -m rag_pipeline.pipelines.golden_evaluation（黄金集评测）
└── docs/runbook-python-retrieval.md       # 运维手册(启动/灌库/联调/已知行为) ⭐
```

```bash
cd services/python-retrieval
pip install -r rag_service/requirements.txt
python -m rag_service                            # 127.0.0.1:8310，单进程
# 配置（EMBED_*/RERANK_*/LLM_*）从 REPO_ROOT/.env 兜底；环境变量仍可覆盖。

# 验证
python -m pytest rag_service/tests -q              # 68 例
python tools/check_contract.py                     # HTTP 黑盒契约不变量 85 项
python tools/run_service_regression.py --pace 1.5  # 黄金集 20 题过 HTTP vs 冻结基线
```

Java 侧启动参数（**默认已是 python**，通常只需给地址；要回到 ES 才显式设 provider）：

```bash
RAG_PYTHON_BASE_URL=http://127.0.0.1:8310
# 回滚：RAG_RETRIEVAL_PROVIDER=es
```

先决条件：**先灌库**（`python tools/sync_wiki_to_rag_service.py`，把卡片灌进 rag-service 的
MySQL+ES 并产出 `data/wiki_article_mapping.json`），否则 Python 返回的 articleId 过不了 Java 侧
④ MySQL 复核、items 恒为空。详细见 [services/python-retrieval/docs/runbook-python-retrieval.md](services/python-retrieval/docs/runbook-python-retrieval.md)。

## API 一览

统一经网关访问 `http://localhost:8080/api/v1/**`。工单/用户等服务响应为 `{code, msg, data}`（`code=0` 成功）；咨询/知识服务为 PRD 21.1 包络 `{code: "SUCCESS", message, request_id, data}`。常用入口：

| 方法 | 路径 | 说明 | 权限 |
|:---|:---|:---|:---|
| GET | /api/health | 健康检查 | 免认证 |
| POST | /api/v1/users/login | 登录 `{userId,password}` → `{token,user}` | 免认证 |
| GET | /api/v1/users/login-options | 可登录用户列表 | 免认证 |
| POST | /api/v1/users/forgot-password | 忘记密码（三要素自助重置） | 免认证 |
| GET/POST | /api/v1/users/accounts | 账号列表 / 新建账号 | PLATFORM_ADMIN/KNOWLEDGE_ADMIN |
| PUT | /api/v1/users/accounts/:id/role | 修改用户角色 | PLATFORM_ADMIN/KNOWLEDGE_ADMIN |
| GET/POST/DELETE | /api/v1/users/drafts | 提单草稿（每用户一条） | 登录 |
| GET | /api/v1/categories/leaf | 叶子分类（提单表单下拉） | 登录 |
| POST | /api/v1/tickets | 创建工单（Idempotency-Key 幂等，创建后自动路由） | 登录 |
| GET | /api/v1/tickets | 列表（status/category/assignee/priority/unassigned 等筛选 + 分页） | 登录 |
| POST | /api/v1/tickets/:id/assign | 派单/改派 | PLATFORM_ADMIN |
| POST | /api/v1/tickets/:id/claim | 接单（矩阵确认影响×紧急） | ENGINEER |
| POST | /api/v1/tickets/:id/actions | 状态操作（route/accept/request_supplement/supply_info/external_wait/submit_resolution/reject/cancel/abnormal_close/reopen...） | 状态机校验 |
| POST | /api/v1/tickets/:id/rating | 评价 1-5 星（仅已完成） | 登录 |
| POST | /api/v1/tickets/attachments/upload | 照片上传（另有 /:id/content 下载、DELETE 撤回） | 登录 |
| GET | /api/v1/sla/:ticketId | SLA 计时（剩余工作秒，前端倒计时基准） | 登录 |
| GET | /api/v1/notifications、/pending-count | 通知列表 / 未读数（前端轮询） | 登录 |
| GET | /api/v1/exceptions、/pending-count | 异常队列（路由失败工单） | 管理员 |
| POST | /api/v1/consultations | 创建咨询会话（AI / 转人工） | 登录 |
| POST | /api/v1/consultations/:id/ai-messages | AI 问答（ANSWER/CLARIFY/REFUSE） | 登录 |
| POST | /api/v1/consultations/:id/transfer | 转人工（幂等触发自动分配） | 登录 |
| POST | /api/v1/consultations/:id/messages | 人工会话消息 | 参与者 |
| GET | /api/v1/knowledge/search | 知识搜索（仅 PUBLISHED） | 登录 |
| POST | /api/v1/rag/documents/upload | 文档上传入库（解析→切片→向量化→ES） | 知识管理 |
| POST | /api/v1/rag/retrievals | RAG 检索（Top-K 切片 + 领域判定） | 登录 |
| POST | /api/v1/rag/articles/:id/submit · publish · reject · offline | 知识审核流（按状态/角色守卫） | 知识管理/管理员 |

完整接口契约见 [docs/specs/05-http-api-openapi.yaml](docs/specs/05-http-api-openapi.yaml)（非 AI）与 [docs/specs/02-ai-api-json-schema.md](docs/specs/02-ai-api-json-schema.md)（AI）；错误码与状态机细节见 [it-ticket-cloud/README.md](it-ticket-cloud/README.md)。核心错误码：`40001` 参数校验、`40100/40101` 未登录/禁用、`40300` 权限不足、`40901` 幂等冲突、`40910` 非法状态转移、`40911/40912` 不可领取/已被他人领取。

## 测试与验收

| 套件 | 位置 | 命令 | 状态 |
|:---|:---|:---|:---|
| 提单链路验收（pytest，27 项：TC-01~10 + M-01~09 + 状态机/守卫） | `acceptance/` | `python -m pytest -v`；`python scripts/run.py` 生成评测报告 | 27/27 通过（2026-10-08 报告，V2 §4.2 综合判定通过） |
| RAG/AI 咨询端到端冒烟（Node） | `acceptance/ai-rag-smoke.mjs` | `node acceptance/ai-rag-smoke.mjs [--require-answer]`（需网关 + consultation + rag 已启动） | 验证领域判定/拒答/引用/持久化 |
| 后端单元/集成测试（JUnit，61 个测试类） | `it-ticket-cloud/*/src/test` | `mvn -pl consultation-service,rag-service -am test`（或按模块） | RAG 集成范围 262 项通过（consultation 206 / rag 48 / gateway 2，见 spec 记录） |
| 前端单元/契约测试 | `frontend/tests/*.test.mjs` | `npm test`（node --test，20 个文件） | — |
| 前端浏览器测试（Playwright） | `frontend/tests/browser/` | `npm run test:browser`（端口 5176） | 8 个 spec |

## 生产部署

```bash
cd it-ticket-cloud/deploy
.\pack-local.ps1        # Maven 全量构建 + 前端 build → 打出 it-ticket-system-deploy-YYYYMMDD.tar.gz
# 服务器上解包后：
cp .env.example .env    # 填 JWT_SECRET、AI_API_KEY、EMBEDDING_API_KEY、MYSQL_*、CORS_ORIGINS 等
.\upgrade-server.sh     # 构建镜像并 docker compose -f docker-compose.prod.yml up -d，健康检查 5 个服务 + 前端
```

生产编排（`docker-compose.prod.yml`）含 5 个后端服务 + 前端 nginx（:80，网关 :8080 对外）；基础设施（MySQL/Nacos/Redis/ES）经 `host.docker.internal` 指向宿主机；密钥全部由 `.env` 注入，不进镜像不进 git。

## 配置与环境变量

配置分层：`application.yml`（启动项）→ `application-{profile}.yml`（默认 dev）→ Nacos 可选覆盖（`NACOS_CONFIG_ENABLED=true`，见 [nacos-config/配置管理说明.md](it-ticket-cloud/nacos-config/配置管理说明.md)）。

常用变量（均可在 dev 环境省略，见 `scripts/dotenv-example.env` 与 `deploy/.env.example`）：

| 变量 | 默认 | 说明 |
|:---|:---|:---|
| `MYSQL_HOST/PORT/DB/USERNAME/PASSWORD` | 远程库 / 3306 / it_ticket_system | 数据库连接 |
| `NACOS_ADDR` | 127.0.0.1:8848 | 注册中心 |
| `JWT_SECRET` | dev 内置默认 | **生产必须注入**，缺失启动失败 |
| `RAG_BASE_URL` | http://127.0.0.1:8302 | consultation → rag 检索地址 |
| `AI_BASE_URL / AI_API_KEY / AI_MODEL` | — | OpenAI 兼容对话模型端点 |
| `AI_AGENT_ENABLED` | false | Function Calling 智能体开关（开启后生成层改调 Python agent_service，IDE 裸启动可写进 `ai-secrets.yml` 的 `agent.enabled`） |
| `EMBEDDING_BASE_URL / EMBEDDING_API_KEY / EMBEDDING_MODEL` | — | embedding 模型（1024 维） |
| `AI_SECRETS_FILE / RAG_SECRETS_FILE` | ./ai-secrets.yml | 密钥文件路径（已 gitignore） |
| `ES_HOST/PORT/ES_KNOWLEDGE_INDEX` | localhost / 9200 / knowledge_chunk | Elasticsearch |
| `API_PROXY_TARGET` | ~~http://127.0.0.1:28080~~（过时） | **前端代理，请设为 http://127.0.0.1:8080** |

## 文档地图

| 文档 | 说明 |
|:---|:---|
| [docs/IT服务工单系统PRD-Ultimate.md](docs/IT服务工单系统PRD-Ultimate.md) | 业务基线 PRD 2.2（状态机/SLA/通知/路由的唯一依据；根目录同名文件为占位指针） |
| [it-ticket-cloud/README.md](it-ticket-cloud/README.md) | 微服务版详细技术文档（架构/接口/错误码/状态机/数据库/排查指南）⭐ |
| [docs/specs/](docs/specs/README.md) | 一期契约 01~11：数据模型 / AI Schema / 状态机 / 韧性 / OpenAPI / DDL / 事件 / 权限与 SLA / 追溯矩阵 / 模型与 RAG |
| [docs/superpowers/specs/](docs/superpowers/) | 设计文档存档（RAG 咨询组合设计、服务台 UI 设计等）与实施计划 |
| [docs/IT服务工单系统-验收评测协议书-V2.md](docs/IT服务工单系统-验收评测协议书-V2.md) | 验收评测协议（指标/用例/判定规则）；实测报告在 `acceptance/reports/` |
| [it-ticket-cloud/consultation-service/RAG-INTEGRATION.md](it-ticket-cloud/consultation-service/RAG-INTEGRATION.md) / [rag-service/INTEGRATION.md](it-ticket-cloud/rag-service/INTEGRATION.md) | RAG 集成契约（检索/引用/阈值/反馈沉淀） |
| [design-system/it-service-desk/MASTER.md](design-system/it-service-desk/MASTER.md) | 已实施的前端设计规范（深空蓝黑 + 电光青，亮/暗双主题） |
| [工单提交流程讲解.md](工单提交流程讲解.md) | 提单链路讲解（AI 预审 → 前置校验 → 后置生成，面向答辩/演示） |
| [AGENTS.md](AGENTS.md) | 工程协作约束（接口变更同步迁移调用方、不做静默回退等） |

## 仓库

- **主仓库（GitHub）**：https://github.com/TheWham/ServiceTicketSystem
- **镜像（Gitee）**：https://gitee.com/early-rise/it-ticket-system
