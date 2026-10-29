# 轻量级 GraphRAG 拓扑图谱与多跳推理落地实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 针对 IT Ticket 系统 38 篇 Wiki 知识卡片构建轻量级 GraphRAG 拓扑图谱，打通基于 Pydantic Schema 的受控三元组离线抽取、NetworkX 内存图多跳遍历、与 MySQL Docstore 父卡全文的双轨融合推理，并产出多跳基准对比评测报告。

**Architecture:** 
1. **抽取层**：通过 Pydantic 严格模式锁定 8 类核心业务关系谓词，以卡片 Frontmatter 实体池与原文逐字佐证（Quote Grounding）作为约束模具，通过 DeepSeek 批量抽取并持久化缓存至 JSON。
2. **图引擎层**：基于 Python `networkx.MultiDiGraph` 构建内存多重有向拓扑图，实现 1~2 Hop 双向 BFS 子图遍历与 `replaces` 废止卡片物理剪枝。
3. **双轨融合层**：提取出的显式因果链与 MySQL `rag_parent_docstore` 批量主键回溯的父卡正文拼入混合 Prompt，由大模型完成精准多跳逻辑演绎。
4. **评测层**：针对跨卡连环故障、版本废止冲突、跨系统派单依赖构建多跳测试用例，执行「纯向量 vs GraphRAG」对照跑测，输出量化报告。

**Tech Stack:** Python 3.14, NetworkX, Pydantic v2, DeepSeek-v4-flash (OpenAI-compatible SDK), MySQL Docstore, Pytest

**Spec:** `day22/武汉柯莱特企培_Day22_轻量GraphRAG攻坚：实体三元组抽取与网状关联推理讲义.md` 及 `docs/RAG架构演进与GraphRAG核心问答讲解手册.md`

## Global Constraints

- 遵循 `AGENTS.md` 规范：保留工作区未提交修改，严禁覆盖 `day22/` 等外部文件。
- 遵循单一职责与零冗余：不引入 Neo4j 等外部重型数据库，纯 Python 原生内存图处理。
- 零静默回退：抽取失败或字段缺失显式记录，三元组原文佐证无法对齐时坚决拦截丢弃。
- 离线建图与在线检索严格解耦：抽取只发生于离线阶段，在线多跳遍历必须在 1 毫秒内完成。

## Review Focus

1. **关系谓词防漂移**：大模型不得生成预设 8 类 Enum 之外的自造关系谓词。
2. **虚构幻觉拦截**：抽取三元组必须携带 `evidence_quote`，若原句不在文档中必须坚决丢弃。
3. **同义词消歧对齐**：`AD域`、`域控` 等别名进入 NetworkX 前必须被归一化为单一标准节点。
4. **版本废止剪枝**：指向 `DEPRECATED` 废弃卡片的边在子图检索时必须被硬屏蔽。
5. **双轨融合完整度**：图谱提取到的关联合同父卡必须全量触发 MySQL Docstore `mget` 批量回溯。

---

### Task 1: 依赖安装与 Pydantic 严格模式三元组 Schema 体系

**Files:**
- Create: `services/python-retrieval/rag_pipeline/graph/__init__.py`
- Create: `services/python-retrieval/rag_pipeline/graph/schema.py`
- Test: `services/python-retrieval/rag_pipeline/graph/tests/test_schema.py`

- [ ] **Step 1: 安装 networkx 依赖**
  - 执行 `pip install networkx`
  - 验证 `python -c "import networkx as nx; print(nx.__version__)"`
- [ ] **Step 2: 编写测试用例 `test_schema.py`**
  - 测试枚举约束：非法关系输入引发 `ValidationError`
  - 测试长句与标点拦截：包含逗号/句号的长句实体被拒绝
  - 测试别名规范化映射：`AD域` 自动归一化为 `AD域控制器`
- [ ] **Step 3: 实现 `schema.py`**
  - 定义 `ITRelationEnum`（8 类受控业务关系：诱发根因、衍生次生故障、前置排查动作、处置动作、依赖网络通道、依赖身份源、主责运维组、出差代签人、废止并替代、生效状态）
  - 定义 `GroundedTriple` 模型（含 `head`, `relation`, `tail`, `evidence_quote`）
  - 实现 `ENTITY_ALIAS_MAP` 字典与 `canonicalize_entity(name)` 函数
- [ ] **Step 4: 运行单元测试**
  - 运行 `pytest services/python-retrieval/rag_pipeline/graph/tests/test_schema.py` 确保 100% 通过
- [ ] **Step 5: Git Commit**
  - `git add services/python-retrieval/rag_pipeline/graph/`
  - `git commit -m "feat(graph): 引入 networkx 与 Pydantic 严格模式三元组 Schema"`

---

### Task 2: 知识卡片全量离线抽取器与缓存持久化引擎

**Files:**
- Create: `services/python-retrieval/rag_pipeline/graph/extractor.py`
- Test: `services/python-retrieval/rag_pipeline/graph/tests/test_extractor.py`

- [ ] **Step 1: 编写抽取器测试 `test_extractor.py`**
  - 构造 Mock 卡片文本，验证从 Frontmatter 提取 `entities` 并组装 Prompt
  - 验证 `evidence_quote in card_text` 严格校验逻辑：原句匹配成功保留，不匹配丢弃
  - 验证本地缓存读写：缓存文件存在时跳过重复 LLM 请求
- [ ] **Step 2: 实现 `extractor.py`**
  - 读取 `artifacts/output/wiki/*.md` 全部 38 篇卡片
  - 解析卡片 YAML frontmatter（`id`, `title`, `entities`, `replaces`）
  - 利用卡片自带的 `entities` 候选池与规则组装严格 Prompt，调用 `deepseek-v4-flash`
  - 批量持久化到 `services/python-retrieval/artifacts/indexing/knowledge_graph_triples.json`
- [ ] **Step 3: 运行全量 38 篇卡片离线抽取**
  - 执行抽取脚本并生成缓存文件，统计抽取出的实体与三元组总数，打印日志
- [ ] **Step 4: 运行测试并提交**
  - 运行 `pytest services/python-retrieval/rag_pipeline/graph/tests/test_extractor.py`
  - `git commit -m "feat(graph): 实现基于卡片实体候选池与原文佐证校验的三元组抽取器"`

---

### Task 3: NetworkX 内存图拓扑引擎与废止剪枝算法

**Files:**
- Create: `services/python-retrieval/rag_pipeline/graph/engine.py`
- Test: `services/python-retrieval/rag_pipeline/graph/tests/test_engine.py`

- [ ] **Step 1: 编写图引擎测试 `test_engine.py`**
  - 验证三元组添加入图与节点度数统计
  - 验证从种子实体触发的 1-Hop / 2-Hop BFS 广度优先子图遍历
  - 验证废止剪枝：指向 `DEPRECATED` 状态的旧卡片边在遍历时被硬过滤
- [ ] **Step 2: 实现 `engine.py`**
  - `LightKnowledgeGraph` 类：基于 `nx.MultiDiGraph` 管理节点与关系边
  - `load_from_triples(triples: List[GroundedTriple])`：实体经过 `canonicalize_entity` 后建图
  - `extract_subgraph_facts(seed_entities, max_hops=2)`：支持出边与入边双向探索，输出结构化事实文本
  - `prune_deprecated_edges()`：自动检查 `废止并替代` 关系并剪除失效路径
- [ ] **Step 3: 运行测试并提交**
  - 运行 `pytest services/python-retrieval/rag_pipeline/graph/tests/test_engine.py`
  - `git commit -m "feat(graph): 实现 NetworkX 内存图引擎与拓扑剪枝算法"`

---

### Task 4: 拓扑事实与 MySQL Docstore 双轨融合推理器

**Files:**
- Create: `services/python-retrieval/rag_pipeline/graph/reasoner.py`
- Test: `services/python-retrieval/rag_pipeline/graph/tests/test_reasoner.py`

- [ ] **Step 1: 编写双轨推理测试 `test_reasoner.py`**
  - 模拟多跳问题，验证种子实体识别
  - 验证从图谱关联出的父卡 ID 能够联动调用 `docstore.mget` 批量加载
  - 验证最终组装的 Prompt 结构：包含【因果拓扑事实】与【Docstore 参考正文】两部分
- [ ] **Step 2: 实现 `reasoner.py`**
  - `extract_query_entities(query)`：从用户提问抽取核心实体
  - `retrieve_multihop_context(query, max_hops=2)`：
    - 图谱轨：获取 BFS 子图关联事实
    - 联动轨：从事实中捕获涉及的卡片 ID，批量调用 `docstore.mget`
  - `generate_multihop_answer(query)`：注入双轨上下文，驱动 LLM 输出带证据链的回答
- [ ] **Step 3: 运行测试并提交**
  - 运行 `pytest services/python-retrieval/rag_pipeline/graph/tests/test_reasoner.py`
  - `git commit -m "feat(graph): 打通图谱拓扑事实与 MySQL Docstore 父卡全文双轨推理"`

---

### Task 5: 专属多跳基准用例集与「纯向量 vs GraphRAG」对比盲测

**Files:**
- Create: `services/python-retrieval/evals/multihop_benchmark.json`
- Create: `services/python-retrieval/tools/benchmark_graph_vs_vector.py`
- Output: `services/python-retrieval/artifacts/evaluation/graph_vs_vector_report.md`

- [ ] **Step 1: 构建专属于我们系统的多跳基准集 `multihop_benchmark.json`**
  - 场景 1（跨卡排查链）：VPN 691 认证失败联动域账号锁定与邮件旧密码
  - 场景 2（版本废止治理）：密码多次输错锁定阈值与自动恢复规约（ACC-001 vs LEG）
  - 场景 3（CMDB资产直派）：财务报销系统 502 报错的前置网络通道与主责团队
  - 场景 4（组织流转代签）：重大故障总监休假与代签人流转
- [ ] **Step 2: 编写对照跑测脚本 `benchmark_graph_vs_vector.py`**
  - 分别用「纯向量检索链路（旧）」与「GraphRAG 双轨融合链路（新）」跑测基准集
  - 记录召回切片、事实证据链完整度、推理答复准确率与耗时
- [ ] **Step 3: 执行跑测并生成对比评测报告**
  - 运行脚本，全量输出详细 Markdown 对比报告 `graph_vs_vector_report.md`
- [ ] **Step 4: 运行全量回归测试**
  - 运行 `pytest services/python-retrieval/rag_service/tests` 确保既有 73 个测试完全不被破坏
  - 运行 `pytest services/python-retrieval/rag_pipeline/graph/tests`
- [ ] **Step 5: 最终 Git Commit**
  - `git add services/python-retrieval/`
  - `git commit -m "test(graph): 建立系统专属多跳基准集并完成纯向量 vs GraphRAG 对照评测"`
