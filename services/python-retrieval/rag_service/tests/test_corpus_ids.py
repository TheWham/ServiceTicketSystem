# -*- coding: utf-8 -*-
"""确定性语料装载的守护测试：chunk_id 必须与父子切片的 child_id 对齐。

rag_service 装配与黄金集评测共用同一份语料装载（rag_pipeline.chunking.corpus），
两侧口径必须逐字一致，否则黄金集归因失效。
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from rag_pipeline.chunking.corpus import load_corpus_with_deterministic_ids  # noqa: E402
from rag_pipeline.config import load_config  # noqa: E402


def test_chunk_ids_align_with_children():
    cfg = load_config()
    wiki = REPO_ROOT / "artifacts/output/wiki"
    chunks = load_corpus_with_deterministic_ids(wiki, cfg)
    assert chunks, "语料不应为空"
    assert all(c.metadata.get("chunk_id") for c in chunks)
    # 父子切片下 chunk_id 即 child_id（确定性溯源体系 ITKB-XXX-NNN#cN）
    assert all(c.metadata["chunk_id"] == c.metadata.get("child_id") for c in chunks)
    assert any(c.metadata["chunk_id"].startswith("ITKB-ACC-002#c") for c in chunks)
    # 废止卡留在语料内（由检索侧 default_exclude 物理屏蔽，而非装载期丢弃）
    assert any(c.metadata.get("wiki_status") == "已废止" for c in chunks)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))

