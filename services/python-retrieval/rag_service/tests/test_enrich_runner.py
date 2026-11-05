# -*- coding: utf-8 -*-
"""阶段一 runner 测试(Wiki 图知识库 Task 6)。

测试不打真 LLM:_StubGraphExtractor 继承 GraphExtractor 并覆写两步萃取方法
(模式照 test_degraded_rejection.py 的类内注入法——替身不触网,返回定值),
经 monkeypatch 换入 runner 的 `_build_extractor` 依赖缝(rag_pipeline.ingestion.
graph_extractor 不被触碰)。

覆盖(controller 裁决逐字):
- 四键增补(只动 entities/relations/graph_nodes/graph_meta_source),正文逐字节不变,
  未知键(effective_date_source)原样保留;
- replaces 迁移条目落进 relations(evidence="frontmatter:replaces");
- graph_data.json 与盘上(写卡后)卡片一致:边/节点/指纹(fingerprint 写卡后才算);
- --dry-run 严格零写入(卡片逐字节不变,glossary/graph_data 不落盘);
- glossary 正式跑落盘,二次跑输出相同(F3 幂等:同卡跑两遍 relations 条目不变);
- 裁决 11:normalize_entities 显式传 glossary、extract_relations_and_nodes 显式传
  corpus_digests=全部卡 CardDigest 列表(漏传 corpus=卡间关系静默全灭);
- 裁决 10:last_used_llm 每步读,两步任一 False 记 rule,均 True 记 llm;
- 任何卡萃取异常 = 非零退出整体中止,不做回滚(不跳过不降级);
- 幻觉防护:frontmatter replaces 指向不存在的卡编码 → 非零退出,零写入;
- --limit 只增补前 N 张,语料摘要清单仍传全部卡,图产物卡节点覆盖全部卡。
"""

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import tools.enrich_wiki_metadata as enrich_mod  # noqa: E402
from rag_pipeline.chunking.fingerprint import compute_wiki_fingerprint  # noqa: E402
from rag_pipeline.ingestion.frontmatter_editor import (  # noqa: E402
    MIGRATION_EVIDENCE,
    load_card,
)
from rag_pipeline.ingestion.graph_builder import load_glossary  # noqa: E402
from rag_pipeline.ingestion.graph_extractor import (  # noqa: E402
    CardDigest,
    GraphExtractor,
)
from rag_pipeline.ingestion.graph_schema import (  # noqa: E402
    EntityDef,
    GraphNodeDef,
    RelationDef,
)

# ---- 测试语料(3 张假卡) ----

IDS = ("ITKB-HW-001", "ITKB-HW-002", "ITKB-HW-LEG-001")


def _write_card(path: Path, wiki_id: str, **extra) -> bytes:
    meta = {
        "id": wiki_id,
        "title": f"{wiki_id} 标题",
        "category": "硬件与外设故障",
        "department": "IT 部",
        "effective_date": "2024-03-01",
        "effective_date_source": "demo-constructed",
        "version": "v1.0",
        "status": "现行",
        "replaces": [],
        "entities": ["无线局域网(WiFi)", "ipconfig"],
        "keywords": ["关键词A", "关键词B"],
        "summary": "示范摘要。",
        "meta_source": "llm",
    }
    meta.update(extra)
    body = (
        f"\n# 【{wiki_id}】演示正文\n\n"
        "> ⚠️ 演示正文逐字节不变性检查段。\n\n"
        "- WiFi 反复掉线, 请用 ipconfig 排查。\n"
    )
    text = "---\n" + "\n".join(
        f"{k}: " + (
            "[" + ", ".join(f'"{v2}"' for v2 in v) + "]"
            if isinstance(v, list) and all(isinstance(i, str) for i in v)
            and not isinstance(v, str)
            else f'"{v}"'
        )
        for k, v in meta.items()
    ) + "\n---" + body
    path.write_bytes(text.encode("utf-8"))
    return path.read_bytes()


def _make_corpus(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    _write_card(wiki / "ITKB-HW-001.md", "ITKB-HW-001",
                replaces=["ITKB-HW-LEG-001"])
    _write_card(wiki / "ITKB-HW-002.md", "ITKB-HW-002")
    _write_card(wiki / "ITKB-HW-LEG-001.md", "ITKB-HW-LEG-001", status="已废止")
    return wiki


class _StubGraphExtractor(GraphExtractor):
    """GraphExtractor 两步方法替身:不触网、返回定值、记录入参。

    覆写 __init__ 绕开 OpenAI client 构造;覆写 normalize_entities /
    extract_relations_and_nodes 返回定值并按 id 微调(不自指),每步调用后
    按注入值改写 self.last_used_llm(runner 按「立即读」语义消费)。
    """

    ENTITIES = ([EntityDef(name="无线局域网", type="配置项"),
                 EntityDef(name="打印机", type="设备")],
                [EntityDef(name="新式打印机", type="设备")])
    NODES = [GraphNodeDef(kind="symptom", name="WiFi反复掉线")]

    def __init__(self, ent_used=True, rel_used=True, raise_on=None):
        self.ent_used = ent_used
        self.rel_used = rel_used
        self.raise_on = raise_on
        self.ent_calls = []
        self.rel_calls = []
        self.last_used_llm = False

    def normalize_entities(self, wiki_id, entities, body, glossary=None):
        if self.raise_on and wiki_id == self.raise_on:
            raise RuntimeError(f"graph_ent: 卡 {wiki_id} 萃取异常(测试注入)")
        self.ent_calls.append({"wiki_id": wiki_id, "entities": list(entities or []),
                               "glossary": glossary})
        self.last_used_llm = self.ent_used
        return (
            list(type(self).ENTITIES[0]),
            list(type(self).ENTITIES[1]),
        )

    def extract_relations_and_nodes(self, digest, corpus_digests=None):
        if self.raise_on and digest.wiki_id == self.raise_on:
            raise RuntimeError(f"graph_rel: 卡 {digest.wiki_id} 萃取异常(测试注入)")
        target = "ITKB-HW-002" if digest.wiki_id != "ITKB-HW-002" else "ITKB-HW-001"
        self.rel_calls.append({"digest": digest,
                                "corpus_digests": list(corpus_digests or [])})
        self.last_used_llm = self.rel_used
        return (
            [RelationDef(target=target, type="related",
                         note="同为硬件排查", evidence="WiFi 反复掉线")],
            [_StubGraphExtractor.NODES[0]],
        )


def _run(tmp_path, monkeypatch, *, dry_run=False, limit=None, stub=None,
         wiki_dir=None):
    wiki = wiki_dir or _make_corpus(tmp_path)
    graph_out = tmp_path / "graph" / "graph_data.json"
    glossary = tmp_path / "graph" / "entity_glossary.json"
    stub = stub if stub is not None else _StubGraphExtractor()
    monkeypatch.setattr(enrich_mod, "GraphExtractor", lambda cfg, cache_dir=None: stub)
    monkeypatch.setattr(enrich_mod, "load_api_config",
                        lambda: {"base_url": "stub", "api_key": "k", "chat_model": "m"})
    rc = enrich_mod.run_enrichment(wiki, graph_out, glossary,
                                   cache_dir=str(tmp_path / "cache"),
                                   dry_run=dry_run, limit=limit)
    return rc, stub, wiki, graph_out, glossary


def _read_meta(wiki_dir: Path, wiki_id: str):
    meta, body = load_card(wiki_dir / f"{wiki_id}.md")
    return meta, body


def _relations_of(meta):
    return [(r["target"], r["type"], r["evidence"]) for r in (meta.get("relations") or [])]


# ---- 四键增补 + 正文不变 + 迁移条目 ----


def test_run_enriches_four_keys_and_keeps_body(tmp_path, monkeypatch):
    """正式跑：四键更新、正文逐字节不变、未知键保留、replaces 迁移条目进 relations。"""
    wiki = _make_corpus(tmp_path)
    before = {p.name: p.read_bytes() for p in sorted(wiki.glob("*.md"))}
    rc, stub, wiki, graph_out, glossary = _run(tmp_path, monkeypatch, wiki_dir=wiki)
    assert rc == 0

    for wid in IDS:
        meta, body = _read_meta(wiki, wid)
        assert [(e["name"], e["type"]) for e in meta["entities"]] == \
            [(e.name, e.type) for e in _StubGraphExtractor.ENTITIES[0]]
        assert meta["graph_nodes"] == [{"kind": "symptom", "name": "WiFi反复掉线"}]
        assert meta["graph_meta_source"] == "llm"
        # 正文逐字节不变 + 无关键原样保留(Review Focus 2)
        assert body.encode("utf-8") == before[f"{wid}.md"].split(b"---\n", 2)[2]
        assert meta["effective_date_source"] == "demo-constructed"
        # 两步均 True → llm(裁决 10)
        assert meta["graph_meta_source"] == "llm"

    # 迁移条目:卡 ITKB-HW-001 的 frontmatter replaces → relations
    meta1, _ = _read_meta(wiki, "ITKB-HW-001")
    assert ("ITKB-HW-LEG-001", "replaces", MIGRATION_EVIDENCE) in _relations_of(meta1)
    # 萃取关系也在
    assert ("ITKB-HW-002", "related", "WiFi 反复掉线") in _relations_of(meta1)
    # glossary 正式跑落盘,且新增实体被合并
    assert glossary.exists()
    saved = load_glossary(glossary)
    assert "新式打印机" in saved["entities"]
    assert saved["entities"]["新式打印机"]["type"] == "设备"


def test_dry_run_strictly_zero_writes(tmp_path, monkeypatch):
    """--dry-run 严格零写入：卡片逐字节不动，词表/图产物不落盘。"""
    wiki = _make_corpus(tmp_path)
    before = {p.name: p.read_bytes() for p in sorted(wiki.glob("*.md"))}
    rc, stub, wiki, graph_out, glossary = _run(tmp_path, monkeypatch, dry_run=True, wiki_dir=wiki)
    assert rc == 0
    for p in (tmp_path / "wiki").glob("*.md"):
        assert p.read_bytes() == before[p.name]
    assert not glossary.exists(), "dry-run 连 glossary 都不落盘(裁决)"
    assert not graph_out.exists()
    assert not (tmp_path / "cache").exists(), "dry-run 不建 LLM 磁盘缓存(严格零写入)"


def test_second_run_output_identical(tmp_path, monkeypatch):
    """F3 幂等:同卡跑两遍,relations 条目不变,卡片与图产物字节相同(缓存命中语义)。"""
    rc, _, wiki, graph_out, glossary = _run(tmp_path, monkeypatch)
    assert rc == 0
    rel_first = {wid: _relations_of(_read_meta(wiki, wid)[0]) for wid in IDS}
    files_first = {p.name: p.read_bytes() for p in sorted(tmp_path.rglob("*")) if p.is_file()}
    g_first = graph_out.read_bytes()

    rc2, _, _, _, _ = _run(tmp_path, monkeypatch, wiki_dir=wiki)
    assert rc2 == 0
    for wid in IDS:
        assert _relations_of(_read_meta(wiki, wid)[0]) == rel_first[wid], \
            f"同卡跑两遍 {wid} relations 条目不变(F3)"
    for p in sorted(tmp_path.rglob("*")):
        if p.is_file():
            assert p.read_bytes() == files_first[p.name], f"二次跑输出漂移: {p}"
    assert graph_out.read_bytes() == g_first


# ---- 裁决 11:两参显式传递 ----


def test_glossary_and_corpus_digests_explicitly_passed(tmp_path, monkeypatch):
    """裁决 11:normalize_entities 必须显式传 glossary,rel 步必须传全部卡 CardDigest 列表。"""
    rc, stub, wiki, graph_out, glossary = _run(tmp_path, monkeypatch)
    assert rc == 0
    assert len(stub.ent_calls) == 3
    for call in stub.ent_calls:
        assert call["glossary"] is not None and "entities" in call["glossary"], \
            "normalize_entities 未显式传 glossary(漏传=归一失去全局基线)"
    assert len(stub.rel_calls) == 3
    seen_ids = set()
    for call in stub.rel_calls:
        assert isinstance(call["digest"], CardDigest)
        corpus = call["corpus_digests"]
        assert len(corpus) == 3, f"corpus_digests 必须是全部卡(漏传=卡间关系静默全灭), 实得 {len(corpus)}"
        assert all(isinstance(d, CardDigest) for d in corpus)
        seen_ids |= {d.wiki_id for d in corpus}
    assert seen_ids == set(IDS)


def test_limit_passes_full_corpus_digests(tmp_path, monkeypatch):
    """--limit=2 只增补前 2 张,corpus_digests 仍是全部 3 卡,图产物卡节点覆盖 3 张。"""
    rc, stub, wiki, graph_out, glossary = _run(tmp_path, monkeypatch, limit=2, wiki_dir=_make_corpus(tmp_path))
    assert rc == 0
    for call in stub.rel_calls:
        assert len(call["corpus_digests"]) == 3
    processed, untouched = _read_meta(wiki, "ITKB-HW-001")[0], _read_meta(wiki, "ITKB-HW-LEG-001")[0]
    assert "graph_meta_source" in processed
    assert "relations" in processed
    assert "graph_meta_source" not in untouched, "limit 外的卡不得被改写"
    meta3 = _read_meta(wiki, "ITKB-HW-LEG-001")[0]
    assert set(meta3.keys()) >= {"entities"} and not meta3.get("relations")
    import json
    graph = json.loads(graph_out.read_text(encoding="utf-8"))
    card_nodes = {n["id"] for n in graph["nodes"] if n["label"] == "card"}
    assert card_nodes == {f"card:{w}" for w in IDS}


# ---- 裁决 10:provenance 聚合 ----


def test_meta_source_rule_when_rel_degraded(tmp_path, monkeypatch):
    """两步任一 False 记 rule:rel 步走规则兜底时 graph_meta_source=rule。"""
    stub = _StubGraphExtractor(rel_used=False)
    rc, _, wiki, _, _ = _run(tmp_path, monkeypatch, stub=stub)
    assert rc == 0
    for wid in IDS:
        assert _read_meta(wiki, wid)[0]["graph_meta_source"] == "rule"


def test_meta_source_rule_when_ent_degraded(tmp_path, monkeypatch):
    """ent 步兜底时同样记 rule。"""
    stub = _StubGraphExtractor(ent_used=False)
    rc, _, wiki, _, _ = _run(tmp_path, monkeypatch, stub=stub)
    assert rc == 0
    for wid in IDS:
        assert _read_meta(wiki, wid)[0]["graph_meta_source"] == "rule"


# ---- graph_data 与盘上卡片一致 ----


def test_graph_data_consistent_with_cards_and_fingerprint(tmp_path, monkeypatch):
    """graph_data 的边/节点镜像写卡后盘上内容;指纹=写卡后重算(裁决 2)。"""
    rc, _, wiki, graph_out, _ = _run(tmp_path, monkeypatch)
    assert rc == 0
    import json
    graph = json.loads(graph_out.read_text(encoding="utf-8"))
    wiki_files = sorted(p for p in wiki.glob("*.md") if p.name != "_index.md")
    assert graph["wiki_fingerprint"] == compute_wiki_fingerprint(wiki_files)
    edges = {(e["src"], e["dst"], e["type"], e["evidence"]) for e in graph["edges"]}
    assert ("card:ITKB-HW-001", "card:ITKB-HW-LEG-001", "REPLACES", MIGRATION_EVIDENCE) in edges
    assert ("card:ITKB-HW-001", "card:ITKB-HW-002", "RELATED", "WiFi 反复掉线") in edges
    assert ("card:ITKB-HW-001", "entity:无线局域网", "MENTIONS", "frontmatter:entities") in edges
    assert ("concept:symptom:WiFi反复掉线", "card:ITKB-HW-001", "SYMPTOM_OF",
            "frontmatter:graph_nodes") in edges
    node_ids = {n["id"] for n in graph["nodes"]}
    assert {"card:ITKB-HW-001", "card:ITKB-HW-002", "card:ITKB-HW-LEG-001",
            "entity:无线局域网", "concept:symptom:WiFi反复掉线"} <= node_ids
    # glossary 已合并进产物
    assert graph["glossary"]["entities"]["新式打印机"]["type"] == "设备"


# ---- 异常 = 非零退出整体中止,不回滚 ----


def test_extraction_failure_aborts_with_nonzero_exit(tmp_path, monkeypatch):  # noqa: D401
    """裁决：任何卡萃取异常 = 非零退出整体中止，不做回滚(失败靠 git 恢复)。"""
    wiki = _make_corpus(tmp_path)
    before = {p.name: p.read_bytes() for p in sorted(wiki.glob("*.md"))}
    stub = _StubGraphExtractor(raise_on="ITKB-HW-002")
    rc, _, wiki, graph_out, glossary = _run(tmp_path, monkeypatch, stub=stub, wiki_dir=wiki)
    assert rc == 1, "萃取异常必须非零退出"
    for p in wiki.glob("*.md"):
        assert p.read_bytes() == before[p.name], "中止不留半写状态(写卡在萃取全胜之后)"
    assert not graph_out.exists()
    assert not glossary.exists()


def test_unknown_replaces_target_aborts(tmp_path, monkeypatch):
    """幻觉防护:frontmatter replaces 指向不存在的卡编码 → 非零退出,零写入。"""
    wiki = _make_corpus(tmp_path)
    meta, body = load_card(wiki / "ITKB-HW-002.md")
    meta["replaces"] = ["ITKB-NOPE-999"]
    from rag_pipeline.ingestion.frontmatter_editor import write_card
    write_card(wiki / "ITKB-HW-002.md", meta, body)
    rc, _, wiki, graph_out, glossary = _run(tmp_path, monkeypatch, wiki_dir=wiki)
    assert rc == 1
    assert not graph_out.exists(), "未知 target 拒绝兜底,零产物写入"
    meta2, _ = load_card(wiki / "ITKB-HW-002.md")
    assert "graph_meta_source" not in meta2


# ---- 手册契约:方向判定说明 ----


def test_manual_documents_replaces_direction_note():
    """Task 4 遗留注记:runner 手册须写明 b 类(REPLACES 方向)判定只看 note,evidence 措辞不参与。"""
    doc = enrich_mod.__doc__
    assert "以本卡为准" in doc and "evidence 措辞不参与" in doc


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
