# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

这是一个教学演示工程：针对非结构化数据预处理中三大高频文件载体（PDF、Word、Excel）的**格式专项治理**对照实验代码集。每个专项是一个可独立运行的 Python Demo，演示"错误/朴素做法 vs 推荐工程做法"的对照。

## 常用命令

一键运行全部 3 个 Demo（串行，任一失败即中断）：

```bash
python day11_demos/run_all_demos.py
```

单独运行某个专项（必须 cd 到子目录运行，脚本依赖相对路径的样本文件）：

```bash
cd day11_demos/01_pdf_governance && python run_demo.py
```

Demo 4（知识库清洗 + Wiki 生成，依赖外部 LLM API，不挂入 run_all_demos.py）：

```bash
cd day11_demos/04_wiki_pipeline && python run_demo.py   # 全流程（需 LLM_API_KEY）
python run_demo.py --offline                            # 离线降级（全规则兜底）
python run_demo.py --limit 3                            # 调试前 N 条
```

RAG 链路（切块建库 → 混合检索评测，依赖 Wiki 卡片与 LLM API）：

```bash
python -m rag_pipeline.pipelines.indexing     # 切块 + 嵌入 + Chroma 建库（含 manifest 指纹）
python -m rag_pipeline.pipelines.evaluation   # 四轨检索评测（Dense/BM25/RRF/全链路+Rerank）
```

**配置中心 `configs/pipeline.yaml`**：切片规则（策略/child_size/H2 边界/前言合并/溯源剔除/检索增强注入范围/面包屑）、嵌入与重排模型、检索参数（top_k/rrf_k/融合权重/废止卡排除）。Day12 与 Day13 经 `rag_pipeline.config.build_chunker()` 共用同一切块器实例化路径；Day12 建库时在 manifest 落 `config_fingerprint`，Day13 加载前比对——改 YAML 任何切片参数，旧库自动判失效并重建内存索引。

## rag_pipeline 包（RAG 全链路，自 run_day12/13 与 04_wiki_pipeline 抽取整合）

```
rag_pipeline/
├── config.py          # 配置加载 + ChunkingConfig/RetrievalConfig + config_fingerprint + build_chunker
├── ingestion/         # 04 清洗生成三模块（clean_pipeline / llm_synthesizer / wiki_generator）
├── chunking/          # parent_child（父子切片+expand_to_parents）/ structure_aware（结构感知+朴素基线）/ fingerprint
├── embedding.py       # KspEmbeddingProvider + load_embedding_config
├── store.py           # VectorStoreManager（全量重建 + manifest）
├── retrieval/         # tokenizer（分词+纯Python BM25）/ reranker（KSP /rerank+启发式兜底）/ hybrid（双路+RRF+按秩融合+置信度门控+Top-1/2共振保护）
├── evaluation/        # suite（Day12 TC + Day13 HC/NEG 题集）/ report（主报告+详细召回过程）
└── pipelines/         # indexing.py（建库，原 day12）/ evaluation.py（检索评测，原 day13）
```

主流水线自带 CLI 入口：`python -m rag_pipeline.pipelines.indexing`（建库）与 `python -m rag_pipeline.pipelines.evaluation`（评测），均可通过 API 调用（`from rag_pipeline.pipelines.indexing import run_indexing`）。工具/诊断脚本已归拢到 `tools/`，并**直连 `rag_pipeline.*`**（不依赖薄入口）；`rag_pipeline.config` 提供 `WIKI_DIR`/`INDEXING_OUTPUT`/`EVALUATION_OUTPUT`/`ARTIFACTS_ROOT` 路径常量，运行产物统一归档 `artifacts/`。`ParentChildChunker(child_size=512)` 旧签名仍兼容，但新代码应传 `config=ChunkingConfig(...)`。

## day16（企业级单 Agent 工具交付，已落地）

顶层**独立目录**，与 RAG 检索内核（`rag_pipeline`/`rag_service`）**无耦合**，只复用 `rag_pipeline.config.load_llm_config()` 读 `.env` 模型配置。Text2SQL 直连企业真实业务库 `it_ticket_system`（IT 服务工单系统，MySQL 8）。核心构件：

```
day16/
├── agent.py               # EnterpriseReActAgent：tools schema + ReAct 循环 + 确定性沙箱兜底
├── text2sql.py            # SafeText2SQLEngine：五重门禁只读 SQL 拦截器（连真实库，分号/危险动词/白名单/LIMIT 注入）
├── gateway.py             # ExternalAPIGateway：超时 + 指数退避 + 抖动 + 熔断降级（工单升级协同）
├── prompts.py             # AGENT_SYSTEM_PROMPT（客观第三人称/封闭世界/错误反思三军规）
├── schemas.py             # Pydantic 严格入参契约（pattern/gt/le）+ 对外出参模型
├── api.py                 # FastAPI 演示页 + /api/v1/agent/chat + /health + /tools（端口 8321）
├── config.py              # DAY16_* 环境变量（HOST/PORT/OFFLINE/LLM_TIMEOUT/REPORT_DIR + DAY16_DB_* 真实库连接）
└── run_day16_pipeline.py  # 3 验收用例回归 + 报告落盘 artifacts/day16/；--serve 转发服务
```

实现要点：LLM 经 `load_llm_config()` 装配（默认取 `clean_model`=deepseek-v4-flash，可用 `DAY16_AGENT_MODEL` 覆盖，**不显式传 temperature**）；`SafeText2SQLEngine` 用 pymysql 连 `it_ticket_system`，白名单 = 真实表（`ticket`/`ticket_transition`/`knowledge_article`/`knowledge_version`/`category`/`consultation`…），查询工单故障流程与知识库卡片；未配置 LLM / 断网 / `DAY16_OFFLINE=1` 时走 `_run_deterministic_mock` 确定性沙箱（仍直查真实库，恶意注入 `DROP TABLE` 优先于业务关键词判定，注入语句夹带合法关键词也能正确拦截）；SQL 一律过五重门禁后才 `cursor.execute`，无 LIMIT 自动注入 `LIMIT 50`；回归 3/3 通过（工单查询/恶意 DROP 拦截/知识库卡片查询）。讲义见 `docs/武汉柯莱特企培_Day16_...讲义.md`。

## day11_demos/04_wiki_pipeline（IT 知识库清洗 + Wiki 生成）

两层架构的实现已迁移至 `rag_pipeline/ingestion/`：`clean_pipeline.py`（L1 规则物理清洗：保序解析 docx → 剔除分隔线/空段、2 列字段表摊平为结构化字段、按 H2 切条目）→ `llm_synthesizer.py`（双模型：deepseek-v4-flash 做语义级正文清洗，kimi-k3 做 frontmatter 元数据萃取，均有磁盘缓存 `artifacts/output/.llm_cache/` 与规则兜底）→ `wiki_generator.py`（YAML frontmatter + 分节正文 + 溯源 → `artifacts/output/wiki/`）。`day11_demos/04_wiki_pipeline/run_demo.py` 保留为入口（内部 import 指向 rag_pipeline.ingestion）。

- 三类模型配置：LLM / Embedding / Rerank **各自独立** `base_url` + `key`（环境变量 `LLM_*` / `EMBED_*` / `RERANK_*` 或根目录 `.env`，内网地址不入库、`.env` 已被 .gitignore 忽略）。LLM 的对话/清洗模型可用 `LLM_CHAT_MODEL`/`LLM_CLEAN_MODEL` 覆盖。
- kimi-k3 不接受 temperature 参数（只允许 1），调用时勿传。
- 输入文档《IT常见问题RAG知识库.docx》结构固定：35 个 H2 条目（32 个带【XXX-NNN】代码 + 3 个附录），每条 4 行 2 列字段表；改动文档结构需同步检查 `rag_pipeline/ingestion/clean_pipeline.py` 的 `FIELD_LABEL_RE` 与 `ENTRY_CODE_RE`。
- Windows 控制台为 GBK，入口脚本必须 `sys.stdout.reconfigure(encoding="utf-8")` 否则 emoji 打印崩溃。

依赖（无 requirements.txt，需手动安装）：

```bash
pip install PyMuPDF pdfplumber Pillow python-docx pandas openpyxl openai PyYAML
```

无测试框架、无 lint 配置。验证方式即运行 Demo 观察输出。

## 架构要点

每个专项目录结构相同：`generate_sample_*` 生成仿真样本文件 → `*_governor/parser` 是核心引擎类 → `run_demo.py` 是入口。样本文件（`enterprise_sample.pdf` 等）是生成产物，删除后会被重新生成。

三个核心引擎各自独立的治理策略：

- **PDF（`pdf_governor.py` 的 `PDFGovernanceEngine`）**：先按"字符量 < 30 且有图片"把每页分类为 `VECTOR_TEXT` 或 `SCANNED_IMAGE`。矢量页用 pdfplumber 提表格转 Markdown、用 PyMuPDF 按 block 提正文并用表格包围盒去重（5px 容差判定重叠）。扫描页走图像预处理（灰度→对比度→二值化）→ OCR → 后置纠错词典。**注意：扫描页的 OCR 文本是硬编码的模拟字符串（`raw_ocr_simulation`），并未接真实 OCR 引擎**——这是为演示后置纠错流水线（`10O,00O.OO → 100,000.00`、`人氏币 → 人民币`）而设计的。
- **Word（`docx_stream_parser.py` 的 `DocxGovernanceEngine`）**：对照两种策略——`parse_naive_separated`（分别遍历 paragraphs 和 tables，表格全部坠落到文末）vs `parse_stream_ordered`（遍历 `doc.element.body` 的 `<w:p>`/`<w:tbl>` 子节点保序提取，Heading 样式映射为 Markdown 标题）。
- **Excel（`excel_dual_governor.py` 的 `ExcelDualGovernanceEngine`）**：双轨策略。明细表导入内存 SQLite 走 Text2SQL（中文字段重命名为英文字段后再 `to_sql`，表名 `sales_orders`）；规则表逐行生成"行级自包含切片"（每行绑定全量列名，同时产出 Markdown 和带 metadata 的 JSON 两种形态，供 RAG 召回）。

## 注意事项

- Excel 引擎硬编码依赖样本文件的 sheet 名（`order_sales_details`、`reimbursement_policy`）和中文列名；改动生成器的表结构必须同步改 `rename_map` 与切片字段。
- README.md 中的绝对路径示例（`/Users/lucas/...`）是原始作者机器上的路径，本仓库实际位于 `D:\day12\demos`。
