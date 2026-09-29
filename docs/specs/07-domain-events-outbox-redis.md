# 领域事件、Outbox 与 Redis 契约

| 项目 | 约束 |
|---|---|
| 规范编号 | EV |
| 事实源 | MySQL `OutboxEvent`；Redis 不保存业务最终事实 |
| 事件语义 | 事件码引用 `SM-EVENT-001` 与 PRD 21.4 |
| 故障语义 | `RD-002`、`RD-008`、`RD-014` |

本规范中的 `event_type` 是已发生业务事实，统一使用 `SCREAMING_SNAKE_CASE`；`ticket_transition.event_code` 是触发迁移的 `DOMAIN_ACTION` 动作码。即使一次动作产生同名近似事实，两者仍按字段和语义严格区分。

## EV-001 Envelope

Outbox payload 必须使用统一 envelope；业务字段仍以 DM-004 为准，禁止放聊天原文、撤回原文、令牌或附件内容。

```json
{
  "event_id": "EV01...",
  "event_type": "TICKET_STATUS_CHANGED",
  "event_version": 1,
  "aggregate_type": "TICKET",
  "aggregate_id": "TK...",
  "occurred_at": "2026-09-28T10:00:00Z",
  "actor_type": "USER|SYSTEM",
  "actor_id": "...",
  "request_id": "req_...",
  "trace_id": "trace_...",
  "aggregate_version": 7,
  "payload": {}
}
```

`event_id` 全局唯一；同一聚合按 `aggregate_version` 单调递增。消费者按 `event_id` 幂等，不能用 Redis offset 作为业务去重依据。

## EV-002 Outbox 写入与发布

状态迁移、主对象投影、不可变历史、SLA 投影和 Outbox 行在同一 MySQL 事务内提交。提交前不得写 Redis或调用外部服务。publisher 扫描 `status=PENDING AND next_attempt_at<=now`，用行级租约/版本条件抢占，再写 Redis Streams。

生命周期：`PENDING → PUBLISHED`；异常为 `FAILED` 并递增 attempts；超过上限转 `DEAD_LETTER`。`published_at` 只在 Redis 接收成功后写入。重复扫描不得产生新的 event_id。

## EV-003 Redis Streams/Consumer Group

默认使用 Redis Streams + Consumer Group：

| Stream | Group | 用途 |
|---|---|---|
| `its:prod:stream:notification` | `notification-worker` | 站内/邮件 |
| `its:prod:stream:index` | `index-worker` | 搜索/RAG 索引刷新 |
| `its:prod:stream:identity` | `identity-worker` | HR/组织同步 |
| `its:prod:stream:compensation` | `compensation-worker` | Outbox/失败补偿 |

entry 至少包含 event_id、event_type、event_version、aggregate_id、published_at 和 envelope；单条 entry 最大 256 KB，超限只传引用 ID，消费者回源 MySQL。容量、保留期、并发和 pending 租约使用 EV-009 默认值，变更必须配置化并审计。

消费顺序：读取 → 校验 envelope → 查询 MySQL 幂等/事实 → 执行副作用 → 记录结果 → XACK。副作用成功前不得确认；Pending Entry 由 claim 任务接管。重复消费返回已处理，不重复通知、索引或审计。

## EV-004 重试与死信

瞬时依赖错误按 RD-003 有界退避；业务不可重试错误立即记录；安全/权限错误立即拒绝并告警。达到上限后：

1. entry 复制到同类 `:dlq` stream，并写 MySQL 死信记录（事件 ID、最后错误、次数、对象、时间）。
2. 原 entry XACK，避免无限 Pending；Outbox 保持 PUBLISHED，delivery 记录进入 DEAD_LETTER。
3. 管理员重放复用原 event_id，重新校验当前权限和版本；失败回原死信。

## EV-005 Key、序列和缓存

格式为 `its:{env}:{purpose}:{object-type}:{object-id}`，如 `its:prod:cache:route:CAT-1`、`its:prod:seq:ticket`。禁止无环境前缀和无限 TTL。

| 用途 | 允许内容 | 规则 |
|---|---|---|
| 排队 | Outbox envelope 或受控引用 | XACK 前保留，失败进入 DLQ |
| 序列 | 号段/尾号 | 允许跳号；MySQL 唯一键兜底 |
| 缓存 | 可重建路由、配置、列表投影 | cache-aside，提交后失效 |

不得缓存聊天、撤回原文、令牌、权限事实、SLA 累计值、知识发布事实或敏感附件。TTL、最大长度、序列号段大小和缓存 TTL 使用 EV-009 默认值；变更必须配置化并审计，禁止缺省 TTL。

## EV-006 Redis 故障与恢复

Redis 不可用时 publisher 保留 Outbox PENDING/FAILED，由 MySQL 扫描补发；消费者恢复后对账 Streams Pending 与 MySQL 状态。序列回退 MySQL 号段/唯一键重试，查询回源 MySQL。Redis 清空、重启或主从切换不得改变状态、权限、审计、SLA、幂等最终结果或知识事实。

## EV-007 事件版本与可观测性

事件版本只递增不复用；新增可选字段可留在主版本，删除/改语义必须升 major 并兼容上一个 major。未知版本进入兼容队列并告警。发布、消费、重试、claim、DLQ 和重放均记录 event_id/request_id/trace_id、stream、group、延迟、结果和错误分类；不得记录正文、令牌或附件内容。


## EV-008 事件生产者、消费者与 Payload 约束

所有 payload 采用 object，禁止空对象；未列出的字段不得写入。字段名引用 DM/SM，不在事件中复制实体定义。

| 事件 | 生产者 | 消费者 | 顺序键 | 必需 payload |
|---|---|---|---|---|
| TICKET_CREATED | TicketService | Assignment/SLA/Notification | ticket_id | ticket_id, status, source_session_id |
| TICKET_ASSIGNED | AssignmentService | Notification/SLA | ticket_id | ticket_id, assignment_id, engineer_id |
| TICKET_STATUS_CHANGED | StateMachine | SLA/Notification/Audit | ticket_id | ticket_id, from_status, to_status, event_code |
| TICKET_TRANSFERRED | AssignmentService | Notification/Audit | ticket_id | ticket_id, old_engineer_id, new_engineer_id |
| TICKET_REOPENED | StateMachine | Assignment/SLA/Notification | ticket_id | ticket_id, reopen_reason |
| TICKET_RESPONDED | TicketService | SLA/Notification | ticket_id | ticket_id, message_id |
| TICKET_PRIORITY_CHANGED | TicketService | SLA/Notification/Audit | ticket_id | ticket_id, old_priority, new_priority, reason |
| CONSULTATION_TRANSFERRED | ConsultationService | Assignment/Notification | session_id | session_id, category_id, assignment_id |
| CONSULTATION_RESPONDED | ConsultationService | SLA/Notification | session_id | session_id, message_id |
| CONSULTATION_RESOLVED | ConsultationService | CaseCandidate/Notification | session_id | session_id, resolution_type |
| CONSULTATION_REOPENED | ConsultationService | Assignment/Notification | session_id | session_id, reopen_reason |
| CONSULTATION_CONVERTED | ConsultationService | TicketService/Notification | session_id | session_id, ticket_id |
| SLA_NEAR_BREACH | SlaScheduler | Notification | aggregate_id | sla_id, aggregate_id, threshold_percent |
| SLA_BREACHED | SlaScheduler | ExceptionQueue/Notification | aggregate_id | sla_id, aggregate_id, breached_at |
| KNOWLEDGE_PUBLISHED | KnowledgeService | Index/Notification | article_id | article_id, version_id |
| KNOWLEDGE_SUBMITTED | KnowledgeService | ReviewQueue/Notification | article_id | article_id, version_id, author_id |
| KNOWLEDGE_OFFLINE | KnowledgeService | Index/Notification | article_id | article_id, version_id |
| KNOWLEDGE_INDEX_REFRESH_REQUESTED | IndexService | IndexWorker | version_id | article_id, version_id, index_version |
| NOTIFICATION_REQUESTED | Domain services | NotificationWorker | event_id | receiver_id, channel, dedup_key |

生产者在业务事务中写 Outbox；消费者成功副作用后写 outbox_delivery 并 ACK。聚合顺序只要求同一 aggregate_id 的 event_version 单调，跨聚合不保证全局顺序。

## EV-009 Stream 运维常量

默认值（可由运维变更但必须配置化、审计化）：

| 参数 | 默认值 |
|---|---:|
| Stream MAXLEN | 100000 |
| Stream 保留期 | 7 日 |
| Consumer claim idle | 60 秒 |
| 单事件最大重试 | 5 次 |
| 重试退避 | 1s/5s/30s/5m/30m |
| DLQ 保留期 | 30 日 |
| publisher 扫描间隔 | 2 秒 |
| delivery 记录保留期 | 90 日 |
| cache key 默认 TTL | 300 秒 |

Key 统一为 its:{env}:{purpose}:{object-type}:{object-id}；Stream 示例为 its:prod:stream:notification，DLQ 为 its:prod:stream:notification:dlq。配置缺失或 TTL=0 时启动失败。



## EV-010 Payload JSON Schema

事件注册表必须将 event_type 映射到 Draft 2020-12 payload schema。所有 payload 禁止未知字段；生产者写 Outbox 前和消费者执行副作用前都必须校验。

~~~json
{
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "$id":"https://example.invalid/events/payloads-1.0.json",
  "$defs":{
    "id":{"type":"string","minLength":1,"maxLength":64},
    "reason":{"type":"string","minLength":1,"maxLength":2000},
    "ticketCreated":{"type":"object","additionalProperties":false,"required":["ticket_id","status"],"properties":{"ticket_id":{"$ref":"#/$defs/id"},"status":{"const":"NEW"},"source_session_id":{"type":["string","null"],"maxLength":32}}},
    "ticketAssigned":{"type":"object","additionalProperties":false,"required":["ticket_id","assignment_id","engineer_id"],"properties":{"ticket_id":{"$ref":"#/$defs/id"},"assignment_id":{"$ref":"#/$defs/id"},"engineer_id":{"$ref":"#/$defs/id"}}},
    "ticketStatusChanged":{"type":"object","additionalProperties":false,"required":["ticket_id","from_status","to_status","event_code"],"properties":{"ticket_id":{"$ref":"#/$defs/id"},"from_status":{"type":["string","null"],"maxLength":32},"to_status":{"type":"string","maxLength":32},"event_code":{"type":"string","maxLength":64}}},
    "ticketTransferred":{"type":"object","additionalProperties":false,"required":["ticket_id","old_engineer_id","new_engineer_id"],"properties":{"ticket_id":{"$ref":"#/$defs/id"},"old_engineer_id":{"$ref":"#/$defs/id"},"new_engineer_id":{"$ref":"#/$defs/id"}}},
    "ticketReopened":{"type":"object","additionalProperties":false,"required":["ticket_id","reopen_reason"],"properties":{"ticket_id":{"$ref":"#/$defs/id"},"reopen_reason":{"$ref":"#/$defs/reason"}}},
    "ticketResponded":{"type":"object","additionalProperties":false,"required":["ticket_id","message_id"],"properties":{"ticket_id":{"$ref":"#/$defs/id"},"message_id":{"$ref":"#/$defs/id"}}},
    "ticketPriorityChanged":{"type":"object","additionalProperties":false,"required":["ticket_id","old_priority","new_priority","reason"],"properties":{"ticket_id":{"$ref":"#/$defs/id"},"old_priority":{"enum":["HIGH","MEDIUM","LOW"]},"new_priority":{"enum":["HIGH","MEDIUM","LOW"]},"reason":{"$ref":"#/$defs/reason"}}},
    "consultationTransferred":{"type":"object","additionalProperties":false,"required":["session_id","category_id","assignment_id"],"properties":{"session_id":{"$ref":"#/$defs/id"},"category_id":{"$ref":"#/$defs/id"},"assignment_id":{"$ref":"#/$defs/id"}}},
    "consultationResponded":{"type":"object","additionalProperties":false,"required":["session_id","message_id"],"properties":{"session_id":{"$ref":"#/$defs/id"},"message_id":{"$ref":"#/$defs/id"}}},
    "consultationResolved":{"type":"object","additionalProperties":false,"required":["session_id","resolution_type"],"properties":{"session_id":{"$ref":"#/$defs/id"},"resolution_type":{"enum":["EMPLOYEE_CONFIRMED","AUTO_RESOLVED"]}}},
    "consultationReopened":{"type":"object","additionalProperties":false,"required":["session_id","reopen_reason"],"properties":{"session_id":{"$ref":"#/$defs/id"},"reopen_reason":{"$ref":"#/$defs/reason"}}},
    "consultationConverted":{"type":"object","additionalProperties":false,"required":["session_id","ticket_id"],"properties":{"session_id":{"$ref":"#/$defs/id"},"ticket_id":{"$ref":"#/$defs/id"}}},
    "slaSignal":{"type":"object","additionalProperties":false,"required":["sla_id","aggregate_id"],"properties":{"sla_id":{"$ref":"#/$defs/id"},"aggregate_id":{"$ref":"#/$defs/id"},"threshold_percent":{"type":"integer","minimum":1,"maximum":100},"breached_at":{"type":"string","format":"date-time"}}},
    "knowledgeVersion":{"type":"object","additionalProperties":false,"required":["article_id","version_id"],"properties":{"article_id":{"$ref":"#/$defs/id"},"version_id":{"$ref":"#/$defs/id"},"author_id":{"$ref":"#/$defs/id"},"index_version":{"type":"string","minLength":1,"maxLength":128}}},
    "notificationRequested":{"type":"object","additionalProperties":false,"required":["receiver_id","channel","dedup_key"],"properties":{"receiver_id":{"$ref":"#/$defs/id"},"channel":{"enum":["IN_APP","EMAIL"]},"dedup_key":{"type":"string","minLength":1,"maxLength":255}}}
  }
}
~~~

注册映射：TICKET_CREATED→ticketCreated；TICKET_ASSIGNED→ticketAssigned；TICKET_STATUS_CHANGED→ticketStatusChanged；TICKET_TRANSFERRED→ticketTransferred；TICKET_REOPENED→ticketReopened；TICKET_RESPONDED→ticketResponded；TICKET_PRIORITY_CHANGED→ticketPriorityChanged；CONSULTATION_TRANSFERRED→consultationTransferred；CONSULTATION_RESPONDED→consultationResponded；CONSULTATION_RESOLVED→consultationResolved；CONSULTATION_REOPENED→consultationReopened；CONSULTATION_CONVERTED→consultationConverted；SLA_NEAR_BREACH/SLA_BREACHED→slaSignal；KNOWLEDGE_SUBMITTED/KNOWLEDGE_PUBLISHED/KNOWLEDGE_OFFLINE/KNOWLEDGE_INDEX_REFRESH_REQUESTED→knowledgeVersion；NOTIFICATION_REQUESTED→notificationRequested。
