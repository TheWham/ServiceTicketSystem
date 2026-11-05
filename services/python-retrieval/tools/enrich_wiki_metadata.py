#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enrich_wiki_metadata.py — Wiki 图知识库阶段一 runner(就地增补 + 产图)

批处理流水线(计划 Task 6,glossary 载入/合并/落盘一体):

1. 载入 `--wiki-dir` 下全部卡片(硬排除 `_index.md`,其余 `*.md` 一张不落,
   LEG 卡同样参与——图需要它们承接 REPLACES 边);
2. `load_glossary` 读本轮词表(文件不存在 → 空词表,首跑自建);词表整轮冻结为
   「本轮词表」,每张卡的实体归一步都显式传 `glossary=<本轮词表>`、关系步显式传
   `corpus_digests=<全部卡 CardDigest 列表>`(漏传 corpus = 卡间关系静默全灭,
   runner 永不缺省);
3. 两步萃取(GraphExtractor):实体归一 → 逐卡立即读 `last_used_llm`;
   关系+结构节点 → 逐卡立即读 `last_used_llm`;provenance 聚合:两步任一步
   非来自 LLM → `graph_meta_source: rule`,两步均 LLM → `llm`;
4. relations = 萃取条目 + frontmatter replaces 规则迁移条目(`migrate_replaces`
   叠加;以「无 relations 的新底」迁移,绝不与旧卡 relations 累加 → 幂等),
   按 (target, type, evidence) 去重后整批过
   `validate_relations(valid_targets=全部卡编码)`——幻觉 target 在源头即拒;
5. 四键就地增补(`entities/relations/graph_nodes/graph_meta_source`),其余
   frontmatter 键与正文逐字节不动;`--dry-run` 严格零写入(卡不写、词表只读
   不落、图不产、LLM 磁盘缓存关闭),仅打印 diff 计数;
6. 正式跑:全部萃取成功后才写卡 → 合并新实体并落盘词表 → **写卡之后**重算
   wiki 指纹 → `build_graph_data` 组装 `{wiki_fingerprint, glossary, nodes,
   edges}` 原子落盘(阶段二 Neo4j 同步工具的唯一输入)。`--limit N` 时词表与
   语料摘要清单仍按全部卡;未处理卡以盘上现状进图产物(扁平实体补「概念」
   兜底类型,与萃取规则兜底同语义)。

异常语义(controller 裁决):任何卡的萃取/校验异常 = 非零退出整体中止,
不跳过、不降级、不做回滚——原子性交给 git(批次前确认工作区干净快照,
失败后以 git 恢复),runner 无自建事务。

【方向判定注记(Task 4 遗留,卡片撰写须知)】REPLACES 双向两卡对需要方向
裁决时,b 类「以本卡为准」的现行自证信号只取 relations 条目的 note,
**evidence 措辞不参与**该类方向判定——卡作者想表达替换方向请写在 note,
改 evidence 措辞不会改变方向裁决结果。

用法(在 services/python-retrieval 目录下;真批次是 Task 7 GATE,由 controller 安排):
    python tools/enrich_wiki_metadata.py --dry-run
    python tools/enrich_wiki_metadata.py
    python tools/enrich_wiki_metadata.py --limit 5 --dry-run
"""

import argparse
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rag_pipeline.chunking.fingerprint import compute_wiki_fingerprint
from rag_pipeline.ingestion.frontmatter_editor import (
    load_card,
    migrate_replaces,
    write_card,
)
from rag_pipeline.ingestion.graph_builder import (
    build_graph_data,
    load_glossary,
    merge_new_entities,
    save_glossary,
)
from rag_pipeline.ingestion.graph_extractor import (
    CardDigest,
    GraphExtractor,
)
from rag_pipeline.ingestion.graph_schema import (
    validate_entities,
    validate_graph_nodes,
    validate_relations,
)
from rag_pipeline.ingestion.llm_synthesizer import load_api_config

# 就地增补只动这四键;其余 frontmatter 键与正文逐字节不动(Review Focus 2)。
GRAPH_META_KEYS = ("entities", "relations", "graph_nodes", "graph_meta_source")
# rel 步摘要只送正文前 ~1500 字(CardDigest 契约)。
BODY_HEADLINE_CHARS = 1500
# 未处理卡(--limit 范围外)的扁平实体在图产物里的兜底类型:
# 与 GraphExtractor 规则兜底同语义(未定型 → 概念)。
UNTYPED_ENTITY_TYPE = "概念"
MIGRATION_EVIDENCE = "frontmatter:replaces"


def _build_extractor(cfg: Dict[str, str], cache_dir: Optional[str]) -> GraphExtractor:
    """依赖缝:真实流水线走 GraphExtractor;测试按 test_degraded_rejection.py
    注入法(monkeypatch 模块属性 GraphExtractor/load_api_config)替换本依赖。"""
    return GraphExtractor(cfg, cache_dir=cache_dir)


def _collect_card_paths(wiki_dir: Path) -> List[Path]:
    paths = sorted(
        p for p in Path(wiki_dir).glob("*.md")
        if p.name != "_index.md"
    )
    if not paths:
        raise ValueError(f"wiki 目录下没有任何卡片(*.md, 排除 _index.md): {wiki_dir}")
    return paths


def _flat_entity_names(entities: Any) -> List[str]:
    """卡上实体列表 → 扁平名列表(旧卡为字符串列表,已增补卡为 {name,type} 对象列表)。"""
    out: List[str] = []
    for e in entities or []:
        if isinstance(e, dict):
            name = e.get("name")
            if isinstance(name, str) and name.strip():
                out.append(name)
        elif isinstance(e, str) and e.strip():
            out.append(e)
    return out


def _make_digest(wiki_id: str, meta: Dict[str, Any], body: str) -> CardDigest:
    return CardDigest(
        wiki_id=wiki_id,
        title=str(meta.get("title") or wiki_id),
        summary=str(meta.get("summary") or ""),
        entities=_flat_entity_names(meta.get("entities")),
        keywords=[k for k in (meta.get("keywords") or []) if isinstance(k, str)],
        body_headline=body[:BODY_HEADLINE_CHARS],
    )


def _graph_view(meta: Dict[str, Any]) -> Dict[str, Any]:
    """未处理卡进图产物时的视图:扁平实体补兜底类型,其余键原样(build 侧再验)。"""
    view = dict(meta)
    typed: List[Dict[str, str]] = []
    for e in meta.get("entities") or []:
        if (isinstance(e, dict) and isinstance(e.get("name"), str)
                and isinstance(e.get("type"), str)):
            typed.append({"name": e["name"], "type": e["type"]})
        elif isinstance(e, str) and e.strip():
            typed.append({"name": e, "type": UNTYPED_ENTITY_TYPE})
    view["entities"] = typed
    return view


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    """产物原子写(临时文件 + os.replace),与 save_glossary 同语义。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = None, None
    try:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        raise


def _run(wiki_dir: Path, graph_out: Path, glossary_path: Path,
         cache_dir: Optional[str], dry_run: bool,
         limit: Optional[int]) -> None:
    card_paths = _collect_card_paths(wiki_dir)

    loaded: List[Tuple[Path, str, Dict[str, Any], str]] = []
    seen_ids: Set[str] = set()
    for p in card_paths:
        meta, body = load_card(p)
        wiki_id = str(meta.get("id") or p.stem).strip()
        if not wiki_id:
            raise ValueError(f"卡片缺少 id 编码: {p}")
        if wiki_id in seen_ids:
            raise ValueError(f"卡编码重复: {wiki_id}({p})")
        seen_ids.add(wiki_id)
        loaded.append((p, wiki_id, meta, body))
    valid_targets = set(seen_ids)

    if limit is not None:
        if limit <= 0:
            raise ValueError(f"--limit 必须是正整数, 实得 {limit}")
        processed = loaded[:limit]
    else:
        processed = loaded

    print(f"载入卡片 {len(loaded)} 张(含 LEG, 排除 _index.md), "
          f"本轮增补 {len(processed)} 张(dry-run={dry_run}, limit={limit})")

    glossary = load_glossary(glossary_path)
    print(f"词表载入: 实体 {len(glossary['entities'])} 个({glossary_path})")

    extractor = _build_extractor(
        load_api_config(), cache_dir=None if dry_run else cache_dir
    )

    # ---- 第一步:实体归一(glossary=<本轮词表>,整轮冻结;显式传参,永不缺省)。
    # last_used_llm 每步调用后立即读(裁决 10)。
    ent_results: Dict[str, Tuple[List[Tuple[str, str]], bool]] = {}
    all_new_entities = []
    for _p, wiki_id, meta, body in processed:
        normalized, new_entities = extractor.normalize_entities(
            wiki_id, _flat_entity_names(meta.get("entities")), body,
            glossary=glossary,
        )
        ent_used = bool(extractor.last_used_llm)
        # 计划逐字:装配前过 validate_*;萃取器已验一遍,runner 侧复核防线。
        validated = validate_entities(
            [{"name": e.name, "type": e.type} for e in normalized]
        )
        ent_results[wiki_id] = ([(e.name, e.type) for e in validated], ent_used)
        all_new_entities.extend(new_entities)

    merged_glossary = merge_new_entities(glossary, all_new_entities)

    # ---- 第二步:关系 + 结构节点(corpus_digests=<全部卡 CardDigest 列表>,
    # 显式传参;漏传 = 卡间关系静默全灭)。last_used_llm 每步调用后立即读。
    digests = [_make_digest(w, m, b) for _p, w, m, b in loaded]
    assembled: List[Tuple[Path, str, Dict[str, Any], Dict[str, Any]]] = []
    for _p, wiki_id, meta, _body in processed:
        rel_defs, node_defs = extractor.extract_relations_and_nodes(
            _make_digest(wiki_id, meta, _body), corpus_digests=digests
        )
        rel_used = bool(extractor.last_used_llm)

        ent_names_types, ent_used = ent_results[wiki_id]
        provenance = "llm" if (ent_used and rel_used) else "rule"

        extracted_dicts = [
            {"target": r.target, "type": r.type, "note": r.note,
             "evidence": r.evidence}
            for r in rel_defs
        ]
        # 迁移以「无 relations 的新底」叠加 → 不与旧卡 relations 累加 → 幂等。
        migrate_src = {k: v for k, v in meta.items() if k != "relations"}
        migrated = migrate_replaces(migrate_src)
        combined = extracted_dicts + list(migrated.get("relations") or [])
        seen_rel: Set[Tuple[str, str, str]] = set()
        deduped: List[Dict[str, Any]] = []
        for item in combined:
            key = (item["target"], item["type"], item["evidence"])
            if key in seen_rel:
                continue
            seen_rel.add(key)
            deduped.append(item)
        # 未知/幻觉 target 在此整批拒(小语料幻觉防护);任何异常 = 整体中止。
        validated_rels = validate_relations(deduped, valid_targets)
        relation_dicts = [
            {"target": r.target, "type": r.type, "note": r.note,
             "evidence": r.evidence}
            for r in validated_rels
        ]

        validated_nodes = validate_graph_nodes(
            [{"kind": g.kind, "name": g.name} for g in node_defs]
        )
        node_dicts = [{"kind": g.kind, "name": g.name} for g in validated_nodes]

        new_meta = dict(meta)
        new_meta["entities"] = [{"name": n, "type": t} for n, t in ent_names_types]
        new_meta["relations"] = relation_dicts
        new_meta["graph_nodes"] = node_dicts
        new_meta["graph_meta_source"] = provenance
        assembled.append((_p, wiki_id, meta, new_meta))
        migrated_n = sum(1 for r in relation_dicts
                         if r["evidence"] == MIGRATION_EVIDENCE)
        print(f"  ✅ {wiki_id}: 实体 {len(ent_names_types)}, "
              f"关系 {len(relation_dicts)}(其中迁移 {migrated_n}), "
              f"结构节点 {len(node_dicts)}, provenance={provenance}")

    # 变更计数(四键新旧对比);--dry-run 的产出即这份计数。此处仅打印。
    changed = {k: 0 for k in GRAPH_META_KEYS}
    for _p, _w, old, new in assembled:
        for key in GRAPH_META_KEYS:
            if old.get(key) != new.get(key):
                changed[key] += 1
    print("变更计数: " + ", ".join(f"{k}={changed[k]}" for k in GRAPH_META_KEYS))
    print(f"词表合并: 新增实体 {len(all_new_entities)} 个, "
          f"合并后 {len(merged_glossary['entities'])} 个")

    if dry_run:
        print("DRY-RUN: 严格零写入 —— 卡片未写、词表只读未落、图产物未产、LLM 缓存关闭")
        return

    # ---- 写卡:全部萃取成功后才落卡(萃取途中异常时一张都不写;若写卡后
    # 故障中止,已写卡不回滚——原子性交给 git,裁决逐字)。
    for card_path, wiki_id, _old, new_meta in assembled:
        old_meta = _old
        body = next(b for p, _w, _m, b in loaded if p == card_path)
        write_card(card_path, new_meta, body)
    print(f"写卡完成: {len(assembled)} 张(就地四键增补, 正文逐字节不动)")

    glossary_path.parent.mkdir(parents=True, exist_ok=True)
    save_glossary(glossary_path, merged_glossary)
    print(f"词表落盘: {glossary_path}")

    # ---- 指纹在写卡之后重算(裁决 2:勿在写卡前缓存)。
    fingerprint = compute_wiki_fingerprint(card_paths)

    processed_ids = {w for _p, w, _m, _b in processed}
    world = [
        (wiki_id,
         _graph_view(next(m for p, w, m, _b in loaded if p == card_p))
         if wiki_id not in processed_ids
         else next(m for _p, w, _om, m in assembled if w == wiki_id))
        for card_p, wiki_id, _m, _b in (
            (p, w, m, b) for p, w, m, b in loaded
        )
    ]
    graph_data = build_graph_data(world, merged_glossary, fingerprint)
    _atomic_write_json(graph_out, graph_data)
    print(f"图产物落盘: {graph_out}(节点 {len(graph_data['nodes'])}, "
          f"边 {len(graph_data['edges'])}, 指纹 {fingerprint[:12]}…)")


def run_enrichment(wiki_dir: Path, graph_out: Path, glossary_path: Path,
                   cache_dir: Optional[str] = None, dry_run: bool = False,
                   limit: Optional[int] = None) -> int:
    """执行一轮增补;0 = 成功,非 0 = 整体中止(异常即此路,无回滚)。"""
    try:
        _run(Path(wiki_dir), Path(graph_out), Path(glossary_path),
             cache_dir, dry_run, limit)
    except Exception:
        traceback.print_exc()
        print("❌ 增补中止: 萃取/校验异常 = 非零退出整体中止"
              "(不跳过、不降级、不回滚; 已写卡请以 git 快照恢复, "
              "批次后再评估——真批次走 Task 7 GATE)")
        return 1
    return 0


def _resolve(p: str) -> Path:
    """CLI 相对路径以 services/python-retrieval 为基准;绝对路径原样。"""
    path = Path(p)
    return path if path.is_absolute() else REPO_ROOT / path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wiki 图知识库阶段一 runner:四键就地增补 + graph_data 产物"
                    "(真批次属 Task 7 GATE;先 --dry-run 看计数)"
    )
    parser.add_argument("--wiki-dir", default="artifacts/output/wiki",
                        help="wiki 卡片目录(默认 artifacts/output/wiki)")
    parser.add_argument("--graph-out",
                        default="artifacts/output/graph/graph_data.json",
                        help="graph_data.json 输出路径")
    parser.add_argument("--glossary",
                        default="artifacts/output/graph/entity_glossary.json",
                        help="实体词表路径(读+合并+落盘;dry-run 只读不落)")
    parser.add_argument("--cache-dir", default="artifacts/indexing/.graph_llm_cache",
                        help="两步 LLM 萃取磁盘缓存目录(dry-run 关闭)")
    parser.add_argument("--dry-run", action="store_true",
                        help="严格零写入:只打印 diff 计数")
    parser.add_argument("--limit", type=int, default=None,
                        help="只增补前 N 张卡(定向定位;语料摘要清单仍传全部卡)")
    args = parser.parse_args(argv)

    print("=== enrich_wiki_metadata: Wiki 图元数据增补(阶段一 runner) ===")
    return run_enrichment(
        _resolve(args.wiki_dir), _resolve(args.graph_out), _resolve(args.glossary),
        str(_resolve(args.cache_dir)), dry_run=args.dry_run, limit=args.limit,
    )


if __name__ == "__main__":
    sys.exit(main())
