# -*- coding: utf-8 -*-
"""Pydantic 严格模式三元组 Schema 与实体消歧规范体系。"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ITRelationEnum(str, Enum):
    """受控的 IT 领域与制度核心关系谓词枚举。"""

    # 1. 故障因果与排查
    ROOT_CAUSE = "诱发根因"
    DERIVED_ISSUE = "衍生次生故障"
    PRE_CHECK = "前置排查动作"
    RESOLVED_BY = "处置动作"

    # 2. 资产与依赖
    DEPENDS_ON = "依赖系统组件"
    DEPENDS_ON_NETWORK = "依赖网络通道"
    DEPENDS_ON_AUTH = "依赖身份源"

    # 3. 工单流转与规约
    OWNED_BY = "主责运维组"
    ESCALATE_TO = "SLA升级流转"
    DELEGATE_TO = "出差代签人"
    AVOID_TO = "利益回避转派"

    # 4. 知识生命周期与版本
    REPLACES = "废止并替代"
    STATUS_IS = "生效状态"


class GroundedTriple(BaseModel):
    """带原文佐证依据的原子三元组模型。"""

    head: str = Field(
        ...,
        min_length=2,
        max_length=35,
        description="头实体，必须是具体专业术语、错误码、卡片ID或岗位人名，严禁使用长句",
    )
    relation: ITRelationEnum = Field(..., description="严格受控的关系谓词")
    tail: str = Field(
        ...,
        min_length=1,
        max_length=45,
        description="尾实体，必须是具体的术语、系统、团队、代签人或处置动作，严禁包含复合长句",
    )
    evidence_quote: str = Field(
        ...,
        min_length=2,
        description="从原始知识库文档中摘录的直接证据原句（不可修改，必须能完全匹配）",
    )

    @field_validator("head", "tail")
    @classmethod
    def reject_sentences_and_noise(cls, v: str) -> str:
        s = v.strip()
        # 拦截长句子标点
        for punct in ["。", "；", "！", "？", "\n"]:
            if punct in s:
                raise ValueError(f"实体不能是长句子或包含换行: '{s}'")
        return s


class ExtractionOutput(BaseModel):
    """单篇文档抽取的结构化响应外壳。"""

    triples: List[GroundedTriple] = Field(default_factory=list, description="抽取出的三元组列表")


# ==============================================================================
# 实体标准化与别名消歧字典 (Canonicalization)
# ==============================================================================

ENTITY_ALIAS_MAP: Dict[str, str] = {
    # 账号与认证体系
    "AD域": "AD域控制器",
    "域控": "AD域控制器",
    "Active Directory": "AD域控制器",
    "ActiveDirectory": "AD域控制器",
    "AD账号": "AD域账号",
    "域账号": "AD域账号",
    "MFA": "双因子MFA认证",
    "双因素认证": "双因子MFA认证",
    # 网络与办公
    "SSLVPN": "SSL VPN",
    "虚拟专用网": "VPN",
    "公司VPN": "VPN",
    # 典型人物与角色消歧（对齐制度中的标准岗位）
    "陈主任": "陈梓豪",
    "监察委陈主任": "陈梓豪",
    "监察委员会主任陈梓豪": "陈梓豪",
    "赵副主任": "赵小雪",
    "监察委副主任赵小雪": "赵小雪",
    "王总监": "王大明",
    "交付总监王大明": "王大明",
    # 团队组织
    "网络组": "IT网络基础运维组",
    "系统组": "IT系统组",
    "桌面支持": "桌面运维支持组",
}


def canonicalize_entity(name: str) -> str:
    """对实体名称执行轻量消歧与归一化，消除同义词断链。"""
    cleaned = name.strip()
    return ENTITY_ALIAS_MAP.get(cleaned, cleaned)
