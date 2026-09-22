# -*- coding: utf-8 -*-
"""提单 DTO 字段级校验（SPEC §1.7 校验矩阵 / 协议书 M-01）：
逐字段收集错误一次性返回；CMDB 联动校验由 service 在字段校验通过后执行。"""
from datetime import datetime

from .constants import (
    ASSET_ID_RE, ATTACH_MAX_COUNT, ATTACH_URL_RE, CATEGORIES, CODE_BIZ_ERROR,
    DESC_MAX_LEN, DESC_MIN_LEN, PRIORITIES, TIME_FMT, TITLE_MAX_LEN,
)
from .errors import FieldError


def validate_submission(dto: dict, now: datetime) -> list:
    """返回 FieldError 列表；空列表 = 全部通过。"""
    errs = []

    # title：必填 1~50，含尖括号拒绝（XSS 防线，协议书 TC-10）
    title = (dto.get("title") or "").strip()
    if not title:
        errs.append(FieldError("title", CODE_BIZ_ERROR, "工单标题不能为空"))
    elif len(title) > TITLE_MAX_LEN:
        errs.append(FieldError("title", CODE_BIZ_ERROR, "工单标题长度需在 1~50 之间"))
    elif "<" in title or ">" in title:
        errs.append(FieldError("title", CODE_BIZ_ERROR, "工单标题含非法字符"))

    # category：必填 + 值域
    if dto.get("category") not in CATEGORIES:
        errs.append(FieldError("category", CODE_BIZ_ERROR,
                               "工单分类不合法，仅支持 HARDWARE/SOFTWARE/NETWORK/ACCOUNT/OTHER"))

    # priority：必填（缺省已在外层回填 MEDIUM）+ 值域
    if dto.get("priority") not in PRIORITIES:
        errs.append(FieldError("priority", CODE_BIZ_ERROR, "优先级不合法，仅支持 HIGH/MEDIUM/LOW"))

    # description：必填 10~500
    desc = dto.get("description") or ""
    if len(desc) < DESC_MIN_LEN:
        errs.append(FieldError("description", CODE_BIZ_ERROR,
                               "请至少填写10个字，说明何时开始、报错原文、已尝试的操作"))
    elif len(desc) > DESC_MAX_LEN:
        errs.append(FieldError("description", CODE_BIZ_ERROR, "问题描述长度需在 10~500 之间"))

    # assetId：选填 + 正则（CMDB 查无 → 40401 由 service 判定）
    asset_id = dto.get("assetId")
    if asset_id and not ASSET_ID_RE.match(asset_id):
        errs.append(FieldError("assetId", CODE_BIZ_ERROR, "资产编号格式不正确"))

    # attachmentUrls：选填 ≤3 且必须为上传返回的 /files/** URL
    urls = dto.get("attachmentUrls") or []
    if len(urls) > ATTACH_MAX_COUNT:
        errs.append(FieldError("attachmentUrls", CODE_BIZ_ERROR, "附件最多上传 3 个"))
    else:
        for u in urls:
            if not ATTACH_URL_RE.match(u):
                errs.append(FieldError("attachmentUrls", CODE_BIZ_ERROR, "附件地址不合法，请先上传附件"))
                break

    # expectedFinishTime：选填 + 必须 ≥ 当前时间
    eft = dto.get("expectedFinishTime")
    if eft:
        try:
            eft_dt = datetime.strptime(eft, TIME_FMT)
            if eft_dt < now:
                errs.append(FieldError("expectedFinishTime", CODE_BIZ_ERROR,
                                       "期望完成时间不能早于当前时间"))
        except ValueError:
            errs.append(FieldError("expectedFinishTime", CODE_BIZ_ERROR,
                                   "期望完成时间格式须为 yyyy-MM-dd HH:mm:ss"))
    return errs
