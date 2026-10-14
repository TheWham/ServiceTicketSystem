"""
重排服务验收探针：换供应商/换模型后先跑它，再跑 Day13 评测。

检查三件事（对应讲义 6.6 的两次踩坑）：
  1. 端点与响应格式：实际命中哪个 URL、返回哪种格式；
  2. 可复现性：同一输入连调 3 次，分数是否一致；
  3. 判别力扰动：只去掉文档末尾换行，分数是否大幅变化——
     合格的 Cross-Encoder 应几乎不变；KSP 网关 Jina 那一路曾因此 0.78→0.37。

运行：python probe_reranker.py
"""

import sys
from pathlib import Path

from rag_pipeline.config import load_config, build_chunker
from rag_pipeline.embedding import load_rerank_config
from rag_pipeline.retrieval.reranker import KspReranker

sys.stdout.reconfigure(encoding="utf-8")

QUERY = "网页打不开但QQ正常，IT排查DNS时，要检查防火墙是否拦截了哪个端口？"
CARDS = ["ITKB-NET-004", "ITKB-SYS-005", "ITKB-MAIL-003", "ITKB-VPN-002"]  # 第一张为正确答案


def main():
    rc = load_rerank_config()
    cfg = load_config()
    print(f"供应商: {rc['provider']}  模型: {rc['model'] or cfg.reranker_model}")
    rr = KspReranker(model_name=rc["model"] or cfg.reranker_model, cfg=rc, backend=cfg.reranker_backend)
    if not rr.available:
        print("❌ 重排服务不可用，检查 .env 中 RERANK_BASE_URL / RERANK_API_KEY / RERANK_MODEL")
        return 1

    chunker, _ = build_chunker(cfg)
    parents = {}
    for f in sorted(Path("output/wiki").glob("ITKB-*.md")):
        p, children = chunker.split_wiki_document(str(f))
        parents[children[0].metadata["parent_id"]] = p.page_content
    docs = [parents[c] for c in CARDS]

    print(f"端点: {rr.endpoint}\n")
    runs = [rr._call_api(QUERY, docs) for _ in range(3)]
    for i, s in enumerate(runs):
        print(f"第{i + 1}次: " + "  ".join(f"{c}={v:.4f}" for c, v in zip(CARDS, s)))
    drift = max(max(abs(a - b) for a, b in zip(runs[0], r)) for r in runs[1:])

    stripped = rr._call_api(QUERY, [d.rstrip() for d in docs])
    print("去文末换行: " + "  ".join(f"{c}={v:.4f}" for c, v in zip(CARDS, stripped)))
    perturb = max(abs(a - b) for a, b in zip(runs[0], stripped))

    top_ok = max(range(len(CARDS)), key=lambda i: runs[0][i]) == 0
    print()
    print(f"{'✅' if drift < 0.02 else '❌'} 可复现性：3 次最大差 {drift:.4f}（< 0.02 合格）")
    print(f"{'✅' if perturb < 0.05 else '❌'} 扰动敏感度：去换行最大差 {perturb:.4f}（< 0.05 合格）")
    print(f"{'✅' if top_ok else '❌'} 排序：正确卡 {CARDS[0]} {'排第 1' if top_ok else '未排第 1'}")
    return 0 if (drift < 0.02 and perturb < 0.05 and top_ok) else 2


if __name__ == "__main__":
    sys.exit(main())
