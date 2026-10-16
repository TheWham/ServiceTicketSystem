# -*- coding: utf-8 -*-
"""确定性语料装载：Wiki 卡片 -> 切片（绑定可溯源的确定性 chunk_id）。

与索引构建共用 build_chunker 工厂：父子切片下 chunk_id 即 metadata 的
child_id（ITKB-XXX-NNN#cN），黄金集 reference_chunk_ids 与 rag_service 装配
均按此体系对齐（黄金集评测入口见 rag_pipeline.pipelines.golden_evaluation）。
"""

from pathlib import Path
from typing import List

from ..chunking.structure_aware import Document
from ..config import build_chunker


def load_corpus_with_deterministic_ids(wiki_dir: Path, cfg) -> List[Document]:
    """提取 Wiki 切片并绑定确定性可溯源 chunk_id，供黄金问题集精准归因。

    与索引构建共用 build_chunker 工厂：父子切片下 chunk_id 即 metadata 的
    child_id（ITKB-XXX-NNN#cN），黄金集的 reference_chunk_ids 按此体系书写。
    """
    chunker, use_parent_child = build_chunker(cfg)
    wiki_files = sorted(p for p in wiki_dir.glob("*.md") if p.name != "_index.md")
    if not wiki_files:
        raise FileNotFoundError(f"❌ 未在 {wiki_dir} 找到 Wiki 卡片，请先运行 Wiki 清洗流水线！")

    all_chunks: List[Document] = []
    for wf in wiki_files:
        if use_parent_child:
            _parent, children = chunker.split_wiki_document(str(wf))
        else:
            children = chunker.split_wiki_document(str(wf))
        for chunk in children:
            # 确定性溯源 id：父子切片用 child_id；结构感知切片回退为 文件名#序号
            if "child_id" not in chunk.metadata:
                chunk.metadata["child_id"] = f"{wf.stem}#c{chunk.metadata.get('sub_idx', 0)}"
            chunk.metadata["chunk_id"] = chunk.metadata["child_id"]
            all_chunks.append(chunk)
    return all_chunks
