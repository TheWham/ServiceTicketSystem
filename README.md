# 企业非结构化数据治理 → RAG 检索基座工程 Demo 集

> 📌 **工程定位**：覆盖企业 RAG 数据工程的完整链路——从三大高频非结构化格式（PDF/Word/Excel）的专项治理，到知识库清洗与 Wiki 重构，再到结构感知切块、向量化入库与混合检索调优的可运行对照实验工程。

---

## 📂 工程目录结构

```text
demos/
├── run_all_demos.py                  # 一键串行运行 Day 11 的 3 大格式专项 Demo
├── run_day12_pipeline.py             # Day 12：结构感知切块 + 向量化入库 + A/B 对照评测
├── run_day13_pipeline.py             # Day 13：BM25+Dense 混合检索 + RRF + Rerank 重排评测
├── ingest_vector_store.py            # 独立向量库批量入库脚本（可复用）
├── inspect_chroma.py                 # Chroma 向量库内容查看/检索小工具
│
├── 01_pdf_governance/                # 【Day 11 · Demo 1: PDF 文件专项治理】
│   ├── generate_sample_pdf.py        # 仿真 PDF 生成器（含矢量页与扫描图页）
│   ├── pdf_governor.py               # 核心引擎：页面分类、pdfplumber 表格提取、OCR 预处理纠错
│   ├── run_demo.py                   # 一键运行入口
│   └── enterprise_sample.pdf         # 自动生成的测试样本
│
├── 02_docx_governance/               # 【Day 11 · Demo 2: Word 文件专项治理】
│   ├── generate_sample_docx.py       # 仿真 DOCX 生成器（标题/正文/表格穿插）
│   ├── docx_stream_parser.py         # 核心引擎：朴素分离提取 vs 底层 XML 流式保序提取
│   ├── run_demo.py                   # 一键运行入口
│   └── enterprise_sla.docx           # 自动生成的测试样本
│
├── 03_excel_governance/              # 【Day 11 · Demo 3: Excel 文件专项治理】
│   ├── generate_sample_excel.py      # 仿真 EXCEL 生成器（流水明细表 + 规则对照表）
│   ├── excel_dual_governor.py        # 核心引擎：明细表 Text2SQL + 规则表行级自包含切片
│   ├── run_demo.py                   # 一键运行入口
│   └── enterprise_data.xlsx          # 自动生成的测试样本
│
├── 04_wiki_pipeline/                 # 【Day 11 · Demo 4: 知识库清洗 + Wiki 重构】
│   ├── clean_pipeline.py             # 规则物理清洗：保序解析 docx、字段表摊平、按 H2 切条目
│   ├── llm_synthesizer.py            # 双模型 LLM 治理：正文清洗 + frontmatter 元数据萃取
│   ├── wiki_generator.py             # 生成带 YAML frontmatter 的 Wiki 卡片
│   ├── run_demo.py / run_examples.py # 运行入口
│   └── .env.example                  # KSP 配置模板（脱敏，真实 key 放根目录 .env）
│
├── output/                           # 【Day 11 产物】
│   ├── cleaned/                      # 规则清洗后的结构化条目（.md）
│   ├── wiki/                         # LLM 治理后的 35 张 ITKB Wiki 卡片（含 _index.md）
│   └── example/                      # 三大格式 Demo 的 Wiki 化示例输出
│
├── day12_output/                     # 【Day 12 产物】
│   ├── Day12_Chunking与向量化评测报告.md
│   ├── chroma_wiki_structured/       # 结构感知切块向量库（含元数据注入）
│   ├── chroma_naive/                 # 朴素切块对照向量库
│   └── chroma_db/                    # ingest_vector_store.py 独立入库库
│
├── day13_output/                     # 【Day 13 产物】
│   └── Day13_混合检索与Rerank重排评测报告.md
│
├── IT常见问题RAG知识库.docx           # 源数据：IT 常见问题原始 Word 文档
└── CLAUDE.md                         # 工程约定说明
```

---

## 🗓️ 三天实战内容总览

### Day 11 — 非结构化文档治理 与 Wiki 知识重构

**目标**：把杂乱的原始企业文档（PDF/Word/Excel）治理成干净、结构化、带元数据的知识资产。

| 专项 | 核心治理策略 | 对照实验 |
| :--- | :--- | :--- |
| **PDF** | 页面分类（矢量/扫描）→ pdfplumber 表格转 Markdown + PyMuPDF 正文去重 → OCR 后置纠错词典 | 朴素按行切 vs 结构保序提取 |
| **Word** | 遍历 `doc.element.body` 子 XML 节点保序提取标题/正文/表格 | 朴素分离提取（表格坠落文末）vs 流式保序 |
| **Excel** | 明细表 → SQLite Text2SQL；规则表 → 行级自包含切片 | 直接切词（算术幻觉）vs 确定性 SQL 聚合 |
| **Wiki 重构** | 规则物理清洗 → 双模型 LLM 治理（正文清洗 + frontmatter 萃取）→ Wiki 卡片生成 | 产出 35 张带 YAML frontmatter 的 ITKB 卡片 |

**产出**：`output/wiki/` 35 张高纯度 Wiki 知识卡片。

---

### Day 12 — 结构感知切块工程 与 Embedding 向量化调优

**目标**：把 Wiki 卡片切成"自包含、语义完整"的原子切片，向量化入 Chroma 库，并注入 frontmatter 元数据支持过滤。

- **自适应粒度切块（`run_day12_pipeline.py`）**：
  - 短卡片（≤1000 字符）**整卡原子化**——卡片本身就是原子语义单元，不再按标题切碎（避免跨小节事实分裂，详见讲义 2.3 节反面教材）；
  - 长文档降级为"Markdown 标题树粗切 → 相邻小节合并 → 递归字符微切兜底"。
- **Embedding**：KSP OpenAI 兼容端点 `qwen3-embedding-8b`（4096 维），磁盘缓存复用，失败自动降级 hash 兜底。
- **A/B 对照**：结构感知切块库 vs 朴素切块库，5 道 IT 业务对抗题评测 Top-3 命中率。
- **元数据前置过滤**：`wiki_category` 等字段注入，支持按分类硬过滤。

**产出**：`day12_output/chroma_wiki_structured/`（含元数据）+ `chroma_naive/`（对照）+ 评测报告。

> 🛠️ 配套讲义：`武汉柯莱特企培_Day12_Chunking分块策略工程与Embedding向量化调优讲义.md`

---

### Day 13 — 混合检索机制 与 Rerank 重排优化

**目标**：在向量库之上构建双路召回 + 融合 + 精排的工业级检索链路，根治纯向量检索对专有编号的盲区。

- **双路召回（`run_day13_pipeline.py`）**：BM25 关键词倒排索引（术语归一化红利）+ Dense 向量语义检索。
- **RRF 融合**：Reciprocal Rank Fusion（k=60）倒数排名融合，无需调参即可化解异构打分冲突。
- **Cross-Encoder 精排**：KSP `qwen3-reranker-8b`（`/rerank` 接口），对粗排候选做交叉注意力重排。
- **四轨对比评测**：纯向量 vs 纯 BM25 vs RRF 融合 vs 全链路(+Rerank)，7 道含命令/错误码/端口/跨分类过滤的硬对抗题。

**产出**：`day13_output/Day13_混合检索与Rerank重排评测报告.md`（数据驱动，谁高标谁）。

---

## 🚀 快速执行命令

### Day 11 三大格式专项（可一键全跑）
```bash
python run_all_demos.py
```
或单独运行某一专项（需 cd 到子目录）：
```bash
cd 01_pdf_governance && python run_demo.py
```

### Day 11 · Wiki 清洗重构（依赖 KSP API）
```bash
cd 04_wiki_pipeline && python run_demo.py            # 全流程
python run_demo.py --offline                         # 离线规则兜底
python run_demo.py --limit 3                         # 调试前 N 条
```

### Day 12 · 切块 + 向量化入库
```bash
python run_day12_pipeline.py
```

### Day 13 · 混合检索 + Rerank 评测
```bash
python run_day13_pipeline.py
```

### 辅助工具
```bash
python ingest_vector_store.py                        # 独立批量入库
python inspect_chroma.py                             # 查看向量库内容
python inspect_chroma.py --query "VPN报错806" --k 5   # 检索测试
```

---

## ⚙️ 环境依赖

```bash
pip install PyMuPDF pdfplumber Pillow python-docx pandas openpyxl openai \
            pyyaml langchain-text-splitters langchain-community chromadb jieba rank_bm25
```

KSP API 配置（根目录 `.env`，已被 `.gitignore` 忽略，勿入库）：
```ini
KSP_API_KEY=sk-...
KSP_BASE_URL=https://<你的接入点>/v1
KSP_CHAT_MODEL=kimi-k3
KSP_CLEAN_MODEL=deepseek-v4-flash
```

> 说明：`qwen3-embedding-8b` / `qwen3-reranker-8b` 由 KSP 端点提供，密集调用可能触发限流（403），重跑时稍等重试即可，脚本已带降级兜底。
