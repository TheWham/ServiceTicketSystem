"""rag_pipeline.config — 全链路统一配置中心。

configs/pipeline.yaml 是唯一真源：切片规则、嵌入/重排模型、检索参数、
废止卡排除清单全部在此声明。索引构建与检索评测共用同一份
配置实例化切块器与检索器，杜绝"两处硬编码各改一处"的静默错配。

config_fingerprint() 对 chunking+embedding 两节做规范化哈希，写入
manifest.json；检索评测加载持久化向量库前比对指纹，配置变更自动判旧库失效。
"""

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# 数据/配置根目录：服务化部署时用 RAG_HOME 环境变量注入（指向服务的工作/数据目录）；
# 未设置则回退到包位置上一级（demo 仓库的仓库根）。
REPO_ROOT = Path(os.environ.get("RAG_HOME", "") or Path(__file__).resolve().parents[1])
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "pipeline.yaml"


def _load_dotenv() -> Dict[str, str]:
    """解析 REPO_ROOT/.env 的键值（.env 已被 .gitignore 忽略，key 绝不入库）。"""
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return {}
    kv: Dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        kv[k.strip()] = v.strip().strip('"').strip("'")
    return kv


def load_embedding_config() -> Dict[str, str]:
    """Embedding 模型配置（独立 base_url/key/model）：进程环境变量 > .env > 默认。"""
    dotenv = _load_dotenv()
    return {
        "api_key": os.environ.get("EMBED_API_KEY") or dotenv.get("EMBED_API_KEY", ""),
        "base_url": os.environ.get("EMBED_BASE_URL") or dotenv.get("EMBED_BASE_URL", ""),
        "model": os.environ.get("EMBED_MODEL") or dotenv.get("EMBED_MODEL", "qwen3-embedding-8b"),
    }


def load_rerank_config() -> Dict[str, str]:
    """Rerank 模型配置（独立 base_url/key/model）。

    provider 判断后端形态：base_url 指向 KSP 网关（域名含 kspmas）时走 KSP 双后端
    限定与并发对冲（Jina/DashScope 随机分流），否则直连单后端（如阿里云百炼）。
    model 默认空，交由 yaml 的 reranker_model 兜底。
    """
    dotenv = _load_dotenv()
    base_url = os.environ.get("RERANK_BASE_URL") or dotenv.get("RERANK_BASE_URL", "")
    api_key = os.environ.get("RERANK_API_KEY") or dotenv.get("RERANK_API_KEY", "")
    model = os.environ.get("RERANK_MODEL") or dotenv.get("RERANK_MODEL", "")
    provider = "ksp" if "kspmas" in base_url else "direct"
    return {
        "provider": provider,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "note": "",
    }


def load_llm_config() -> Dict[str, str]:
    """LLM（对话/清洗）模型配置（独立 base_url/key + chat/clean 两个模型）。"""
    dotenv = _load_dotenv()
    return {
        "api_key": os.environ.get("LLM_API_KEY") or dotenv.get("LLM_API_KEY", ""),
        "base_url": os.environ.get("LLM_BASE_URL") or dotenv.get("LLM_BASE_URL", ""),
        "chat_model": os.environ.get("LLM_CHAT_MODEL") or dotenv.get("LLM_CHAT_MODEL", "kimi-k3"),
        "clean_model": os.environ.get("LLM_CLEAN_MODEL") or dotenv.get("LLM_CLEAN_MODEL", "deepseek-v4-flash"),
    }


# ---- demo 专用路径常量（仅供 demo 仓库 tools/ 脚本引用；服务化接入时不应依赖）----
ARTIFACTS_ROOT = REPO_ROOT / "artifacts"
WIKI_DIR = ARTIFACTS_ROOT / "output" / "wiki"          # demo: Wiki 卡片输入
INDEXING_OUTPUT = ARTIFACTS_ROOT / "indexing"          # demo: 建库产物（向量库/缓存/报告）
EVALUATION_OUTPUT = ARTIFACTS_ROOT / "evaluation"      # demo: 评测产物（报告）


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
    reject_threshold: Optional[float] = None   # 低置信拒答：候选最高原始 rerank 分低于此值返回空
    rerank_granularity: str = "child"          # 精排粒度: child=子块 | parent=子块召回后对整卡全文打分
    query_rewrite: bool = False                # 查询改写：LLM 删猜测+补术语，原查询+改写查询四路召回
    rewrite_model: str = ""                    # 改写模型，空=取 LLM_CLEAN_MODEL
    default_exclude: Dict[str, List[str]] = field(
        default_factory=lambda: {"wiki_status": ["已废止", "已下线"]}
    )


@dataclass
class PipelineConfig:
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    embedding_model: str = "qwen3-embedding-8b"
    embedding_cache_dir: str = "data/.emb_cache"
    store_persist_dir: str = "data/chroma_wiki_structured"
    store_collection: str = "wiki_structured_kb"
    reranker_model: str = "qwen3-reranker-8b"
    reranker_backend: str = "dashscope"    # 仅走 KSP 网关时生效（直连供应商时忽略）


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
        embedding_cache_dir=(raw.get("embedding") or {}).get("cache_dir", "data/.emb_cache"),
        store_persist_dir=(raw.get("store") or {}).get("persist_dir", "data/chroma_wiki_structured"),
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

    索引构建与检索评测都必须经此工厂取切块器——保证两侧语料粒度永远一致。
    """
    from .chunking.parent_child import ParentChildChunker
    from .chunking.structure_aware import WikiStructureAwareChunker

    cc = cfg.chunking
    if cc.strategy == "parent_child":
        return ParentChildChunker(config=cc), True
    return WikiStructureAwareChunker(
        chunk_size=cc.struct_chunk_size, chunk_overlap=cc.struct_chunk_overlap
    ), False
