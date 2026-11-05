# AI 咨询流式输出（SSE + 打字机）设计

日期: 2026-11-04
状态: 待用户裁决（本文档为路线 A「上游真流式 + 终审回滚」的落地设计）
前置: `2026-11-04-semantic-answer-cache-design.md`（语义缓存已实施完成）; `2026-09-30-rag-consultation-composition-design.md`（组合方案红线）

## 意图与动因

当前 AI 咨询回答是「全文生成完毕 → 校验 → 一次性返回」，员工提问后要盯着「AI 正在思考」
等待整个生成过程（实测数秒到数十秒）。用户裁决（2026-11-04）:
**上游（模型侧）真流式,前端打字机逐字播放**——即讲义 Day29 的流式体验,但保留本项目的
守卫红线:用户看到的仍是「已通过哨兵与置信度裁决」的答案,裁决若在全文到齐后否决,
则发送终审事件,前端撤回暂定内容并替换为最终文案。

## 目标

1. POST 流式端点,首 token 延迟≈模型出字速度（消解 `aiThinking` 长等待）
2. 前端 ConsultationChat.vue 打字机渲染,`final` 事件前内容标记为暂定
3. 终审回滚:Guard/引用/版本哨兵语义与现状**完全一致**,零红线降级
3a. **会话内串行队列**（2026-11-05 用户裁决）:同一会话内的流式请求按 FIFO 排队,
  后到消息照常在窗口发出,前一问终态（final/error）后才开始处理下一问;
  排队请求的等待时间计入其自身统一预算,超预算以真实 TIMEOUT 走 error 终态
4. `firstTokenTimeoutMs=5000` 首次生效（预算哨兵,超时以真实原因报 error 事件,不静默回退）
5. 与语义缓存共存:命中时整文一次性作为单 token 事件 + final

## 非目标 / 反目标

- 不做多轮 token 级对话协议（仍是单请求-单回答的 SSE 通道）
- Python agent_service（Function Calling/ReAct）路径**本期不流式**:其 LLM 调用与 ReAct 循环
  在 Python 侧,流式化它属于跨语言改造,收益场景（AI_AGENT_ENABLED=false 为默认）不成立;
  agent 启用时流式端点自动退化为「整文单 token 事件 + final」——打字机由前端动画兜底
- 不做 WebSocket（无状态单答场景 SSE 足够）;不做 token 级幂等（幂等仍以完整回答为单位）
- 旧 POST `/ai-messages` 端点保留不动（对外契约稳定性;前端是唯一消费者,逐步切换）

## 现状关键事实（侦察结论）

- `OpenAiCompatibleModelClient.complete()`: `stream:false` + `response_format:json_object`,
  单 `message.content` 为完整 JSON,严格校验 finish_reason=stop/无 tool_calls/content 文本
- 六键协议: `replyType/answerText/usedVersionIds/confidence/knowledgeConflict/offTopic`,
  校验要求 `payload.size()==6`;system prompt 的字段示例顺序为 replyType→answerText→…
  （answerText 第二位,流式增量提取可尽早开工,但**不能依赖**此顺序——键序不受约束）
- 链路: `AiConsultationService.chat`（幂等包裹）→ `GuardedRagClient.answer`
  （断路器+信号量+Future.get 超时+可重试重试）→ `ComposedRagAdapter.answer`（七步编排,
  含语义缓存 lookup/write）→ `OpenAiCompatibleAnswerGenerator.generate`（六键严格校验）
  → Guard/哨兵 → `persistInteraction/persistAiMessage` → `AiChatResponse`
- 前端: `frontend/src/api/consultation.js:88` `aiMessage()` axios POST;
  `ConsultationChat.vue` 已有 `aiThinking` 占位与 aria-live 结构
- 2026-09-23 spec:485 曾设计过 SSE（`firstTokenTimeoutMs=5000`）但未实施

## 方案（已选路线 A）与备选

- **A（选定）**: 上游 `stream:true`,六键 JSON 增量提取 `answerText` 字段值逐段外发;
  全文到齐后按现状六键整校验 → Guard/哨兵 → final 事件。终审否决则前端撤回暂定文本。
- **B（否决）**: 已审答案分块推送。首 token 延迟无改善,违背用户明示的「上游流式」。
- **C（否决）**: 混合按风险分流。双路径分支债,违背装配期选择原则。

## 组成部分

### 1. 事件协议（text/event-stream, POST）

```
event: queued  data: {"position":2}                 // 0..1 次,进入即告知在队（可选推进）
event: token   data: {"delta":"文本片段"}          // 0..N 次,final 前视为暂定
event: final   data: {ApiEnvelope<AiChatResponse>} // 恰 1 次;含 replyType/citations/confidence/…
event: error   data: {"errorClass":"TIMEOUT",      // 0..1 次,终态,流中途依赖失败/排队超预算
                        "retryable":true,"message":"…"}
```

- **会话串行**: ai-chat/stream 以 sessionId 为键做 FIFO 串行（每会话同一时刻仅 1 个在处理,
  其余排队;排队中除 queued/keep-alive 外不发事件）;同 key 重复请求被串行化后
  排到队首时前请求已落库,幂等重放直接生效——无需挂起等待原语;排队等待计入该请求
  统一预算（deadline 在接受请求时建立）,超预算以真实 TIMEOUT error 终态,不静默丢弃

- final 即终态:REFUSE/CLARIFY 时 `answerText` 为最终文案,前端**清空暂定流并替换**;
  `final` 中的回答与旧 POST 端点逐字节一致（同一 AiChatResponse 序列化）
- error 只在「已发过 token 或无法产生 final」时出现;未开始流式即失败（域拒答/检索失败）
  的场景**不发 token,直接 final**（拒答也是合法终态,走 final 而非 error——错误是故障,拒绝是业务结果）
- 事件 data 均为 JSON;注释帧 `: keep-alive` 每 15s（防网关空闲断连）

### 2. 模型客户端流式化（`OpenAiCompatibleModelClient`）

- 新增 `completeStream(policy, input, maxTokens, context, TokenSink sink)`:
  body 同 complete 但 `stream:true`;响应体以 SSE 帧解析（`data: {...}`、`[DONE]`）,
  累积 `choices[0].delta.content`;每帧解析失败/字段畸形 → `DependencyFailure.invalid()`
  （与现状同严）;结束帧校验 finish_reason=stop
- **增量六键提取器**（新组件 `adapter/model/StreamingJsonExtractor`）:
  状态机扫描累积缓冲,定位 `"answerText"` 字符串值,对其内容片段做 JSON 字符串反转义后
  调 `sink.accept(unescapedFragment)`;键序不依赖（answerText 未出现前缓冲等待,
  出现即开始外发;字段结束后停止）;转义/UTF-16 代理对跨片段边界正确处理
- 完整 JSON 到齐后走与 `complete` 相同的六键整校验并返回 `JsonNode`——
  流式只影响「外发时机」,不影响「校验语义」

### 3. TokenSink 贯通（内部接口变更,同步迁移调用方）

- 新类型 `adapter/TokenSink`（`void accept(String fragment)`,附 `onFirstToken` 时间钩子）
- `AnswerGenerator.generate(query, material, context, TokenSink)` 增参;
  `LocalKnowledgeAnswerGenerator` 忽略 sink（零 token,与现状一致）;
  `OpenAiCompatibleAnswerGenerator` 本地路径传给 `completeStream`,
  agent 路径在拿到整文后单次 `sink.accept(text)`（保证前端一次拿到全文）
- `RagAdapter/GuardedRagClient.answer(query, requestId, TokenSink)` 增参并迁移全部调用点;
  `ComposedRagAdapter` 把 sink 传入 generator;语义缓存命中路径不调 sink（由服务层整文单发）
- **重试与重复语义（红线）**: GuardedRagClient 的可重试重试**仅在尚未外发任何 token 时**
  允许;已外发 token 的尝试失败 → 直接以真实 errorClass 走 error 终态,不静默重发
  （避免用户看到拼接重复文本,也避免静默回退）

### 4. 流式端点（`AiConsultationController`）

- `POST /{id}/ai-messages/stream`,头 `Idempotency-Key` 必填,返回
  `text/event-stream`（Spring `SseEmitter` 或直接 `ResponseBodyEmitter`——实现期定,倾向后者,少一层封装）
- `AiConsultationService.chatStream(...)`: 复用现有 doChat 全链路
  （幂等包裹、历史加载、员工消息落库、Guard、哨兵、双持久化**全部不变**）,
  仅新增 TokenSink 实现:转发到 HTTP 响应流,记录首 token 时刻用于
  `firstTokenTimeoutMs` 预算检查（超时 → 取消上游、error 事件、留真实原因）
- 幂等重放: 同 key 二次请求不重跑链路,以缓存的结果重放「单 token(final.answerText)+final」
- 落库时机不变:token 边发边走,`final` 发出前完成 persist（final 里的 interactionId 是真的）

### 5. 前端打字机（ConsultationChat.vue + consultation.js）

- `aiMessageStream(id, message, {onToken})`: 原生 `fetch` + `ReadableStream` 解析 SSE 帧
  （axios 不支持浏览器流式响应体）;鉴权头沿用现有 token 注入逻辑
- 气泡渲染: 收到 token 即追加,「AI 正在思考」占位切换为流式气泡
  （加打字机光标样式）;`final` 到达 → 撤除暂定标记,以 final 载荷重建完整气泡
  （引用/置信度/草稿/反馈按钮只在 final 后出现）;final 为 REFUSE/CLARIFY →
  清空已流文本替换为最终文案;`error` → 显示故障提示并保留已流文本的可复制性
- 断流兜底: 连接中断且无 final → 提示「回复中断」;不做自动重发（幂等键已消费）
- 旧 `aiMessage()` 保留（渐进切换与降级开关用）

### 6. 配置

`itticket.consultation.ai.*` 新增:
- `streaming-enabled`（默认 `true`? 否——**默认 false**,与缓存同款渐进开关,`AI_STREAMING_ENABLED`）
- `firstTokenTimeoutMs=5000`（已存在未生效,本期启用）
其余预算/超时沿用现有统一预算（RagCallContext deadline 全程管流式生命周期）

### 7. 语义缓存共存

- 命中: 服务层单 token 事件（整文）+ final——零模型调用,延迟最优
- 未命中: 流式生成,成功后按现 write 规则入缓存（缓存的是终稿,与流式无关）
- 流式路径**不读缓存旁路**（lookup 仍在 adapter 域门禁后,不变）

## 约束（红线沿用）

1. 用户所见文本仍必须过 Guard+哨兵:final 前的暂定文本属「展示中」,终审否决即撤回——
   这是路线 A 的明示代价,用户已裁决接受
2. 三态严格区分:final=业务终态（含拒答）;error=依赖故障（真实 errorClass）;不发模糊的
   「出错了请重试」
3. 无静默回退:agent 路径退化整文、流式失败不退回 POST 协议,均以事件如实告知
4. 流式超时计入统一预算;firstToken 预算哨兵独立计数
5. 旧端点字节级不变;新端点消费者只有自家前端
6. AGENTS.md:内部接口增参须迁移全部调用方与测试,不留转发壳

## 验收

- 首 token 延迟 < 2s（本地 stub 模型）,final 延迟与现状全链路同量级
- 拒答/CLARIFY/降级/断流/幂等重放/缓存命中各有一条 HTTP 集成测试
- 前端打字机 + 终审回滚手动演示
- 旧端点回归:全量测试零变更通过

## 已定裁决（实施期不再议）

1. **firstTokenTimeoutMs=5000 只管模型流式首字节**;agent 路径（ReAct 实测 10-70s 才有整文）
   与缓存命中天然豁免（它们的延迟由 requestTimeoutMs 统一预算管辖）——否则 agent 路径 100% 假超时
2. **/stream 端点始终存在**,`streaming-enabled=false` 时退化为「整文单 token + final」;
   前端仅一条代码路径,无客户端降级分支（守无静默回退）
3. **断流后暂定文本置灰标记「回复中断(未完成)」**:不删除（可复制）,不冒充正式回答
4. **同 key 并发 = 会话串行队列 + 幂等重放**:后到者排队,排到时前问已完,重放 final;
   无立即拒绝（方案甲否决）,无独立挂起原语（方案乙否决）

## 留给实施期的裁决

- SseEmitter vs ResponseBodyEmitter（倾向后者）;gateway SSE 空闲超时实测
- TokenSink 的背压策略（本期:无界缓冲+写失败即中断流,单答案体量小,不做复杂背压）
- 前端 SSE 帧解析器放 api 层还是独立 util
- 队列深度上限（若设）:倾向不设——预算哨兵已封顶最坏等待
- DependencyHttpClient 新增 postStream（ofLines 流式读取,错误语义与 post 完全一致）
- 幂等冲突边界:appendEmployeeMessage 在事务内,流式路径沿用现有 IdempotencyService 语义,不重造
