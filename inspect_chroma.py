#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_chroma.py — 查看本地持久化 Chroma 向量库内容的小工具

用法（在 D:\\day12\\demos 目录下）：
  python inspect_chroma.py                          # 查看集合概况 + 抽样 3 条
  python inspect_chroma.py --sample 5               # 抽样 5 条
  python inspect_chroma.py --collection naive_fixed_kb   # 看朴素对照库
  python inspect_chroma.py --query "电脑蓝屏怎么办"      # 直接发起一次向量检索
"""

import sys
import argparse
from pathlib import Path

# Windows 控制台默认 GBK，统一切换 UTF-8 防止 emoji 打印崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import chromadb
from run_day12_pipeline import KspEmbeddingProvider

DEFAULT_DIR = "day12_output/chroma_wiki_structured"
OUTPUT_ROOT = "day12_output"


def discover_collections() -> dict:
    """扫描 OUTPUT_ROOT 下所有 Chroma 持久化目录，返回 {集合名: 目录路径}"""
    found: dict = {}
    root = Path(OUTPUT_ROOT)
    if not root.exists():
        return found
    # 候选：OUTPUT_ROOT 自身 + 其下每个含 chroma.sqlite3 的子目录
    candidates = [root] + [p for p in root.iterdir() if p.is_dir()]
    for d in candidates:
        if not (d / "chroma.sqlite3").exists():
            continue
        try:
            client = chromadb.PersistentClient(path=str(d))
            for c in client.list_collections():
                found[c.name] = str(d)
        except Exception:
            continue
    return found


def main():
    parser = argparse.ArgumentParser(description="查看 Chroma 向量库内容")
    parser.add_argument("--path", default="", help="Chroma 持久化目录(留空则自动发现集合所在目录)")
    parser.add_argument("--collection", default="wiki_structured_kb", help="集合名")
    parser.add_argument("--sample", type=int, default=3, help="抽样展示条数")
    parser.add_argument("--query", default="", help="可选：发起一次相似度检索")
    parser.add_argument("--k", type=int, default=3, help="检索返回条数")
    args = parser.parse_args()

    # 自动发现全部集合及其所在目录
    collection_map = discover_collections()
    print("🗂️  已发现的集合：")
    for name, path in sorted(collection_map.items()):
        print(f"    - {name}  ->  {path}")

    # 解析目标集合所在路径：显式 --path 优先，否则从发现结果里查
    if args.path:
        target_path = args.path
    elif args.collection in collection_map:
        target_path = collection_map[args.collection]
    else:
        print(f"\n❌ 未找到集合 [{args.collection}]。可用集合：{list(collection_map.keys())}")
        print(f"   提示：--collection 指定集合名，或用 --path 指定目录")
        sys.exit(1)

    client = chromadb.PersistentClient(path=target_path)

    # 1. 列出该目录全部集合
    print("=" * 80)
    print(f"📂 Chroma 目录: {Path(target_path).resolve()}")
    cols = client.list_collections()
    print(f"📚 集合列表: {[c.name for c in cols]}")
    col = client.get_collection(args.collection)
    print(f"📦 集合 [{args.collection}] 共 {col.count()} 条记录")
    print("=" * 80)

    # 2. 抽样查看
    res = col.get(limit=args.sample, include=["documents", "metadatas", "embeddings"])
    print(f"\n🔍 抽样 {len(res['ids'])} 条：")
    for i, cid in enumerate(res["ids"]):
        meta = res["metadatas"][i] or {}
        doc = res["documents"][i] or ""
        emb = res["embeddings"][i]
        print("-" * 80)
        print(f"[{i+1}] id={cid}")
        print(f"    向量维度: {len(emb)}  (前5维: {[round(float(x),4) for x in emb[:5]]})")
        print(f"    卡片/分类: {meta.get('wiki_id', '-')} / {meta.get('wiki_category', '-')}")
        print(f"    标题层级: {meta.get('Header_1', '-')} > {meta.get('Header_2', '-')}")
        print(f"    切块长度: {meta.get('chunk_length', '-')}  策略: {meta.get('split_strategy', '-')}")
        print(f"    正文预览: {doc[:150].replace(chr(10), ' ')}...")

    # 3. 可选检索测试
    if args.query:
        print("\n" + "=" * 80)
        print(f"🔎 向量检索测试: 「{args.query}」 (Top-{args.k})")
        provider = KspEmbeddingProvider(cache_dir=str(Path(target_path).parent / ".emb_cache"))
        print(f"    Embedding 引擎: {provider.engine_type}")
        qres = col.query(
            query_embeddings=[provider.embed_query(args.query)],
            n_results=args.k,
            include=["documents", "metadatas", "distances"],
        )
        for i in range(len(qres["ids"][0])):
            meta = qres["metadatas"][0][i] or {}
            doc = qres["documents"][0][i] or ""
            dist = qres["distances"][0][i]
            print(f"  [{i+1}] 距离={dist:.4f} | {meta.get('wiki_id','-')} {meta.get('Header_2','-')}")
            print(f"      {doc[:120].replace(chr(10), ' ')}...")
    print("\n✅ 完成")


if __name__ == "__main__":
    main()
