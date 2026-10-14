"""Day13 评测报告生成：主报告 + 逐题详细召回过程。"""

from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document


TRACK_LABELS = {"dense": "链路 A：纯 Dense", "bm25": "链路 B：纯 BM25",
                "fused": "链路 C：RRF 融合", "full": "链路 D：全链路"}

QTYPE_NAMES = {"hard": "硬匹配", "paraphrase": "同义改写",
               "confusable": "近邻混淆", "negative": "库外负样本"}


GRANULARITY_NAMES = {"child": "子块级（逐小节打分）", "parent": "父块级（子块召回后对整卡打分）"}


def suite_breakdown(suite: List[Dict[str, Any]]) -> str:
    """按题型统计题集构成，如"7 道硬匹配 + 3 道同义改写 + 2 道库外负样本"（不再写死题数）。"""
    counts: Dict[str, int] = {}
    for t in suite:
        q = t.get("qtype", "hard")
        counts[q] = counts.get(q, 0) + 1
    return " + ".join(f"{n} 道{QTYPE_NAMES.get(q, q)}" for q, n in counts.items())


def pick_winners(stats: Dict[str, Dict[str, Any]]) -> List[str]:
    """返回综合最优链路列表：Recall@3 > MRR > 事实数 > 负样本误召回少。

    指标完全相同的链路全部返回——旧逻辑 max() 在并列时默认取第一个(A 纯 Dense)，
    会在报告里写出"纯 Dense 领先"这种并不成立的结论。
    """
    def key(t):
        s = stats[t]
        return (round(s["recall"], 6), round(s["mrr"], 6), s["facts"], -s["false_n"])
    best = max(key(t) for t in stats)
    return [t for t in stats if key(t) == best]


def _generate_retrieval_detail_report(
    report_path: Path,
    records: List[Dict[str, Any]],
    reranker_name: str = "Kimi3-reranker-8b",
    corpus: Optional[List[Document]] = None,
    rerank_granularity: str = "child",
    suite_label: str = "主题集"
):
    """生成"对抗题详细召回过程"报告。

    按"父子切片 Small-to-Big"的完整链路，逐题展示四个阶段的召回轨迹：
      ① Dense 子块匹配 -> ② BM25 子块匹配 -> ③ RRF 融合 -> ④ Rerank精排+按秩融合
    并标注每题命中的黄金考点、漏掉项、正确答案卡片，便于汇报讲解。
    """
    # ground truth：评测集显式标注的目标卡 id（负样本为 None，表示库内无答案）
    def ground_truth(record):
        return [record["target_id"]] if record.get("target_id") else []

    lines = [
        f"# Day13 · 对抗题详细召回过程报告（{suite_label}）",
        "",
        f"**检索架构**：父子切片（Small-to-Big）。子块（512字符行累加）做向量/关键词精确匹配，",
        f"命中后经 `expand_to_parents` 回溯父块（整卡全文）返回。精排模型：{reranker_name}，"
        f"精排粒度：{GRANULARITY_NAMES.get(rerank_granularity, rerank_granularity)}。",
        "",
        "> 说明：每题展示四阶段——① Dense 子块召回 ② BM25 子块召回 ③ RRF 融合 ④ Rerank精排+按秩融合，",
        "> 卡片 id 前的 `→` 表示“命中子块后回溯到的父块”。",
        "",
        "---",
    ]

    for r in records:
        tr = r["trace"]
        expected = r.get("expected", [])
        missed = tr.get("missed", [])
        gt = ground_truth(r)

        def _fmt_rank(rank, false, track=None):
            rejected = track == "full" and r.get("full_rejected")
            if not r["target_id"]:
                if rejected:
                    return "✅ 低置信拒答（正确）"
                return "❌ 误召回陷阱卡" if false else "✅ 未误召回（正确）"
            if rejected:
                return "❌ 低置信误拒答"
            return f"第 {rank} 位" if rank else "❌ 未召回"

        lines += [
            "",
            f"## [{r['id']}] {r['category']}（题型：{r['qtype']}）",
            "",
            f"- **查询**：`{r['query']}`",
        ]
        if r.get("rewrite") and r["rewrite"] != r["query"]:
            lines.append(f"- **改写查询**（全链路召回+精排使用）：`{r['rewrite']}`")
        if r.get("filter"):
            lines.append(f"- **元数据前置过滤**：`{r['filter']}`")
        if gt:
            lines.append(f"- **正确答案卡片**：{', '.join(gt)}")
        elif r["qtype"] == "negative":
            lines.append(f"- **正确答案卡片**：无（库外问题；陷阱卡：{', '.join(r['trap_ids'])}）")
        if r.get("confusable_with"):
            lines.append(f"- **易混淆兄弟卡**：{r['confusable_with']}")
        if expected:
            lines.append(f"- **黄金考点**：{'、'.join(f'`{x}`' for x in expected)}")
        lines.append("")
        lines.append("| 阶段 | 命中子块 → 回溯父块 | 分数 | 目标卡名次 |")
        lines.append("| :--- | :--- | :--- | :--- |")
        lines.append(f"| ① Dense 子块召回 | {'、'.join(tr['dense_child_ids'])} → **{'、'.join(tr['dense_parent_ids'])}** | {tr['dense_scores']} | {_fmt_rank(r['dense_rank'], r['dense_false'])} |")
        lines.append(f"| ② BM25 子块召回 | {'、'.join(tr['bm25_child_ids'])} → **{'、'.join(tr['bm25_parent_ids'])}** | {tr['bm25_scores']} | {_fmt_rank(r['bm25_rank'], r['bm25_false'])} |")
        lines.append(f"| ③ RRF 融合 | — → **{'、'.join(tr['rrf_parent_ids'])}** | — | {_fmt_rank(r['fused_rank'], r['fused_false'])} |")
        if r.get("full_rejected"):
            full_cell = f"— → **（拒答：候选最高原始分 {r['max_rerank']} < 阈值）**"
            score_cell = f"原始分最高 {r['max_rerank']}"
        else:
            full_cell = f"— → **{'、'.join(f'{i}🛡' if i in set(tr.get('protected_ids', [])) else i for i in tr['full_parent_ids'])}**"
            score_cell = f"融合分 {tr['full_fused_scores']}<br>原始 rerank 分 {tr.get('full_rerank_scores', [])}"
        lines.append(f"| ④ Rerank+按秩融合 | {full_cell} | {score_cell} | {_fmt_rank(r['full_rank'], r['full_false'], 'full')} |")
        lines.append("")
        sib = r.get("confusable_with")
        if sib:
            def _sib(ids):
                return f"第{ids.index(sib) + 1}位" if sib in ids else "未进Top-3"
            lines.append(f"- **兄弟卡 {sib} 名次**：Dense {_sib(r['dense_ids'])} / BM25 {_sib(r['bm25_ids'])} / "
                         f"RRF {_sib(r['fused_ids'])} / 全链路 {_sib(r['full_ids'])}")
        if expected:
            hits_txt = f"{r['full_hits']}/{r['expected_count']}（限目标卡内计数）"
            miss_txt = "、".join(f"`{x}`" for x in missed) if missed else "无"
            lines.append(f"- **最终命中**：{hits_txt}　**漏掉考点**：{miss_txt}")
        lines.append(f"- **挑战点**：{r['challenge']}")
        lines.append("")

    # 末尾汇总四轨卡级指标（与主报告同口径，由 records 现算，保证两份报告不打架）
    pos = [r for r in records if r["target_id"]]
    neg = [r for r in records if not r["target_id"]]
    n_pos = max(len(pos), 1)
    n_neg = max(len(neg), 1)
    total_exp = sum(r["expected_count"] for r in pos)

    def _sum_row(tag, name):
        hit_n = sum(1 for r in pos if r[f"{tag}_rank"])
        mrr = sum(1.0 / r[f"{tag}_rank"] for r in pos if r[f"{tag}_rank"]) / n_pos
        facts = sum(r[f"{tag}_hits"] for r in pos)
        false_n = sum(1 for r in neg if r[f"{tag}_false"])
        return (f"| {name} | {hit_n} / {len(pos)} | {hit_n / n_pos:.1%} | {mrr:.2f} "
                f"| {facts} / {total_exp} | {false_n} / {len(neg)} |")

    lines += [
        "---",
        "",
        "## 四轨卡级指标汇总",
        "",
        "> 卡级口径：目标卡进 Top-3 记命中（Recall@3），名次越前 MRR 越高；",
        "> 事实命中只在检索到的目标卡正文内计数；负样本看是否误召回陷阱卡。",
        "",
        "| 链路 | 卡级命中 | Recall@3 | MRR | 事实覆盖(限目标卡) | 负样本误召回 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
        _sum_row("dense", "A 纯 Dense"),
        _sum_row("bm25", "B 纯 BM25"),
        _sum_row("fused", "C RRF 融合"),
        _sum_row("full", "D 全链路(+Rerank)"),
        "",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _generate_markdown_report(
    report_path: Path,
    records: List[Dict[str, Any]],
    stats: Dict[str, Dict[str, Any]],
    total_expected: int,
    n_pos: int,
    n_neg: int,
    reranker_name: str = "qwen3-reranker-8b",
    avg_latency: Optional[Dict[str, float]] = None,
    reject_threshold: Optional[float] = None,
    rerank_granularity: str = "child",
    suite_label: str = "主题集"
):
    # 数据驱动：真实最优链路才标 🏆；指标完全相同时如实标"并列"，不默认偏向第一条
    winners = pick_winners(stats)
    tied = len(winners) > 1
    best = stats[winners[0]]
    label = ("并列：" if tied else "") + "、".join(
        f"{TRACK_LABELS[t]}+{reranker_name}" if t == "full" else TRACK_LABELS[t] for t in winners
    )

    def crown(tag):
        s = stats[tag]
        txt = f"{s['hit_n']} / {n_pos}（{s['recall']:.1%}）"
        if tag not in winners:
            return txt
        return f"**🏆{'(并列)' if tied else ''} {txt}**"

    def mrr_s(tag):
        return f"**{stats[tag]['mrr']:.2f}**"

    def fact_s(tag):
        return f"{stats[tag]['facts']} / {total_expected}"

    def false_s(tag):
        return f"{stats[tag]['false_n']} / {n_neg}"

    def lat(tag):
        # 真实平均端到端延迟（由调用方从每题实测均值传入），不再写死
        v = (avg_latency or {}).get(tag)
        return f"{v}ms" if v is not None else "-"

    full = stats["full"]
    # 全链路是否只靠"负样本拒答"胜出（Recall/MRR/事实与某条链路打平）
    wins_by_reject = any(
        (round(stats[t]["recall"], 6), round(stats[t]["mrr"], 6), stats[t]["facts"])
        == (round(full["recall"], 6), round(full["mrr"], 6), full["facts"])
        for t in stats if t != "full"
    )
    if winners == ["full"] and wins_by_reject:
        d_note = (f"正样本卡级指标与召回侧并列满分；差异在库外负样本——原始 rerank 分低于阈值即拒答，"
                  f"误召回 {full['false_n']} / {n_neg}")
        concl3 = (f"{reranker_name} 在正样本排序上与 RRF 打平（本库主题区分度高，RRF 已排对），"
                  f"其独有价值在于原始相关度分可用于**低置信拒答**：库外问题的最高分明显低于库内问题，"
                  f"按阈值 {reject_threshold} 拒答后负样本误召回降至 {full['false_n']} / {n_neg}，"
                  f"而 Dense/BM25/RRF 只能给出名次、无法判断\"像不像\"，必然把最像的 3 张卡塞给 LLM。")
    elif winners == ["full"]:
        d_note = "卡级 Recall@3 与 MRR 居四轨之首，Top-1 黄金上下文相关度置信度最高"
        concl3 = (f"{reranker_name} 对候选 Top-15 片段进行交叉注意力重排，再与召回侧 RRF 名次按秩加权融合，"
                  f"既保留精排精度又避免精排单点误判把正确切片挤出 Top-3，全链路综合指标居四轨之首。")
    elif "full" in winners:
        d_note = "与其他链路卡级指标并列最优；精排增益需看近邻混淆题与负样本拒答"
        concl3 = (f"本轮 {label} 卡级指标完全相同，说明题集在这些链路之间没有拉开差距，"
                  f"不能据此断言精排有增益或无增益；请重点看近邻混淆题(confusable)的兄弟卡名次"
                  f"与负样本的低置信拒答结果，那才是 {reranker_name} 独有的贡献点。")
    else:
        d_note = ("RRF 与 Rerank 名次加权融合后兼顾召回与精度；当事实分散于多个小节时，"
                  "融合排序以召回侧信号托底，避免正确切片被挤出 Top-3")
        concl3 = (f"{reranker_name} 精排提升了 Top-1 相关度精度；再将其名次与召回侧 RRF 名次按秩加权融合"
                  f"（召回侧 0.6 / 精排侧 0.4，小 k 增强区分度）后，即便精排在个别多约束查询上误判，"
                  f"召回侧的稳定名次也能把正确切片托住——这正是工业实践中 rerank 主精度、RRF 主召回、融合兜底的工程取舍。"
                  f"本轮实测中 {label} 的卡级指标反而领先，如实记录，不做美化。")

    # 双路互补：按本轮真实名次统计"一路排第 1、另一路掉出第 1"的题，不再写死题号
    pos_all = [r for r in records if r["target_id"]]
    bm25_only = [r["id"] for r in pos_all if r["bm25_rank"] == 1 and r["dense_rank"] != 1]
    dense_only = [r["id"] for r in pos_all if r["dense_rank"] == 1 and r["bm25_rank"] != 1]
    full_rescue = [r["id"] for r in pos_all if r["full_rank"] == 1 and r["fused_rank"] != 1]
    parts = []
    if bm25_only:
        parts.append(f"BM25 排第 1 而 Dense 未排第 1：{'、'.join(bm25_only)}（字面硬匹配补位）")
    if dense_only:
        parts.append(f"Dense 排第 1 而 BM25 未排第 1：{'、'.join(dense_only)}（语义对齐补位）")
    if full_rescue:
        parts.append(f"RRF 未排第 1、全链路纠正到第 1：{'、'.join(full_rescue)}（改写/精排增益）")
    complement_txt = "；".join(parts) + "。" if parts else "本轮各通道在正样本上名次一致，未观测到互补补位。"

    # 原始 rerank 分分布：标定低置信拒答阈值的依据（正样本最低分应明显高于负样本最高分）
    pos_recs = [r for r in records if r["target_id"]]
    neg_recs = [r for r in records if not r["target_id"]]
    th_txt = f"`{reject_threshold}`" if reject_threshold is not None else "未启用（`retrieval.reject_threshold: null`）"
    score_rows = []
    for r in records:
        if r["target_id"]:
            verdict = "❌ 误拒答" if r.get("full_rejected") else ("✅ 放行" if r["full_rank"] else "放行但未命中")
        else:
            verdict = "✅ 拒答" if r.get("full_rejected") else "❌ 放行（误召回风险）"
        if not r.get("rerank_remote", True):
            verdict = "⚠️ 精排降级为启发式，阈值未生效"
        top1 = r.get("top1_rerank")
        score_rows.append(f"| {r['id']} | {QTYPE_NAMES.get(r['qtype'], r['qtype'])} | {r.get('max_rerank', 0.0)} "
                          f"| {top1 if top1 is not None else '—'} | {verdict} |")
    if pos_recs and neg_recs:
        pos_min = min(r.get("max_rerank", 0.0) for r in pos_recs)
        neg_max = max(r.get("max_rerank", 0.0) for r in neg_recs)
        gap_txt = (f"正样本最高分的最小值 **{pos_min}**，负样本最高分的最大值 **{neg_max}**——"
                   + ("两者之间存在可切分区间，阈值取在区间内即可同时放行全部正样本、拒答全部负样本。"
                      if pos_min > neg_max else
                      "两者重叠，单一绝对阈值无法无损切分，需在误拒答与误召回之间取舍。"))
    else:
        gap_txt = "正/负样本不全，无法评估可切分区间。"
    score_section = "\n".join([
        "## 三、 原始 Rerank 分分布与低置信拒答",
        "",
        f"> 按秩融合分被 1/(fuse_k+1) 封顶，只反映名次；下表的**原始 rerank 分**才反映精排对\"相关与否\"的把握。",
        f"> 当前拒答阈值：{th_txt}。规则：候选集原始最高分低于阈值时，全链路返回空结果（拒答）。",
        "",
        "| 题号 | 题型 | 候选最高原始分 | 最终 Top-1 原始分 | 拒答判定 |",
        "| :--- | :--- | :---: | :---: | :--- |",
        *score_rows,
        "",
        f"**可切分性**：{gap_txt}",
        "",
        "⚠️ 讲义第六篇记录过远程 reranker 绝对分整体漂移的情况；阈值依赖绝对分，换模型/换服务后须按本表重新标定。",
        "",
        "---",
        "",
    ])

    content = f"""# Day 13 纯向量检索 vs 混合检索+重排 召回率对比实验报告

**所属项目**：企业 IT 常见问题知识库 RAG 检索基座工程
**实验日期**：{date.today().isoformat()}
**知识库**：《IT常见问题RAG知识库.docx》→ Day 11 清洗重构的 35 张 Wiki 卡片 → Day 12 结构感知切块
**测试引擎**：Chroma 向量数据库 + BM25Okapi 倒排索引 + RRF (k=60) + {reranker_name} (KSP /rerank，精排粒度：{GRANULARITY_NAMES.get(rerank_granularity, rerank_granularity)})
**评测集**：{suite_label}　**构成**：{n_pos} 道正样本 + {n_neg} 道负样本（{suite_breakdown(records)}）
**综合最优链路**：{label}（Recall@3 {best['recall']:.1%}, MRR {best['mrr']:.2f}）

> **指标口径说明（为什么不再是 100%）**：本版评测已废弃旧的"Top-3 拼接文本子串覆盖"口径——
> 该口径下高频通用词（"时间/地址/停止"等）在错误卡片上也会误命中，四轨必然满分、无区分度。
> 现行口径：
> - **卡级 Recall@3**：目标卡 `wiki_id` 是否进入回溯父块 Top-3；
> - **MRR**：目标卡名次的倒数均值，区分"排第 1"与"排第 3"；
> - **事实覆盖（限目标卡）**：黄金考点只在检索到的目标卡正文内计数，目标卡未召回记 0；
> - **负样本误召回**：库外问题若 Top-3 命中预设陷阱卡，记一次误召回；全链路低置信拒答（返回空）不算误召回；
> - **近邻混淆题**：query 字面贴近兄弟卡，额外报告兄弟卡名次，用于观察精排能否把兄弟卡压到目标卡之后。

---

## 一、 实验总览与核心指标大盘

| 检索机制链路架构 | 卡级 Recall@3 | MRR | 事实覆盖(限目标卡) | 负样本误召回 | 平均端到端延迟 | 架构技术定性分析 |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **链路 A：纯 Dense 向量检索** | {crown('dense')} | {mrr_s('dense')} | {fact_s('dense')} | {false_s('dense')} | {lat('dense')} | 命令/错误码/端口/事件ID 等专有编号易漂移脱靶；同义改写题是其主场 |
| **链路 B：纯 BM25 关键词检索** | {crown('bm25')} | {mrr_s('bm25')} | {fact_s('bm25')} | {false_s('bm25')} | {lat('bm25')} | 得益于 Day 11 术语归一化，硬编号命中佳；但同义改写与抽象因果句检索受限 |
| **链路 C：双路粗排 + RRF 融合** | {crown('fused')} | {mrr_s('fused')} | {fact_s('fused')} | {false_s('fused')} | {lat('fused')} | 兼得两路之长，多样性融合召回率高，但未做精细相关度重排 |
| **链路 D：顶级全链路 (+ {reranker_name})** | {crown('full')} | {mrr_s('full')} | {fact_s('full')} | {false_s('full')} | {lat('full')} | {d_note} |

---

## 二、 {len(records)} 组对抗评测明细 (Golden Hard Benchmark)

"""
    for r in records:
        if r["target_id"]:
            sib = r.get("confusable_with")

            def _rk(tag):
                if tag == "full" and r.get("full_rejected"):
                    return "低置信误拒答"
                rank = r[f"{tag}_rank"]
                txt = f"第{rank}位" if rank else "未召回"
                if sib:
                    ids = r[f"{tag}_ids"]
                    txt += f"｜兄弟卡{'第' + str(ids.index(sib) + 1) + '位' if sib in ids else '未进Top-3'}"
                return txt
            sib_line = f"\n- **易混淆兄弟卡**：`{sib}`" if sib else ""
            detail = f"""### [{r['id']}] {r['category']}（{r['qtype']}）
- **业务查询**：`{r['query']}`
- **目标卡片**：`{r['target_id']}`{sib_line}
- **对抗难点与挑战**：`{r['challenge']}`
- **各链路 Top-3 目标卡名次对比**：
  - 纯向量检索 (Dense)：**{_rk('dense')}**（事实命中 {r['dense_hits']}/{r['expected_count']}，{r['dense_time']}ms）
  - 纯关键词检索 (BM25)：**{_rk('bm25')}**（事实命中 {r['bm25_hits']}/{r['expected_count']}，{r['bm25_time']}ms）
  - RRF 倒数融合：**{_rk('fused')}**（事实命中 {r['fused_hits']}/{r['expected_count']}）
  - **顶级全链路 (+ Rerank)**：**{_rk('full')}**（事实命中 {r['full_hits']}/{r['expected_count']}，Top-1 融合分 {r['top1_score']}，Top-1 原始 rerank 分 {r.get('top1_rerank')}）

---
"""
        else:
            def _fr(tag):
                if tag == "full" and r.get("full_rejected"):
                    return "✅ 低置信拒答"
                return "❌ 误召回陷阱卡" if r[f"{tag}_false"] else "✅ 未误召回"
            detail = f"""### [{r['id']}] {r['category']}（negative·库外问题）
- **业务查询**：`{r['query']}`
- **目标卡片**：无（知识库确无答案；陷阱卡：{'、'.join(f'`{t}`' for t in r['trap_ids'])}）
- **对抗难点与挑战**：`{r['challenge']}`
- **各链路误召回判定**：
  - 纯向量检索 (Dense)：{_fr('dense')}
  - 纯关键词检索 (BM25)：{_fr('bm25')}
  - RRF 倒数融合：{_fr('fused')}
  - **顶级全链路 (+ Rerank)**：**{_fr('full')}**（候选最高原始 rerank 分 {r.get('max_rerank')}）

---
"""
        content += detail

    content += score_section
    content += f"""## 四、 核心架构总结与技术承接

1. **双路召回的互补性（本轮数据）**：
   {complement_txt}
2. **RRF 倒数排名融合的鲁棒性**：
   通过常数 $k=60$ 的倒数打分，无需调参即完美化解了余弦分（0~1）与 BM25 分（0~30+）异构打分冲突，多样性融合在事实分散题面上召回率领先。
3. **Cross-Encoder 精排的定位**：
   {concl3}
4. **评测方法论沉淀**：
   本轮评测弃用了"子串覆盖率"这一饱和口径，改用卡级 Recall@3 / MRR / 限目标卡事实覆盖 + 负样本误召回四项指标，
   并补充同义改写题与库外负样本题——题库与语料同源、期望词含高频通用词时，任何链路的"100%"都不可信。
5. **技术承接预告**：
   - **Day 14**：我们将基于此高召回检索基座，构建企业级自动化**黄金问题集（Golden Dataset）与 RAGAS/TruLens 评测流水线**！
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)


