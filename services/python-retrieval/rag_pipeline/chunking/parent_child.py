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

    ── metadata 的五大作用（汇报口径：page_content 管"像不像"，metadata 管其余一切）──
    ① 资格审定  wiki_status=已废止/已下线 物理屏蔽、wiki_category 类目收窄——
                业务规则向量表达不了（废止卡与现行卡内容几乎一样，相似度再高也不能返回）
    ② 身份注入  Header_1/Header_2 在切块时拼进文本成为面包屑，让 512 字片段
                在向量空间里始终带着"哪张卡 > 哪个环节"的工牌
    ③ 上下文回溯 parent_content 让每个子块随身携带整卡全文：命中任意片段零成本
                展开成完整上下文，无需 Docstore 组件、无需二次查询
    ④ 归拢去重  parent_id/child_id 是判断"几个候选碎片是否同卡"的钥匙——
                RRF 去重键、父块去重、双路共振保护都靠它们
    ⑤ 契约装配  rag_service/mapping.py 从 metadata 抽取对外响应字段：
                child_id→chunkId、Header_1→title、wiki_version→versionId、parent_content→content

    ⚠️ metadata 不参与向量化：embedding 模型只吃 page_content（见 store.py
    embed_documents([d.page_content ...])）；metadata 走结构化旁路随行，
    落库时与向量同主键绑定（chroma.sqlite3 的 embedding_metadata 表），查询时整行带回。
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

        ── 全流程总览（8 步，按代码顺序）──
        步骤1  解析 frontmatter：正文与元数据分家，parent_id 在切块前就确定
        步骤2  构造公共 metadata 底座（wiki_* 全字段，父块子块共享）
        步骤3  产出父块 = 整卡正文全文（不切分，不入向量库）
        步骤4  溯源尾剔除（仅子块：匹配要纯净；父块保留：溯源要完整）
        步骤5  第一级切分：按 H2 语义边界分节 + 前言并入首节
        步骤6  准备上下文头材料：面包屑 + 检索增强行（会拼进 page_content 一起向量化）
        步骤7  第二级切分：节内按行累加到 512 封顶（行级切分永不断句，表格跨块续表头）
        步骤8  _emit：子块诞生即自带全套 metadata 行李（child_id / parent_content …）
        """
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        # ---- 步骤1：frontmatter 解析（正则取两个 --- 之间的 YAML 块，见 structure_aware.parse_wiki_frontmatter）----
        # body = 从 H1 标题开始的正文；parent_id = frontmatter.id（如 ITKB-VPN-001），父块身份证在此确定
        frontmatter_meta, body = WikiStructureAwareChunker.parse_wiki_frontmatter(raw_content)
        wiki_title = frontmatter_meta.get("title", Path(file_path).stem)
        parent_id = frontmatter_meta.get("id", Path(file_path).stem)

        # ---- 步骤2：公共 metadata 底座——切块时一次性拼好，之后随块走完全生命周期 ----
        # ① 每个字段加 wiki_ 前缀：与切块自身字段（child_id 等）划清命名边界，检索时可按前缀一眼区分
        # ② list/dict 序列化成 JSON 字符串：向量库 metadata 只收标量（keywords/entities 是列表）
        # ③ wiki_status 兜底"现行"：旧卡无状态字段时不被 default_exclude 过滤误杀
        base_meta: Dict[str, Any] = {}
        for k, v in frontmatter_meta.items():
            base_meta[f"wiki_{k}"] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)
        base_meta.setdefault("wiki_status", "现行")
        base_meta["source_file"] = os.path.basename(file_path)   # 溯源：检索结果可追到源文件
        base_meta["parent_id"] = parent_id                       # 回溯钥匙：Small-to-Big 靠它去重与展开

        # ---- 步骤3：父块 = 整卡正文全文，一行代码"切完"----
        # 父块不进向量库、不参与匹配，它只活在每个子块的 metadata.parent_content 里（见步骤8）；
        # 交给 LLM 的永远是它——所以正文完整性比什么都重要，一刀不切。
        parent_meta = dict(base_meta)
        parent_meta["Header_1"] = wiki_title
        parent_meta["Header_2"] = wiki_title
        parent_meta["chunk_role"] = "parent"
        parent_meta["split_strategy"] = "Parent-Child (父块=整卡全文)"
        parent_doc = Document(page_content=body, metadata=parent_meta)

        # ---- 步骤4：溯源尾剔除（不对称设计）----
        # 文末"> 🔗 溯源：…"是清洗模板的尾巴，对向量匹配是纯噪声 → 子块剔除；
        # 父块保留它 → 追溯知识来源时信息完整。
        child_src = (re.sub(r"\n-{3,}\s*\n>\s*🔗\s*溯源：[^\n]*\s*$", "", body)
                     if self.cfg.strip_trace_tail else body)

        # ---- 步骤5（第一级切分）：按 H2 语义边界分节 ----
        # 先在标题处切开，保证子块边界天然落在话题转换处；节内怎么切是步骤7的事。
        sec_marker = "#" * self.cfg.section_header_level + " "
        sections: List[Tuple[str, List[str]]] = []   # (小节标题, 小节内行列表)
        cur_h2 = ""
        cur_lines: List[str] = []
        for ln in child_src.splitlines(keepends=True):
            if ln.startswith(sec_marker):
                sections.append((cur_h2, cur_lines))   # 遇到新 H2：当前节收工
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

        # ---- 步骤6：准备两样"上下文头"——注意它们会拼进 page_content 一起向量化 ----
        # （metadata 不参与向量化；想喂给向量模型的信息必须写进文本，这两样就是为此存在）
        # ① 检索增强行：把 frontmatter 的规范化术语直接送进向量空间，补口语 query 与书面正文的语义鸿沟
        kw_txt = "、".join(frontmatter_meta.get("keywords") or [])
        # entities 单一形态 {name, type}：拼入检索增强行取 name，无 isinstance 兼容分支
        ent_txt = "、".join(e["name"] for e in (frontmatter_meta.get("entities") or []))
        boost = f"【检索增强：关键词 {kw_txt}｜实体 {ent_txt}】\n" if (kw_txt or ent_txt) else ""
        if self.cfg.boost_injection == "none":
            boost = ""

        # ---- 步骤8：_emit——子块在此诞生，metadata 全套行李就地拼好 ----
        # 切块 = 同时产出"文本 + metadata"这对组合，此后二者同主键绑死：
        #   入库时同行写入 chroma.sqlite3 → 查询时按向量选出 id、按 id 整行带回 →
        #   parent_content 随检索结果"搭车"回到内存，回溯无需再查任何库。
        child_docs: List[Document] = []
        idx = 0

        def _emit(text: str, h2_label: str = ""):
            nonlocal idx
            md = dict(base_meta)                       # 继承 wiki_* 公共字段（资格审定/溯源用）
            md["Header_1"] = wiki_title                # 卡片标题：装配期映射为响应 title
            md["Header_2"] = h2_label or wiki_title    # 所在小节：面包屑原料 + 排错定位
            md["chunk_role"] = "child"
            md["child_idx"] = idx                      # 块序号：调试/排序
            md["child_id"] = f"{parent_id}#c{idx}"     # 全局唯一切片ID：RRF去重键/契约chunkId/黄金集归因
            md["chunk_length"] = len(text)
            md["split_strategy"] = f"Parent-Child (子块={self.child_size}字符 H{self.cfg.section_header_level}边界行累加+差异化上下文头)"
            # 企业级改造：父块正文解耦存入 MySQL Docstore，子块 metadata 不再冗余写入 parent_content
            child_docs.append(Document(page_content=text, metadata=md))
            idx += 1

        # 差异化注入（boost_injection=first）：完整检索增强行只挂每卡第一个子块——
        # 若挂到每个子块，关键词会稀释局部步骤的向量特征（实测强匹配 query 相似度 0.639→0.588）。
        def _with_boost() -> bool:
            if self.cfg.boost_injection == "all":
                return True
            return idx == 0  # first：仅每卡首块

        # ---- 步骤7（第二级切分）：节内按行累加到 child_size 封顶——核心循环 ----
        # 三个机制：
        # ① 行级累加：以"行"为最小单元、预算满了才切 → 永不切断一行字，句子完整性天然保住
        # ② 巨块兜底：单行超预算时 _split_long_line 按句末标点（。！？；）温和再切
        # ③ 表格续头：切分点落在表格数据行时，新子块自动带上表头两行——
        #    否则"半截表格"丢列含义，向量语义残废
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


def expand_to_parents(items, docstore: Optional[Any] = None) -> List[Document]:
    """Small-to-Big 回溯：把检索命中的子块展开为去重后的父块全文。

    企业级标准设计：
    - 父块正文由 Docstore（如 MySQL）托管，命中子块后按 parent_id 批量回溯；
    - 兼容本地 metadata.parent_content（若旧对象带有），无二次 IO；
    - 若 docstore 与 metadata 均无父块正文，降级保留原子块文本。

    items 可以是 Document 列表或 dict 列表（含 metadata / page_content|content）。
    返回 Document 列表，page_content 为"最终交给下游的上下文"。
    """
    seen = set()
    out: List[Document] = []

    # 预先收集需要从 Docstore 查询的 parent_id
    pids_to_fetch = []
    if docstore is not None:
        for it in items:
            md = it.metadata if isinstance(it, Document) else it.get("metadata", {})
            if not md.get("parent_content"):
                pid = md.get("parent_id") or md.get("wiki_id")
                if pid and pid not in pids_to_fetch:
                    pids_to_fetch.append(pid)

    docstore_parents = docstore.mget(pids_to_fetch) if (docstore is not None and pids_to_fetch) else {}

    for it in items:
        if isinstance(it, Document):
            md, txt = it.metadata, it.page_content
        else:
            md, txt = it.get("metadata", {}), it.get("content", it.get("page_content", ""))
        pid = md.get("parent_id") or md.get("wiki_id")
        pc = md.get("parent_content") or (docstore_parents.get(pid) if pid else None)
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
