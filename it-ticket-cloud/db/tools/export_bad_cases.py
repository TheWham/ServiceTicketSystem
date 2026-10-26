# -*- coding: utf-8 -*-
"""
Bad Case 导出与人工标定助手：打通「ai_interaction/消息记录 → 黄金问题集回归」动线的第 1~2 层。

用法(与 db/tools 下其他脚本一致,先设置环境变量):
    set DB_PASSWORD=...          (必填)
    python export_bad_cases.py                    # 导出 + 生成分桶标定表
    python export_bad_cases.py --since 2026-10-01 --limit 200

数据来源(三表联查,均为线上既有表,零 schema 改动):
  - consultation_message.ai_msg  : sender_type='AI' 且 citation_json->>'$.replyType'='REFUSE'
                                   (拒答原因 refusalReason 由 AiConsultationService.persistAiMessage 写入)
  - consultation_message.q       : 同会话中该 AI 消息之前最近一条员工提问 = bad case 的 query 正文
  - ai_interaction               : 置信度/耗时/模型版本/员工反馈,经 metadata.interactionId 关联

产出(默认写入 <repo>/evals/badcase/):
  1. bad_cases.jsonl    — 原始导出,一行一案,带 refusalReason/confidence 等全字段(审计留档)
  2. bad_case_triage.csv — 人工标定表,utf-8-sig 可直接用 Excel 打开:
                           已按 refusalReason 预分桶并给出建议动作(suggested_action),
                           人工只需填 4 列: decision / category / expected_keywords / ground_truth_answer,
                           填完后交给 merge_golden_cases.py 合并进黄金问题集(第 3 层)。

预分桶规则(为什么不让"拒答即坏例"全自动进黄金集):
  - HIGH_RISK_TOPIC / OFF_TOPIC / POLICY_BLOCKED → EXPECTED_REFUSAL:这是设计性诚实拒答,
    属于正确行为,应进黄金集的对抗区(is_adversarial=true),回归时验证"仍然拒答"。
  - NO_RELIABLE_KNOWLEDGE / LOW_CONFIDENCE / CONFLICTING_KNOWLEDGE → REVIEW_KNOWLEDGE_GAP:
    待人工判断——本该有答案的真知识缺口(补知识后进黄金集) or 本就该拒答的越界题(改标拒答)。
  - MODEL_UNAVAILABLE → INFRA_NOISE:基础设施故障,不是知识问题,不进黄金集。
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pymysql

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# refusalReason → (建议动作, 一句话处置说明)
BUCKETS = {
    "HIGH_RISK_TOPIC": ("EXPECTED_REFUSAL", "设计性拒答,进黄金集对抗区,回归验证仍拒答"),
    "OFF_TOPIC": ("EXPECTED_REFUSAL", "设计性拒答,进黄金集对抗区,回归验证仍拒答"),
    "POLICY_BLOCKED": ("EXPECTED_REFUSAL", "设计性拒答,进黄金集对抗区,回归验证仍拒答"),
    "NO_RELIABLE_KNOWLEDGE": ("REVIEW_KNOWLEDGE_GAP", "人工判断:真缺口补知识后进黄金集;越界题改标拒答"),
    "LOW_CONFIDENCE": ("REVIEW_KNOWLEDGE_GAP", "人工判断:真缺口补知识后进黄金集;越界题改标拒答"),
    "CONFLICTING_KNOWLEDGE": ("REVIEW_KNOWLEDGE_GAP", "人工判断:版本冲突需消歧,补知识后进黄金集"),
    "MODEL_UNAVAILABLE": ("INFRA_NOISE", "基础设施故障,不进黄金集,建议 DISCARD 或另走运维归因"),
}

DECISION_OPTIONS = "GOLDEN_REFUSAL | GOLDEN_QA | DISCARD(留空=待定)"

# 拒答消息与本条 AI 消息之前最近一条员工提问配对(相关子查询取 MAX(sent_at))
EXPORT_SQL = """
SELECT
  ai_msg.message_id                                            AS ai_message_id,
  ai_msg.session_id                                            AS session_id,
  q.message_id                                                 AS question_message_id,
  q.content                                                    AS question,
  JSON_UNQUOTE(JSON_EXTRACT(ai_msg.citation_json, '$.replyType'))     AS reply_type,
  JSON_UNQUOTE(JSON_EXTRACT(ai_msg.citation_json, '$.refusalReason')) AS refusal_reason,
  JSON_UNQUOTE(JSON_EXTRACT(ai_msg.citation_json, '$.interactionId')) AS interaction_id,
  it.model_version                                             AS model_version,
  it.confidence                                                AS confidence,
  it.latency                                                   AS latency_ms,
  it.feedback                                                  AS feedback,
  ai_msg.sent_at                                               AS occurred_at
FROM consultation_message ai_msg
JOIN consultation_message q
  ON q.session_id = ai_msg.session_id
 AND q.sender_type = 'EMPLOYEE'
 AND q.sent_at = (
       SELECT MAX(q2.sent_at) FROM consultation_message q2
       WHERE q2.session_id = ai_msg.session_id
         AND q2.sender_type = 'EMPLOYEE'
         AND q2.sent_at < ai_msg.sent_at
     )
LEFT JOIN ai_interaction it
  ON it.interaction_id = JSON_UNQUOTE(JSON_EXTRACT(ai_msg.citation_json, '$.interactionId'))
WHERE ai_msg.sender_type = 'AI'
  AND JSON_UNQUOTE(JSON_EXTRACT(ai_msg.citation_json, '$.replyType')) = 'REFUSE'
  {since_clause}
ORDER BY ai_msg.sent_at ASC
{limit_clause}
"""

TRIAGE_COLUMNS = [
    "case_id", "session_id", "occurred_at", "refusal_reason", "suggested_action",
    "confidence", "model_version", "latency_ms", "feedback", "question",
    "decision", "category", "expected_keywords", "ground_truth_answer", "decision_note",
]


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


def bucket_of(reason: str):
    return BUCKETS.get(reason, ("REVIEW_KNOWLEDGE_GAP", f"未知拒答原因 {reason!r},请人工归因"))


def fetch_cases(conn, since: str, limit: int):
    since_clause = "AND ai_msg.sent_at >= %s" if since else ""
    limit_clause = "LIMIT %d" % limit if limit > 0 else ""
    sql = EXPORT_SQL.format(since_clause=since_clause, limit_clause=limit_clause)
    params = (since,) if since else ()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def export_jsonl(rows, out_path: Path):
    with out_path.open("w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            r = dict(r)
            r["case_id"] = "BC-" + str(r["session_id"])[-8:] + "-" + f"{i:04d}"
            for k in ("sent_at", "occurred_at"):
                if isinstance(r.get(k), datetime):
                    r[k] = r[k].isoformat()
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def export_triage_csv(rows, out_path: Path):
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRIAGE_COLUMNS)
        writer.writeheader()
        for i, r in enumerate(rows, 1):
            case_id = "BC-" + str(r["session_id"])[-8:] + "-" + f"{i:04d}"
            action, note = bucket_of(r["refusal_reason"])
            writer.writerow({
                "case_id": case_id,
                "session_id": r["session_id"],
                "occurred_at": r["occurred_at"],
                "refusal_reason": r["refusal_reason"],
                "suggested_action": action,
                "confidence": r["confidence"],
                "model_version": r["model_version"],
                "latency_ms": r["latency_ms"],
                "feedback": r["feedback"],
                "question": r["question"],
                # ---- 以下 5 列由人工填写 ----
                "decision": "",          # GOLDEN_REFUSAL / GOLDEN_QA / DISCARD
                "category": "",
                "expected_keywords": "",  # 分号分隔,如: 转人工;不能执行操作
                "ground_truth_answer": "",
                "decision_note": note,   # 预填建议,人工可改
            })


def print_summary(rows):
    stats = {}
    for r in rows:
        action, _ = bucket_of(r["refusal_reason"])
        stats[action] = stats.get(action, 0) + 1
    print(f"\n共导出 {len(rows)} 条 REFUSE 记录,预分桶结果:")
    for action, n in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"  {action:<22} {n:>5} 条")
    print("\n下一步: 用 Excel 打开 bad_case_triage.csv,人工填写 decision 等列")
    print(f"       (decision 可选值: {DECISION_OPTIONS})")
    print("       填完后执行 merge_golden_cases.py 合并进黄金问题集。")


def main():
    parser = argparse.ArgumentParser(description="导出 AI 拒答 bad case 并生成人工标定表")
    parser.add_argument("--since", default=None, help="只导出该日期(含)之后的记录,如 2026-10-01")
    parser.add_argument("--limit", type=int, default=0, help="最多导出条数,0=不限")
    parser.add_argument("--out-dir", default=None, help="输出目录,默认 <repo>/evals/badcase")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else \
        Path(__file__).resolve().parents[3] / "evals" / "badcase"
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = connect()
    try:
        rows = fetch_cases(conn, args.since, args.limit)
    finally:
        conn.close()

    jsonl_path = out_dir / "bad_cases.jsonl"
    csv_path = out_dir / "bad_case_triage.csv"
    export_jsonl(rows, jsonl_path)
    export_triage_csv(rows, csv_path)

    print(f"✅ 原始导出: {jsonl_path}")
    print(f"✅ 标定表:   {csv_path}")
    print_summary(rows)


if __name__ == "__main__":
    main()
