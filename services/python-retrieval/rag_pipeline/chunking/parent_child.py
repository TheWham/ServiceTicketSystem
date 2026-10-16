"""父子切片（Small-to-Big）引擎：子块做匹配、父块做上下文。"""

import os
import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

try:
    from langchain_core.documents import Document
except ImportError:
    @dataclass
    class Document:  # type: ignore
        page_content: str
        metadata: Dict[str, Any] = field(default_factory=dict)

from ..config import ChunkingConfig
from .structure_aware import WikiStructureAwareChunker


class ParentChildChunker:
    """
    父子切片（Small-to-Big）引擎——企业知识库的标准检索架构：
    - 父块 (Parent)：整张 Wiki 卡片全文，自包含语义单元，作为"最终交给 LLM 的上下文"
    - 子块 (Child) ：按行累加到 child_size(默认512字符) 的细粒度切片，作为"向量匹配单元"
    - 每个子块 metadata 携带 parent_id + parent_content(父块全文) + Header_1/Header_2 + 全部 wiki_* 元数据

    检索流程（Small-to-Big）：
      embedding 只打在子块上（文本小、语义聚焦、匹配精确）
      -> 命中子块后通过 parent_id / parent_content 回溯父块全文
      -> 把父块全文交给下游（LLM / 评测），保证上下文完整
    """

    def __init__(self, child_size: int = 512, config: Optional[ChunkingConfig] = None):
        # config 优先（YAML 配置中心）；child_size 单参数保留向后兼容旧调用
        self.cfg = config or ChunkingConfig(child_size=child_size)
        self.child_size = self.cfg.child_size

    @staticmethod
    def _split_long_line(line: str, budget: int) -> List[str]:
        """当单行文本超预算时，按句末标点（。！？；）温和切分，防止单行巨块突破 child_size。"""
        if len(line) <= budget:
            return [line]
        parts = re.split(r"(?<=[。！？；])", line)
        out: List[str] = []
        cur = ""
        for p in parts:
            if not p:
                continue
            if cur and len(cur) + len(p) > budget:
                out.append(cur)
                cur = p
            else:
                cur += p
        if cur:
            out.append(cur)
        return out if out else [line]

    def split_wiki_document(self, file_path: str) -> Tuple[Document, List[Document]]:
        """切分单个 Wiki 卡片，返回 (父块, [子块列表])。

        父块：剥离 frontmatter 后的正文全文。
        子块：正文按 H2 分节后按行累加，累计到 child_size 即切下一块（超长单行按句微切，跨块表格自动续接表头）。
        """
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        frontmatter_meta, body = WikiStructureAwareChunker.parse_wiki_frontmatter(raw_content)
        wiki_title = frontmatter_meta.get("title", Path(file_path).stem)
        parent_id = frontmatter_meta.get("id", Path(file_path).stem)

        # ---- 公共元数据：wiki_* 全字段（子块与父块都带，支持元数据过滤）----
        base_meta: Dict[str, Any] = {}
        for k, v in frontmatter_meta.items():
            base_meta[f"wiki_{k}"] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)
        base_meta.setdefault("wiki_status", "现行")
        base_meta["source_file"] = os.path.basename(file_path)
        base_meta["parent_id"] = parent_id

        # ---- 父块：整卡全文 ----
        parent_meta = dict(base_meta)
        parent_meta["Header_1"] = wiki_title
        parent_meta["Header_2"] = wiki_title
        parent_meta["chunk_role"] = "parent"
        parent_meta["split_strategy"] = "Parent-Child (父块=整卡全文)"
        parent_doc = Document(page_content=body, metadata=parent_meta)

        # ---- 溯源尾剔除：文末"--- + > 🔗 溯源：…"是模板信息，非检索对象 ----
        child_src = (re.sub(r"\n-{3,}\s*\n>\s*🔗\s*溯源：[^\n]*\s*$", "", body)
                     if self.cfg.strip_trace_tail else body)

        # ---- 子块：先按语义边界标题分节，节内再按行累加到 child_size ----
        sec_marker = "#" * self.cfg.section_header_level + " "
        sections: List[Tuple[str, List[str]]] = []   # (小节标题, 小节内行列表)
        cur_h2 = ""
        cur_lines: List[str] = []
        for ln in child_src.splitlines(keepends=True):
            if ln.startswith(sec_marker):
                sections.append((cur_h2, cur_lines))
                cur_h2 = ln.strip().lstrip("#").strip()
                cur_lines = [ln]
            else:
                cur_lines.append(ln)
        sections.append((cur_h2, cur_lines))

        # 前言节（H1 标题+导语，即旧版过薄的 c0）并入第一个真实小节：
        # 前言仅百余字符、不承载排查步骤，独立成块浪费一个检索位；
        # 无边界标题的附录卡（sections 只有前言节）保持独立成块兜底。
        if self.cfg.merge_preamble and len(sections) > 1 and not sections[0][0]:
            preamble_lines = sections[0][1]
            sections = [(sections[1][0], preamble_lines + sections[1][1])] + sections[2:]

        # ---- 上下文头：把卡片身份与 04 萃取的检索增强词注入子块 ----
        kw_txt = "、".join(frontmatter_meta.get("keywords") or [])
        ent_txt = "、".join(frontmatter_meta.get("entities") or [])
        boost = f"【检索增强：关键词 {kw_txt}｜实体 {ent_txt}】\n" if (kw_txt or ent_txt) else ""
        if self.cfg.boost_injection == "none":
            boost = ""

        child_docs: List[Document] = []
        idx = 0

        def _emit(text: str, h2_label: str = ""):
            nonlocal idx
            md = dict(base_meta)
            md["Header_1"] = wiki_title
            md["Header_2"] = h2_label or wiki_title
            md["chunk_role"] = "child"
            md["child_idx"] = idx
            md["child_id"] = f"{parent_id}#c{idx}"
            md["chunk_length"] = len(text)
            md["split_strategy"] = f"Parent-Child (子块={self.child_size}字符 H{self.cfg.section_header_level}边界行累加+差异化上下文头)"
            md["parent_content"] = body
            child_docs.append(Document(page_content=text, metadata=md))
            idx += 1

        # 差异化注入（boost_injection=first）：完整检索增强行只挂每卡第一个子块——
        # 若挂到每个子块，关键词会稀释局部步骤的向量特征（实测强匹配 query 相似度 0.639→0.588）。
        def _with_boost() -> bool:
            if self.cfg.boost_injection == "all":
                return True
            return idx == 0  # first：仅每卡首块

        for h2, sec_lines in sections:
            if not sec_lines:
                continue
            header = ""
            if self.cfg.breadcrumb_header:
                header = f"【卡片：{wiki_title} > {h2}】\n" if h2 else f"【卡片：{wiki_title}】\n"
            cur: List[str] = []
            cur_len = 0
            # 检测小节内是否包含 Markdown 表格表头（| col | + | --- |），跨块切分时为后续块自动补齐表头
            table_header_pair: List[str] = []
            for raw_ln in sec_lines:
                s_ln = raw_ln.strip()
                if s_ln.startswith("|") and s_ln.endswith("|"):
                    if not table_header_pair:
                        table_header_pair = [raw_ln if raw_ln.endswith("\n") else raw_ln + "\n"]
                    elif len(table_header_pair) == 1 and re.match(r"^\|\s*[-:]+\s*\|", s_ln):
                        table_header_pair.append(raw_ln if raw_ln.endswith("\n") else raw_ln + "\n")
                elif len(table_header_pair) < 2:
                    table_header_pair = []

                hdr = header + (boost if _with_boost() else "")
                budget = max(self.child_size - len(hdr), 64)
                for ln in self._split_long_line(raw_ln, budget):
                    hdr = header + (boost if _with_boost() else "")
                    budget = max(self.child_size - len(hdr), 64)
                    if cur and cur_len + len(ln) > budget:
                        _emit(hdr + "".join(cur), h2)
                        # 若当前正在切分 Markdown 表格数据行，为新起的子块自动续上表头
                        if len(table_header_pair) == 2 and ln.strip().startswith("|") and ln not in table_header_pair:
                            cur = list(table_header_pair) + [ln]
                            cur_len = sum(len(x) for x in cur)
                        else:
                            cur = [ln]
                            cur_len = len(ln)
                    else:
                        cur.append(ln)
                        cur_len += len(ln)
            if cur:
                _emit(header + (boost if _with_boost() else "") + "".join(cur), h2)

        return parent_doc, child_docs


def expand_to_parents(items) -> List[Document]:
    """Small-to-Big 回溯：把检索命中的子块展开为去重后的父块全文。

    items 可以是 Document 列表或 dict 列表（含 metadata / page_content|content）。
    - 若带 parent_content（子块）：取其父块全文，按 parent_id 去重；
    - 若不带（已是父块/朴素块）：原样保留，按内容去重。
    返回 Document 列表，page_content 为"最终交给下游的上下文"。
    """
    seen = set()
    out: List[Document] = []
    for it in items:
        if isinstance(it, Document):
            md, txt = it.metadata, it.page_content
        else:
            md, txt = it.get("metadata", {}), it.get("content", it.get("page_content", ""))
        pc = md.get("parent_content")
        pid = md.get("parent_id") or md.get("wiki_id")
        if pc is not None:
            key = pid or pc[:60]
            if key in seen:
                continue
            seen.add(key)
            out.append(Document(page_content=pc, metadata=md))
        else:
            key = pid or txt[:60]
            if key in seen:
                continue
            seen.add(key)
            out.append(Document(page_content=txt, metadata=md))
    return out
