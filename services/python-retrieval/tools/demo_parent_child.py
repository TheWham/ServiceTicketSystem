# -*- coding: utf-8 -*-
"""父子切片（Small-to-Big）演示脚本：真实切块 + 线上同款检索内核逐阶段留痕。

产出两份 Markdown（供汇报演示）：
1. artifacts/demo/parent_child_chunks_demo.md     —— 一张 Wiki 卡怎么被切成父块+子块
2. artifacts/demo/parent_child_retrieval_demo.md  —— 一次检索从双路召回到最终父块的全程

用法：
    python tools/demo_parent_child.py [--card ITKB-VPN-001] [--query "在家连不上VPN怎么办"]
"""

import argparse
import contextlib
import io
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rag_pipeline.config import load_config, build_chunker, build_gate  # noqa: E402

OUT_DIR = REPO_ROOT / "artifacts" / "demo"


def demo_chunking(card_name: str) -> Path:
    """第一部分：对单张 Wiki 卡执行父子切块，输出父块+子块明细。"""
    from rag_pipeline.chunking.parent_child import ParentChildChunker

    cfg = load_config()
    cc = cfg.chunking
    chunker, _ = build_chunker(cfg)
    assert isinstance(chunker, ParentChildChunker), "pipeline.yaml 需配置 strategy=parent_child"

    card_path = REPO_ROOT / "artifacts/output/wiki" / f"{card_name}.md"
    parent, children = chunker.split_wiki_document(str(card_path))
    raw = card_path.read_text(encoding="utf-8")

    lines = [
        "# 父子切块演示——真实切块结果",
        "",
        f"> 演示卡片：`{card_name}.md`　生成时间：{datetime.now():%Y-%m-%d %H:%M}",
        f"> 配置：child_size={cc.child_size}｜section_header_level=H{cc.section_header_level}"
        f"｜merge_preamble={cc.merge_preamble}｜boost_injection={cc.boost_injection}"
        f"｜breadcrumb_header={cc.breadcrumb_header}｜strip_trace_tail={cc.strip_trace_tail}",
        "",
        "## 0. 输入：原始 Wiki 卡片",
        "",
        "```markdown",
        raw.rstrip(),
        "```",
        "",
        "---",
        "",
        "## 1. 父块（整卡正文，最终交给 LLM 的上下文）",
        "",
        f"- `parent_id`：`{parent.metadata['parent_id']}`",
        f"- `chunk_role`：`{parent.metadata['chunk_role']}`",
        f"- 正文长度：{len(parent.page_content)} 字符（= 剥离 frontmatter 后的全文，含溯源尾）",
        "",
        "```markdown",
        parent.page_content.rstrip(),
        "```",
        "",
        "---",
        "",
        f"## 2. 子块（共 {len(children)} 个，向量匹配单元）",
        "",
        "| # | child_id | 所属小节 Header_2 | 长度 | 含检索增强行 | 开头预览 |",
        "|---|---|---|---|---|---|",
    ]
    for i, c in enumerate(children):
        md = c.metadata
        boost = "是" if c.page_content.startswith("【检索增强") else "否"
        preview = " ".join(c.page_content.split())[:40]
        lines.append(
            f"| {i} | `{md['child_id']}` | {md['Header_2']} | {md['chunk_length']} | {boost} | {preview}… |"
        )

    lines += ["", "### 每个子块的完整内容与 metadata", ""]
    for i, c in enumerate(children):
        md = c.metadata
        lines += [
            f"#### 子块 {i}：`{md['child_id']}`",
            "",
            "**完整 metadata（与 chroma.sqlite3 中存储的逐字段一致，已解耦剥离 parent_content，轻量化入库）：**",
            "",
            "```json",
            json.dumps(md, ensure_ascii=False, indent=2),
            "```",
            "",
            f"- 要点：`parent_id` 作为外键指向 MySQL Docstore（`rag_parent_docstore` 表），向量库不存父块全文；"
            f"`wiki_status` 等字段供检索时元数据硬过滤（剔除已废止卡）",
            "",
            "**实际参与向量化的文本（含上下文头）：**",
            "",
            "```markdown",
            c.page_content.rstrip(),
            "```",
            "",
        ]

    out = OUT_DIR / "parent_child_chunks_demo.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def demo_retrieval(query: str) -> Path:
    """第二部分：走线上同一条检索链路（ServiceAssembly），逐阶段记录结果。"""
    from rag_service.assembly import ServiceAssembly

    asm = ServiceAssembly()
    cfg, rc = asm.cfg, asm.cfg.retrieval

    # 阶段 A：查询改写（与线上同款 QueryRewriter，失败自动跳过）
    rewrite = asm.rewriter.rewrite(query) if asm.rewriter else None

    # 阶段 B~E：双路召回 -> RRF -> 精排 -> 融合（verbose 输出即逐阶段过程）
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = asm.retriever.hybrid_rerank_search(
            query=query,
            final_top_k=rc.top_k,
            rrf_k=rc.rrf_k,
            rough_top_k=rc.rough_top_k,
            fuse_k=rc.fuse_k,
            rrf_weight=rc.rrf_weight,
            rerank_weight=rc.rerank_weight,
            reject_threshold=rc.reject_threshold,
            heuristic_reject_threshold=rc.heuristic_reject_threshold,
            rerank_granularity=rc.rerank_granularity,
            rewrite_query=rewrite,
            gate=build_gate(rc),
            verbose=True,
        )

    def brief(item, w=100):
        t = " ".join(item["content"].split())
        return t[:w] + ("…" if len(t) > w else "")

    lines = [
        "# 检索流程演示——一次真实检索的逐阶段结果",
        "",
        f"> 查询：`{query}`　生成时间：{datetime.now():%Y-%m-%d %H:%M}",
        f"> 配置：rough_top_k={rc.rough_top_k}｜rrf_k={rc.rrf_k}｜精排粒度={rc.rerank_granularity}"
        f"｜gate_enabled={rc.gate_enabled}｜query_rewrite={rc.query_rewrite}",
        "",
        "## 阶段 A：查询改写（query_rewriter.py）",
        "",
    ]
    if rewrite and rewrite != query:
        lines += [f"原查询：`{query}`", "", f"改写查询：`{rewrite}`", ""]
    elif rewrite:
        lines += [f"改写返回与原查询一致：`{query}`（未产生实质改写，四路召回退化为两路）", ""]
    else:
        lines += ["（本次改写未启用/未成功——线上行为：改写失败自动跳过，仅双路原查询召回）", ""]
    lines += [
        "## 阶段 B~E：内核逐阶段过程（hybrid.py verbose 实录）",
        "",
        "```",
        buf.getvalue().rstrip(),
        "```",
        "",
        "## 最终结果结构化明细",
        "",
        f"- 双路召回：BM25 {res['bm25_count']} 个 / Dense {res['dense_count']} 个，"
        f"RRF 融合后候选 {res['fused_count']} 个",
        f"- 精排粒度：{res['granularity']}｜置信度门控：{res['gate_mode']}"
        f"（margin={res['gate_margin']}，生效权重 RRF {res['eff_weights'][0]} : Rerank {res['eff_weights'][1]}）",
        f"- rerank 远程/降级：{'远程模型' if res['rerank_remote'] else '启发式降级'}，"
        f"最高精排分 {res['max_rerank_score']}",
        f"- 低置信拒答：{'触发' if res['rejected'] else '未触发'}｜耗时 {res['latency_ms']} ms",
        "",
        "| # | 命中子块 child_id | RRF名次 | Rerank名次 | 融合分 | 内容预览 |",
        "|---|---|---|---|---|---|",
    ]
    for i, it in enumerate(res["final_results"], 1):
        md = it["metadata"]
        lines.append(
            f"| {i} | `{md.get('child_id', '?')}` | {it['rrf_rank']} | {it['rerank_rank']} "
            f"| {it['fused_score']:.6f} | {brief(it)} |"
        )

    lines += [
        "",
        "## 阶段 F：Small-to-Big 回溯（MySQL Docstore / mapping.py）",
        "",
        "返回给下游的 content 一律取 MySQL Docstore / parent_content（整卡全文）：",
        "",
    ]
    for i, it in enumerate(res["final_results"], 1):
        md = it["metadata"]
        pc = it.get("parent_content") or md.get("parent_content", "")
        lines += [
            f"### 结果 {i}：子块 `{md.get('child_id', '?')}` → 父卡 `{md.get('parent_id', '?')}`",
            "",
            f"（父卡全文 {len(pc)} 字符，返回给 LLM 的上下文完整无截断）开头预览：",
            "",
            "```markdown",
            " ".join(pc.split())[:200] + ("…" if len(pc) > 200 else ""),
            "```",
            "",
        ]

    out = OUT_DIR / "parent_child_retrieval_demo.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default="ITKB-VPN-001")
    ap.add_argument("--query", default="在家连不上VPN，提示认证失败怎么办")
    ap.add_argument("--chunks-only", action="store_true", help="只重跑切块演示，不覆盖检索演示")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p1 = demo_chunking(args.card)
    print(f"✅ 切块演示已写入 {p1}")
    if not args.chunks_only:
        p2 = demo_retrieval(args.query)
        print(f"✅ 检索演示已写入 {p2}")


if __name__ == "__main__":
    main()
