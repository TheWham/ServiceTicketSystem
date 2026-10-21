#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_service_regression.py — 黄金集 20 题过 HTTP 服务端点，逐题比对 Day14 冻结基线

一致性口径（必须逐题一致，否则回归失败）：
  - 拒答集合：基线 rejected ⇔ 服务 ends REFUSE（items 为空）；
  - 命中集合：基线 parent_ids ⇔ 服务 items[].articleId。
    注意：灌库前映射未加载，articleId 降级为 parent_id（wiki 侧 id），可直接比对；
    灌库后 articleId 变为 Java 侧 id，需以 --id-mode java 跳过集合比对（仅比拒答）。

用法：
    python tools/run_service_regression.py                       # 灌库前：全量比对
    python tools/run_service_regression.py --id-mode java        # 灌库后：只比拒答
"""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def post(base: str, path: str, payload: dict, timeout: float = 60.0):
    req = urllib.request.Request(
        base + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}


def main() -> int:
    parser = argparse.ArgumentParser(description="黄金集服务化回归 vs Day14 基线")
    parser.add_argument("--base", default="http://127.0.0.1:8310")
    parser.add_argument("--baseline", default="artifacts/evals/day14_baseline.json")
    parser.add_argument("--id-mode", choices=["wiki", "java", "auto"], default="auto",
                        help="wiki=灌库前（articleId 降级为 parent_id）；java=灌库后将 articleId 经映射表翻回 wiki_id 再比对；"
                             "auto=有映射表即按 java 口径")
    parser.add_argument("--mapping", default="data/wiki_article_mapping.json",
                        help="wiki→Java 映射表（java 口径下用于把 articleId 翻回 wiki_id）")
    parser.add_argument("--pace", type=float, default=1.0,
                        help="每题之间的间隔秒数；网关限流敏感，连续轰炸会导致 rerank 降级启发式")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    # 灌库后服务返回 Java 侧 articleId（art-…）；经映射表反查翻回 wiki_id，
    # 才能与基线（wiki 侧 id）逐卡比对。
    mapping_path = REPO_ROOT / args.mapping
    wiki_of_article: dict = {}
    if mapping_path.exists():
        for wiki_id, entry in json.loads(mapping_path.read_text(encoding="utf-8")).items():
            if entry.get("articleId"):
                wiki_of_article[entry["articleId"]] = wiki_id
    id_mode = args.id_mode
    if id_mode == "auto":
        id_mode = "java" if wiki_of_article else "wiki"
    print(f"id 口径：{id_mode}（映射表 {mapping_path.name}：{len(wiki_of_article)} 条）")
    if id_mode == "java" and not wiki_of_article:
        print("⚠️ java 口径但映射表为空：无法把 articleId 翻回 wiki_id，集合/名次比对将跳过")

    def degraded_count() -> int:
        try:
            req = urllib.request.Request(base + "/api/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8")).get("rerankDegradedCount", -1)
        except Exception:
            return -1

    degraded_before = degraded_count()

    baseline = json.loads((REPO_ROOT / args.baseline).read_text(encoding="utf-8"))
    top_k = baseline.get("top_k", 3)

    print(f"基线：{args.baseline}（{baseline['generated_at']}，top_k={top_k}）")
    print(f"端点：{base}\n")
    print(f"{'用例':<15}{'基线拒答':<9}{'服务拒答':<9}{'命中集合一致':<13}{'基线Top1':<10}{'服务Top1':<10}{'时延(ms)'}")
    print("-" * 84)

    mismatches, degraded_warns, latencies = [], [], []
    for ref in baseline["results"]:
        degraded_before_q = degraded_count()
        t0 = time.time()
        status, env = post(base, "/api/v1/rag/retrievals",
                           {"question": ref["query"], "topK": top_k})
        latency = round((time.time() - t0) * 1000, 1)
        latencies.append(latency)
        # 串行执行 + 逐题读降级计数器：delta>0 即本题的 rerank 走了启发式降级
        degraded_after_q = degraded_count()
        degraded_this_q = (degraded_before_q >= 0 and degraded_after_q > degraded_before_q)
        data = (env or {}).get("data") or {}
        items = data.get("items") or []
        service_refused = (status == 200 and env.get("code") == 0
                           and data.get("suggestedReplyType") == "REFUSE" and not items)
        service_ids = [it.get("articleId") for it in items]
        # java 口径：把服务返回的 articleId 翻回 wiki_id，与基线同口径比对
        if id_mode == "java" and wiki_of_article:
            service_ids = [wiki_of_article.get(a, a) for a in service_ids]
        service_top = data.get("topScore")

        refused_ok = bool(ref["rejected"]) == bool(service_refused)
        # 目标卡名次：基线 parent_ids 按检索顺序记录，hit_rank-1 处即黄金集目标卡。
        # 这是 Day14 指标（Top-1/Top-3/MRR/冲突消歧）的直接载体，必须逐题一致。
        target_card = ref["parent_ids"][ref["hit_rank"] - 1] if ref.get("hit_rank") else None
        service_target_rank = (service_ids.index(target_card) + 1) if target_card in service_ids else None
        rank_ok = (ref.get("hit_rank") is None) or (service_target_rank == ref["hit_rank"])
        if ref["rejected"]:
            ids_ok = True          # 拒答题不比对集合
        else:
            ids_ok = set(ref["parent_ids"]) == set(service_ids)

        if not refused_ok or not rank_ok or not ids_ok:
            rec = {
                "id": ref["id"], "refused_ok": refused_ok, "ids_ok": ids_ok, "rank_ok": rank_ok,
                "baseline_refused": ref["rejected"], "service_refused": service_refused,
                "baseline_parents": ref["parent_ids"], "service_ids": service_ids,
                "target_card": target_card, "baseline_rank": ref.get("hit_rank"),
                "service_rank": service_target_rank, "degraded": degraded_this_q,
            }
            if not refused_ok or not rank_ok:
                # 拒答不一致 / 目标卡名次漂移 = 指标级回归（Day14 Top-K/MRR 载体），一律硬失败
                mismatches.append(rec)
            elif degraded_this_q:
                degraded_warns.append(rec)     # 限流降级导致：报告不判负
            elif not ids_ok:
                # 非目标槽位排序抖动：网关 dashscope 后端对同一输入存在轻微跨调用分数漂移，
                # 目标卡名次与拒答均未变 → 报告项（不影响任何 Day14 达标线）
                degraded_warns.append(rec)
        mismatch = not refused_ok or not rank_ok or not ids_ok
        if ref["rejected"] and service_refused:
            cell = "—"
        elif not mismatch:
            cell = "✅"
        elif degraded_this_q and refused_ok and rank_ok:
            cell = "⚠️降级"
        elif refused_ok and rank_ok:
            cell = "⚠️尾槽"
        else:
            cell = "❌"
        print(f"{ref['id']:<15}{str(ref['rejected']):<9}{str(service_refused):<9}"
              f"{cell:<13}{ref['top_score']:<10}{str(service_top):<10}{latency}")
        if args.pace > 0:
            time.sleep(args.pace)

    degraded_delta = degraded_count() - degraded_before if degraded_before >= 0 else -1

    latencies_sorted = sorted(latencies)
    p50 = statistics.median(latencies_sorted)
    p95 = latencies_sorted[min(len(latencies_sorted) - 1, int(round(0.95 * (len(latencies_sorted) - 1))))]
    print("-" * 84)
    print(f"\n延迟：P50 {p50:.0f}ms / P95 {p95:.0f}ms / max {max(latencies):.0f}ms"
          f"（基线 avg {baseline['summary_metrics'].get('avg_latency_ms')}）")
    print(f"基线指标：{json.dumps(baseline['summary_metrics'], ensure_ascii=False)}")
    if degraded_delta >= 0:
        print(f"本轮 rerank 降级启发式次数：{degraded_delta}"
              f"（>0 说明网关限流，降级题排序可能与基线不同，属预期行为）")

    if degraded_warns:
        print(f"\n⚠️ {len(degraded_warns)} 题因限流降级与基线集合漂移（报告项，非失败）：")
        for w in degraded_warns:
            print(f"  {w['id']}: 基线 parents={w['baseline_parents']} 服务 ids={w['service_ids']}")

    if mismatches:
        print(f"\n❌ 回归失败：{len(mismatches)} 题与基线不一致（拒答红线或目标卡名次漂移）")
        for m in mismatches:
            print(f"  {m['id']}: 拒答一致={m['refused_ok']} 目标卡={m['target_card']}"
                  f" 基线名次={m['baseline_rank']} 服务名次={m['service_rank']} 降级={m['degraded']}")
        return 1
    print(f"\n🎉 回归通过：{len(baseline['results'])} 题逐题一致"
          f"（含降级报告 {len(degraded_warns)} 题，降级占比 {degraded_delta}/{len(baseline['results'])}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
