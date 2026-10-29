# -*- coding: utf-8 -*-
"""
第 3 层：把人工标定完的 bad_case_triage.csv 合并进黄金问题集，完成回归闭环。

用法:
    python merge_golden_cases.py \
        --triage  <repo>/evals/badcase/bad_case_triage.csv \
        --golden  <repo>/evals/golden_dataset_v1.0.json \
        --out     <repo>/evals/golden_dataset_v1.1.json

规则(与 export_bad_cases.py 的预分桶呼应):
  - decision=GOLDEN_REFUSAL → is_adversarial=true,验证回归时系统"仍然拒答";
    ground_truth_answer 缺省用设计性拒答话术,expected_keywords 缺省["转人工"]
  - decision=GOLDEN_QA      → 正常知识问答条目,必须人工填 ground_truth_answer
  - decision=DISCARD 或留空 → 跳过(拒绝答/未标定)
  - 与现有黄金集 query 完全重复的条目自动去重
"""
import argparse
import csv
import json
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_REFUSAL_ANSWER = "系统应给出确定性拒答并引导转人工/提单,不得编造答案。"
DEFAULT_REFUSAL_KEYWORDS = ["转人工"]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="把标定完的 bad case 合并进黄金问题集")
    parser.add_argument("--triage", required=True, help="人工标定完的 bad_case_triage.csv")
    parser.add_argument("--golden", required=True, help="现有黄金问题集 JSON")
    parser.add_argument("--out", required=True, help="输出新版本黄金问题集 JSON")
    parser.add_argument("--prefix", default="BC", help="新条目 ID 前缀(与 GOLDEN-QA 原有条目区分)")
    args = parser.parse_args()

    golden = load_json(Path(args.golden))
    existing_queries = {row.get("query", "").strip() for row in golden}
    max_seq = 0
    for row in golden:
        rid = str(row.get("id", ""))
        if "-" in rid and rid.rsplit("-", 1)[-1].isdigit():
            max_seq = max(max_seq, int(rid.rsplit("-", 1)[-1]))

    added, skipped = [], []
    with Path(args.triage).open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            decision = (row.get("decision") or "").strip().upper()
            question = (row.get("question") or "").strip()
            if decision not in ("GOLDEN_REFUSAL", "GOLDEN_QA"):
                skipped.append((row.get("case_id"), decision or "未标定"))
                continue
            if not question:
                skipped.append((row.get("case_id"), "问题正文为空"))
                continue
            if question in existing_queries:
                skipped.append((row.get("case_id"), "与现有黄金集重复"))
                continue

            max_seq += 1
            keywords = [k.strip() for k in (row.get("expected_keywords") or "").split(";") if k.strip()]
            if decision == "GOLDEN_REFUSAL":
                entry = {
                    "id": f"{args.prefix}-R-{max_seq:04d}",
                    "category": (row.get("category") or "").strip() or "越界拒答",
                    "difficulty": "HARD",
                    "query": question,
                    "ground_truth_answer": (row.get("ground_truth_answer") or "").strip()
                                            or DEFAULT_REFUSAL_ANSWER,
                    "reference_chunk_ids": [],
                    "expected_keywords": keywords or DEFAULT_REFUSAL_KEYWORDS,
                    "is_conflict_check": False,
                    "is_adversarial": True,
                }
            else:  # GOLDEN_QA
                answer = (row.get("ground_truth_answer") or "").strip()
                if not answer:
                    skipped.append((row.get("case_id"), "GOLDEN_QA 未填 ground_truth_answer"))
                    continue
                entry = {
                    "id": f"{args.prefix}-Q-{max_seq:04d}",
                    "category": (row.get("category") or "").strip() or "知识缺口补录",
                    "difficulty": "MEDIUM",
                    "query": question,
                    "ground_truth_answer": answer,
                    "reference_chunk_ids": [],
                    "expected_keywords": keywords,
                    "is_conflict_check": False,
                    "is_adversarial": False,
                }
            golden.append(entry)
            existing_queries.add(question)
            added.append(entry["id"])

    with Path(args.out).open("w", encoding="utf-8") as f:
        json.dump(golden, f, ensure_ascii=False, indent=2)

    print(f"✅ 新增 {len(added)} 条: {', '.join(added) if added else '(无)'}")
    if skipped:
        print(f"⏭ 跳过 {len(skipped)} 条:")
        for case_id, why in skipped[:10]:
            print(f"   {case_id}: {why}")
        if len(skipped) > 10:
            print(f"   ... 其余 {len(skipped) - 10} 条同上")
    print(f"✅ 已写出: {args.out}  (共 {len(golden)} 条, 原有 {len(existing_queries) - len(set(added))} 条)")
    print("下一步: 用新黄金集跑检索/端到端评测,对比 v1.0 指标,门禁达标后发布。")


if __name__ == "__main__":
    main()
