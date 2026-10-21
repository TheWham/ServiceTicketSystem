"""Fetch official zh-CN translations from Microsoft Learn for the Dify KB corpus.

For each English markdown file in support-articles-en that has no counterpart in
support-articles-zh, read the Microsoft Learn source URL from its footer, fetch the
corresponding /zh-cn/ page, convert the article body to markdown, and write it to the
mirrored path under support-articles-zh with the standard attribution footer.

Pages that have no official Chinese translation (zh-cn URL falls back to English
content) are skipped and listed at the end.

Usage:
  python db/tools/fetch_dify_kb_zh.py [--en-root DIR] [--zh-root DIR] [--only REGEX]
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

SOURCE_RE = re.compile(r"> Source: \[Microsoft Learn\]\((https://learn\.microsoft\.com/en-us/[^)]+)\)")
IMG_ABS_BASE = "https://learn.microsoft.com"
FOOTER_TMPL = (
    "\n\n---\n\n> 来源: [Microsoft Learn]({en_url})（Microsoft 版权所有，依据 "
    "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；"
    "本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）\n"
)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

STRIP_CLASSES = {
    "visually-hidden",
    "display-none-print",
    "ms--inline-notifications",
    "margin-block-xs",
}
STRIP_IDS = {"site-user-feedback-footer", "article-metadata-footer"}


def extract_en_url(text: str) -> str | None:
    m = SOURCE_RE.search(text)
    return m.group(1) if m else None


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def clean_node(node) -> None:
    for bad in list(node.find_all(True)):
        classes = set(bad.get("class") or [])
        if classes & STRIP_CLASSES or (bad.get("id") in STRIP_IDS):
            bad.decompose()
    for img in node.find_all("img"):
        src = img.get("src") or ""
        if src.startswith("/"):
            img["src"] = IMG_ABS_BASE + src


def fetch_zh_markdown(session: requests.Session, en_url: str) -> tuple[str, str]:
    """Return (markdown, zh_url) or raise LookupError when untranslated."""
    zh_url = en_url.replace("/en-us/", "/zh-cn/", 1)
    resp = session.get(zh_url, headers=UA, timeout=40)
    resp.raise_for_status()
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')
    main = soup.find("main")
    if main is None:
        raise LookupError("no <main> element")
    blocks = main.find_all("div", class_="content")
    if not blocks:
        raise LookupError("no article content block")
    parts = []
    for block in blocks:
        clean_node(block)
        part = md(str(block), heading_style="ATX", bullets="-")
        parts.append(part.strip("\n"))
    return "\n\n".join(p for p in parts if p), zh_url


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser()
    parser.add_argument("--en-root", default=str(repo_root / "dify-kb" / "support-articles-en"))
    parser.add_argument("--zh-root", default=str(repo_root / "dify-kb" / "support-articles-zh"))
    parser.add_argument("--only", default="", help="regex filter on the source URL")
    args = parser.parse_args()

    en_root, zh_root = Path(args.en_root), Path(args.zh_root)
    session = requests.Session()

    todo, done_exists, untranslated, failed = [], [], [], []
    for en_path in sorted(en_root.rglob("*.md")):
        rel = en_path.relative_to(en_root)
        if (zh_root / rel).exists():
            done_exists.append(rel)
            continue
        todo.append((en_path, rel))

    print(f"todo={len(todo)} already-translated={len(done_exists)}", flush=True)

    written = 0
    for i, (en_path, rel) in enumerate(todo, 1):
        en_text = en_path.read_text(encoding="utf-8-sig")
        en_url = extract_en_url(en_text)
        if not en_url:
            failed.append((rel, "no source url"))
            continue
        if args.only and not re.search(args.only, en_url):
            continue
        try:
            markdown, _ = fetch_zh_markdown(session, en_url)
        except Exception as exc:  # noqa: BLE001 - log and continue with next file
            failed.append((rel, f"{type(exc).__name__}: {exc}"))
            continue
        en_h1 = first_heading(en_text).lower()
        if en_h1 and en_h1 in markdown.lower():
            # h1 identical to the English one -> zh-cn page fell back to English
            zh_h1 = first_heading(markdown)
            if zh_h1.lower() == en_h1:
                untranslated.append(rel)
                continue
        markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
        out_path = zh_root / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown + FOOTER_TMPL.format(en_url=en_url), encoding="utf-8-sig")
        written += 1
        if i % 20 == 0 or i == len(todo):
            print(f"[{i}/{len(todo)}] written={written} untranslated={len(untranslated)} failed={len(failed)}", flush=True)
        time.sleep(0.25)

    print(f"\nwritten={written} untranslated={len(untranslated)} failed={len(failed)}")
    for rel in untranslated:
        print(f"  UNTRANSLATED {rel}")
    for rel, why in failed:
        print(f"  FAILED {rel}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


