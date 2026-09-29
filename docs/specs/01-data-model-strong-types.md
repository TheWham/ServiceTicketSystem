# 数据模型与强类型实体契约

| 项目 | 约束 |
|---|---|
| 规范编号 | DM |
| 技术基线 | Java 17、Spring Boot 3.x、MyBatis/MyBatis-Plus、MySQL 8.x；Redis 仅作队列、序列和缓存 |
| 权威范围 | Java 领域类型、MyBatis 映射、MySQL 表/约束/事务和版本快照 |
| 上游需求 | [IT服务工单系统PRD-Ultimate.md](../IT服务工单系统PRD-Ultimate.md) 2.2 |

本规范是字段、枚举、关系、索引和持久化约束的唯一来源。业务迁移规则见 `SM-*`；AI HTTP DTO 和 JSON Schema 见 `AI-*`；重试、超时和降级见 `RD-*`。其他规范不得复制本规范的字段表或实体定义。

## DM-001 Java 基础约定

- 主键使用不可变 `String` 业务 ID，生成规则由应用服务统一实现。
- 时间统一使用 `Instant` 持久化为 MySQL `DATETIME(6)`，展示层按用户时区转换。
- 业务日期使用 `LocalDate`；服务日历时间使用 `LocalTime`；持续时长使用 `Duration` 或 `long` 秒数。
- 金额、计数和权重禁止使用浮点类型；权重使用 `BigDecimal(8,4)`。
- 枚举使用显式字符串值，MyBatis/MyBatis-Plus 显式映射为 `VARCHAR`，禁止按序号持久化。
- 实体使用 `Long version` 做乐观锁；MyBatis 更新必须将 `version` 放入 `WHERE` 条件并递增，业务更新不得覆盖审计历史。
- 所有实体包含 `createdAt: Instant`、`updatedAt: Instant`；可归档实体包含 `archivedAt: Instant?`。
- JSON 字段使用 MySQL `JSON`，Java 映射为不可变 DTO 或 `JsonNode`；不得将可查询核心字段藏在 JSON 中。

### DM-001.1 Java 到 MySQL 映射

| Java 类型/约束 | MySQL 8 类型 | 规则 |
|---|---|---|
| `String` ID，最大 64 | `VARCHAR(64) CHARACTER SET utf8mb4` | 主键或普通索引按长度配置；禁止无界 `TEXT` 作为 ID。 |
| 短文本，最大 255 | `VARCHAR(255)` | 标题、名称、错误码、枚举字符串。 |
| 长文本 | `TEXT` 或 `MEDIUMTEXT` | 描述、消息正文按最大业务长度选择；必须在 Java 校验长度。 |
| 显式枚举 | `VARCHAR(32)` | 保存枚举字符串，不使用 MySQL `ENUM`，便于向后兼容。 |
| `Instant` | `DATETIME(6)` | 应用统一按 UTC 写入；数据库连接时区固定。 |
| `LocalDate` | `DATE` | 不含时区。 |
| `LocalTime` | `TIME(6)` | 服务日历使用。 |
| `boolean` | `TINYINT(1)` | 只允许 0/1。 |
| `int/long` | `INT/BIGINT` | 计数和秒数不得溢出；权重不用浮点。 |
| `BigDecimal(8,4)` | `DECIMAL(8,4)` | 置信度和权重需在应用层校验范围。 |
| JSON DTO | `JSON` | 使用 Jackson 序列化；禁止依赖字段顺序。 |

MyBatis-Plus Entity/Mapper 必须显式声明字段长度、空值、唯一键和索引意图；迁移脚本必须与本表及 DM-004 的索引约束一致。禁止通过 ORM 自动建表。

## DM-002 枚举目录

以下枚举名称是状态机和接口规范引用的唯一名称。

```java
public enum TicketNature { INCIDENT, SERVICE_REQUEST }
public enum TicketStatus {
    NEW, ASSIGNED, IN_PROGRESS, PENDING_SUPPLEMENT, PENDING_EXTERNAL,
    PENDING_ACCEPTANCE, COMPLETED, CANCELLED, CLOSED
}
public enum ConsultationStatus {
    AI_ACTIVE, WAITING_ENGINEER, HUMAN_ACTIVE, PENDING_CONFIRMATION,
    RESOLVED, CONVERTED_TO_TICKET, CLOSED
}
public enum ConsultationSource { AI, HUMAN_DIRECT, TICKET_FOLLOW_UP }
public enum ConsultationResolutionType { EMPLOYEE_CONFIRMED, AUTO_RESOLVED }
public enum KnowledgeStatus { DRAFT, PENDING_REVIEW, PUBLISHED, OFFLINE }
public enum CaseStatus { PENDING_MASKING, PENDING_REVIEW, REJECTED, ACCEPTED, DISCARDED }
public enum CaseSourceType { CONSULTATION, TICKET }
public enum MaskingStatus { NOT_STARTED, IN_PROGRESS, PASSED, FAILED }
public enum KnowledgeRiskLevel { NORMAL, HIGH }
public enum KnowledgeClusterStatus { OPEN, MERGED, DISMISSED }
public enum Priority { HIGH, MEDIUM, LOW }
public enum FieldType { TEXT, SINGLE_SELECT, MULTI_SELECT, DATE, ATTACHMENT }
public enum EngineerPresence { AVAILABLE, BUSY, AWAY, OFFLINE }
public enum RoleCode { EMPLOYEE, ENGINEER, PLATFORM_ADMIN, KNOWLEDGE_ADMIN }
public enum AssignmentEndReason { RESPONDED, TIMEOUT, TRANSFERRED, CANCELLED, COMPLETED }
public enum SlaType { CONSULTATION_RESPONSE, TICKET_RESPONSE, TICKET_COMPLETION }
public enum SlaStatus { RUNNING, PAUSED, MET, BREACHED, CANCELLED }
public enum MessageSenderType { EMPLOYEE, ENGINEER, AI, SYSTEM }
public enum AttachmentScanStatus { PENDING, PASSED, REJECTED, ERROR }
public enum NotificationStatus { PENDING, SENT, FAILED, DEAD_LETTER }
public enum NotificationChannel { IN_APP, EMAIL }
public enum AssignmentBizType { CONSULTATION, TICKET }
public enum SlaPauseReason { PENDING_SUPPLEMENT, PENDING_EXTERNAL }
public enum ExternalDependencyType { SPARE_PART, VENDOR, CARRIER, OTHER }
public enum AttachmentBizType { CONSULTATION, TICKET, MESSAGE, SUPPLEMENT, KNOWLEDGE }
public enum OutboxStatus { PENDING, PUBLISHED, FAILED, DEAD_LETTER }
public enum AiFeedbackType { HELPFUL, NOT_HELPFUL, INCORRECT }
public enum AcceptanceResult { ACCEPTED, REJECTED, AUTO_ACCEPTED }
public enum IdempotencyStatus { IN_PROGRESS, SUCCEEDED, FAILED }
```

优先级矩阵的业务含义和状态迁移不在本规范定义，分别引用 `SM-TICKET-002` 和 `SM-TICKET-001`。

## DM-003 标识符和值对象

| 类型 | Java 类型 | 约束 |
|---|---|---|
| `UserId` | `record UserId(String value)` | 非空，长度 1-64。 |
| `TeamId` | `record TeamId(String value)` | 非空，长度 1-64。 |
| `CategoryId` | `record CategoryId(String value)` | 非空，末级分类可路由。 |
| `TicketId` | `record TicketId(String value)` | `TK` 前缀，最大 32 字符，唯一。 |
| `SessionId` | `record SessionId(String value)` | `CS` 前缀，最大 32 字符，唯一。 |
| `MessageId` | `record MessageId(String value)` | 唯一，禁止复用。 |
| `IdempotencyKey` | `record IdempotencyKey(String value)` | 1-128 字符；绑定主体、操作和请求摘要。 |
| `WorkDuration` | `record WorkDuration(long seconds)` | `seconds >= 0`。 |
| `SlaTarget` | `record SlaTarget(long workSeconds)` | `workSeconds > 0`。 |

## DM-004 核心持久化实体

以下表名、字段类型、关系和唯一约束为实现基线。外键可以按部署方案使用逻辑外键，但应用必须实现同等一致性校验。

代码块中的类是领域模型示意，不表示 ORM 映射。实际持久化必须使用 MyBatis-Plus `@TableName`、`@TableId`、`@TableField`、`@Version` 或 XML `resultMap`；复合主键使用唯一索引和显式 `WHERE` 条件，不使用 ORM 复合主键注解。所有写入 SQL 必须显式列出列名，禁止 `UPDATE ...` 覆盖审计字段或未知字段。

### 用户与组织

```java
class User {
   String userId; String employeeNo; String name;
  String departmentId; String status; String identitySource;
  Instant lastIdentitySyncAt;  Long version;
}
class UserRole {
   String userId; RoleCode roleCode; String grantedBy; Instant grantedAt; Instant revokedAt;
}
class SupportTeam {  String teamId; String name; String status;  Long version; }
class TeamMember {
   String teamId; String engineerId; Instant joinedAt; Instant leftAt; String status;
}
class EngineerRuntimeState {
   String engineerId; EngineerPresence presence; Instant lastActivityAt;
  Instant lastAssignedAt; long version;
}
class EngineerCategoryCapability {
   String engineerId; String categoryId; String teamId; boolean enabled;
  Instant effectiveAt; Instant expiredAt;
}
```

MySQL：`user(user_id PK, employee_no UNIQUE, department_id INDEX, status)`；`user_role(user_id, role_code PK, revoked_at INDEX)`；`support_team(team_id PK)`；`team_member(team_id, engineer_id PK, status INDEX)`；`engineer_runtime_state(engineer_id PK, presence, last_activity_at)`；`engineer_category_capability(engineer_id, category_id, team_id, effective_at UNIQUE)`。`last_identity_sync_at`、`version`、`created_at` 和 `updated_at` 是身份同步和持久化元数据，不替代 PRD 用户业务字段。

加权负载不作为权限或状态事实持久化：分配器在同一 MySQL 一致性快照内，按当前未结束 `Assignment`、活跃咨询/工单和 PRD 默认权重实时聚合；允许建立可重建的负载投影缓存，但命中前必须校验投影版本，Redis 丢失时回源聚合。

### 分类、路由与字段快照

```java
class Category {
   String categoryId; String parentId; TicketNature ticketNature;
  String name; short level; String status; String definitionVersion; Long version;
}
class CategoryRoute {
   String categoryId; String teamId; int routeOrder; Instant effectiveAt; Instant expiredAt;
}
class FieldDefinition {
   String fieldDefinitionId; String categoryId; String fieldKey;
  FieldType fieldType; boolean required; String optionsJson; int displayOrder; boolean enabled;
}
```

`category(parent_id, level, status)` 建索引；`category_route(category_id, route_order,effective_at)` 唯一；`field_definition(category_id, field_key,definition_version)` 唯一。提交工单必须保存 `field_definition_snapshot JSON`，分类配置更新不得改变历史值。

### 咨询与消息

```java
class Consultation {
   String sessionId; String creatorId; String categoryId;
  ConsultationStatus status; String currentEngineerId; ConsultationSource source;
  ConsultationResolutionType resolvedType; String convertedTicketId;
  Instant createdAt; Instant closedAt;  Long version;
}
class ConsultationMessage {
   String messageId; String sessionId; String senderId; MessageSenderType senderType;
  String clientMessageId; String content; String citationJson;
  Instant sentAt; Instant withdrawnAt; String withdrawReason;
}
```

`consultation(creator_id, status, created_at)`、`consultation(current_engineer_id, status)` 建索引；消息按 `session_id, sent_at, message_id` 索引。消息撤回只更新撤回元数据，不删除正文。

AI 消息的 `citation_json` 兼容原引用数组，并支持 `schemaVersion=1` 元数据对象：`citations`、`interactionId`、`replyType`、`refusalReason`、`generalAnswer`。这些字段用于恢复引用、反馈关联和回答/拒答展示，不作为权限或业务状态事实；无需增加数据库列。撤回消息不得返回这些元数据。旧数组仍正常读取，不猜测旧消息的交互 ID。

### 工单、流转、消息与附件

```java
class Ticket {
   String ticketId; String creatorId; TicketNature nature; String categoryId;
  String title; String description; String impactDescription; String urgencyDescription;
  String location; String contact; String assetId; TicketStatus status; Priority priority;
  String assigneeId; String sourceSessionId; String fieldDefinitionSnapshot;
  Instant createdAt; Instant completedAt; Instant closedAt;  Long version;
}
class TicketTransition {
   String transitionId; String ticketId; TicketStatus fromStatus; TicketStatus toStatus;
  String event; String operatorId; String reason; Instant occurredAt;
}
class TicketFieldValue {
   String ticketId; String fieldDefinitionId; String fieldKey;
  String fieldDefinitionSnapshot; String fieldValue; String definitionVersion; Instant createdAt;
}
class TicketMessage {
   String messageId; String ticketId; String senderId; MessageSenderType senderType;
  String clientMessageId; String content; Instant sentAt; Instant withdrawnAt; String withdrawReason;
}
class TicketDraft {
   String draftId; String creatorId; TicketNature ticketNature; String categoryId;
  String payloadJson; Instant lastSavedAt; Instant expiresAt;  Long version;
}
class SupplementRequest {
   String requestId; String ticketId; int sequenceNo; String requestedBy;
  String content; Instant requestedAt; Instant respondedAt; boolean overdueClosed;
}
class ExternalWait {
   String waitId; String ticketId; ExternalDependencyType dependencyType; String reason;
  Instant expectedAt; Instant startedAt; Instant endedAt; String resumeNote;
}
class TicketResolution {
   String resolutionId; String ticketId; String solution; String verification;
  String submittedBy; Instant submittedAt;
}
class TicketAcceptance {
   String acceptanceId; String ticketId; AcceptanceResult result;
  String reason; String operatorId; Instant occurredAt;
  Integer ratingScore; String ratingComment; Instant ratedAt;
}
class Attachment {
   String attachmentId; AttachmentBizType bizType; String bizId; String uploaderId;
  String objectKey; String fileName; long size; String hash;
  String contentType; AttachmentScanStatus scanStatus; Instant uploadedAt; Instant withdrawnAt;
}
class AttachmentAccess {
   String accessId; String attachmentId; String subjectId; String requestId;
  Instant issuedAt; Instant expiresAt; Instant accessedAt; String accessResult; Instant revokedAt;
}
```

约束：`ticket(title, category_id, created_at)`、`ticket(creator_id, status)`、`ticket(assignee_id, status)`、`ticket(priority, status)` 建索引；`ticket_transition(ticket_id, occurred_at, transition_id)` 唯一排序；消息按业务对象与 `client_message_id` 唯一；`attachment(biz_type, biz_id, hash)` 唯一；`attachment_access(attachment_id, subject_id, expires_at)` 建索引并追加记录每次访问结果。

### 分配、SLA、通知和审计

```java
class Assignment {
   String assignmentId; AssignmentBizType bizType; String bizId; String engineerId;
  Instant assignedAt; Instant responseDeadline; Instant respondedAt; AssignmentEndReason endReason;
}
class SlaInstance {
   String slaId; String ticketId; AssignmentBizType bizType; String bizId; SlaType slaType; SlaStatus status;
  long targetWorkSeconds; long elapsedWorkSeconds; long pausedSeconds;
  Instant targetAt; Instant breachAt; Instant metAt; String calendarId; long calendarVersion;
}
class SlaPause {  String pauseId; String slaId; SlaPauseReason reasonType; Instant startedAt; Instant endedAt; String operatorId; }
class Notification {
   String notificationId; String eventId; String receiverId;
  NotificationChannel channel; String dedupKey; NotificationStatus status;
  int attempts; String lastError; Instant sentAt;
}
class AuditLog {
   String auditId; String actorId; String action; String objectType; String objectId;
  String beforeValue; String afterValue; String reason; String requestId; Instant occurredAt;
}
```

`assignment(biz_type, biz_id, engineer_id, assigned_at)`、`sla_instance(biz_type, biz_id, sla_type)` 唯一；`sla_pause(sla_id, started_at)`；`notification(dedup_key)` 唯一；`audit_log(object_type, object_id, occurred_at)` 和 `audit_log(actor_id, occurred_at)` 建索引。审计表只允许追加。

字段语义对齐 PRD20.1：`SlaInstance.ticketId` 仅工单实例非空并等于 `bizId`，咨询实例为空；`bizType/bizId` 保持共享表隔离。`KnowledgeVersion.content`、`CaseCandidate.structuredContent`、`AiInteraction.retrievedVersions`、`AuditLog.beforeValue/afterValue` 和工单字段快照/值采用 JSON 持久化；示意代码的 String 只是传输表示，不能把业务列改名为 `_json`。`AiInteraction.latency` 单位毫秒。技术元数据不替代 PRD 字段。

`ticket_draft(creator_id)` 唯一保证每位员工只有一个活动草稿；`supplement_request(ticket_id, sequence_no)` 唯一；`external_wait(ticket_id, started_at)`；`ticket_resolution(ticket_id, submitted_at)`；`ticket_acceptance(ticket_id, occurred_at)`；`idempotency_record(owner_id, operation, idempotency_key)` 唯一；`outbox_event(status, next_attempt_at)` 建索引。草稿可更新，补充、等待、解决方案和验收记录只追加。

### 案例、知识和 AI 持久化对象

```java
class CaseCandidate {
   String caseId; CaseSourceType sourceType; String sourceId; String structuredContent;
  MaskingStatus maskingStatus; boolean reusableFlag; CaseStatus status; Instant createdAt;
}
class KnowledgeArticle {
   String articleId; KnowledgeStatus status; String currentVersionId; String categoryId;
  KnowledgeRiskLevel riskLevel;  Long version;
}
class KnowledgeVersion {
   String versionId; String articleId; int versionNo; String content;
  String authorId; String reviewerId; Instant publishedAt; String changeNote;
  String platformReviewerId; Instant platformReviewedAt; String platformReviewDecision;
}
class KnowledgeCluster {  String clusterId; String similarityBasis; KnowledgeClusterStatus status; }
class AiInteraction {
   String interactionId; String sessionId; String modelVersion; String retrievedVersions;
  BigDecimal confidence; AiFeedbackType feedback; long latency; Instant occurredAt;
}
class AiProviderConfig {
   String providerConfigId; String providerId; long configVersion; String status;
  String baseUrl; String apiKeySecretRef; String model; String embeddingModel;
  String protocolVersion; String pathJson; String capabilityJson; String timeoutJson;
  String generationJson; String createdBy; Instant validatedAt; Instant activatedAt;
  Instant retiredAt; Long rollbackFromVersion; String auditRequestId;
}
class RagIndexPointer {
   String pointerId; String articleId; String knowledgeVersionId; String indexVersion;
  String status; long version; Instant activatedAt; Instant offlinedAt;
}
class IdempotencyRecord {
   String recordId; String ownerId; String operation; String idempotencyKey;
  String requestHash; IdempotencyStatus status; String resultJson;
  Instant createdAt; Instant expiresAt;
}
class OutboxEvent {
   String eventId; String eventType; String aggregateType; String aggregateId;
  String payloadJson; OutboxStatus status; int attempts; Instant nextAttemptAt; Instant publishedAt;
}
```

`TicketTransition.event` 保存 `DOMAIN_ACTION` 业务动作码（例如 `TICKET_ACCEPT`）；`OutboxEvent.eventType` 保存 `SCREAMING_SNAKE_CASE` 领域事实事件类型（例如 `TICKET_RESPONDED`）。禁止把动作码写入 `event_type`，也禁止用领域事实事件类型替代流转动作码。

知识版本使用 `(article_id, version_no)` 唯一；`PUBLISHED` 只能有一个当前版本；RAG 索引版本必须可追溯到 `knowledge_version.version_id`。`AiInteraction` 只保存审计、反馈和引用元数据，不作为训练语料自动发布。`ai_provider_config(provider_id, config_version)` 唯一且同一 provider 只允许一个 ACTIVE 版本；`rag_index_pointer(knowledge_version_id)` 唯一，且按 `article_id` 通过 active 指针唯一索引保证同一文章只有一个 ACTIVE，切换使用 version 乐观锁。Secret 只保存引用。

`ai_interaction.feedback` 中的 HELPFUL、NOT_HELPFUL、INCORRECT 均可作为知识优化待处理标记；HELPFUL 只代表员工满意，不代表答案已审核。通用回答可没有检索版本；只有引用已通过校验的版本才可展示为知识来源。当前反馈标记持久化不等于已经完成知识域脱敏消费、案例生成或审核发布。

## DM-005 数据库事务与一致性

- 创建工单、首条 `TicketTransition`、首个 `SlaInstance` 和幂等记录必须在同一事务中完成。
- 保存草稿不创建工单；正式提交时必须从草稿生成一次性快照，草稿状态与幂等记录不得覆盖已创建工单。
- 状态变化与业务对象的 `version` 必须乐观锁校验；版本冲突返回 `ASSIGNMENT_CHANGED` 或 `ILLEGAL_STATE_TRANSITION`，由 `RD-*` 定义重试策略。
- 消息、附件和知识版本是追加写；撤回、下线和回滚只产生新事件或元数据。
- 补充、外部等待、解决方案、验收、审计和状态流转必须保留不可变历史；业务对象只保存当前投影。
- 外部对象存储、邮件、模型和索引不参与主业务事务；通过 `OutboxEvent` 和 `RD-*` 补偿保持最终一致。

## DM-006 MySQL、MyBatis 与 Redis 边界

- MySQL 是用户、工单、咨询、状态、SLA、审计、知识、幂等和 Outbox 的唯一事实源；任何业务读取在一致性要求下必须回源 MySQL。
- MyBatis/MyBatis-Plus 是唯一业务数据访问层；事务边界使用 Spring `@Transactional` 管理 MySQL 连接，禁止服务直接写 Redis 代替数据库提交。
- Redis 仅允许三类用途：
  1. **排队**：承载由 MySQL `OutboxEvent` 发布的异步任务（通知、索引、HR 同步、补偿）；消费成功前不能删除消息，消息体必须含 `eventId`，消费幂等仍由 MySQL 记录保证。
  2. **序列**：使用 `INCR` 分配短期序列或业务号尾号；最终唯一性由 MySQL 唯一索引兜底，Redis 丢失后允许出现间隙但不得出现重复。
  3. **缓存**：只缓存可重建的查询投影、配置快照和路由候选；写 MySQL 成功后按事件失效或更新，缓存 miss/过期/不可用必须回源 MySQL。
- Redis 不保存状态机当前状态、权限事实、审计原文、SLA 累计值、知识发布事实或幂等最终结果；Redis 清空、重启或网络隔离不得丢失业务事实。
- Redis 队列、序列和缓存的 TTL、最大长度、重试和死信策略由 `RD-*` 定义；未配置 TTL 的 Redis key 不得上线。
