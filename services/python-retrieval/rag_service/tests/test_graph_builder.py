# -*- coding: utf-8 -*-
"""glossary 与 graph_data 构建器测试(Task 4)。

被测对象 rag_pipeline/ingestion/graph_builder.py(纯函数,无 IO 除显式传 path 的
load_glossary/save_glossary):

- load_glossary: 不存在 → {"entities": {}}(首跑建词表,不抛错);
  存在但结构损坏 → 显式 ValueError(不静默重建);
- save_glossary: 原子写 + 与 load 往返无损;
- merge_new_entities: 幂等合并(词表已含则跳过,重复 merge 计数不变,入参不被改动);
- build_graph_data: 节点 id 稳定可复算(card:/entity:/concept: 编码)、
  边型映射(小写→大写、kind→概念边型)、REPLACES 对方向规约
  (两卡双向产出时只保 target 为 LEG 卡的那条)、fingerprint 透传、
  边幂等去重(完全相同边只留一条)、Task 1 校验器拒收的输入显式抛错。
"""

import copy
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_pipeline.ingestion.graph_builder import (  # noqa: E402
    build_graph_data,
    load_glossary,
    merge_new_entities,
    save_glossary,
)
from rag_pipeline.ingestion.graph_schema import EntityDef  # noqa: E402

FP = "sha1-abc-001"

GLOSSARY = {
    "entities": {
        "AD域": {"type": "系统", "aliases": ["Active Directory"]},
    }
}

# 四张假卡:HB-001/HB-002 两张现行互为 same_root_cause;
# HB-003(现行)+ HB-LEG-003(废止)双向产出 replaces(唯一受方向规约约束的对)。
CARDS = [
    (
        "ITKB-HB-001",
        {
            "title": "域账号锁定排查与解锁处理",
            "category": "账号与权限问题",
            "version": "v1.0",
            "status": "现行",
            "entities": [{"name": "AD域", "type": "系统"}],
            "relations": [
                {
                    "target": "ITKB-HB-002",
                    "type": "same_root_cause",
                    "note": "同一密码策略根因",
                    "evidence": "正文:连续输错密码触发锁定策略",
                },
            ],
            "graph_nodes": [
                {"kind": "symptom", "name": "账号锁定"},
                {"kind": "tool", "name": "事件查看器"},
            ],
        },
    ),
    (
        "ITKB-HB-002",
        {
            "title": "密码重置与过期处理",
            "category": "账号与权限问题",
            "version": "v1.0",
            "status": "现行",
            "entities": [
                {"name": "AD域", "type": "系统"},
                {"name": "密码重置平台", "type": "软件"},
            ],
            "relations": [
                {
                    "target": "ITKB-HB-001",
                    "type": "same_root_cause",
                    "note": "同一密码策略根因",
                    "evidence": "正文:密码过期未改触发锁定",
                },
            ],
            "graph_nodes": [
                {"kind": "root_cause", "name": "密码策略到期"},
            ],
        },
    ),
    (
        "ITKB-HB-003",
        {
            "title": "DNS 解析失败排查与处置",
            "category": "网络连接问题",
            "version": "v1.0",
            "status": "现行",
            "entities": [{"name": "DNS", "type": "协议"}],
            "relations": [
                {
                    "target": "ITKB-HB-LEG-003",
                    "type": "replaces",
                    "note": "frontmatter replaces 规则迁移",
                    "evidence": "frontmatter:replaces",
                },
            ],
            "graph_nodes": [],
        },
    ),
    (
        "ITKB-HB-LEG-003",
        {
            "title": "DNS 解析故障处理(旧版·已废止)",
            "category": "网络连接问题",
            "version": "v0.9",
            "status": "已废止",
            "entities": [{"name": "DNS", "type": "协议"}],
            "relations": [
                {
                    "target": "ITKB-HB-003",
                    "type": "replaces",
                    "note": "旧版叙述:本卡已废止,以现行卡为准",
                    "evidence": "正文:现行标准请以《ITKB-HB-003》为准",
                },
            ],
            "graph_nodes": [],
        },
    ),
]


def _card_ids(data):
    return {
        n["id"] for n in data["nodes"] if n["label"] == "card"
    }


def _edges(data, src=None, dst=None, type_=None):
    return [
        e
        for e in data["edges"]
        if (src is None or e["src"] == src)
        and (dst is None or e["dst"] == dst)
        and (type_ is None or e["type"] == type_)
    ]


# ---------- ① build_graph_data:节点 id 稳定可复算 + 透传 ----------


class TestBuildGraphDataNodes:
    def test_node_ids_stable_encoded(self):
        data = build_graph_data(CARDS, GLOSSARY, FP)
        ids = {n["id"] for n in data["nodes"]}
        assert ids == {
            "card:ITKB-HB-001",
            "card:ITKB-HB-002",
            "card:ITKB-HB-003",
            "card:ITKB-HB-LEG-003",
            "entity:AD域",
            "entity:密码重置平台",
            "entity:DNS",
            "concept:symptom:账号锁定",
            "concept:tool:事件查看器",
            "concept:root_cause:密码策略到期",
        }

    def test_rebuild_reproducible(self):
        d1 = build_graph_data(CARDS, GLOSSARY, FP)
        d2 = build_graph_data(copy.deepcopy(CARDS), copy.deepcopy(GLOSSARY), FP)
        assert d1 == d2

    def test_fingerprint_passed_through(self):
        data = build_graph_data(CARDS, GLOSSARY, FP)
        assert data["wiki_fingerprint"] == FP

    def test_glossary_embedded_verbatim(self):
        data = build_graph_data(CARDS, GLOSSARY, FP)
        assert data["glossary"] == GLOSSARY

    def test_entity_type_from_glossary_preferred(self):
        data = build_graph_data(CARDS, GLOSSARY, FP)
        ents = {n["id"]: n for n in data["nodes"] if n["label"] == "entity"}
        # AD域 在词表中 → 取词表类型;
        # 密码重置平台/DNS 不在词表 → 回退卡上已验类型。
        assert ents["entity:AD域"]["type"] == "系统"
        assert ents["entity:密码重置平台"]["type"] == "软件"
        assert ents["entity:DNS"]["type"] == "协议"


# ---------- ② build_graph_data:边型映射 + REPLACES 方向规约 ----------


class TestBuildGraphDataEdges:
    def test_relation_type_mapped_uppercase(self):
        data = build_graph_data(CARDS, GLOSSARY, FP)
        # 互为 same_root_cause:两个方向都保留(对称关系不属方向规约范围)。
        fwd = _edges(data, "card:ITKB-HB-001", "card:ITKB-HB-002", "SAME_ROOT_CAUSE")
        bwd = _edges(data, "card:ITKB-HB-002", "card:ITKB-HB-001", "SAME_ROOT_CAUSE")
        assert len(fwd) == 1 and len(bwd) == 1
        assert fwd[0]["evidence"].startswith("正文:")

    def test_mentions_edges_from_entities(self):
        data = build_graph_data(CARDS, GLOSSARY, FP)
        m = _edges(data, "card:ITKB-HB-002", "entity:AD域", "MENTIONS")
        assert len(m) == 1
        for e in data["edges"]:
            assert set(e.keys()) == {"src", "dst", "type", "evidence"}
            assert e["evidence"]

    def test_concept_kind_edge_mapping(self):
        data = build_graph_data(CARDS, GLOSSARY, FP)
        assert len(_edges(data, "concept:symptom:账号锁定", "card:ITKB-HB-001", "SYMPTOM_OF")) == 1
        assert len(_edges(data, "concept:tool:事件查看器", "card:ITKB-HB-001", "USED_IN")) == 1
        assert len(_edges(data, "concept:root_cause:密码策略到期", "card:ITKB-HB-002", "ROOT_CAUSE_OF")) == 1

    def test_replaces_pair_keeps_target_leg_only(self):
        # 规约:两卡双向产出 replaces 时,丢弃 target 为现行卡的那条,
        # 只保 target 为 LEG 卡(现行卡 → LEG)的那条。
        data = build_graph_data(CARDS, GLOSSARY, FP)
        replaces = [e for e in data["edges"] if e["type"] == "REPLACES"]
        assert len(replaces) == 1
        assert replaces[0]["src"] == "card:ITKB-HB-003"
        assert replaces[0]["dst"] == "card:ITKB-HB-LEG-003"
        assert replaces[0]["evidence"] == "frontmatter:replaces"

    def test_replaces_single_direction_kept_as_is(self):
        cards = [
            ("ITKB-HB-003", dict(CARDS[2][1])),
            # LEG 卡不产出反向 replaces(仅自述),此时也无对可去。
            ("ITKB-HB-LEG-003", dict(CARDS[3][1], relations=[])),
        ]
        data = build_graph_data(cards, GLOSSARY, FP)
        replaces = [e for e in data["edges"] if e["type"] == "REPLACES"]
        assert len(replaces) == 1
        assert replaces[0]["dst"] == "card:ITKB-HB-LEG-003"

    def test_replaces_no_status_decided_by_evidence_note(self):
        # frontmatter 两卡都无 status:按 relations 条目 evidence/note 判定方向
        # (note/evidence 自述「废止/为准」的那条 = 源为 LEG 卡的那条 → 丢弃)。
        cur = dict(CARDS[2][1]); cur.pop("status")
        leg = dict(CARDS[3][1]); leg.pop("status")
        cards = [("ITKB-HB-003", cur), ("ITKB-HB-LEG-003", leg)]
        data = build_graph_data(cards, GLOSSARY, FP)
        replaces = [e for e in data["edges"] if e["type"] == "REPLACES"]
        assert len(replaces) == 1
        assert replaces[0]["dst"] == "card:ITKB-HB-LEG-003"

    def test_replaces_undecidable_keeps_first_in_input_order(self):
        # 两卡同现行、note/evidence 无差异信号:保持确定性——
        # 保留输入卡序列中先出现者为源的那条,并告警。
        a = dict(CARDS[2][1]); a["relations"] = [
            {"target": "ITKB-HB-004", "type": "replaces", "note": "spec", "evidence": "e1"}
        ]
        b = dict(CARDS[3][1]); b["status"] = "现行"; b["relations"] = [
            {"target": "ITKB-HB-003", "type": "replaces", "note": "spec", "evidence": "e2"}
        ]
        cards = [("ITKB-HB-003", a), ("ITKB-HB-004", b)]
        with caplog_context("rag_pipeline.ingestion.graph_builder") as records:
            data = build_graph_data(cards, GLOSSARY, FP)
        replaces = [e for e in data["edges"] if e["type"] == "REPLACES"]
        assert len(replaces) == 1
        assert replaces[0]["src"] == "card:ITKB-HB-003"
        assert any("replaces" in r.getMessage().lower() for r in records)

    def test_identical_edges_deduplicated(self):
        # 完全相同的边(src/dst/type/evidence 全等)幂等去重,只留一条。
        cur = dict(CARDS[2][1])
        cur["relations"] = [
            {
                "target": "ITKB-HB-LEG-003",
                "type": "replaces",
                "note": "重复条目1",
                "evidence": "frontmatter:replaces",
            },
            {
                "target": "ITKB-HB-LEG-003",
                "type": "replaces",
                "note": "重复条目2",
                "evidence": "frontmatter:replaces",
            },
        ]
        cards = [("ITKB-HB-003", cur), ("ITKB-HB-LEG-003", dict(CARDS[3][1], relations=[]))]
        data = build_graph_data(cards, GLOSSARY, FP)
        assert len(_edges(data, "card:ITKB-HB-003", "card:ITKB-HB-LEG-003", "REPLACES")) == 1

    def test_edges_reference_existing_nodes_only(self):
        data = build_graph_data(CARDS, GLOSSARY, FP)
        ids = {n["id"] for n in data["nodes"]}
        for e in data["edges"]:
            assert e["src"] in ids, e
            assert e["dst"] in ids, e


# ---------- ③ build_graph_data:输入经 Task 1 校验器(先验后写) ----------


class TestBuildGraphDataValidation:
    def test_unknown_relation_target_raises(self):
        bad = ("ITKB-HB-001", dict(CARDS[0][1], relations=[
            {"target": "ITKB-GHOST", "type": "related", "note": "n", "evidence": "e"}
        ]))
        with pytest.raises(ValueError, match="ITKB-GHOST"):
            build_graph_data([bad], GLOSSARY, FP)

    def test_invalid_entity_type_raises(self):
        bad = ("ITKB-HB-001", dict(CARDS[0][1], entities=[
            {"name": "X", "type": "不存在类型"}
        ]))
        with pytest.raises(ValueError, match="不存在类型"):
            build_graph_data([bad], GLOSSARY, FP)

    def test_relation_without_evidence_dropped(self):
        card = dict(CARDS[0][1])
        card["relations"] = [
            {"target": "ITKB-HB-002", "type": "related", "note": "n", "evidence": None},
        ]
        data = build_graph_data([("ITKB-HB-001", card), CARDS[1]], GLOSSARY, FP)
        assert not _edges(data, "card:ITKB-HB-001", "card:ITKB-HB-002", "RELATED")

    def test_duplicated_card_id_raises(self):
        with pytest.raises(ValueError, match="重复"):
            build_graph_data([CARDS[0], CARDS[0]], GLOSSARY, FP)


# ---------- ④ glossary:load/save/merge ----------


class TestGlossary:
    def test_load_missing_returns_empty(self, tmp_path):
        g = load_glossary(tmp_path / "entity_glossary.json")
        assert g == {"entities": {}}

    def test_save_atomic_roundtrip(self, tmp_path):
        path = tmp_path / "entity_glossary.json"
        save_glossary(path, GLOSSARY)
        assert load_glossary(path) == GLOSSARY
        # 父目录被显式传入才建;不存在的目录是调用方错误 → 显式失败。
        deep = tmp_path / "nested"
        with pytest.raises(FileNotFoundError):
            save_glossary(deep / "g.json", GLOSSARY)

    def test_load_corrupt_structure_raises(self, tmp_path):
        path = tmp_path / "g.json"
        path.write_text('{"entities": ["not-a-map"]}', encoding="utf-8")
        with pytest.raises(ValueError, match="entities"):
            load_glossary(path)
        path.write_text('["not-an-object"]', encoding="utf-8")
        with pytest.raises(ValueError, match="顶层"):
            load_glossary(path)

    def test_merge_adds_new_entities(self):
        glo = copy.deepcopy(GLOSSARY)
        out = merge_new_entities(glo, [EntityDef(name="堡垒机", type="软件")])
        assert out["entities"]["堡垒机"] == {"type": "软件", "aliases": []}
        # 入参不被改动。
        assert "堡垒机" not in glo["entities"]
        assert glo == GLOSSARY

    def test_merge_idempotent(self):
        glo = copy.deepcopy(GLOSSARY)
        new = [EntityDef(name="堡垒机", type="软件"), EntityDef(name="AD域", type="系统")]
        once = merge_new_entities(glo, new)
        twice = merge_new_entities(once, new)
        assert once == twice
        assert len(twice["entities"]) == 2
        # 词表已有的 AD域:类型不被新生项覆盖。
        assert twice["entities"]["AD域"] == {"type": "系统", "aliases": ["Active Directory"]}

    def test_merge_dedupes_within_new_list(self):
        out = merge_new_entities({"entities": {}}, [
            EntityDef(name="堡垒机", type="软件"),
            EntityDef(name="堡垒机", type="概念"),
        ])
        assert list(out["entities"].keys()) == ["堡垒机"]
        assert out["entities"]["堡垒机"]["type"] == "软件"


class caplog_context:
    """捕获指定 logger 的记录(纯标准库,不依赖 pytest caplog fixture 包装方式)。"""

    def __init__(self, logger_name):
        self.logger = logging.getLogger(logger_name)
        self.records = []
        self.handler = None

    def __enter__(self):
        self.handler = _ListHandler(self.records)
        self.logger.addHandler(self.handler)
        return self.records

    def __exit__(self, *args):
        self.logger.removeHandler(self.handler)


class _ListHandler(logging.Handler):
    def __init__(self, records):
        super().__init__()
        self.records = records

    def emit(self, record):
        self.records.append(record)


if __name__ == "__main__":
    import pytest as _pytest

    _pytest.main([__file__, "-q"])
