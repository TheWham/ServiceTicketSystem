# 企业级 AI 交付工程 (FDE) Day 01 ~ Day 29 核心产出与交付材料总览

> **项目名称**：企业级 IT 服务工单系统与智能客服全链路交付工程  
> **定位标准**：严守「只保留项目实际产出与交付材料（去除教学讲义）」要求，归纳整理 Day 01 至 Day 29 各阶段里程碑成果。  
> **统一归档目录**：`docs/deliverables/`  
> **更新时间**：2026-11-05  

---

## 目录结构大盘

```text
docs/deliverables/
├── README.md                      # 全天次交付物大盘与索引导航
├── Day01/                         # 业务需求规划与 4 栏矩阵 (BRD)
├── Day02-03/                      # 需求工程归因、风险防线与模型算力定盘表
├── Day04/                         # 验收评测协议与四维 SPEC 规格书
├── Day05/                         # 项目上下文协议 (AGENTS.md / CLAUDE.md)
├── Day06-10/                      # 第一阶段 Web 业务全生命周期闭环交付 (PRD / 验收协议 / 契约单测 / 缺陷报告)
├── Day11/                         # 非结构化文档解析清洗管道与格式专项治理策略
├── Day12/                         # Chunking 分块策略工程与 Embedding 向量化调优报告
├── Day13/                         # 混合检索机制与 Rerank 重排模型优化评测报告
├── Day14/                         # 黄金问题集基准库 (Golden Dataset) 与 RAG 评测基准报告
├── Day15/                         # 企业垂直知识库跑测报告与第 3 周结营封版验收签名书
├── Day16/                         # 安全 Text2SQL AST 级防注入拦截与 API 网关代码导读
├── Day17/                         # 确定性工作流编排、状态机控制与 Langfuse APM 追踪实战
├── Day18/                         # 三位一体架构 (知识库+数据库+API) 协同 Agent 与人机回环 (HITL)
├── Day19/                         # 混沌工程故障注入测试与第二阶段实战考核考卷
├── Day20/                         # 第二阶段终极验收：Demo Day 质量防线全景汇报与甲方业务价值讲解词
├── Day21/                         # 高阶检索：MySQL Parent Docstore 架构方案与知识库检索盲测任务书
├── Day22/                         # 轻量 GraphRAG 攻坚：实体三元组抽取、Neo4j 拓扑推理与问答讲解手册
├── Day23-25/                      # 企业级 Agent 开发全流程与 LangGraph 状态图沉淀方案
├── Day26/                         # LangGraph Checkpointer 快照持久化、原生中断与时光机补丁
├── Day27/                         # 工业互联新标准：生产级 FastMCP Server 协议调试与验证交付报告
├── Day28/                         # Supervisor 主从多 Agent 编排、安全护栏与全闭环审计套件
└── Day29/                         # 语义缓存优化、Model Router 成本治理与 Web 演示控制台
```

---

## 阶段明细与交付文档清单

### 一、第一阶段：业务规划、四维 SPEC 与单体业务闭环 (Day 1 ~ Day 10)

| 阶段/天数 | 归档目录 | 交付物文件清单 | 核心成果物说明 |
| :--- | :--- | :--- | :--- |
| **Day 01** | [`Day01/`](file:///d:/day12/demos/docs/deliverables/Day01) | • `BRD业务需求规划_4栏矩阵实操表.md`<br>• `IT服务工单系统-BRD业务需求四栏矩阵.md`<br>• `IT服务工单系统-小组选题四栏表.md` | 业务现状痛点拆解、4 栏功能定义矩阵（业务场景/技术归因/ROI/验收口径） |
| **Day 02-03** | [`Day02-03/`](file:///d:/day12/demos/docs/deliverables/Day02-03) | • `IT服务工单系统-需求归因文档.md`<br>• `IT服务工单系统-技术风险登记册.md`<br>• `it工单系统-Qwen3-4B-算力与基础设施定盘表.md` | 需求归因三棱镜（检索/编排/生成）、技术风险登记与降级防线、静态显存与动态 KV Cache 卡数拓扑速算 |
| **Day 04** | [`Day04/`](file:///d:/day12/demos/docs/deliverables/Day04) | • `IT服务工单系统-验收评测协议书.md`<br>• `技术SPEC规格书.md` | 消除模糊验收指标；输出四维 SPEC（强类型数据模型、OpenAPI 契约、状态转移矩阵、超时降级） |
| **Day 05** | [`Day05/`](file:///d:/day12/demos/docs/deliverables/Day05) | • `AGENTS.md`<br>• `CLAUDE.md` | 系统级上下文协议、代码分层防腐化宪法、Agent 生命周期治理与门禁规则 |
| **Day 06-10** | [`Day06-10/`](file:///d:/day12/demos/docs/deliverables/Day06-10) | • `FDE实训第一阶段Web项目产出方案.md`<br>• `IT服务工单系统PRD-Ultimate.md` (全量 59KB)<br>• `IT服务工单系统-验收评测协议书-V2.md`<br>• `test_contract_alignment.py`<br>• `HITL放行后工单状态未流转-问题报告.md` | 第一阶段 5 天全生命周期成果：Day 6 需求评审 $\to$ Day 7 架构与红灯单测 $\to$ Day 8 全栈跑通 $\to$ Day 9 QA提测与故障注入 $\to$ Day 10 现场答辩 |

---

### 二、第二阶段：企业垂直知识库工程与业务 Agent 全链路 (Day 11 ~ Day 20)

| 阶段/天数 | 归档目录 | 交付物文件清单 | 核心成果物说明 |
| :--- | :--- | :--- | :--- |
| **Day 11** | [`Day11/`](file:///d:/day12/demos/docs/deliverables/Day11) | • `clean_pipeline.py`<br>• `格式专项治理策略.md` | PDF/Word/Excel 非结构化格式专项治理规范、解析清洗管道（对应 38 篇标准 Wiki 资产卡片） |
| **Day 12** | [`Day12/`](file:///d:/day12/demos/docs/deliverables/Day12) | • `Day12_Chunking与向量化评测报告.md`<br>• `ingest_vector_store.py` | 结构化切块 vs 暴力切块对照实验报告、1024 维 Embedding 向量化入库脚本 |
| **Day 13** | [`Day13/`](file:///d:/day12/demos/docs/deliverables/Day13) | • `Day13_混合检索与Rerank重排评测报告.md` | 向量 + BM25 双路召回 + RRF 融合 + Cross-Encoder 重排模型优化对比实验报告 |
| **Day 14** | [`Day14/`](file:///d:/day12/demos/docs/deliverables/Day14) | • `Day14_黄金问题集RAG评测基准报告.md`<br>• `golden_dataset_v1.0.json.bak`<br>• `day14_baseline.json` | 6:2:2 工业级黄金问题集基准库（典型业务题/版本冲突题/拒答陷阱题）与跑测基线量化报告 |
| **Day 15** | [`Day15/`](file:///d:/day12/demos/docs/deliverables/Day15) | • `Day15_企业垂直知识库全链路跑测与封版交付报告.md`<br>• `第二阶段第3周里程碑封版验收签名书.md`<br>• `run_day15_pipeline.py` | 知识库全量跑测（拦截率 100%、溯源角标 100%、时延 11.7ms）与结营封版验收签名书 |
| **Day 16** | [`Day16/`](file:///d:/day12/demos/docs/deliverables/Day16) | • `AST 级防注入拦截.md`<br>• `Day16代码导读.md` | Function Calling 协议解析、安全 Text2SQL AST 树语法只读拦截器与外部 API 网关验证报告 |
| **Day 17** | [`Day17/`](file:///d:/day12/demos/docs/deliverables/Day17) | • `Day 17 生产级确定性工作流与 Langfuse APM 追踪实战脚本.md`<br>• `Day17-汇报讲稿-确定性工作流与链路追踪.md`<br>• `四大经典确定性设计模式.md`<br>• `系统边界划分（System Boundary Separation）.md`<br>• `Agent架构生产实践军规.md`<br>• `run_day17_workflow.py` | 确定性工作流状态机、Trace/Span/Generation APM 链路追踪、时延与成本核算实战报告 |
| **Day 18** | [`Day18/`](file:///d:/day12/demos/docs/deliverables/Day18) | • `Day18-汇报讲稿-RAG模块.md`<br>• `Day18三位一体架构与人机回环实战导读.md`<br>• `hitl_demo.py`<br>• `run_day18_triad_agent.py` | 知识库 + 数据库 + API 三位一体协同、写操作 HITL 中断挂起与凭据恢复演练 |
| **Day 19** | [`Day19/`](file:///d:/day12/demos/docs/deliverables/Day19) | • `第二阶段考题.md`<br>• `LangChain与LlamaIndex核心解构及LCEL编排演进指南.md` | 混沌工程故障注入测试、Fallback 降级规范、第二阶段场景穿刺实战考核试卷 |
| **Day 20** | [`Day20/`](file:///d:/day12/demos/docs/deliverables/Day20) | • `Day20-汇报文档-质量防线全景-降级HITL与黄金集闭环.md`<br>• `Day20-甲方汇报-业务价值讲解词.md` | 第二阶段 Demo Day 答辩与商业级封版大盘：GuardedRagClient 四层隔离壳、拔线降级演练、Bad Case 回流闭环 |

---

### 三、第三阶段：高级 RAG、LangGraph、MCP、多 Agent 协同与高并发服务化 (Day 21 ~ Day 29)

| 阶段/天数 | 归档目录 | 交付物文件清单 | 核心成果物说明 |
| :--- | :--- | :--- | :--- |
| **Day 21** | [`Day21/`](file:///d:/day12/demos/docs/deliverables/Day21) | • `Day21_五大课题知识库检索盲测挑战与代码寻宝任务书.md`<br>• `2026-10-28-mysql-parent-docstore.md` | Parent-Child 大小块切分方案、微观小块召回与宏观大块回溯、MySQL Parent Docstore 存储设计 |
| **Day 22** | [`Day22/`](file:///d:/day12/demos/docs/deliverables/Day22) | • `RAG架构演进与GraphRAG核心问答讲解手册.md`<br>• `run_day22_light_graphrag.py`<br>• `run_day22_neo4j_graphrag.py`<br>• `2026-10-29-adaptive-graphrag-intent-routing.md`<br>• `2026-10-29-neo4j-graphrag-migration.md` | 实体三元组抽取、Neo4j 拓扑关联推导、自适应意图路由与 GraphRAG 核心问答讲解手册 |
| **Day 23-25** | [`Day23-25/`](file:///d:/day12/demos/docs/deliverables/Day23-25) | • `企业级 Agent 开发全流程(1).md`<br>• `2026-11-02-langgraph-knowledge-precipitation.md` | 企业级 Agent 开发全流程白皮书（工具拆解/架构路线/安全防护/评测大盘）、LangGraph 状态图沉淀方案 |
| **Day 26** | [`Day26/`](file:///d:/day12/demos/docs/deliverables/Day26) | • `基于LangGraph的知识库沉淀与Checkpointer持久化设计.md`<br>• `run_day26_langgraph_hitl_2.py` | LangGraph Checkpointer 快照持久化、原生 `interrupt()` 人工终审挂起、Time-Travel 时光机热补丁重放 |
| **Day 27** | [`Day27/`](file:///d:/day12/demos/docs/deliverables/Day27) | • `mcp_verification_report.md`<br>• `mcp_config.json`<br>• `run_day27_enterprise_finance_mcp.py`<br>• `run_day27_it_mcp_client.py`<br>• `run_day27_it_ticket_mcp.py`<br>• `2026-11-03-it-ticket-mcp-server-design.md`<br>• `2026-11-03-it-ticket-mcp-server.md` | Anthropic FastMCP 工业互联规范、三层架构握手报文抓包、生产级 MCP Server 验证交付报告 |
| **Day 28** | [`Day28/`](file:///d:/day12/demos/docs/deliverables/Day28) | • `run_day28_supervisor_guardrails.py`<br>• `run_it_supervisor_guardrails_demo.py`<br>• `run_end_to_end_audit.py`<br>• `2026-11-03-langgraph-subagent-guardrails.md` | Supervisor-Worker 主从协同架构、Prompt 越狱安全护栏、PII 动态脱敏与还原、全生命周期闭环审计套件 |
| **Day 29** | [`Day29/`](file:///d:/day12/demos/docs/deliverables/Day29) | • `cost_governance.py`<br>• `long_task_worker.py`<br>• `run_cost_governance_web_demo.py`<br>• `test_demo_endpoints.py`<br>• `semantic_cache_fastapi_server.py` | 语义缓存（0 Token、50ms 极速响应）、Model Router 动态阶梯选模、Token 预算控制台 Web Demo、SSE 流式打字机输出 |

---

## 交付资产核验汇总

- **纯净性保障**：已彻底剥离各天的教程讲义文件，仅留存实际产出的规格说明书、设计文档、评测报告、基准数据与交付代码套件；
- **全生命周期覆盖**：从 Day 01 需求输入至 Day 29 高并发服务化，各天次交付物环环相扣，具备完整的生产级闭环。
