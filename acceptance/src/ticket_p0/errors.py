# -*- coding: utf-8 -*-
"""统一业务异常：BizError(code,msg) 与字段级校验失败 ValidationFailed（SPEC §2.7）"""
from dataclasses import dataclass


@dataclass
class FieldError:
    """单字段校验失败（多字段越界时逐字段收集，一次性返回）"""
    field: str
    code: int
    msg: str


class BizError(Exception):
    """业务错误：code 取值仅允许 SPEC §2.7 错误码表"""

    def __init__(self, code: int, msg: str):
        super().__init__(f"[{code}] {msg}")
        self.code = code
        self.msg = msg

    def __repr__(self):
        return f"BizError(code={self.code}, msg={self.msg!r})"


class ValidationFailed(BizError):
    """DTO 字段校验失败：携带全部 FieldError，不逐一中断"""

    def __init__(self, errors):
        self.errors = list(errors)
        merged = "; ".join(f"{e.field}: {e.msg}" for e in self.errors)
        super().__init__(40000, merged)

    @property
    def fields(self):
        return {e.field for e in self.errors}
