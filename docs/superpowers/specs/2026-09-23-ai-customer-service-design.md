# 智能客服与 RAG 转人工设计规格

## 1. 文档信息

| 项目 | 内容 |
|---|---|
| 文档状态 | 已按 PRD（10）与泳道图修订：优先级与工单类型统一回归 PRD 契约，待实施计划评审 |
| 日期 | 2026-09-23 |
| 适用项目 | ServiceTicketSystem |
| 当前模型 | 通义千问 OpenAI 兼容接口 |
| 设计原则 | PRD 契约优先、当前代码兼容映射、可插拔模型、RAG 事实约束、L1 热转接、规则优先 |
| PRD 对齐基线 | category 五值（HARDWARE/SOFTWARE/NETWORK/ACCOUNT/OTHER）与 priority 三档（HIGH/MEDIUM/LOW，员工自选，默认 MEDIUM）不变；Incident/Request 分流与影响×紧急矩阵降级为 ai-service/L1 内部辅助维度 |
| 角色口径 | 与泳道图统一：知识审核角色为**知识库管理员**（PRD 中"主管审核"由该角色承担）；沉淀决策双环节＝工程师勾选建议 + 知识库管理员研判审核 |

## 2. 背景与目标

当前系统已经具备 Vue 3 员工工作台、Spring Cloud 微服务、JWT 鉴权、工单状态机、通知和幂等建单能力，但缺少“AI 客服 → L1 服务台 → 工程师”的完整前置受理链路。

本设计按 PRD（10）与泳道图实现：员工在提单前发起咨询，AI 结合 RAG 进行基础排查；AI 无法解决或命中转人工条件时，保持同一会话热转接到 L1 服务台；L1 坐席继承完整上下文并继续沟通。L1 可直接解决问题形成零工单闭环，也可生成报修卡并由坐席代客建单，员工不重复填写。

### 2.1 目标

1. 支持登录员工在工作台发起多轮 IT 问题对话。
2. 通过 RAG 回答 FAQ、操作手册、服务政策和已审核知识。
3. 使用 JSON Schema 约束 Qwen 输出，避免自由文本污染业务链路。
4. 通过可配置的轮数、置信度、风险和用户意图规则触发转人工。
5. 转人工时自动生成工单预填数据，但不绕过用户确认和现有工单状态机。
6. AI 服务、模型、向量库或第三方 API 故障时，传统提单功能仍可用。
7. 所有 AI 会话必须落库并记录 `outcome`，可计算 AI 拦截率和 L1 拦截率。
8. 增加 L1 服务台角色、在线队列、热转接和坐席代客建单。
9. AI 内部区分 Incident（故障）与 Request（申请）意图；账号权限类申请命中时必须走人工与审批提示，不得按普通故障直接放行；对外工单仍使用 PRD 五值 category 枚举。
10. 工单优先级按 PRD 由员工自选 HIGH/MEDIUM/LOW（默认 MEDIUM）；影响范围 × 紧急程度矩阵仅作为 L1 坐席侧辅助校验建议，修正需留痕。
11. 重大故障期间阻断普通转人工，统一播报已确认的 Incident 信息。
12. SLA 超时自动 @组长 / @经理，并将升级事件纳入审计。

### 2.2 非目标

1. AI 不直接派单、领取、推进或关闭工程师工单；L1 坐席可以在授权范围内代客创建工单。
2. 第一阶段不构建复杂全渠道联络中心，但必须提供最小可用的 L1 在线队列和 IM 工作台。
3. 不引入复杂 Agent 工具调用，不允许模型直接执行权限变更、删除、恢复等写操作。
4. 历史工单不能直接发布为正式知识，必须经过脱敏、审核和向量化。
5. 重大故障不走普通 L1 排队，由 Incident 广播和统一公告承接。
6. 不修改 PRD 的工单类型（category）与优先级（priority）枚举及字段语义；Incident/Request 双维分类、影响范围与紧急程度仅作为 ai-service 内部意图与坐席辅助标记，不进入工单对外契约。

### 2.3 契约兼容策略

- 对外契约按 PRD 使用 `/api/ai-cs/chat`、`/api/ai-cs/transfer` 等接口语义。
- 网关内部保留 `/api/v1/ai/**` 作为版本化实现路由，并提供兼容映射。
- PRD 的八态状态和新字段作为目标模型；当前 Java 七态枚举通过映射层过渡，禁止在文档中假设代码已经完成迁移。

### 2.4 PRD 契约字段映射表

前端按 PRD 契约开发，映射在网关/兼容层完成：

| PRD 契约 | 本设计内部实现 | 说明 |
|---|---|---|
| `POST /api/ai-cs/chat` | `POST /api/v1/ai/sessions/{id}/messages`（SSE） | 会话创建/消息为 RESTful 细分，网关聚合映射 |
| `reply_type=ANSWER` | `action=ANSWER` | |
| `reply_type=CLARIFY` | `action=ASK_CLARIFICATION` | |
| `reply_type=REFUSE` | `action=OFFER_HUMAN / SAFETY_BLOCKED / 低置信拒答` | REFUSE 语义＝无法回答并引导转人工 |
| `answer_text` | `answer` | |
| `source_article_ids[]` | `citations[].document_id` | 引用收敛到文档级返回 |
| `confidence` | `confidence` | |
| `suggest_transfer` | `EscalationDecision` 结果回填 | 规则层决策，非模型输出 |
| `POST /api/ai-cs/transfer` 的 `trigger_type=MANUAL` | 用户输入"转人工" / 点击"未解决" | |
| `trigger_type=RULE_SUGGESTED` | 低置信建议转人工 | |
| `trigger_type=RULE_FORCED` | 轮数超限 / 步骤连续失败 / 重复描述 / 超时 / 高风险关键词 / 重大故障 | 即 PRD"自动兜底策略 R1-R6"的落地定义 |
| `queue_position / estimated_wait_sec / transfer_status` | L1 队列字段直传 | CONNECTED/QUEUED/OFFLINE 对应接入/排队/离线留言 |
| `POST /api/kb/faq/generate` | `POST /internal/ai/knowledge/ingest`（内部入口） | 触发契约见「RAG 知识库设计·知识来源」一节 |
| `idempotency_key` | `client_token`（建议 `ai-{session_id}`） | 提交工单幂等去重 |

## 3. 总体架构

```text
Vue 员工工作台
  └─ 智能客服面板
       │ JWT + SSE
       ▼
Gateway :8080
  └─ /api/v1/ai/** → ai-service :8301
                         ├─ Chat Orchestrator
                         ├─ Intent Router
                         ├─ Escalation Policy
                         ├─ RAG Retriever
                         │    ├─ MySQL 元数据
                         │    ├─ Qdrant 向量检索
                         │    └─ MySQL FULLTEXT 关键词检索
                         ├─ Provider Adapter
                         │    ├─ Qwen OpenAI-Compatible
                         │    ├─ EmbeddingProvider
                         │    └─ RerankProvider
                        ├─ Conversation Store
                         └─ L1 Handoff Adapter
                                  │ WebSocket/SSE IM
                                  ▼
                         service-desk-service :8401
                         ├─ L1 坐席队列
                         ├─ 热转接会话
                         ├─ 人工分类与处理
                         └─ 报修卡生成/坐席代客建单
                                  │
                                  ▼
                         ticket-service :8201
                         ├─ PRD 五类工单（HARDWARE/SOFTWARE/NETWORK/ACCOUNT/OTHER）
                         ├─ 审批、SLA 和通知
                         └─ 现有建单、幂等和状态机
```

### 3.1 服务边界

#### frontend

- 在提单页提供“咨询客服”入口，同时保留工作台智能客服入口。
- 支持 AI 与 L1 坐席在同一窗口继续对话，显示坐席接入、队列和处理中状态。
- 支持快捷问题、文本、附件、知识引用、已解决、仍未解决和转人工。
- 坐席确认需要工程师时，在同一窗口展示报修卡状态；员工只接收结果和通知，不重复填写表单。
- 不保存 API Key，不直接调用 Qwen。

#### gateway

- 新增 `ai-service` 路由：`/api/v1/ai/**`。
- 复用 JWT 鉴权和用户上下文透传。
- 支持 SSE 响应、请求体限制和基础限流。

#### ai-service

- 负责会话、消息、意图、RAG、模型适配、输出校验、转人工建议和审计。
- 从 JWT 获取当前用户，不信任请求体中的 `user_id`。
- 每个会话必须写入最终 `outcome`，包括 AI 解决、L1 解决、工程师升级、重大故障播报、放弃和系统失败。
- 命中重大故障时返回统一播报，不创建普通转人工请求。
- 将 AI 会话上下文热转接给 `service-desk-service`。

#### service-desk-service

- 管理 L1 坐席在线状态、技能标签、队列、接入、转接和 IM 消息。
- L1 坐席继承 AI 会话摘要、用户消息、检索引用、已尝试步骤和风险标记。
- L1 坐席可以直接标记 `HUMAN_RESOLVED`，也可以生成报修卡并代客创建工单（对外即 PRD category 五值枚举）。
- 不能绕过审批、SLA、通知和 ticket-service 状态机。

#### ticket-service

- 继续作为工单创建和状态流转的唯一权威服务。
- 工单类型与优先级枚举、字段语义完全维持 PRD（category 五值；priority 三档、员工自选、默认 MEDIUM）；Incident/Request 意图、影响范围与紧急程度作为会话侧补充标记存储，不进入工单对外契约。
- 账号权限类申请（ACCESS_REQUEST）建单时携带审批提示标记，由 L1 转交审批流程，不改变工单状态机对外语义。
- 继续执行字段校验、幂等、工单号生成和状态机校验。
- 支持 L1 坐席代客建单，`creator_id` 仍为员工，`created_by` 记录坐席。
- 增加 SLA 计时和超时升级事件，自动 @组长 / @经理。

## 4. 会话状态机

```text
NEW
  ↓
TRIAGING
  ├─ 重大故障命中 → MAJOR_INCIDENT_BROADCAST
  └─ 普通问题 → COLLECTING_INFO
                  ↓
               RETRIEVING
                  ↓
               ANSWERING
                  ↓
               VERIFYING
                  ├─ AI 已解决 → AI_RESOLVED → ARCHIVED
                  ├─ 继续排查 → COLLECTING_INFO
                  └─ 转人工条件命中 → L1_QUEUED
                                         ↓
                                      L1_CONNECTED
                                         ↓
                                      L1_CLASSIFYING
                                         ├─ L1 直接解决 → HUMAN_RESOLVED → ARCHIVED
                                         └─ 需要工程师 → REPORT_CARD_READY
                                                          ↓ 坐席确认
                                                       TICKET_CREATING
                                                          ↓
                                                       TICKET_CREATED
```

异常状态：`MODEL_TIMEOUT`、`RETRIEVAL_EMPTY`、`SAFETY_BLOCKED`、`SESSION_EXPIRED`、`L1_OFFLINE`、`TICKET_CREATE_FAILED`。

每轮只允许一个目标：识别问题、补一个关键字段、给一个排查动作或确认动作结果。禁止一次生成多个无关排查分支。

## 5. 转人工策略

### 5.1 默认参数

```yaml
ai:
  chat:
    transfer-after-turns: 5
    max-retry-per-step: 1
    session-timeout-minutes: 30
    low-confidence-threshold: 0.55
    answer-confidence-threshold: 0.78
  service-desk:
    queue-timeout-seconds: 60
    handoff-mode: HOT
```

### 5.2 立即转人工

满足任一条件，进入 L1 热转接：

- 用户明确输入“转人工”；
- 会话轮数超过 5 轮；
- 用户点击“未解决”。

以下情况不进入普通转人工，而是进入统一重大故障播报：

- 已确认的公司级或多部门级生产故障；
- 影响范围达到重大 Incident 阈值；
- Incident 指挥台已发布进行中的统一公告。

账号权限、提权、密码重置、疑似数据泄露等安全高风险问题仍需进入 L1，但 L1 只能分类和审批转交，不能由 AI 或坐席直接授予权限。

与 PRD 转人工契约的对应：用户输入"转人工" / 点击"未解决" → `trigger_type=MANUAL`；低置信建议转 → `RULE_SUGGESTED`；轮数超限、同一步骤失败两次、重复描述、超时、高风险关键词、重大故障 → `RULE_FORCED`。本节规则即 PRD"自动兜底策略 R1-R6"的落地定义。

### 5.3 轮数与置信度规则

- 第 5 轮结束仍未解决，自动进入 L1 队列。
- 用户点击“未解决”或明确请求人工，不等待轮数。
- 同一排查步骤失败两次，进入 L1 队列。
- 同一问题重复描述两次，进入 L1 队列。
- 置信度低于阈值：先澄清一次；仍低置信度时提供“未解决”按钮。
- L1 坐席接入后，AI 不再继续自动抢答，避免人机并发发言。

### 5.4 规则优先

模型只输出建议，最终由 `EscalationPolicy` 计算：

```text
重大 Incident 命中 → 阻断普通转人工并统一播报
否则 → transfer trigger 命中 → L1 热转接
否则 → intent_confidence
      + retrieval_confidence
      + answer_grounding_score
      + failed_step_count
      + user_sentiment
      → EscalationDecision
```

## 6. L1 服务台与热转接

### 6.1 热转接原则

- 用户始终停留在同一会话窗口，不跳转到冷转接提单页。
- 转接时将 AI 会话摘要、原始消息、知识引用、已尝试步骤、资产信息、风险标记和建议分类一次性带给 L1 坐席。
- 坐席接入后，前端展示“L1 服务台已接入”，AI 进入静默状态。
- 坐席可以继续 IM 沟通、补充字段、修改分类和判断是否需要工程师。

### 6.2 L1 坐席处理分支

```text
L1_CONNECTED
  ↓
L1_CLASSIFYING
  ├─ L1 直接解决 → HUMAN_RESOLVED → 会话归档，不创建工单
  └─ 需要工程师 → 生成报修卡 → 坐席确认 → 代客创建工单
```

员工不需要再次填写同一遍表单。工单中的 `creator_id` 仍为员工，`created_by` 为 L1 坐席，确保责任归属和审计都可追溯。

### 6.3 L1 队列

队列至少记录：`queue_id`、`session_id`、`user_id`、`reason_code`、`priority_hint`、`queued_at`、`assigned_agent_id`、`status`、`first_response_at`、`closed_at`。

队列分配按在岗状态、技能标签、当前队列长度和 SLA 剩余时间排序。L1 无人在线时，进入留言队列并发送组长通知，但仍保留同一会话上下文。

## 7. Incident / Request 分流

### 7.1 定位与内部意图定义

Incident / Request 是 `ai-service` 的内部意图维度，用于分流与风险控制，不改变 PRD 工单类型枚举，对外建单一律映射回 PRD 五值：

- `INCIDENT`：已有服务或设备异常，目标是恢复服务。
- `REQUEST`：申请权限、开通服务、增加资源、安装软件等，目标是完成审批和交付。

`ACCOUNT` 类在意图层进一步细分：

- `ACCOUNT_INCIDENT`：账号无法登录、账号被锁、认证异常；
- `ACCESS_REQUEST`：申请权限、提权、开通账号、访问资源。

`ACCESS_REQUEST` 必须走审批流，不能按普通故障直接派工程师处理，也不能由 AI 或 L1 直接授予权限。

内部意图 → PRD category 映射（建单时由报修卡生成方负责转换）：

| 内部意图 | PRD category | 建单与处理 |
|---|---|---|
| INCIDENT（硬件/网络/软件故障） | HARDWARE / NETWORK / SOFTWARE / OTHER | 正常建单派工程师 |
| REQUEST（软件安装、资源申请） | SOFTWARE / OTHER | 建单后由 L1 转交审批流 |
| ACCOUNT_INCIDENT | ACCOUNT | 正常建单派工程师，不自动变更权限 |
| ACCESS_REQUEST | ACCOUNT | 建单携带审批提示标记，转交审批任务，不得直接放行 |

### 7.2 转人工和建单映射

| 内部意图 | PRD category | L1 处理 | 工单/审批结果 |
|---|---|---|---|
| INCIDENT | HARDWARE / NETWORK / SOFTWARE / OTHER | 先判断是否已有 Major Incident，再决定单点排查或建单 | 恢复服务或进入工程师处理 |
| REQUEST | SOFTWARE / OTHER | 收集申请对象、用途、范围和审批人 | 建单后进入审批，批准后执行，拒绝后通知 |
| ACCOUNT_INCIDENT | ACCOUNT | 验证身份后进入账号故障排查 | 必要时转工程师，不自动变更权限 |
| ACCESS_REQUEST | ACCOUNT | 验证身份并补齐申请字段 | 生成 ACCOUNT 工单并转交审批任务 |

## 8. 重大故障播报与转人工阻断

当系统检测到已确认的 Major Incident，或 Incident 指挥台发布进行中公告时：

1. 阻断普通 L1 转人工和重复建单；
2. 返回统一播报文案、当前影响范围、已知临时措施和下一次更新时间；
3. 会话仍然落库，`outcome=MAJOR_INCIDENT_BROADCAST`；
4. 用户可以订阅恢复通知，但不能通过普通入口占用 L1 队列；
5. 只有 Incident 管理员或值班经理可以创建关联子事件或开放紧急例外通道。

## 9. 优先级处理（PRD 对齐）

工单优先级完全按 PRD 执行：员工在提单表单自选 `priority=HIGH/MEDIUM/LOW`，默认 `MEDIUM`；选中 HIGH 时前端提示"高优先级将同步短信通知，请确认确为紧急故障"；通知服务按 PRD 对 HIGH 级在企微推送失败 3 秒后触发短信兜底。

影响范围 × 紧急程度矩阵降级为 L1 坐席侧辅助校验工具：

- `impact_scope`、`urgency` 仅在 AI 会话与 L1 工作台内部收集与展示，不进入工单对外字段；
- L1 坐席接入后比对员工自选优先级与矩阵建议值，偏差显著时（如单人影响选了 HIGH）可下调修正，修正记录入会话审计，工单以修正后值为准；
- 转人工预览（报修卡）中的 `suggested_ticket.priority` 仅为预填建议，默认 MEDIUM，员工确认前可修改。

矩阵辅助视图示例：

| 影响范围 \ 紧急程度 | LOW | NORMAL | HIGH | CRITICAL |
|---|---:|---:|---:|---:|
| SINGLE_USER | LOW | LOW | MEDIUM | HIGH |
| TEAM | LOW | MEDIUM | HIGH | HIGH |
| DEPARTMENT | MEDIUM | MEDIUM | HIGH | HIGH |
| MULTI_DEPARTMENT | MEDIUM | HIGH | HIGH | HIGH |
| COMPANY_WIDE | HIGH | HIGH | HIGH | HIGH |

矩阵版本、建议值和坐席修正都要落库（会话侧审计），不影响工单字段语义；工单 priority 的最终值仍由 PRD 提单表单产生。

`impact_scope` 取值：`SINGLE_USER`、`TEAM`、`DEPARTMENT`、`MULTI_DEPARTMENT`、`COMPANY_WIDE`；`urgency` 取值：`LOW`、`NORMAL`、`HIGH`、`CRITICAL`。

## 10. SLA 与层级升级

SLA 至少覆盖：AI 首次响应、L1 首次接入、L1 处理时长、工程师首次响应、Request 审批等待和 Incident 恢复。

超时升级规则：

```text
第一次超时 → @当前处理人
第二次超时 → @L1 组长 / 工程师组长
持续超时或高优先级超时 → @服务经理 / 值班经理
```

每次升级写入 `sla_escalation_log`，记录 `target_role`、`threshold`、`notified_at`、`channel`、`delivery_status`。升级消息复用通知调度和幂等机制。

## 11. RAG 知识库设计

### 6.1 知识来源

第一阶段纳入：FAQ、IT 操作手册、服务政策/目录、已解决并经过脱敏审核的历史工单。

历史工单必须经过：

```text
工单验收通过(ACCEPTED) → 脱敏 → 提取问题/原因/步骤/结果
                      → 相似度判重 → FAQ 草稿 → 知识库管理员审核 → 发布正式知识
```

沉淀决策对齐泳道图（双环节）：工程师提交处理结果时勾选「沉淀至知识库」为**沉淀建议**；最终由**知识库管理员研判并审核**——审核通过则发布入库，研判不通过或未勾选则仅工单归档，不生成公共知识。

触发与判重契约（对齐 PRD FAQ 自动生成接口）：

- `ticket-service` 在工单验收通过（ACCEPTED，含 48h 超时自动通过）后异步调用 `POST /internal/ai/knowledge/ingest`，携带 `ticket_id / category / title / solution_text / asset_id`，即 PRD `POST /api/kb/faq/generate` 的内部入口；
- 失败不影响关单：ingest 侧负责重试，重试耗尽后落 `kb_ingest_task` 待人工处理（对应 PRD"归档候选队列"）；
- 生成的 FAQ 一律 `faq_status=DRAFT`，知识库管理员审核后方可发布（人机回环）；
- 相似度判重防污染（对齐 PRD `merged / similarity_group_id`）：草稿与库内条目计算向量相似度，超过阈值（默认 cos > 0.92，可配）自动合并进既有 `similarity_group_id`，不新建条目，仅追加现象变体；灰区（0.75～0.92）打"疑似重复"标记，知识库管理员审核时并排展示相似条目辅助合并/新建决策。

### 6.2 切片策略

- 以标题、问题现象、适用条件、排查步骤、预期结果为语义单元。
- 默认 300～600 个中文字符，重叠 50～80 个中文字符。
- 保留 `heading_path`，避免切片脱离章节语义。
- 每个切片带 `category`、`system_stage`、`access_scope`、`status` 元数据。

### 6.3 检索链路

```text
用户问题
  ↓ 清洗与脱敏
  ↓ 意图识别与分类
  ├─ MySQL FULLTEXT 关键词检索
  └─ Qdrant 向量检索
       ↓ 加权 RRF / 分数合并
       ↓ Rerank 前 8～20 条
       ↓ 最终取 3～5 条
       ↓ 可信度判断
       ↓ Qwen JSON Schema 生成
```

初始配置：向量候选 20、关键词候选 20、重排候选 8、最终上下文 5、最低 Grounding Score 0.70。

### 6.4 不命中处理

1. 第一次不命中：只追问一个澄清问题。
2. 第二次仍不命中：提示知识库无法确认，并提供转人工。
3. 命中高风险关键词：立即转人工。
4. 禁止因为没有检索结果而让模型自由发挥。

## 7. Provider 适配层

```java
public interface LlmProvider {
    ChatDecision complete(ChatContext context);
    Flux<ChatStreamEvent> stream(ChatContext context);
}

public interface EmbeddingProvider {
    List<float[]> embed(List<String> texts);
}

public interface RerankProvider {
    List<RankedDocument> rerank(String query, List<RetrievedDocument> documents);
}
```

当前实现：`QwenOpenAiProvider`。

Provider 只负责协议转换和调用，不负责转人工业务规则、不负责工单写操作。

```yaml
ai:
  provider:
    type: qwen-openai
    base-url: ${DASHSCOPE_BASE_URL}
    api-key: ${DASHSCOPE_API_KEY}
    chat-model: ${AI_CHAT_MODEL:qwen-plus}
    embedding-model: ${AI_EMBEDDING_MODEL:text-embedding-v3}
    rerank-model: ${AI_RERANK_MODEL:}
    connect-timeout-ms: 2000
    read-timeout-ms: 15000
    max-retries: 1
    temperature: 0.2
    response-format: json_schema
    schema-version: v1
```

## 8. JSON Schema 约束

Schema 文件放在：

```text
ai-service/src/main/resources/schemas/chat-decision.schema.json
ai-service/src/main/resources/schemas/escalation-decision.schema.json
```

`ChatDecision` 必须包含：`action`、`answer`、`confidence`、`citations`、`need_user_confirmation`、`risk_flags`。

`action` 仅允许：

```text
ANSWER
ASK_CLARIFICATION
OFFER_HUMAN
RESOLVED
SAFETY_BLOCKED
```

Schema 必须设置 `additionalProperties: false`，并在服务端校验：

1. JSON 是否可解析；
2. 是否符合 Schema；
3. 引用的 `document_id/chunk_id` 是否存在且属于本次检索结果；
4. 生成的分类、优先级是否属于系统枚举；
5. 风险标记是否命中硬规则。

非法结果最多重试一次，仍失败则不展示模型文本，进入固定降级提示或转人工。

## 9. API 设计

### 9.1 对外接口

```http
POST /api/v1/ai/sessions
GET  /api/v1/ai/sessions/{session_id}
POST /api/v1/ai/sessions/{session_id}/messages
POST /api/v1/ai/sessions/{session_id}/resolve
POST /api/v1/ai/sessions/{session_id}/handoff/preview
POST /api/v1/ai/sessions/{session_id}/close
```

`messages` 使用 SSE 流式响应，事件类型：`delta`、`result`、`error`、`done`。

### 9.2 转人工预览

`POST /api/v1/ai/sessions/{session_id}/handoff/preview` 只生成预览，不创建工单。

返回字段：

```text
handoff_id
reason_code
suggested_ticket.title
suggested_ticket.category
suggested_ticket.priority
suggested_ticket.description
suggested_ticket.asset_id
missing_fields
conversation_summary
```

`suggested_ticket` 各字段均为预填建议：`category` 映射回 PRD 五值枚举，`priority` 建议值默认 MEDIUM，员工确认前可修改；`missing_fields` 为提单页高亮提示的待补字段。

用户确认后，前端调用现有 `POST /api/v1/tickets`。推荐 `client_token` 使用 `ai-{session_id}`，确保重复提交不会生成重复工单（对应 PRD `idempotency_key` 防重）。

### 9.3 内部接口

```http
POST /internal/ai/knowledge/ingest
POST /internal/ai/knowledge/publish
POST /internal/ai/knowledge/reindex
GET  /internal/ai/health
```

内部接口仅允许服务间调用，不对浏览器公开。

## 10. 数据模型

### `ai_chat_session`

```text
session_id, user_id, entry, status, current_intent, category,
severity, turn_count, last_confidence, handoff_reason_code,
started_at, last_active_at, resolved_at, expired_at
```

### `ai_chat_message`

```text
id, session_id, turn_no, role, content, structured_payload,
citations, model_name, prompt_version, retrieval_trace_id,
latency_ms, token_usage, created_at
```

### `ai_handoff`

```text
handoff_id, session_id, user_id, reason_code, summary,
suggested_title, suggested_category, suggested_priority,
suggested_description, asset_id, missing_fields,
status, ticket_id, created_at, confirmed_at
```

`suggested_*` 字段均为建议值，以员工确认提交的工单字段为准（PRD 契约）；`suggested_category` 存 PRD 五值枚举。

### `ai_model_call_log`

```text
id, session_id, message_id, provider, model, operation,
request_hash, response_status, latency_ms, input_tokens,
output_tokens, error_code, created_at
```

不保存 API Key、密码、完整未脱敏 Prompt 或其他用户敏感数据。

### 知识库表

`kb_document` 保存文档元数据；`kb_chunk` 保存切片、关键词、向量 ID、权限范围和内容哈希；`kb_ingest_task` 记录导入/切片/向量化任务；`kb_feedback` 记录知识引用后的有用性和解决结果。

## 11. 前端改造点

```text
frontend/src/api/index.js             新增 aiApi
frontend/src/components/AiChatPanel.vue
frontend/src/components/AiMessageList.vue
frontend/src/components/AiCitationList.vue
frontend/src/components/AiHandoffCard.vue
frontend/src/components/AiTicketPreview.vue
frontend/src/stores/aiChat.js
frontend/src/views/EmployeeView.vue  增加智能客服 Tab
```

前端不自行判断转人工，只消费后端结构化结果。转人工确认后复用现有提单表单和字段校验。

## 12. 安全、降级与可观测性

### 12.1 安全

- JWT 中的 `user_id` 是会话归属唯一来源。
- API Key 仅在服务端配置。
- 知识库按 `access_scope` 过滤。
- 用户输入、附件 OCR 文本和知识片段都视为不可信文本。
- Prompt Injection、敏感字段和高风险动作由固定规则拦截。
- 手机号、邮箱、身份证、密码、Cookie、API Key 和敏感内网地址在外发模型前脱敏。

### 12.2 降级

| 故障 | 行为 |
|---|---|
| Qwen 超时 | 重试一次，失败后固定提示或转人工 |
| Schema 非法 | 重试一次，仍失败不展示模型文本 |
| Embedding 失败 | 降级到关键词检索 |
| Qdrant 不可用 | 使用 MySQL FULLTEXT |
| Rerank 不可用 | 使用初始检索分数 |
| SSE 断开 | 使用 `message_id` 幂等重试 |
| ticket-service 不可用 | 保存转人工草稿，稍后重试建单 |
| ai-service 不可用 | 原提单链路完全可用 |

### 12.3 指标

```text
ai_chat_requests_total
ai_chat_latency_ms
ai_first_token_latency_ms
ai_provider_error_total
ai_schema_validation_error_total
ai_retrieval_hit_rate
ai_grounded_answer_rate
ai_handoff_rate
ai_resolution_rate
ai_session_turn_count
ai_token_usage_total
ai_cost_estimate
```

日志统一携带 `trace_id`、脱敏后的用户标识、`session_id`、`message_id`、`retrieval_trace_id`、Provider、模型、延迟和状态。

## 13. 测试与验收

### 单元测试

- 会话状态机和轮数规则；
- 高风险立即转人工；
- 置信度阈值和分类优先级映射；
- JSON Schema 和引用存在性校验；
- 转人工摘要和字段完整性。

### 集成测试

- Qwen、Embedding、Rerank Mock；
- Qdrant 检索和 MySQL FULLTEXT 降级；
- ticket-service 建单契约；
- SSE 流式返回和断线重试；
- `client_token` 重试幂等。

### 安全测试

- Prompt Injection；
- API Key 和敏感信息泄露；
- 越权读取会话或知识；
- 模型触发高风险写操作；
- 恶意附件、超长消息和频率攻击。

### 业务验收

1. FAQ 命中并在 3 轮内解决；
2. 错误码问题返回精确引用；
3. 无匹配知识时澄清并转人工；
4. 用户第 3 轮主动转人工；
5. 用户第 5 轮仍未解决时强制转人工；
6. 生产故障跳过普通排查；
7. Qwen 超时不影响传统提单；
8. Qdrant 故障退化为关键词搜索；
9. 非法 JSON 不污染前端；
10. 转人工预填后可以正常创建工单；
11. 相同 `client_token` 不生成重复工单；
12. 员工不能检索工程师/知识库管理员内部知识。
13. 工单对外字段与 PRD 契约一致：category 五值、priority 三档且默认 MEDIUM，HIGH 级企微失败后短信兜底联动正常。
14. FAQ 草稿相似度超阈值自动合并（merged=true 且挂 similarity_group_id），不产生重复知识条目。
15. 工单验收通过后知识入库触发链路失败时不影响关单，重试耗尽落 `kb_ingest_task`。

### 初始性能目标

```text
知识检索 P95             < 500ms
首个流式字符 P95         < 2s
完整回答 P95             < 15s
普通消息失败率           < 1%
Schema 校验成功率        > 99%
转人工草稿生成           < 2s
AI 故障时传统提单成功率   100%
```

## 14. 分阶段实施顺序

### Phase 1：AI 服务骨架

- 新增 `ai-service` 模块和 Nacos 注册；
- 网关增加 AI 路由；
- JWT 用户上下文透传；
- 会话、消息、转人工表；
- Qwen Provider 和 JSON Schema 校验。

### Phase 2：RAG MVP

- 知识库文档/切片表；
- MySQL FULLTEXT；
- Qdrant 向量检索；
- 混合检索和引用返回；
- 知识导入、发布、重建索引接口。

### Phase 3：前端对话和转人工

- 员工工作台智能客服 Tab；
- SSE 消息流；
- 知识引用卡片；
- 转人工预览；
- 复用现有提单表单完成建单。

### Phase 4：安全与运营

- Prompt Injection、脱敏、权限过滤；
- 限流、审计、指标和告警；
- 压测和全量验收场景；
- 已解决工单转 FAQ 草稿流程（含相似度判重与自动合并）。

## 15. 完成定义

以下条件全部满足后，第一版智能客服视为完成：

1. 员工可在工作台创建和恢复 AI 会话。
2. Qwen 返回结果经过 JSON Schema 校验。
3. 至少一类 FAQ 能通过 RAG 正确命中并返回引用。
4. 第 3/5/6 轮转人工规则有自动化测试。
5. 转人工预览可填充现有工单表单并成功建单。
6. Qwen、Qdrant、ai-service 故障时传统提单仍可用。
7. 无越权知识访问、无 API Key 泄露、无模型直接写工单状态。
8. 关键指标、日志和错误降级可观测。
9. 工单对外契约与 PRD（10）一致：category 五值、priority 三档（员工自选、默认 MEDIUM），转人工接口字段按 2.4 映射表输出。
10. FAQ 自动生成走 DRAFT＋知识库管理员审核＋相似合并，验收通过的工单知识入库不阻塞关单。
