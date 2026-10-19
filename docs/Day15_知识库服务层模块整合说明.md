# Day15 知识库服务层模块整合说明

> 📌 **一句话定位**：在 `rag_pipeline` 检索基座（Day13 混合检索 + Day14 黄金集评测保护体系）之上，把知识库封装成可对外服务的企业级问答微服务（顶层独立 `day15/` 目录），并提供结构化溯源与防幻觉拒答。

---

## 一、模块定位与上下游

- **上游**：`run_day14_pipeline.py` 建立的评测保护体系（`IndustrialHybridRetriever` 混合检索、`default_exclude` 废止卡屏蔽、低置信拒答、置信度动态门控）。
- **本层职责**：把检索能力封装成 HTTP 问答服务——接收入参 → 检索 → 触发拒答 → 受约束生成（grounding）→ 返回带溯源角标的答案。
- **下游**：前端页面、企业微信/钉钉机器人、第 4 周要接的业务 Agent。

```
IT常见问题RAG知识库.docx
  → rag_pipeline.ingestion（清洗/Wiki）
  → rag_pipeline.chunking（父子切片）
  → artifacts/indexing/chroma_wiki_structured（Chroma + manifest 指纹）
  → rag_pipeline.retrieval.hybrid（BM25+Dense+RRF+Cross-Encoder）
  → 【day15/ 服务层】FastAPI 问答 + 溯源角标   ← 本模块
  → 前端 / 机器人 / 业务 Agent
```

---

## 二、目录结构（预期，待落地确认）

`day15/` 为**顶层独立目录**，不混入 `rag_pipeline/`，保持服务层与检索内核解耦：

```
day15/
├── service.py               # EnterpriseKnowledgeService：拼装检索器 + grounding + Citation
├── api.py                   # FastAPI app：/api/v1/knowledge/chat、/health、/docs
├── schemas.py               # Citation / 请求响应模型
├── prompts.py               # STRICT_GROUNDING_PROMPT 防幻觉模板
└── run_day15_pipeline.py    # 全量黄金集回归 + 报告落盘
```

【待回填：day15/ 落地后的真实文件清单】

---

## 三、核心类与方法（设计意图，落地后回填真实签名）

- **`EnterpriseKnowledgeService.answer(query, top_k=3, metadata_filter=None)`**
  - 内部调用 `rag_pipeline.retrieval.hybrid.IndustrialHybridRetriever.hybrid_rerank_search(...)` 取得父卡级 Top-K 结果；
  - 依据检索置信度触发**诚实拒答**："抱歉，当前知识库中未记载相关内容，建议咨询相关主管部门"；
  - 将命中切片填入 `STRICT_GROUNDING_PROMPT` 生成答案，并抽取 `Citation` 列表。
- **`Citation`**：字段至少包含 `chunk_id` / `source_file` / `section`（面包屑章节）/ `snippet` / `relevance_score`；回答正文中关键结论后紧跟 `[来源: 卡片id - 章节名]` 角标。
- **`STRICT_GROUNDING_PROMPT`**：三大军规——严格事实绑定（只依据参考片段）、诚实拒答（未记载则明说）、精准溯源（结论带角标）。
- **HTTP 端点**：
  - `POST /api/v1/knowledge/chat`：主问答接口，入参 `query/top_k/metadata_filter`，返回 `answer/is_refused/citations/latency_ms`；
  - `GET /health`：健康检查；
  - `/docs`：FastAPI 自带 Swagger 交互文档。

---

## 四、与主链路的一致性契约（低耦合）

服务层**不复制**检索参数与切块逻辑，必须通过同一条装配路径消费既有配置：

- 配置唯一真源：`configs/pipeline.yaml`（服务层禁止内置第二套检索参数）；
- 装配入口：`rag_pipeline.config.load_config` → `build_chunker(config)` → `KspEmbeddingProvider` → `IndustrialHybridRetriever`（含 `default_exclude` 废止卡屏蔽与 `gate_*` 置信度门控）；
- 关键检索参数沿用：`top_k=3`、`rough_top_k=15`、`rrf_k=60`、`fuse_k=10`、`rrf_weight=0.6`/`rerank_weight=0.4`、`rerank_granularity=parent`、`query_rewrite=true`；
- 拒答阈值口径见《Day15 封版交付报告》第五节：配置 `0.40` 与 Day14 实测自动标定 `0.6018` 的关系，服务层最终采用：【待回填：服务层落地后确认】。

---

## 五、快速运行命令（占位，待回填）

```bash
# 全量黄金集回归（跑测 + 报告落盘）
python day15/run_day15_pipeline.py                 # 【待回填：真实入口与参数】

# 启动 HTTP 服务（Swagger 调试）
python day15/run_day15_pipeline.py --serve --port 8000   # 【待回填】
```

启动前确保 `.env` 已配置 `LLM_*`（生成答案）与 `EMBED_*`/`RERANK_*`（检索）。

---

## 六、与讲义 / 桌面样例的域差异说明

- 培训讲义中出现的「集团员工差旅报销管理规约」仅作 Day12 讲义中切块/frontmatter 的**教学示例**；桌面参考样例的「华科智造差旅与财务合规知识库」属外部演示口径。
- 本工程全链路真实语料是《IT 常见问题 RAG 知识库》（35 张 ITKB 卡片），Day15 服务层承载的是**企业 IT 服务台问答**场景。
- 所有指标以 `evals/golden_dataset_v1.0.json` + `artifacts/evaluation/Day14_黄金问题集RAG评测基准报告.md` 的真实跑测为准；桌面样例报告中的「100% 达标 / 11.7ms」为硬编码自打分，不作为本仓库依据。

---

## 七、现状与待办

- ⏳ `day15/` 代码落地中（见上方占位结构）。
- ⏳ 落地后跑一次全量回测，回填《Day15_企业知识库服务层封版交付报告》1.2 / 2.2 / 三.3 / 四节。
- ⏳ 鉴权（API-Key 依赖注入 + 按 `wiki_category` 的可见域过滤）与结构化 `Citation` 角标联调。
- ✅ 检索层底座（Day11~Day14）已完成并留档，可作为服务层验收证据链。
