"""
Demo 4 扩展：将「清洗 + LLM 治理 + Wiki 生成」流水线应用到三大格式治理 Demo 的样本文件
- 01_pdf_governance/enterprise_sample.pdf    -> 逐页条目（矢量页 + 扫描件 OCR 页）
- 02_docx_governance/enterprise_sla.docx     -> 按章节切条（SLA 协议）
- 03_excel_governance/enterprise_data.xlsx   -> 规则表行级卡片 + 明细表数据集卡片（Text2SQL 统计）
产物输出到 output/example/{pdf,docx,excel}/

用法：
    python run_examples.py              # 全流程（LLM 在线清洗 + 萃取）
    python run_examples.py --offline    # 离线降级
"""

import argparse
import os
import re
import sqlite3
import sys
import warnings
from dataclasses import replace
from typing import Any, Dict, List, Tuple

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

import pandas as pd

from clean_pipeline import CleanPipeline, Entry, desensitize_text
from llm_synthesizer import LlmSynthesizer, load_api_config
from wiki_generator import render_card, render_index, make_wiki_id

DEMO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_ROOT = os.path.join(DEMO_ROOT, "output", "example")
CACHE_DIR = os.path.join(OUTPUT_ROOT, ".llm_cache")

CN_NUM_RE = re.compile(r"^[一二三四五六七八九十]+、\s*")


def banner(text: str):
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


# ==================== 适配器 1：PDF 样本 ====================

def adapt_pdf() -> List[Entry]:
    sys.path.insert(0, os.path.join(DEMO_ROOT, "01_pdf_governance"))
    from pdf_governor import PDFGovernanceEngine

    engine = PDFGovernanceEngine(os.path.join(DEMO_ROOT, "01_pdf_governance", "enterprise_sample.pdf"))
    entries: List[Entry] = []

    for report in engine.inspect_and_classify_pages():
        idx = report["page_index"]
        if report["page_type"] == "VECTOR_TEXT":
            md = engine.parse_vector_page(idx)
            body = re.sub(r"^### 【矢量解析结果】第 \d+ 页\s*", "", md).strip()
        else:
            md = engine.parse_scanned_page(idx)
            # 截取「最终清洗交付文本」代码块作为该页正文
            m = re.findall(r"```text\n(.*?)```", md, re.DOTALL)
            body = m[-1].strip() if m else md
        # R8 PII 脱敏（类型占位符，保 RAG 语义）
        body, pii_hits = desensitize_text(body)
        first_line = next((ln.strip() for ln in body.splitlines() if ln.strip() and not ln.startswith("#")), f"第{idx}页")
        title = first_line if report["page_type"] == "VECTOR_TEXT" else f"{first_line}（扫描件 OCR）"
        category = "矢量页解析" if report["page_type"] == "VECTOR_TEXT" else "扫描件 OCR 治理"
        print(f"   [脱敏] 第 {idx} 页（{category}）：PII 命中 {pii_hits} 处")
        entries.append(Entry(code=f"PDF-P{idx}", title=title, category=category, fields={"页面内容": body}))
    return entries


# ==================== 适配器 2：DOCX 样本（SLA 协议） ====================

def adapt_docx() -> List[Entry]:
    path = os.path.join(DEMO_ROOT, "02_docx_governance", "enterprise_sla.docx")
    pipeline = CleanPipeline(path)
    blocks = pipeline.clean(pipeline.parse_blocks())

    doc_title = ""
    entries: List[Entry] = []
    current = None
    seq = 0
    for b in blocks:
        if b.kind == "h1":
            doc_title = b.text
            continue
        if b.kind == "h2":
            seq += 1
            current = Entry(
                code=f"SLA-{seq:03d}",
                title=CN_NUM_RE.sub("", b.text).strip(),
                category=doc_title,
            )
            entries.append(current)
            continue
        if current is None:
            continue
        if b.kind == "table":
            current.tables.append(b.rows)
        elif b.text:
            current.body_paras.append(b.text)
    return entries


# ==================== 适配器 3：Excel 样本 ====================

def adapt_excel() -> List[Entry]:
    path = os.path.join(DEMO_ROOT, "03_excel_governance", "enterprise_data.xlsx")
    entries: List[Entry] = []

    # --- 规则表：行级自包含卡片 ---
    policy = pd.read_excel(path, sheet_name="reimbursement_policy")
    for _, row in policy.iterrows():
        level_code = str(row["职级代码"])
        level_name = str(row["职级名称"])
        fields = {col: desensitize_text(str(row[col]))[0]
                  for col in policy.columns if col not in ("职级代码", "职级名称")}
        entries.append(Entry(
            code=f"TRAVEL-{level_code}",
            title=f"差旅报销与审批规则（{level_name}）",
            category="财务制度/差旅报销",
            keywords=[level_code, level_name],
            fields=fields,
        ))

    # --- 明细表：Text2SQL 统计 -> 数据集说明卡 ---
    details = pd.read_excel(path, sheet_name="order_sales_details")
    rename_map = {
        "订单流水号": "order_id", "销售大区": "region", "业务季度": "quarter",
        "客户行业类别": "client_type", "合同销售额(元)": "sales_amount",
        "履约交付成本(元)": "cost_amount", "回款结算状态": "payment_status",
    }
    df = details.rename(columns=rename_map)
    conn = sqlite3.connect(":memory:")
    df.to_sql("sales_orders", conn, if_exists="replace", index=False)

    total = conn.execute(
        "SELECT COUNT(*), ROUND(SUM(sales_amount),2), ROUND(SUM(cost_amount),2) FROM sales_orders"
    ).fetchone()
    by_region = conn.execute(
        "SELECT region, COUNT(*) cnt, ROUND(SUM(sales_amount),2) sales FROM sales_orders GROUP BY region ORDER BY sales DESC"
    ).fetchall()
    by_status = conn.execute(
        "SELECT payment_status, COUNT(*) FROM sales_orders GROUP BY payment_status"
    ).fetchall()
    conn.close()

    region_md = "| 销售大区 | 订单数 | 合同销售额(元) |\n| --- | --- | --- |\n" + "\n".join(
        f"| {r} | {c} | {s:,.2f} |" for r, c, s in by_region)
    overview = (
        f"订单流水明细共 {total[0]} 行 × {len(details.columns)} 列；"
        f"合同销售额合计 {total[1]:,.2f} 元，履约交付成本合计 {total[2]:,.2f} 元，"
        f"毛利 {total[1] - total[2]:,.2f} 元。\n"
        f"回款状态分布：" + "、".join(f"{s} {c} 单" for s, c in by_status)
    )
    schema = "\n".join(f"{cn}（{en}）" for cn, en in rename_map.items())
    entries.append(Entry(
        code="DATASET-SALES",
        title="销售订单流水明细数据集",
        category="数据资产/销售明细",
        keywords=["订单流水", "Text2SQL", "销售统计", "数据集说明"],
        fields={
            "数据概览（SQL 确定性统计）": overview,
            "字段字典": schema,
            "分大区销售汇总": region_md,
            "使用说明": "本表为纯明细流水，禁止直接切词喂大模型做汇总；自然语言查询一律走 Text2SQL 映射到关系引擎执行确定性聚合。",
        },
    ))
    return entries


# ==================== 流水线编排 ====================

def run_group(name: str, entries: List[Entry], synthesizer,
              id_prefix: str, source_name: str, department: str,
              index_title: str) -> Tuple[int, int]:
    banner(f"📦 处理样本组：{name}（{len(entries)} 个条目）")
    out_dir = os.path.join(OUTPUT_ROOT, name)
    os.makedirs(out_dir, exist_ok=True)

    cards = []
    clean_ok = meta_ok = 0
    for i, e in enumerate(entries, 1):
        if synthesizer is not None:
            result = synthesizer.clean_entry(e)
            fields = dict(result["fields"])
            remark = fields.pop("备注", e.remark)
            body = [] if "正文" in fields else e.body_paras
            e = replace(e, fields=fields, remark=remark, body_paras=body)
            meta = synthesizer.extract_frontmatter(e)
            clean_ok += 1 if result.get("clean_source") == "llm" else 0
            meta_ok += 1 if meta.get("meta_source") == "llm" else 0
        else:
            meta = LlmSynthesizer.fallback_frontmatter(e)

        wiki_id = make_wiki_id(e, id_prefix)
        path = os.path.join(out_dir, f"{wiki_id}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(render_card(e, meta, id_prefix, source_name, department))
        cards.append({"entry": e, "meta": meta, "category": e.category, "wiki_id": wiki_id})
        print(f"   [{i:>2}/{len(entries)}] ✅ {e.code} -> {meta.get('title') or e.title}")

    with open(os.path.join(out_dir, "_index.md"), "w", encoding="utf-8") as f:
        f.write(render_index(cards, index_title, source_name))
    print(f"   [OK] {name} 组完成：{len(cards)} 张卡片 + _index.md -> {out_dir}")
    return clean_ok, meta_ok


def main():
    parser = argparse.ArgumentParser(description="三大样本文件 Wiki 生成")
    parser.add_argument("--offline", action="store_true", help="离线模式：不调用 LLM")
    parser.add_argument("--only", choices=["pdf", "docx", "excel"], help="只重跑指定样本组")
    args = parser.parse_args()

    banner("🚀 [Demo 4 扩展] PDF / DOCX / Excel 样本清洗 + Wiki 生成")

    synthesizer = None
    if not args.offline:
        cfg = load_api_config()
        if not cfg["api_key"]:
            print("   [警告] 未找到 KSP_API_KEY，自动降级为离线模式")
        else:
            print(f"   [配置] 清洗模型={cfg['clean_model']} | 精修模型={cfg['chat_model']}")
            synthesizer = LlmSynthesizer(cfg, cache_dir=CACHE_DIR)
    else:
        print("   [离线模式] 跳过全部 LLM 调用")

    banner("📄 [Step 1] 样本解析与规则清洗（各格式适配器）")
    specs = [
        ("pdf", adapt_pdf(), "WIKI-PDF", "enterprise_sample.pdf",
         "集团战略与信息化委员会", "企业预算决议报告 · Wiki 索引"),
        ("docx", adapt_docx(), "WIKI-SLA", "enterprise_sla.docx",
         "集团基础设施技术保障部", "核心系统运维保障 SLA · Wiki 索引"),
        ("excel", adapt_excel(), "WIKI-XLS", "enterprise_data.xlsx",
         "财务共享中心 & 人力资源部", "差旅规则与销售数据集 · Wiki 索引"),
    ]
    for name, entries, *_ in specs:
        print(f"   [适配] {name}: {len(entries)} 个条目（{', '.join(e.code for e in entries[:5])}{'...' if len(entries) > 5 else ''}）")

    if args.only:
        specs = [s for s in specs if s[0] == args.only]

    banner("🤖 [Step 2] LLM 语义级清洗 + 元数据萃取 + Wiki 落盘")
    for name, entries, id_prefix, source_name, department, index_title in specs:
        run_group(name, entries, synthesizer, id_prefix, source_name, department, index_title)

    banner("✅ 全部样本组 Wiki 生成完毕")
    print(f"   产物目录：{OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
