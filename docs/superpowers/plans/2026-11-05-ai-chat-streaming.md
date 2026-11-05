# AI 咨询流式输出（SSE + 会话串行队列 + 前端打字机）实施计划

plan: docs/superpowers/plans/2026-11-05-ai-chat-streaming.md
spec: docs/superpowers/specs/2026-11-04-ai-chat-streaming-design.md（含 4 条已定裁决, 实施期不再议）
方式: TDD, 每任务 RED→GREEN→迁移→提交→ledger（.superpowers/sdd/streaming/progress.md）
测试运行: cd it-ticket-cloud && JAVA_HOME=.superpowers/sdd/2026-11-04-semantic-answer-cache/tools/jdk-17.0.20.1+1 …/apache-maven-3.9.16/bin/mvn -q test -Dtest=Xxx -pl consultation-service

## 红线（每任务自检）
- final/queued/error 三态语义: final=业务终态(含拒答), error=依赖故障真实 errorClass, 无静默回退
- 全部答案仍过 Guard+版本哨兵; final 载荷与旧 POST 端点逐字节同构
- 内部接口增参必须迁移全部调用方与测试, 不留转发壳; 对外旧端点零变更
- 基线 340/340 不得回归

## Task 1 — StreamingJsonExtractor（纯组件）
文件: adapter/model/StreamingJsonExtractor.java + 同名 Test
契约: `void feed(String chunk)` + `boolean answerFieldCompleted()` + 流式状态机:
- 只外发 `"answerText":"…"` 字符串值内部内容（UTF-16 代理对/转义 \n \t \" \\ \/ \uXXXX 跨片段边界正确处理, 经 Consumer<String> sink 外发反转义片段）
- 键序不依赖: answerText 未出现之前缓冲所有 chunk; 以 JSON string 语法状态(in-string/depth)驱动而不是子串扫描, 避免键名出现在其他字符串值内误触发
- answered 字段结束后停止外发(剩余给整校验消费); `String extractComplete(String json)` 静态便捷方法给单测
用例: 单片完整对象 / 逐字符 feed 等价 / 转义跨片段 / 代理对跨片段 / answerText 在尾部 / 重复键取首 / 无 answerText(不外发不抛) / 键名出现在字符串值内

## Task 2 — 模型客户端流式化
文件: DependencyHttpClient(+postStream, 用 BodyHandlers.ofLines 流式行 + 与 post 完全一致的 4xx/5xx/超时/中断→DependencyFailure 语义, 冷状态码在首行前判断); OpenAiCompatibleModelClient(+completeStream(policy,input,maxTokens,context,Consumer<String> tokenSink) 返回 JsonNode: body stream:true, SSE data: 帧累积 delta.content→extractor.feed, [DONE]/finish_reason=stop 收口, 帧畸形 invalid; LocalKnowledge… 不动)
测试: JDK HttpServer stub 流式响应 data: {choices:[{delta:{content:…}}]}…data:[DONE], 断言 token 回调碎片序列与最终六键 JsonNode; 401/500/超时/畸形帧→DependencyFailure
前置: 错误分类复用现有 AUTH_FAILED/UNAVAILABLE/TIMEOUT, 无新枚举

## Task 3 — TokenSink 贯通生成侧
改动: adapter/TokenSink.java(新类型: accept(String)+boolean emitted(), AtomicBoolean 实现);
AnswerGenerator.generate(query, material, context, TokenSink) 增参; LocalKnowledgeAnswerGenerator 忽略 sink; OpenAiCompatibleAnswerGenerator 本地路径传 completeStream 的 extractor sink, agent 路径拿到整文后单次 sink.accept(text)(仅 tokenSink 未 emitted 时); 迁移全部实现与测试
测试: generator 流式回调冒烟(真 HTTP stub)

## Task 4 — TokenSink 贯通编排侧 + 缓存/重试语义
改动: RagAdapter.answer(+TokenSink)/GuardedRagClient.answer(+TokenSink) 增参, 迁迁移 7 处调用点(ComposedModelProtocolTest/GuardedRagDeadlineTest/RagCompositionHttpTest:105/ToolIntentBypassTest×3/AiCompositionConfig/AiConsultationService/新测试); GuardedRagClient 重试规则: 可重试重试仅当 tokenSink.emitted()==false, 已外发即以真实失败终态返回; ComposedRagAdapter: 语义缓存命中→sink.accept(整文 answerText) 再返回 hit(服务层无需感知); 拒答/CLARIFY/降级不调 sink
测试: ComposedRagCacheTest 增命中单 token 断言; 重试不重复发字

## Task 5 — SSE 服务编排（会话串行队列）
文件: service/AiConsultationService(+chatStream) 或新 StreamingChatOrchestrator(裁决: 倾向外置编排类, AiConsultationService 保持事务链; 复用其 doChat 语义但为事件流改造)
契约: `SseStreamHandle openStream(user, sessionId, request, idempotencyKey, StreamEventSink out)`:
- 会话 FIFO: sessionId→单许可+等待队列(ConcurrentHashMap<String, SessionGate>), 出队条件=前一 handle 终态; 排队等待计入自身统一预算, 超限 TIMEOUT error
- 事件: queued(带 position)/token/final/error, 15s keep-alive 注释帧(排队中最长 15s 一帧)
- 首字节哨兵: streaming-enabled 开启且本地生成路径时, 首 token 距开始>firstTokenTimeoutMs(5000)→取消上游以真实原因终态; agent/缓存豁免(裁决①)
- final 前完成 persistInteraction/persistAiMessage(链路内不资产阶级新写); 幂等: 排到队首后沿现有 idempotencyService 语义, 完成后重放开单 token+final
- 客户端断连: emitter onError/onCompletion→中断上游(经 sink 中断标志), 终态前不落库(与旧端点同律: 员工消息已落, AI 侧不半落)
测试: 两个并发流请求的 serial 化断言(第二个先 queued 后处理)/幂等重放/排队超预算

## Task 6 — 控制器与配置
文件: controller/AiConsultationController(+POST /{id}/ai-messages/stream, ResponseBodyEmitter, 头 Idempotency-Key, text/event-stream); ConsultationProperties.Ai(+streamingEnabled=false, `AI_STREAMING_ENABLED`); application.yml(占位符)
测试: 控制器层 wire test(401/首帧/事件头), flag=false 时整文单 token 路径

## Task 7 — 前端
文件: frontend/src/api/consultation.js(+aiMessageStream(id,msg,{onQueued,onToken,signal}): fetch+ReadableStream SSE 帧解析, 复刻 Authorization/X-Request-Id/Idempotency-Key 三头); frontend/src/components/ConsultationChat.vue(优化: 发送不锁输入、排队气泡、打字机光标、final 重建正式气泡含引用/置信度/反馈/草稿、REFUSE 回滚替换、中断置灰态)
验收: 手动打字机+终审回滚+排序演示; 旧 aiMessage() 保留

## Task 8 — 全量回归与提交整备
- mvn 全量+前端构建通过(npm run build); spec 部署说明(gateway SSE 空闲超时实测记录); 逐任务提交如已完成则为 rebase 检查; 整分支评审(独立子代理)

## 基线数字
- 当前: consultation-service 340/340; 前端构建另行验证
