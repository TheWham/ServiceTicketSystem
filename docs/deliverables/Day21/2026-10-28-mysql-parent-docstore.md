# MySQL 父块文档存储（Docstore）与向量库元数据轻量化改造计划

## 1. 目标与背景

当前父子切片（Small-to-Big）实现中，每个子块的元数据均携带了父块全文（`md["parent_content"] = body`），导致：
1. 向量库 Chroma（`chroma.sqlite3`）与内存中产生数倍的文本数据冗余；
2. 检索返回的 payload 包含重复的大文本，不符合企业级规范。

改造目标：
1. **剥离元数据中的父块全文**：子块仅保留 `parent_id` 及其必要轻量标量字段（`child_id`, `Header_1`, `Header_2`, `wiki_*`），不再向向量库写入 `parent_content`。
2. **使用 MySQL 作为 Docstore**：引入 `BaseDocstore` 抽象与 `MySqlDocstore` 实现，将父块正文持久化存储在 MySQL 的 `rag_parent_docstore` 表中。
3. **检索与装配链路适配**：
   - 在混合检索 Step 2.5（父块精排）时，按 `parent_ids` 批量从 Docstore 获取父块正文参与 Cross-Encoder 精排；
   - 在服务装配映射层（`mapping.py`），通过命中结果携带的 `parent_content` 或 Docstore 批量解析父块全文，确保对外契约交付的 `content` 仍为整卡全文；
   - 索引构建流水线（`indexing.py`）同步将父块写入 MySQL，并重新构建干净的向量数据库。

---

## 2. 架构设计与文件变更

### 2.1 新增/修改模块职责划分

1. **`services/python-retrieval/rag_pipeline/docstore.py` (新增)**:
   - 定义 `BaseDocstore` 抽象基类：`get(parent_id)`、`mget(parent_ids)`、`save_documents(docs)`；
   - 实现 `MySqlDocstore`：连接 `it_ticket_system`，通过 `rag_parent_docstore` 表管理父块，支持批量获取与 upsert，带连接池/重连保护；
   - 实现 `InMemoryDocstore`：内存键值存储，供单元测试和无外部 DB 环境使用；
   - 工厂函数 `build_docstore(cfg)`：根据配置装配对应实现。

2. **`services/python-retrieval/rag_pipeline/chunking/parent_child.py` (修改)**:
   - `ParentChildChunker._emit`：移除 `md["parent_content"] = body`，保留 `parent_id`；
   - `expand_to_parents(items, docstore=None)`：支持传入 `docstore`，通过 `docstore.mget(parent_ids)` 回溯父块全文。

3. **`services/python-retrieval/rag_pipeline/retrieval/hybrid.py` (修改)**:
   - `IndustrialHybridRetriever` 支持注入 `docstore`；
   - 在父块精排阶段（`rerank_granularity == "parent"`），通过 `self.docstore.mget` 批量获取父块正文进行精排；
   - 组装 `scored_docs` 时将解析出的父块正文挂载在 `item["parent_content"]`，避免后续重复查询。

4. **`services/python-retrieval/rag_service/mapping.py` (修改)**:
   - `build_response` 获取 `content` 的优先级更新为：`it.get("parent_content")` -> `md.get("parent_content")` -> `(docstore.get(pid) if docstore else None)` -> `it.get("content")`。

5. **`services/python-retrieval/rag_service/assembly.py` (修改)**:
   - 在单例装配体初始化时构造 `self.docstore`，传入 `IndustrialHybridRetriever` 与 `build_response`。

6. **`services/python-retrieval/rag_pipeline/pipelines/indexing.py` (修改)**:
   - 索引构建流程中，将切分产生的 `parent_docs` 保存到 `docstore`；
   - 将轻量化（无 `parent_content`）的 `structured_chunks` 入库 Chroma。

7. **`services/python-retrieval/configs/pipeline.yaml` (修改)**:
   - 增加 `docstore` 配置段，默认启用 `mysql`。

---

## 3. 详细实施步骤 (Tasks)

- [ ] **Task 1: 实现 Docstore 模块与单元测试**
  - 创建 `services/python-retrieval/rag_pipeline/docstore.py`；
  - 编写 `test_docstore.py` 验证 `InMemoryDocstore` 与 `MySqlDocstore` 的 CRUD、批量查询、异常处理。

- [ ] **Task 2: 切块逻辑轻量化与回溯逻辑解耦**
  - 修改 `rag_pipeline/chunking/parent_child.py`，移除 `_emit` 中的 `parent_content`；
  - 改造 `expand_to_parents` 支持 `docstore` 回溯。

- [ ] **Task 3: 混合检索器与服务映射装配适配**
  - 修改 `rag_pipeline/retrieval/hybrid.py` 支持 `docstore` 父块精排与结果挂载；
  - 修改 `rag_service/mapping.py` 与 `rag_service/assembly.py` 对齐 `docstore` 装配。

- [ ] **Task 4: 配置与索引构建流水线改造**
  - 更新 `configs/pipeline.yaml`；
  - 修改 `rag_pipeline/pipelines/indexing.py`，执行全量索引重建；
  - 验证 MySQL `rag_parent_docstore` 表数据入库，验证 Chroma 库中 `parent_content` 彻底消失。

- [ ] **Task 5: 全链路回归测试与契约验证**
  - 运行 `pytest services/python-retrieval/rag_service/tests`；
  - 运行真实端到端检索验证，确保对外输出的 `content` 与 `snippet` 符合规范。
