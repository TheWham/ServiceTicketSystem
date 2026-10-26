# -*- coding: utf-8 -*-
"""
黄金问题集种子导入:evals/golden_dataset_v1.1.json → golden_case 表(V2_6)。

用法(与 db/tools 下其他脚本一致):
    set DB_PASSWORD=...          (必填)
    python golden_seed_import.py [--golden <path>] [--truncate-warn]

幂等策略:按 natural_key(=原 JSON id) ON DUPLICATE KEY UPDATE 全字段覆盖,
重复执行安全。只做 upsert,不做删除。
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymysql

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

UPSERT_SQL = """
INSERT INTO golden_case
  (natural_key, category, difficulty, query, ground_truth_answer,
   reference_chunk_ids, expected_keywords, is_conflict_check, is_adversarial,
   is_aggregate_check, aggregate_expect,
   source_type, enabled, created_by, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'SEED', 1, 'seed-import', %s)
ON DUPLICATE KEY UPDATE
  category=VALUES(category), difficulty=VALUES(difficulty), query=VALUES(query),
  ground_truth_answer=VALUES(ground_truth_answer),
  reference_chunk_ids=VALUES(reference_chunk_ids),
  expected_keywords=VALUES(expected_keywords),
  is_conflict_check=VALUES(is_conflict_check), is_adversarial=VALUES(is_adversarial),
  is_aggregate_check=VALUES(is_aggregate_check), aggregate_expect=VALUES(aggregate_expect),
  source_type='SEED', enabled=1
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
    )


def main():
    parser = argparse.ArgumentParser(description="黄金问题集种子导入(golden_case)")
    parser.add_argument("--golden", default=None, help="黄金集 JSON 路径,默认 <repo>/evals/golden_dataset_v1.1.json")
    args = parser.parse_args()

    golden_path = Path(args.golden) if args.golden else \
        Path(__file__).resolve().parents[3] / "evals" / "golden_dataset_v1.1.json"
    if not golden_path.exists():
        print(f"[中止] 黄金集文件不存在: {golden_path}", file=sys.stderr)
        sys.exit(2)

    entries = json.loads(golden_path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    conn = connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            for e in entries:
                cur.execute(UPSERT_SQL, (
                    e["id"],
                    e.get("category") or "general",
                    (e.get("difficulty") or "MEDIUM").upper(),
                    e["query"],
                    e.get("ground_truth_answer") or "",
                    json.dumps(e.get("reference_chunk_ids") or [], ensure_ascii=False),
                    json.dumps(e.get("expected_keywords") or [], ensure_ascii=False),
                    1 if e.get("is_conflict_check") else 0,
                    1 if e.get("is_adversarial") else 0,
                    1 if e.get("is_aggregate_check") else 0,
                    # 聚合题没有 aggregate_expect 就存 NULL（= 该题不参与聚合校验），
                    # 而不是存一个空对象 —— 后者会让评测侧读出"有期望但什么都没要求"
                    json.dumps(e["aggregate_expect"], ensure_ascii=False)
                    if e.get("aggregate_expect") else None,
                    now,
                ))
                inserted += cur.rowcount
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM golden_case WHERE enabled=1")
            total = cur.fetchone()[0]
    finally:
        conn.close()

    print(f"✅ 已处理 {len(entries)} 条(写入/更新 {inserted} 行), golden_case 当前有效条目: {total}")
    print(f"   来源文件: {golden_path}")


if __name__ == "__main__":
    main()
