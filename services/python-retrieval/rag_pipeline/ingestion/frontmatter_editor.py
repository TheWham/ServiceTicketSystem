# -*- coding: utf-8 -*-
"""frontmatter 就地增补器(Wiki 图知识库 阶段一 Task 2)。

职责:只管 wiki 卡片文件的读写——frontmatter 增补/迁移的产物由上游 runner 组装,
本模块不感知 schema 语义、不做任何业务校验(那是 graph_schema 与 runner 的事)。

- load_card / write_card:读三明治格式 ``---\n{fm}\n---\n{body}``;
  write 为原子写(同目录临时文件 + os.replace),正文原样字符串,
  在 load→write→load 往返中逐字节相等(Review Focus 2);
  原文件换行约定(CRLF/LF)读原文探测后原样保留,不做换行转换。
- render_frontmatter_block: 确定性 YAML——按 meta 的键插入顺序渲染
  (Python dict 保序,via yaml.safe_load 读入的卡天然保留文档序),
  新键由调用方追加在 dict 尾部即渲染在尾部;
- render_obj_list: 对象列表块式序列化(Ruling 6,公开导出,Task 5 复用),
  固定四键定序 target/type/note/evidence,实体 name/type,图节点 kind/name;
- migrate_replaces: 纯函数,frontmatter 的 replaces 扁平字段迁移为
  relations 条目;replaces 字段保留不删(清洗流水线 REQUIRED_FIELDS 的一部分,
  graph 只读镜像)。
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from .wiki_generator import _yaml_scalar, _yaml_str_list

MIGRATION_NOTE = "frontmatter replaces 规则迁移"
MIGRATION_EVIDENCE = "frontmatter:replaces"

# 对象列表条目的固定键序(brief 逐字:target/type/note/evidence 或 name/type;
# graph_nodes 条目 {kind, name} 为块式渲染经由 render_obj_list 时的自然补全)
_OBJ_KEY_ORDERS: Tuple[Tuple[str, ...], ...] = (
    ("target", "type", "note", "evidence"),
    ("name", "type"),
    ("kind", "name"),
)


def _ordered_item_keys(item: Dict[str, Any]) -> List[str]:
    """对象条目的确定性键序:已知键按固定顺序,未知键保持插入顺序垫后。"""
    for order in _OBJ_KEY_ORDERS:
        if all(key in item for key in order):
            ordered = [k for k in order if k in item]
            return ordered + [k for k in item if k not in ordered]
    return list(item.keys())


def render_obj_list(items: List[Dict[str, Any]]) -> str:
    """对象列表 → 块式 YAML 条目串(不含键行本身)。

    每条形如 ``- target: "…"\n  type: "…"``,键序见 _OBJ_KEY_ORDERS;
    与 `wiki_generator._yaml_scalar` 同一套标量转义,渲染结果可被
    `yaml.safe_load` 无损往返。
    """
    lines: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"render_obj_list: 期望对象条目, 实得 {type(item).__name__}")
        for i, key in enumerate(_ordered_item_keys(item)):
            prefix = "- " if i == 0 else "  "
            lines.append(f"{prefix}{key}: {_yaml_scalar(item[key])}")
    return "\n".join(lines)


def render_frontmatter_block(meta: Dict[str, Any]) -> str:
    """meta → frontmatter YAML 文本(不含首尾 ``---`` 行)。

    标量 / 字符串列表复用 wiki_generator 的转义;对象列表走块式
    render_obj_list,勿在别处复制第二份实现(Ruling 6)。
    """
    lines: List[str] = []
    for key, value in meta.items():
        if isinstance(value, list) and value:
            if all(isinstance(i, dict) for i in value):
                lines.append(f"{key}:")
                lines.append(render_obj_list(value))
            elif any(isinstance(i, dict) for i in value):
                # 混合类型列表(str 与 dict 混杂):显式拒绝,
                # 不得 str(dict) 静默塞入字符串列表(裁决 9)
                raise ValueError(f"{key}: 列表混入对象条目, 拒绝混合类型列表")
            else:
                lines.append(f"{key}: {_yaml_str_list(value)}")
        elif isinstance(value, list):
            lines.append(f"{key}: {_yaml_str_list(value)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    return "\n".join(lines)


def load_card(path: Path) -> Tuple[Dict[str, Any], str]:
    """读卡:返回 (frontmatter dict, 正文原样字符串)。

    frontmatter 分隔沿用 `tools/sync_wiki_to_rag_service.py:50 parse_frontmatter`
    的 split 语义,但正文必须能被 write_card 原样写回——split 第二段开头的
    单个换行是分隔符的一部分,不属于正文,剥掉它才能让
    ``load(write(fm, body))[1] == body`` 在多轮编辑下幂等。
    解析失败显式 ValueError:不静默回退成"空 frontmatter"。
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path}: 缺少 frontmatter 分隔符 '---', 不是 wiki 卡片")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{path}: frontmatter 块未以 '---' 闭合")
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: frontmatter YAML 解析失败: {exc}") from exc
    if not isinstance(meta, dict):
        raise ValueError(f"{path}: frontmatter 期望键值映射, 实得 {type(meta).__name__}")
    body = parts[2]
    if body.startswith("\n"):
        body = body[1:]  # 恰好剥掉 write_card 写入的分隔换行,见 docstring
    return meta, body


def write_card(path: Path, meta: Dict[str, Any], body: str) -> None:
    """原子写卡:同目录临时文件 + os.replace,统一 ``---\\n{fm}\\n---\\n{body}``。

    换行约定读原文字节探测(load_card 经 read_text 通用换行翻译会把
    CRLF 归一成 LF,写回时按原约定还原),故多次就地编辑不会把存量
    CRLF 卡整体翻译成 LF;新文件默认 LF。
    任一步骤抛错时清理临时文件后原样 re-raise,不残留 .tmp。
    """
    fm = render_frontmatter_block(meta)
    text = f"---\n{fm}\n---\n{body}"
    newline = "\n"
    if path.exists():
        with open(path, "rb") as fh:
            head = fh.read(8192)
        if b"\r\n" in head:
            newline = "\r\n"
    if newline == "\r\n":
        text = text.replace("\n", "\r\n")
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)  # 写失败清理临时文件不留 .tmp,原样 re-raise(裁决 9)
        raise


def migrate_replaces(meta: Dict[str, Any]) -> Dict[str, Any]:
    """纯函数:replaces 非空者 → 追加 relations 迁移条目;replaces 原值保留不删。

    返回新 dict(键序 = 原键序,relations 不存在时追加在尾),入参不被改动;
    note 为固定迁移注记,evidence 指回 frontmatter 字段本身,
    让图知道这条关系的出处是文档头而非人工编写或 LLM 萃取。
    replaces 非列表(如单个字符串)时显式 ValueError,不做静默容错。
    """
    replaces = meta.get("replaces")
    if not replaces:  # 缺失或空列表:无迁移条目
        return dict(meta)
    if not isinstance(replaces, list):
        # 非列表(如单个字符串)显式拒绝,不做静默单元素列表容错(AGENTS:明确失败)
        raise ValueError(f"replaces 必须是列表: {type(replaces).__name__}")
    relations = [
        dict(item) if isinstance(item, dict) else item
        for item in (meta.get("relations") or [])
    ]
    for target in replaces:
        relations.append(
            {
                "target": target,
                "type": "replaces",
                "note": MIGRATION_NOTE,
                "evidence": MIGRATION_EVIDENCE,
            }
        )
    out = dict(meta)
    out["relations"] = relations
    return out
