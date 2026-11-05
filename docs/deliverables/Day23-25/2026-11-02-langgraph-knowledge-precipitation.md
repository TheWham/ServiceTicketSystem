# 基于 LangGraph 的知识库沉淀流程编排方案设计与实施计划

> **分支**：`rag-langgraph`  
> **服务归属**：`services/python-retrieval/knowledge_flow`  
> **核心原则**：**知识库完全使用 Python 原生模块（Chroma / SimpleVectorStore / Docstore），完全不依赖 Elasticsearch！**

---

## 一、 架构与模块设计

沉淀流程作为生产级编排模块直接嵌入 Python 后端服务，并深度复用现有的 `rag_pipeline` 向量与文档存储能力：

```
services/python-retrieval/
├── rag_pipeline/             # 【已有】Python 检索与向量基础设施
│   ├── store.py              # Chroma / SimpleVectorStore 向量库
│   ├── embedding.py          # KspEmbeddingProvider 向量计算与缓存
│   └── docstore.py           # MySqlDocstore / MemoryDocstore 全文卡片存储
│
└── knowledge_flow/           # 【本次新建】基于 LangGraph 的沉淀中枢
    ├── __init__.py           # 包导出
    ├── contract.py           # StateGraph TypedDict 与 Pydantic DTO
    ├── checkpointer.py       # MySQL / SQLite / Memory 持久化快照抽象
    ├── nodes.py              # 5大纯函数节点（提取、脱敏、向量查重、中断、Python向量库入库）
    ├── engine.py             # LangGraph 组装编排与 Time-Travel 接口
    ├── app.py                # FastAPI 端点（/trigger, /pending, /resume, /history, /patch）
    └── tests/
        └── test_knowledge_flow.py # 端到端测试集
```

---

## 二、 核心五阶段节点编排与数据流

```mermaid
flowchart TD
    START([开始: 接收待沉淀问答/工单候选]) --> Node1[Node 1: ExtractCandidateNode<br>LLM 结构化提取标题/现象/根因/步骤]
    Node1 --> Node2[Node 2: SanitizeGuardNode<br>规则+正则脱敏手机/工号/IP，防注入拦截]
    Node2 --> Node3[Node 3: ClusterDedupNode<br>调用 Python store.py 检索 Chroma 向量余弦相似度查重]
    Node3 --> CondCheck{查重/风险判定}
    CondCheck -- 疑似高度重复 --> NodeReview["Node 4: AdminReviewNode<br>🛑 原生 interrupt() 挂起等待终审"]
    CondCheck -- 正常新知识 --> NodeReview
    
    NodeReview -. 挂起并持久化至 Checkpointer .-> SuspendedState[(MySQL / SQLite 快照存储<br>0 CPU 占用等待管理员)]
    
    SuspendedState -. 外部管理员调用 /resume 注入决议 .-> ResumeSignal[Command(resume=decision)]
    ResumeSignal --> NodeReview
    
    NodeReview --> DecisionCheck{审批决议}
    DecisionCheck -- 审核通过 APPROVED --> NodePublish["Node 5: PublishAndIndexNode<br>调用 Python VectorStoreManager 向量化<br>写入本地 Chroma / Docstore，不依赖 ES"]
    DecisionCheck -- 审核驳回 REJECTED --> NodeReject[退回草稿并归档驳回日志]
    
    NodePublish --> END([流转结束: 正式成为已发布知识])
    NodeReject --> END
```

---

## 三、 Time-Travel（时间旅行）容灾与纠错机制

如果在审核阶段发现前序步骤（例如提取分类填错、或者脱敏多删了核心配置）：
1. 管理员通过 `GET /api/v1/knowledge-flow/history/{thread_id}` 查看全生命周期快照版本链；
2. 管理员通过 `POST /api/v1/knowledge-flow/patch` 传入目标 `checkpoint_id` 与修正数据（如订正 `category_id` 或微调正文）；
3. 系统在修补版本处分叉（Fork），调用 `invoke(None, config=fork_config)` 重新从修补点放行流转，免除废弃重提成本！

---

## 四、 详细任务拆解与交付步骤

### Task 1: 契约与 Checkpointer 快照存储层 (`contract.py` & `checkpointer.py`)
- 定义 `KnowledgeFlowState`（TypedDict），包含状态字段、 Reducer（`audit_logs: Annotated[List[str], operator.add]`）；
- 实现兼容 MySQL 与 SQLite/Memory 的持久化 Checkpointer 抽象，确保任何节点执行完毕自动落盘。

### Task 2: 五大核心计算节点实现 (`nodes.py`)
- `extract_candidate_node`：调用模型提取规范结构；
- `sanitize_guard_node`：执行脱敏与防注入；
- `cluster_dedup_node`：调用 Python `SimpleVectorStore` / Chroma 执行相似度比对；
- `admin_review_node`：按业务条件调用 `interrupt(review_card)` 挂起，支持 `Command(resume=...)` 唤醒；
- `publish_index_node`：**调用 Python `VectorStoreManager` 写入向量库与 Docstore（彻底废弃 ES）**。

### Task 3: 状态图装配与引擎中枢 (`engine.py`)
- 构造 `StateGraph`，添加节点、拓扑边、条件边，compile 编译并注入 Checkpointer；
- 封装 `trigger`、`resume`、`get_state`、`get_state_history` 与 `update_state`（Time-Travel API）。

### Task 4: RESTful API 端点暴露 (`app.py`)
- 实现 `/trigger`、`/pending`、`/resume`、`/history`、`/patch` 接口，支持前后端或自动化工具调用。

### Task 5: 编写测试用例与验证全生命周期 (`tests/test_knowledge_flow.py`)
- 编写端到端自动化测试，覆盖：
  - 常规单据正常通过并落盘到 Python 向量库；
  - 中断挂起与管理员唤醒流转；
  - 断点重启容灾（Checkpointer 状态无损还原）；
  - Time-Travel 时光倒流与状态热修补演练。
