# -*- coding: utf-8 -*-
import json
import pytest
from pathlib import Path
from rag_pipeline.graph.schema import ITRelationEnum, GroundedTriple
from rag_pipeline.graph.extractor import (
    parse_card_markdown,
    validate_triples_against_source,
    inject_frontmatter_governance_triples,
    save_triples_cache,
    load_triples_cache,
)

SAMPLE_CARD = """---
id: "ITKB-VPN-001"
title: "VPN连接失败（拨号/认证失败）"
category: "VPN与远程办公"
department: "IT 部"
replaces: ["ITKB-LEG-VPN-001"]
entities: ["VPN", "SSL VPN", "AD账号", "预共享密钥"]
---

# 【VPN-001】VPN连接失败

## 常见根因
- ③ 用户名密码错误或AD账号被锁定
- ⑥ 证书过期（SSL VPN）
"""


def test_parse_card_markdown():
    meta, body = parse_card_markdown(SAMPLE_CARD)
    assert meta["id"] == "ITKB-VPN-001"
    assert meta["replaces"] == ["ITKB-LEG-VPN-001"]
    assert "AD账号" in meta["entities"]
    assert "## 常见根因" in body


def test_validate_triples_against_source():
    valid_triple = GroundedTriple(
        head="VPN",
        relation=ITRelationEnum.ROOT_CAUSE,
        tail="AD账号",
        evidence_quote="用户名密码错误或AD账号被锁定",
    )
    fake_triple = GroundedTriple(
        head="VPN",
        relation=ITRelationEnum.ROOT_CAUSE,
        tail="外星人攻击",
        evidence_quote="由于火星网络风暴导致彻底断网",
    )
    filtered = validate_triples_against_source([valid_triple, fake_triple], SAMPLE_CARD)
    assert len(filtered) == 1
    assert filtered[0].tail == "AD账号"


def test_inject_frontmatter_governance_triples():
    meta, _ = parse_card_markdown(SAMPLE_CARD)
    gov_triples = inject_frontmatter_governance_triples(meta)
    assert len(gov_triples) == 4
    # 验证废止与替代
    replaces_triples = [t for t in gov_triples if t.relation == ITRelationEnum.REPLACES]
    assert len(replaces_triples) == 1
    assert replaces_triples[0].head == "ITKB-VPN-001"
    assert replaces_triples[0].tail == "ITKB-LEG-VPN-001"
    # 验证状态
    status_triples = [t for t in gov_triples if t.relation == ITRelationEnum.STATUS_IS]
    assert len(status_triples) == 2


def test_cache_save_and_load(tmp_path: Path):
    cache_file = tmp_path / "triples_cache.json"
    triples = [
        GroundedTriple(
            head="VPN",
            relation=ITRelationEnum.ROOT_CAUSE,
            tail="AD账号",
            evidence_quote="用户名密码错误或AD账号被锁定",
        )
    ]
    save_triples_cache(triples, cache_file)
    assert cache_file.exists()

    loaded = load_triples_cache(cache_file)
    assert len(loaded) == 1
    assert loaded[0].head == "VPN"
    assert loaded[0].relation == ITRelationEnum.ROOT_CAUSE
