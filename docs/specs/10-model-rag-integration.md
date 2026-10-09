# 模型与 RAG 接入契约

| 项目 | 约束 |
|---|---|
| 规范编号 | MR |
| 冻结接入方式 | baseUrl + apiKeySecretRef |
| 默认协议 | OpenAI-compatible HTTP；路径和协议版本配置化 |
| 输出权威 | AI-003、AI-004 |
| 故障权威 | RD-003、RD-006、RD-007 |

本规范只负责模型 provider、RAG 检索编排、安全配置、协议适配、验证链路和运行治理。不定义工单实体、状态迁移、权限事实或领域事件。模型不得访问 MySQL、Redis、对象存储、企业业务 API，也不得创建、修改、分配或关闭工单。

## MR-001 Provider 配置

配置以不可变版本发布。除 Secret 值外，配置元数据可保存在 MySQL；运行时通过 apiKeySecretRef 从批准的加密 Secret 管理器解析。

| 字段 | 类型 | 必填 | 默认/约束 |
|---|---|---:|---|
| providerId | string | 是 | 1-64，环境内唯一 |
| baseUrl | URI | 是 | HTTPS；本地 HTTP 需安全审批 |
| apiKeySecretRef | string | 是 | 1-255，只保存 Secret 引用 |
| model | string | 是 | 1-128 |
| embeddingModel | string | 否 | 启用 embeddings 时必填 |
| protocolVersion | string | 否 | openai-compatible-v1 |
| chatPath | string | 否 | /v1/chat/completions |
| embeddingsPath | string | 否 | /v1/embeddings |
| healthPath | string | 否 | /v1/models |
| connectTimeoutMs | integer | 否 | 2000，范围 100-5000 |
| firstByteTimeoutMs | integer | 否 | 5000，范围 1000-10000 |
| requestTimeoutMs | integer | 否 | 15000，范围 1000-30000 |
| maxTokens | integer | 否 | 2048，范围 1-8192 |
| temperature | decimal | 否 | 0.1，范围 0-1 |
| topK | integer | 否 | 5，范围 1-20 |
| similarityThreshold | decimal | 否 | 0.70，范围 0-1；仅决定可靠引用，不作为回答门槛 |
| streamEnabled | boolean | 否 | true |
| enabled | boolean | 否 | false，健康和评测通过后启用 |

禁止内联 apiKey、任意自定义认证头、URL 凭据、通配域名、未授权重定向、关闭 TLS 校验、无限超时、temperature 大于 1、缺省 token 上限和 provider 工具调用。配置发布必须校验字段、Secret 可读、baseUrl 安全和 chat 健康。

## MR-002 baseUrl 与 Secret

每次保存和解析 baseUrl 都执行 SSRF 防御：scheme 仅批准 HTTPS（本地 HTTP 需环境策略）；hostname 和解析出的全部地址命中白名单；禁止 loopback、link-local、metadata、未授权内网地址、用户信息、fragment 和非批准端口；禁止未重新校验的重定向；path 禁止 ..、协议覆盖和双重编码。

apiKey 只存在 Secret 管理器和调用进程短生命周期内存，以 Authorization Bearer 发送。禁止出现在代码、Git、MySQL、Redis、日志、trace/span、指标 label、异常、HTTP 响应、诊断包和 prompt。过滤器必须屏蔽 Authorization、api-key 和 provider 认证头。

## MR-003 OpenAI-compatible HTTP

适配器对业务层暴露稳定接口，provider 差异不得扩散。

Chat Completions 请求为 baseUrl + chatPath：

~~~json
{"model":"configured-model","messages":[{"role":"system","content":"policy and output contract"},{"role":"user","content":"question and published context"}],"temperature":0.1,"max_tokens":2048,"stream":false,"response_format":{"type":"json_object"}}
~~~

必需字段为 model/messages/temperature/max_tokens/stream。response_format 不支持时可由 adapter 省略，但返回仍必须通过 AI-004.3 Schema。非流式响应至少含 id、model、choices[].message.content、finish_reason；adapter 只接受一个 choice，将 content 解析为 JSON，不采信工具调用、系统指令、引用 ID 或业务动作。

Embeddings 仅在配置 embeddingModel 且检索需要时调用：

~~~json
{"model":"configured-embedding-model","input":["normalized published knowledge chunk"]}
~~~

响应至少含 data[].index、data[].embedding、model。向量必须为有限数值且维度与索引版本一致。检索请求可发送当前问题及从授权 AI 历史中提取的必要上下文，受 MR-004 的范围和长度限制；不得发送普通人工聊天、撤回内容、未脱敏案例或未发布知识，不得将整段会话作为知识入库。

SSE 使用 stream=true，消费 data JSON 帧和 data [DONE]，限制单帧/累计大小，按序拼接 delta.content。缺 DONE、超时、中断、无 choice 或超限均丢弃不完整结果。只有完整 JSON 通过 MR-005 后才转为 AI-007 客户端 SSE，不原样透传 provider 帧。

健康检查默认 GET healthPath，不发送业务数据，只检查认证、连接、协议和目标模型可见性。状态为 HEALTHY、DEGRADED、UNHEALTHY。

## MR-004 RAG 调用链路

当前会话鉴权与有界 AI 历史加载 -> 模型领域/风险语义判定 -> 已发布 KnowledgeVersion 检索 -> prompt/context assembler -> provider adapter -> JSON parse 与 AI-004 Schema 校验 -> citation verifier -> AiInteraction 元数据 -> AI API 响应。

当前认证用户须先通过当前会话的归属/访问校验，再由服务端加载该 AI 会话历史；不得由请求指定任意他人会话。默认最多最近 12 条、合计 12000 字符，配置有硬上限；只保留 AI 对话的 user/assistant 消息，按时间正序传递，并排除撤回、普通人工聊天、系统消息及当前重复消息。不得读取其他会话、原始工单或未发布知识。历史用于理解追问和已尝试步骤；历史正文与知识正文均作为数据隔离，不能提升为 system 指令。分类、检索查询组装和生成使用同一授权上下文，话题变化时以当前请求为准。

领域判定独立于生成结果，区分 OFFICE_IT、OFF_TOPIC、HIGH_RISK、UNCERTAIN；模型根据当前请求和历史的完整语义分类，覆盖所有合法 IT/电脑问题，不以固定词表替代语义判断。领域外直接结构化拒答，信息不足时先针对上下文澄清。单个 IT 关键词或检索命中不构成领域许可；没有关键词的连续追问也不构成拒答理由。模型已经判定为合法 IT 的请求，不得因 RAG 旧领域规则误判或 LOW_CONFIDENCE 建议被阻断通用生成。

非法入侵、未经授权提权、绕过身份验证或安全控制等风险请求仍阻断。合法自助密码重置、普通登录排障、安装配置等可给出官方步骤、权限前提和必要注意事项；不能仅凭“重置”“密码”“命令”等词拒答。模型不得编造公司内部地址、政策、凭据、审批结果或已执行操作，不能执行系统操作或调用企业业务接口。

检索器只返回当前 PUBLISHED 版本并携带 articleId/versionId/score/snippet/indexVersion。assembler 负责 token 预算、边界标记和 prompt injection 隔离。有可靠相关资料优先参考；无命中或弱命中均允许模型给出合法 IT 通用建议，ANSWER 可无引用，客户端明确标注无知识库依据。RAG 的 confidence-threshold（默认 0.70）仅决定可靠引用：有效命中最高分达到该阈值才有 reliable=true，低于阈值或无命中为 false；0.4499、0.45、0.55、0.6999 均不建议拒答，0.70 才达到默认引用质量阈值。low-confidence-threshold（旧默认 0.45）保留配置兼容但不再参与判定，不存在分数区间拒答策略。

模型输出需校验 replyType、confidence 的 [0,1] 数值范围、领域/风险标记和引用的一致性；有效的通用或带引用 ANSWER 不因自评分低于 minConfidence 被拒答。confidence 用于审计和 suggestTransfer（低评分仍建议转人工；通用回答始终保留该建议）。CLARIFY 应为无引用的非空追问，不要求置信度达到回答阈值。只要声明引用，无论自评分多少，版本必须来自本次检索且仍为当前 PUBLISHED，并能定位 snippet。伪造/失效引用、矛盾领域标记、知识冲突、非法结构均不得作为通用 ANSWER 放行。AiInteraction 不保存 key、内部推理或完整 prompt。领域判定与生成共享一次业务请求的总体超时、并发限制及有限重试预算。

## MR-005 错误衔接

| 结果 | 行为 |
|---|---|
| 超时 | AI_UNAVAILABLE，保留转人工/提单 |
| HTTP 429 | 按 RD-003 同一请求最多重试一次，失败 AI_UNAVAILABLE |
| HTTP 5xx | 断路器计数，有界重试后 AI_UNAVAILABLE |
| HTTP 401/403 | 不重试，标记 UNHEALTHY，告警，AI_UNAVAILABLE |
| 其他 4xx | 不重试，AI_UNAVAILABLE |
| 非 JSON、缺字段、Schema 失败 | AI_SCHEMA_INVALID，不返回原文 |
| 引用伪造/版本失效 | 结构化拒答或 AI_SCHEMA_INVALID |
| 无相关知识或弱命中，问题属于合法 IT/电脑范围 | 模型可给出通过校验的无引用通用回答，不因检索分数或空检索直接拒答 |
| 非办公 IT | AI-004 REFUSE + OFF_TOPIC，明确不能答复 |
| 领域不明确或缺少必要信息 | AI-004 CLARIFY，结合当前会话追问，非空正文且无引用 |
| 非法/未授权风险请求或知识冲突 | AI-004 REFUSE，提供人工入口 |
| 有效 ANSWER 的模型自评分低 | 保留回答和审计分数，可建议转人工，不转为 LOW_CONFIDENCE 拒答 |
| 验证成功 | 返回 AI-004 结果 |

错误不得包含 provider body、凭据、prompt、知识全文或堆栈。重试复用 requestId，不重复写成功 AiInteraction。

## MR-006 Adapter 边界

~~~java
interface ModelProviderAdapter {
  ProviderResult<ProviderChatResult> complete(ProviderChatRequest request, ProviderConfigSnapshot config);
  ProviderResult<ProviderStream> stream(ProviderChatRequest request, ProviderConfigSnapshot config);
  ProviderResult<ProviderEmbeddingResult> embed(ProviderEmbeddingRequest request, ProviderConfigSnapshot config);
  ProviderResult<ProviderHealth> health(ProviderConfigSnapshot config);
}
~~~

业务层只依赖标准接口和结果，不判断 Qwen/OpenAI 厂商名。本地 Qwen 与第三方差异仅存在 adapter/config mapping，不改变 AI DTO、状态机、错误码或验证顺序。embeddings 与 stream 仅在对应功能启用时必须具备；response_format、usage、models 可缺失，按 MR-013 使用本地 Schema 校验、usage=null 和配置化 health probe fallback，不得伪造能力。

## MR-007 版本和观测

请求冻结 providerConfigVersion、providerId、model、embeddingModel、providerModelVersion、promptTemplateVersion、retrievalIndexVersion、AI Schema version，并携带 requestId/traceId/interactionId/providerRequestId。指标覆盖成功率、429/4xx/5xx、超时、Schema/引用失败、拒答、首字节/完整延迟、token、命中数、索引版本、断路器和健康状态。日志只写 ID、版本、耗时、计数和错误分类。

## MR-008 轮换、灰度

Secret 轮换：创建新 Secret 版本 -> 探针 -> 原子切换引用 -> 清理旧认证上下文 -> 观察 -> 吊销旧版本。失败回退旧引用并告警。

配置状态为 DRAFT -> VALIDATED -> CANARY -> ACTIVE -> RETIRED。灰度按 hash(sessionId) % 100，同一会话保持同版本，除非熔断/紧急停用。灰度不得改变知识可见范围、Schema 或安全规则。回滚只切活动配置，不覆盖历史 AiInteraction 版本。

## MR-009 验收与未决部署参数

必须验证本地 Qwen 与第三方 stub 的同一 adapter contract、SSRF/DNS rebinding/重定向拒绝、Secret 不进入 Git/MySQL/Redis/日志/trace、chat/SSE/embeddings 错误行为、只检索发布知识、模型无法调用业务 API，以及灰度/轮换/熔断证据。

需部署冻结：Secret 管理器和引用 URI、baseUrl 域名/IP/CIDR/端口白名单、本地 Qwen HTTP 隔离网段、provider 并发/队列和成本阈值、灰度比例/观察窗口/健康频率。具体安全键名和默认值以 MR-015 为冻结基线。


## MR-010 持久化、DAO 与版本状态

provider 配置元数据必须持久化在 MySQL，apiKey 只保存 Secret 引用。规范表为 ai_provider_config，DDL 由 SQL-010 提供：

- provider_config_id、provider_id、config_version、status、base_url、api_key_secret_ref、model、embedding_model、protocol_version、path/capability JSON、timeout/concurrency JSON、generation JSON；
- created_by、created_at、validated_by、validated_at、activated_by、activated_at、retired_at、rollback_from_version、audit_request_id；
- 唯一键 provider_id + config_version，索引 provider_id + status；
- status 只能按 DRAFT -> VALIDATED -> CANARY -> ACTIVE -> RETIRED，ACTIVE 同一 provider 只能一个版本。

MyBatis DAO 只允许显式列查询和 version 条件更新：

~~~java
interface AiProviderConfigMapper {
  Optional<ProviderConfigSnapshot> selectActive(String providerId);
  Optional<ProviderConfigSnapshot> selectVersion(String providerId, long version);
  int insertDraft(ProviderConfigRecord record);
  int updateStatus(String providerId, long version, String expectedStatus, String nextStatus, String actorId);
}
~~~

审计记录配置版本、字段前后值（Secret 只记录 ref）、操作者、请求追踪和结果。配置生效、灰度、回滚、轮换均不可覆盖历史版本。

## MR-011 RAG Adapter 与索引生命周期

业务层使用四个稳定接口：

~~~java
interface KnowledgeRetriever {
  List<RetrievedChunk> search(String query, RetrievalPolicy policy);
}
interface IndexWriter {
  IndexWriteResult write(String articleId, String versionId, List<KnowledgeChunk> chunks);
}
interface IndexActivator {
  ActivationResult activate(String indexVersion, String knowledgeVersion);
  ActivationResult offline(String knowledgeVersion);
}
interface IndexRefreshWorker {
  void handle(IndexRefreshCommand command, WorkerContext context);
}
~~~

IndexWriter 只能接收已脱敏、结构完整的 PUBLISHED 候选版本；写入新 indexVersion 后才允许 IndexActivator 原子切换 active pointer。active pointer 持久化在 MySQL rag_index_pointer（article_id、knowledge_version_id、index_version、status、version），使用 generated active_article_id + unique index 保证同一文章只有一个 ACTIVE；IndexActivator 按 article_id 加事务锁，通过 MyBatis version 条件在同一事务中将旧 ACTIVE 置为 OFFLINE、新版本置为 ACTIVE。下线先在 MySQL 完成知识状态迁移，再发布 KNOWLEDGE_OFFLINE，IndexActivator 移除检索可见版本；索引失败不回滚知识事实，进入 Outbox delivery 重试/DLQ。

索引存储必须包含 articleId、versionId、chunkId、embedding、contentHash、indexVersion、publishedAt、offlineAt；向量库或搜索引擎是可重建投影，不是事实源。Redis 只承载索引 refresh 队列，不保存 active pointer。worker 流程为读取 Outbox -> 校验 Schema/版本 -> 写索引 -> 激活或下线 -> MySQL 记录 delivery 成功 -> ACK；失败先重试，超过 EV-009 上限进入 DLQ。

## MR-012 ProviderResult 统一类型

所有 provider adapter 方法返回同一强类型结果包络：

~~~java
record ProviderResult<T>(
  String providerRequestId,
  ProviderStatus status,
  ProviderErrorClass errorClass,
  boolean retryable,
  Instant occurredAt,
  T value
) {}
enum ProviderStatus { SUCCESS, RETRYABLE_FAILURE, PERMANENT_FAILURE, UNAVAILABLE }
enum ProviderErrorClass {
  TIMEOUT, RATE_LIMITED, UNAVAILABLE, AUTH_FAILED, INVALID_REQUEST,
  INVALID_RESPONSE, CITATION_INVALID, NO_RELIABLE_KNOWLEDGE, SECURITY_REJECTED
}
~~~

complete、stream finalization、embed、health 均必须填充 providerRequestId（provider 无 id 时使用受控本地 request id）、status、errorClass、retryable、occurredAt。MR-005 是唯一映射：429/5xx/超时为 RETRYABLE_FAILURE；401/403、非法请求、Schema/引用失败为 PERMANENT_FAILURE；网络熔断为 UNAVAILABLE。业务层只依据 ProviderStatus 和 errorClass，不读取 provider-specific body。

## MR-013 Capability 与协商

provider capability 必须显式持久化并在健康检查返回：

~~~json
{
  "chat": true,
  "stream": true,
  "responseFormatJson": false,
  "embeddings": true,
  "usage": false,
  "models": false
}
~~~

responseFormatJson=false 时 adapter 不发送 response_format，始终在本地执行 AI-004 JSON Schema 校验；不能因 provider 不支持而放宽约束。usage=false 时 usage 字段为 null，指标标记 usage_unavailable；models=false 时 health 使用配置化只读 probe，不能伪造 models 列表。embeddings=false 或 stream=false 时，相关能力配置必须关闭；配置校验拒绝 capability 与路径不一致。

## MR-014 客户端流式协商

AI chat endpoint 按 Accept 协商：

- Accept: application/json -> 非流式 AiChatResponse；
- Accept: text/event-stream 且 provider/config streamEnabled=true -> 服务端 AI-007 SSE；
- 其他 Accept -> 406 NOT_ACCEPTABLE；
- 请求 Content-Type 必须是 application/json，响应 Content-Type 严格匹配协商结果。

AI-007 事件 envelope Schema：

~~~json
{
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "$id":"https://example.invalid/schemas/ai-stream-event-1.0.json",
  "type":"object","additionalProperties":false,
  "required":["eventId","sessionId","sequence","eventType","data"],
  "properties":{
    "eventId":{"type":"string","minLength":1,"maxLength":64},
    "sessionId":{"type":"string","minLength":1,"maxLength":32},
    "sequence":{"type":"integer","minimum":1},
    "eventType":{"enum":["answer_delta","citation","answer_completed","refusal","error"]},
    "data":{"type":"object"}
  }
}
~~~

服务端只有在完整 answer JSON、Schema、引用和安全规则均通过后发送 answer_completed；provider 中断只发送结构化 error，不改变咨询状态。客户端缺号按 AI-007 重新拉取非流式响应。

## MR-015 冻结安全键与默认策略

环境变量/配置键名固定如下，禁止同义别名：

| 键 | 默认值 | 规则 |
|---|---|---|
| MODEL_SECRET_REF | 无默认 | 必填 Secret 引用，禁止明文 |
| MODEL_BASE_URL_ALLOWLIST | 无默认 | 启动时非空；host/CIDR/port 白名单 |
| MODEL_EGRESS_PROXY_URL | 空 | 生产默认必须配置；直连仅开发环境批准 |
| MODEL_PIN_RESOLVED_IP | true | 每次连接前解析并 pin 已校验 IP |
| MODEL_CONNECT_TIMEOUT_MS | 2000 | 100-5000 |
| MODEL_FIRST_BYTE_TIMEOUT_MS | 5000 | 1000-10000 |
| MODEL_REQUEST_TIMEOUT_MS | 15000 | 1000-30000 |
| MODEL_MAX_CONCURRENCY | 16 | 1-128，队列满立即降级 |
| MODEL_MAX_QUEUE | 64 | 0-1000，禁止无限队列 |
| MODEL_TLS_VERIFY | true | 禁止关闭 |
| MODEL_MAX_REDIRECTS | 0 | 每跳重校验，生产默认不跟随 |
| MODEL_STREAM_ENABLED | true | provider capability 仍须为 true |

Secret ref、allowlist、egress proxy、TLS verify 和 IP pin 在启动与配置热更新时校验。若不使用 egress proxy，每次连接前重新解析 DNS、校验全部地址、选取已校验 IP 建立连接并绑定 Host/SNI；连接期间 DNS 变化不允许切换到未校验地址。每一跳重定向重新执行 allowlist、DNS、IP pin 和端口校验；失败立即拒绝。

MODEL_SECRET_REF 仅是单 provider 部署的兼容默认键；当 ai_provider_config 存在 api_key_secret_ref 时，provider 版本引用优先，MODEL_SECRET_REF 不得覆盖它。多 provider 环境必须为每个 provider 版本显式配置 api_key_secret_ref，禁止回退到全局键。
