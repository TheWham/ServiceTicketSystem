# 一期契约索引

九份契约均以 `docs/IT服务工单系统PRD-v2.md` 为业务基线。实现或评审时，按下表选择唯一权威来源；不要在其他 spec 中复制被引用内容。

| 契约 | 文件 | 唯一负责 | 不负责 |
|---|---|---|---|
| DM | `01-data-model-strong-types.md` | Java 值对象、枚举、实体、关系、字段约束、索引、快照、事务投影 | 合法状态迁移、HTTP JSON、重试和降级 |
| AI | `02-ai-api-json-schema.md` | AI/RAG DTO、HTTP 路径、JSON Schema、引用、拒答、反馈、流式协议 | 业务实体持久化、状态流转、故障重试 |
| SM | `03-business-state-machine.md` | 咨询/工单/知识状态、事件、角色守卫、迁移矩阵和业务副作用 | 字段定义、JSON 格式、超时重试实现 |
| RD | `04-resilience-degradation.md` | 幂等、并发、超时、重试、熔断、依赖降级、补偿、死信、监控和灾备 | 正常请求字段、合法迁移矩阵、AI 输出结构 |
| HTTP | `05-http-api-openapi.yaml` | 非 AI HTTP 路径、请求/响应与错误包络 | AI JSON、实体持久化、状态合法性 |
| SQL | `06-mysql-ddl-and-migrations.md` | MySQL 版本迁移、辅助持久化表、旧数据转换边界 | Java 类型、业务动作和 Redis 投递 |
| EV | `07-domain-events-outbox-redis.md` | 事件 envelope、生产消费、Outbox 投递、Redis Streams/缓存/序列 | 主业务事实和合法状态迁移 |
| AX | `08-authz-sla-external-adapters.md` | 可执行权限、SLA 计算和外部适配器 | 实体字段、状态枚举和 AI Schema |
| TR | `09-prd-spec-test-traceability.md` | PRD F/AC 到 spec/API/事件/表/测试的追踪 | 新业务规则和实现字段 |

## 引用规则

- `DM-*` 是字段、枚举和持久化对象的唯一来源。
- `AI-*` 只引用 `DM-*` 的类型名称，不重新定义实体字段；AI 不得写工单。
- `SM-*` 只引用 `DM-*` 的状态和记录类型，不重复字段表；未列出的状态组合一律非法。
- `RD-*` 只描述异常路径和恢复动作；正常成功路径分别由 `DM-*`、`AI-*`、`SM-*` 定义。
- PRD 中未定义的一期角色、状态、终态恢复窗口或知识可见范围不得通过实现“顺便增加”。
- `HTTP/SQL/EV/AX/TR` 负责把前四份领域契约落实为可开发边界，不得覆盖 `DM/AI/SM/RD` 的权威定义。
- 领域事实事件 `event_type` 只使用 `SCREAMING_SNAKE_CASE`；状态迁移动作 `eventCode` 只使用 `DOMAIN_ACTION`，两类代码不得混用。

## 评审顺序

1. 先检查 DM 的类型和持久化约束。
2. 再检查 SM 的动作是否能由这些类型表达。
3. AI 接口只允许产生 AI 会话输出、引用、反馈和转人工请求。
4. 最后用 RD 验证依赖失败、重复请求、并发冲突和灾备时主链路仍满足 PRD。
