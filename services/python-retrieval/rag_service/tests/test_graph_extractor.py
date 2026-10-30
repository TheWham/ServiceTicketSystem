# -*- coding: utf-8 -*-
"""GraphExtractor 两步 LLM 萃取测试(Task 3)。

被测对象 rag_pipeline/ingestion/graph_extractor.py:LLM 两步图萃取器——
1. normalize_entities:glossary 归一,词表(含别名)与正文证据之外的名称一律拒;
2. extract_relations_and_nodes:卡间关系(证据门 + 合法 target 门)+ 卡内结构节点。

测试不打真 LLM:_StubExtractor 子类覆写 _chat_json 注入固定 JSON / 抛错
(模式参照 test_degraded_rejection.py 的 _StubReranker 注入法);
代码围栏容忍用例注入桩 client 走真实 _chat_json -> LlmSynthesizer._parse_json_loose;
缓存目录一律 tmp_path。
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_pipeline.ingestion.graph_schema import (  # noqa: E402
    EntityDef,
    GraphNodeDef,
    RelationDef,
    validate_entities,
    validate_graph_nodes,
    validate_relations,
)
from rag_pipeline.ingestion.graph_extractor import (  # noqa: E402
    MAX_ENTITIES_PER_CARD,
    CardDigest,
    GraphExtractor,
)

CFG = {"api_key": "stub-key", "base_url": "http://stub.local", "chat_model": "stub-model"}

GLOSSARY = {
    "entities": {
        "防火墙": {"type": "配置项", "aliases": ["FW"]},
    }
}


class _StubExtractor(GraphExtractor):
    """替身:不触网,_chat_json 返回用例注入的固定 JSON(或抛注入的异常)。"""

    def __init__(self, payload=None, error=None, cache_dir=None):
        super().__init__(CFG, cache_dir)
        self.payload = payload
        self.error = error
        self.chat_calls = 0

    def _chat_json(self, model, system_prompt, user_prompt):
        self.chat_calls += 1
        if self.error is not None:
            raise self.error
        return self.payload


def _digest(wiki_id="KB-1", **kw):
    return CardDigest(
        wiki_id=wiki_id,
        title=kw.get("title", f"知识卡 {wiki_id}"),
        summary=kw.get("summary", f"{wiki_id} 的一句话摘要"),
        entities=kw.get("entities", []),
        keywords=kw.get("keywords", []),
        body_headline=kw.get("body_headline", ""),
    )


def _as_dicts(items):
    import dataclasses

    return [dataclasses.asdict(x) for x in items]


# ---------- ① glossary 约束:词表与正文证据之外的名称一律拒 ----------

def test_glossary_constraint_rejects_unbacked_names(tmp_path):
    body = "防火墙策略更新后无法登录,请检查堡垒机的会话并发配置。"
    payload = {
        "entities": [
            {"name": "FW", "type": "设备"},              # 别名命中词表 -> 归一为标准名+词表类型
            {"name": "量子加密网关", "type": "设备"},    # 词表外且正文无证据 -> 拒
        ],
        "new_entities": [
            {"name": "堡垒机", "type": "账号权限"},      # 正文中出现 -> 新增实体
            {"name": "暗物质路由器", "type": "设备"},    # 词表外且正文无证据 -> 拒
        ],
    }
    ex = _StubExtractor(payload, cache_dir=str(tmp_path))
    normalized, new_entities = ex.normalize_entities(
        "KB-1", ["FW", "堡垒机"], body, glossary=GLOSSARY
    )
    assert normalized == [
        EntityDef(name="防火墙", type="配置项"),
        EntityDef(name="堡垒机", type="账号权限"),
    ]
    assert new_entities == [EntityDef(name="堡垒机", type="账号权限")]
    assert ex.last_used_llm is True
    # 结果再过一遍 Task 1 校验器必须全通过
    assert validate_entities(_as_dicts(normalized)) == normalized
    assert validate_entities(_as_dicts(new_entities)) == new_entities


def test_entity_count_capped(tmp_path):
    names = [f"实体{i:02d}" for i in range(MAX_ENTITIES_PER_CARD + 5)]
    body = "、".join(names)
    payload = {
        "entities": [{"name": n, "type": "概念"} for n in names],
        "new_entities": [],
    }
    ex = _StubExtractor(payload, cache_dir=str(tmp_path))
    normalized, new_entities = ex.normalize_entities("KB-1", names, body)
    assert len(normalized) == MAX_ENTITIES_PER_CARD
    assert len(new_entities) == MAX_ENTITIES_PER_CARD


# ---------- ② _parse_json_loose 容忍 ```json 围栏(真实 _chat_json 路径) ----------

def test_fenced_json_tolerated(tmp_path):
    payload = {"entities": [{"name": "防火墙", "type": "设备"}], "new_entities": []}
    fenced = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
    ex = GraphExtractor(CFG, cache_dir=str(tmp_path))
    ex.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kw: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=fenced))]
                )
            )
        )
    )
    normalized, new_entities = ex.normalize_entities(
        "KB-1", ["防火墙"], "防火墙策略说明与排障步骤"
    )
    assert normalized == [EntityDef(name="防火墙", type="设备")]
    assert new_entities == [EntityDef(name="防火墙", type="设备")]
    assert ex.last_used_llm is True


# ---------- ③ 输出经 Task 1 校验器全通过;未知 target 被拒时不产出该条 ----------

def test_relations_guards_and_validator_roundtrip(tmp_path):
    corpus = [
        _digest("KB-1", title="密码登录排障", body_headline="无法登录,检查堡垒机并发"),
        _digest("KB-2", title="账号锁定处置"),
        _digest("KB-3", title="VPN 配置变更"),
    ]
    payload = {
        "relations": [
            {  # 合法:target 在语料内、类型合法、有证据
                "target": "KB-2", "type": "same_root_cause",
                "note": "", "evidence": "两卡均为同一策略下发错误引起",
            },
            {  # 未知 target -> 被拒,不产出该条
                "target": "GHOST-9", "type": "related",
                "note": "", "evidence": "幻觉证据",
            },
            {  # 无证据 -> 校验器丢弃
                "target": "KB-3", "type": "related",
                "note": "", "evidence": None,
            },
            {  # 空白证据 -> 校验器丢弃
                "target": "KB-3", "type": "related",
                "note": "", "evidence": "   ",
            },
            {  # 非法关系类型 -> 拒
                "target": "KB-3", "type": "幻觉关系",
                "note": "", "evidence": "原文证据",
            },
        ],
        "graph_nodes": [
            {"kind": "symptom", "name": "无法登录"},
            {"kind": "ghost_kind", "name": "未知类型节点"},
            {"kind": "tool", "name": ""},  # 空名 -> 拒
            {"kind": "root_cause", "note": "无 name 字段"},  # 缺 name -> 拒
        ],
    }
    ex = _StubExtractor(payload, cache_dir=str(tmp_path))
    relations, graph_nodes = ex.extract_relations_and_nodes(corpus[0], corpus)
    assert relations == [
        RelationDef(target="KB-2", type="same_root_cause", note="", evidence="两卡均为同一策略下发错误引起"),
    ]
    assert graph_nodes == [GraphNodeDef(kind="symptom", name="无法登录")]
    # 未知 target 被拒后,剩余输出再过 Task 1 校验器必须全通过、不抛错
    valid_targets = {d.wiki_id for d in corpus}
    assert validate_relations(_as_dicts(relations), valid_targets) == relations
    assert validate_graph_nodes(_as_dicts(graph_nodes)) == graph_nodes


# ---------- ④ 两次尝试均失败 -> 规则兜底 ----------

def test_fallback_after_two_failed_attempts(tmp_path):
    ex = _StubExtractor(error=RuntimeError("stub 网络故障"), cache_dir=str(tmp_path))
    flat = ["无线局域网(WiFi)", "堡垒机"]
    normalized, new_entities = ex.normalize_entities(
        "KB-1", flat, "正文与实体名毫无交集"
    )
    assert normalized == [EntityDef(name="无线局域网(WiFi)", type="概念"),
                          EntityDef(name="堡垒机", type="概念")]
    assert new_entities == []
    assert ex.last_used_llm is False
    assert ex.chat_calls == 2  # 首次 + 1 次重试,共两次 LLM 尝试

    relations, graph_nodes = ex.extract_relations_and_nodes(
        _digest("KB-1"), [_digest("KB-1"), _digest("KB-2")]
    )
    assert relations == []
    assert graph_nodes == []
    assert ex.last_used_llm is False
    assert ex.chat_calls == 4  # ent 两次 + rel 两次
    # 兜底结果不落缓存(不把降级产物固化到磁盘)
    assert list(tmp_path.iterdir()) == []


# ---------- ⑤ 缓存命中不再调 _chat_json ----------

def test_cache_hit_skips_llm_call(tmp_path):
    payload = {
        "entities": [{"name": "防火墙", "type": "配置项"}],
        "new_entities": [],
        "relations": [{"target": "KB-2", "type": "related", "note": "", "evidence": "同属账号类问题"}],
        "graph_nodes": [{"kind": "symptom", "name": "无法登录"}],
    }
    ex = _StubExtractor(payload, cache_dir=str(tmp_path))
    corpus = [_digest("KB-1"), _digest("KB-2")]

    norm1, new1 = ex.normalize_entities("KB-1", ["防火墙"], "防火墙策略正文", glossary=GLOSSARY)
    assert ex.chat_calls == 1
    norm2, new2 = ex.normalize_entities("KB-1", ["防火墙"], "防火墙策略正文", glossary=GLOSSARY)
    assert ex.chat_calls == 1  # 第二次命中磁盘缓存,零 LLM 调用
    assert (norm1, new1) == (norm2, new2)
    assert ex.last_used_llm is True  # 缓存内容源自 LLM,provenance 仍为 llm

    rels1, nodes1 = ex.extract_relations_and_nodes(corpus[0], corpus)
    assert ex.chat_calls == 2
    rels2, nodes2 = ex.extract_relations_and_nodes(corpus[0], corpus)
    assert ex.chat_calls == 2  # rel 步同样命中缓存
    assert (rels1, nodes1) == (rels2, nodes2)

    # 缓存文件命名形如 graph_{ent|rel}_{sha1(user_prompt)}.json
    names = sorted(p.name for p in tmp_path.iterdir())
    assert len(names) == 2
    assert any(n.startswith("graph_ent_") and n.endswith(".json") for n in names)
    assert any(n.startswith("graph_rel_") and n.endswith(".json") for n in names)
