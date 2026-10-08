# consultation-service · 智能客服与转人工

对应 PRD-v2 的 **F-02(咨询入口与知识搜索)、F-03(转人工及人工咨询)、F-13(RAG/AI 回答、引用、拒答、反馈)**。
本服务是**咨询会话状态的唯一写入方**，与用户、工单服务共用规范数据库 `it_ticket_system`；共享表按业务类型隔离。

2026-10-08：默认已接入 rag-service 混合检索。联调配置、降级语义和验证命令见 [RAG-INTEGRATION.md](RAG-INTEGRATION.md)，接口契约见 [RAG 对接说明](../rag-service/INTEGRATION.md)。

端口 `8301`,通过 gateway 的 `/api/v1/consultations/**`、`/api/v1/knowledge/**` 路由访问。

---

## 1. 契约映射

| 实现 | 契约来源 |
|---|---|
| 咨询状态机 `statemachine/ConsultationStateMachine` | SM-CONSULT-001(唯一实现,纯函数) |
| AI 接口 `controller/AiConsultationController` | AI-005 的 AI-API-002 / 003 / 004 |
| 创建咨询、会话读写 `controller/ConsultationController` | AI-API-001 + OpenAPI 05 `/consultations` 系列 |
| 知识搜索 `controller/KnowledgeSearchController` | AI-API-005(只返回 `PUBLISHED` 当前版本) |
| AI 输出闸门 `service/AiAnswerGuard` | AI-001 能力边界、AI-008 输出校验 |
| RAG 隔离壳 `adapter/GuardedRagClient` | RD-003 超时重试、RD-007 断路器与并发隔离 |
| 模型接入 `adapter/OpenAiCompatibleRagAdapter` | AX-003 / AX-007 外部适配器,受约束生成 |
| 转人工分配 `service/AssignmentService` | PRD 8.4 / 12.1 / 12.2、RD-005 |
| 响应 SLA `service/ConsultationSlaService` + `WorkCalendar` | PRD 11.1 / 11.2 / 11.3、AX-002、AX-008 |
| 幂等 `service/IdempotencyService` | RD-002 |
| 领域事件 `service/OutboxService` + `scheduler/OutboxPublishScheduler` | EV-001 / EV-002 / EV-004 / EV-009 |
| 授权判定 `service/AuthzService` | AX-001、AX-006、PRD 5.2 |
| 表结构 `db/init/00-schema.sql` | DM-004、SQL-010；仅已实现模块对齐，详见 `db/README.md` |

响应包络按 **PRD 21.1** 的 `{code, message, request_id, data}`,错误码取 PRD 21.3 + AI-006。
这与旧模块(user-service / ticket-service)的 `{code, msg, data}` 不同 —— 见第 5 节。

---

## 2. 主链路

### 2.1 智能客服

```
POST /api/v1/consultations                 source=AI        → AI_ACTIVE
POST /api/v1/consultations/{id}/ai-messages                  → ANSWER / CLARIFY / REFUSE
POST /api/v1/consultations/{id}/feedback                     → 持久化待处理反馈标记
```

每次 AI 回答依次经过:

1. 会话状态必须是 `AI_ACTIVE`,否则 `AI_SESSION_NOT_ACTIVE`;
2. 员工提问先落库 —— 即便后续 AI 降级,对话历史仍然完整;
3. 默认由 rag-service 返回领域和知识策略：`OFFICE_IT` 才进入生成，`OFF_TOPIC` 明确拒答，`HIGH_RISK` 转人工，`UNCERTAIN` 追问；显式配置 `retrieval-provider=mysql` 时保留模型分类与 SQL 检索的兼容链路；
4. `ai.answer-enabled=false`(评测未达 PRD 17.3 上线门槛)→ `REFUSE / POLICY_BLOCKED`;
5. 否则经 `GuardedRagClient` 调用 RAG:超时、并发上限、连续 5 次失败打开断路器;
6. **输出闸门 `AiAnswerGuard`** 按固定优先级判定,任一条不过即结构化拒答:
   `POLICY_BLOCKED → HIGH_RISK_TOPIC → MODEL_UNAVAILABLE → NO_RELIABLE_KNOWLEDGE(Schema)
   → CONFLICTING_KNOWLEDGE → NO_RELIABLE_KNOWLEDGE(引用失效)→ LOW_CONFIDENCE`;
7. 有依据时优先引用已发布知识；无命中或命中不足时可提供办公 IT 通用建议。通用回答引用为空，不能冒充内部政策或编造地址/来源；任何实际引用都必须仍为 `PUBLISHED` 当前版本，失效即整体拒答；
8. 写 `ai_interaction`(模型版本、命中知识版本、置信度、耗时)，消息的 `citation_json` 写 schemaVersion=1 元数据（引用、interactionId、replyType、refusalReason、generalAnswer），历史读取兼容旧引用数组，不写提示词与推理过程。

员工可主动确认 `AI_ACTIVE → RESOLVED`；AI 不自动确认、建单或修改企业系统。调用模型期间关闭咨询后，原有写锁复核仍会阻止迟到回答落库。

反馈接口保持兼容：`HELPFUL`、`NOT_HELPFUL`、`INCORRECT` 都更新 `ai_interaction.feedback`，
`queuedForOptimization=true` 只表示持久化待处理标记。当前没有队列消费者、脱敏任务或知识审核后台，
不能把该字段理解为已经脱敏入库；未来知识域必须完成脱敏、审核后才能发布，不能直接训练或自动发布。

**降级策略**:模型/检索故障统一表达为结构化拒答 + `suggestTransfer=true`,而不是抛 `AI_UNAVAILABLE`。
RD-006 允许两者二选一,选拒答是因为会话保持可用、客户端只需处理一种结构(RD-013 要求降级结果可判定)。
降级分类仍进日志与 `ai_interaction`,可按 RD-010 统计拒答率。

### 2.1.1 生成侧接入

`itticket.consultation.ai.provider` 二选一:

| 取值 | 行为 |
|---|---|
| `openai-compatible` | 走 OpenAI 兼容端点做受约束生成(当前默认) |
| `local` | 不调外部模型,只按检索结果拼装答案。离线、演示或评测未上线时使用 |

`local` 不具备模型通用知识能力，无命中仍拒答；冷启动通用回答策略需使用 `openai-compatible`。检索独立由 `retrieval-provider=rag-service|mysql` 决定，默认使用 RAG；关键词高风险兜底仅用于 `local + mysql` 兼容模式。

**两种模式下检索都只读 `PUBLISHED` 当前版本**,模型拿不到数据库、未发布案例、原始工单或聊天正文。

三道硬约束:

1. **引用不可由模型编造** —— 模型只回答"用了哪几个 `versionId`",引用条目的
   `articleId/versionId/title/snippet/score` 全部由服务端用检索结果重建。
   模型给出的 `versionId` 只要有一个不在本次检索集合内,整次输出判为无效(AI-008)。
2. **内部推理不外泄** —— thinking 类模型会返回 `reasoning_content`,本服务只读
   `choices[0].message.content`,推理字段不解析、不落库、不写日志(AI-001、AI-008)。
3. **先范围判定再受约束生成** —— 无命中仍可生成办公 IT 通用建议；即使无命中，模型给出的任何虚构 versionId 也会导致整次输出无效。有命中但不相关时允许不引用，不把不相关来源挂到通用答案上。

检索和生成共享同一次 `GuardedRagClient` 的总超时与并发保护，重试也消耗同一预算。RAG 模式只调用一次生成模型；MySQL 兼容模式另加一次模型分类。
两次调用都严格验证完整响应、字段类型、置信度范围和引用，不接收工具调用或截断响应。
HTTP stub 测试验证流程与边界，不能证明真实模型对自然语言、混合请求和提示注入的分类准确率；上线仍需代表性语义评测。

配置项:

```yaml
itticket.consultation.ai:
  provider: openai-compatible
  base-url: https://<endpoint>/compatible-mode/v1   # 不含 /chat/completions
  api-key: ${AI_API_KEY:}                            # 见下方「凭据」
  model: qwen3-vl-32b-thinking
  max-output-tokens: 8192
  temperature: 0.0
```

**凭据**:`application.yml` 只留 `${AI_API_KEY:}` 占位。本地开发把真实 key 写在模块根目录的
`ai-secrets.yml`(已 gitignore,不打进 jar),由 `spring.config.import: optional:file:./ai-secrets.yml`
加载;生产走环境变量或 Nacos 配置中心(AX-007:凭据从加密配置读取)。
文件缺失时 `api-key` 为空,AI 回答降级为 `NOT_CONFIGURED`,**知识搜索、人工咨询与转人工不受影响**。

**两个实测踩坑**(端点 `qwen3-vl-32b-thinking`):

- `max_tokens` 把**推理 token 也算在内**。给 800 时推理占满、`content` 返回空字符串,
  表现为无声的无效输出。默认给到 8192,不要按 `answerText` 的 12000 字符上限倒推。
- 延迟波动大:实测单次问答 11~73 秒(推理 token 从 481 到 3300 不等),最差一次超过 120 秒。
  RD-003 规定完整 15 秒,按契约值会几乎每次降级成 `MODEL_UNAVAILABLE`,
  因此 `request-timeout-ms` 暂放宽到 120 秒 —— **这是已知的性能契约偏离**,见第 4 节 G10。
- 模型自评的 `confidence` 偏乐观(命中时直接给 1.0),所以 `min-confidence` 这道闸门
  主要挡的是"模型自己都不确定"的情况,**不能当作答案质量的度量**。
  真正的质量保证来自:引用必须落在检索集合内、引用版本必须仍是 PUBLISHED 当前版本,
  以及 PRD 17.3 的上线评测。

### 2.2 转人工

```
POST /api/v1/consultations/{id}/transfer   {categoryId}
  → AI_ACTIVE 或起点 → WAITING_ENGINEER
  → 按 PRD 12.1 选候选工程师 → 建 assignment(10 个工作分钟响应截止)
  → 启动 CONSULTATION_RESPONSE SLA → 发 CONSULTATION_TRANSFERRED
```

- 候选算法:分类路由有序团队 → 团队内 `AVAILABLE` 且可接该分类 → 加权负载最低 → 同负载取最久未分配;
- 无候选人:保持 `WAITING_ENGINEER`,写异常队列,**不**把分配失败写成咨询终态;
- 已在 `WAITING_ENGINEER` 时重复调用 → 幂等返回当前分配(SM-001);
- 响应超时由 `ConsultationResponseTimeoutScheduler` 处理:抢占式结束分配 → 记违约 →
  转派下一候选人 → 候选人耗尽入异常队列(AC-08 / AC-09);
- 转派**不重置**咨询级 SLA 投影(RD-005),新候选人计时由新 assignment 的 `response_deadline` 承载;
- 违约一经写入不再清除,恢复咨询只重置目标与状态(PRD 11.2)。

### 2.3 人工咨询与收尾

| 动作 | 接口 | 迁移 |
|---|---|---|
| 工程师首次有效回复 | `POST /{id}/messages`(工程师身份) | `WAITING_ENGINEER → HUMAN_ACTIVE` |
| 员工回复未解决 | `POST /{id}/messages`(员工身份) | `PENDING_CONFIRMATION → HUMAN_ACTIVE` |
| 工程师提交结论 | `POST /{id}/resolution` | `HUMAN_ACTIVE → PENDING_CONFIRMATION` |
| 员工确认解决 | `POST /{id}/confirmation` ⚠ | `PENDING_CONFIRMATION → RESOLVED` |
| 员工主动结束 | `POST /{id}/close` | 任意非终态 → `CLOSED` |
| 24 小时内恢复 | `POST /{id}/reopen` | `RESOLVED → WAITING_ENGINEER` |
| 转工单回写 | `POST /api/internal/consultations/{id}/converted` ⚠ | 任意非终态 → `CONVERTED_TO_TICKET` |

打开、已读和系统消息都不算首次有效响应(SM-CONSULT-001 规则补充)。

---

## 3. 运行

```bash
# 1. 建库与种子(docker-compose 首次启动自动执行 db/init/*.sql)
docker compose up -d mysql nacos

# 2. 启动
mvn -pl consultation-service -am spring-boot:run
```

所有 `/api/v1/**` 请求必须带 `X-Request-Id`;写接口必须带 `Idempotency-Key`(AI-002、OpenAPI 05)。

```bash
curl -X POST http://localhost:8080/api/v1/consultations \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Request-Id: req_demo_1" -H "Idempotency-Key: idem_demo_1" \
  -H "Content-Type: application/json" \
  -d '{"source":"AI"}'

curl -X POST http://localhost:8080/api/v1/consultations/$SID/ai-messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Request-Id: req_demo_2" -H "Idempotency-Key: idem_demo_2" \
  -H "Content-Type: application/json" \
  -d '{"message":"打印机显示离线,怎么处理?"}'

curl -X POST http://localhost:8080/api/v1/consultations/$SID/transfer \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Request-Id: req_demo_3" -H "Idempotency-Key: idem_demo_3" \
  -H "Content-Type: application/json" \
  -d '{"categoryId":"CAT-IT-DEVICE"}'
```

种子数据：工程师 `U_ENG01`（`AVAILABLE`）、分类 `C_HW_PC/C_HW_PR/C_SW/C_NET/C_ACC/C_OTH`，
4 篇知识(3 篇 `PUBLISHED` + 1 篇 `OFFLINE`,用于验证下线版本不被检索)。

---

## 4. 契约缺口(需要回写 spec 或由其他模块补齐)

标 ⚠ 的是**实现补出来、契约里没有**的部分,需要确认:

| 编号 | 问题 | 现状处理 |
|---|---|---|
| G1 | SM-CONSULT-001 有"员工确认解决"迁移,OpenAPI 05 与 AI-005 都没有对应路径 | 补 `POST /consultations/{id}/confirmation`,需回写 05 |
| G2 | 咨询转工单缺少咨询侧的状态回写接口 | 补内部接口 `POST /api/internal/consultations/{id}/converted`,由 ticket-service 建单成功后调用 |
| G3 | `ConsultationSource.TICKET_FOLLOW_UP` 在 SM-CONSULT-001 没有对应起点行 | 按"需要人工跟进"归入人工起点,需确认 |
| G4 | PRD 8.3 的自动解决要求"员工会话已断开",DM-004 没有承载该事实的字段 | `EmployeePresenceProvider` 默认返回未断开,自动解决**不会触发**;不用超时沉默冒充断开 |
| G5 | EV-008 的 `consultationTransferred` 把 `assignment_id` 列为必填 | 无候选人时不发该事件,事实由异常队列 + 审计承载 |
| G6 | AI-005 的 DTO 是 camelCase,OpenAPI 05 的 Schema 是 snake_case | 各自遵循所属契约,未统一;建议在 spec 层统一 |
| G7 | AI-006 的错误包络有 `fallback`,05 的 `ErrorEnvelope` 是 `additionalProperties:false` 且未声明它 | 按 AI-006 输出,非 AI 错误时省略;建议 05 补声明 |
| G8 | `knowledge_version.search_text` 是为 ngram 全文索引新增的生成列 | 只是可重建的检索投影,非业务事实;建议在 DM-004/SQL-010 登记 |
| G9 | 网关鉴权失败仍返回旧包络 `{code:int,msg,data}` | 本服务内已统一,网关侧未改;跨模块统一需单独排期 |
| G11 | OpenAPI 05 的 `MessageProjection` 只声明 `message_id/sent_at/withdrawn_at` 且 `additionalProperties:false`,按字面实现聊天记录读不出正文,与 PRD 5.2/13.1「普通聊天正文对本人和当前负责人可见」冲突 | 已按产品需求扩展为含 `sender_type/content/citations`;撤回消息只返回占位文案不返回原文。需回写 05 |
| G10 | RD-003 要求 AI 完整响应 15 秒,实测 `qwen3-vl-32b-thinking` 单次 11~73 秒,最差超过 120 秒 | 已按业务决定放宽 `request-timeout-ms` 到 120 秒保证可用。上线前二选一:换更快的模型,或走变更流程修订 RD-003 |

## 5. 不在本服务范围

- **工单创建与工单字段**:ticket-service。AI 不得创建、修改或关闭工单(AI-001),咨询服务也不写工单表。
- **`GET /consultations/{id}/ticket-draft`**(已实现):预填数据由本服务从咨询会话生成
  (标题取员工首条消息、描述/摘要取完整时间线,PRD 9.1 第 3 条);工单域的字段定义与
  草稿持久化仍归 ticket-service / user-service,本接口只读、不创建工单。
- **消息撤回、附件**:F-09 附件与消息域。`consultation_message` 已预留撤回列,`ContentRequest`
  收到 `attachment_ids` 时显式报错而非静默丢弃(RD-013)。
- **通知投递**:F-10。本服务只发领域事件,不直接发通知。
- **知识审核与发布**:F-12 知识域。本服务对 `knowledge_*` 表**只读**。
- **工单侧负载**:`TicketWorkloadProvider` 默认返回 0,接入 ticket-service 内部接口后替换实现即可。
- **Outbox 投递到 Redis Streams**:当前技术栈无 Redis,`DomainEventPublisher.Logging` 是接线点;
  接入真实队列前不得宣称满足 EV-003 的端到端投递语义(TR-005)。
- **向量检索与 Rerank**:当前召回是 MySQL ngram 全文索引 + LIKE 回退,没有 Embedding 与向量库。
  模型负责范围判定与受约束生成，不承担召回。召回不足时允许办公 IT 通用建议；实际使用的知识引用仍严格校验，并持续改进检索质量。

## 6. 关键实现约定

- **时间**:持久化层用 `LocalDateTime` 承载 **UTC 挂钟时间**写入 `DATETIME(6)`,JDBC 不做时区换算;
  对外一律 `Times.iso(...)` 输出 ISO 8601 带时区。**禁止**无参 `LocalDateTime.now()` 和 SQL 里的 `NOW()`。
- **乐观锁**:不装 MyBatis-Plus 的乐观锁拦截器,全部用 `LambdaUpdateWrapper` 手写 `WHERE version = ?`
  并按影响行数判冲突,冲突返回 `ASSIGNMENT_CHANGED`(DM-001、DM-005)。
- **幂等**:幂等记录在业务事务的最后插入,并发同键者在唯一索引上阻塞后整体回滚并重放首次结果,
  因此 `IdempotencyStatus.IN_PROGRESS` 不会落库。
- **事务边界**:调度器与幂等执行器都用 `TransactionTemplate`,不用 `@Transactional` ——
  同类内部调用不经过 Spring 代理,注解在那里是无效的。
- **越权**:对象不存在与无权访问统一返回 `OBJECT_NOT_FOUND`,不向无权主体泄露对象存在性(AX-001)。
