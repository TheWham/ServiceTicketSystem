# Neo4j 生产级知识图谱迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## 任务背景与目标

当前系统在 `feature-graph` 分支完成了基于 NetworkX 内存图的 Light GraphRAG 基础链路与评测验证。
为满足生产环境对大规模图数据持久化、高并发检索、因果事实图谱可视化探索（Neo4j Browser）的诉求，遵循用户在 `/grill-me` 讨论中的决议以及 `AGENTS.md` 架构准则（**彻底替换旧实现，不留转发壳或重复业务链路；装配时选择，外部依赖明确报错不静默回退**），将图谱引擎全面迁移至 **Docker 运行的 Neo4j 5 图数据库**。

---

## 架构规格与设计决议

1. **Docker 编排与环境**：
   - 镜像版本：`neo4j:5.26-community`
   - 服务端口：`7474:7474` (HTTP / Neo4j Browser 可视化控制台), `7687:7687` (Bolt 协议连接)
   - 认证配置：`neo4j / neo4j123456`
   - 编排入口：根目录 `docker-compose.neo4j.yml` 与 `it-ticket-cloud/rag-service/docker-compose.yml` 同步提供
   - 持久化：命名卷 `it-ticket-neo4j-data` 和 `it-ticket-neo4j-logs`

2. **Graph Schema (Cypher 建模)**：
   - **实体节点**：`(:Entity {name: string, is_deprecated: boolean, card_id: string})`
     - 建立唯一约束：`CONSTRAINT FOR (e:Entity) REQUIRE e.name IS UNIQUE`
     - 建立索引：`INDEX FOR (e:Entity) ON (e.is_deprecated)`
   - **拓扑关系**：直接映射 `ITRelationEnum`（如 `[:ROOT_CAUSE]`, `[:DEPENDS_ON]`, `[:REPLACES]`, `[:TRIGGERED_BY]`, `[:BELONGS_TO]`, `[:STATUS_IS]` 等）
     - 关系属性：`quote: string`（原文字符级证据）, `source_card_id: string`

3. **Cypher 原生拓扑遍历与剪枝**：
   - 1~2 跳广度优先遍历与因果事实生成：
     ```cypher
     MATCH path = (seed:Entity)-[r*1..2]-(target:Entity)
     WHERE seed.name IN $seeds
       AND NONE(n IN nodes(path)[1..] WHERE n.is_deprecated = true AND n <> last(nodes(path)))
     UNWIND relationships(path) AS rel
     RETURN DISTINCT
       startNode(rel).name AS source,
       type(rel) AS relation,
       endNode(rel).name AS target,
       rel.quote AS quote
     ```
   - 废止卡片与实体识别：
     - 若三元组为 `(A)-[:REPLACES]->(B)`，置 `B.is_deprecated = true`
     - 若三元组为 `(A)-[:STATUS_IS]->(废弃/废止)`，置 `A.is_deprecated = true`

4. **数据同步与初始化**：
   - 编写 `sync_triples_to_neo4j.py` 脚本，将已有 596 条三元组以 `UNWIND ... MERGE` 幂等灌入 Neo4j。

5. **调用方与测试全面迁移**：
   - 彻底删除 `networkx` 在图引擎中的代码，`engine.py` 实现 `Neo4jKnowledgeGraph`。
   - 同步迁移 `reasoner.py`、`test_engine.py`、`test_reasoner.py`、`benchmark_graph_vs_vector.py`、`run_compare_ui.py`。
   - `compare_workbench.html` 增加一键直达 Neo4j 可视化 Browser 导航与 Cypher 示例。

---

## 实施任务清单

### Task 1: Docker 编排与 Neo4j 服务部署

- [ ] 在项目根目录创建 `docker-compose.neo4j.yml`
- [ ] 在 `it-ticket-cloud/rag-service/docker-compose.yml` 中追加 `neo4j` 服务定义
- [ ] 在 `services/python-retrieval/.env` 与 `.env.example` 中补充 Neo4j 连接配置 (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`)
- [ ] 启动 Docker Neo4j 容器 (`docker compose -f docker-compose.neo4j.yml up -d`)
- [ ] 验证 Neo4j 容器健康状态及 7474/7687 端口可访问性

### Task 2: 安装 Python Neo4j Driver 并重构 `engine.py` 为 `Neo4jKnowledgeGraph`

- [ ] 安装 `neo4j` Python 客户端驱动 (`python -m pip install neo4j`)
- [ ] 重写 `services/python-retrieval/rag_pipeline/graph/engine.py`：
  - 实现 `Neo4jKnowledgeGraph`，管理 Neo4j Driver 连接生命周期
  - 实现 Schema 唯一约束与索引自愈建立
  - 实现 `add_triple` 与 `load_from_triples`（利用 Cypher `MERGE`）
  - 实现 `has_node` 快速探测
  - 实现 `extract_subgraph_facts`（Cypher 变长路径匹配 + 拓扑剪枝）
  - 实现 `get_associated_card_ids`（Cypher 关联节点提取有效卡片 ID）
  - 严格遵守 `AGENTS.md`：连接失败直接抛出显式异常，不静默回退
- [ ] 彻底清理 `networkx` 依赖与相关代码

### Task 3: 编写并运行全量三元组幂等同步工具

- [ ] 编写 `services/python-retrieval/tools/sync_triples_to_neo4j.py`：
  - 从 `artifacts/indexing/knowledge_graph_triples.json` 读取 596 条三元组
  - 批量执行 Cypher `UNWIND` 幂等写入
  - 自动打标 `is_deprecated = true`
  - 打印同步节点数、边数与废止实体统计
- [ ] 运行脚本将 596 条数据全量写入 Neo4j
- [ ] 验证数据在 Neo4j 中的完整性（Cypher 校验节点与关系数量）

### Task 4: 迁移调用方、测试套件与评测基准

- [ ] 调整 `services/python-retrieval/rag_pipeline/graph/reasoner.py` 适配 `Neo4jKnowledgeGraph`
- [ ] 迁移 `rag_pipeline/graph/tests/test_engine.py`：全量适配 Neo4j 数据库测试
- [ ] 迁移 `rag_pipeline/graph/tests/test_reasoner.py`：验证双轨推理在 Neo4j 下的行为
- [ ] 迁移 `tools/benchmark_graph_vs_vector.py`：适配 Neo4j 并重新跑通 4 大多跳问答基准
- [ ] 运行 pytest 确保所有图谱测试与检索测试 100% 通过

### Task 5: Web 对比实验工作台配套升级与 Neo4j 可视化联动

- [ ] 调整 `services/python-retrieval/tools/run_compare_ui.py`：连接 Neo4j 引擎
- [ ] 优化 `services/python-retrieval/tools/compare_workbench.html`：
  - 添加 Neo4j 运行状态徽章与一键直跳 `http://localhost:7474`（Neo4j Browser）链接
  - 增加常见场景的 Cypher 查询 Recipe（如查询错误代码 691 拓扑、查询废弃替代链路等）
- [ ] 重启并在后台保持 `run_compare_ui.py` (端口 8350)
- [ ] 验证页面交互、实时推理与 Neo4j 状态展示正常

### Task 6: 提交与验收

- [ ] 验证全量测试套件
- [ ] 遵循 `AGENTS.md` 规则，仅提交本任务相关改动，保留工作区既有未提交文件
- [ ] 交付说明与 Neo4j Browser 可视化操作指南
