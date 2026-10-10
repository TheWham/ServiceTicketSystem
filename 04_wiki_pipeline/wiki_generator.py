"""
Layer 2 Wiki 生成器：wiki_generator.py
职责：将清洗后的条目 + LLM 萃取的元数据渲染为企业标准 Markdown Wiki 知识卡片
（YAML Frontmatter + 分节正文 + 溯源引用），并生成总索引 _index.md
"""

import os
from typing import Any, Dict, List, Optional

from clean_pipeline import Entry

DEFAULT_SOURCE_NAME = "IT常见问题RAG知识库.docx"
DEFAULT_DEPARTMENT = "IT 部"
DEFAULT_ID_PREFIX = "ITKB"


def _yaml_scalar(value: Any) -> str:
    if value is None or value == "":
        return "null"
    text = str(value).replace('"', '\\"')
    return f'"{text}"'


def _yaml_str_list(values: List[Any]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(_yaml_scalar(v) for v in values) + "]"


def make_wiki_id(entry: Entry, id_prefix: str) -> str:
    return f"{id_prefix}-{entry.code}"


def render_frontmatter(entry: Entry, meta: Dict[str, Any],
                       id_prefix: str = DEFAULT_ID_PREFIX,
                       department: str = DEFAULT_DEPARTMENT) -> str:
    """【Step 4-a】生成 YAML frontmatter。
    注意：effective_date 为 None 时整行省略——不编造日期是防幻觉约束的一部分。"""
    lines = [
        "---",
        f'id: "{make_wiki_id(entry, id_prefix)}"',
        f"title: {_yaml_scalar(meta.get('title') or entry.title)}",  # LLM 标题缺失时回退原始标题
        f'category: {_yaml_scalar(entry.category)}',
        f'department: "{department}"',
    ]
    if meta.get("effective_date"):
        lines.append(f"effective_date: {_yaml_scalar(meta['effective_date'])}")
    lines.append(f"version: {_yaml_scalar(meta.get('version') or 'v1.0')}")
    lines.append(f"replaces: {_yaml_str_list(meta.get('replaces') or [])}")
    lines.append(f"entities: {_yaml_str_list(meta.get('entities') or [])}")
    lines.append(f"keywords: {_yaml_str_list(entry.keywords)}")
    lines.append(f"summary: {_yaml_scalar(meta.get('summary'))}")
    lines.append(f"meta_source: {_yaml_scalar(meta.get('meta_source') or 'rule')}")
    if meta.get("conflict_note"):  # 版本冲突/废止条款仅在检出时输出
        lines.append(f"conflict_note: {_yaml_scalar(meta['conflict_note'])}")
    lines.append("---")
    return "\n".join(lines)


def render_card(entry: Entry, meta: Dict[str, Any],
                id_prefix: str = DEFAULT_ID_PREFIX,
                source_name: str = DEFAULT_SOURCE_NAME,
                department: str = DEFAULT_DEPARTMENT) -> str:
    parts = [render_frontmatter(entry, meta, id_prefix, department), ""]

    title = meta.get("title") or entry.title
    parts.append(f"# 【{entry.code}】{title}\n" if not entry.is_appendix else f"# {title}\n")

    if meta.get("conflict_note"):
        parts.append(f"> 📌 **版本冲突特别裁决条款**：{meta['conflict_note']}\n")

    # 结构化字段按插入顺序渲染为 ## 分节（dict 保序，Python 3.7+）
    for key, value in entry.fields.items():
        parts.append(f"## {key}\n")
        field_text = str(value)
        if field_text.lstrip().startswith("|"):
            parts.append(field_text)  # 已是 Markdown 表格（如 Excel 数据集卡的统计表），原样输出
        else:
            for ln in field_text.split("\n"):
                ln = ln.strip()
                if ln:
                    # 已是 Markdown 语法的行（表格/标题/列表/引用）原样保留，其余加列表前缀
                    parts.append(f"- {ln}" if not ln.startswith(("|", "#", "-", ">")) else ln)
        parts.append("")

    for para in entry.body_paras:
        parts.append(para + "\n")

    for rows in entry.tables:
        header = [c.replace("\n", " ") for c in rows[0]]
        md = "| " + " | ".join(header) + " |\n"
        md += "| " + " | ".join(["---"] * len(header)) + " |\n"
        for row in rows[1:]:
            md += "| " + " | ".join(c.replace("\n", "<br>") for c in row) + " |\n"
        parts.append(md)

    if entry.remark:
        parts.append(f"> 📝 备注：{entry.remark}\n")

    parts.append("---")
    parts.append(f"> 🔗 溯源：摘自《{source_name}》· 条目 {entry.code} · 分类「{entry.category}」· 由清洗流水线自动生成")
    return "\n".join(parts).strip() + "\n"


def render_index(cards: List[Dict[str, Any]], title: str, source_name: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"> 共 {len(cards)} 张知识卡片 · 来源《{source_name}》· 由清洗 + LLM 治理流水线自动生成",
        "",
    ]
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for c in cards:
        by_category.setdefault(c["category"] or "未分类", []).append(c)

    for category, items in by_category.items():
        lines.append(f"## {category}\n")
        for c in items:
            summary = (c["meta"].get("summary") or "").strip()
            suffix = f" — {summary}" if summary else ""
            lines.append(f"- [{c['entry'].code} {c['meta'].get('title') or c['entry'].title}](./{c['wiki_id']}.md){suffix}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def generate_wiki(entries: List[Entry], metas: Dict[str, Dict[str, Any]], output_dir: str,
                  id_prefix: str = DEFAULT_ID_PREFIX,
                  source_name: str = DEFAULT_SOURCE_NAME,
                  department: str = DEFAULT_DEPARTMENT,
                  index_title: str = "企业 IT 常见问题知识库 · Wiki 索引") -> List[str]:
    """【Step 4】批量渲染 Wiki 卡片 + 总索引，返回全部落盘文件路径。
    每个条目一个 .md 文件（而非单一大文件），因为 RAG 检索的最小命中单元是"块"。"""
    os.makedirs(output_dir, exist_ok=True)
    cards = []
    paths = []
    for e in entries:
        meta = metas[e.code]
        wiki_id = make_wiki_id(e, id_prefix)
        content = render_card(e, meta, id_prefix, source_name, department)
        path = os.path.join(output_dir, f"{wiki_id}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        cards.append({"entry": e, "meta": meta, "category": e.category, "wiki_id": wiki_id})
        paths.append(path)

    index_path = os.path.join(output_dir, "_index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(render_index(cards, index_title, source_name))
    paths.append(index_path)
    return paths
