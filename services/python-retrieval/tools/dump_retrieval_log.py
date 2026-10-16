#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dump_retrieval_log.py — 把检索全流程日志（5 环节）落盘到一个 md 文件，供汇报翻看。

跑每道题的全链路检索（hybrid_rerank_search verbose=True），把 5 环节日志
（向量检索 / 全文检索 / RRF / Rerank / 按秩融合）捕获后写入一个 Markdown 文件，
避免控制台刷屏。每个题目一个代码块，汇报时直接翻文件即可。

用法（在 D:\\day12\\demos 目录下）：
  python tools/dump_retrieval_log.py                  # 全部 12 题
  python tools/dump_retrieval_log.py --ids HC-01 HC-10  # 只跑指定题
  python tools/dump_retrieval_log.py --out 我的日志.md  # 自定义输出路径
"""

import sys
import io
import json
import argparse
import contextlib
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import warnings
warnings.filterwarnings("ignore")

from langchain_community.vectorstores import Chroma
from rag_pipeline.config import load_config, build_chunker, WIKI_DIR, INDEXING_OUTPUT, EVALUATION_OUTPUT, load_rerank_config
from rag_pipeline.embedding import KspEmbeddingProvider
from rag_pipeline.chunking.fingerprint import compute_wiki_fingerprint
from rag_pipeline.retrieval.hybrid import IndustrialHybridRetriever
from rag_pipeline.evaluation.suite import HARD_BENCHMARK_SUITE


def build_retriever():
    """装配与主流水线一致的混合检索器（config -> 切块 -> 嵌入 -> Chroma -> retriever）。"""
    cfg = load_config()
    reranker_model = load_rerank_config().get("model") or cfg.reranker_model
    project_root = Path(__file__).resolve().parent.parent
    wiki_path = WIKI_DIR
    chroma_path = INDEXING_OUTPUT / "chroma_wiki_structured"

    print(f"[1/3] 载入知识基座与向量库 ...")
    chunker, use_parent_child = build_chunker(cfg)
    embed_provider = KspEmbeddingProvider(cache_dir=str(project_root / cfg.embedding_cache_dir))

    wiki_files = sorted(wiki_path.glob("*.md"))
    wiki_files = [f for f in wiki_files if f.name != "_index.md"]
    if not wiki_files:
        raise FileNotFoundError(f"未在 {wiki_path} 找到 Wiki 卡片，请先跑清洗/建库流水线")

    all_chunks = []
    for wf in wiki_files:
        if use_parent_child:
            _p, children = chunker.split_wiki_document(str(wf))
            all_chunks.extend(children)
        else:
            all_chunks.extend(chunker.split_wiki_document(str(wf)))
    print(f"      -> Wiki 卡片 {len(wiki_files)} 篇 → 切片 {len(all_chunks)} 块")

    # manifest 指纹校验（同主流水线），不一致则重建内存索引
    stale_reason = None
    manifest_file = chroma_path / "manifest.json"
    if chroma_path.exists() and compute_wiki_fingerprint is not None:
        if not manifest_file.exists():
            stale_reason = "无 manifest"
        else:
            try:
                saved = json.loads(manifest_file.read_text(encoding="utf-8"))
                if saved.get("wiki_fingerprint") != compute_wiki_fingerprint(wiki_files):
                    stale_reason = "Wiki 卡片内容已变更"
                elif saved.get("config_fingerprint") and \
                        saved["config_fingerprint"] != config_fingerprint_of(cfg):
                    stale_reason = "切片配置已变更"
            except Exception as e:
                stale_reason = f"manifest 读取失败({e})"

    if chroma_path.exists() and stale_reason is None:
        try:
            vector_db = Chroma(persist_directory=str(chroma_path),
                               embedding_function=embed_provider,
                               collection_name="wiki_structured_kb")
            print(f"      -> 加载持久化 Chroma 成功：{chroma_path.name}")
        except Exception as e:
            print(f"      ⚠️ 加载 Chroma 警告({e})，重建内存索引")
            vector_db = Chroma.from_documents(all_chunks, embed_provider, collection_name="wiki_structured_kb")
    else:
        if stale_reason:
            print(f"      ⚠️ 向量库与语料不一致（{stale_reason}），重建内存索引")
        vector_db = Chroma.from_documents(all_chunks, embed_provider, collection_name="wiki_structured_kb")

    print(f"[2/3] 装配 IndustrialHybridRetriever ...")
    retriever = IndustrialHybridRetriever(
        vector_db=vector_db,
        corpus_docs=all_chunks,
        reranker_model_name=reranker_model,
        default_exclude=cfg.retrieval.default_exclude,
    )
    return retriever, cfg


def config_fingerprint_of(cfg):
    from rag_pipeline.config import config_fingerprint
    return config_fingerprint(cfg)


def main():
    parser = argparse.ArgumentParser(description="把检索全流程日志落盘到 md 文件")
    parser.add_argument("--ids", nargs="*", default=None, help="只跑指定题号（如 HC-01 HC-10）")
    parser.add_argument("--out", default="", help="输出 md 路径（默认 artifacts/evaluation/检索流程日志.md）")
    args = parser.parse_args()

    retriever, cfg = build_retriever()
    rc = cfg.retrieval
    suite = [t for t in HARD_BENCHMARK_SUITE if not args.ids or t["id"] in args.ids]
    if not suite:
        print("❌ 没有匹配的题目")
        sys.exit(1)

    print(f"[3/3] 跑 {len(suite)} 题，收集全链路检索日志 ...\n")

    lines = [
        "# 检索全流程日志",
        "",
        "> 每题展示混合检索的 5 个环节：① 向量检索（dense_search）② 全文检索（bm25_search）",
        "> ③ RRF 倒数排序（rrf_fusion）④ Rerank 精排（KspReranker.predict）⑤ 按秩融合。",
        "",
    ]

    for test in suite:
        print(f"  {test['id']} {test['query'][:30]}...")
        buf = io.StringIO()
        # 把 verbose 日志捕获到内存，不刷屏
        with contextlib.redirect_stdout(buf):
            retriever.hybrid_rerank_search(
                query=test["query"],
                final_top_k=rc.top_k,
                rrf_k=rc.rrf_k,
                rough_top_k=rc.rough_top_k,
                fuse_k=rc.fuse_k,
                rrf_weight=rc.rrf_weight,
                rerank_weight=rc.rerank_weight,
                metadata_filter=test["filter"],
                verbose=True,
            )
        lines.append(f"## [{test['id']}] {test['category']}（{test.get('qtype', 'hard')}）")
        lines.append("")
        lines.append(f"- **查询**：`{test['query']}`")
        if test.get("target_id"):
            lines.append(f"- **目标卡片**：`{test['target_id']}`")
        lines.append("")
        lines.append("```text")
        lines.append(buf.getvalue().strip())
        lines.append("```")
        lines.append("")

    out = Path(args.out) if args.out else EVALUATION_OUTPUT / "检索流程日志.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n🎉 检索流程日志已落盘：{out}")


if __name__ == "__main__":
    main()
