# HITL 放行后工单状态未流转 —— 问题报告

> 提出人：RAG 模块（版本消歧）负责人
> 日期：2026-10-21
> 涉及提交：`6a0930b feat(ticket-service): 对齐 Day18 HITL 写操作门禁`
> 严重级别：**P0** —— 门禁放行了，但工单实际没有进入下一状态

---

## 一句话

派单草案**批准放行**后，`assignment` 落了库、`ticket_transition` 记了 `NEW → ASSIGNED`，
但 **`ticket.status` 仍是 `NEW`**、`version` 也没递增。三方数据互相矛盾。

---

## 实测证据

联调环境：本地 Docker（Nacos + Redis）+ 远程 MySQL，`user-service:8101` + `ticket-service:8201`
（手工 `javac` 编译，`provider` 走默认）。走完整链路：

```
① POST /api/v1/tickets                              → 201  TK202610210001  status=NEW  assignee=null
② [路由] 负载均衡选择: U_ENG02 (未结工单 0)
   [派单草案] 已挂起待确认: TK202610210001 -> U_ENG02 草案=DDbf0c0f...
   [通知] DISPATCH_DRAFT_PENDING -> U_ADM01
③ POST /api/v1/dispatch-drafts/{id}/claim           → 200  [派单草案] 已认领 by U_ADM01
④ POST /api/v1/dispatch-drafts/{id}/decide {approve:true}
                                                    → 200  [派单草案] 已批准并放行分派
   AssignmentMapper.insert → Updates: 1
   [通知] ASSIGNED:TK202610210001:U_ENG02:IN_APP
```

**放行后直接查库**（不是接口缓存，连续读两次一致）：

```
工单   TK202610210001:  status=NEW   assignee=U_ENG02   version=0
草案   DDbf0c0f...:     status=APPROVED  engineer=U_ENG02  resolvedBy=U_ADM01
assignment:             1 条活动记录（end_reason=null）
流转日志:               null -> NEW (TICKET_CREATE) by U_EMP01
                        NEW -> NEW (TICKET_DISPATCH_DRAFT_CREATED) by SYSTEM
                        NEW -> ASSIGNED (TICKET_ASSIGN) by PLATFORM_ADMIN   ← 假的
```

**矛盾点**：最后一条流转说到了 `ASSIGNED`，但工单行还是 `NEW`。

数据库日志里那唯一的工单 UPDATE：

```sql
UPDATE ticket SET assignee_id=?, updated_at=? WHERE (ticket_id = ? AND status NOT IN (?,?,?))
```

—— **SET 子句里没有 `status`**。

---

## 根因

`RoutingService.assign()`（`RoutingService.java:203-206`）**只写 `assignee_id`，不写 `status`**：

```java
int rows = ticketMapper.update(null, new UpdateWrapper<Ticket>()
        .eq("ticket_id", ticket.getTicketId())
        .notIn("status", CANCELLED, COMPLETED, CLOSED)
        .set("assignee_id", engineerId).set("updated_at", now));
// ← 没有 .set("status", ASSIGNED)
```

**改状态的责任在调用方**。既有调用方补了，新路径漏了：

| 路径 | 调用 `assign()` 后 | 结果 |
|---|---|---|
| **手动派单** `TicketService.java:588-593` | `ticketMapper.update(...).set(Ticket::getStatus, ASSIGNED).set(updatedAt, now)` ✅ | 状态正确 |
| **HITL 放行** `TicketService.java:950-954` `confirmDispatch` | 直接 `insertFlowLog(NEW→ASSIGNED)` + 发通知，**没有 set status** ❌ | 状态停在 NEW |

`confirmDispatch` 完整实现（`TicketService.java:950-954`）：

```java
routingService.assign(ticket, draft.getEngineerId(), "首次分派");
insertFlowLog(ticketId, TicketStatus.NEW.getValue(), TicketStatus.ASSIGNED.getValue(),
        "TICKET_ASSIGN", "PLATFORM_ADMIN",
        "审批人确认派单草案 " + draftId + "，分配工程师: " + draft.getEngineerId());
notificationService.sendNotification(ticketId, "ASSIGNED", draft.getEngineerId());
// ← 漏了手动路径 L590-593 的那次 update
```

### 这是漏写，不是有意设计成「工单停 NEW」

四条都不依赖推断，是代码与文档自己写的：

**① 方法自己的 javadoc 说要改状态**（`TicketService.java:921-926`）：

```java
/**
 * 确认派单草案 —— 门禁的<b>唯一放行执行点</b>。
 *
 * <p>审批人对草案 approve 后（DispatchDraftService.decide 判定通过）由
 * DispatchDraftController 调用本方法，真正落分派：
 * 写 assignment、NEW → ASSIGNED、记流转日志、通知工程师。   ← 声称要做 NEW → ASSIGNED
 */
public void confirmDispatch(String draftId) {
```

**② 本次改动的对齐文档也这么写**（`docs/ticket-service-hitl-alignment.md:112`）：

> `approveExecutesAssignmentAndTransitionsTicket` | "凭有效 Token 唤醒原任务"——…`onApproved`
> 回调执行 `RoutingService.assign()`，**工单 NEW→ASSIGNED**

**③ 同一个 `assign()` 调用点，手动路径补了状态、HITL 路径没补**（`L588-593` vs `L950-954`），
两条路径行为不一致。

**④ 实测系统不自洽**：工程师接单被状态机拒（见「影响 1」），如果是「有意停 NEW」，
那接单这条正常业务就永远走不通。

---

## 影响

### 1. 工单卡死：工程师看得见，但接不了单 【已实测】

工程师看板**能看到**这张工单（`TicketService.java:390-394` 的「我负责的」只按 `assignee_id`
过滤，不看 `status`）：

```java
qw.and(w -> w.eq("assignee_id", mineOrPool)                     // 我负责的 ← 不过滤 status
        .or(o -> o.isNull("assignee_id").eq("status", NEW)));   // 或 无主待领取
```

以 `U_ENG02` 身份查工程师看板，9 条工单里它**排第一条**：

```
TK202610210001 | status= NEW | assignee= U_ENG02
```

但工程师接下来要做的「接单」会被状态机拒：

| 工单 | 当前状态 | `POST /api/v1/tickets/{id}/claim` |
|---|---|---|
| **`TK202610210001`**（HITL 放行后） | `NEW` | **HTTP 409** |
| `TK202609300014`（正常 `ASSIGNED` 单，对照组） | `ASSIGNED` | **HTTP 200「接单成功」** |

报错原文：

```json
{"code":40910,"msg":"不允许从「NEW」转到「IN_PROGRESS」，允许的目标状态：ASSIGNED、NEW、CANCELLED、CLOSED"}
```

校验在 `TicketService.java:648-653`：接单只允许 `ASSIGNED → IN_PROGRESS`。

**所以准确的影响是：工单卡死在「已派单但接不了」——没有任何正常路径能把它推进下去。**
（比"看不见"更糟：看不见至少有人会去查。）

另外工程师看板上它显示为 `NEW`（=「已提交待路由」），但实际已派给本人，**界面标签也是误导的**。

### 2. 流转日志与事实不符

`ticket_transition` 记了 `NEW → ASSIGNED`，工单行却是 `NEW`。
任何按流转日志做的统计 / 审计（SLA 归因、报表、复盘）都会读到假数据。

### 3. 乐观锁失效

`version` 停在 `0`，没随状态变更递增。

### 4. 可能重复派单

工单仍是 `NEW`，若再产生一份草案并放行，
`confirmDispatch` 的 `if (ticket.getStatus() != NEW) throw` 守卫**拦不住**（状态确实是 NEW）。
而 `uk_dispatch_draft_pending` 只约束 `PENDING` 态，草案变 `APPROVED` 后不拦新草案。

---

## 建议修法

在 `confirmDispatch` 里补上手动路径那次 update（`TicketService.java:950` 之后）：

```java
routingService.assign(ticket, draft.getEngineerId(), "首次分派");

// 与手动派单路径（L590-593）保持一致：assign() 只写 assignee_id，状态由调用方落
ticketMapper.update(null, new LambdaUpdateWrapper<Ticket>()
        .eq(Ticket::getTicketId, ticketId)
        .set(Ticket::getStatus, TicketStatus.ASSIGNED)
        .set(Ticket::getUpdatedAt, LocalDateTime.now(java.time.ZoneOffset.UTC)));

insertFlowLog(...);
```

另外建议补一个**断言式单测**钉住这条不变量。

**为什么 131 个测试全绿却漏掉了它**：`HitlDispatchApprovalTest.approveExecutesAssignmentAndTransitionsTicket`
是给 `DispatchDraftService.decide` 传一个**回调 lambda**（`callbackFired[0] = true`）来验「回调被触发了」，
**从未走到真实的 `TicketService.confirmDispatch`**。该测试类里所有 `getStatus()` 断言的都是
**DispatchDraft 的状态**（PENDING / APPROVED / REJECTED），**没有一处断言 `Ticket.status`**。

所以建议补的断言是端到端的那种：approve 之后断言真实 `Ticket.status == ASSIGNED`，
**并且换工程师身份调一次 `/claim` 断言返回 200**（而不是只断言回调被调用）。
按「影响 1」的实测，第二个断言正是当前失败的用例——修好后它会变成回归防线。

---

## 附：复现所需环境

1. `docker compose -f it-ticket-cloud/docker-compose.yml up -d nacos redis`
2. 远程 MySQL（`it_ticket_system`）需有 `dispatch_draft` 表（`V2_5` 迁移）
3. 编译：`javac -parameters`（**必须带 `-parameters`**，否则 Spring MVC 报
   `Name for argument ... not specified`）
4. 起 `user-service:8101` → `ticket-service:8201`（`RoutingService` 依赖
   `userClient.engineers()`，user-service 不可达时路由直接返回 null，产不出草案）
5. 建单走链路（**注意 body 用 snake_case**，`CreateTicketRequest` / `AcceptRequest`
   都有 `@JsonNaming(SnakeCaseStrategy)`）：

```bash
printf '%s' '{"nature":"INCIDENT","category_id":"C_NET","title":"...","description":"...",
"impact_description":"...","urgency_description":"..."}' > tk.json

curl -X POST http://127.0.0.1:8201/api/v1/tickets \
  -H 'Content-Type: application/json' -H 'X-User-Id: U_EMP01' -H 'X-User-Role: EMPLOYEE' \
  -H 'Idempotency-Key: k1' --data-binary @tk.json
# → 201  status=NEW  assignee=null

# 草案、认领、放行
D=$(curl -s -H 'X-User-Id: U_ADM01' -H 'X-User-Role: PLATFORM_ADMIN' \
      http://127.0.0.1:8201/api/v1/dispatch-drafts | jq -r '.data.list[0].draftId')
curl -X POST -H 'X-User-Id: U_ADM01' -H 'X-User-Role: PLATFORM_ADMIN' \
      "http://127.0.0.1:8201/api/v1/dispatch-drafts/$D/claim"
curl -X POST -H 'X-User-Id: U_ADM01' -H 'X-User-Role: PLATFORM_ADMIN' \
      -H 'Content-Type: application/json' \
      -d '{"approve":true,"reason":"放行"}' \
      "http://127.0.0.1:8201/api/v1/dispatch-drafts/$D/decide"
# → 200，assignment 落库，但工单 status 仍是 NEW
```

6. **关键断言**——换工程师身份去接单，应当被拒（这就是复现证据）：

```bash
curl -X POST -H 'X-User-Id: U_ENG02' -H 'X-User-Role: ENGINEER' \
     -H 'Content-Type: application/json' \
     -d '{"impact_scope":"SINGLE","urgency_level":"MEDIUM"}' \
     "http://127.0.0.1:8201/api/v1/tickets/<新工单号>/claim"
# → 409  {"code":40910,"msg":"不允许从「NEW」转到「IN_PROGRESS」…"}

# 对照：拿一张真正的 ASSIGNED 工单，同样调用 → 200「接单成功」
```

---

**共享库里留有本次联调的测试单据**：`TK202610210001`（标题含「【HITL联调测试】请忽略」），
当前正处在上面那个不一致状态，可作为活证据查看，确认后可清理。

另：做「影响 1」的对照实验时，我以 `U_ENG01` 身份**真的接了一张正常的 `ASSIGNED` 种子工单**
`TK202609300014`（现为 `IN_PROGRESS`，流转日志多了一条 `TICKET_ACCEPT by U_ENG01`）。
属测试操作留下的痕迹，状态自洽，**不是产品缺陷**；需要的话可以还原。