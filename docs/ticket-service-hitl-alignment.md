# ticket-service HITL 门禁对齐 Day18 讲义 — 变更说明

> 「强制 Human-in-the-Loop 人机确认（派单草案主管点击才生效）；派单幂等防重与失败补偿」

---

## 一、变更总览

| 项目 | 数据 |
|---|---|
| 新增 Java 文件 | 8 个，共 991 行 |
| 修改 Java 文件 | 4 个，+233 / −68 行 |
| 新增测试场景 | 13 个（`HitlDispatchApprovalTest`） |
| 测试总结果 | 131 通过 / 0 失败（118 回归 + 13 新增 HITL） |
| 新数据表 | `dispatch_draft`（1 张） |
| 迁移脚本 | `db/migration/V2_5__dispatch_approval_draft.sql` |

---

## 二、新增文件清单

| 文件 | 行数 | 说明 |
|---|---|---|
| `entity/DispatchDraft.java` | 60 | HITL 门禁实体。`PENDING / APPROVED / REJECTED / EXPIRED` 四态，含 `claimedBy / claimedAt / expiresAt / version` |
| `dto/DispatchDraftPayload.java` | 45 | 审批人可读的结构化载荷。落库快照，含候选人、选人依据、候选列表、失效时间 |
| `dto/DecideDispatchRequest.java` | 21 | 裁决请求体：`approve / resolution / reason`。与异常队列共用 |
| `mapper/DispatchDraftMapper.java` | 8 | MyBatis-Plus Mapper |
| `service/DispatchDraftService.java` | 384 | **门禁核心状态机**：生成草案（幂等防重）→ 认领（乐观锁防并发）→ 裁决（条件更新）→ 批准回调 `confirmDispatch` → `scanExpired` 定时失效扫描 |
| `service/RouteOutcome.java` | 37 | 路由结果类型。三态显式：`DRAFT_PENDING`（正常路径）/ `ROUTE_FAILED`（失败）/ `SKIPPED`（正常空结果）。替代原来用 `null` 兼表多义的 `String` 返回 |
| `controller/DispatchDraftController.java` | 106 | `GET /api/v1/dispatch-drafts` 待办列表 · `GET /{id}` 详情 · `POST /{id}/claim` 认领 · `POST /{id}/decide` 裁决 |
| `test/HitlDispatchApprovalTest.java` | 330 | 13 个场景，覆盖讲义验收第 3 条全部检查点 |
| `db/migration/V2_5__dispatch_approval_draft.sql` | — | `dispatch_draft` 建表 + 两个唯一约束：`uk_dispatch_draft_pending`（同一工单同时仅一份待确认草案，MySQL 8 生成列）+ `uk_dispatch_draft_idem`（同一轮路由防重） |

---

## 三、修改文件清单

| 文件 | 改动说明 |
|---|---|
| `service/RoutingService.java` | `route()` 返回类型 `String` → `RouteOutcome`；找到工程师后调 `DispatchDraftService.createDraft()` 而非直接 `assign()` |
| `service/TicketService.java` | 新增 `confirmDispatch(draftId)` 供批准回调调用；`afterCreate()` 不再立即置 `ASSIGNED`，工单保持 `NEW` 待审批确认 |
| `service/ExceptionQueueService.java` | 新增 `claim(exceptionId, adminId)` 与 `settle(exceptionId, adminId, reason, dismissed)` — 异常队列从只读变为可闭环 |
| `controller/ExceptionQueueController.java` | 新增 `POST /{exceptionId}/claim` 认领端点 · `POST /{exceptionId}/decide` 裁决端点 |

---

## 四、既有测试同步迁移（8 个文件，按要求不改旧断言语义只适配接口）

| 文件 | 适配点 |
|---|---|
| `PrdRoutingStatusTest.java` | `RoutingService` 构造器新增 `DispatchDraftService` 依赖 |
| `RoutingDirtyDataTest.java` | `assertNull(route())` → `RouteOutcome.Kind.ROUTE_FAILED`（A1 语义修正，null 不再兼表多义） |
| `RoutingLoadBalanceTest.java` | 构造器适配 |
| `TicketActionEventTest.java` | `TicketService` / `RoutingService` 构造器适配 |
| `TicketEditTest.java` | 构造器适配 |
| `TicketMergeIntegrationTest.java` | 流转日志断言：2 条（含 `TICKET_ASSIGN`）→ 1 条（仅 `TICKET_CREATE`）—— `TICKET_ASSIGN` 待审批确认后写入 |
| `TicketWithdrawalTest.java` | `TicketService` / `RoutingService` 构造器适配 |
| `UserLookupDegradationTest.java` | 构造器适配 |

---

## 五、与 Day18 讲义核心机制的对照

| 讲义机制（行号） | 我们的实现 | 偏离及理由 |
|---|---|---|
| 挂起状态持久化 — `pending_approval_store: Dict[str, Dict]`（内存，:180-181） | `dispatch_draft` MySQL 表，`PENDING / APPROVED / REJECTED / EXPIRED` | **内存字典 → DB 表**。讲义自称"生产环境应持久化在 Redis 或 PostgreSQL，本教学环境从简"，我们用真实表一步到位 |
| 专属 Token — `f"TOKEN-HITL-{uuid.uuid4()...}"`（:274） | `draft_id` = 数据库主键 + `expires_at` 超时列 | **字符串 Token → 行 ID + 列级超时**。讲义 Token 无过期语义（字典永不过期），我们实现了讲义宣称但未交付的超时失效 |
| 恢复状态机 — `resume_human_approval(token, auditor, approve)`（:311） | `DispatchDraftService.decide(draftId, reason, approve, operatorId, onApproved)` | **回调签名不同**。讲义把 OA 写入嵌在恢复函数里（紧耦合），我们 `onApproved: Consumer<String>` 由调用方注入，门禁与业务解耦 |
| 结构化决策载荷 — `AuditDecisionPayload`（Pydantic BaseModel，:151-163） | `DispatchDraftPayload`（Jackson `@Data`）→ `payload_json` 字段 | **Pydantic → Java Bean**。载荷是落库时的快照，审批人看到的必须是裁决那一刻的依据 |
| 高风险门禁 — `action_required: 'REQUIRE_HUMAN_APPROVAL'`（:163, 273） | `RouteOutcome.Kind.DRAFT_PENDING` + 工单保持 `NEW` | 语义同构。路由返回明确枚举而非 null，工单状态显式留在 `NEW` |
| 驳回必填原因 — 但注释未强制（:319） | `if (!approve && reason.isBlank()) throw PARAM_INVALID` | 讲义只声明应填实际未校验，我们加了强制校验 |
| 并发驳回安全 — `if approval_token not in pending_approval_store`（:313-314） | `UPDATE ... WHERE status='PENDING'` 乐观锁 + `rows != 1` 检查 | 讲义检查存在性但不防并发（两个 Token 可同时 pop 同一 key），我们加了条件更新，并发裁决时后者明确报"已被他人裁决" |

---

## 六、刻意偏离讲义的问题

| 讲义缺陷 | 我们的修正 |
|---|---|
| **Token 无过期**：`pending_approval_store` 字典永不过期，无清理 | `expires_at` + `@Scheduled scanExpired`（每 1 分钟）实现讲义宣称的"超时失效" |
| **内存态重启丢**：`self.pending_approval_store = {}`（:180） | `dispatch_draft` 表落库，进程重启待确认草案仍在 |
| **并发不防**：`if approval_token not in ...` 查有即可 pop | `UPDATE ... WHERE status='PENDING'` + `rows != 1`，第二人明确失败 |
| **驳回后无恢复路径**：驳回了流程终止（:319-323） | 草案 `REJECTED` 后工单保持 `NEW` ，可重新触发 `route()` 生成新草案 |
| **Agent 直接调外部 OA**：`time.sleep(0.02)` 模拟外部 API（:327） | 批准后执行 `RoutingService.assign()` 落 `assignment` + `TicketFlowLog` 审计事件。AI 不直接调 OA，由人在 approve 时触发 |

---

## 七、与讲义架构的角色差异

| 讲义架构 | 我们 | 说明 |
|---|---|---|
| Agent（LLM）执行 | 系统自动路由 | 都是"产生写操作意图的发起方"——都需要被门禁拦住 |
| 人工审核员（Auditor） | `PLATFORM_ADMIN` | PRD §98："系统不设置主管和坐台客服角色"，审批人取 PLATFORM_ADMIN |
| 外部 OA API 写入 | `TicketFlowLog` 事件 + `assignment` 落库 | 都是"批准后执行的真实写操作" |
| 财务总监审批看板 | `GET /api/v1/dispatch-drafts` 待办列表 | 管理员工作台角标来源 |
| 差旅扣款（clawback） | **不实现** | PRD 排除项：无 OA 审批流、无差旅数据、无财务域；知识库种子仅 4 条（打印机离线、VPN、WiFi、旧邮箱），无任何财务制度 |

---

## 八、讲义验收第 3 条 → 测试逐条覆盖

讲义验收标准（:403-408）第 3+4 条：

> **3. 人机回环 (HITL) 门禁**：涉及扣款/超标处分等高风险动作，系统 100% 安全挂起，严禁越权直调写 API。
> **4. Token 状态恢复机制**：审核员凭有效 Token 能够精准唤醒原任务并成功完成外部 API 写入。

在我们的 13 个 `HitlDispatchApprovalTest` 场景中的映射：

| # | 测试场景 | 对应讲义验收点 |
|---|---|---|
| 1 | `routeReturnsDraftPendingAndPreservesNewStatus` | "系统 100% 安全挂起"——路由后工单仍 `NEW`，无任何 assignment 写入 |
| 2 | `approveExecutesAssignmentAndTransitionsTicket` | "凭有效 Token 唤醒原任务"——`draft_id` 定位草案，`onApproved` 回调执行 `RoutingService.assign()`，工单 NEW→ASSIGNED |
| 3 | `rejectPreservesNewStatusAndRecordsReason` | "人工驳回"路径——不执行分派，工单保持 `NEW`，原因留存 |
| 4 | `rejectWithoutReasonIsRejected` | 驳回不填原因 → `PARAM_INVALID` 拒绝 |
| 5 | `decideOnExpiredDraftFailsAndMarksExpired` | "超时失效"——过期草案不可批准，自动置 `EXPIRED` |
| 6 | `duplicateDraftGenerationIsIdempotent` | "幂等防重"（需求归因文档要求）——同一工单同一轮只落一份草案 |
| 7 | `concurrentClaimIsRaceSafe` | "严禁越权直调写 API"——两人同时认领，只有一人成功 |
| 8 | `concurrentDecideIsRaceSafe` | 两人同时裁决，乐观锁保证只有一人生效 |
| 9 | `approveCallbackFailureRollsBackEntireTransaction` | "状态机恢复"——回调失败 → `@Transactional` 回滚，不留"已批准但没分派"的半截状态 |
| 10 | `toPayloadReadsPersistedSnapshotNotLiveData` | 审批人看到的必须是落库快照，不可按当前数据重算 |
| 11 | `claimOnExpiredDraftIsRejected` | 认领瞬间已过期 → `ILLEGAL_TRANSITION` |
| 12 | `doubleDecideOnSameDraftIsRejected` | 已裁决草案不可重复操作（防 Token 重用） |
| 13 | `terminalTicketDoesNotGenerateDraft` | 终态工单不产生草案（脏数据防护） |

---

## 九、为什么不把审批放进 `exception_queue`

`exception_queue` 的唯一键是 `uk_exception_open(object_type, object_id, reason_code, status)`——**含 `status`**。这意味着同一业务同一原因结案后，第二次结案会撞唯一键。派单草案超时、驳回后重新路由都会产生多个 `EXPIRED`/`REJECTED`/`RESOLVED` 记录，不适配。另建 `dispatch_draft` 表零冲突，不承受这一限制。

---

## 十、验证结果

```
[INFO] Tests run: 131, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

- 118 个既有测试全部回归通过（语义修正 2 处：`RoutingDirtyDataTest` 路由失败断言 + `TicketMergeIntegrationTest` 流转日志断言）
- 13 个新增 HITL 场景全部覆盖通过
