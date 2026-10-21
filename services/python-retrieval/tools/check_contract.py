#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_contract.py — rag_service 对外契约运行时校验（HTTP 黑盒）

逐条断言 consultation-service `RagServiceKnowledgeRetriever.parse` 强校验的不变量，
外加三项服务化专属要求：
  - content 必须取到整卡全文（parent_content），长度显著大于子块预算（防"半截卡"回归）；
  - 检索打满时 /api/health 仍须秒回，且锁等待不得把并发请求排队几十秒（5031 快速失败）；
  - `/api/v1/policy/resolve`（版本消歧）：它没有 Java 消费方，但同样是本服务对外的
    HTTP 契约。核心断言是**分水岭**——同一主题在两个日期必须给出不同版本；
    同时校验「非 RESOLVED 态不返回半截结论」与参数校验。

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

    print(f"\n[1/7] /api/health 自检（含在线预算回显）—— {base}")
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

    print(f"\n[2/7] 正向检索契约（{positive['id']}）")
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

    print(f"\n[3/7] 拒答契约（{adversarial['id']}）")
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

    print("\n[4/7] topK 上限钳制（topK=20）")
    status, env = post(base, "/api/v1/rag/retrievals",
                       {"question": positive["query"], "topK": 20})
    items = (env.get("data") or {}).get("items") or []
    check("items ≤ 20", len(items) <= 20, str(len(items)))

    print("\n[5/7] 非法请求（question 缺失）")
    status, env = post(base, "/api/v1/rag/retrievals", {"topK": 3})
    check("HTTP 4xx", 400 <= status < 500, f"status={status}")
    check("code != 0", env.get("code") != 0, str(env.get("code")))

    print("\n[6/7] 并发与锁：健康检查不抢锁 + 锁等待快速失败（不排队）")
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

    print("\n[7/7] 版本消歧契约（/api/v1/policy/resolve）")
    # 这个端点没有 Java 消费方，但它同样是本服务对外的 HTTP 契约，一并黑盒校验。
    # 核心断言是**分水岭**：同一主题在两个日期必须给出不同版本，否则这个端点没有存在意义。
    FOUR_STATES = {"RESOLVED", "NO_EFFECTIVE_VERSION", "UNDATED", "NO_MATCH"}
    st_old, env_old = post(base, "/api/v1/policy/resolve",
                           {"query": "域账号锁定 解锁", "at": "2024-01-15", "topK": 6})
    st_new, env_new = post(base, "/api/v1/policy/resolve",
                           {"query": "域账号锁定 解锁", "at": "2024-06-01", "topK": 6})
    d_old, d_new = env_old.get("data") or {}, env_new.get("data") or {}

    check("HTTP 200", st_old == 200 and st_new == 200, f"{st_old}/{st_new}")
    check("code == 0", env_old.get("code") == 0 and env_new.get("code") == 0,
          f"{env_old.get('code')}/{env_new.get('code')}")
    check("status ∈ 四态",
          d_old.get("status") in FOUR_STATES and d_new.get("status") in FOUR_STATES,
          f"{d_old.get('status')}/{d_new.get('status')}")
    check("分水岭两侧命中**不同**版本（相同则消歧失效）",
          d_old.get("articleId") is not None and d_old.get("articleId") != d_new.get("articleId"),
          f"old={d_old.get('articleId')} new={d_new.get('articleId')}"
          "（相同通常意味着语料里的演示版本链丢了，见 runbook）")

    for label, d in (("旧规", d_old), ("新规", d_new)):
        ck = d.get("citation") or ""
        check(f"{label} citation 形如 [来源: 卡号@版本 《标题》]",
              ck.startswith("[来源: ") and "@" in ck and "《" in ck, ck[:60])
        check(f"{label} articleId/version/effectiveDate 均非空",
              all(d.get(k) for k in ("articleId", "version", "effectiveDate")), str(d)[:60])
    check("旧规 supersededAt 非空（已被取代）", bool(d_old.get("supersededAt")),
          str(d_old.get("supersededAt")))
    check("新规 supersededAt 为空（现行）", d_new.get("supersededAt") is None,
          str(d_new.get("supersededAt")))
    check("chain 至少含新旧两版", len(d_new.get("chain") or []) >= 2,
          str(len(d_new.get("chain") or [])))

    # 非 RESOLVED 态不得带出半截结论：三字段要么齐、要么全空（不让人从「字段为空」反推结论）
    st_un, env_un = post(base, "/api/v1/policy/resolve",
                         {"query": "打印机脱机无法打印", "at": "2024-06-01"})
    d_un = env_un.get("data") or {}
    check("非 RESOLVED 态三字段必须同时为 null（不返回半截结论）",
          d_un.get("status") == "RESOLVED"
          or (d_un.get("citation") is None and d_un.get("articleId") is None
              and d_un.get("version") is None),
          f"status={d_un.get('status')} citation={d_un.get('citation')!r}")
    check("UNDATED/NO_MATCH 是结论不是失败（HTTP 200 + code 0）",
          d_un.get("status") in ("RESOLVED", "NO_EFFECTIVE_VERSION", "UNDATED", "NO_MATCH")
          and st_un == 200 and env_un.get("code") == 0,
          f"status={st_un} code={env_un.get('code')}")

    st_noq, env_noq = post(base, "/api/v1/policy/resolve", {"topK": 6})
    check("缺 query → HTTP 4xx", 400 <= st_noq < 500, f"status={st_noq}")
    check("缺 query → code != 0", env_noq.get("code") != 0, str(env_noq.get("code")))
    st_topk, _ = post(base, "/api/v1/policy/resolve", {"query": "VPN", "topK": 99})
    check("topK 越界 → HTTP 4xx", 400 <= st_topk < 500, f"status={st_topk}")

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
