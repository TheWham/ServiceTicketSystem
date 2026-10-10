# Day 11 格式专项治理实战工程 Demo 集

> 📌 **工程定位**：针对非结构化数据预处理中最高频的三大文件载体（PDF、Word、Excel），提供工业界成熟、可直接运行验证的专项治理代码与对照实验工程。

---

## 📂 工程目录结构与策略矩阵

```text
day11/demos/
├── run_all_demos.py                  # 一键串行运行全部 3 大专项 Demo
├── 01_pdf_governance/                # 【Demo 1: PDF 文件专项治理】
│   ├── generate_sample_pdf.py        # 仿真 PDF 生成器（含矢量页与扫描图页）
│   ├── pdf_governor.py               # 核心引擎：页面分类、pdfplumber 表格提取、OCR 预处理纠错
│   ├── run_demo.py                   # 一键运行入口
│   └── enterprise_sample.pdf         # 自动生成的测试样本
├── 02_docx_governance/               # 【Demo 2: Word 文件专项治理】
│   ├── generate_sample_docx.py       # 仿真 DOCX 生成器（标题/正文/表格穿插）
│   ├── docx_stream_parser.py         # 核心引擎：朴素分离提取 vs 底层 XML 流式保序提取
│   ├── run_demo.py                   # 一键运行入口
│   └── enterprise_sla.docx           # 自动生成的测试样本
└── 03_excel_governance/              # 【Demo 3: Excel 文件专项治理】
    ├── generate_sample_excel.py      # 仿真 EXCEL 生成器（流水明细表 + 规则对照表）
    ├── excel_dual_governor.py        # 核心引擎：明细表 Text2SQL + 规则表行级自包含切片
    ├── run_demo.py                   # 一键运行入口
    └── enterprise_data.xlsx          # 自动生成的测试样本
```

---

## 🛠️ 三大格式治理核心技术点与对照

### 1. PDF 文件（最难啃的硬骨头）
- **页面分类判定**：依据页内字符量阈值与图片元数据，将 PDF 页面划分为 `VECTOR_TEXT`（矢量文字）与 `SCANNED_IMAGE`（图片扫描）。
- **矢量页治理**：使用 `pdfplumber.find_tables()` 提取边界矩形，精准转换为 Markdown 表格；结合 `PyMuPDF` 过滤表格区域，提取自洽的段落文本，避免表格内容被按行拆散。
- **扫描件治理**：执行灰度化与二值化增强，接入 OCR 解析流水线，并通过 **后置规则与纠错词典（Post-OCR Error Correction）**，自动校正 `10O,00O.OO -> 100,000.00`、`人氏币 -> 人民币` 等致命混淆。

### 2. Word 文件 (`.docx`)
- **常见缺陷（策略 A）**：分别遍历 `doc.paragraphs` 与 `doc.tables`，会导致所有表格坠落到文档最底部，割裂与前置标题和后置声明的语义依赖。
- **推荐解法（策略 B）**：遍历 `doc.element.body` 的子 XML 节点（`<w:p>` 与 `<w:tbl>`），严格按物理阅读顺序交替提取，保证 Markdown 标题、正文与表格完全保序。

### 3. Excel 文件 (`.xlsx`)
- **严禁直接切词**：上千行表格切词后丢给大模型做汇总统计，极易发生算术幻觉与漏算。
- **明细表走 Text2SQL**：将数据表映射至关系型数据库（如 SQLite/PostgreSQL），将自然语言查询转化为确定性 SQL 聚合计算（`SUM`, `AVG`, `GROUP BY`），保证 100% 准确率。
- **规则表转行级自包含切片**：逐行显式绑定全部列名属性（元数据注入），无论单行被如何检索召回，都拥有完整的独立语义。

---

## 🚀 快速执行与验证命令

### 方式一：一键运行全部 3 大 Demo
```bash
python3 /Users/lucas/Documents/项目/武汉柯莱特企培/day11/demos/run_all_demos.py
```

### 方式二：按专项独立运行
```bash
# 1. 运行 PDF 专项治理
cd /Users/lucas/Documents/项目/武汉柯莱特企培/day11/demos/01_pdf_governance
python3 run_demo.py

# 2. 运行 Word 专项治理
cd /Users/lucas/Documents/项目/武汉柯莱特企培/day11/demos/02_docx_governance
python3 run_demo.py

# 3. 运行 Excel 专项治理
cd /Users/lucas/Documents/项目/武汉柯莱特企培/day11/demos/03_excel_governance
python3 run_demo.py
```
