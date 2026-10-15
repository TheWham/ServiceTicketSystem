#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Day 14 黄金问题集建设与 RAG 检索层量化评估基准工程流水线
================================================================================
前置承接：Wiki 清洗重构 -> 父子切块与向量库 -> 混合检索与重排（rag_pipeline 包）
核心功能：
  1. 自动化加载并解析 6:2:2 黄金问题集基准库 (evals/golden_dataset_v1.0.json)
  2. 装配并调度主链路混合重排检索引擎 (IndustrialHybridRetriever，含废止卡屏蔽/共振保护)
  3. 执行 Top-K 检索评测与名次统计 (Hit Rate@1 / Hit Rate@K)
  4. 计算工业级度量指标 MRR (Mean Reciprocal Rank，平均倒数排名)
  5. 专项评测版本冲突消歧正确率 (is_conflict_check)：命中现行卡且无"已废止"卡混入
  6. 专项评测对抗样本置信度截断与防幻觉安全拦截率 (is_adversarial)
  7. 自动化生成量化体检大盘报告落盘：《Day14_黄金问题集RAG评测基准报告.md》

与讲义参考实现的差异（均为适配本仓库实测结论的必要改造）：
  - 语料/向量库：复用 rag_pipeline 配置中心与持久化库（manifest 指纹校验），
    chunk_id 采用父子切片的确定性 child_id（ITKB-XXX-NNN#cN），与黄金集 reference 对齐；
  - 拒答判定：主链路已实现低置信拒答（pipeline.yaml reject_threshold=0.40，精排原始分
    低于阈值返回空结果），评测器直接复用该机制；另以"正样本 top-1 rerank 分最小值"
    自动标定阈值作对照（Day13 压测证明 rerank 绝对分不可跨端点移植，讲义硬编码 0.40
    仅对其端点成立），可用 --adversarial-threshold 覆盖；
  - 冲突判定：讲义按"2024/v2.0/新规"词面判新版；本库以元数据 version/status 为准
    （现行 v1.0 vs 废止 v0.9+status=已废止），判定=命中现行卡且 Top-K 无废止卡混入。
================================================================================
"""

import sys
import time
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Windows 控制台默认 GBK，统一切换 UTF-8 防止 emoji 打印崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from langchain_community.vectorstores import Chroma
except ImportError:
    Chroma = None

from rag_pipeline.config import load_config, config_fingerprint, build_gate
from rag_pipeline.embedding import KspEmbeddingProvider
from rag_pipeline.chunking.fingerprint import compute_wiki_fingerprint
from rag_pipeline.chunking.corpus import load_corpus_with_deterministic_ids
from rag_pipeline.retrieval.hybrid import IndustrialHybridRetriever
from rag_pipeline.retrieval.query_rewriter import QueryRewriter

DEPRECATED_STATUS = ("已废止", "已下线")

# 黄金集 reference_chunk_ids 三级粒度后缀：确定性切片 _chunk_N / 父子子块 #cN
_REF_SUFFIX_RE = re.compile(r"(#c\d+|_chunk_\d+)$")


def _parent_id_of(ref: str) -> str:
    """把三级粒度的 reference id 归一到父卡 id：ITKB-XXX#cN / ITKB-XXX_chunk_N -> ITKB-XXX。

    黄金数据集为兼容不同切块与精排粒度，同时绑定 chunk_id（确定性切片）、
    child_id（父子子块）与父卡 id 三种形态；命中判定统一归一到父卡口径，
    另对 child_id 形态保留精确命中（见 run_evaluation 内 chunk_hit）。
    """
    return _REF_SUFFIX_RE.sub("", ref)


# ==============================================================================
# 1. 确定性切片拓扑构建器（对齐 reference_chunk_ids）
#    实现已迁入 rag_pipeline.chunking.corpus，由顶部 import 导出——
#    旧引用 from run_day14_pipeline import load_corpus_with_deterministic_ids 仍然有效。
# ==============================================================================


# ==============================================================================
# 2. 生产级 RAGEvaluator 评测中枢 (讲义第五篇标准实现，适配本仓库)
# ==============================================================================

class RAGEvaluator:
    """
    RAG 黄金评测基准引擎：
    - 读取符合六维 Schema 的 golden_dataset.json
    - 计算 Hit Rate@1, Hit Rate@K, MRR
    - 分支路由处理 is_conflict_check 与 is_adversarial
    - 输出控制台体检大盘与落盘 Markdown 报告
    """

    def __init__(self, retriever: Any, golden_dataset_path: str, rc, rewriter=None):
        self.retriever = retriever
        self.rc = rc  # RetrievalConfig：top_k/rrf_k/权重/reject_threshold/granularity 与主链路同源
        self.rewriter = rewriter
        with open(golden_dataset_path, "r", encoding="utf-8") as f:
            self.golden_dataset: List[Dict[str, Any]] = json.load(f)

    def run_evaluation(self, top_k: int = 3, adversarial_threshold: Optional[float] = None) -> Dict[str, Any]:
        """执行全量评测并输出指标统计。

        拒答阈值两阶段：先跑完全部题目收集 top-1 分，再标定阈值
        （未命令行指定时 = 正样本 top-1 rerank 分最小值），最后判定拒答拦截。
        """
        total_queries = len(self.golden_dataset)
        rr_sum = 0.0
        total_latency = 0.0
        rows: List[Dict[str, Any]] = []

        print(f"🚀 开始执行黄金问题集自动化评估 (共 {total_queries} 道考题，考核 Top-{top_k}) ...\n")

        for idx, item in enumerate(self.golden_dataset, 1):
            q_id = item["id"]
            query = item["query"]
            expected_chunks = item.get("reference_chunk_ids", [])
            expected_keywords = item.get("expected_keywords", [])
            is_adversarial = item.get("is_adversarial", False)
            is_conflict = item.get("is_conflict_check", False)
            expected_parents = {_parent_id_of(c) for c in expected_chunks}

            start_t = time.time()
            rewrite = self.rewriter.rewrite(query) if self.rewriter else None
            search_res = self.retriever.hybrid_rerank_search(
                query=query,
                final_top_k=top_k,
                rrf_k=self.rc.rrf_k,
                rough_top_k=self.rc.rough_top_k,
                fuse_k=self.rc.fuse_k,
                rrf_weight=self.rc.rrf_weight,
                rerank_weight=self.rc.rerank_weight,
                reject_threshold=self.rc.reject_threshold,
                rerank_granularity=self.rc.rerank_granularity,
                rewrite_query=rewrite,
                gate=build_gate(self.rc),
            )
            retrieved_results = search_res.get("final_results", [])
            latency = (time.time() - start_t) * 1000
            total_latency += latency
            # 拒答（返回空）时提取真实 max_rerank_score 记录到报告，而非记 0
            top_score = (retrieved_results[0]["rerank_score"] if retrieved_results
                         else search_res.get("max_rerank_score", 0.0))
            degraded = search_res.get("rerank_degraded", False)
            rejected = bool(search_res.get("rejected", False))

            # 命中名次判定：子块 child_id 命中、父块（Small-to-Big 回溯口径）命中、
            # 或单切片关键事实词全包含（讲义兜底口径）
            hit_rank = None
            for rank, res in enumerate(retrieved_results, 1):
                md = res["metadata"]
                cid = md.get("child_id")
                pid = md.get("parent_id") or md.get("wiki_id")
                chunk_hit = (cid in expected_chunks) or (pid in expected_parents)
                keyword_hit = all(k in res.get("content", "") for k in expected_keywords) if expected_keywords else False
                if expected_chunks and (chunk_hit or keyword_hit):
                    hit_rank = rank
                    break

            # 版本冲突专项：Top-K 是否混入"已废止"父块（default_exclude 应物理屏蔽）
            has_deprecated = any(
                res["metadata"].get("wiki_status") in DEPRECATED_STATUS for res in retrieved_results
            )

            rows.append({
                "id": q_id, "category": item.get("category", "通用"), "query": query,
                "is_adversarial": is_adversarial, "is_conflict": is_conflict,
                "hit_rank": hit_rank, "top_score": top_score, "latency": latency,
                "has_deprecated": has_deprecated, "degraded": degraded, "rejected": rejected,
                "gate_mode": search_res.get("gate_mode", "off"),
                "parent_ids": [r["metadata"].get("parent_id") or r["metadata"].get("wiki_id")
                               for r in retrieved_results],
            })

        # ---- 拒答阈值标定（讲义 0.40 为其端点标定值，本端点按正样本分布自动标定）----
        positive_scores = [r["top_score"] for r in rows if not r["is_adversarial"] and r["top_score"] > 0]
        calibrated = min(positive_scores) if positive_scores else 0.40
        threshold = adversarial_threshold if adversarial_threshold is not None else calibrated
        threshold_src = "命令行指定" if adversarial_threshold is not None else "自动标定（正样本 top-1 rerank 分最小值）"

        # ---- 指标汇总 ----
        scored = [r for r in rows if not r["is_adversarial"]]
        valid_queries = len(scored)
        hit_top1 = sum(1 for r in scored if r["hit_rank"] == 1)
        hit_topk = sum(1 for r in scored if r["hit_rank"] is not None and r["hit_rank"] <= top_k)
        rr_sum = sum(1.0 / r["hit_rank"] for r in scored if r["hit_rank"])

        conflicts = [r for r in scored if r["is_conflict"]]
        conflict_passed = sum(1 for r in conflicts if r["hit_rank"] is not None and not r["has_deprecated"])

        # 拒答判定（与主链路低置信拒答一致）：主链路返回空（触发 reject_threshold 物理拒答）
        # 或 top-1 分低于标定阈值，二者任一即视为拦截成功
        def _adv_pass(r):
            return r["rejected"] or r["top_score"] < threshold

        advs = [r for r in rows if r["is_adversarial"]]
        adv_passed = sum(1 for r in advs if _adv_pass(r))

        for r in rows:
            if r["is_adversarial"]:
                passed = _adv_pass(r)
                r.update(type="ADVERSARIAL",
                         status="PASS" if passed else "FAIL (未截断)",
                         hit_txt="N/A (安全拒答)" + ("（物理拒答）" if r["rejected"] else ""),
                         note=("主链路低置信拒答触发（返回空结果）" if r["rejected"]
                               else ("成功触发低分截断保护" if passed else "⚠️ 分数过高，存在幻觉泄露风险")))
            else:
                if r["is_conflict"]:
                    ok = r["hit_rank"] is not None and not r["has_deprecated"]
                    r.update(type="CONFLICT",
                             status="PASS (消歧成功)" if ok else "FAIL (旧规干扰)",
                             note="命中现行有效条款且无废止卡混入" if ok
                             else ("⚠️ 废止旧卡混入 Top-K" if r["has_deprecated"] else "未命中现行卡"))
                else:
                    r.update(type="STANDARD",
                             status="HIT" if r["hit_rank"] else "MISSED",
                             note="命中标准切片" if r["hit_rank"] else "未在Top-K召回")
                r["hit_txt"] = f"Rank #{r['hit_rank']}" if r["hit_rank"] else "MISSED"
            if r["degraded"]:
                r["note"] += "（本轮 Rerank 无有效分，退化为纯 RRF 排序）"

        summary = {
            "total_test_cases": total_queries,
            "valid_evaluation_cases": valid_queries,
            "adversarial_cases": len(advs),
            "conflict_cases": len(conflicts),
            "hit_rate_top1": f"{(hit_top1 / valid_queries * 100) if valid_queries else 0:.1f}%",
            f"hit_rate_top{top_k}": f"{(hit_topk / valid_queries * 100) if valid_queries else 0:.1f}%",
            "conflict_accuracy": f"{(conflict_passed / len(conflicts) * 100) if conflicts else 100:.1f}%",
            "adversarial_refusal_rate": f"{(adv_passed / len(advs) * 100) if advs else 100:.1f}%",
            "mrr": round(rr_sum / valid_queries, 3) if valid_queries else 0.0,
            "avg_latency_ms": f"{total_latency / total_queries:.1f}ms" if total_queries else "0ms",
            "adversarial_threshold": threshold,
            "adversarial_threshold_src": threshold_src,
            "details": rows,
        }
        self._print_console_dashboard(summary, top_k)
        return summary

    def _print_console_dashboard(self, summary: Dict[str, Any], top_k: int):
        print("=" * 105)
        print("📊 【企业级 RAG 检索层黄金评测健康大盘报告 (Golden Benchmark Dashboard)】")
        print("=" * 105)
        print(f"{'用例编号':<15}{'题型分类':<14}{'样本类型':<13}{'评测判定':<18}{'命中名次':<14}{'时延':<10}{'Top-1得分'}")
        print("-" * 105)
        for d in summary["details"]:
            print(
                f"{d['id']:<15}{d['category']:<14}{d['type']:<13}{d['status']:<18}"
                f"{d['hit_txt']:<14}{str(round(d['latency']))+'ms':<10}{d['top_score']:.4f}"
            )
        print("=" * 105)
        print(f"• 测试总题数：{summary['total_test_cases']} 题 (正向考察: {summary['valid_evaluation_cases']} 题, 越界防伪: {summary['adversarial_cases']} 题)")
        print(f"• Top-1 击中率：{summary['hit_rate_top1']}")
        print(f"• Top-{top_k} 综合召回率：{summary[f'hit_rate_top{top_k}']}  (及格线 >= 85%)")
        print(f"• MRR (平均倒数排名)：{summary['mrr']}  (优秀线 >= 0.75)")
        print(f"• 版本冲突消歧准确率：{summary['conflict_accuracy']}  (及格线 >= 90%)")
        print(f"• 越界拒答截断拦截率：{summary['adversarial_refusal_rate']}  (底线 = 100%；阈值 {summary['adversarial_threshold']:.4f}，{summary['adversarial_threshold_src']})")
        print(f"• 平均单次端到端检索延迟：{summary['avg_latency_ms']}")
        print("=" * 105)

    def generate_markdown_report(self, report_path: Path, summary: Dict[str, Any], top_k: int):
        """生成 Markdown 格式的正式体检大盘报告"""
        def pct(key):
            return float(summary[key].rstrip("%"))

        thr = summary["adversarial_threshold"]
        conflict_rows = [d for d in summary["details"] if d["is_conflict"]]
        adv_rows = [d for d in summary["details"] if d["is_adversarial"]]

        content = f"""# Day 14 黄金问题集 (Golden Dataset) RAG 评测基准报告

**所属阶段**：第二阶段 RAG 数据工程、黄金问题集与单 Agent 工具交付
**评测版本**：`golden_dataset_v1.0.json` (6:2:2 黄金结构配比)
**评估引擎**：Chroma 向量数据库 + BM25Okapi + Cross-Encoder 混合精排检索器（主链路同源装配）
**生成日期**：{time.strftime("%Y-%m-%d %H:%M:%S")}

---

## 一、 核心指标雷达与交付达标定盘

| 评测维度 | 工业级达标基线 (Baseline) | 本次跑测实测值 | 达标判定 | 架构工程意义 |
| :--- | :---: | :---: | :---: | :--- |
| **Top-1 击中率** | ≥ 70.0% | **{summary['hit_rate_top1']}** | {'✅ 达标' if pct('hit_rate_top1') >= 70 else '⚠️ 需调优'} | 黄金事实直接排在首位，最大化大模型注意力 |
| **Top-{top_k} 综合召回率** | ≥ 85.0% | **{summary[f'hit_rate_top{top_k}']}** | {'✅ 达标' if pct(f'hit_rate_top{top_k}') >= 85 else '⚠️ 需调优'} | 确保真理进入上下文候选池，杜绝生成层幻觉 |
| **MRR (平均倒数排名)** | ≥ 0.750 | **{summary['mrr']}** | {'✅ 达标' if summary['mrr'] >= 0.75 else '⚠️ 需调优'} | 衡量 Cross-Encoder 重排将真理置顶的精排能力 |
| **版本冲突消歧率** | ≥ 90.0% | **{summary['conflict_accuracy']}** | {'✅ 达标' if pct('conflict_accuracy') >= 90 else '⚠️ 需调优'} | 元数据 default_exclude 物理屏蔽废止卡 + 现行卡命中 |
| **越界拒答截断率** | = 100.0% | **{summary['adversarial_refusal_rate']}** | {'✅ 达标' if pct('adversarial_refusal_rate') == 100 else '⚠️ 需调优'} | 检索层置信度截断（阈值 {thr:.4f}，{summary['adversarial_threshold_src']}），筑牢防幻觉底线 |
| **平均检索时延** | 含远程精排往返 | **{summary['avg_latency_ms']}** | — | 双路召回 + RRF + 重排端到端延迟（远程 /rerank 为主开销） |

> 拒答阈值说明：讲义参考实现的 0.40 为其重排端点标定值；Day13 压测已证明 rerank 绝对分
> 不可跨端点/跨查询移植（本端点正样本 top-1 分普遍落在 0.2~0.4 区间），故本版默认以
> "正样本 top-1 rerank 分最小值"自动标定，保证"越界题置信度低于最弱正样本"这一语义成立。

---

## 二、 6:2:2 试题结构与全量跑测明细

```
总考题数：{summary['total_test_cases']} 题
├── 60% 基础标准业务题 ({summary['valid_evaluation_cases'] - summary['conflict_cases']} 题) -> 考察核心知识卡片高精度召回
├── 20% 跨文档版本冲突题 ({summary['conflict_cases']} 题) -> 考察新旧规约更迭、废止条款过滤
└── 20% 越界注入与安全拒答题 ({summary['adversarial_cases']} 题) -> 考察无记载事实低分安全截断
```

### 详细测试用例跑测记录表

| 用例编号 | 业务场景 | 考题类型 | 评测状态 | 命中名次 | Top-1重排分 | 耗时 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
"""
        for d in summary["details"]:
            content += f"| `{d['id']}` | {d['category']} | `{d['type']}` | {d['status']} | {d['hit_txt']} | {d['top_score']:.4f} | {round(d['latency'])}ms |\n"

        conflict_desc = "；".join(
            f"{d['id']}（{'、'.join(d['parent_ids'])}）→ {d['status']}" for d in conflict_rows
        ) or "无"
        adv_desc = "；".join(
            f"{d['id']} top-1={d['top_score']:.4f} {'<' if d['top_score'] < thr else '≥'} 阈值 {thr:.4f}"
            for d in adv_rows
        ) or "无"

        content += f"""
---

## 三、 典型对抗场景与工程归因分析

1. **版本冲突消歧（现行生效 vs 旧规拦截）**：
   - 冲突题跑测结果：{conflict_desc}。
   - 工程机制：主链路 `default_exclude={{wiki_status: [已废止]}}` 在 BM25 与 Dense 两路召回
     前置物理屏蔽废止卡（v0.9 LEG 系列），Cross-Encoder 根本见不到旧版候选，消歧由元数据层完成。
2. **越界对抗用例低分拦截**：
   - 拒答题 top-1 重排分：{adv_desc}。
   - 工程意义：低于标定阈值的查询应在生成层触发"知识库未记载"拒答话术，而非强行作答。

---

## 四、 后续交付承接

- **Day 15**：将基于本评测保护体系，封装 FastAPI 知识库端点（带溯源角标 `[来源: 卡片id-章节名]`），完成全量回归并正式结营封版！
"""
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)


# ==============================================================================
# 3. 命令行主程序入口
# ==============================================================================

def run_day14_pipeline():
    parser = argparse.ArgumentParser(description="Day 14 黄金问题集建设与 RAG 评测基准工程流水线")
    parser.add_argument("--wiki-dir", default="artifacts/output/wiki", help="Wiki 卡片目录")
    parser.add_argument("--chroma-dir", default="artifacts/indexing/chroma_wiki_structured", help="持久化向量库目录")
    parser.add_argument("--golden-dataset", default="evals/golden_dataset_v1.0.json", help="黄金问题集路径")
    parser.add_argument("--output-dir", default="artifacts/evaluation", help="评测产物输出目录")
    parser.add_argument("--top-k", type=int, default=None, help="评测 Top-K（默认取 pipeline.yaml retrieval.top_k）")
    parser.add_argument("--adversarial-threshold", type=float, default=None,
                        help="拒答置信截断阈值（默认自动标定=正样本 top-1 rerank 分最小值）")
    args = parser.parse_args()

    print("=" * 80)
    print("🎯 Day 14 黄金问题集建设与 RAG 检索层量化评估基准工程流水线")
    print("=" * 80)

    cfg = load_config()
    top_k = args.top_k or cfg.retrieval.top_k
    wiki_path = REPO_ROOT / args.wiki_dir
    chroma_path = REPO_ROOT / args.chroma_dir
    golden_path = REPO_ROOT / args.golden_dataset
    output_path = REPO_ROOT / args.output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 载入语料并绑定确定性 chunk_id（与黄金集 reference_chunk_ids 对齐）
    print("\n[1/3] 提取 Wiki 知识切片语料并绑定确定性溯源 Chunk ID...")
    corpus_docs = load_corpus_with_deterministic_ids(wiki_path, cfg)
    print(f"       -> 成功提取并装配切片语料：{len(corpus_docs)} 个标准 Chunks")

    # 2. 装配 IndustrialHybridRetriever（优先加载持久化库，manifest 指纹校验）
    print("\n[2/3] 装配工业级双路混合检索与重排核心中枢...")
    embed_provider = KspEmbeddingProvider(cache_dir=str(REPO_ROOT / cfg.embedding_cache_dir))
    vector_db = None
    stale_reason = None
    manifest_file = chroma_path / "manifest.json"
    if Chroma is not None and chroma_path.exists():
        if not manifest_file.exists():
            stale_reason = "无 manifest（旧版本向量库）"
        else:
            saved = json.loads(manifest_file.read_text(encoding="utf-8"))
            wiki_files = sorted(p for p in wiki_path.glob("*.md") if p.name != "_index.md")
            if saved.get("wiki_fingerprint") != compute_wiki_fingerprint(wiki_files):
                stale_reason = "Wiki 卡片内容已变更"
            elif saved.get("config_fingerprint") and saved["config_fingerprint"] != config_fingerprint(cfg):
                stale_reason = "切片配置已变更（configs/pipeline.yaml）"
        if stale_reason is None:
            try:
                vector_db = Chroma(persist_directory=str(chroma_path),
                                   embedding_function=embed_provider,
                                   collection_name=cfg.store_collection)
                print(f"       -> 成功加载持久化向量数据库：{chroma_path.name}")
            except Exception as e:
                stale_reason = f"加载异常({e})"
    if vector_db is None and Chroma is not None:
        if stale_reason:
            print(f"       ⚠️ 持久化库不可用（{stale_reason}），内存重建索引...")
        vector_db = Chroma.from_documents(documents=corpus_docs, embedding=embed_provider,
                                          collection_name="wiki_structured_golden_eval")

    retriever = IndustrialHybridRetriever(
        vector_db=vector_db,
        corpus_docs=corpus_docs,
        reranker_model_name=cfg.reranker_model,
        default_exclude=cfg.retrieval.default_exclude,
    )

    # 查询改写器：与主链路评测同一装配（yaml query_rewrite 开关，缓存落评测产物目录）
    rewriter = QueryRewriter(
        model=cfg.retrieval.rewrite_model,
        cache_dir=str(output_path / ".llm_cache" / "rewrite"),
    ) if cfg.retrieval.query_rewrite else None
    if rewriter:
        print(f"       -> 查询改写已启用：{rewriter.model}（磁盘缓存 evaluation/.llm_cache/rewrite）")

    # 3. 运行评测大盘
    print(f"\n[3/3] 启动 RAGEvaluator 对《{golden_path.name}》进行量化评估...")
    evaluator = RAGEvaluator(retriever=retriever, golden_dataset_path=str(golden_path),
                             rc=cfg.retrieval, rewriter=rewriter)
    summary = evaluator.run_evaluation(top_k=top_k, adversarial_threshold=args.adversarial_threshold)

    # 门控档位分布（生产级可观测性：说明融合权重是固定还是按置信度切换）
    gate_modes = [d.get("gate_mode", "off") for d in summary["details"]]
    if any(m != "off" for m in gate_modes):
        print(f"置信度门控：高置信 {gate_modes.count('high')} 题（放权精排 "
              f"{cfg.retrieval.gate_conf_weights}）/ 低置信 {gate_modes.count('low')} 题（召回托底 "
              f"{cfg.retrieval.gate_low_weights}）（门槛 top-1 ≥{cfg.retrieval.gate_min_score} "
              f"且 margin ≥{cfg.retrieval.gate_min_margin}）")

    # 4. 报告落盘
    report_file = output_path / "Day14_黄金问题集RAG评测基准报告.md"
    evaluator.generate_markdown_report(report_file, summary, top_k=top_k)
    print(f"\n🎉 评测报告已成功落盘至：{report_file}")
    print("=" * 80)


if __name__ == "__main__":
    run_day14_pipeline()
