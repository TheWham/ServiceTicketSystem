# -*- coding: utf-8 -*-
"""wiki_generator 图字段序列化(Task 5)+ boost 文本不变性金标。

覆盖:
1. 含 typed entities / relations / graph_nodes / graph_meta_source 的 meta,
   经 render_frontmatter 渲染后可被 yaml.safe_load 无损往返,三新键完整
   (Task 1 EntityDef / RelationDef / GraphNodeDef 形态:{"name","type"} /
   {"target","type","note","evidence"} / {"kind","name"});
2. 旧形态 meta(无新键)输出不含 relations / graph_nodes / graph_meta_source;
3. 空对象列表不写键(F6:单写 ``key:`` 行会被 yaml.safe_load 解析为 None),
   entities / relations / graph_nodes 三键各配一条断言;graph_meta_source
   模式对齐 effective_date 的仅非空输出;
4. boost 文本不变性金标:真语料卡 ITKB-NET-001 的实际 entities 列表逐字写死,
   旧扁平串的 join 与迁移后 [{name,...}] 取 name 的 join 逐字符相等,且经
   render_card 渲染 + ParentChildChunker 切片的真实消费链路产出的检索增强行
   实体段与旧值逐字符相等(检索行为不漂移;语料本体由 Task 7 增补)。
"""

import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from rag_pipeline.chunking.parent_child import ParentChildChunker  # noqa: E402
from rag_pipeline.config import ChunkingConfig  # noqa: E402
from rag_pipeline.ingestion.clean_pipeline import Entry  # noqa: E402
from rag_pipeline.ingestion.wiki_generator import render_card, render_frontmatter  # noqa: E402

# ITKB-NET-001 frontmatter 的实际扁平 entities 列表(逐字,迁移前的真实值)
ITKB_NET_001_FLAT_ENTITIES = [
    "无线局域网(WiFi)",
    "无线网卡驱动",
    "DHCP",
    "MAC地址",
    "无线接入点(AP)",
    "ipconfig",
    "802.1X认证",
    "NPS服务器",
]
ITKB_NET_001_KEYWORDS = ["WiFi", "无线网络", "无法连接", "网络断开", "WLAN", "信号弱"]


def _make_entry(**kw) -> Entry:
    base = dict(code="NET-001", title="公司WiFi连接故障排查", category="网络连接问题",
                keywords=list(ITKB_NET_001_KEYWORDS), is_appendix=False)
    base.update(kw)
    return Entry(**base)


def _parse_frontmatter(text: str) -> dict:
    """解析 render_frontmatter 输出(含首尾 ``---`` 行)为 dict。"""
    assert text.startswith("---\n") and text.endswith("\n---")
    return yaml.safe_load(text[4:-4].strip())


def _meta(**extra) -> dict:
    meta = {
        "title": "公司WiFi连接故障排查",
        "effective_date": "2024-03-01",
        "version": "v1.0",
        "status": "现行",
        "replaces": [],
        "entities": [{"name": n, "type": "配置项"} for n in ITKB_NET_001_FLAT_ENTITIES[:3]],
        "summary": "解决电脑无法连接公司WiFi问题。",
        "meta_source": "llm",
    }
    meta.update(extra)
    return meta


def test_render_graph_fields_yaml_roundtrip():
    """① typed 三新键 + 对象列表 entities 渲染后 yaml.safe_load 无损往返。"""
    meta = _meta(
        entities=[
            {"name": "无线局域网(WiFi)", "type": "配置项"},
            {"name": "NPS服务器", "type": "设备"},
        ],
        relations=[
            {"target": "ITKB-NET-002", "type": "related",
             "note": "同为无线链路层故障", "evidence": "frontmatter:replaces"},
        ],
        graph_nodes=[
            {"kind": "symptom", "name": "WiFi反复掉线"},
            {"kind": "tool", "name": "ipconfig"},
        ],
        graph_meta_source="llm",
    )
    parsed = _parse_frontmatter(render_frontmatter(_make_entry(), meta))
    assert parsed["entities"] == meta["entities"]
    assert parsed["relations"] == meta["relations"]
    assert parsed["graph_nodes"] == meta["graph_nodes"]
    assert parsed["graph_meta_source"] == "llm"


def test_render_old_meta_omits_new_keys():
    """② 旧 meta(无新键)输出不含三新键。"""
    text = render_frontmatter(_make_entry(), _meta(entities=[
        {"name": "DHCP", "type": "协议"},
    ]))
    parsed = _parse_frontmatter(text)
    for key in ("relations", "graph_nodes", "graph_meta_source"):
        assert key not in parsed
        assert f"\n{key}:" not in text, f"旧 meta 不得输出 {key} 行"


def test_empty_entities_writes_no_key():
    """③ F6:entities 为空对象列表 → 不写键(单写 ``entities:`` 行会解析为 None)。"""
    text = render_frontmatter(_make_entry(), _meta(entities=[]))
    assert "\nentities:" not in text
    assert "entities" not in _parse_frontmatter(text)


def test_empty_relations_writes_no_key():
    text = render_frontmatter(_make_entry(), _meta(relations=[]))
    assert "\nrelations:" not in text
    assert "relations" not in _parse_frontmatter(text)


def test_empty_graph_nodes_writes_no_key():
    text = render_frontmatter(_make_entry(), _meta(graph_nodes=[]))
    assert "\ngraph_nodes:" not in text
    assert "graph_nodes" not in _parse_frontmatter(text)


def test_empty_graph_meta_source_writes_no_key():
    """graph_meta_source 仅非空输出(模式对齐 effective_date),空串不落键。"""
    text = render_frontmatter(_make_entry(), _meta(graph_meta_source=""))
    assert "\ngraph_meta_source:" not in text
    assert "graph_meta_source" not in _parse_frontmatter(text)


def test_boost_text_invariance_golden():
    """④ 金标:旧扁平 join 与迁移后 typed join 逐字符相等,真实切片链路不漂移。

    旧扁平形态 ``"、".join(entities)`` 的实体段必须与迁移后
    ``"、".join(e["name"] for e in entities)`` 逐字符相等
    (parent_child.py:116 检索增强行取值迁移);本测试用真卡
    ITKB-NET-001 的实际 entities 消除构造失真。
    """
    typed = [{"name": n, "type": "配置项"} for n in ITKB_NET_001_FLAT_ENTITIES]
    old_flat_join = "、".join(ITKB_NET_001_FLAT_ENTITIES)          # 迁移前的旧扁平 join
    migrated_join = "、".join(e["name"] for e in typed)            # 迁移后的取 name join
    assert migrated_join == old_flat_join, "两序 join 必须逐字符相等"

    # 真实消费链路:typed 卡经 render_card 落盘 → ParentChildChunker 切片,
    # 首子块的检索增强行实体段必须仍逐字符等于旧扁平 join(boost_injection=first)。
    entry = _make_entry(fields={"现象描述": "电脑无法连接公司WiFi,无线图标显示已连接但无法上网。",
                               "排查步骤": "1. ipconfig /all 查看 IP 地址;2. 确认 802.1X认证 已通过。"})
    meta = _meta(entities=typed)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "ITKB-NET-001.md"
        path.write_text(render_card(entry, meta), encoding="utf-8")
        chunker = ParentChildChunker(config=ChunkingConfig(child_size=512))
        _parent, children = chunker.split_wiki_document(str(path))
        assert children, "夹具卡应产出子块"
        first = children[0].page_content
        expected_line = (f"【检索增强：关键词 {'、'.join(ITKB_NET_001_KEYWORDS)}"
                         f"｜实体 {old_flat_join}】")
        assert expected_line in first, "首子块检索增强行实体段必须与旧扁平 join 逐字符相等"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
