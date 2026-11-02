"""rag_pipeline.config — 全链路统一配置中心。

configs/pipeline.yaml 是唯一真源：切片规则、嵌入/重排模型、检索参数、
废止卡排除清单全部在此声明。索引构建与检索评测共用同一份
配置实例化切块器与检索器，杜绝"两处硬编码各改一处"的静默错配。

config_fingerprint() 对 chunking+embedding 两节做规范化哈希，写入
manifest.json；检索评测加载持久化向量库前比对指纹，配置变更自动判旧库失效。
"""

import hashlib
import json
import logging
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

# D-23:「白名单不含 REPLACES」说明性告警的进程级 once-latch
# （热路径每请求 load_config()，真正的刚需告警只发一次；测试可用 monkeypatch 归零）。
_whitelist_notice_latched = False


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
    heuristic_reject_threshold: Optional[float] = 0.25  # 降级（启发式打分）拒答阈值：None=降级时不拒答
    rerank_granularity: str = "child"          # 精排粒度: child=子块 | parent=子块召回后对整卡全文打分
    query_rewrite: bool = False                # 查询改写：LLM 删猜测+补术语，原查询+改写查询四路召回
    rewrite_model: str = ""                    # 改写模型，空=取 LLM_CLEAN_MODEL
    default_exclude: Dict[str, List[str]] = field(
        default_factory=lambda: {"wiki_status": ["已废止", "已下线"]}
    )
    # 置信度动态门控：按本次 rerank 打分分布决定给精排多大话语权（详见 retrieval/hybrid.py Step 4）
    gate_enabled: bool = False                              # 关闭时行为与固定权重完全一致
    gate_min_score: float = 0.55                            # 高置信门槛①：top-1 原始 rerank 分 ≥ 此值
    gate_min_margin: float = 0.10                           # 高置信门槛②：top-1 与 top-2 分差 ≥ 此值
    gate_conf_weights: List[float] = field(default_factory=lambda: [0.35, 0.65])
    gate_low_weights: List[float] = field(default_factory=lambda: [0.65, 0.35])


@dataclass
class Neo4jConfig:
    """Neo4j 连接参数。凭证不落明文：password 直填仅限本地测试（优先级更高），
    为空时从 password_env 指名的环境变量取（进程环境 > REPO_ROOT/.env）。"""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password_env: str = "NEO4J_PASSWORD"
    password: str = ""


@dataclass
class ExpansionConfig:
    """图扩展参数：白名单边的邻居按衰减分补进检索结果（分数严格低于源卡）。"""
    edge_whitelist: List[str] = field(
        default_factory=lambda: ["SAME_ROOT_CAUSE", "RELATED", "PROCESS_APPLIES"]
    )
    max_neighbors: int = 2
    decay: float = 0.5          # 扩展分 = 源卡分 × decay，加载期强制 0 < decay < 1
    score_floor: float = 0.10
    timeout_ms: int = 300


@dataclass
class GraphConfig:
    """图知识库开关与参数（默认 enabled=false：写而不启用）。"""
    enabled: bool = False
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    expansion: ExpansionConfig = field(default_factory=ExpansionConfig)


@dataclass
class PipelineConfig:
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    graph: GraphConfig = field(default_factory=GraphConfig)
    embedding_model: str = "qwen3-embedding-8b"
    embedding_cache_dir: str = "data/.emb_cache"
    store_persist_dir: str = "data/chroma_wiki_structured"
    store_collection: str = "wiki_structured_kb"
    reranker_model: str = "qwen3-reranker-8b"
    reranker_backend: str = "dashscope"    # 仅走 KSP 网关时生效（直连供应商时忽略）


def _as_bool(value: Any) -> bool:
    """类型安全布尔解析（语义对齐 rag_service.assembly._env_bool 同集）：
    bool 直接用；其余按字符串 strip+小写后仅接受 "1"/"true"/"yes"/"on"。
    防止 yaml 带引号字符串 'false' 落进 bool("false")==True 的 truthiness 陷阱。"""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _fill(dc: Any, data: Optional[Dict[str, Any]]) -> Any:
    """把 YAML 片段填进 dataclass：未知键忽略、缺失键保留默认值。"""
    for k, v in (data or {}).items():
        if hasattr(dc, k) and v is not None:
            setattr(dc, k, v)
    return dc


def _build_graph_config(raw: Optional[Dict[str, Any]]) -> GraphConfig:
    """装配并校验 graph 段。

    校验全部在加载期完成——配置错误必须在启动时炸，而不是在检索热路径上
    才发现扩展分冒充了相似度（Review Focus 4）。
    - REPLACES 进白名单 → ValueError（永不进热路径，配了即配错）；
      enabled=true 且不含 REPLACES → 告警日志说明其不参与图扩展（由版本消歧
      在检索层处理）。告警仅在 enabled=true 时打：默认关=静默，否则 policy
      版本消歧热路径每次请求 load_config 都会刷一条误导性 WARNING；
    - decay 必须严格 0<decay<1：decay>=1 使扩展分不低于源卡，搅浑准入/去重
      语义与 topScore 复核；decay<=0 使扩展条目恒为 0 分；
    - 凭证：password 直填（本地测试）优先，否则从 password_env 指名的环境变量取
      （进程环境 > .env）；enabled=true 且两者皆空 → ValueError，不带空密码上路。

    顺序约定：两条 ValueError（白名单/decay）与凭证校验前置，说明性告警
    放在全部校验之后、返回之前——必炸的配置不会先留下声报级别的噪声日志。
    """
    raw = raw or {}
    g = GraphConfig()
    if raw.get("enabled") is not None:
        g.enabled = _as_bool(raw["enabled"])
    g.neo4j = _fill(Neo4jConfig(), raw.get("neo4j"))
    g.expansion = _fill(ExpansionConfig(), raw.get("expansion"))

    if "REPLACES" in g.expansion.edge_whitelist:
        raise ValueError(
            "graph.expansion.edge_whitelist 不允许包含 REPLACES：其语义已由版本消歧"
            "（rag_pipeline.policy）在检索层处理，进图扩展热路径会与准入/去重"
            "语义搅浑。请从白名单移除。"
        )

    if not (0 < g.expansion.decay < 1):
        raise ValueError(
            f"graph.expansion.decay 必须严格 0<decay<1（当前 {g.expansion.decay}）："
            "decay>=1 会使扩展分不低于源卡分，破坏『扩展分严格低于基础分』"
            "不变量；decay<=0 使扩展条目恒为 0 分。"
        )

    if not g.neo4j.password:
        dotenv = _load_dotenv()
        g.neo4j.password = (
            os.environ.get(g.neo4j.password_env)
            or dotenv.get(g.neo4j.password_env, "")
        )
    if g.enabled and not g.neo4j.password:
        raise ValueError(
            f"graph.enabled=true 但 Neo4j 凭证为空：请设置环境变量 "
            f"{g.neo4j.password_env}（或 .env 同名键），本地测试可在 "
            "graph.neo4j.password 直填（仅限本地）。"
        )

    if g.enabled and "REPLACES" not in g.expansion.edge_whitelist:
        # D-23 once-latch：policy 版本消歧热路径每次请求都 load_config()，这条
        # 设计说明同一进程只告警一次，避免每请求刷一条 WARNING（关图零告警不变）。
        global _whitelist_notice_latched
        if not _whitelist_notice_latched:
            _whitelist_notice_latched = True
            logging.getLogger(__name__).warning(
                "graph.expansion.edge_whitelist 不含 REPLACES：REPLACES 边不参与图扩展"
                "（由版本消歧在检索层处理），此为设计预期；如需其进热路径请先复核设计。"
            )
    return g


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
        graph=_build_graph_config(raw.get("graph")),
    )


def build_gate(rc: "RetrievalConfig") -> Dict[str, Any]:
    """把 RetrievalConfig 里的门控字段打包成 hybrid_rerank_search(gate=...) 的参数。"""
    return {
        "enabled": rc.gate_enabled,
        "min_score": rc.gate_min_score,
        "min_margin": rc.gate_min_margin,
        "conf_weights": tuple(rc.gate_conf_weights),
        "low_weights": tuple(rc.gate_low_weights),
    }


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
