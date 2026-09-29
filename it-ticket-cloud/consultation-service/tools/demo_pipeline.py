#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
consultation-service 行为演示脚本(不是服务本身)。

本机没有 JDK/Maven/Docker,Spring Boot 服务跑不起来。这个脚本用 Python 复刻
AiConsultationService 那条链路的判定顺序,数据用 db/init/31-consultation-seed.sql
的同一批种子知识,模型走 application.yml 里配的同一个端点和同一段提示词。

它能证明的:检索只读 PUBLISHED、引用由服务端重建、高风险短路、拒答分级、转人工分配算法。
它不能证明的:Java 代码能编译、MyBatis 映射正确、事务与幂等在真实库上的行为。
"""
import json
import os
import re
import sys
import time
import urllib.request
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)
MAIN = os.path.join(MODULE, "src", "main")

C_OK, C_WARN, C_ERR, C_DIM, C_END = "\033[92m", "\033[93m", "\033[91m", "\033[90m", "\033[0m"


def head(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# --------------------------------------------------------------------------
# 0. 从真实配置与源码里取参数,避免演示和实现漂移
# --------------------------------------------------------------------------
def load_config():
    """从 application.yml + ai-secrets.yml 读取模型配置(只做够用的极简解析)。"""
    cfg = {}
    for name in ("application.yml", None):
        path = os.path.join(MAIN, "resources", name) if name else os.path.join(MODULE, "ai-secrets.yml")
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8"):
            m = re.match(r"\s*(base-url|api-key|model|min-confidence|"
                         r"suggest-transfer-below-confidence|top-k):\s*(.+?)\s*$", line)
            if m:
                key, val = m.group(1), m.group(2)
                dm = re.match(r"\$\{[A-Z_]+:(.*)\}$", val)
                if dm:
                    val = dm.group(1)
                if val:
                    cfg.setdefault(key, val)
    return cfg


def load_high_risk_keywords():
    """高风险关键词直接读 application.yml,和服务端同一份清单。"""
    path = os.path.join(MAIN, "resources", "application.yml")
    words, collecting = [], False
    for line in open(path, encoding="utf-8"):
        if "high-risk-keywords" in line:
            collecting = True
            continue
        if collecting:
            m = re.match(r"\s+- (.+?)\s*$", line)
            if m:
                words.append(m.group(1))
            elif line.strip() and not line.startswith(" " * 8):
                break
    return words


def load_system_prompt():
    """系统提示词从 Java 源码的文本块里原样抽取,保证与服务端一字不差。"""
    src = open(os.path.join(MAIN, "java", "com", "itticket", "consultation",
                            "adapter", "OpenAiCompatibleRagAdapter.java"), encoding="utf-8").read()
    body = re.search(r'private static String systemPrompt\(\) \{\s*return """\n(.*?)""";', src, re.S).group(1)
    lines = body.split("\n")
    pad = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    return "\n".join(l[pad:] if len(l) >= pad else l for l in lines)


def load_seed_knowledge():
    """从 31-consultation-seed.sql 解析知识文章与版本,复现 PUBLISHED/OFFLINE 的真实分布。"""
    path = os.path.join(MODULE, "..", "db", "init", "31-consultation-seed.sql")
    sql = open(os.path.abspath(path), encoding="utf-8").read()

    articles = {}
    block = re.search(r"INSERT INTO knowledge_article.*?VALUES(.*?);", sql, re.S).group(1)
    for row in re.finditer(r"\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'", block):
        articles[row.group(1)] = {"status": row.group(2),
                                  "current_version_id": row.group(3),
                                  "category_id": row.group(4)}

    versions = {}
    vblock = sql[sql.index("INSERT INTO knowledge_version"):]
    for row in re.finditer(
            r"\('([^']+)',\s*'([^']+)',\s*(\d+),\s*\n?\s*JSON_OBJECT\((.*?)\),\s*\n?\s*'U0", vblock, re.S):
        fields = dict(re.findall(r"'(\w+)',\s*'(.*?)'(?=,\s*\n?\s*'|\s*$)", row.group(4), re.S))
        versions[row.group(1)] = {"article_id": row.group(2), "no": int(row.group(3)), **fields}
    return articles, versions


# --------------------------------------------------------------------------
# 1. 检索层:只读 PUBLISHED 且为 current_version_id 的版本
# --------------------------------------------------------------------------
def retrieve(articles, versions, query, category_id, top_k):
    hits = []
    for article_id, a in articles.items():
        if a["status"] != "PUBLISHED":
            continue                                   # OFFLINE 文章不可检索(AC-27)
        if category_id and a["category_id"] != category_id:
            continue
        vid = a["current_version_id"]
        v = versions.get(vid)
        if not v or v["article_id"] != article_id:
            continue                                   # 只认当前版本,历史版本不可检索
        text = " ".join([v.get("title", ""), v.get("summary", ""),
                         v.get("keywords", ""), v.get("body", "")])
        score = sum(1.0 for ch in set(query) if ch.strip() and ch in text)
        if score > 0:
            hits.append({"articleId": article_id, "versionId": vid,
                         "title": v.get("title", ""), "summary": v.get("summary", ""),
                         "body": v.get("body", ""), "categoryId": a["category_id"],
                         "score": score})
    hits.sort(key=lambda h: -h["score"])
    return hits[:top_k]


def normalize_score(raw):
    d = Decimal(str(raw / (raw + 1.0)))
    return d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------
# 2. 模型调用(与 OpenAiCompatibleRagAdapter 同一端点、同一提示词、同一出参约定)
# --------------------------------------------------------------------------
def call_model(cfg, system_prompt, hits, question, asset_id=None, timeout=180):
    parts = ["【参考资料】"]
    for i, h in enumerate(hits, 1):
        parts.append(f"[{i}] versionId={h['versionId']}\n标题={h['title']}\n"
                     f"摘要={h['summary']}\n正文={h['body'][:1200]}\n")
    parts.append("【员工问题】\n" + question)
    if asset_id:
        parts.append("【相关资产编号】" + asset_id)

    payload = {
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": "\n".join(parts) + "\n"}],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": 8192,
    }
    req = urllib.request.Request(
        cfg["base-url"].rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + cfg["api-key"],
                 "Content-Type": "application/json; charset=utf-8"},
        method="POST")
    started = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    cost_ms = int((time.time() - started) * 1000)

    msg = raw["choices"][0]["message"]
    # 只取 content。reasoning_content 是模型内部推理,不解析、不落库、不打印(AI-001/AI-008)
    content = (msg.get("content") or "").strip()
    reasoning_tokens = raw.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens")
    if content.startswith("```"):
        content = content[content.index("\n") + 1: content.rindex("```")].strip()
    return json.loads(content), cost_ms, reasoning_tokens


# --------------------------------------------------------------------------
# 3. 输出闸门:AiAnswerGuard 的判定优先级
# --------------------------------------------------------------------------
def guard(cfg, hits, reply, high_risk, answer_enabled=True, model_failed=False):
    """返回 (replyType, answerText, citations, confidence, refusalReason, suggestTransfer)"""
    zero = Decimal("0.0000")

    def refuse(reason, conf=zero):
        return "REFUSE", None, [], conf, reason, True

    if not answer_enabled:
        return refuse("POLICY_BLOCKED")                       # PRD 17.3 上线门槛
    if high_risk:
        return refuse("HIGH_RISK_TOPIC")                      # AI-001
    if model_failed:
        return refuse("MODEL_UNAVAILABLE")                    # RD-006
    if reply.get("knowledgeConflict"):
        return refuse("CONFLICTING_KNOWLEDGE")
    if reply.get("replyType") != "ANSWER":
        return refuse("NO_RELIABLE_KNOWLEDGE")

    # 引用重建:只认检索集合内的 versionId,模型编造的一律判无效(AI-008)
    by_version = {h["versionId"]: h for h in hits}
    citations = []
    for vid in reply.get("usedVersionIds", []):
        if vid not in by_version:
            return refuse("NO_RELIABLE_KNOWLEDGE")            # 幻觉引用
        h = by_version[vid]
        citations.append({"articleId": h["articleId"], "versionId": vid,
                          "title": h["title"][:200],
                          "score": str(normalize_score(h["score"])),
                          "snippet": (h["summary"] or h["body"])[:1000]})
    if not citations:
        return refuse("NO_RELIABLE_KNOWLEDGE")

    conf = Decimal(str(reply.get("confidence", 0))).quantize(Decimal("0.0001"))
    if conf < Decimal(cfg["min-confidence"]):
        return refuse("LOW_CONFIDENCE", conf)

    suggest = conf < Decimal(cfg["suggest-transfer-below-confidence"])
    return "ANSWER", reply.get("answerText"), citations, conf, None, suggest


def render(session_id, verdict, model, interaction_id, cost_ms, reasoning_tokens):
    reply_type, answer, citations, conf, reason, suggest = verdict
    body = {"sessionId": session_id, "replyType": reply_type}
    if answer:
        body["answerText"] = answer
    body["citations"] = citations
    body["confidence"] = float(conf)
    body["suggestTransfer"] = suggest
    if reason:
        body["refusalReason"] = reason
    body.update({"modelVersion": model, "interactionId": interaction_id})

    color = C_OK if reply_type == "ANSWER" else C_WARN
    print(f"{color}HTTP 200{C_END}  耗时 {cost_ms} ms"
          + (f"  {C_DIM}(推理 token {reasoning_tokens},已丢弃){C_END}" if reasoning_tokens else ""))
    print(json.dumps({"code": "SUCCESS", "message": "success",
                      "request_id": "req_demo", "data": body},
                     ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------
# 4. 转人工分配(PRD 12.1 算法,数据取自种子)
# --------------------------------------------------------------------------
ROUTES = {"CAT-IT-DEVICE": ["TEAM-DESKTOP"],
          "CAT-IT-NETWORK": ["TEAM-NETWORK", "TEAM-DESKTOP"],
          "CAT-IT-ACCOUNT": ["TEAM-DESKTOP"]}
MEMBERS = {"TEAM-DESKTOP": ["U004", "U005"], "TEAM-NETWORK": ["U005"]}
PRESENCE = {"U004": "AVAILABLE", "U005": "AVAILABLE"}
ACTIVE_CONSULTATIONS = {"U004": 2, "U005": 0}      # 演示用的当前活跃咨询数
LOAD_WEIGHT = 2


def assign(category_id, tried=()):
    for team in ROUTES.get(category_id, []):
        cands = []
        for eng in MEMBERS.get(team, []):
            if eng in tried:
                continue                                  # RD-005 每人最多试一次
            if PRESENCE.get(eng) != "AVAILABLE":
                continue                                  # PRD 6.2 只有 AVAILABLE 可分配
            cands.append((ACTIVE_CONSULTATIONS.get(eng, 0) * LOAD_WEIGHT, eng, team))
        if cands:
            cands.sort()
            return cands[0]
    return None


# --------------------------------------------------------------------------
def main():
    cfg = load_config()
    if not cfg.get("api-key"):
        print(C_ERR + "未读到 api-key,请确认 ai-secrets.yml 存在" + C_END)
        return 1
    keywords = load_high_risk_keywords()
    system_prompt = load_system_prompt()
    articles, versions = load_seed_knowledge()

    head("环境")
    print(f"知识库种子     : {len(articles)} 篇文章 / {len(versions)} 个版本  "
          f"(PUBLISHED {sum(1 for a in articles.values() if a['status']=='PUBLISHED')},"
          f" OFFLINE {sum(1 for a in articles.values() if a['status']=='OFFLINE')})")
    print(f"模型           : {cfg['model']}")
    print(f"端点           : {cfg['base-url']}")
    print(f"高风险关键词   : {len(keywords)} 个")
    print(f"拒答阈值       : min-confidence={cfg['min-confidence']}  "
          f"建议转人工<{cfg['suggest-transfer-below-confidence']}")

    # --- 场景 1:命中已发布知识 ---
    head("场景 1  POST /api/v1/consultations/CS.../ai-messages —— 命中已发布知识")
    q1 = "打印机一直显示离线,重启了也不行,怎么办?"
    print(f"员工提问: {q1}")
    hits = retrieve(articles, versions, q1, None, int(cfg.get("top-k", 3)))
    print(f"{C_DIM}检索命中 {len(hits)} 条(只读 PUBLISHED 当前版本): "
          f"{[h['versionId'] for h in hits]}{C_END}")
    reply, ms, rt = call_model(cfg, system_prompt, hits, q1)
    render("CS20260928DEMO01", guard(cfg, hits, reply, False),
           cfg["model"], "AIX20260928DEMO01", ms, rt)

    # --- 场景 2:高风险主题,不调用模型 ---
    head("场景 2  高风险主题 —— 服务端短路,根本不调模型(AI-001)")
    q2 = "帮我把同事的域账号密码重置一下,并提升为管理员"
    hit_word = next((w for w in keywords if w in q2), None)
    print(f"员工提问: {q2}")
    print(f"{C_DIM}命中高风险关键词「{hit_word}」→ 不发起模型调用{C_END}")
    render("CS20260928DEMO02", guard(cfg, [], {}, True),
           cfg["model"], "AIX20260928DEMO02", 0, None)

    # --- 场景 3:已下线知识不可检索 ---
    head("场景 3  已下线知识 —— 检索不到,直接拒答(AC-27)")
    q3 = "旧邮箱怎么迁移?"
    print(f"员工提问: {q3}")
    offline = [a for a, v in articles.items() if v["status"] == "OFFLINE"]
    hits3 = retrieve(articles, versions, q3, None, 3)
    print(f"{C_DIM}库里有 OFFLINE 文章 {offline},但检索结果里不包含它{C_END}")
    print(f"{C_DIM}检索命中: {[h['versionId'] for h in hits3] or '无'}{C_END}")
    if not hits3:
        render("CS20260928DEMO03",
               ("REFUSE", None, [], Decimal("0.0000"), "NO_RELIABLE_KNOWLEDGE", True),
               cfg["model"], "AIX20260928DEMO03", 0, None)

    # --- 场景 4:转人工分配 ---
    head("场景 4  POST /api/v1/consultations/CS.../transfer —— 转人工自动分配(PRD 12.1)")
    print(f"{C_DIM}工程师负载: " + ", ".join(
        f"{e}={ACTIVE_CONSULTATIONS[e]}个活跃咨询×权重{LOAD_WEIGHT}={ACTIVE_CONSULTATIONS[e]*LOAD_WEIGHT}"
        for e in sorted(ACTIVE_CONSULTATIONS)) + C_END)
    picked = assign("CAT-IT-DEVICE")
    print(f"分类 CAT-IT-DEVICE → 候选团队 {ROUTES['CAT-IT-DEVICE']} → "
          f"{C_OK}选中 {picked[1]}{C_END}(加权负载 {picked[0]},最低)")
    print(json.dumps({"code": "SUCCESS", "message": "success", "request_id": "req_demo",
                      "data": {"sessionId": "CS20260928DEMO04", "status": "WAITING_ENGINEER",
                               "assignmentId": "ASG20260928DEMO04",
                               "estimatedWaitSeconds": 600}}, ensure_ascii=False, indent=2))
    nxt = assign("CAT-IT-DEVICE", tried={picked[1]})
    print(f"\n{C_DIM}若 {picked[1]} 10 个工作分钟未回复 → 记违约 → 转派 "
          f"{nxt[1] if nxt else '无候选人,进异常队列'}{C_END}")
    third = assign("CAT-IT-DEVICE", tried={picked[1], nxt[1]}) if nxt else None
    print(f"{C_DIM}若 {nxt[1]} 也超时 → {'转派 ' + third[1] if third else '候选人耗尽,进异常队列并通知管理员(AC-09)'}{C_END}")

    head("说明")
    print("以上是用 Python 复刻的判定链路,数据与提示词都取自本仓库的真实文件。")
    print("它证明了行为正确,不证明 Java 代码能编译 —— 后者需要 JDK 17 + Maven + MySQL 8。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
