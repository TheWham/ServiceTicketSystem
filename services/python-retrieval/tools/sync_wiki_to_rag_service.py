#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_wiki_to_rag_service.py — 把 Git 侧 Wiki 卡片灌进 Java rag-service（MySQL+ES）并产出 id 映射

为什么需要：Python 检索服务返回的 articleId/versionId 必须能在 Java rag-service 的
knowledge_article/knowledge_version 中查到 PUBLISHED 且 currentVersionId 匹配，否则
Java 侧第 ④ 步 MySQL 复核会把 items 全部滤空（映射缺失 → 服务 DEGRADED，检索必空）。

硬性排除：`_index.md`；status ∈ {已废止, 已下线} 的 LEG 卡（不得推成 PUBLISHED）。
幂等：`wiki_version` 未变即跳过；`--force` 强制重灌（注意：重灌会生成新的 articleId）。
产出：`data/wiki_article_mapping.json`（原子写）。

用法（在 D:\\day12\\demos 目录下，需 Java rag-service 已启动）：
    python tools/sync_wiki_to_rag_service.py
    python tools/sync_wiki_to_rag_service.py --java-base http://127.0.0.1:8302 --force
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 中文类目 → Java 类目编码（编码取自 db/init/10-seed.sql：C_HW/C_HW_PC/C_HW_PR/C_SW/C_NET/C_ACC/C_OTH）
JAVA_CATEGORY_BY_WIKI_CATEGORY = {
    "账号与权限问题": "C_ACC",
    "网络连接问题": "C_NET",
    "网络连接": "C_NET",
    "VPN与远程办公": "C_NET",
    "硬件与外设故障": "C_HW",
    "系统与软件故障": "C_SW",
    "办公软件问题（WPS/Office）": "C_SW",
    "邮件与通讯问题": "C_SW",
    "数据存储与备份": "C_SW",
    "附录：IT故障排查通用流程": "C_OTH",
}

DEPRECATED_STATUS = ("已废止", "已下线")


def parse_frontmatter(text: str) -> Dict[str, Any]:
    """解析 Markdown 卡片的 YAML frontmatter（首个 `---` 块）。"""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}


def collect_cards(wiki_dir: Path) -> List[Dict[str, Any]]:
    """收集可入库卡片：排除 `_index.md` 与已废止/已下线卡。"""
    cards: List[Dict[str, Any]] = []
    for path in sorted(wiki_dir.glob("*.md")):
        if path.name == "_index.md":
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        status = fm.get("status")
        if status in DEPRECATED_STATUS:
            continue
        wiki_id = fm.get("id") or path.stem
        cards.append({
            "wiki_id": wiki_id,
            "title": fm.get("title") or wiki_id,
            "category": fm.get("category") or "",
            "version": fm.get("version") or "",
            "status": status,
            "path": path,
        })
    return cards


def java_category_of(category: str) -> str:
    """中文类目 → Java 类目编码；未知类目回退 C_OTH。"""
    return JAVA_CATEGORY_BY_WIKI_CATEGORY.get(category, "C_OTH")


def load_mapping(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except Exception as e:      # noqa: BLE001
        print(f"⚠️ 映射文件损坏（{path}）：{e}，按空映射继续")
        return {}


def save_mapping_atomic(path: Path, mapping: Dict[str, Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def needs_sync(card: Dict[str, Any], mapping: Dict[str, Dict[str, Any]], force: bool) -> bool:
    """幂等判定：映射已有且 wiki_version 未变即跳过。"""
    if force:
        return True
    entry = mapping.get(card["wiki_id"])
    if not entry:
        return True
    return entry.get("wiki_version") != card["version"]


def upload_card(session, java_base: str, card: Dict[str, Any], category_id: str,
                headers: Dict[str, str], timeout: float) -> Dict[str, Any]:
    """走 rag-service 既有上传 API（publishNow=true 快速通道，直接 PUBLISHED 并写 ES）。

    Returns: {"articleId": ..., "versionId": ..., "currentVersionId": ...}
    """
    url = java_base.rstrip("/") + "/api/v1/rag/documents/upload"
    with open(card["path"], "rb") as f:
        files = {"file": (card["path"].name, f, "text/markdown")}
        data = {
            "title": card["title"],
            "categoryId": category_id,
            "riskLevel": "NORMAL",
            "publishNow": "true",
        }
        resp = session.post(url, files=files, data=data, headers=headers, timeout=timeout)
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(f"code={body.get('code')} msg={body.get('msg')}")
    payload = body.get("data") or {}
    article = payload.get("article") or {}
    version = payload.get("version") or {}
    return {
        "articleId": article.get("articleId"),
        "versionId": version.get("versionId") or article.get("currentVersionId"),
        "currentVersionId": article.get("currentVersionId"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Wiki 卡片灌库到 Java rag-service 并产出 id 映射")
    parser.add_argument("--wiki-dir", default="artifacts/output/wiki")
    parser.add_argument("--mapping", default="data/wiki_article_mapping.json")
    parser.add_argument("--java-base", default=os.environ.get("RAG_JAVA_BASE_URL", "http://127.0.0.1:8302"))
    parser.add_argument("--user-id", default=os.environ.get("RAG_SYNC_USER_ID", "U_KBA01"))
    parser.add_argument("--user-role", default=os.environ.get("RAG_SYNC_USER_ROLE", "KNOWLEDGE_ADMIN"))
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--force", action="store_true", help="忽略 wiki_version 幂等判定，强制重灌")
    args = parser.parse_args()

    import requests

    wiki_dir = REPO_ROOT / args.wiki_dir
    mapping_path = REPO_ROOT / args.mapping
    cards = collect_cards(wiki_dir)
    mapping = load_mapping(mapping_path)
    headers = {"X-User-Id": args.user_id, "X-User-Role": args.user_role}

    print(f"🔗 Java rag-service: {args.java_base}")
    print(f"📚 待处理现行卡 {len(cards)} 张（已排除 _index.md 与废止/下线卡）\n")

    session = requests.Session()
    synced, skipped, failures = [], 0, []
    for card in cards:
        if not needs_sync(card, mapping, args.force):
            skipped += 1
            continue
        category_id = java_category_of(card["category"])
        last_err = None
        for attempt in range(args.retries):
            try:
                result = upload_card(session, args.java_base, card, category_id, headers, args.timeout)
                if not result.get("articleId") or not result.get("versionId"):
                    raise RuntimeError(f"上传响应缺 articleId/versionId：{result}")
                mapping[card["wiki_id"]] = {
                    "articleId": result["articleId"],
                    "versionId": result["versionId"],
                    "categoryId": category_id,
                    "wiki_version": card["version"],
                    "wiki_category": card["category"],
                    "title": card["title"],
                    "synced_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                synced.append(card["wiki_id"])
                print(f"  ✅ {card['wiki_id']:<18} → articleId={result['articleId']} "
                      f"versionId={result['versionId']} ({category_id})")
                save_mapping_atomic(mapping_path, mapping)   # 逐张落盘：中断也不丢已完成映射
                break
            except Exception as e:      # noqa: BLE001
                last_err = e
                if attempt < args.retries - 1:
                    time.sleep(2 ** attempt)
        else:
            failures.append((card["wiki_id"], str(last_err)))
            print(f"  ❌ {card['wiki_id']:<18} 失败（{args.retries} 次重试后）：{last_err}")

    print(f"\n{'=' * 72}")
    print(f"灌库汇总：成功 {len(synced)} / 跳过 {skipped} / 失败 {len(failures)}（映射 {mapping_path}）")
    if failures:
        for wid, err in failures:
            print(f"  ❌ {wid}: {err}")
        return 1
    print("🎉 全部现行卡已 PUBLISHED 并写入映射表")
    return 0


if __name__ == "__main__":
    sys.exit(main())
