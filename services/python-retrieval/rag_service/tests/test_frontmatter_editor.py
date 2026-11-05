# -*- coding: utf-8 -*-
"""frontmatter 就地增补器测试(Task 2)。

被测对象 rag_pipeline/ingestion/frontmatter_editor.py:
- load_card: yaml.safe_load frontmatter + 返回正文(正文原样,write_card 后回读逐字节相等);
- write_card: 原子写(临时文件 + os.replace),统一 `---\n{fm}\n---\n{body}`;
- render_frontmatter_block: 确定性 YAML——保留原键插入顺序,新键追加在尾;
- render_obj_list: 对象列表块式序列化(Ruling 6 公开导出,Task 5 复用);
- migrate_replaces: 纯函数,把 replaces 扁平字段迁移为 relations 条目,replaces 本身保留。
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_pipeline.ingestion.frontmatter_editor import (  # noqa: E402
    load_card,
    migrate_replaces,
    render_frontmatter_block,
    render_obj_list,
    write_card,
)

# 手工制作的假卡:含清洗流水线 REQUIRED_FIELDS 之外的自定义键
# effective_date_source(未知键必须全部存活且值不变)。
CARD_BODY = """# 【0301】VPN 连接后无法访问内网系统

## 现象

用户已连接 VPN,但内网系统页面持续转圈。

## 排查命令

```
ipconfig /all
route print
```

| 步骤 | 命令 | 预期 |
| --- | --- | --- |
| 1 | ping 10.0.0.1 | 通 |
| 2 | tracert intra.corp | 3 跳内 |

## 备注

正文与 frontmatter 变更完全无关,必须保持原样。
"""

CARD_TEXT = (
    "---\n"
    'id: "ITKB-0301"\n'
    'title: "VPN 连接后无法访问内网系统"\n'
    'category: "网络连接问题"\n'
    'department: "IT 部"\n'
    'version: "v1.0"\n'
    'status: "已废止"\n'
    'replaces: ["ITKB-0300"]\n'
    'effective_date_source: "demo-constructed"\n'
    "---\n"
    + CARD_BODY
)


def _write_fixture(path: Path) -> None:
    path.write_text(CARD_TEXT, encoding="utf-8", newline="\n")


ORIGINAL_KEYS = [
    "id", "title", "category", "department",
    "version", "status", "replaces", "effective_date_source",
]


class TestRoundTrip:
    """write_card → load_card 往返:正文零变更 + 未触碰键存活 + 键顺序。"""

    def test_body_byte_equal_after_write(self, tmp_path):
        path = tmp_path / "card.md"
        _write_fixture(path)
        meta, body = load_card(path)
        assert body == CARD_BODY

        migrated = migrate_replaces(meta)
        write_card(path, migrated, body)

        meta2, body2 = load_card(path)
        # Review Focus 2:正文逐字节相等
        assert body2 == CARD_BODY
        assert meta2 == migrated

        # 再写一轮仍然幂等(正文不会因 frontmatter 编辑被增删空白)
        write_card(path, meta2, body2)
        _, body3 = load_card(path)
        assert body3 == CARD_BODY

    def test_unknown_keys_and_values_survive(self, tmp_path):
        path = tmp_path / "card.md"
        _write_fixture(path)
        meta, body = load_card(path)
        assert meta["effective_date_source"] == "demo-constructed"
        assert meta["status"] == "已废止"
        assert meta["replaces"] == ["ITKB-0300"]

        migrated = migrate_replaces(meta)
        write_card(path, migrated, body)
        meta2, _ = load_card(path)
        assert meta2["effective_date_source"] == "demo-constructed"
        assert meta2["status"] == "已废止"
        assert meta2["replaces"] == ["ITKB-0300"]

    def test_key_order_original_then_appended(self, tmp_path):
        path = tmp_path / "card.md"
        _write_fixture(path)
        meta, _ = load_card(path)
        assert list(meta.keys()) == ORIGINAL_KEYS

        migrated = migrate_replaces(meta)
        assert list(migrated.keys()) == ORIGINAL_KEYS + ["relations"]
        assert list(meta.keys()) == ORIGINAL_KEYS  # 纯函数不改动入参

        write_card(path, migrated, CARD_BODY)
        meta2, _ = load_card(path)
        assert list(meta2.keys()) == ORIGINAL_KEYS + ["relations"]


class TestMigrateReplaces:
    """replaces 迁移:产出 relations 条目且 replaces 原值不动。"""
    def test_migrates_non_empty_replaces(self):
        meta = {
            "id": "ITKB-0301",
            "status": "已废止",
            "replaces": ["ITKB-0300", "ITKB-0299"],
        }
        migrated = migrate_replaces(meta)
        assert migrated["relations"] == [
            {
                "target": "ITKB-0300",
                "type": "replaces",
                "note": "frontmatter replaces 规则迁移",
                "evidence": "frontmatter:replaces",
            },
            {
                "target": "ITKB-0299",
                "type": "replaces",
                "note": "frontmatter replaces 规则迁移",
                "evidence": "frontmatter:replaces",
            },
        ]
        assert migrated["replaces"] == ["ITKB-0300", "ITKB-0299"]
        assert "relations" not in meta  # 入参不被改动

    def test_no_relations_key_added_when_replaces_empty(self):
        meta = {"id": "ITKB-0001", "replaces": []}
        assert migrate_replaces(meta) == {"id": "ITKB-0001", "replaces": []}
        assert migrate_replaces({"id": "ITKB-0001"}) == {"id": "ITKB-0001"}

    def test_appends_to_existing_relations(self):
        meta = {
            "replaces": ["ITKB-0300"],
            "relations": [
                {
                    "target": "ITKB-0200",
                    "type": "related",
                    "note": "存量",
                    "evidence": "wiki:ITKB-0200",
                }
            ],
        }
        migrated = migrate_replaces(meta)
        assert [r["target"] for r in migrated["relations"]] == ["ITKB-0200", "ITKB-0300"]

    def test_replaces_plain_string_rejected(self):
        # 不做静默单元素列表容错:非列表显式拒绝(AGENTS:明确失败不做静默回退)
        with pytest.raises(ValueError, match="replaces 必须是列表: str"):
            migrate_replaces({"id": "ITKB-0301", "replaces": "ITKB-A-001"})


class TestRender:
    """render_frontmatter_block / render_obj_list:确定性 + yaml 往返。"""

    def test_render_frontmatter_block_roundtrip(self):
        meta = {
            "id": "ITKB-0301",
            "status": "已废止",
            "replaces": ["ITKB-0300"],
            "keywords": ["vpn", "内网"],
            "effective_date_source": "demo-constructed",
            "relations": [
                {
                    "target": "ITKB-0300",
                    "type": "replaces",
                    "note": "frontmatter replaces 规则迁移",
                    "evidence": "frontmatter:replaces",
                }
            ],
        }
        fm = render_frontmatter_block(meta)
        assert yaml.safe_load(fm) == meta
        # 渲染顺序即键插入顺序
        lines = [ln for ln in fm.splitlines() if not ln.startswith((" ", "-"))]
        assert [ln.split(":")[0] for ln in lines] == list(meta.keys())

    def test_render_frontmatter_block_escapes_and_empty_values(self):
        meta = {"note": '含"引号"的值', "conflict_note": None, "keywords": []}
        fm = render_frontmatter_block(meta)
        assert yaml.safe_load(fm) == {"note": '含"引号"的值', "conflict_note": None, "keywords": []}

    def test_render_obj_list_relation_order(self):
        items = [
            {
                "evidence": "frontmatter:replaces",
                "note": "回",
                "type": "replaces",
                "target": "ITKB-0300",
            }
        ]
        text = "relations:\n" + render_obj_list(items)
        assert text == (
            "relations:\n"
            '- target: "ITKB-0300"\n'
            '  type: "replaces"\n'
            '  note: "回"\n'
            '  evidence: "frontmatter:replaces"'
        )
        assert yaml.safe_load(text)["relations"] == items

    def test_render_obj_list_graph_node_order(self):
        items = [{"name": "内网不通", "kind": "symptom"}]
        text = "graph_nodes:\n" + render_obj_list(items)
        assert text == (
            "graph_nodes:\n"
            '- kind: "symptom"\n'
            '  name: "内网不通"'
        )
        assert yaml.safe_load(text)["graph_nodes"] == [{"kind": "symptom", "name": "内网不通"}]

    def test_render_obj_list_entity_order(self):
        items = [{"type": "协议", "name": "VPN"}]
        text = "entities:\n" + render_obj_list(items)
        assert yaml.safe_load(text)["entities"] == [{"name": "VPN", "type": "协议"}]
        assert text == 'entities:\n- name: "VPN"\n  type: "协议"'

    def test_render_obj_list_rejects_str_mixed_into_object_list(self):
        # str 混入对象列表:显式拒绝,不得把 str 当本应转义的对象条目静默写入
        with pytest.raises(ValueError, match="对象条目"):
            render_obj_list([{"kind": "symptom", "name": "内网不通"}, "oops"])

    def test_render_frontmatter_block_rejects_dict_mixed_into_string_list(self):
        # 字符串列表混入 dict:显式拒绝,不得 str(dict) 静默塞入
        with pytest.raises(ValueError, match="keywords.*混合"):
            render_frontmatter_block(
                {"keywords": ["vpn", {"name": "内网不通"}]}
            )

    def test_render_frontmatter_block_rejects_dict_str_mixed_list(self):
        # 对象列表位置混入 str(整体非纯 dict 列表)同样显式拒绝
        with pytest.raises(ValueError, match="relations.*混合"):
            render_frontmatter_block(
                {
                    "relations": [
                        {"target": "ITKB-0300", "type": "replaces",
                         "note": "n", "evidence": "frontmatter:replaces"},
                        "oops",
                    ]
                }
            )


class TestWriteCard:
    """"原子写与换行约定。"""

    def test_crlf_file_keeps_crlf_line_endings(self, tmp_path):
        path = tmp_path / "card.md"
        path.write_bytes(
            (
                "---\n"
                'id: "ITKB-0001"\n'
                'replaces: []\n'
                "---\n"
                + CARD_BODY
            ).replace("\n", "\r\n").encode("utf-8")
        )
        meta, body = load_card(path)
        write_card(path, meta, body)

        raw = path.read_bytes()
        assert b"\r\n" in raw  # 原文件换行约定不变:不做换行转换
        assert b"\r\n\r\n---" not in raw  # 无双重换行
        meta2, body2 = load_card(path)
        assert body2 == body
        assert meta2 == meta

    def test_rewrites_via_temp_file_no_stray_tmp(self, tmp_path):
        path = tmp_path / "card.md"
        _write_fixture(path)
        meta, body = load_card(path)
        write_card(path, migrate_replaces(meta), body)
        assert list(tmp_path.glob("*.tmp")) == []  # 临时文件已被 replace 掉

    def test_write_failure_cleans_tmp_and_reraises(self, tmp_path, monkeypatch):
        # 写失败(replace 抛错)必须清理 tmp 后原样 re-raise,不留 .tmp 残留(裁决 9)
        path = tmp_path / "card.md"
        _write_fixture(path)
        meta, body = load_card(path)

        def _boom(src, dst):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(
            "rag_pipeline.ingestion.frontmatter_editor.os.replace", _boom
        )
        with pytest.raises(OSError, match="simulated replace failure"):
            write_card(path, meta, body)
        assert list(tmp_path.glob("*.tmp")) == []
        # 原卡不被半成品破坏
        meta2, body2 = load_card(path)
        assert meta2 == meta
        assert body2 == CARD_BODY

    def test_load_card_rejects_missing_frontmatter(self, tmp_path):
        path = tmp_path / "plain.md"
        path.write_text("没有 frontmatter 的正文", encoding="utf-8")
        with pytest.raises(ValueError, match="frontmatter"):
            load_card(path)

    def test_load_card_rejects_unparsable_frontmatter_yaml(self, tmp_path):
        # F6:坏 YAML 必须显式失败,不得静默回退成空 frontmatter
        path = tmp_path / "bad.md"
        path.write_text(
            "---\nid: [未闭合的流\n---\n正文", encoding="utf-8", newline="\n"
        )
        with pytest.raises(ValueError, match="frontmatter YAML 解析失败"):
            load_card(path)

    def test_load_card_rejects_non_mapping_frontmatter(self, tmp_path):
        # F6:frontmatter 是序列(如 "- a")而非键值映射,显式拒绝
        path = tmp_path / "seq.md"
        path.write_text("---\n- a\n- b\n---\n正文", encoding="utf-8", newline="\n")
        with pytest.raises(ValueError, match="期望键值映射.*list"):
            load_card(path)
