"""rag_pipeline.config — 全链路统一配置中心。

configs/pipeline.yaml 是唯一真源：切片规则、嵌入/重排模型、检索参数、
废止卡排除清单全部在此声明。Day12（建库）与 Day13（检索评测）共用同一份
配置实例化切块器与检索器，杜绝"两处硬编码各改一处"的静默错配。

config_fingerprint() 对 chunking+embedding 两节做规范化哈希，写入 Day12
的 manifest.json；Day13 加载持久化向量库前比对指纹，配置变更自动判旧库失效。
"""

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "pipeline.yaml"


@dataclass
class ChunkingConfig:
    strategy: str = "parent_child"
    child_size: int = 512
    section_header_level: int = 2
    merge_preamble: bool = True
    strip_trace_tail: bool = True
    boost_injection: str = "first"   # first | all | none
    breadcrumb_header: bool = True
    struct_chunk_size: int = 550
    struct_chunk_overlap: int = 80


@dataclass
class RetrievalConfig:
    top_k: int = 3
    rough_top_k: int = 15
    rrf_k: int = 60
    fuse_k: int = 10
    rrf_weight: float = 0.6
    rerank_weight: float = 0.4
    reject_threshold: Optional[float] = None
    rerank_granularity: str = "child"
    query_rewrite: bool = False
    rewrite_model: str = ""
    default_exclude: Dict[str, List[str]] = field(
        default_factory=lambda: {"wiki_status": ["已废止", "已下线"]}
    )


@dataclass
class PipelineConfig:
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    embedding_model: str = "qwen3-embedding-8b"
    embedding_cache_dir: str = "day12_output/.emb_cache"
    store_persist_dir: str = "day12_output/chroma_wiki_structured"
    store_collection: str = "wiki_structured_kb"
    reranker_model: str = "qwen3-reranker-8b"
    reranker_backend: str = "dashscope"


def _fill(dc: Any, data: Optional[Dict[str, Any]]) -> Any:
    """把 YAML 片段填进 dataclass：未知键忽略、缺失键保留默认值。"""
    for k, v in (data or {}).items():
        if hasattr(dc, k) and v is not None:
            setattr(dc, k, v)
    return dc


def load_config(path: Optional[str] = None) -> PipelineConfig:
    """加载 YAML 配置；文件缺失时全部走内置默认值（= 当前线上行为）。"""
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    raw: Dict[str, Any] = {}
    if cfg_path.exists():
        try:
            import yaml
            raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except ImportError as e:
            raise RuntimeError(
                f"缺少 PyYAML 依赖，无法读取配置文件 {cfg_path}。请执行: pip install PyYAML"
            ) from e
    return PipelineConfig(
        chunking=_fill(ChunkingConfig(), raw.get("chunking")),
        retrieval=_fill(RetrievalConfig(), raw.get("retrieval")),
        embedding_model=(raw.get("embedding") or {}).get("model", "qwen3-embedding-8b"),
        embedding_cache_dir=(raw.get("embedding") or {}).get("cache_dir", "day12_output/.emb_cache"),
        store_persist_dir=(raw.get("store") or {}).get("persist_dir", "day12_output/chroma_wiki_structured"),
        store_collection=(raw.get("store") or {}).get("collection", "wiki_structured_kb"),
        reranker_model=(raw.get("reranker") or {}).get("model", "qwen3-reranker-8b"),
        reranker_backend=(raw.get("reranker") or {}).get("backend", "dashscope"),
    )


def config_fingerprint(cfg: PipelineConfig) -> str:
    """chunking+embedding 两节的规范化 sha1：任何切片参数变动都会改变指纹。"""
    payload = {
        "chunking": asdict(cfg.chunking),
        "embedding_model": cfg.embedding_model,
    }
    return hashlib.sha1(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def build_chunker(cfg: PipelineConfig):
    """按配置实例化切块器，返回 (chunker, use_parent_child)。

    Day12 与 Day13 都必须经此工厂取切块器——保证两侧语料粒度永远一致。
    """
    from .chunking.parent_child import ParentChildChunker
    from .chunking.structure_aware import WikiStructureAwareChunker

    cc = cfg.chunking
    if cc.strategy == "parent_child":
        return ParentChildChunker(config=cc), True
    return WikiStructureAwareChunker(
        chunk_size=cc.struct_chunk_size, chunk_overlap=cc.struct_chunk_overlap
    ), False
