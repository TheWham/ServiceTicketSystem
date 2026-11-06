# 个人核心研发成果与交付履约白皮书
### —— 从垂直 RAG 检索到多智能体生产总装（Day 11 ~ Day 29 实战成果清单）

---

## 📌 报告元数据

| 属性 | 内容说明 |
| :--- | :--- |
| **交付人 / 开发者** | 许迟帅（核心 AI 交付工程师） |
| **所属工程** | 华科智造企业级 IT 服务工单系统与智能客服全链路交付工程 |
| **攻坚周期** | Day 11（RAG 启程） $\to$ Day 29（生产级性能发布与成本治理） |
| **核心技术栈** | Python 3.11+ / FastAPI / LangGraph / Neo4j / FastMCP / Chroma / BM25 / Rerank |
| **交付定位** | 专供向评审专家、技术总监呈报，**证明个人在过去 20 天内的代码产出、技术攻坚与真实落地成效** |

---

## 🗓️ 核心成果时间轴清单：我这 20 天亲手完成了什么？

```
Day 11~15 ──▶ 垂直知识库 RAG：清洗分块 ➔ 双路召回 ➔ Rerank 重排 ➔ 黄金测试集打封
Day 16~20 ──▶ 安全受控 Agent：AST 防注入 ➔ Text2SQL 安全沙箱 ➔ 三位一体 ➔ HITL 派单草案
Day 21~22 ──▶ 高阶图谱推理：Parent-Child ➔ Neo4j 拓扑 ➔ 2-Hop 多跳因果推导 ➔ 因果拓扑白盒可视化
Day 23~26 ──▶ 状态编排中枢：LangGraph 状态图 ➔ Checkpointer 快照 ➔ 原生中断断电秒级恢复
Day 27    ──▶ 工业标准互联：原生 FastMCP Server/Client ➔ 打通 HR/工单外部工具资产
Day 28    ──▶ 协同多智能体：Supervisor-Worker 主从调度 ➔ Guardrails 越狱拦截与 PII 脱敏
Day 29    ──▶ 生产性能与降本：Model Router 动态阶梯选模 (降本42%) ➔ SSE 打字机流式输出
```

---

### 阶段一：垂直知识库 RAG 核心技术攻坚（Day 11 ~ Day 15）

#### 1. 核心代码与产出文件
- 清洗与切块管道：[`clean_pipeline.py`](file:///d:/day12/demos/docs/deliverables/Day11/clean_pipeline.py)
- 向量入库与评测：[`ingest_vector_store.py`](file:///d:/day12/demos/docs/deliverables/Day12/ingest_vector_store.py) \| [`Day12_Chunking与向量化评测报告.md`](file:///d:/day12/demos/docs/deliverables/Day12/Day12_Chunking与向量化评测报告.md)
- 混合检索与重排：[`Day13_混合检索与Rerank重排评测报告.md`](file:///d:/day12/demos/docs/deliverables/Day13/Day13_混合检索与Rerank重排评测报告.md)
- 黄金测试基准库：[`day14_baseline.json`](file:///d:/day12/demos/docs/deliverables/Day14/day14_baseline.json) \| [`Day14_黄金问题集RAG评测基准报告.md`](file:///d:/day12/demos/docs/deliverables/Day14/Day14_黄金问题集RAG评测基准报告.md)
- 全链路封版套件：[`run_day15_pipeline.py`](file:///d:/day12/demos/docs/deliverables/Day15/run_day15_pipeline.py) \| [`Day15_企业垂直知识库全链路跑测与封版交付报告.md`](file:///d:/day12/demos/docs/deliverables/Day15/Day15_企业垂直知识库全链路跑测与封版交付报告.md)

#### 2. 我攻克的核心技术难题与成果
- **解决通用分块上下文割裂**：废弃简单按字数暴力截断的方案，基于 Markdown 标题树层级的结构化分块，完整保留操作步骤上下文；
- **解决专有错误代码漏召回**：针对 `0x0000007B`、`regedit` 等冷僻稀疏词，搭建 **1024 维 Embedding + BM25** 双路召回引擎，使用 **RRF（倒数排名融合）** 算法平衡权重；
- **剔除“字面相似但逻辑无关”脏块**：后置部署 **Cross-Encoder 深度重排模型（Rerank）**，精细打分排除假相关片段；
- **解决模型面对过时条款瞎编**：构建 6:2:2 黄金测试集，加入版本冲突题与拒答陷阱题；
- **实测成果收益**：
  - 越界提问与废止条款拦截率：**100%**；
  - 答案参考来源角标命中率：**100%**；
  - 单次检索平均耗时：**11.7 ms**。

---

### 阶段二：安全受控 Agent、确定性编排与三位一体（Day 16 ~ Day 20）

#### 1. 核心代码与产出文件
- 安全 AST 语法树拦截器：[`AST 级防注入拦截.md`](file:///d:/day12/demos/docs/deliverables/Day16/AST%20级防注入拦截.md) \| [`Day16代码导读.md`](file:///d:/day12/demos/docs/deliverables/Day16/Day16代码导读.md)
- 确定性工作流与执行沙箱：[`run_day17_workflow.py`](file:///d:/day12/demos/docs/deliverables/Day17/run_day17_workflow.py) \| [`四大经典确定性设计模式.md`](file:///d:/day12/demos/docs/deliverables/Day17/四大经典确定性设计模式.md)
- 三位一体与 HITL 人机回环：[`hitl_demo.py`](file:///d:/day12/demos/docs/deliverables/Day18/hitl_demo.py) \| [`run_day18_triad_agent.py`](file:///d:/day12/demos/docs/deliverables/Day18/run_day18_triad_agent.py)
- 混沌测试与降级防线：[`Day20-汇报文档-质量防线全景-降级HITL与黄金集闭环.md`](file:///d:/day12/demos/docs/deliverables/Day20/Day20-汇报文档-质量防线全景-降级HITL与黄金集闭环.md)

#### 2. 我攻克的核心技术难题与成果
- **物理阻断模型越权写库**：编写 Python AST 抽象语法树分析模块，大模型生成的 SQL 必须经由语法树遍历校验，非 SELECT 语句在解析层直接抛出异常切断；
- **Text2SQL 执行安全沙箱**：构建结构化 Schema 动态绑定，严格限定查询字段与分页深度，杜绝慢查询扫表与敏感库越权；
- **解决大模型操作不可归责痛点**：实现“知识库 + 数据库 + API”三位一体协同，落地 **HITL（人机协同）断点机制**。大模型无权直接写库转派工单，只能生成《派单草案》，必须由人工点击放行；
- **高可用容灾兜底**：通过混沌工程模拟向量库故障与超时，接入完整 Fallback 降级通路。

---

### 阶段三：GraphRAG 多跳因果推导与拓扑大屏（Day 21 ~ Day 22）

#### 1. 核心代码与产出文件
- Parent-Child 存储架构：[`2026-10-28-mysql-parent-docstore.md`](file:///d:/day12/demos/docs/deliverables/Day21/2026-10-28-mysql-parent-docstore.md)
- Neo4j 拓扑图谱与问答：[`run_day22_neo4j_graphrag.py`](file:///d:/day12/demos/docs/deliverables/Day22/run_day22_neo4j_graphrag.py) \| [`RAG架构演进与GraphRAG核心问答讲解手册.md`](file:///d:/day12/demos/docs/deliverables/Day22/RAG架构演进与GraphRAG核心问答讲解手册.md)
- 意图路由与前端抽屉：[`2026-10-29-adaptive-graphrag-intent-routing.md`](file:///d:/day12/demos/docs/deliverables/Day22/2026-10-29-adaptive-graphrag-intent-routing.md) \| 推理拓扑白盒可视化

#### 2. 我攻克的核心技术难题与成果
- **解决跨文档隐性因果推导**：传统语义相似度无法解决“表象是 VPN 报错，根因是域控 DNS 欠费”的多跳故障。我将规章实体三元组入库 **Neo4j**，结合意图路由实现了 **2-Hop 因果多跳推理**；
- **推导过程白盒可视化**：动态输出因果关联拓扑链路，提问时实时渲染出实体关联子图，让 AI 推理逻辑透明可见。

---

### 阶段四：LangGraph 状态编排与 Checkpointer 断电快照恢复（Day 23 ~ Day 26）

#### 1. 核心代码与产出文件
- 状态图架构设计：[`企业级 Agent 开发全流程(1).md`](file:///d:/day12/demos/docs/deliverables/Day23-25/企业级%20Agent%20开发全流程(1).md) \| [`2026-11-02-langgraph-knowledge-precipitation.md`](file:///d:/day12/demos/docs/deliverables/Day23-25/2026-11-02-langgraph-knowledge-precipitation.md)
- HITL 状态机与持久化快照：[`run_day26_langgraph_hitl_2.py`](file:///d:/day12/demos/docs/deliverables/Day26/run_day26_langgraph_hitl_2.py) \| [`基于LangGraph的知识库沉淀与Checkpointer持久化设计.md`](file:///d:/day12/demos/docs/deliverables/Day26/基于LangGraph的知识库沉淀与Checkpointer持久化设计.md)

#### 2. 我攻克的核心技术难题与成果
- **杜绝死循环与状态丢失**：用 LangGraph 有向无环图取代脆弱的 ReAct 循环；
- **生产级故障断电恢复**：引入 **持久化 Checkpointer 快照**，在关键节点执行原生 `interrupt()` 挂起。实测服务端强杀重启后，传入 Session ID 即可秒级从快照恢复，**状态 100% 还原，零数据丢失**；
- **支持 Time-Travel 时光机调试**：支持对历史状态打补丁并局部重放验证。

---

### 阶段五：Anthropic FastMCP 工业标准互联落地（Day 27）

#### 1. 核心代码与产出文件
- FastMCP 协议服务与客户端：[`run_day27_enterprise_finance_mcp.py`](file:///d:/day12/demos/docs/deliverables/Day27/run_day27_enterprise_finance_mcp.py) \| [`run_day27_it_mcp_client.py`](file:///d:/day12/demos/docs/deliverables/Day27/run_day27_it_mcp_client.py) \| [`run_day27_it_ticket_mcp.py`](file:///d:/day12/demos/docs/deliverables/Day27/run_day27_it_ticket_mcp.py)
- 协议规格与验证报告：[`2026-11-03-it-ticket-mcp-server-design.md`](file:///d:/day12/demos/docs/deliverables/Day27/2026-11-03-it-ticket-mcp-server-design.md) \| [`mcp_verification_report.md`](file:///d:/day12/demos/docs/deliverables/Day27/mcp_verification_report.md)

#### 2. 我攻克的核心技术难题与成果
- **打破外部工具硬编码绑定**：基于原生 Python 实现了轻量级 FastMCP 规范，将工单数据与企业 HR 系统包装为标准化 MCP 工具端点；
- **工具生态无缝对接**：完成 MCP Client 与 OpenAI 工具适配器的双向握手，使底层工具能够零耦合支持多模型客户端。

---

### 阶段六：Supervisor-Worker 多智能体与双向安全护栏（Day 28）

#### 1. 核心代码与产出文件
- Supervisor 调度中枢与多子图：[`run_day28_supervisor_guardrails.py`](file:///d:/day12/demos/docs/deliverables/Day28/run_day28_supervisor_guardrails.py) \| [`run_it_supervisor_guardrails_demo.py`](file:///d:/day12/demos/docs/deliverables/Day28/run_it_supervisor_guardrails_demo.py)
- 全链路审计套件：[`run_end_to_end_audit.py`](file:///d:/day12/demos/docs/deliverables/Day28/run_end_to_end_audit.py) \| [`2026-11-03-langgraph-subagent-guardrails.md`](file:///d:/day12/demos/docs/deliverables/Day28/2026-11-03-langgraph-subagent-guardrails.md)

#### 2. 我攻克的核心技术难题与成果
- **多专家智能体分工**：构建 Supervisor 智能路由中枢，独立调度 KnowledgeWorker（规章检索专家）与 TicketWorker（工单办理专家）；
- **构筑双向安全护栏（Guardrails）**：
  - **输入拦截**：命中越狱注入（如“忽略之前指令/我是管理员”）直接 0 Token 403 阻断；
  - **输出脱敏**：出库前对手机号、身份证号、银行卡号自动正则掩码。

---

### 阶段七：生产性能发布、成本治理与近 1 个月历史回放（Day 29）

#### 1. 核心代码与产出文件
- 成本治理与选模：[`cost_governance.py`](file:///d:/day12/demos/docs/deliverables/Day29/cost_governance.py) \| [`run_cost_governance_web_demo.py`](file:///d:/day12/demos/docs/deliverables/Day29/run_cost_governance_web_demo.py)
- 测试验证脚本：[`test_demo_endpoints.py`](file:///d:/day12/demos/docs/deliverables/Day29/test_demo_endpoints.py)
- 时序架构拓扑图：[`mermaid-diagram3.svg`](file:///d:/day12/demos/docs/deliverables/Day29/mermaid-diagram3.svg)
- 会话抽屉与思考回放：主干最新提交（支持近 1 个月历史会话抽屉、随时开启新咨询与深度思考过程全量持久化回放）

#### 2. 我攻克的核心技术难题与成果
- **Model Router 动态阶梯选模**：复杂推导走高阶模型，常规问答路由至极速 Flash 模型，杜绝杀鸡用牛刀，综合成本实测下降 **42.3%**；
- **FastAPI SSE 流式高并发**：实现打字机流式输出并广播思考阶段，TTFT 首字时间压缩在 **380ms** 以内；
- **全景会话治理**：支持随时新开会话、历史会话全量查看回放以及深度思考过程持久化还原。

---

## 📈 交付成果指标对照表（我带来的量化成效）

| 指标维度 | 优化前状态（常见开源/基线水平） | 经我重构优化后的生产指标 | 核心归因手段 |
| :--- | :---: | :---: | :--- |
| **知识库忠实度** | 0.68（频繁断章取义） | **`0.94`** | 标题树切块 + 向量/BM25 双路 + Cross-Encoder 重排 |
| **专有代码召回率** | 52%（错误代码常漏召回） | **`98.5%`** | BM25 关键词增强 + RRF 倒数排名融合算法 |
| **Prompt 越狱拦截率** | 0%（无防护，易套取数据） | **`100.0%`** | Guardrails 输入安全护栏（1.2ms 阻断，0 Token） |
| **黄金测试集检索延迟** | 180 ms | **`11.7 ms` (极速召回)** | 1024 维向量 + BM25 倒排索引双路检索打封 |
| **API 调用 Token 开销** | 每次调用均计费 | **综合开销立降 `42.3%`** | Model Router 意图阶梯动态选模分流 |
| **单点宕机状态丢失率** | 100%（内存状态重启全失） | **`0%` (100% 秒级还原)** | LangGraph Checkpointer 持久化快照序列化机制 |
| **复杂隐性故障诊断** | 仅单点浅层匹配（误诊率高） | **2-Hop 因果多跳推导** | Neo4j 图谱三元组拓扑推理 + 因果拓扑白盒可视化 |

---

## 🎖️ 总结：作为交付工程师（FDE）的综合价值

在过去 20 天的连续攻坚中，我所交付的绝不是孤立分散的代码片段，而是**一套高可用、受业务规则严密控制、高性价比的企业级 AI 生产系统**。

1. **筑牢了安全底线**：用 AST 树与 Guardrails 护栏，守死了大模型不能越权写库、不能泄露数据的铁律；
2. **打磨了算法精度**：用混合检索、Rerank 与 Neo4j 图谱，解决了大模型在企业垂直场景下的胡言乱语；
3. **落实了降本增效**：用 Model Router 意图阶梯选模，让企业真正享受大模型红利的同时，账单开销削减了 40% 以上；
4. **守住了工程闭环**：用 LangGraph 原生中断与 Checkpointer，让关键审批始终有人类兜底、让每一次中断都有快照可恢复。

这份成绩单有据可查、有码可验，具备极高的商业成熟度与投产可行性！
