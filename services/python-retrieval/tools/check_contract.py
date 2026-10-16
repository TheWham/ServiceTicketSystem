#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_contract.py — rag_service 对外契约运行时校验（HTTP 黑盒）

逐条断言 consultation-service `RagServiceKnowledgeRetriever.parse` 强校验的不变量，
外加两项服务化专属要求：
  - content 必须取到整卡全文（parent_content），长度显著大于子块预算（防"半截卡"回归）；
  - 检索打满时 /api/health 仍须秒回，且锁等待不得把并发请求排队几十秒（5031 快速失败）。

用法：
    python tools/check_contract.py
    python tools/check_contract.py --base http://127.0.0.1:8310
"""

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PASS, FAIL = [], []


def check(name: str, ok: bool, detail: str = ""):
    (PASS if ok else FAIL).append(name)
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name}" + (f" — {detail}" if detail and not ok else ""))


def post(base: str, path: str, payload: dict, timeout: float = 30.0):
    req = urllib.request.Request(
        base + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}


def get(base: str, path: str, timeout: float = 10.0):
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {}


def main():
    parser = argparse.ArgumentParser(description="rag_service 契约校验")
    parser.add_argument("--base", default="http://127.0.0.1:8310")
    parser.add_argument("--golden", default="evals/golden_dataset_v1.0.json")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    golden = json.loads((REPO_ROOT / args.golden).read_text(encoding="utf-8"))
    positive = next(q for q in golden if not q.get("is_adversarial"))
    adversarial = next(q for q in golden if q.get("is_adversarial"))

    print(f"\n[1/6] /api/health 自检（含在线预算回显）—— {base}")
    status, health = get(base, "/api/health")
    check("health 200", status == 200, f"status={status}")
    check("health.status ∈ {UP, DEGRADED}", health.get("status") in ("UP", "DEGRADED"),
          str(health.get("status")))
    print(f"  ℹ️ health.status = {health.get('status')}"
          f"（DEGRADED = 尚未灌库，映射未加载；灌库后应为 UP）")
    check("rerankWaitBudget == 1.5（在线已收紧）", health.get("rerankWaitBudget") == 1.5,
          str(health.get("rerankWaitBudget")))
    check("rerankMaxRetries == 8（在线已收紧）", health.get("rerankMaxRetries") == 8,
          str(health.get("rerankMaxRetries")))
    check("health 携带 mappingLoaded", "mappingLoaded" in health)
    check("health 携带 chunkCount>0", isinstance(health.get("chunkCount"), int) and health["chunkCount"] > 0)
    check("rerank 远程可用", health.get("rerankAvailable") is True, str(health.get("rerankAvailable")))

    print(f"\n[2/6] 正向检索契约（{positive['id']}）")
    status, env = post(base, "/api/v1/rag/retrievals",
                       {"question": positive["query"], "topK": 3})
    check("HTTP 200", status == 200, f"status={status}")
    check("code == 0", env.get("code") == 0, str(env.get("code")))
    check("msg == success", env.get("msg") == "success", str(env.get("msg")))
    data = env.get("data") or {}
    items = data.get("items") or []
    check("domain == OFFICE_IT", data.get("domain") == "OFFICE_IT", str(data.get("domain")))
    check("publishedOnly == true", data.get("publishedOnly") is True)
    check("reliable == true", data.get("reliable") is True)
    check("suggestedReplyType == ANSWER", data.get("suggestedReplyType") == "ANSWER",
          str(data.get("suggestedReplyType")))
    check("suggestedRefusalReason 缺省", "suggestedRefusalReason" not in data)
    check("items 非空且 ≤ topK", 1 <= len(items) <= 3, f"items={len(items)}")

    for i, it in enumerate(items):
        tag = f"items[{i}]"
        check(f"{tag}.chunkId 非空白", bool((it.get("chunkId") or "").strip()))
        check(f"{tag}.chunkId 为 #cN 形态", "#c" in (it.get("chunkId") or ""), str(it.get("chunkId")))
        for field in ("articleId", "versionId", "indexVersion", "title", "snippet", "content"):
            check(f"{tag}.{field} 非空白", bool((it.get(field) or "").strip()), repr(it.get(field))[:40])
        check(f"{tag}.indexVersion == versionId", it.get("indexVersion") == it.get("versionId"))
        check(f"{tag}.score ∈ [0,1]", isinstance(it.get("score"), (int, float)) and 0 <= it["score"] <= 1,
              str(it.get("score")))
        check(f"{tag}.snippet ≤ 1000", len(it.get("snippet") or "") <= 1000,
              str(len(it.get("snippet") or "")))
        # 整卡全文 vs 子块：本语料子块 200~280 字符、整卡 570~910 字符（最短卡 ACC-002=568），
        # 故 >550 即证明取到 parent_content 而非子块 page_content。
        check(f"{tag}.content 取到整卡全文（>550 字符，非子块半截）",
              len(it.get("content") or "") > 550, str(len(it.get("content") or "")))

    if items:
        scores = [it["score"] for it in items]
        check("topScore == max(items.score)", data.get("topScore") == max(scores),
              f"topScore={data.get('topScore')} max={max(scores)}")
    else:
        check("topScore 存在", "topScore" in data)

    print(f"\n[3/6] 拒答契约（{adversarial['id']}）")
    status, env = post(base, "/api/v1/rag/retrievals",
                       {"question": adversarial["query"], "topK": 3})
    check("HTTP 200", status == 200, f"status={status}")
    check("code == 0", env.get("code") == 0)
    data = env.get("data") or {}
    check("items 为空", data.get("items") == [], str(data.get("items"))[:60])
    check("reliable == false", data.get("reliable") is False)
    check("suggestedReplyType == REFUSE", data.get("suggestedReplyType") == "REFUSE",
          str(data.get("suggestedReplyType")))
    check("suggestedRefusalReason == LOW_CONFIDENCE",
          data.get("suggestedRefusalReason") == "LOW_CONFIDENCE",
          str(data.get("suggestedRefusalReason")))
    check("topScore == 0.0", data.get("topScore") == 0.0, str(data.get("topScore")))
    check("publishedOnly == true", data.get("publishedOnly") is True)

    print("\n[4/6] topK 上限钳制（topK=20）")
    status, env = post(base, "/api/v1/rag/retrievals",
                       {"question": positive["query"], "topK": 20})
    items = (env.get("data") or {}).get("items") or []
    check("items ≤ 20", len(items) <= 20, str(len(items)))

    print("\n[5/6] 非法请求（question 缺失）")
    status, env = post(base, "/api/v1/rag/retrievals", {"topK": 3})
    check("HTTP 4xx", 400 <= status < 500, f"status={status}")
    check("code != 0", env.get("code") != 0, str(env.get("code")))

    print("\n[6/6] 并发与锁：健康检查不抢锁 + 锁等待快速失败（不排队）")
    lock_wait = float(health.get("lockWaitSeconds") or 1.0)
    token = str(time.time_ns())
    results = []
    health_latency = []

    def worker(idx):
        q = f"{positive['query']} 并发探针{token}{idx}"
        t0 = time.time()
        st, body = post(base, "/api/v1/rag/retrievals", {"question": q, "topK": 3}, timeout=60)
        results.append((st, (body or {}).get("code"), round(time.time() - t0, 3)))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    t_start = time.time()
    for t in threads:
        t.start()
    time.sleep(0.15)
    th0 = time.time()
    h_status, _ = get(base, "/api/health", timeout=5)
    health_latency.append(round(time.time() - th0, 3))
    for t in threads:
        t.join()
    total = round(time.time() - t_start, 3)

    check("并发请求全部返回", len(results) == 3, str(results))
    check("并发请求状态 ∈ {200/code0, 503/code5031}",
          all((st == 200 and code == 0) or (st == 503 and code == 5031) for st, code, _ in results),
          str(results))
    check("检索打满时 health 仍秒回（<1.0s）", health_latency[0] < 1.0, f"{health_latency[0]}s")
    fast_fail = [el for st, code, el in results if code == 5031]
    if fast_fail:
        check(f"5031 快速失败（≤ 锁等待 {lock_wait}s + 0.8s 余量）",
              max(fast_fail) <= lock_wait + 0.8, f"max={max(fast_fail)}s")
    else:
        print(f"  ℹ️ 本轮并发未触发锁竞争（3 请求均成功，总耗时 {total}s）——非失败项")
    check("无请求排队超过 30s", all(el < 30 for _, _, el in results), str(results))

    print(f"\n{'=' * 72}")
    print(f"契约校验结果：{len(PASS)} 通过 / {len(FAIL)} 失败")
    if FAIL:
        print("失败项：")
        for name in FAIL:
            print(f"  ❌ {name}")
        return 1
    print("🎉 全部契约不变量通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
