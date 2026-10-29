# -*- coding: utf-8 -*-
"""知识卡片全量离线抽取器与缓存持久化引擎。

支持 Frontmatter 实体预注入、LLM 结构化抽取、原文佐证比对过滤与 JSON 缓存。
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .schema import ExtractionOutput, GroundedTriple, ITRelationEnum

logger = logging.getLogger(__name__)


def parse_card_markdown(text: str) -> Tuple[Dict[str, Any], str]:
    """解析 Markdown 卡片，分离 YAML frontmatter 与正文。"""
    meta: Dict[str, Any] = {}
    body = text.strip()

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            raw_yaml = parts[1].strip()
            body = parts[2].strip()
            try:
                meta = yaml.safe_load(raw_yaml) or {}
            except Exception as e:
                logger.warning("解析 YAML frontmatter 异常: %s", e)

    return meta, body


def inject_frontmatter_governance_triples(meta: Dict[str, Any]) -> List[GroundedTriple]:
    """从卡片元数据中提取确定性制度治理与版本关系三元组。"""
    triples: List[GroundedTriple] = []
    card_id = meta.get("id")
    if not card_id:
        return triples

    # 1. 废止与替代关系 (replaces)
    replaces = meta.get("replaces") or []
    if isinstance(replaces, str):
        try:
            replaces = json.loads(replaces)
        except Exception:
            replaces = [replaces]

    for old_id in replaces:
        if old_id:
            triples.append(
                GroundedTriple(
                    head=card_id,
                    relation=ITRelationEnum.REPLACES,
                    tail=str(old_id),
                    evidence_quote=f'replaces: ["{old_id}"]',
                )
            )
            # 附带废止状态标识
            triples.append(
                GroundedTriple(
                    head=str(old_id),
                    relation=ITRelationEnum.STATUS_IS,
                    tail="已废止下线",
                    evidence_quote=f'replaces: ["{old_id}"]',
                )
            )

    # 2. 现行卡片生效状态
    status = meta.get("status", "现行有效")
    triples.append(
        GroundedTriple(
            head=card_id,
            relation=ITRelationEnum.STATUS_IS,
            tail="现行有效" if status in ("现行", "现行有效") else str(status),
            evidence_quote=f'id: "{card_id}"',
        )
    )

    # 3. 关联服务分类
    category = meta.get("category")
    if category:
        triples.append(
            GroundedTriple(
                head=card_id,
                relation=ITRelationEnum.DEPENDS_ON,
                tail=str(category),
                evidence_quote=f'category: "{category}"',
            )
        )

    return triples


def validate_triples_against_source(
    triples: List[GroundedTriple], source_text: str
) -> List[GroundedTriple]:
    """严格原文佐证比对 (Quote Grounding)：原句在原文中无法逐字匹配时拦截丢弃。"""
    validated: List[GroundedTriple] = []
    # 预处理空白便于容错比对
    normalized_source = re.sub(r"\s+", " ", source_text)

    for t in triples:
        quote = t.evidence_quote.strip()
        # 元数据规则三元组跳过文本比对
        if quote.startswith('replaces:') or quote.startswith('id:') or quote.startswith('category:'):
            validated.append(t)
            continue

        normalized_quote = re.sub(r"\s+", " ", quote)
        if quote in source_text or normalized_quote in normalized_source:
            validated.append(t)
        else:
            logger.warning(
                "❌ 拦截虚假三元组 [佐证不符]: (%s, %s, %s) -> 原文未找到: '%s'",
                t.head,
                t.relation.value,
                t.tail,
                quote[:30],
            )

    return validated


def save_triples_cache(triples: List[GroundedTriple], cache_path: Path) -> None:
    """持久化三元组列表至本地 JSON 缓存。"""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    raw_data = [t.model_dump(mode="json") for t in triples]
    cache_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_triples_cache(cache_path: Path) -> List[GroundedTriple]:
    """从本地 JSON 缓存加载三元组列表。"""
    if not cache_path.exists():
        return []
    content = cache_path.read_text(encoding="utf-8")
    raw_list = json.loads(content)
    return [GroundedTriple.model_validate(item) for item in raw_list]


# ==============================================================================
# LLM 批量结构化抽取
# ==============================================================================

EXTRACTION_SYSTEM_PROMPT = """你是一个严谨的企业级知识图谱构建专家。
你的任务是从给定的 IT 运维与制度 Markdown 卡片中，提取实体间的核心关系三元组。

【严格约束要求】：
1. 关系 (relation) 必须且只能从以下受控枚举中选取：
   - "诱发根因": 某故障/错误码的直接潜在原因或诱发诱因
   - "衍生次生故障": 某故障发生后衍生连锁影响的其他故障或系统
   - "前置排查动作": 解决/诊断该问题前员工必做的排查步骤
   - "处置动作": 解决该故障的最终修复手段、命令或配置
   - "依赖网络通道": 访问系统所必须具备的 VPN 或专用网段通道
   - "依赖身份源": 系统/凭据所依赖的认证中心（如 AD域、统一认证）
   - "依赖系统组件": 依赖的软硬件底层或驱动
   - "主责运维组": 处置该类故障或系统的负责团队
   - "出差代签人": 审批人出差时被授权的代签人
   - "利益回避转派": 遇到利益冲突时必须转派的审核机构或人员
2. 实体 (head / tail) 必须是简短、原子的专业名词、代码或团队，严禁使用长句子，严禁包含句号逗号！
3. 必须优先使用提供的【实体候选池】中的标准名词。
4. 每条三元组必须提供 evidence_quote（从原文中逐字摘录的佐证原句，不可篡改）！

请严格按 JSON 格式输出：{"triples": [{"head": "...", "relation": "...", "tail": "...", "evidence_quote": "..."}]}
"""


def extract_card_triples_with_llm(
    card_id: str,
    card_meta: Dict[str, Any],
    card_text: str,
    client: Any = None,
    model: str = "deepseek-v4.1-flash",
) -> List[GroundedTriple]:
    """使用 LLM 对单张卡片进行严格模式三元组提取（带重试）。"""
    candidate_entities = card_meta.get("entities", [])
    user_prompt = f"""【卡片编号】：{card_id}
【卡片标题】：{card_meta.get('title', '')}
【实体候选池】：{candidate_entities}

【卡片正文】：
{card_text}

请提取出卡片中的关键因果、依赖与排查关系三元组，以 JSON 输出："""

    if client is None:
        return []

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                timeout=25,
            )
            raw_json = response.choices[0].message.content
            data = json.loads(raw_json)
            triples_data = data.get("triples", [])
            extracted: List[GroundedTriple] = []
            for item in triples_data:
                try:
                    triple = GroundedTriple.model_validate(item)
                    extracted.append(triple)
                except Exception as e:
                    logger.debug("过滤无效格式三元组: %s (error: %s)", item, e)
            return extracted
        except Exception as e:
            if attempt == 1:
                logger.warning("卡片 %s LLM 抽取失败 (已重试): %s", card_id, e)
    return []


def extract_all_wiki_cards(
    wiki_dir: Path,
    cache_path: Path,
    client: Any = None,
    model: str = "deepseek-v4.1-flash",
    use_cache: bool = True,
    max_workers: int = 5,
) -> List[GroundedTriple]:
    """批量抽取 Wiki 目录下全部卡片，支持并发与本地缓存。"""
    if use_cache and cache_path.exists():
        cached = load_triples_cache(cache_path)
        if cached:
            print(f"📦 [Graph Extractor] 直接命中本地缓存，已加载 {len(cached)} 条三元组: {cache_path}", flush=True)
            return cached

    print(f"🚀 [Graph Extractor] 开始对 {wiki_dir} 进行全量卡片三元组抽取与图谱构建 (并发={max_workers}, model={model})...", flush=True)
    card_files = sorted(p for p in wiki_dir.glob("*.md") if p.name != "_index.md")
    all_triples: List[GroundedTriple] = []

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def process_one_card(card_file: Path) -> List[GroundedTriple]:
        raw_text = card_file.read_text(encoding="utf-8")
        meta, body = parse_card_markdown(raw_text)
        card_id = meta.get("id") or card_file.stem

        card_triples: List[GroundedTriple] = []
        # 1. 注入元数据确定性治理关系
        gov_triples = inject_frontmatter_governance_triples(meta)
        card_triples.extend(gov_triples)

        # 2. 驱动 LLM 抽取正文因果排查关系
        llm_count = 0
        if client:
            llm_triples = extract_card_triples_with_llm(card_id, meta, raw_text, client=client, model=model)
            validated = validate_triples_against_source(llm_triples, raw_text)
            card_triples.extend(validated)
            llm_count = len(validated)

        print(f"  • 已处理 {card_id:15s}: 规则三元组 {len(gov_triples)} 条, LLM 有效三元组 {llm_count} 条", flush=True)
        return card_triples

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_one_card, cf): cf for cf in card_files}
        for future in as_completed(futures):
            try:
                card_triples = future.result()
                all_triples.extend(card_triples)
            except Exception as e:
                logger.error("处理卡片异常: %s", e)

    # 去重
    unique_map: Dict[Tuple[str, str, str], GroundedTriple] = {}
    for t in all_triples:
        key = (t.head, t.relation.value, t.tail)
        if key not in unique_map:
            unique_map[key] = t

    final_triples = list(unique_map.values())
    print(f"✅ [Graph Extractor] 抽取完成！全局去重后总计 {len(final_triples)} 条三元组，正在持久化至缓存...", flush=True)
    save_triples_cache(final_triples, cache_path)
    return final_triples


if __name__ == "__main__":
    import sys
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    from openai import OpenAI
    from rag_pipeline.config import REPO_ROOT

    wiki_dir = REPO_ROOT / "artifacts" / "output" / "wiki"
    cache_path = REPO_ROOT / "artifacts" / "indexing" / "knowledge_graph_triples.json"

    api_key = os.environ.get("AI_API_KEY") or os.environ.get("LLM_API_KEY")
    base_url = os.environ.get("AI_BASE_URL") or os.environ.get("LLM_BASE_URL")
    model = os.environ.get("GRAPH_EXTRACT_MODEL") or "deepseek-v4.1-flash"

    client = None
    if api_key and base_url:
        client = OpenAI(api_key=api_key, base_url=base_url)
        print(f"🔗 [Graph Extractor] 成功初始化 LLM 客户端: {base_url} (model={model})")
    else:
        print("⚠️ [Graph Extractor] 未检测到大模型凭据，仅提取 Frontmatter 规则三元组")

    extract_all_wiki_cards(wiki_dir, cache_path, client=client, model=model, use_cache=False)

