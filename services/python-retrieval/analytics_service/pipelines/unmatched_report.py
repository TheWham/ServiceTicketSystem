# -*- coding: utf-8 -*-
"""词表未命中回捞报告 —— 词表演化的原料。

为什么需要这个脚本：受控词表有两个互相拉扯的需求 —— 口径要**稳定**（否则历史统计
不可比、评测不可回归），覆盖要**演化**（新故障类型出现时词表得跟上）。解法不是
"别固定词表"，而是给它一个**发现新词的机制**。本脚本就是那个机制的第一步：

  未命中工单 → 落盘 + 词频候选 → （人工/LLM 提候选标签）→ 确认后入词表 → 版本 +1

**打标本身仍然只由词典完成** —— LLM 可以提候选，但不参与判定，否则口径不可复现。

用法（在 services/python-retrieval 目录下）：
    python -m analytics_service.pipelines.unmatched_report
    python -m analytics_service.pipelines.unmatched_report --fixture tests/fixtures/tickets.json
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from .. import config as cfg
from .. import taxonomy as tx
from ..aggregate import collect_unmatched
from ..timewindow import parse_window

# 候选词提取：只取中文/英文连续片段，过滤纯数字与单字（单字噪声太大）
_TOKEN_RE = re.compile(r"[一-鿿]{2,}|[A-Za-z]{3,}")
_STOPWORDS = frozenset({
    "电脑", "公司", "员工", "问题", "情况", "进行", "已经", "无法", "不能", "需要",
    "可以", "这个", "那个", "什么", "怎么", "处理", "排查", "确认", "协助", "申请",
})


def _candidates(texts: List[str], top_n: int = 20) -> List[Tuple[str, int]]:
    """从文本里提候选词（中文 2-gram + 英文单词词频）。

    刻意用朴素的 n-gram 词频而不是 LLM 提词：这一步要的是**可复现、可审计**的
    信号，人工确认前后都能重跑出同一份候选。LLM 提候选放在人工确认链条的上游，
    不作为本脚本的依赖。
    """
    counter: collections.Counter = collections.Counter()
    for text in texts:
        tokens = _TOKEN_RE.findall(text or "")
        for tok in tokens:
            t = tok.lower()
            if t in _STOPWORDS:
                continue
            counter[t] += 1
        # 中文再叠加相邻片段（近似二元组），捕捉"进纸组件"这类复合词
        for a, b in zip(tokens, tokens[1:]):
            if len(a) >= 2 and len(b) >= 2 and a not in _STOPWORDS and b not in _STOPWORDS:
                counter[f"{a}{b}"] += 1
    return counter.most_common(top_n)


def main(argv=None) -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="词表未命中回捞报告")
    parser.add_argument("--question", default="本季度", help="用来确定时间窗的问题（默认本季度）")
    parser.add_argument("--fixture", default="", help="离线 fixture JSON（不连 ticket-service）")
    parser.add_argument("--out-dir", default="artifacts/analytics")
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args(argv)

    from ..data_source import FixtureDataSource, HttpDataSource

    ds = FixtureDataSource.from_json(Path(args.fixture)) if args.fixture \
        else HttpDataSource(role="ENGINEER")
    window = parse_window(args.question)
    rows = ds.scan_tickets(window)

    tax = tx.load_taxonomy()
    unmatched = collect_unmatched(rows, tax)

    # 三个桶互斥且穷尽：噪声 / 已打标 / 未命中。分开统计而不是相减，
    # 否则口径一变就悄悄错位，而覆盖率正是要靠这些数字说话。
    noise = 0
    labelled = 0
    for r in rows:
        if tx.low_information_reason(r.title, r.description):
            noise += 1
        elif tx.extract_ticket(r.title, r.description, tax).symptom:
            labelled += 1
    rate = round(labelled * 100.0 / max(1, labelled + len(unmatched)), 1)

    out_dir = cfg.REPO_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = window.start_iso.replace("-", "") + "_" + window.end_iso.replace("-", "")
    out_file = out_dir / f"unmatched_{stamp}.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for row in unmatched:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("=" * 84)
    print(f"词表：v{tax.version}  指纹 {tax.fingerprint}")
    print(f"时间窗：{window.label}（{window.start_iso} ~ {window.end_iso}）")
    print(f"扫描 {len(rows)} 单 → 噪声剔除 {noise} 单 / 已打标 {labelled} 单 / 未命中 {len(unmatched)} 单")
    print(f"**词表覆盖率 taxonomy_coverage_rate = {rate}%**（门槛 ≥ 80%，低于即需扩充词表）")
    print(f"未命中明细已落盘：{out_file}")

    cands = _candidates([r["title"] + " " + r["excerpt"] for r in unmatched], args.top)
    if cands:
        print(f"\n候选新词（词频 Top {args.top}，供人工确认后入词表 —— 本脚本不自动改词表）：")
        for word, n in cands:
            print(f"  {n:>3}×  {word}")
    else:
        print("\n无未命中工单，词表无需扩充。")
    return 0


if __name__ == "__main__":
    sys.exit(main())