# -*- coding: utf-8 -*-
"""Day15 全量黄金集回归 + 报告落盘；--serve 转发到 uvicorn 服务。

用法：
  python day15/run_day15_pipeline.py                 # 全量黄金集回归，报告 → artifacts/day15/
  python day15/run_day15_pipeline.py --limit 3       # 只跑前 N 题（调试）
  python day15/run_day15_pipeline.py --serve         # 启动 HTTP 演示服务（同 python -m day15）
  python day15/run_day15_pipeline.py --serve --port 8320

判定口径（evals/golden_dataset_v1.0.json，20 题）：
  - 对抗题（is_adversarial）      → 必须拒答（is_refused）；
  - 版本冲突题（is_conflict_check）→ 来源列表不得含已废止 LEG 卡；
  - 正例题                        → 答案或来源片段须命中 expected_keywords 中的事实。
联网时走真实 LLM 生成；离线（DAY15_OFFLINE=1 或网关不可用）时正例题的关键词
改在命中片段中校验，并在报告中注明模式。
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

GOLDEN_PATH = REPO_ROOT / "evals" / "golden_dataset_v1.0.json"


def _serve(port: int | None) -> None:
    from day15 import config as dcfg
    import uvicorn
    from day15.api import create_app
    uvicorn.run(create_app(), host=dcfg.HOST, port=port or dcfg.PORT, workers=1,
                log_level="info")


def run_regression(limit: int | None) -> None:
    from day15 import config as dcfg
    from day15.service import EnterpriseKnowledgeService

    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    if limit:
        golden = golden[:limit]

    svc = EnterpriseKnowledgeService()
    dcfg.REPORT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    passed = 0
    for i, item in enumerate(golden, 1):
        q = item["query"]
        print(f"\n[{i}/{len(golden)}] {item['id']} ({item['category']}) — {q[:50]}…")
        t0 = time.time()
        try:
            r = svc.answer(q, include_trace=False)
        except Exception as e:  # noqa: BLE001 —— 回归不中断，记为失败
            rows.append({"id": item["id"], "ok": False, "why": f"异常: {e}"})
            print(f"   ❌ 异常: {e}")
            continue
        elapsed = round(time.time() - t0, 1)

        why = []
        ok = True
        cite_ids = [c.card_id for c in r.citations]
        corpus_text = " ".join(c.snippet for c in r.citations)

        if item.get("is_adversarial"):
            if not r.is_refused:
                ok = False
                why.append("对抗题未拒答")
        elif item.get("is_conflict_check"):
            leg = [cid for cid in cite_ids if cid.startswith("ITKB-LEG")]
            if leg:
                ok = False
                why.append(f"引用了废止卡: {leg}")
            if r.is_refused:
                ok = False
                why.append("冲突题误拒答")
        else:
            hits = [k for k in item.get("expected_keywords", [])
                    if k in r.answer or k in corpus_text]
            if r.is_refused:
                ok = False
                why.append("正例题误拒答")
            elif item.get("expected_keywords") and not hits:
                ok = False
                why.append(f"未命中关键词 {item['expected_keywords']}")
            else:
                why.append(f"关键词命中: {hits}")

        mode_note = f"{r.mode}{'/offline' if r.offline else ''}"
        rows.append({"id": item["id"], "ok": ok, "why": "; ".join(why),
                     "mode": mode_note, "refused": r.is_refused,
                     "cites": cite_ids, "sec": elapsed})
        passed += ok
        mark = "✅" if ok else "❌"
        print(f"   {mark} {mode_note} | {elapsed}s | {'; '.join(why)}")
        if r.is_refused:
            print(f"   拒答: {r.answer[:60]}")

    total = len(rows)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Day15 服务层黄金集回归报告",
        "",
        f"- 运行时间：{stamp}",
        f"- 题数：{total}，通过：{passed}，失败：{total - passed}",
        f"- 模式：{'强制离线' if dcfg.OFFLINE else '联网优先'}；LLM 可用：{svc.generator.available}",
        "",
        "| 题号 | 结果 | 模式 | 拒答 | 来源卡 | 说明 |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {'✅' if row['ok'] else '❌'} | {row.get('mode','-')} | "
            f"{'是' if row.get('refused') else '否'} | {', '.join(row.get('cites') or []) or '—'} | {row['why']} |")
    report = "\n".join(lines) + "\n"
    out = dcfg.REPORT_DIR / "Day15_黄金集回归报告.md"
    out.write_text(report, encoding="utf-8")
    print(f"\n{'='*60}\n通过 {passed}/{total}；报告 → {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Day15 服务层回归与演示入口")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 题")
    parser.add_argument("--serve", action="store_true", help="启动 HTTP 演示服务")
    parser.add_argument("--port", type=int, default=None, help="服务端口")
    args = parser.parse_args()

    if args.serve:
        _serve(args.port)
    else:
        run_regression(args.limit)


if __name__ == "__main__":
    main()
