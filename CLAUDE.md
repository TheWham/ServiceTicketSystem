# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

这是一个教学演示工程：针对非结构化数据预处理中三大高频文件载体（PDF、Word、Excel）的**格式专项治理**对照实验代码集。每个专项是一个可独立运行的 Python Demo，演示"错误/朴素做法 vs 推荐工程做法"的对照。

## 常用命令

一键运行全部 3 个 Demo（串行，任一失败即中断）：

```bash
python run_all_demos.py
```

单独运行某个专项（必须 cd 到子目录运行，脚本依赖相对路径的样本文件）：

```bash
cd 01_pdf_governance && python run_demo.py
```

Demo 4（知识库清洗 + Wiki 生成，依赖外部 LLM API，不挂入 run_all_demos.py）：

```bash
cd 04_wiki_pipeline && python run_demo.py            # 全流程（需 KSP_API_KEY）
python run_demo.py --offline                         # 离线降级（全规则兜底）
python run_demo.py --limit 3                         # 调试前 N 条
```

RAG 链路（切块建库 → 混合检索评测，依赖 Wiki 卡片与 LLM API）：

```bash
python run_day12_pipeline.py   # 切块 + 嵌入 + Chroma 建库（含 manifest 指纹）
python run_day13_pipeline.py   # 四轨检索评测（Dense/BM25/RRF/全链路+Rerank）
python run_day13_pipeline.py --suite dev    # 开发集（可用于调参）
python run_day13_pipeline.py --suite test   # 封存测试集：只在方案定稿后运行一次，结果不得用于回调参数
python probe_reranker.py       # 重排服务验收（可复现性/文末换行扰动/排序）
```

**评测题集纪律**（`rag_pipeline/evaluation/suite.py`）：`HARD_BENCHMARK_SUITE`（主题集）与 `DEV_SUITE`（开发集）用于调参与阈值标定；`TEST_SUITE` 在调参前写好并封存，2026-10-14 定稿后已运行一次（快照 `day13_output/_run10_test_once/`）。若再改检索参数，需另出新测试题，不能拿旧测试集回调。`--reject-threshold` / `--rewrite-model` 可临时覆盖配置做对照实验。

**配置中心 `configs/pipeline.yaml`**：切片规则（策略/child_size/H2 边界/前言合并/溯源剔除/检索增强注入范围/面包屑）、嵌入与重排模型（含 `reranker.backend` 后端限定，见下）、检索参数（top_k/rrf_k/融合权重/精排粒度 rerank_granularity/查询改写 query_rewrite/低置信拒答阈值 reject_threshold/废止卡排除）。Day12 与 Day13 经 `rag_pipeline.config.build_chunker()` 共用同一切块器实例化路径；Day12 建库时在 manifest 落 `config_fingerprint`，Day13 加载前比对——改 YAML 任何切片参数，旧库自动判失效并重建内存索引。

**KSP rerank 双后端**：网关把同名 `qwen3-reranker-8b` 随机分流到 Jina 格式（`{"results":...}`，约 70%，疑似未套 Qwen3 提示模板、对文末空白极敏感、判别力差）与 DashScope 格式（`{"output":{"results":...}}`，约 30%，正常）两种后端。`KspReranker` 默认只接受 dashscope 打分（并发对冲；429 只退避不耗重试预算）；单次请求超过约 1 万字会分批发送（dashscope 后端长请求会截断文档、改变分数）。排查 rerank 分数异常先落盘原始响应看格式。

**当前定稿链路**：KSP `qwen3-reranker-8b`（dashscope）+ 父块精排 + 查询改写（`rag_pipeline/retrieval/query_rewriter.py`，deepseek-v4-flash，原查询+改写查询四路召回、精排用改写查询，缓存在 `day13_output/.llm_cache/rewrite`）+ `reject_threshold: 0.40`。阈值与改写模型、重排模型强绑定，任一更换都要在主题集+开发集上重标。

**重排可独立换供应商**（当前默认走 KSP，`.env` 中 `RERANK_*` 已注释停用；百炼 qwen3.7 免费额度已耗尽，启用前需在控制台关闭"仅使用免费额度"）：`.env` 中配置 `RERANK_BASE_URL` + `RERANK_API_KEY`（+ 可选 `RERANK_MODEL`）后，重排直连该服务（不做双后端限定/对冲），嵌入与 LLM 仍走 KSP；只填地址不填 key 时回落 KSP 并提示。阿里云百炼的 OpenAI 兼容重排在 `/compatible-api/v1/reranks`（不是 Chat 用的 `/compatible-mode/v1`），代码会自动换算并探测端点，模型名为 `qwen3-rerank`（分数与 KSP dashscope 后端逐题一致，阈值 0.37 通用；`qwen3.7-text-rerank` 需改阈值 0.64）。换供应商后先跑 `python probe_reranker.py`（可复现性 + 文末换行扰动 + 排序三项验收），再跑 Day13 评测并按报告重标 `reject_threshold`。

## rag_pipeline 包（RAG 全链路，自 run_day12/13 与 04_wiki_pipeline 抽取整合）

```
rag_pipeline/
├── config.py          # 配置加载 + ChunkingConfig/RetrievalConfig + config_fingerprint + build_chunker
├── ingestion/         # 04 清洗生成三模块（clean_pipeline / llm_synthesizer / wiki_generator）
├── chunking/          # parent_child（父子切片+expand_to_parents）/ structure_aware（结构感知+朴素基线）/ fingerprint
├── embedding.py       # KspEmbeddingProvider + load_ksp_config
├── store.py           # VectorStoreManager（全量重建 + manifest）
├── retrieval/         # tokenizer（分词+纯Python BM25）/ reranker（KSP或直连 /rerank+启发式兜底）/ query_rewriter（LLM 查询改写）/ hybrid（多路+RRF+按秩融合+Top-1/2共振保护+低置信拒答）
├── evaluation/        # suite（Day12 TC + Day13 主题集/开发集/封存测试集）/ report（主报告+详细召回过程）
└── pipelines/         # indexing.py（建库，原 day12）/ evaluation.py（检索评测，原 day13）
```

根目录 `run_day12_pipeline.py` / `run_day13_pipeline.py` 是**薄入口**：转发到包内主流水线并再导出公开 API（`adversarial_benchmark.py`、`dump_chunks.py` 等工具脚本的旧 import 因此无需改动）。`ParentChildChunker(child_size=512)` 旧签名仍兼容，但新代码应传 `config=ChunkingConfig(...)`。

## 04_wiki_pipeline（IT 知识库清洗 + Wiki 生成）

两层架构的实现已迁移至 `rag_pipeline/ingestion/`：`clean_pipeline.py`（L1 规则物理清洗：保序解析 docx → 剔除分隔线/空段、2 列字段表摊平为结构化字段、按 H2 切条目）→ `llm_synthesizer.py`（双模型：deepseek-v4-flash 做语义级正文清洗，kimi-k3 做 frontmatter 元数据萃取，均有磁盘缓存 `output/.llm_cache/` 与规则兜底）→ `wiki_generator.py`（YAML frontmatter + 分节正文 + 溯源 → `output/wiki/`）。`04_wiki_pipeline/run_demo.py` 保留为入口（内部 import 指向 rag_pipeline.ingestion）。

- LLM 配置：OpenAI 兼容协议，`base_url` 通过环境变量 `KSP_BASE_URL` 或根目录 `.env` 提供（内网地址不入库）；key 只从环境变量 `KSP_API_KEY` 或根目录 `.env`（已被 .gitignore 忽略）读取。模型可用 `KSP_CHAT_MODEL`/`KSP_CLEAN_MODEL` 覆盖。
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
