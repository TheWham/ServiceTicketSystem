# -*- coding: utf-8 -*-
"""
黄金问题集导出:golden_case 表 → evals/golden_dataset_v2.0.json。

用法:
    set DB_PASSWORD=...          (必填)
    python golden_export.py [--out <path>] [--v1-compat-id]

评测管道(rag_pipeline.pipelines.golden_evaluation / GoldenSetEvaluator)继续读
JSON 文件且零改动:硬取 id/query,其余字段 .get() 容错。导出字段与 v1.1 schema 对齐:
id=natural_key, 其余按表字段直出;字符串列表列从 JSON 数组解析。
"""
import argparse
import json
import os
import sys
from pathlib import Path

import pymysql

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EXPORT_SQL = """
SELECT natural_key, category, difficulty, query, ground_truth_answer,
       reference_chunk_ids, expected_keywords, is_conflict_check, is_adversarial,
       is_aggregate_check, aggregate_expect
FROM golden_case
WHERE enabled = 1
ORDER BY created_at ASC, id ASC
"""


def connect():
    password = os.environ.get("DB_PASSWORD")
    if not password:
        print("[中止] 缺少必填环境变量 DB_PASSWORD", file=sys.stderr)
        sys.exit(2)
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "120.92.138.195"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=password,
        database=os.environ.get("DB_NAME", "it_ticket_system"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def parse_json(raw):
    """解析 JSON 列；空值 / 坏值返回 None（而不是 {} —— 见导入侧的同一取舍）。"""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def parse_list(raw):
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def main():
    parser = argparse.ArgumentParser(description="从 golden_case 表导出黄金问题集 JSON")
    parser.add_argument("--out", default=None, help="输出路径,默认 <repo>/evals/golden_dataset_v2.0.json")
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else \
        Path(__file__).resolve().parents[3] / "evals" / "golden_dataset_v2.0.json"

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(EXPORT_SQL)
            rows = cur.fetchall()
    finally:
        conn.close()

    entries = []
    for r in rows:
        entries.append({
            "id": r["natural_key"],
            "category": r["category"],
            "difficulty": r["difficulty"],
            "query": r["query"],
            "ground_truth_answer": r["ground_truth_answer"],
            "reference_chunk_ids": parse_list(r["reference_chunk_ids"]),
            "expected_keywords": parse_list(r["expected_keywords"]),
            "is_conflict_check": bool(r["is_conflict_check"]),
            "is_adversarial": bool(r["is_adversarial"]),
            "is_aggregate_check": bool(r["is_aggregate_check"]),
            "aggregate_expect": parse_json((r.get("aggregate_expect") or "").strip())
                                if isinstance(r.get("aggregate_expect"), (str, bytes))
                                else r.get("aggregate_expect"),
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    adversarial = sum(1 for e in entries if e["is_adversarial"])
    aggregate = sum(1 for e in entries if e.get("is_aggregate_check"))
    print(f"✅ 已导出 {len(entries)} 条 → {out_path}")
    print(f"   对抗样本 {adversarial} 条 / 正常样本 {len(entries) - adversarial - aggregate} 条"
          f" / 跨工单聚合 {aggregate} 条")
    print("   评测: python -m rag_pipeline.pipelines.golden_evaluation --golden-dataset <该文件>")


if __name__ == "__main__":
    main()
