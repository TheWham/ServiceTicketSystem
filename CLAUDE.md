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

## 04_wiki_pipeline（IT 知识库清洗 + Wiki 生成）

两层架构：`clean_pipeline.py`（L1 规则物理清洗：保序解析 docx → 剔除分隔线/空段、2 列字段表摊平为结构化字段、按 H2 切条目）→ `llm_synthesizer.py`（双模型：deepseek-v4-flash 做语义级正文清洗，kimi-k3 做 frontmatter 元数据萃取，均有磁盘缓存 `output/.llm_cache/` 与规则兜底）→ `wiki_generator.py`（YAML frontmatter + 分节正文 + 溯源 → `output/wiki/`）。

- LLM 配置：OpenAI 兼容协议，`base_url` 通过环境变量 `KSP_BASE_URL` 或根目录 `.env` 提供（内网地址不入库）；key 只从环境变量 `KSP_API_KEY` 或根目录 `.env`（已被 .gitignore 忽略）读取。模型可用 `KSP_CHAT_MODEL`/`KSP_CLEAN_MODEL` 覆盖。
- kimi-k3 不接受 temperature 参数（只允许 1），调用时勿传。
- 输入文档《IT常见问题RAG知识库.docx》结构固定：35 个 H2 条目（32 个带【XXX-NNN】代码 + 3 个附录），每条 4 行 2 列字段表；改动文档结构需同步检查 `clean_pipeline.py` 的 `FIELD_LABEL_RE` 与 `ENTRY_CODE_RE`。
- Windows 控制台为 GBK，入口脚本必须 `sys.stdout.reconfigure(encoding="utf-8")` 否则 emoji 打印崩溃。

依赖（无 requirements.txt，需手动安装）：

```bash
pip install PyMuPDF pdfplumber Pillow python-docx pandas openpyxl openai
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
