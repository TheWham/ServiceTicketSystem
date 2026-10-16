# 企业非结构化数据治理 → RAG 检索基座工程 Demo 集

> 📌 **工程定位**：覆盖企业 RAG 数据工程的完整链路——从三大高频非结构化格式（PDF/Word/Excel）的专项治理，到知识库清洗与 Wiki 重构，再到父子切块、向量化入库与混合检索调优的可运行对照实验工程。核心链路已封装为 **`rag_pipeline` 包**，切片/检索参数由 **`configs/pipeline.yaml`** 统一配置。

---

## 📂 工程目录结构

```text
demos/
├── rag_pipeline/                     # ★ RAG 全链路包（核心，可复用，供接入正式项目）
│   ├── config.py                     # 配置加载 + 指纹 + 路径常量 + 切块器工厂（build_chunker）
│   ├── ingestion/                    # 04 清洗生成：clean_pipeline / llm_synthesizer / wiki_generator
│   ├── chunking/                     # parent_child（父子切片）/ structure_aware（对照）/ fingerprint
│   ├── embedding.py                  # KspEmbeddingProvider（qwen3-embedding-8b，磁盘缓存）
│   ├── store.py                      # Chroma 入库管理（全量重建 + manifest 构建指纹）
│   ├── retrieval/                    # tokenizer / reranker（双后端）/ query_rewriter（查询改写）/ hybrid（双路+RRF+精排+共振保护+拒答）
│   ├── evaluation/                   # suite（评测题集：主题/开发/测试）/ report（报告生成）
│   └── pipelines/
│       ├── indexing.py               # 索引构建主流水线
│       └── evaluation.py             # 检索评测主流水线
│
├── configs/
│   └── pipeline.yaml                 # ★ 配置中心：切片规则/模型/检索参数（唯一真源）
│
├── tools/                            # 工具/诊断脚本（直连 rag_pipeline，可独立运行）
│   ├── adversarial_benchmark.py      # 版本冲突对抗压测（验证元数据过滤屏蔽废止卡）
│   ├── dump_chunks.py                # 导出全部子块到 chunk_preview.md 供人工审阅
│   ├── ingest_vector_store.py        # 独立向量库批量入库脚本（可复用）
│   ├── inspect_chroma.py             # Chroma 向量库内容查看/检索小工具
│   ├── trace_retrieval.py            # 检索轨迹追踪工具
│   ├── test_rerank_stability.py      # Reranker 打分稳定性压测（绝对分漂移 vs 名次稳定）
│   ├── probe_rerank_zero.py          # 复现 /rerank 间歇全 0 现象的探针
│   ├── probe_reranker.py             # 重排服务验收探针（换供应商先跑它）
│   └── dump_retrieval_log.py         # 检索全流程日志落盘（5 环节，供汇报翻看）
│
├── day11_demos/                      # 【Day 11】三大格式专项治理 + Wiki 重构 Demo
│   ├── run_all_demos.py              # 一键串行运行 3 大格式专项 Demo
│   ├── 01_pdf_governance/            # Demo 1: PDF 文件专项治理
│   ├── 02_docx_governance/           # Demo 2: Word 文件专项治理
│   ├── 03_excel_governance/          # Demo 3: Excel 文件专项治理
│   └── 04_wiki_pipeline/             # Demo 4: 知识库清洗 + Wiki 生成（实现在 rag_pipeline/ingestion/）
│
├── docs/                             # 讲义与讲稿
│   ├── 武汉柯莱特企培_Day12_...讲义.md
│   ├── 武汉柯莱特企培_Day13_...讲义.md
│   └── 汇报讲稿_RAG检索链路实战.md
│
├── artifacts/                        # ★ 运行产物（output / indexing / evaluation 归档于此）
│   ├── output/                       # 清洗产物：cleaned/ + wiki/（35 张 ITKB 卡片）
│   ├── indexing/                     # 建库产物：向量库（含 manifest 指纹）+ 评测报告
│   └── evaluation/                   # 评测产物：评测报告 + 详细召回过程报告
│
├── IT常见问题RAG知识库.docx           # 源数据：IT 常见问题原始 Word 文档
├── .env.example                      # KSP 配置模板（脱敏；复制为根目录 .env 并填真实 key）
├── README.md                         # 工程说明（本文档）
└── CLAUDE.md                         # 工程约定说明
```

---

## ⚙️ 配置中心（configs/pipeline.yaml）

改一个文件，全链路生效。覆盖的旋钮：

| 分组 | 关键参数 | 说明 |
| :--- | :--- | :--- |
| `chunking` | `strategy` | `parent_child`（父子切片）/ `structure_aware`（对照） |
| | `child_size` | 子块字符预算（默认 512，含上下文头） |
| | `section_header_level` | 语义边界标题级别（2=`##`） |
| | `merge_preamble` / `strip_trace_tail` | 前言并入首节 / 剔除溯源尾模板行 |
| | `boost_injection` | 检索增强词注入范围：`first`（仅首块）/ `all` / `none` |
| | `breadcrumb_header` | 【卡片：标题 > 小节】面包屑开关 |
| `embedding` / `reranker` | `model` | 可被环境变量 `EMBED_MODEL` / `RERANK_MODEL` 覆盖 |
| `retrieval` | `top_k` / `rough_top_k` / `rrf_k` / `fuse_k` / `rrf_weight` / `rerank_weight` / `gate_*`（置信度门控） | 检索与融合参数 |
| | `rerank_granularity` | 精排粒度：`parent`（子块召回后对整卡全文打分）/ `child`（逐子块） |
| | `query_rewrite` / `rewrite_model` | 查询改写开关 + 改写模型（LLM 删猜测+补术语） |
| | `reject_threshold` | 低置信拒答阈值（候选最高原始 rerank 分低于此值返回空；null 不启用） |
| `reranker` | `backend` | 双后端限定：`dashscope`（仅走 KSP 网关时生效，直连供应商忽略） |
| | `default_exclude` | 主链路默认物理屏蔽（如 `wiki_status: [已废止]`） |

**同步机制**：Day12 与 Day13 经 `build_chunker(config)` 共用同一切块器实例化路径；Day12 建库时在 `manifest.json` 落 `config_fingerprint`，Day13 加载前比对——改 YAML 任何切片参数，旧库自动判失效并重建内存索引，杜绝"两处参数各改一处"的静默错配。

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

**产出**：`artifacts/output/wiki/` 35 张高纯度 Wiki 知识卡片。

---

### Day 12 — 父子切块工程 与 Embedding 向量化调优

**目标**：把 Wiki 卡片切成"小而不碎、语义自包含"的匹配单元，向量化入 Chroma 库，并注入 frontmatter 元数据支持过滤。

- **父子切片（Small-to-Big，`chunking/parent_child.py`）**：
  - **H2 语义边界分节**：以"现象描述/常见根因/员工自助排查/IT工程师进阶处理"小节为原子单位，节内行累加到预算，不切断行、不跨节混切（防止多跳事实链被拦腰斩断）；
  - **前言并入首节 + 溯源尾剔除**：消灭过薄碎块（170→132 块）；
  - **差异化上下文头**：每块注入【卡片：标题 > 小节】面包屑；检索增强词（04 萃取的 keywords/entities）只挂每卡首块——BM25 词面命中与 Dense 向量纯度兼得；
  - 命中子块经 `expand_to_parents` 回溯父块全文（匹配用小、回答用整）。
- **Embedding**：KSP OpenAI 兼容端点 `qwen3-embedding-8b`（4096 维），磁盘缓存复用，失败自动降级 hash 兜底。
- **A/B 对照**：父子切片库 vs 朴素切块库，5 道 IT 业务对抗题评测 Top-3 命中率。
- **元数据前置过滤 + manifest 指纹**：`wiki_category` 等字段注入支持硬过滤；建库落 `config_fingerprint` 供 Day13 语料一致性校验。

**产出**：`artifacts/indexing/chroma_wiki_structured/`（含 manifest）+ `chroma_naive/`（对照）+ 评测报告 + `chunk_preview.md`（切块人工审阅）。

> 🛠️ 配套讲义：`docs/武汉柯莱特企培_Day12_Chunking分块策略工程与Embedding向量化调优讲义.md`

---

### Day 13 — 混合检索机制 与 Rerank 重排优化

**目标**：在向量库之上构建双路召回 + 融合 + 精排的工业级检索链路，根治纯向量检索对专有编号的盲区。

- **双路召回（`retrieval/hybrid.py`）**：BM25 关键词倒排索引（术语归一化红利）+ Dense 向量语义检索。
- **RRF 融合**：Reciprocal Rank Fusion（k=60）倒数排名融合，无需调参即可化解异构打分冲突。
- **Cross-Encoder 精排**：KSP `qwen3-reranker-8b`（`/rerank` 接口），按秩加权融合（召回侧托底，免疫远程分数漂移）；融合权重经**置信度动态门控**按每次精排打分分布切换（高置信放权精排翻盘 / 低置信与启发式降级时召回侧托底），阈值在本端点标定（`pipeline.yaml` 的 `gate_*`）。
- **双后端修复**：KSP 网关随机分流 Jina/DashScope 两后端（旧代码只认 Jina，DashScope 响应被静默补 0），现双格式解析 + 并发对冲只收 dashscope 高质量打分。
- **查询改写**：LLM 删去用户对原因的猜测、补规范术语，原查询+改写查询四路 RRF 召回。
- **父块精排**：子块只负责召回，按父块（整卡）去重后对整卡全文精排，返回 Top-K 张卡。
- **低置信拒答**：候选最高原始 rerank 分 < `reject_threshold`（0.40）时返回空，库外问题不再硬塞答案。
- **Top-1/Top-2 双路共振保护**：召回两路都认可的父块不被精排单点踢出 Top-K。
- **默认屏蔽废止卡**：`default_exclude` 把对抗压测结论固化进主链路。
- **四轨对比评测**：纯向量 vs 纯 BM25 vs RRF 融合 vs 全链路(+Rerank)，**主题集 20 道**（7 硬匹配 + 3 同义改写 + 4 近邻混淆 + 6 库外负样本）+ 开发集 19 道 + 封存测试集 26 道。
- **卡级指标口径**：目标卡 Recall@3 / MRR / 事实覆盖（限目标卡内计数）/ 负样本误召回——替代旧的子串覆盖率（高频词误命中导致四轨全 100% 的饱和口径）。

**产出**：`artifacts/evaluation/混合检索与Rerank重排评测报告.md` + `对抗题详细召回过程.md`（含 🛡 保护标记）。

---

## 🚀 快速执行命令

### Day 11 三大格式专项（可一键全跑）
```bash
python day11_demos/run_all_demos.py
```
或单独运行某一专项（需 cd 到子目录）：
```bash
cd day11_demos/01_pdf_governance && python run_demo.py
```

### Day 11 · Wiki 清洗重构（依赖 KSP API）
```bash
cd day11_demos/04_wiki_pipeline && python run_demo.py   # 全流程
python run_demo.py --offline                            # 离线规则兜底
python run_demo.py --limit 3                            # 调试前 N 条
```

### Day 12 · 切块 + 向量化入库
```bash
python -m rag_pipeline.pipelines.indexing
python tools/dump_chunks.py                             # 导出切块结果人工审阅
```

### Day 13 · 混合检索 + Rerank 评测
```bash
python -m rag_pipeline.pipelines.evaluation              # 主题集（默认）
python -m rag_pipeline.pipelines.evaluation --suite dev  # 开发集
python -m rag_pipeline.pipelines.evaluation --suite test # 封存测试集（定稿后只跑一次）
python -m rag_pipeline.pipelines.evaluation --verbose    # 每题打印检索全流程日志
python tools/adversarial_benchmark.py                    # 版本冲突对抗压测（可选）
```

### Day 14 · 黄金问题集基准评测（6:2:2 配比 + 四项体检指标）
```bash
python run_day14_pipeline.py                               # 全量跑测 + 体检报告落盘
python run_day14_pipeline.py --top-k 5                     # 调整召回深度
python run_day14_pipeline.py --adversarial-threshold 0.5   # 覆盖拒答阈值（默认自动标定）
```
黄金数据集真源：`evals/golden_dataset_v1.0.json`（12 标准 + 4 冲突/跨文档 + 4 越界拒答）；
体检报告落盘 `artifacts/evaluation/Day14_黄金问题集RAG评测基准报告.md`。

### 辅助工具
```bash
python tools/probe_reranker.py                           # 重排验收探针（换供应商先跑它）
python tools/ingest_vector_store.py                      # 独立批量入库
python tools/inspect_chroma.py                           # 查看向量库内容
python tools/inspect_chroma.py --query "VPN报错806" --k 5   # 检索测试
python tools/probe_rerank_zero.py --ids HC-04 HC-07 --n 10   # 复现 rerank 全 0 现象
python tools/dump_retrieval_log.py --ids HC-01 HC-10     # 检索全流程日志落盘
```

---

## ⚙️ 环境依赖

```bash
pip install PyMuPDF pdfplumber Pillow python-docx pandas openpyxl openai \
            pyyaml langchain-text-splitters langchain-community chromadb jieba rank_bm25
```

三类模型各自独立配置（根目录 `.env`，已被 `.gitignore` 忽略，勿入库）——可自由切换不同供应商、互不影响：
```ini
# LLM（对话/清洗）
LLM_API_KEY=sk-...
LLM_BASE_URL=https://<你的接入点>/v1
LLM_CHAT_MODEL=kimi-k3
LLM_CLEAN_MODEL=deepseek-v4-flash

# Embedding（向量化）
EMBED_API_KEY=sk-...
EMBED_BASE_URL=https://<你的接入点>/v1
EMBED_MODEL=qwen3-embedding-8b

# Rerank（重排）
RERANK_API_KEY=sk-...
RERANK_BASE_URL=https://<你的接入点>/v1
RERANK_MODEL=qwen3-reranker-8b
```

> 说明：`qwen3-embedding-8b` / `qwen3-reranker-8b` 由 KSP 端点提供，密集调用可能触发限流（403），重跑时稍等重试即可，脚本已带降级兜底。

---

## 🔌 接入正式项目

```python
from rag_pipeline.config import load_config, build_chunker
from rag_pipeline.pipelines.indexing import run_indexing      # 建库
from rag_pipeline.pipelines.evaluation import run_evaluation  # 评测
from rag_pipeline.retrieval.hybrid import IndustrialHybridRetriever
from rag_pipeline.chunking.parent_child import expand_to_parents
```
