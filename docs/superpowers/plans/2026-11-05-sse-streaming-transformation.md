# SSE 流式输出改造实现计划 (AI-007 标准)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有同步问答链路全面升级为基于 W3C 标准的 Server-Sent Events (SSE) 流式传输，并与 Day 29 的成本治理 Model Router 深度融合，实现首字极速呈现（打字机效果）与尾帧无缝挂载调用链可视化抽屉。

**Architecture:** 
采用端到端分层流式中继架构：Python 端（Agent/ModelClient）利用 `stream=True` 生成增量 Token 并在尾帧结算 GovernanceTrace；Java 端（consultation-service）通过 HTTP `Accept` 协商分发 `SseEmitter` 并封装 `AI-007` 标准事件包络；前端通过 `fetch` + `ReadableStreamDefaultReader` 逐帧解析，驱动双端打字机效果与高光胶囊抽屉联动。

**Tech Stack:** Python FastAPI/Starlette StreamingResponse, OpenAI SDK streaming, Spring MVC SseEmitter, Vue 3, Fetch Streams API.

**Spec:** `docs/specs/02-ai-api-json-schema.md` (AI-007 流式协议), `docs/specs/10-model-rag-integration.md` (协商与包络规范).

## Global Constraints
- 严格遵循 `docs/specs/10-model-rag-integration.md` 的事件包络结构：`eventId`, `sessionId`, `sequence`, `eventType`, `data`。
- 保留非流式兼容：`Accept: application/json` 返回原有 `ApiEnvelope<AiChatResponse>`；`Accept: text/event-stream` 返回 SSE。
- 遵循 `d:\day12\demos\AGENTS.md`：保持已有未提交改动，不使用空转发壳，保留真实失败状态。

---

### Task 1: Python 端 SSE 流式生成器与端点 (`services/python-retrieval`)
- [x] 1.1 在 `agent_service/model_client.py` 中为 `ModelClient` 增加 `complete_with_tools_stream` 与 `StreamingAnswerExtractor`，调用 `chat.completions.create(stream=True, stream_options={"include_usage": True})`，逐 Token 产出增量文本，在最后返回 usage。
- [x] 1.2 在 `agent_service/agent.py` 中为 `AgentRunner` 增加 `run_stream` 方法：
  - 触发 `CostGovernor` 前置路由与预扣，先 `yield` 路由/阶段信息帧；
  - 若触发工具调用则按需执行，并在进入生成时流式吐出模型 tokens；
  - 在生成完毕后执行事后结算，构建 `governance_trace`，`yield` 最终的 `done` 帧。
- [x] 1.3 在 `agent_service/app.py` 中新增 `POST /api/v1/agent/chat/stream` 端点，基于 `StreamingResponse(media_type="text/event-stream")` 输出符合 SSE 规范的行格式：`event: <type>\ndata: <json>\n\n`。
- [x] 1.4 在 `agent_service/tests/test_agent_stream.py` 编写测试并验证通过：`$env:PYTHONPATH="services/python-retrieval"; pytest services/python-retrieval/agent_service/tests/test_agent_stream.py -v`。

### Task 2: Java 端 SseEmitter 与内容协商 (`consultation-service`)
- [x] 2.1 新建 `dto/AiStreamEvent.java`，定义符合 `AI-007` 规范的传输载体（`eventId`, `sessionId`, `sequence`, `eventType`, `data`）。
- [x] 2.2 在 `adapter/model/DependencyHttpClient.java` 与 `adapter/agent/PythonAgentClient.java` 中增加 `postStream` 与 `chatStream`，利用 `HttpClient` 消费 Python 的 SSE 流并逐行分发回调。
- [x] 2.3 在 `service/AiConsultationService.java` 中增加 `chatStream(CurrentUser user, String id, AiChatRequest request, String idempotencyKey, SseEmitter emitter)`：
  - 鉴权、校验会话状态并保存用户消息；
  - 将 Python 产生的增量转换为 `AiStreamEvent`（`eventType=answer_delta`）实时发送给客户端；
  - 遇到引用与工具草稿按 `eventType=citation` 分发；
  - 在接收到完成通知并完成 Schema 校验后，持久化 AI 消息及 `governanceTrace`，发送 `eventType=answer_completed`，最后调用 `emitter.complete()`；
  - 异常时按 `AI-007` 发送 `eventType=error` 并安全关闭。
- [x] 2.4 在 `controller/AiConsultationController.java` 中针对 `POST /{id}/ai-messages` 增加 `produces = MediaType.TEXT_EVENT_STREAM_VALUE` 的处理逻辑。
- [x] 2.5 编写 `AiConsultationStreamTest` 验证内容协商与流式包络全部通过。

### Task 3: 前端双端流式接收器与打字机交互 (`frontend`)
- [x] 3.1 新建 `src/utils/sseReader.js`，实现标准 W3C SSE 流解析工具（支持行缓冲、事件类型分发、解析 JSON 数据、乱序递增校验与连接断开处理）。
- [x] 3.2 在 `src/api/consultation.js` 中增加 `aiMessageStream` 方法。
- [x] 3.3 在 `src/components/ConsultationChat.vue`（员工端）：
  - 改造发送逻辑，使用 `aiMessageStream` 携带 `Accept: text/event-stream`；
  - 逐字增量追加至当前气泡，支持打字机光标动画（`.stream-cursor`）与平滑触底滚动；
  - 收到 `answer_completed` 时挂载高光胶囊徽章与链路抽屉元数据。
- [x] 3.4 执行 `npm run build --prefix frontend` 验证打包无语法与构建错误。

### Task 4: 端到端综合回归与验证
- [x] 4.1 运行 Python 单元测试集（30/30 passed, 100%）。
- [x] 4.2 运行 Java consultation-service 全量回归测试（56/56 passed, 100%）。
- [x] 4.3 验证断流、降级及前后向兼容性。
