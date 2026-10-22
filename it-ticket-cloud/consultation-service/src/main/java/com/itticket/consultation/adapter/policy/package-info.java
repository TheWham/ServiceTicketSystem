/**
 * 请求意图判定包 —— AI 客服链路的第 1 环：决定「这次请求走哪条路」。
 *
 * <p><b>整条链路全景</b>（一份员工 AI 消息从进入到回答的完整旅程）：
 * <pre>
 *  前端 AI 会话 → 网关 :8080 → consultation-service :8301（AiConsultationService）
 *    │
 *    ├─ ① 意图判定（本包）…………… SemanticRequestClassifier 一次模型调用给出
 *    │      RequestVerdict{domain, tool}：
 *    │        domain → 拒答空间（OFF_TOPIC/HIGH_RISK 拒答，UNCERTAIN 追问，OFFICE_IT 作答）
 *    │        tool   → 工具意图（query_my_tickets / prepare_ticket / NONE）
 *    │
 *    ├─ ② 领域门禁（ComposedRagAdapter.restrict）… OFF_TOPIC/HIGH_RISK 在此短路，
 *    │      工具意图顶不开它（安全红线先于一切）
 *    │
 *    ├─ ③ 知识检索 …………………… RagServiceKnowledgeRetriever → rag-service :8302
 *    │      → Python 检索服务 :8310（向量化 + 双路召回 + 精排 + 低置信拒答）
 *    │
 *    ├─ ④ 工具意图放行 ……………… 检索无果/低置信本应拒答；若 tool != NONE 且 agent
 *    │      开启（pythonAgentClient.enabled()），放行给 Function Calling 智能体
 *    │
 *    ├─ ⑤ 生成 ……………………… tool 路径 → PythonAgentClient → agent_service :8320
 *    │      （ReAct 循环：deepseek 按白名单工具自主调用 查工单/建单草稿/补搜知识，
 *    │        代码在 services/python-retrieval/agent_service/）
 *    │      知识路径 → OpenAiCompatibleModelClient 单轮生成（引用 material）
 *    │
 *    ├─ ⑥ 输出守卫 …………………… AiAnswerGuard.evaluate：引用存在性 + MySQL
 *    │      PUBLISHED 复核 + 置信度门槛；工具意图作答按「无知识依据」通道放行
 *    │
 *    └─ ⑦ 落库与返回 ……………… 人机回环：建单只产草稿（ticketDraft 带外返回），
 *           员工在前端确认后才经 /ticket-draft/confirm 调 ticket-service 真正建单
 * </pre>
 *
 * <p><b>本包只负责第 ① 环</b>。三个实现要点：
 * <ul>
 *   <li>判定结果 {@link RequestVerdict} 用 Python 侧 {@code tool_specs()} 的工具名，
 *       两端同一套符号，防漂移测试见 {@code agent_service/tests/test_tool_contract.py}；</li>
 *   <li>{@link SemanticRequestClassifier}（默认）是模型语义判定，
 *       {@link KeywordRequestClassifier} 是它的降级兜底（模型输出不合法时整条退回，
 *       传输层失败则上抛交给断路器——见其类注释的失败语义表）；</li>
 *   <li>判定与门禁的先后不可交换：先判 domain 再谈 tool，
 *       越界内容不因提到「工单」二字而被放行。</li>
 * </ul>
 */
package com.itticket.consultation.adapter.policy;
