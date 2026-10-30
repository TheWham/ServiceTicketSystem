# 自适应 GraphRAG 意图分流与动态实体路由实施方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建智能 IT 客服的自适应 GraphRAG 检索路由内核，实现轻量 LLM 一次性完成意图判别（单维事实 vs 关系多维）与自然语言实体抽取，彻底废除硬编码词表并对齐 Neo4j 动态节点池，将图谱因果推导透明融合进检索切片，在保证 Java 客服契约与 MySQL 发布版本复核零破坏的前提下实现高精度故障排查。

**Architecture:** 
采用 Adaptive RAG 路由架构，检索内核（Python `rag_service`）作为统一入口。请求进入后先由 `AdaptiveQueryRouter` 进行快速 LLM 语义分析（单次解析），单维查询走纯 IndustrialHybridRetriever（Dense + BM25）极速返回；多维关系查询提取实体并与 Neo4j 动态节点池对齐，执行 Cypher 多跳因果拓扑推导，推导结论与证据链结构化前置注入至真实卡片切片中，直接对齐现有 Java `RagServiceKnowledgeRetriever` 契约与 `FOR SHARE NOWAIT` 数据库发布校验。

**Tech Stack:** 
FastAPI, Neo4j (Cypher Bolt), Chroma / BM25, LangChain / OpenAI Client, Pydantic, pytest.

**Spec:** `docs/superpowers/specs/2026-09-30-rag-consultation-composition-design.md`

## Global Constraints

- **契约稳定性**：`POST /api/v1/rag/retrievals` 的对外响应契约（`RagRetrievalResponse`）与字段（camelCase）保持 100% 镜像对齐，不得增删破坏 Java 侧 DTO 解析。
- **发布版本真实性**：图谱注入的所有知识必须归属于真实有效的 `articleId` 和 `versionId`，禁止伪造不存在于 MySQL 知识库中的切片或文章，确保 Java 端 `FOR SHARE NOWAIT` 事务校验通过。
- **超时预算收敛**：Java 客户端检索总超时为 4.2s。LLM 意图路由严格限制单次超时 ≤ 1.5s（`max_retries=0`），若超时或故障优雅回落至纯双路召回，不阻断主链路。
- **杜绝硬编码技术债**：彻底废除 `COMMON_ENTITY_TERMS` 静态词表，所有图谱实体基于 Neo4j 实时存储动态加载与匹配。

## Review Focus

- **LLM 分类器超时/异常容错**：当外部模型网关返回 500/429 或超过 1.5s 时，能否无损回落至纯向量+BM25 检索，而不会导致 500 级崩溃。
- **动态实体链接精确度**：口语化提问提取出的实体（如“手机邮箱报错”）能否准确模糊映射到 Neo4j 的真实节点（如“移动端邮件客户端旧密码轮询”）。
- **粗粒度 Hub 实体抑制**：自适应提取在存在具体故障码（如 691）时，是否仍然严格抑制“VPN”、“网络”等泛化中心节点。
- **切片注入上下文长度与格式**：注入的前缀因果链是否符合 Java 消费端的 snippet 截断规则（≤1000 字符）与 Markdown 结构。
- **单维查询性能零损耗**：对于非图谱查询，确认不执行任何 Neo4j 拓扑查询与图推理，仅消耗极短的判定耗时。

---

### Task 1: 废除硬编码词表并实现 Neo4j 动态节点池对齐

**Files:**
- Modify: `services/python-retrieval/rag_pipeline/graph/engine.py:30-80`
- Modify: `services/python-retrieval/rag_pipeline/graph/reasoner.py:18-80`
- Test: `services/python-retrieval/rag_pipeline/graph/tests/test_dynamic_entity_extraction.py`

- [x] **Step 1.1: 编写动态节点池与实体对齐的单测**
  创建 `test_dynamic_entity_extraction.py`，验证：
  1. `Neo4jKnowledgeGraph.get_all_node_names()` 能返回内存缓存的真实节点集合；
  2. `extract_query_entities(query, candidate_nodes=...)` 在不依赖任何静态全局硬编码词表的情况下，仅依据传入的动态节点池正确识别实体并剔除泛化粗粒度节点；
  3. 确认未传候选池时能安全回落至图数据库直读或空集。
- [x] **Step 1.2: 在 Neo4jKnowledgeGraph 中实现节点名缓存接口**
  在 `Neo4jKnowledgeGraph` 中新增 `get_all_node_names(refresh: bool = False) -> Set[str]`：
  - 启动后初次执行 `MATCH (n) RETURN DISTINCT n.name AS name` 并缓存在 `self._cached_node_names`；
  - 遇到 Neo4j 未连接时优雅降级为空集合，不阻断进程。
- [x] **Step 1.3: 重构 reasoner.py 移除 COMMON_ENTITY_TERMS**
  - 删除 `COMMON_ENTITY_TERMS` 静态常量；
  - 重写 `extract_query_entities` 函数签名：`def extract_query_entities(query: str, candidate_nodes: Optional[Set[str]] = None, kg: Optional[Neo4jKnowledgeGraph] = None) -> List[str]`；
  - 优先使用 `candidate_nodes`，若无则尝试 `kg.get_all_node_names()`；
  - 保持长词优先匹配逻辑和 `GENERIC_COARSE_TERMS` 剪枝策略。
- [x] **Step 1.4: 运行单测并验证现有图谱测试套件**
  运行 `pytest services/python-retrieval/rag_pipeline/graph/tests -v`，确保 18 项既有测试及新增测试 100% 通过。

---

### Task 2: 实现轻量 LLM 自适应意图与实体分析器 (AdaptiveQueryRouter)

**Files:**
- Create: `services/python-retrieval/rag_pipeline/graph/router.py`
- Test: `services/python-retrieval/rag_pipeline/graph/tests/test_router.py`

- [x] **Step 2.1: 编写 AdaptiveQueryRouter 的单元测试与边界 Mock**
  创建 `test_router.py`，测试覆盖：
  1. 单维事实提问（如“公司WiFi密码”、“Outlook设置”）Mock 返回 `intent='SINGLE_DIMENSION'`, `needs_graph=False`；
  2. 复合因果提问（如“VPN 691 + 手机邮箱失效”）Mock 返回 `intent='MULTI_HOP_RELATIONAL'`, `needs_graph=True`，且包含动态提取的实体短语；
  3. LLM 超时（TimeoutError）或返回非法 JSON 时，验证鲁棒性：自动安全回退为 `needs_graph=False`，同时从文本基础提取关键字，不抛出未捕获异常。
- [x] **Step 2.2: 实现 AdaptiveQueryRouter 核心逻辑**
  创建 `services/python-retrieval/rag_pipeline/graph/router.py`：
  - 使用 Pydantic 定义 `QueryIntent` (`SINGLE_DIMENSION`, `MULTI_HOP_RELATIONAL`) 和 `IntentAnalysisResult` (`intent`, `needs_graph`, `extracted_entities: List[str]`, `reason: str`)；
  - 复用 `load_llm_config()` 配置的 OpenAI 兼容客户端；
  - 严格限制单次调用超时为 1.5s，`max_retries=0`；
  - 设计专注的 System Prompt 与 Few-Shot 指引：指导大模型区分“单点功能/SOP/文档查阅”与“跨系统联动/异常报错/多因推导”；
  - 实现可选的磁盘 SHA1 缓存（与 `QueryRewriter` 一致，避免同类提问重复消耗延迟）。
- [x] **Step 2.3: 运行 Router 单测确保通过**
  运行 `pytest services/python-retrieval/rag_pipeline/graph/tests/test_router.py -v`。

---

### Task 3: 检索内核自适应装配与图谱推导无损融合

**Files:**
- Modify: `services/python-retrieval/rag_service/assembly.py:75-195`
- Modify: `services/python-retrieval/rag_service/mapping.py:35-85`
- Test: `services/python-retrieval/rag_service/tests/test_adaptive_retrieval.py`

- [x] **Step 3.1: 编写检索内核自适应分流集成测试**
  创建 `test_adaptive_retrieval.py`，校验：
  1. 单维度输入时，确保检索结果不包含 `【知识图谱因果推导】` 前缀，执行速度快，且结果结构合规；
  2. 多维度输入时，图谱推理生效，Top-1 切片正文前置注入结构化推导事实，且 `articleId`、`versionId` 均为真实 ID；
  3. 接口数据包完全符合 Java 契约（包含 `chunkId`, `title`, `score`, `indexVersion` 等非空校验）。
- [x] **Step 3.2: 在 ServiceAssembly 中装配图谱与自适应路由组件**
  - 在 `ServiceAssembly.__init__` 中初始化 `Neo4jKnowledgeGraph`、`GraphReasoner` 与 `AdaptiveQueryRouter`；
  - 在 `search(req)` 中先调用 `router.analyze(req.question)` 评估意图；
  - 若 `needs_graph=True`：
    - 将 `extracted_entities` 与 Neo4j 动态节点池对齐；
    - 执行 `reasoner.reason(entities)` 产出 `reasoning_res`（包含 diagnosis, facts, action_plan）；
    - 传递 `reasoning_res` 给 `build_response`。
- [x] **Step 3.3: 在 mapping.py 中实现因果链无损注入**
  - 在 `build_response` 中接收可选的 `reasoning_res`；
  - 当存在有效的图谱推导结论时，将规范的因果推导块：
    ```markdown
    【知识图谱因果推导】
    • 综合诊断：...
    • 拓扑推导因果链：...
    • 处置建议：...
    ---
    ```
    注入到相关度最高的首条有效切片的 `content` 开头，并同步适度更新 `snippet`；
  - 严格保持切片的 `articleId`、`versionId`、`chunkId` 真实不变，不造假数据。
- [x] **Step 3.4: 运行装配测试验证**
  运行 `pytest services/python-retrieval/rag_service/tests/test_adaptive_retrieval.py -v`。

---

### Task 4: 端到端联调与回归测试验证

**Files:**
- Test: `services/python-retrieval/rag_service/tests/` (全量)
- Test: `services/python-retrieval/rag_pipeline/graph/tests/` (全量)
- Verify: `tools/check_contract.py` (契约校验)

- [x] **Step 4.1: 执行契约检查脚本 check_contract.py**
  运行 `python services/python-retrieval/tools/check_contract.py`，确保对外 HTTP 响应字段 100% 对齐 Java 消费端。
- [x] **Step 4.2: 运行 Python 端全量测试集**
  运行 `pytest services/python-retrieval/rag_service/tests services/python-retrieval/rag_pipeline/graph/tests -v`，确认全部通过。
- [x] **Step 4.3: 启动/重启 rag_service 并进行实际 HTTP 请求验证**
  通过真实 HTTP 调用测试典型提问：
  - 单维提问：“如何修改域账号密码？” -> 验证 0ms 图谱开销，纯双召回；
  - 多维提问：“在家连不上公司VPN提示错误代码691认证失败，同时手机企业邮箱提示凭据失效” -> 验证自适应进入图谱因果链，成功诊断 AD 域锁定。
