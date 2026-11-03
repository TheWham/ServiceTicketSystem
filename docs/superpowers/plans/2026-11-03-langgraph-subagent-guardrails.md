# LangGraph Subagent 多智能体编排与 Guardrails 安全护栏实施计划 (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `services/python-retrieval/agent_service` 中构建工业级 LangGraph 主从多智能体编排（Supervisor-Worker 拓扑，子图即节点）与双向 AI Guardrails（Prompt 越狱拦截 + PII 敏感信息动态脱敏与还原），对齐上游 Java 6 键契约，实现安全合规、职责隔离的 IT 运维排障闭环。

**Architecture:**
- **外层护栏 (AI Guardrails)**: 输入端拦截 Prompt 注入并对手机号/身份证等敏感信息进行 PII 掩码（`<PII_PHONE_1>`），输出端在本地安全 Vault 中对答复和草稿执行真实数据无损还原。
- **调度中枢 (Supervisor Router)**: 智能分析员工意图，自适应调度知识排障子图或工单流转子图（单意图走快通道，复合意图走多子图协同）。
- **垂直子智能体 (Subgraphs as Nodes)**:
  - `knowledge_subagent`: 专职 IT 知识库检索与排障反思子图（绑定 `search_knowledge`，底层直通双路召回与 Neo4j 因果检索）；
  - `ticket_subagent`: 专职个人工单状态查询与带外草稿拟定子图（绑定 `query_my_tickets` 与 `prepare_ticket`）。
- **终审收敛 (Formulator Node)**: 将多源子图事实汇聚为符合 Java 契约的严格 6 键结构化 JSON 与 `ticketDraft`。

**Tech Stack:** Python 3.14, LangGraph, LangChain Core, Pydantic, Pytest.

---

## 任务拆解与执行清单

### Task 1: 核心安全护栏组件 (`guardrails.py` 与单元测试)

- [ ] **Step 1: 编写失败的单元测试 (`tests/test_guardrails.py`)**
  - 覆盖 Prompt 越狱注入攻击检测（`check_prompt_injection`）
  - 覆盖手机号（11位）、身份证（18位）、银行卡等 PII 双向脱敏与还原（`mask_pii_data` / `unmask_pii_data`）
- [ ] **Step 2: 实现 `services/python-retrieval/agent_service/guardrails.py`**
  - 定义 `GuardrailsSecurityEngine`
  - 包含典型注入正则模式与 PII 正则占位符 Vault 提取/还原
- [ ] **Step 3: 运行测试确保 100% 通过**
  - `pytest services/python-retrieval/agent_service/tests/test_guardrails.py`

---

### Task 2: 垂直领域 Subagent 子图构建 (`subagents/`)

- [ ] **Step 1: 编写子图契约与单元测试 (`tests/test_subagents.py`)**
  - 测试 `knowledge_subagent` 在给定问题时调 `search_knowledge` 并产出 `knowledge_evidence` 与版本列表
  - 测试 `ticket_subagent` 在给定工单诉求时调 `query_my_tickets` / `prepare_ticket` 并产出草稿
- [ ] **Step 2: 实现 `services/python-retrieval/agent_service/subagents/knowledge_subagent.py`**
  - 独立 LangGraph 子图：专职排障提示词 + `search_knowledge` 工具循环
- [ ] **Step 3: 实现 `services/python-retrieval/agent_service/subagents/ticket_subagent.py`**
  - 独立 LangGraph 子图：专职事实核验与草稿提示词 + `query_my_tickets` 与 `prepare_ticket`
- [ ] **Step 4: 运行测试确保子图独立运行通过**
  - `pytest services/python-retrieval/agent_service/tests/test_subagents.py`

---

### Task 3: Supervisor 主管调度中心与终审节点 (`supervisor.py`)

- [ ] **Step 1: 编写 Supervisor 路由与终审逻辑测试**
  - 单一知识问题路由至 `CALL_KNOWLEDGE`
  - 单一工单问题路由至 `CALL_TICKET`
  - 复合问题在排障后由 Supervisor 派发工单，最终收敛至 `FINISH`
  - `formulator_node` 严格组装 6 键结构与草稿
- [ ] **Step 2: 实现 `services/python-retrieval/agent_service/supervisor.py`**
  - 定义 Supervisor 意图分析、动态条件边判定与汇总节点

---

### Task 4: 总控状态图装配与端到端回归 (`graph.py` 与 `agent.py`)

- [ ] **Step 1: 在 `graph.py` 中编排完整拓扑**
  - 连线：`START -> guard_input -> supervisor -> [knowledge_worker / ticket_worker] -> supervisor -> formulator -> guard_output -> END`
- [ ] **Step 2: 更新 `agent.py`（AgentRunner）适配主从编排**
  - 接入全生命周期 Langfuse 审计与 Session Vault 闭环
- [ ] **Step 3: 执行端到端测试与回归套件**
  - `pytest services/python-retrieval/agent_service/tests/`
