# -*- coding: utf-8 -*-
"""附件校验（SPEC §1.7 / 协议书 M-08、TC-10）：
不信任扩展名，必须读取文件头部魔数判定真实类型，防 EXE 伪装图片。"""
from .constants import ATTACH_EXTS, ATTACH_MAX_BYTES, CODE_BIZ_ERROR
from .errors import BizError

# 魔数签名：JPEG=FFD8FF，PNG=89504E47 0D0A1A0A
_MAGIC_JPG = b"\xff\xd8\xff"
_MAGIC_PNG = b"\x89PNG\r\n\x1a\n"


def sniff_image_type(content: bytes):
    """按魔数嗅探真实图片类型；非图片（如 MZ/PE 可执行文件）返回 None"""
    if content[:3] == _MAGIC_JPG:
        return "jpg"
    if content[:8] == _MAGIC_PNG:
        return "png"
    return None


def validate_upload(filename: str, content: bytes) -> str:
    """四维校验：扩展名白名单 → 大小 → 魔数 → 魔数与扩展名一致。通过返回小写扩展名。"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ATTACH_EXTS:
        raise BizError(CODE_BIZ_ERROR, "仅支持 jpg/png 格式")
    if len(content) > ATTACH_MAX_BYTES:
        raise BizError(CODE_BIZ_ERROR, "单张不超过 5MB")
    real = sniff_image_type(content)
    if real is None:
        # 魔数不是图片：典型如 EXE(MZ) 伪装 .jpg —— TC-10 注入向量，拒绝
        raise BizError(CODE_BIZ_ERROR, "仅支持 jpg/png 格式")
    if (ext in ("jpg", "jpeg") and real != "jpg") or (ext == "png" and real != "png"):
        # 扩展名与真实内容不符（如 png 改名 .jpg），拒绝
        raise BizError(CODE_BIZ_ERROR, "仅支持 jpg/png 格式")
    return ext
