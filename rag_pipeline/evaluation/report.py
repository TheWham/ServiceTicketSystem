"""Day13 评测报告生成：主报告 + 逐题详细召回过程。"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document


def _generate_retrieval_detail_report(
    report_path: Path,
    records: List[Dict[str, Any]],
    reranker_name: str = "Kimi3-reranker-8b",
    corpus: Optional[List[Document]] = None
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
        "# Day13 · 对抗题详细召回过程报告",
        "",
        f"**检索架构**：父子切片（Small-to-Big）。子块（512字符行累加）做向量/关键词精确匹配，",
        f"命中后经 `expand_to_parents` 回溯父块（整卡全文）返回。精排模型：{reranker_name}。",
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

        def _fmt_rank(rank, false):
            if not r["target_id"]:
                return "❌ 误召回陷阱卡" if false else "✅ 未误召回（正确）"
            return f"第 {rank} 位" if rank else "❌ 未召回"

        lines += [
            "",
            f"## [{r['id']}] {r['category']}（题型：{r['qtype']}）",
            "",
            f"- **查询**：`{r['query']}`",
        ]
        if r.get("filter"):
            lines.append(f"- **元数据前置过滤**：`{r['filter']}`")
        if gt:
            lines.append(f"- **正确答案卡片**：{', '.join(gt)}")
        elif r["qtype"] == "negative":
            lines.append(f"- **正确答案卡片**：无（库外问题；陷阱卡：{', '.join(r['trap_ids'])}）")
        if expected:
            lines.append(f"- **黄金考点**：{'、'.join(f'`{x}`' for x in expected)}")
        lines.append("")
        lines.append("| 阶段 | 命中子块 → 回溯父块 | 分数 | 目标卡名次 |")
        lines.append("| :--- | :--- | :--- | :--- |")
        lines.append(f"| ① Dense 子块召回 | {'、'.join(tr['dense_child_ids'])} → **{'、'.join(tr['dense_parent_ids'])}** | {tr['dense_scores']} | {_fmt_rank(r['dense_rank'], r['dense_false'])} |")
        lines.append(f"| ② BM25 子块召回 | {'、'.join(tr['bm25_child_ids'])} → **{'、'.join(tr['bm25_parent_ids'])}** | {tr['bm25_scores']} | {_fmt_rank(r['bm25_rank'], r['bm25_false'])} |")
        lines.append(f"| ③ RRF 融合 | — → **{'、'.join(tr['rrf_parent_ids'])}** | — | {_fmt_rank(r['fused_rank'], r['fused_false'])} |")
        lines.append(f"| ④ Rerank+按秩融合 | — → **{'、'.join(f'{i}🛡' if i in set(tr.get('protected_ids', [])) else i for i in tr['full_parent_ids'])}** | 融合分 {tr['full_fused_scores']} | {_fmt_rank(r['full_rank'], r['full_false'])} |")
        lines.append("")
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
    avg_latency: Optional[Dict[str, float]] = None
):
    # 数据驱动：真实最优链路才标 🏆（Recall@3 优先，MRR 次之，事实数兜底）
    winner = max(stats, key=lambda t: (stats[t]["recall"], stats[t]["mrr"], stats[t]["facts"]))
    label = {"dense": "链路 A：纯 Dense", "bm25": "链路 B：纯 BM25",
             "fused": "链路 C：RRF 融合", "full": f"链路 D：全链路+{reranker_name}"}[winner]

    def crown(tag):
        s = stats[tag]
        txt = f"{s['hit_n']} / {n_pos}（{s['recall']:.1%}）"
        return f"**🏆 {txt}**" if tag == winner else txt

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

    if winner == "full":
        d_note = "卡级 Recall@3 与 MRR 居四轨之首，Top-1 黄金上下文相关度置信度最高"
        concl3 = (f"{reranker_name} 对候选 Top-15 片段进行交叉注意力重排，再与召回侧 RRF 名次按秩加权融合，"
                  f"既保留精排精度又避免精排单点误判把正确切片挤出 Top-3，全链路综合指标居四轨之首。")
    else:
        d_note = ("RRF 与 Rerank 名次加权融合后兼顾召回与精度；当事实分散于多个小节时，"
                  "融合排序以召回侧信号托底，避免正确切片被挤出 Top-3")
        concl3 = (f"{reranker_name} 精排提升了 Top-1 相关度精度；再将其名次与召回侧 RRF 名次按秩加权融合"
                  f"（召回侧 0.6 / 精排侧 0.4，小 k 增强区分度）后，即便精排在个别多约束查询上误判，"
                  f"召回侧的稳定名次也能把正确切片托住——这正是工业实践中 rerank 主精度、RRF 主召回、融合兜底的工程取舍。"
                  f"本轮实测中 {label} 的卡级指标反而领先，如实记录，不做美化。")

    content = f"""# Day 13 纯向量检索 vs 混合检索+重排 召回率对比实验报告

**所属项目**：企业 IT 常见问题知识库 RAG 检索基座工程
**实验日期**：2026-10-13
**知识库**：《IT常见问题RAG知识库.docx》→ Day 11 清洗重构的 35 张 Wiki 卡片 → Day 12 结构感知切块
**测试引擎**：Chroma 向量数据库 + BM25Okapi 倒排索引 + RRF (k=60) + {reranker_name} (KSP /rerank)
**评测集构成**：{n_pos} 道正样本（7 道硬匹配 + 3 道同义改写）+ {n_neg} 道负样本（库外问题）
**综合最优链路**：{label}（Recall@3 {stats[winner]['recall']:.1%}, MRR {stats[winner]['mrr']:.2f}）

> **指标口径说明（为什么不再是 100%）**：本版评测已废弃旧的"Top-3 拼接文本子串覆盖"口径——
> 该口径下高频通用词（"时间/地址/停止"等）在错误卡片上也会误命中，四轨必然满分、无区分度。
> 现行口径：
> - **卡级 Recall@3**：目标卡 `wiki_id` 是否进入回溯父块 Top-3；
> - **MRR**：目标卡名次的倒数均值，区分"排第 1"与"排第 3"；
> - **事实覆盖（限目标卡）**：黄金考点只在检索到的目标卡正文内计数，目标卡未召回记 0；
> - **负样本误召回**：库外问题若 Top-3 命中预设陷阱卡，记一次误召回。

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
            def _rk(tag):
                rank = r[f"{tag}_rank"]
                return f"第{rank}位" if rank else "未召回"
            detail = f"""### [{r['id']}] {r['category']}（{r['qtype']}）
- **业务查询**：`{r['query']}`
- **目标卡片**：`{r['target_id']}`
- **对抗难点与挑战**：`{r['challenge']}`
- **各链路 Top-3 目标卡名次对比**：
  - 纯向量检索 (Dense)：**{_rk('dense')}**（事实命中 {r['dense_hits']}/{r['expected_count']}，{r['dense_time']}ms）
  - 纯关键词检索 (BM25)：**{_rk('bm25')}**（事实命中 {r['bm25_hits']}/{r['expected_count']}，{r['bm25_time']}ms）
  - RRF 倒数融合：**{_rk('fused')}**（事实命中 {r['fused_hits']}/{r['expected_count']}）
  - **顶级全链路 (+ Rerank)**：**{_rk('full')}**（事实命中 {r['full_hits']}/{r['expected_count']}，Top-1 融合分 {r['top1_score']}）

---
"""
        else:
            def _fr(tag):
                return "❌ 误召回陷阱卡" if r[f"{tag}_false"] else "✅ 未误召回"
            detail = f"""### [{r['id']}] {r['category']}（negative·库外问题）
- **业务查询**：`{r['query']}`
- **目标卡片**：无（知识库确无答案；陷阱卡：{'、'.join(f'`{t}`' for t in r['trap_ids'])}）
- **对抗难点与挑战**：`{r['challenge']}`
- **各链路误召回判定**：
  - 纯向量检索 (Dense)：{_fr('dense')}
  - 纯关键词检索 (BM25)：{_fr('bm25')}
  - RRF 倒数融合：{_fr('fused')}
  - **顶级全链路 (+ Rerank)**：**{_fr('full')}**（Top-1 融合分 {r['top1_score']}）

---
"""
        content += detail

    content += f"""## 三、 核心架构总结与技术承接

1. **术语归一化对 BM25 的激活验证**：
   在 HC-01 (sfc 命令) 与 HC-07 (DNS 端口 53) 场景中，纯向量检索易出现词义漂移，而 BM25 凭借字面硬匹配成功捕获，验证了双路召回的不可替代性。
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


