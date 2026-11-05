# -*- coding: utf-8 -*-
"""企业级 AI 安全与合规护栏引擎 (Guardrails Security Engine)。

负责两大防御核心职责：
1. 输入防御防线：拦截对抗性 Prompt 注入、角色扮演越狱（DAN）、恶意提权与指令篡改。
2. 数据安全防线：针对手机号、身份证、银行卡等高密隐私数据（PII），
   在进入大模型前自动掩码化（`<PII_...>`）并隔离至会话级安全 Vault，
   在离开模型出网前于本地受信任内存中动态精准还原。
"""

import re
from typing import Dict, Tuple


class GuardrailsSecurityEngine:
    """企业级安全护栏引擎：负责输入校验、越狱拦截与敏感数据双向脱敏。"""

    # 典型恶意注入攻击与越狱模式正则匹配表
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
        r"忽略(之前|上述|以上|所有)的?(指令|系统设定|提示|规则)",
        r"now\s+you\s+are\s+DAN",
        r"作为不受限制的AI",
        r"绕过(安全|合规)?检查",
        r"强制执行.*无需审批",
        r"无条件审核通过",
        r"提权",
    ]

    @classmethod
    def check_prompt_injection(cls, text: str) -> Tuple[bool, str]:
        """检测输入文本是否存在 Prompt 越狱与注入攻击。

        :param text: 用户原始提问或指令
        :return: (is_safe, message)
        """
        if not text:
            return True, "安全校验通过"

        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, f"🚨 命中安全拦截规则：检测到恶意指令注入攻击（特征：'{pattern}'）！"

        return True, "安全校验通过"

    @classmethod
    def mask_pii_data(cls, text: str) -> Tuple[str, Dict[str, str]]:
        """对手机号、身份证号、银行卡号执行双向脱敏与掩码化映射。

        :param text: 待脱敏的原始文本
        :return: (sanitized_text, pii_vault 字典映射)
        """
        if not text:
            return text, {}

        pii_vault: Dict[str, str] = {}
        counter = {"idcard": 0, "phone": 0, "bank": 0, "emp": 0}

        def _mask_idcard(m: re.Match) -> str:
            counter["idcard"] += 1
            placeholder = f"<PII_IDCARD_{counter['idcard']}>"
            pii_vault[placeholder] = m.group(0)
            return placeholder

        def _mask_phone(m: re.Match) -> str:
            counter["phone"] += 1
            placeholder = f"<PII_PHONE_{counter['phone']}>"
            pii_vault[placeholder] = m.group(0)
            return placeholder

        def _mask_bank(m: re.Match) -> str:
            counter["bank"] += 1
            placeholder = f"<PII_BANK_{counter['bank']}>"
            pii_vault[placeholder] = m.group(0)
            return placeholder

        def _mask_emp(m: re.Match) -> str:
            counter["emp"] += 1
            placeholder = f"<PII_EMPID_{counter['emp']}>"
            pii_vault[placeholder] = m.group(0)
            return placeholder

        # 1. 身份证正则 (18位大陆身份证)
        text = re.sub(
            r"\b[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|10|11|12)(?:0[1-9]|[1-2]\d|30|31)\d{3}[\dXx]\b",
            _mask_idcard,
            text,
        )
        # 2. 手机号正则 (11位大陆号码)
        text = re.sub(r"\b1[3-9]\d{9}\b", _mask_phone, text)
        # 3. 银行卡号正则 (16-19位数字)
        text = re.sub(r"\b[1-9]\d{15,18}\b", _mask_bank, text)
        # 4. 企业员工工号正则 (如 E10023, U_ADMIN01)
        text = re.sub(r"(?<![a-zA-Z0-9])(U_[A-Z0-9]+|E\d{4,6})(?![a-zA-Z0-9])", _mask_emp, text)

        return text, pii_vault

    @classmethod
    def unmask_pii_data(cls, text: str, pii_vault: Dict[str, str]) -> str:
        """根据会话安全 Vault 字典，将模型输出文本中的占位符还原为真实数据。

        :param text: 含有 <PII_...> 占位符的模型输出文本
        :param pii_vault: 会话级临时加密映射字典
        :return: 还原真实敏感数据后的文本
        """
        if not text or not pii_vault:
            return text

        restored = text
        for placeholder, original in pii_vault.items():
            restored = restored.replace(placeholder, original)
        return restored
