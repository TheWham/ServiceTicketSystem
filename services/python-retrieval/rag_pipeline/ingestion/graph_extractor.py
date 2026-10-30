# -*- coding: utf-8 -*-
"""LLM 两步图萃取器(Wiki 图知识库 阶段一 Task 3)。

与 llm_synthesizer.py 同风格的语料级图萃取 pass,分两步:

1. normalize_entities(实体归一):给定卡片现有扁平实体与正文,LLM 从全局词表
   (glossary,含别名)或正文证据中选名定 type;词表与正文都没有的名称一律拒
   (确定性守卫兜住 LLM 输出,不依赖模型自觉);确有新实体时随 new_entities
   副产物返回(new ⊆ normalized 且均为词表未收录者),由 runner 交 graph_builder
   合并进词表;
2. extract_relations_and_nodes(关系萃取):单卡对全语料摘要列表抽卡间关系
   (relations)与卡内结构节点(graph_nodes)。

工程保障(复刻 LlmSynthesizer 语义):严格 JSON 输出、代码围栏剥离(直调
LlmSynthesizer._parse_json_loose,不复制实现)、数量守卫截断(实体 15/卡、
关系 8/卡、节点 10/卡,超限截断并记日志)、两次尝试、磁盘缓存
(键 graph_{step}_{sha1(user_prompt)}, step ∈ ent/rel)、规则兜底(实体兜底 =
原扁平名全标 "概念";relations 兜底 = 空列表——replaces 规则迁移条目由 runner
叠加,不在此产生;graph_nodes 兜底 = 空列表)。兜底结果不写缓存,避免把降级
产物固化到磁盘,网络恢复后重跑批次可重新萃取。

provenance(meta_source 语义):每次调用后 self.last_used_llm 标记本步结果是否
来自 LLM(成功或缓存命中为 True,规则兜底为 False)。返回值类型由计划固定为
二元组,无法内嵌第三元素,故以实例属性承载——runner 读取该属性映射
meta_source 的 llm/rule 取值(见 task-3-report.md 偏差段)。

本模块不写 wiki 卡片文件(那是 frontmatter_editor 与阶段一 runner 的职责)。
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from .graph_schema import (
    ENTITY_TYPES,
    NODE_KINDS,
    RELATION_TYPES,
    EntityDef,
    GraphNodeDef,
    RelationDef,
    validate_entities,
    validate_graph_nodes,
    validate_relations,
)
from .llm_synthesizer import LlmSynthesizer

logger = logging.getLogger(__name__)

# 守卫阈值(超限截断并记日志)
MAX_ENTITIES_PER_CARD = 15
MAX_RELATIONS_PER_CARD = 8
MAX_GRAPH_NODES_PER_CARD = 10

# ent 步用户提示词里的正文长度上限(正文归一只需证据片段,不送全文省 token)
ENT_PROMPT_BODY_LIMIT = 4000


ENTITY_SYSTEM_PROMPT = """你是企业知识图谱治理专家。给定一张 Wiki 卡片的现有扁平实体、全局实体词表(glossary)与正文,执行实体规范化与类型判定。

处理规则:
1. 词表已有(含别名映射)的实体:输出必须使用词表标准名,type 沿用词表;
2. 词表没有的实体:仅当其名称逐字出现在正文中时才保留,并从合法类型清单判定 type;
3. 其中词表尚未收录、但正文确有证据的新实体,同时在 new_entities 中列出(供后续批次合并进词表);
4. 严禁编造词表与正文中都不存在的名称,禁止引入外部知识;
5. 每卡实体总数不超过 15,超出时优先保留信息量大的,其余省略。

严格输出一个 JSON 对象(不要输出任何其他文字,不要用代码围栏),字段如下:
{
  "entities": [{"name": "规范化实体名", "type": "类型"}],
  "new_entities": [{"name": "词表未收录的新实体名", "type": "类型"}]
}

铁律:
1. name 只能取自词表标准名/别名,或正文中逐字出现的短语;
2. type 只能是以下之一:设备/协议/软件/系统/故障现象/命令工具/账号权限/配置项/概念;
3. 输出必须是可被 json.loads 解析的合法 JSON。"""


RELATION_SYSTEM_PROMPT = """你是企业知识图谱治理专家。给定一张 Wiki 卡片的摘要要点与全语料卡片摘要清单,抽取两部分图结构:

一、卡间关系 relations:本卡与清单中其他卡片之间的语义关系;
   type ∈ replaces(本卡替代/废止目标卡)/same_root_cause(同一根因的相关卡)/related(弱相关)/process_applies(某流程规范同时适用于两张卡);
二、卡内结构节点 graph_nodes:本卡内部的故障现象、根因与涉及工具,name 用卡片原文短语;
   kind ∈ symptom(故障现象)/root_cause(根因)/tool(工具或命令)。

铁律:
1. 关系必须给原文短句证据,给不出输出 null;target 只能是提供的合法编码清单内的值;
2. graph_nodes 的 name 必须取自本卡原文,严禁编造;
3. 抽不出就输出空数组,不得凑数;
4. 每卡关系不超过 8 条、节点不超过 10 个;
5. 输出必须是可被 json.loads 解析的合法 JSON。

严格输出一个 JSON 对象(不要输出任何其他文字,不要用代码围栏),字段如下:
{
  "relations": [{"target": "对方卡片编码", "type": "关系类型", "note": "一句话说明", "evidence": "原文短句证据或 null"}],
  "graph_nodes": [{"kind": "symptom或root_cause或tool", "name": "原文短语"}]
}"""


@dataclass
class CardDigest:
    """单卡摘要(rel 步的萃取输入粒度)。

    body_headline = 正文前 ~1500 字,由阶段一 runner 切片;relations 萃取只需
    摘要要点级信息,不送全文。
    """

    wiki_id: str
    title: str
    summary: str
    entities: List[str]
    keywords: List[str]
    body_headline: str


class GraphExtractor:
    def __init__(self, cfg: Dict[str, str], cache_dir: Optional[str] = None):
        if not cfg.get("base_url"):
            raise ValueError(
                "未配置 LLM_BASE_URL：请设置环境变量或在 .env 中填写 base_url"
            )
        if OpenAI is None:
            raise RuntimeError("缺少 openai 依赖包，请执行 pip install openai 或使用 --offline 模式")
        self.client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
        self.model = cfg["chat_model"]
        self.cache_dir = cache_dir
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        self.last_used_llm = False

    # ---------- 缓存(键 graph_{step}_{sha1(user_prompt)}) ----------

    def _cache_path(self, step: str, user_prompt: str) -> Optional[str]:
        if not self.cache_dir:
            return None
        digest = hashlib.sha1(user_prompt.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"graph_{step}_{digest}.json")

    def _read_cache(self, step: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        path = self._cache_path(step, user_prompt)
        if path and os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError) as err:
                logger.warning("缓存文件损坏, 丢弃重新萃取: %s (%s)", path, err)
        return None

    def _write_cache(self, step: str, user_prompt: str, data: Dict[str, Any]) -> None:
        path = self._cache_path(step, user_prompt)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    # ---------- 通用调用(复刻 llm_synthesizer.py:164 语义) ----------

    def _chat_json(self, model: str, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """本模块的 LLM 调用接缝:断网测试在此覆写注入替身(Python 试同样可注入桩 client)。"""
        resp = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # 与 LlmSynthesizer._chat_json 同理:服务端只允许 temperature=1,传其他值会 400,故不传
        )
        return LlmSynthesizer._parse_json_loose(resp.choices[0].message.content or "")

    def _llm_result_or_none(self, step: str, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """单步固定模式:查缓存 -> LLM 调用(失败重试 1 次)-> 返回原始 dict 或 None(触发兜底)。

        成功(含缓存命中)后 self.last_used_llm = True;两次尝试均失败置 False 并返回 None。
        成功结果写缓存;兜底不写(降级产物不得固化到磁盘)。
        """
        cached = self._read_cache(step, user_prompt)
        if cached is not None:
            self.last_used_llm = True
            return cached

        last_err: Optional[Exception] = None
        for _attempt in range(2):  # 首次 + 1 次重试
            try:
                data = self._chat_json(self.model, system_prompt, user_prompt)
                if not isinstance(data, dict):
                    raise TypeError(f"graph_{step}: 期望 JSON 对象, 实得 {type(data).__name__}")
                self._write_cache(step, user_prompt, data)
                self.last_used_llm = True
                return data
            except Exception as err:  # 网络错误 / 非法 JSON / 非对象载荷统一重试
                last_err = err

        self.last_used_llm = False
        logger.warning("graph_%s: 两次 LLM 调用均失败, 走规则兜底: %s", step, last_err)
        return None

    # ---------- 第一步:实体归一 ----------

    def normalize_entities(
        self,
        wiki_id: str,
        entities: List[str],
        body: str,
        glossary: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[EntityDef], List[EntityDef]]:
        """glossary 归一:返回 (已归一, 新增),new_entities ⊆ 已归一 且均为词表未收录者。

        守卫:LLM 输出的每个候选名必须命中词表(标准名/别名,别名归一为标准名+词表类型)
        或逐字出现在正文中,否则丢弃并记日志;type 非法降级 "概念"。LLM 归一后零产出
        但原有扁平实体非空,视为异常,同样走规则兜底(卡片不得因本 pass 退化)。
        兜底 = 原扁平名全标 "概念"。
        """
        flat = [e.strip() for e in (entities or []) if isinstance(e, str) and e.strip()]
        body = body or ""
        index = self._glossary_index(glossary)

        raw = self._llm_result_or_none("ent", ENTITY_SYSTEM_PROMPT,
                                       self._ent_prompt(wiki_id, flat, body, glossary))
        if raw is None:
            return self._fallback_entities(flat)

        candidates: List[Any] = []
        if isinstance(raw.get("entities"), list):
            candidates.extend(raw["entities"])
        if isinstance(raw.get("new_entities"), list):
            candidates.extend(raw["new_entities"])

        guarded = self._guard_entity_candidates(candidates, wiki_id, body, index)
        if len(guarded) > MAX_ENTITIES_PER_CARD:
            logger.warning("graph_ent: 卡 %s 实体数 %d 超上限 %d, 截断",
                           wiki_id, len(guarded), MAX_ENTITIES_PER_CARD)
            guarded = guarded[:MAX_ENTITIES_PER_CARD]

        if not guarded and flat:
            # LLM 有响应但零有效实体:防卡片退化,回退原扁平实体
            logger.warning("graph_ent: 卡 %s LLM 归一零产出, 回退扁平实体兜底", wiki_id)
            return self._fallback_entities(flat)

        try:
            normalized = validate_entities([{"name": e.name, "type": e.type} for e in guarded])
        except ValueError as err:  # 理论上守卫后不会触发,防御性兜底
            logger.warning("graph_ent: 卡 %s 校验失败, 回退兜底: %s", wiki_id, err)
            return self._fallback_entities(flat)

        canonical_names = {v[0] for v in index.values()}
        new_entities = [e for e in normalized if e.name not in canonical_names]
        return (normalized, new_entities)

    @staticmethod
    def _fallback_entities(flat: List[str]) -> Tuple[List[EntityDef], List[EntityDef]]:
        """实体规则兜底:原扁平名全标 "概念",新增为空。"""
        return ([EntityDef(name=n, type="概念") for n in flat], [])

    @staticmethod
    def _glossary_index(glossary: Optional[Dict[str, Any]]) -> Dict[str, Tuple[str, str]]:
        """词表拍平为 查询名 -> (标准名, 类型) 索引(标准名与别名都可作为键)。"""
        index: Dict[str, Tuple[str, str]] = {}
        entries = (glossary or {}).get("entities")
        if not isinstance(entries, dict):
            return index
        for name, info in entries.items():
            if not isinstance(name, str) or not name.strip():
                continue
            std = name.strip()
            type_ = info.get("type") if isinstance(info, dict) else None
            if type_ not in ENTITY_TYPES:
                type_ = "概念"
            index[std] = (std, type_)
            aliases = info.get("aliases") if isinstance(info, dict) else None
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str) and alias.strip():
                        index.setdefault(alias.strip(), (std, type_))
        return index

    @staticmethod
    def _guard_entity_candidates(
        candidates: List[Any], wiki_id: str, body: str, index: Dict[str, Tuple[str, str]]
    ) -> List[EntityDef]:
        """防幻觉确定性守卫:名字必须来自词表(或别名)或正文,否则拒。保持首次出现顺序去重。"""
        kept: Dict[str, EntityDef] = {}
        for i, item in enumerate(candidates):
            if not isinstance(item, dict):
                logger.warning("graph_ent: 卡 %s entities[%d] 非对象, 丢弃: %r", wiki_id, i, item)
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                logger.warning("graph_ent: 卡 %s entities[%d].name 空, 丢弃", wiki_id, i)
                continue
            name = name.strip()
            if name in index:
                std, type_ = index[name]
                kept.setdefault(std, EntityDef(name=std, type=type_))
            elif name in body:
                type_ = item.get("type")
                if type_ not in ENTITY_TYPES:
                    logger.warning("graph_ent: 卡 %s 实体 %r type 非法 %r, 降级为 概念",
                                   wiki_id, name, type_)
                    type_ = "概念"
                kept.setdefault(name, EntityDef(name=name, type=type_))
            else:
                logger.warning("graph_ent: 卡 %s 实体 %r 不在词表且正文无证据, 拒", wiki_id, name)
        return list(kept.values())

    def _ent_prompt(self, wiki_id: str, flat: List[str], body: str,
                    glossary: Optional[Dict[str, Any]]) -> str:
        entries = {}
        if isinstance(glossary, dict):
            maybe = glossary.get("entities")
            if isinstance(maybe, dict):
                entries = maybe
        if entries:
            lines = []
            for name, info in entries.items():
                if isinstance(info, dict):
                    aliases = ", ".join(a for a in info.get("aliases") or []
                                       if isinstance(a, str) and a.strip())
                    suffix = f" [别名: {aliases}]" if aliases else ""
                    lines.append(f"- {name} ({info.get('type', '概念')}){suffix}")
                else:
                    lines.append(f"- {name} (概念)")
            glossary_block = "\n".join(lines)
        else:
            glossary_block = "(词表为空, 本批为首跑建词表, 全部正文出现的实体均视作新实体)"
        body_block = body[:ENT_PROMPT_BODY_LIMIT]
        return "\n\n".join([
            f"卡片编码：{wiki_id}",
            "全局实体词表(标准名 (类型) [别名: ...]):\n" + glossary_block,
            "现有扁平实体：" + ("、".join(flat) if flat else "(无)"),
            "正文：\n" + body_block,
        ])

    # ---------- 第二步:关系萃取 ----------

    def extract_relations_and_nodes(
        self,
        digest: CardDigest,
        corpus_digests: Optional[List[CardDigest]] = None,
    ) -> Tuple[List[RelationDef], List[GraphNodeDef]]:
        """单卡对全语料摘要列表抽卡间关系与卡内结构节点,返回 (relations, graph_nodes)。

        corpus_digests 缺省时退化为只含本卡(无卡间关系可抽),runner 批处理时应传全语料摘要。
        守卫:target 必须在语料编码集合内(未知 target 丢弃该条并记日志,不产出)、
        不得自指本卡、relation type 必须合法;graph_nodes kind 必须合法。
        兜底 = relations 空列表(replaces 规则迁移条目由 runner 叠加)+ graph_nodes 空列表。
        """
        corpus = list(corpus_digests) if corpus_digests else [digest]
        valid_targets = {d.wiki_id for d in corpus}

        raw = self._llm_result_or_none("rel", RELATION_SYSTEM_PROMPT,
                                       self._rel_prompt(digest, corpus))
        if raw is None:
            return ([], [])

        relations = self._guard_relations(raw.get("relations"), digest.wiki_id, valid_targets)
        graph_nodes = self._guard_graph_nodes(raw.get("graph_nodes"), digest.wiki_id)
        return (relations, graph_nodes)

    @staticmethod
    def _guard_relations(raw: Any, wiki_id: str, valid_targets) -> List[RelationDef]:
        """target/types 守卫 + 数量截断,最后整批过 Task 1 校验器(证据门在此落刀)。"""
        if not isinstance(raw, list):
            if raw is not None:
                logger.warning("graph_rel: 卡 %s relations 非列表(实得 %s), 丢弃",
                               wiki_id, type(raw).__name__)
            return []
        kept: List[Dict[str, Any]] = []
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                logger.warning("graph_rel: 卡 %s relations[%d] 非对象, 丢弃: %r", wiki_id, i, item)
                continue
            target = item.get("target")
            if not isinstance(target, str) or not target.strip():
                logger.warning("graph_rel: 卡 %s relations[%d].target 空, 丢弃", wiki_id, i)
                continue
            target = target.strip()
            if target not in valid_targets:
                logger.warning("graph_rel: 卡 %s relations[%d].target 未知 %r, 拒",
                               wiki_id, i, target)
                continue
            if target == wiki_id:
                logger.warning("graph_rel: 卡 %s relations[%d].target 自指本卡, 拒", wiki_id, i)
                continue
            if item.get("type") not in RELATION_TYPES:
                logger.warning("graph_rel: 卡 %s relations[%d].type 非法 %r, 拒",
                               wiki_id, i, item.get("type"))
                continue
            note = item.get("note")
            kept.append({
                "target": target,
                "type": item["type"],
                "note": note if isinstance(note, str) else "",
                "evidence": item.get("evidence"),
            })
        if len(kept) > MAX_RELATIONS_PER_CARD:
            logger.warning("graph_rel: 卡 %s 关系数 %d 超上限 %d, 截断",
                           wiki_id, len(kept), MAX_RELATIONS_PER_CARD)
            kept = kept[:MAX_RELATIONS_PER_CARD]
        return validate_relations(kept, valid_targets | {wiki_id})

    @staticmethod
    def _guard_graph_nodes(raw: Any, wiki_id: str) -> List[GraphNodeDef]:
        """kind 守卫 + 数量截断,最后整批过 Task 1 校验器。"""
        if not isinstance(raw, list):
            if raw is not None:
                logger.warning("graph_rel: 卡 %s graph_nodes 非列表(实得 %s), 丢弃",
                               wiki_id, type(raw).__name__)
            return []
        kept: List[Dict[str, Any]] = []
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                logger.warning("graph_rel: 卡 %s graph_nodes[%d] 非对象, 丢弃: %r", wiki_id, i, item)
                continue
            if item.get("kind") not in NODE_KINDS:
                logger.warning("graph_rel: 卡 %s graph_nodes[%d].kind 非法 %r, 拒",
                               wiki_id, i, item.get("kind"))
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                logger.warning("graph_rel: 卡 %s graph_nodes[%d].name 空, 拒", wiki_id, i)
                continue
            kept.append({"kind": item["kind"], "name": name})
        if len(kept) > MAX_GRAPH_NODES_PER_CARD:
            logger.warning("graph_rel: 卡 %s 节点数 %d 超上限 %d, 截断",
                           wiki_id, len(kept), MAX_GRAPH_NODES_PER_CARD)
            kept = kept[:MAX_GRAPH_NODES_PER_CARD]
        return validate_graph_nodes(kept)

    @staticmethod
    def _rel_prompt(digest: CardDigest, corpus: List[CardDigest]) -> str:
        """rel 步用户提示词:全语料摘要清单(合法 target)+ 本卡摘要要点。"""
        lines = [f"- {d.wiki_id} | {d.title} | {d.summary}" for d in corpus]
        entities = "、".join(str(e) for e in digest.entities if str(e).strip()) if digest.entities else "(无)"
        keywords = "、".join(str(k) for k in digest.keywords if str(k).strip()) if digest.keywords else "(无)"
        return "\n\n".join([
            f"本卡卡片编码：{digest.wiki_id}(不得作为 target 指向自己)",
            "全语料卡片摘要清单(target 只能从中选用)：\n" + "\n".join(lines),
            "本卡信息：\n"
            + f"标题：{digest.title}\n"
            + f"摘要：{digest.summary}\n"
            + f"现有实体：{entities}\n"
            + f"检索关键词：{keywords}\n"
            + f"正文要点：\n{digest.body_headline}",
        ])
