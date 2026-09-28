# AI 接口与 JSON Schema 约束契约

| 项目 | 约束 |
|---|---|
| 规范编号 | AI |
| 技术基线 | Java 17、Spring Boot 3.x、OpenAPI 3.1、JSON Schema Draft 2020-12 |
| 权威范围 | AI/RAG HTTP 接口、AI DTO、请求响应 JSON Schema、引用、拒答、反馈和流式协议 |
| 业务基线 | [IT服务工单系统PRD-v2.md](../IT服务工单系统PRD-v2.md) |

本规范只定义 AI 与客户端/服务端之间的接口契约。咨询/工单实体字段引用 `DM-*`；咨询、工单和知识状态迁移引用 `SM-*`；超时、重试、幂等和降级引用 `RD-*`。AI 不得直接创建、修改或关闭工单。

## AI-001 能力边界

- AI 只读取当前 `PUBLISHED` 知识版本及其检索索引；不得读取未发布案例、原始工单、普通聊天正文或撤回消息原文。
- AI 回答可以解释知识、提出澄清问题或拒答；不得执行命令、调用企业业务系统、修改工单、自动转派或静默代替员工提交工单。
- 高风险主题（账号权限、安全事件、数据丢失、高风险命令、硬件拆修）必须返回 `REFUSE`，并提供转人工和直接提单入口。
- 无可靠命中、知识冲突、置信度不足或模型无法完成时必须拒答，不得用常识补写未经引用的解决步骤。
- 每个关键结论必须至少有一个 `KnowledgeCitation`；拒答可为空引用，但必须有结构化拒答原因。

## AI-002 通用 HTTP 规则

- 路径前缀为 `/api/v1`，请求/非流式响应使用 `application/json`，流式响应使用 `text/event-stream`。
- 认证由 SSO 会话或批准的 Bearer Token 提供；`creatorId`、`sessionId` 的归属从认证上下文和路径对象解析，不信任请求体中的操作者 ID。
- 请求必须带 `X-Request-Id`；创建会话、发送消息、转人工和反馈必须带 `Idempotency-Key`。
- 时间使用 ISO 8601 带时区字符串；置信度和引用分数范围为 `[0,1]`；未知字段默认拒绝。
- 成功响应使用平台统一包络 `{code,message,request_id,data}`；AI 领域失败使用 `AI-*` 错误码，通用鉴权/状态/幂等错误引用 PRD API 约定。

## AI-003 Java DTO

```java
public record CreateConsultationRequest(
    @NotNull ConsultationSource source,
    @Size(max = 64) String categoryId) {}

public record AiChatRequest(
    @NotBlank @Size(max = 8000) String message,
    AiContextRefs contextRefs) {}

public record AiContextRefs(
    @Size(max = 64) String categoryId,
    @Size(max = 64) String assetId) {}

public enum AiReplyType { ANSWER, CLARIFY, REFUSE }
public enum AiRefusalReason {
    NO_RELIABLE_KNOWLEDGE, LOW_CONFIDENCE, CONFLICTING_KNOWLEDGE,
    HIGH_RISK_TOPIC, MODEL_UNAVAILABLE, POLICY_BLOCKED
}

public record KnowledgeCitation(
    @NotBlank String articleId,
    @NotBlank String versionId,
    @NotBlank String title,
    @DecimalMin("0.0") @DecimalMax("1.0") BigDecimal score,
    @NotBlank @Size(max = 1000) String snippet) {}

public record AiChatResponse(
    String sessionId,
    AiReplyType replyType,
    String answerText,
    List<KnowledgeCitation> citations,
    BigDecimal confidence,
    boolean suggestTransfer,
    AiRefusalReason refusalReason,
    String modelVersion,
    String interactionId) {}

public enum FeedbackType { HELPFUL, NOT_HELPFUL, INCORRECT }
public record AiFeedbackRequest(
    @NotBlank String interactionId,
    @NotNull FeedbackType feedback,
    @Size(max = 2000) String comment) {}

public record TransferRequest(@NotBlank String categoryId, Priority priorityHint) {}
public record TransferResponse(
    String sessionId, ConsultationStatus status, String assignmentId,
    long estimatedWaitSeconds) {}

public record KnowledgeSearchItem(
    String articleId, String versionId, String title,
    String summary, String categoryId) {}
public record KnowledgeSearchResponse(
    List<KnowledgeSearchItem> items, int page, int pageSize, long total) {}
```

DTO 不直接暴露 `DM-*` 实体；`AiInteraction` 只保存回答审计、引用、反馈和延迟元数据。

## AI-004 JSON Schema

以下 Schema 是 Draft 2020-12 的最小可执行约束。所有 Schema `additionalProperties=false`，版本变更规则见 AI-008。

### AI-004.1 创建咨询请求

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.invalid/schemas/create-consultation-request-1.0.json",
  "type": "object", "additionalProperties": false,
  "required": ["source"],
  "properties": {
    "source": {"enum": ["AI", "HUMAN_DIRECT", "TICKET_FOLLOW_UP"]},
    "categoryId": {"type": "string", "minLength": 1, "maxLength": 64}
  }
}
```

### AI-004.2 AI 消息请求

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.invalid/schemas/ai-chat-request-1.0.json",
  "type": "object", "additionalProperties": false,
  "required": ["message"],
  "properties": {
    "message": {"type": "string", "minLength": 1, "maxLength": 8000},
    "contextRefs": {
      "type": "object", "additionalProperties": false,
      "properties": {
        "categoryId": {"type": "string", "maxLength": 64},
        "assetId": {"type": "string", "maxLength": 64}
      }
    }
  }
}
```

### AI-004.3 AI 消息响应

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.invalid/schemas/ai-chat-response-1.0.json",
  "type": "object", "additionalProperties": false,
  "required": ["sessionId", "replyType", "citations", "confidence", "suggestTransfer", "modelVersion", "interactionId"],
  "properties": {
    "sessionId": {"type": "string", "minLength": 1, "maxLength": 64},
    "replyType": {"enum": ["ANSWER", "CLARIFY", "REFUSE"]},
    "answerText": {"type": "string", "minLength": 1, "maxLength": 12000},
    "citations": {"type": "array", "items": {"$ref": "#/$defs/citation"}},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "suggestTransfer": {"type": "boolean"},
    "refusalReason": {"enum": ["NO_RELIABLE_KNOWLEDGE", "LOW_CONFIDENCE", "CONFLICTING_KNOWLEDGE", "HIGH_RISK_TOPIC", "MODEL_UNAVAILABLE", "POLICY_BLOCKED"]},
    "modelVersion": {"type": "string", "minLength": 1, "maxLength": 128},
    "interactionId": {"type": "string", "minLength": 1, "maxLength": 64}
  },
  "allOf": [
    {"if": {"properties": {"replyType": {"const": "ANSWER"}}}, "then": {"required": ["answerText"], "properties": {"citations": {"minItems": 1}}}},
    {"if": {"properties": {"replyType": {"const": "CLARIFY"}}}, "then": {"required": ["answerText"]}},
    {"if": {"properties": {"replyType": {"const": "REFUSE"}}}, "then": {"required": ["refusalReason"], "properties": {"answerText": {"maxLength": 0}}}}
  ],
  "$defs": {
    "citation": {
      "type": "object", "additionalProperties": false,
      "required": ["articleId", "versionId", "title", "score", "snippet"],
      "properties": {
        "articleId": {"type": "string", "minLength": 1, "maxLength": 64},
        "versionId": {"type": "string", "minLength": 1, "maxLength": 64},
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "score": {"type": "number", "minimum": 0, "maximum": 1},
        "snippet": {"type": "string", "minLength": 1, "maxLength": 1000}
      }
    }
  }
}
```

### AI-004.4 反馈、转人工和知识搜索

反馈请求必须包含 `interactionId` 和 `feedback` (`HELPFUL|NOT_HELPFUL|INCORRECT`)，可选 `comment` 最长 2000 字符。转人工请求必须包含 `categoryId`，可选 `priorityHint` (`HIGH|MEDIUM|LOW`)；响应返回 `sessionId`、`status`、可选 `assignmentId` 和非负等待秒数。知识搜索响应只允许返回已发布文章的 `articleId/versionId/title/summary/categoryId` 及分页元数据，不暴露来源工单。

## AI-005 接口目录

| 编号 | 方法与路径 | 请求 | 响应 | 说明 |
|---|---|---|---|---|
| AI-API-001 | `POST /api/v1/consultations` | `CreateConsultationRequest` | 会话 ID、状态、创建时间 | 只创建咨询，不创建工单。 |
| AI-API-002 | `POST /api/v1/consultations/{id}/ai-messages` | `AiChatRequest` | `AiChatResponse` | 仅使用已发布知识。 |
| AI-API-003 | `POST /api/v1/consultations/{id}/feedback` | `AiFeedbackRequest` | interactionId、接收状态 | 无帮助/错误反馈进入脱敏优化队列。 |
| AI-API-004 | `POST /api/v1/consultations/{id}/transfer` | 转人工请求 | `TransferResponse` | 不接受员工指定工程师。 |
| AI-API-005 | `GET /api/v1/knowledge/search` | query/category/page/pageSize | `KnowledgeSearchResponse` | 只返回 `PUBLISHED`。 |
| AI-API-006 | `POST /api/v1/knowledge/evaluate` | 评测集引用 | 评测指标 | 仅知识库管理员可调用。 |

AI-API-004 的状态迁移引用 `SM-CONSULT-001`；所有超时、重试和不可用行为引用 `RD-003`、`RD-006`。

## AI-006 错误响应

```json
{
  "code": "AI_UNAVAILABLE",
  "message": "AI service unavailable",
  "request_id": "req_01J...",
  "fallback": "TRANSFER_OR_TICKET"
}
```

AI 领域错误码：`AI_UNAVAILABLE`、`AI_SCHEMA_INVALID`、`AI_NO_RELIABLE_KNOWLEDGE`、`AI_HIGH_RISK_BLOCKED`、`AI_SESSION_NOT_ACTIVE`。错误不得包含内部提示词、堆栈、向量内容或未发布知识。

## AI-007 流式协议

流式接口使用 SSE，每条事件包含 `eventId`、`sessionId`、`sequence`、`eventType`、`data`。`sequence` 从 1 递增；事件类型为 `answer_delta`、`citation`、`answer_completed`、`refusal`、`error`。客户端发现缺号必须重新拉取完整非流式响应。流式中断不改变咨询状态，只有服务端完成事件和 `SM-*` 迁移才能改变业务状态。

## AI-008 版本兼容与安全

- Schema `$id` 的 major 变更才允许删除字段或收紧约束；minor 版本只能新增可选字段。
- 服务端同时支持当前 minor 和上一个 minor；读取端忽略未来的非关键字段，写入端不得发送未声明字段。
- 模型输出必须先通过 JSON Schema、引用存在性、知识版本仍为 `PUBLISHED` 和高风险规则校验，再返回客户端。
- 原始对话、提示词和模型内部推理不进入知识库或训练集；反馈入队前按 PRD 脱敏规则处理。
