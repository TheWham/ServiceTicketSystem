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
from rag_pipeline.ingestion.clean_pipeline import Entry
from rag_pipeline.ingestion.wiki_generator import make_wiki_id, render_card


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


def test_typed_entities_fixture_corpus_loads(tmp_path):
    """typed entities 夹具卡的确定性装载（AGENTS：构造夹具的用例随迁移改 typed）。

    迁移后 parent_child 消费方只认单一形态 entities=[{name, type}]；
    typed 卡经切片装载，chunk_id/child_id 对齐、实体段及 wiki_entities
    元数据均以 typed 形态进入块元数据。真实语料仍是旧扁平形态（Task 7
    增补），读真实 artifacts 的用例保留原样——其红由 Task 7 Step 5 恢复。
    """
    import json

    meta = {
        "title": "typed 实体夹具卡", "version": "v1.0", "status": "现行",
        "replaces": [],
        "entities": [{"name": "堡垒机", "type": "设备"}, {"name": "AD域", "type": "系统"}],
        "summary": "覆盖实体对象形态消费。", "meta_source": "rule",
    }
    entry = Entry(code="TZ-001", title="typed 实体夹具卡", category="账号权限",
                  keywords=["堡垒机", "AD域"],
                  fields={"现象描述": "堡垒机登录后无法访问 AD域 资源。"})
    wiki_id = make_wiki_id(entry, "ITKB")
    (tmp_path / f"{wiki_id}.md").write_text(render_card(entry, meta), encoding="utf-8")

    cfg = load_config()
    chunks = load_corpus_with_deterministic_ids(tmp_path, cfg)
    assert chunks, "夹具卡应产出切片"
    assert all(c.metadata["chunk_id"] == c.metadata["child_id"] for c in chunks)
    assert all(c.metadata["wiki_id"] == f"ITKB-TZ-001" for c in chunks)
    # typed 实体以对象形态进入块元数据（wiki_entities 为 json 串）
    first = json.loads(chunks[0].metadata["wiki_entities"])
    assert first == [{"name": "堡垒机", "type": "设备"}, {"name": "AD域", "type": "系统"}]
    # 检索增强行实体段取 name（单一形态迁移，无 isinstance 分支）
    assert "实体 堡垒机、AD域】" in chunks[0].page_content


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))

