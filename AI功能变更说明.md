# AI 智能受理功能 · 变更说明文档

> 日期：2026-09-24
> 范围：`it-ticket-cloud` 微服务后端 + `frontend` 前端 + 数据库脚本
> 原则：对已有功能**零破坏**——所有对老代码的改动均为纯新增（枚举值/路由/配置行/新文件），未修改任何已有业务逻辑。

---

## 一、功能概述

在工单系统前置增加「AI 智能受理」流程，员工遇到 IT 问题先由 AI 解答，解决不了再逐级升级：

```
员工提问
  ↓
① AI 解答(知识库 RAG:历史工单 + 手工录入知识)
  ↓
② 员工反馈「已解决」→ 流程结束,不生成工单
  ↓ 员工点「未解决,转人工」(也可选「直接结束」)
③ 自动转人工客服(新角色 customer_service,带上下文摘要)
  ↓
④ 人工与员工 WebSocket 实时沟通
  ↓
⑤ 人工决策:确认需派单 → 生成工单(幂等);重复/无效/已解决 → 驳回(员工可再次发起)
  ↓
⑥ 工程师接单解决 → 工单完成 →「问题+解决方案」自动回流知识库 → AI 能力持续增长
```

---

## 二、架构变化

新增第 4 个业务微服务 **ai-service**（端口 8202，独立数据库 it_ai）：

```
浏览器(Vue 5173)
   │  /api/**  →  vite proxy → gateway:8080
   │  /ws/**   →  vite proxy(ws) → gateway:8080
   ↓
gateway ──/api/v1/ai/**──→ ai-service:8202 ──Feign──→ ticket-service /api/internal/tickets
        └─/ws/ai/**(lb:ws)─┘        │
                                    ├─ Feign 定时拉取已完成工单(知识回流)
                                    └─ MySQL it_ai(3 张新表)
```

- AI 调用走 **OpenAI 兼容 HTTP 接口**（自研轻量客户端，未引入 Spring AI 等框架，依赖干净）
- 大模型 key 可配可不配：不配时降级运行（AI 回复提示语、跳过检索），**转人工/聊天/转工单全流程不受影响**

---

## 三、数据库变更（db/init/）

| 文件 | 类型 | 内容 |
|---|---|---|
| `30-ai-db.sql` | 新增 | 建 it_ai 库 + 3 张表（开头 `SET NAMES utf8mb4`，沿用乱码修复约定） |
| `12-user-add-customer-service.sql` | 新增 | 客服种子账号 U007 周客服（密码同其他种子 123456，INSERT IGNORE 幂等） |
| `10-user-db.sql` | 修改 1 行 | `user.role` ENUM 增加 `'customer_service'`（**修复线上 NPE 的同步改动**） |

### it_ai 三张表

**ai_knowledge（知识库切片）**：id / title / content / source_type(TICKET工单回流·DOC·MANUAL手工) / source_id(防重) / category / embedding(JSON向量) / create_time

**ai_chat_session（咨询会话）**：id / user_id / status / agent_id / summary(转人工摘要) / reject_reason / ticket_id / resolved / create_time / update_time

**ai_chat_message（会话消息）**：id / session_id / sender_type(USER·AI·AGENT·SYSTEM) / sender_id / content / create_time

> ⚠️ 已有环境记录：老库 ENUM 不含新角色导致 U007 插入被静默写成空串、login-options 报 NPE，已通过
> `ALTER TABLE ... MODIFY role ENUM(...,'customer_service')` + `UPDATE U007` 修复（详见 AI功能启动步骤.md 常见问题 2）。

---

## 四、后端变更明细

### 4.1 已有模块的改动（全部为最小增量）

| 模块 | 文件 | 改动 |
|---|---|---|
| common | `api/ErrorCode.java` | +1 枚举值 `SESSION_NOT_FOUND(40401)` |
| user-service | `enums/UserRole.java` | +1 枚举值 `customer_service("customer_service")` |
| gateway | `resources/application.yml` | +2 条路由：`/api/v1/ai/**`→`lb://ai-service`；`/ws/ai/**`→`lb:ws://ai-service` |
| gateway | `filter/AuthGlobalFilter.java` | 白名单 +1 条件：`/ws/` 前缀放行（WS 握手无法带 Authorization 头，由 ai-service 握手时校验 token 参数） |
| ticket-service | `resources/application.yml` | exclude-paths +1 行：`/api/internal/**` |
| ticket-service | `dto/InternalCreateRequest.java` | **新文件**：内部建单请求（creator_id + 工单字段 + client_token） |
| ticket-service | `vo/SolvedTicketVO.java` | **新文件**：已完成工单摘要（含 solution_remark=工程师处理结论） |
| ticket-service | `controller/InternalTicketController.java` | **新文件**：`POST /api/internal/tickets`（复用 TicketService.create 全部校验/幂等/通知）、`GET /api/internal/tickets/solved?since=&limit=`（供知识回流拉取） |
| 父工程 | `pom.xml` | modules +1 行：`<module>ai-service</module>` |

### 4.2 新模块 ai-service（28 个新文件，包 com.itticket.ai）

**骨架与配置**
- `AiApplication.java`：启动类（@EnableScheduling 知识回流定时任务 + Feign + Nacos）
- `resources/application.yml`：端口 8202、it_ai 数据源、`ai.chat/embedding/rag/sync` 全部 AI 配置（均支持环境变量覆盖）
- `config/AiProperties.java`：AI 配置绑定（chat/embedding 独立配置，可分别缺省降级）
- `config/JwtProperties.java`、`config/MybatisPlusConfig.java`（与 ticket-service 同款）
- `config/WebSocketConfig.java`：注册 `/ws/ai/chat` 端点

**LLM/RAG 核心**
- `service/LlmClient.java`：对话模型客户端（RestClient 调 OpenAI 兼容 /chat/completions，temperature 0.3 防幻觉，超时 5s/60s）
- `service/EmbeddingClient.java`：向量模型客户端（默认硅基流动 BGE-M3；失败返回 null 由上层降级）
- `service/KnowledgeService.java`：知识切片入库（500 字/重叠 50 字）+ 全量向量内存余弦相似度 TopK（阈值 0.55）；数据量大后只换 search() 即可平移 Milvus
- `service/AiChatService.java`：问答编排——消息落库 → 检索 → 拼 Prompt（有资料严格依据资料+标注来源；无资料通用建议+声明+引导转人工）→ 回复落库

**会话与人工客服**
- `enums/SessionStatus.java`：7 态状态机（AI_HANDLING/WAITING_HUMAN/HUMAN_HANDLING/RESOLVED/TO_TICKET/REJECTED/CLOSED）
- `entity/ChatSession.java`、`ChatMessage.java`、`AiKnowledge.java`（均 @JsonNaming snake_case，与项目接口约定一致）
- `mapper/` 3 个 BaseMapper
- `service/ChatSessionService.java`：状态机流转 + 客服队列 + 抢单原子更新（防两客服同时接入）+ 转工单（client_token=`ai-session-{id}` 幂等防重复建单，描述自动由对话记录生成）+ 关键节点 WS 实时推送
- `service/KnowledgeSyncService.java`：每 10 分钟增量拉取已完成工单 → 拼「分类+问题+解决方案」入库（工单号防重，异常不抛保护调度线程）
- `feign/TicketClient.java`：调 ticket-service 内部接口

**WebSocket 实时聊天**
- `ws/WsAuthInterceptor.java`：握手校验 `?token=`（与网关同 secret 的 JWT），身份写入 attributes
- `ws/ChatWebSocketHandler.java`：消息协议处理（发送方身份只信握手 attributes；校验会话状态与发言权；落库+广播）
- `ws/WsNotifier.java`：连接注册中心（按会话分组推送 + 在线客服队列广播）

**接口层**
- `controller/AiChatController.java`（员工）：`/api/v1/ai` → chat、resolve、escalate、close、sessions/mine、sessions/{id}/messages
- `controller/AgentController.java`（客服，checkRole customer_service）：`/api/v1/ai/agent` → queue、accept、resolve、reject、to-ticket、messages
- `controller/KnowledgeController.java`（客服+主管）：`/api/v1/ai/knowledge` → 录入(自动切片向量化)、分页列表、删除
- `dto/`：ChatRequest、RejectRequest、ToTicketRequest、KnowledgeAddRequest

---

## 五、前端变更明细

| 文件 | 类型 | 内容 |
|---|---|---|
| `src/components/AiChatPanel.vue` | **新增** | 员工 AI 聊天面板：气泡对话、AI 思考 loading、📄 参考资料标签、已解决/转人工/直接结束按钮、人工阶段自动切 WebSocket、结束态提示、刷新自动恢复进行中会话 |
| `src/views/AgentWorkbenchView.vue` | **新增** | 客服工作台 `/agent`：会话队列（待接入红点徽标 + WS 实时刷新）、对话窗口、接入/标记解决/驳回(必填原因)/转工单(分类+优先级弹窗) 四个处置动作、知识库管理 tab（录入/列表/删除） |
| `src/views/EmployeeView.vue` | 修改 3 处 | +第 3 个 tab「AI 助手」内嵌 AiChatPanel；+import |
| `src/api/index.js` | 修改（纯追加） | +aiApi（6 个接口）、agentApi（6 个）、knowledgeApi（3 个） |
| `src/router/index.js` | 修改 2 处 | HOME 映射 +`customer_service:'/agent'`；+`/agent` 路由（meta role） |
| `src/App.vue` | 修改 3 处 | 面包屑/角色名/角色标签色映射 +customer_service(客服) |
| `src/views/LoginView.vue` | 修改 2 处 | roleMap/roleTagType/roleRoute +客服 → `/agent` |
| `vite.config.js` | 修改 | proxy +`/ws`（`ws:true`，转发 WebSocket 到网关） |

> 未新增任何 npm 依赖（WebSocket 用浏览器原生 API）。`npm run build` 已通过。

---

## 六、接口与协议速查

### REST（均经网关 :8080，JWT 鉴权）

| 方法 | 路径 | 角色 | 说明 |
|---|---|---|---|
| POST | /api/v1/ai/chat | 全员 | 提问 `{session_id?, question}` → `{session_id, answer, status, sources[]}` |
| POST | /api/v1/ai/sessions/{id}/resolve | 本人 | 反馈已解决，关单 |
| POST | /api/v1/ai/sessions/{id}/escalate | 本人 | 转人工（生成摘要+提醒队列） |
| POST | /api/v1/ai/sessions/{id}/close | 本人 | 直接结束 |
| GET | /api/v1/ai/sessions/mine | 本人 | 最近 20 条会话 |
| GET | /api/v1/ai/sessions/{id}/messages | 本人 | 消息记录 |
| GET | /api/v1/ai/agent/queue | 客服 | 待接入+我处理中 |
| POST | /api/v1/ai/agent/sessions/{id}/accept | 客服 | 接入（原子更新防抢单） |
| POST | /api/v1/ai/agent/sessions/{id}/resolve | 客服 | 标记已解决 |
| POST | /api/v1/ai/agent/sessions/{id}/reject | 客服 | 驳回 `{reason}` |
| POST | /api/v1/ai/agent/sessions/{id}/to-ticket | 客服 | 转工单（幂等） |
| POST/GET/DELETE | /api/v1/ai/knowledge | 客服/主管 | 知识录入/分页/删除 |
| POST | /api/internal/tickets | 服务间 | 内部建单 |
| GET | /api/internal/tickets/solved | 服务间 | 已完成工单拉取 |

### WebSocket

端点：`/ws/ai/chat?token=<JWT>[&sessionId=<id>]`
- 上行：`{"type":"msg","session_id":1,"content":"..."}`
- 下行消息：`{"type":"msg",...}`（聊天）、`{"type":"sys",...}`（系统提示/状态变更）、`{"type":"queue"}`（提醒客服刷队列）、`{"type":"error",...}`

---

## 七、配置项（application.yml / 环境变量）

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `AI_CHAT_API_KEY` | 空 | 对话模型密钥（不配 → AI 回复降级提示语） |
| `AI_CHAT_URL` | deepseek /chat/completions | OpenAI 兼容端点 |
| `AI_CHAT_MODEL` | deepseek-chat | |
| `AI_EMBEDDING_API_KEY` | 空 | 向量模型密钥（不配 → 跳过 RAG 检索） |
| `AI_EMBEDDING_URL` | siliconflow /v1/embeddings | |
| `AI_EMBEDDING_MODEL` | BAAI/bge-m3 | 一经使用不要换（向量空间不兼容） |

RAG 参数：`ai.rag.top-k=5`、`min-score=0.55`、`chunk-size=500`、`chunk-overlap=50`；回流任务：`ai.sync.enabled=true`、10 分钟一轮。

---

## 八、遗留事项与注意

1. **后端未本机编译验证**（本机无 Maven），代码经逐文件自查，首次 `mvn package` 如有报错需修
2. 知识回流采用**定时拉取**而非事件推送（刻意不在工单流转老代码里埋钩子，零侵入）；回流内容注意脱敏
3. AI 密钥必须自行注册配置（免费额度≠免 key），最省事方案：硅基流动一个 key 同时用于免费对话模型 Qwen2.5-7B + 免费 BGE-M3（详见对话记录或 AI功能启动步骤.md）
4. 启动新增步骤见同目录 **AI功能启动步骤.md**（数据库脚本×2、环境变量、多启 ai-service、验收清单、常见问题）
