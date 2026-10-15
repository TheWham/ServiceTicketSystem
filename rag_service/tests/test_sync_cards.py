# -*- coding: utf-8 -*-
"""wiki→Java 灌库脚本的纯逻辑单测（不触网）。

覆盖三件容易错的事：
1. 卡片筛选：必须排除 `_index.md` 与 status ∈ {已废止, 已下线} 的 LEG 卡；
2. 中文类目 → Java 类目编码 的映射必须覆盖全部现行卡（否则灌库后 categoryId 缺省）；
3. 幂等与原子落盘的映射表读写。
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import sync_wiki_to_rag_service as sync  # noqa: E402

WIKI_DIR = REPO_ROOT / "artifacts/output/wiki"


def test_collect_cards_excludes_index_and_deprecated():
    cards = sync.collect_cards(WIKI_DIR)
    ids = [c["wiki_id"] for c in cards]
    assert len(cards) == 35, f"现行卡应为 35 张，实际 {len(cards)}"
    assert "_index" not in ids
    assert not any(wid.startswith("ITKB-LEG-") for wid in ids), "废止 LEG 卡不得入库"
    for c in cards:
        assert c["status"] not in ("已废止", "已下线")
        assert c["version"], f"{c['wiki_id']} 缺 version"
        assert c["path"].exists()


def test_all_current_categories_map_to_java_code():
    cards = sync.collect_cards(WIKI_DIR)
    unmapped = sorted({c["category"] for c in cards if c["category"] not in sync.JAVA_CATEGORY_BY_WIKI_CATEGORY})
    assert unmapped == [], f"以下中文类目缺 Java 编码映射：{unmapped}"
    for c in cards:
        assert sync.java_category_of(c["category"]).startswith("C_")


def test_needs_sync_decisions():
    mapping = {"ITKB-ACC-002": {"wiki_version": "v1.0", "articleId": "a", "versionId": "v"}}
    card_same = {"wiki_id": "ITKB-ACC-002", "version": "v1.0"}
    card_bumped = {"wiki_id": "ITKB-ACC-002", "version": "v1.1"}
    card_new = {"wiki_id": "ITKB-XXX-001", "version": "v1.0"}
    assert sync.needs_sync(card_same, mapping, force=False) is False   # 版本未变 → 跳过
    assert sync.needs_sync(card_same, mapping, force=True) is True     # --force 重灌
    assert sync.needs_sync(card_bumped, mapping, force=False) is True  # 版本变更 → 重灌
    assert sync.needs_sync(card_new, mapping, force=False) is True     # 新卡


def test_mapping_roundtrip_atomic(tmp_path=None):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "wiki_article_mapping.json"
        data = {"ITKB-ACC-002": {"articleId": "art-1", "versionId": "ver-1",
                                 "categoryId": "C_ACC", "wiki_version": "v1.0",
                                 "title": "密码重置与过期处理", "synced_at": "2026-10-15T00:00:00"}}
        sync.save_mapping_atomic(path, data)
        assert sync.load_mapping(path) == data
        assert not list(Path(d).glob("*.tmp")), "原子写不应残留临时文件"
    # 缺失文件 → 空映射（不抛异常）
    assert sync.load_mapping(Path("not/exists.json")) == {}


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
