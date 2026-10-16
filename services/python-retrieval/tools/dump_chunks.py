#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出父子切片结果全量预览到 artifacts/indexing/chunk_preview.md，便于人工审阅切块质量。"""
import sys
from pathlib import Path

# 脚本位于 tools/，向上定位仓库根并加入 sys.path，便于 import rag_pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rag_pipeline.config import WIKI_DIR, INDEXING_OUTPUT
from rag_pipeline.chunking.parent_child import ParentChildChunker

FENCE = chr(96) * 3

pc = ParentChildChunker(child_size=512)
out = [
    "# 父子切片结果全量预览",
    "",
    "> 每张卡 = 1 个父块（整卡全文，不入库，供回溯）+ N 个子块（入库做匹配）",
    "> 子块首两行是注入的上下文头，第三行起是卡片正文切片。",
]
files = sorted(WIKI_DIR.glob("*.md"))
files = [f for f in files if f.name != "_index.md"]
total = 0
for f in files:
    p, cs = pc.split_wiki_document(str(f))
    total += len(cs)
    out.append(f"## {f.stem}（父块 {len(p.page_content)} 字符 → {len(cs)} 个子块）")
    out.append("")
    for c in cs:
        out.append(f"### {c.metadata['child_id']}（{len(c.page_content)} 字符）")
        out.append(FENCE)
        out.append(c.page_content.rstrip())
        out.append(FENCE)
        out.append("")
out.insert(4, f"共 {len(files)} 张卡 → {total} 个子块")
(INDEXING_OUTPUT / "chunk_preview.md").write_text("\n".join(out), encoding="utf-8")
print(f"OK -> {INDEXING_OUTPUT / 'chunk_preview.md'}  共 {total} 个子块, {len(files)} 张卡")
