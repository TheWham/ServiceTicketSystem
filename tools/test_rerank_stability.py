#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_rerank_stability.py — Reranker 打分稳定性压测工具

对同一个 (query, documents) 组合连续调用 N 次远程 rerank API，
记录每次的绝对分与排序，验证"绝对分漂移、名次稳定"这一工程现象
（详见检索评测讲义）。

产出：
  1. 控制台表格：每次调用各文档的绝对分 + 名次
  2. 独立 HTML 报告（含 SVG 折线图，无第三方依赖，可直接浏览器打开）

用法（在 D:\\day12\\demos 目录下）：
  python test_rerank_stability.py                 # 默认压测 20 次
  python test_rerank_stability.py --n 30          # 压测 30 次
  python test_rerank_stability.py --delay 0.5     # 每次调用间隔 0.5s（防限流）
"""

import sys
import argparse
import json
from pathlib import Path
from statistics import mean, pstdev

# 脚本位于 tools/，向上定位仓库根并加入 sys.path，便于 import rag_pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows 控制台默认 GBK，统一切换 UTF-8 防止 emoji 打印崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rag_pipeline.config import WIKI_DIR, EVALUATION_OUTPUT
from rag_pipeline.retrieval.reranker import KspReranker

# 压测用的固定输入：1 个查询 + 3 篇相关性不同的文档
QUERY = "发邮件收到退信提示550 Mailbox not found，最可能是什么问题？"
DOCS = [
    ("MAIL-001(正确)", "邮件无法发送处置指南：退信提示550 Mailbox not found表示收件人地址写错（拼写错误、用户不存在）；552表示附件超限；检查SMTP日志定位拒绝原因。"),
    ("NET-002(无关)", "有线网络无法连接（网口无反应）：检查网线是否插好、网口指示灯是否亮、交换机端口与VLAN配置。"),
    ("ACC-002(弱相关)", "密码重置与过期处理：员工忘记密码可通过自助密码重置平台重置，或联系IT在AD域控重置临时密码。"),
]

# 场景 hc10：HC-10 同义改写题的真实候选子块（4 张卡各取首块，复现"精排误杀"现场）
HC10_QUERY = "表格里改了原始数据，汇总列的数字却一直不跟着变，要检查哪些设置？"
HC10_CARDS = ["ITKB-OFF-004", "ITKB-OFF-001", "ITKB-VPN-002", "ITKB-HW-005"]


def load_hc10_docs():
    """从真实 Wiki 卡片切块取候选（首块含上下文头，语义最完整）。"""
    from rag_pipeline.config import load_config, build_chunker
    chunker, _ = build_chunker(load_config())
    docs = []
    for card in HC10_CARDS:
        _, children = chunker.split_wiki_document(str(WIKI_DIR / f"{card}.md"))
        if children:
            docs.append((f"{card}#c0", children[0].page_content))
    return docs


def run_stress(reranker: KspReranker, n: int, delay: float):
    """连续压测 n 次，返回每次调用的 (分数列表, 名次列表)"""
    import time
    rounds = []
    for i in range(n):
        try:
            scores = reranker._call_api(QUERY, [d for _, d in DOCS])
        except Exception as e:
            print(f"  第 {i+1} 次调用失败: {e}")
            scores = None
        ranks = None
        if scores is not None:
            # 计算名次（1 = 最高）
            order = sorted(range(len(scores)), key=lambda j: scores[j], reverse=True)
            ranks = [0] * len(scores)
            for pos, idx in enumerate(order, 1):
                ranks[idx] = pos
        rounds.append({"scores": scores, "ranks": ranks})
        if delay > 0:
            time.sleep(delay)
    return rounds


def summarize(rounds):
    """汇总每个文档的分数统计（min/max/mean/std）与名次稳定性"""
    n_docs = len(DOCS)
    stats = []
    for d in range(n_docs):
        vals = [r["scores"][d] for r in rounds if r["scores"] is not None]
        ranks = [r["ranks"][d] for r in rounds if r["ranks"] is not None]
        stats.append({
            "min": min(vals) if vals else 0,
            "max": max(vals) if vals else 0,
            "mean": mean(vals) if vals else 0,
            "std": pstdev(vals) if len(vals) > 1 else 0,
            "rank_set": sorted(set(ranks)),
        })
    return stats


def build_html(rounds, stats, out_path: Path):
    """生成无第三方依赖的 HTML 报告（内联 SVG 折线图）"""
    n = len(rounds)
    labels = [name for name, _ in DOCS]
    colors = ["#2563eb", "#dc2626", "#16a34a", "#f59e0b", "#8b5cf6", "#0891b2"][:max(len(DOCS), 1)]

    # ---- SVG 折线图：x=调用次数, y=绝对分 ----
    W, H, PAD = 760, 360, 50
    xs = [PAD + i * (W - 2 * PAD) / max(n - 1, 1) for i in range(n)]
    all_scores = [s for r in rounds if r["scores"] for s in r["scores"]]
    ymin, ymax = (min(all_scores), max(all_scores)) if all_scores else (0, 1)
    if ymax - ymin < 1e-6:
        ymax = ymin + 1e-6

    def y_of(v):
        return H - PAD - (v - ymin) / (ymax - ymin) * (H - 2 * PAD)

    svg = [f'<svg width="{W}" height="{H}" style="background:#fff;border:1px solid #e5e7eb;border-radius:8px">']
    # y 轴网格与刻度
    for t in range(6):
        v = ymin + (ymax - ymin) * t / 5
        y = y_of(v)
        svg.append(f'<line x1="{PAD}" y1="{y}" x2="{W-PAD}" y2="{y}" stroke="#f3f4f6"/>')
        svg.append(f'<text x="{PAD-6}" y="{y+4}" font-size="10" fill="#9ca3af" text-anchor="end">{v:.2f}</text>')
    for d in range(len(DOCS)):
        pts = []
        for i, r in enumerate(rounds):
            if r["scores"] is not None:
                pts.append(f"{xs[i]:.1f},{y_of(r['scores'][d]):.1f}")
        if pts:
            svg.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colors[d]}" stroke-width="2"/>')
            for i, r in enumerate(rounds):
                if r["scores"] is not None:
                    svg.append(f'<circle cx="{xs[i]:.1f}" cy="{y_of(r["scores"][d]):.1f}" r="3" fill="{colors[d]}"/>')
    svg.append("</svg>")
    svg_str = "".join(svg)

    # 图例
    legend = "".join(
        f'<span style="display:inline-flex;align-items:center;margin-right:16px">'
        f'<span style="width:14px;height:3px;background:{colors[d]};display:inline-block;margin-right:6px"></span>{labels[d]}</span>'
        for d in range(len(DOCS))
    )

    # 每次调用明细表
    rows_html = ""
    for i, r in enumerate(rounds):
        if r["scores"] is None:
            rows_html += f"<tr><td>{i+1}</td><td colspan='{len(DOCS)}' style='color:#dc2626'>调用失败</td><td>-</td></tr>"
            continue
        cells = "".join(
            f"<td>{r['scores'][d]:.4f}<br><small style='color:#6b7280'>第{r['ranks'][d]}名</small></td>"
            for d in range(len(DOCS))
        )
        rows_html += f"<tr><td>{i+1}</td>{cells}</tr>"

    stats_rows = "".join(
        f"<tr><td>{labels[d]}</td><td>{s['min']:.4f}</td><td>{s['max']:.4f}</td>"
        f"<td>{s['mean']:.4f}</td><td>{s['std']:.4f}</td><td>{s['rank_set']}</td></tr>"
        for d, s in enumerate(stats)
    )

    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>Reranker 打分稳定性压测</title>
<style>
 body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:32px;color:#111827;background:#f9fafb}}
 h1{{font-size:22px}} h2{{font-size:17px;margin-top:28px}}
 .card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:20px;margin:16px 0}}
 table{{border-collapse:collapse;width:100%;font-size:13px}}
 th,td{{border:1px solid #e5e7eb;padding:6px 10px;text-align:center}}
 th{{background:#f3f4f6}}
 .q{{background:#eff6ff;border-left:4px solid #2563eb;padding:10px 14px;border-radius:6px}}
 .warn{{background:#fef2f2;border-left:4px solid #dc2626;padding:10px 14px;border-radius:6px}}
 .ok{{background:#f0fdf4;border-left:4px solid #16a34a;padding:10px 14px;border-radius:6px}}
 small{{color:#6b7280}}
</style></head><body>
<h1>📉 Reranker 打分稳定性压测报告</h1>
<div class="card q"><b>压测输入（固定不变）</b><br>
<b>Query：</b>{QUERY}<br>
<b>Documents：</b>{" ｜ ".join(f"{n}: {t[:40]}…" for n, t in DOCS)}<br>
<small>连续调用 {n} 次 · 模型 qwen3-reranker-8b (KSP /rerank)</small></div>

<div class="card">
<h2>① 各文档绝对分随调用次数的变化（折线图）</h2>
<div style="margin-bottom:8px">{legend}</div>
{svg_str}
<div class="warn" style="margin-top:12px">
<b>观察点：</b>同一输入多次调用，<b>绝对分区间发生漂移</b>（可能整体抬高或压缩），
但<b>名次基本稳定</b>。因此融合排序不能用绝对分，必须用名次。
</div>
</div>

<div class="card">
<h2>② 每文档分数统计</h2>
<table><tr><th>文档</th><th>最低分</th><th>最高分</th><th>均值</th><th>标准差</th><th>名次集合</th></tr>{stats_rows}</table>
</div>

<div class="card">
<h2>③ 每次调用明细（分数 + 名次）</h2>
<table><tr><th>调用#</th>{"".join(f"<th>{n}</th>" for n, _ in DOCS)}</tr>{rows_html}</table>
</div>

<div class="card ok">
<b>结论（工程取舍）：</b>远程 Reranker 的<b>绝对分不可复现、会漂移</b>，
但<b>排序相对稳定</b>。因此本项目在 hybrid_rerank_search 中采用
<b>按秩加权融合</b>（取 rerank 名次 + RRF 名次，而非绝对分），
保证检索结果对分数漂移免疫、可复现。
</div>
</body></html>"""
    out_path.write_text(html, encoding="utf-8")


def main():
    global QUERY, DOCS
    parser = argparse.ArgumentParser(description="Reranker 打分稳定性压测")
    parser.add_argument("--n", type=int, default=20, help="压测次数（默认20）")
    parser.add_argument("--delay", type=float, default=0.3, help="每次调用间隔秒数（防限流，默认0.3）")
    parser.add_argument("--out", default="", help="HTML 报告输出路径（默认按场景自动命名）")
    parser.add_argument("--scenario", choices=["mail550", "hc10"], default="mail550",
                        help="压测场景：mail550=固定三文档冒烟；hc10=HC-10同义改写题真实候选（复现精排误杀现场）")
    args = parser.parse_args()

    if args.scenario == "hc10":
        QUERY = HC10_QUERY
        DOCS = load_hc10_docs()
        out_path = Path(args.out or str(EVALUATION_OUTPUT / "rerank稳定性压测报告_hc10.html"))
    else:
        out_path = Path(args.out or str(EVALUATION_OUTPUT / "rerank稳定性压测报告.html"))

    print(f"🔬 压测 reranker：连续调用 {args.n} 次（每次间隔 {args.delay}s）...")
    print(f"   场景: {args.scenario} | Query: {QUERY[:40]}...")
    reranker = KspReranker()
    if not reranker.available:
        print("❌ reranker 当前不可用（可能限流/未配置），请稍后重试")
        sys.exit(1)

    rounds = run_stress(reranker, args.n, args.delay)
    stats = summarize(rounds)

    # 控制台表格
    print(f"\n{'调用#':<7}" + "".join(f"{name:<24}" for name, _ in DOCS))
    print("-" * 80)
    for i, r in enumerate(rounds):
        if r["scores"] is None:
            print(f"{i+1:<7}调用失败")
            continue
        row = "".join(f"{r['scores'][d]:.3f}(#{r['ranks'][d]})      " for d in range(len(DOCS)))
        print(f"{i+1:<7}{row}")

    print("\n=== 统计 ===")
    for d, s in enumerate(stats):
        print(f"{DOCS[d][0]:<16} min={s['min']:.3f} max={s['max']:.3f} mean={s['mean']:.3f} std={s['std']:.3f} 名次集合={s['rank_set']}")

    out = out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    build_html(rounds, stats, out)
    print(f"\n🎉 HTML 报告已生成：{out}  （浏览器直接打开即可）")


if __name__ == "__main__":
    main()
