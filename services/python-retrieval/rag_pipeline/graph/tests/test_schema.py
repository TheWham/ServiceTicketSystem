# -*- coding: utf-8 -*-
import pytest
from pydantic import ValidationError

from rag_pipeline.graph.schema import (
    ITRelationEnum,
    GroundedTriple,
    canonicalize_entity,
    ExtractionOutput,
)


def test_valid_triple_creation():
    triple = GroundedTriple(
        head="VPN错误691",
        relation=ITRelationEnum.ROOT_CAUSE,
        tail="AD域账号锁定",
        evidence_quote="密码输错或AD账号被锁定可能导致认证失败",
    )
    assert triple.head == "VPN错误691"
    assert triple.relation == ITRelationEnum.ROOT_CAUSE
    assert triple.relation.value == "诱发根因"
    assert triple.tail == "AD域账号锁定"


def test_invalid_relation_rejected():
    with pytest.raises(ValidationError):
        GroundedTriple(
            head="VPN",
            relation="这是一个非法的随便造的关系",
            tail="网络故障",
            evidence_quote="some quote",
        )


def test_sentence_entity_rejected():
    with pytest.raises(ValidationError):
        GroundedTriple(
            head="这是一个长句子。用户在连接VPN的时候发生了严重的错误",
            relation=ITRelationEnum.ROOT_CAUSE,
            tail="正常尾实体",
            evidence_quote="quote",
        )


def test_long_entity_rejected():
    with pytest.raises(ValidationError):
        GroundedTriple(
            head="这个实体的名字超级长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长",
            relation=ITRelationEnum.ROOT_CAUSE,
            tail="正常尾实体",
            evidence_quote="quote",
        )


def test_canonicalize_entity():
    assert canonicalize_entity("AD域") == "AD域控制器"
    assert canonicalize_entity("域控") == "AD域控制器"
    assert canonicalize_entity("陈主任") == "陈梓豪"
    assert canonicalize_entity("普通实体") == "普通实体"


def test_extraction_output_model():
    data = {
        "triples": [
            {
                "head": "VPN",
                "relation": "诱发根因",
                "tail": "AD域账号锁定",
                "evidence_quote": "测试原句",
            }
        ]
    }
    res = ExtractionOutput.model_validate(data)
    assert len(res.triples) == 1
    assert res.triples[0].head == "VPN"
