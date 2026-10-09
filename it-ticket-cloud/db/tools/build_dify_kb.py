# -*- coding: utf-8 -*-
"""build_dify_kb.py -- Convert Microsoft Learn (microsoft-365-docs) markdown into
clean Markdown files that can be imported directly into a Dify knowledge base.

What it does:
  - strips YAML front-matter (keeps `title`/`description` for the output header)
  - removes MS Learn-only syntax: :::moniker blocks, :::image elements,
    > [!VIDEO] embeds, [!INCLUDE] files (resolved inline when available)
  - rewrites relative .md links to absolute https://learn.microsoft.com URLs
  - appends a CC-BY-4.0 attribution footer (required by the source license)

Usage:
  python build_dify_kb.py <src_dir> <out_dir> [--docset microsoft-365]
"""
import argparse
import html
import re
import sys
from pathlib import Path

LEARN_BASE = "https://learn.microsoft.com/en-us"

ALERT_MAP = {
    "NOTE": "**Note**",
    "IMPORTANT": "**Important**",
    "WARNING": "**Warning**",
    "TIP": "**Tip**",
    "CAUTION": "**Caution**",
}


def parse_front_matter(text: str):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            raw = text[3:end].strip("\n")
            body = text[end + 4:].lstrip("\n")
            for line in raw.splitlines():
                m = re.match(r"^(\w[\w.\-]*):\s*(.+)$", line)
                if m:
                    meta[m.group(1)] = m.group(2).strip().strip('"')
            return meta, body
    return meta, text


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def resolve_includes(body: str, src_root: Path, current_dir: Path, depth: int = 0) -> str:
    """Inline [!INCLUDE [t](path.md)] blocks, one level of recursion."""
    def repl(m):
        rel = m.group(2)
        target = (current_dir / rel).resolve()
        if depth >= 2 or not target.is_file():
            return ""
        try:
            _, inc_body = parse_front_matter(target.read_text(encoding="utf-8"))
            inc_body = resolve_includes(inc_body, src_root, target.parent, depth + 1)
            return "\n" + inc_body.strip() + "\n"
        except OSError:
            return ""

    return re.sub(r"\[!INCLUDE\s*\[([^\]]*)\]\(([^)]+)\)\]", repl, body)


def clean_monikers(body: str) -> str:
    # Remove moniker delimiter lines (possibly indented inside lists) but keep enclosed content.
    body = re.sub(r"^\s*:::+\s*moniker[^\n]*\n", "", body, flags=re.M)
    body = re.sub(r"^\s*:::+\s*moniker-end[^\n]*\n", "", body, flags=re.M)
    return body


def clean_images(body: str) -> str:
    """:::image blocks -> italic alt-text caption (relative images cannot load in Dify)."""

    def repl_block(m):
        attrs = m.group(1)
        alt = re.search(r'alt-text="([^"]*)"', attrs)
        if alt and alt.group(1).strip():
            return f"\n*(image: {alt.group(1).strip()})*\n"
        return ""

    # single-line or multi-line :::image ... :::
    body = re.sub(r":::image\s+(.*?):::", repl_block, body, flags=re.S)

    # standard markdown images with relative paths -> keep alt as caption
    def repl_md(m):
        alt, url = m.group(1), m.group(2)
        if re.match(r"https?://", url):
            return m.group(0)
        return f"*(image: {alt})*" if alt.strip() else ""

    body = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)", repl_md, body)
    return body


def clean_alerts(body: str) -> str:
    for key, label in ALERT_MAP.items():
        body = re.sub(rf"^\s*>\s*\[!{key}\]\s*$", "> " + label, body, flags=re.M)
    # video embeds carry no text value for retrieval
    body = re.sub(r"^\s*>\s*\[!VIDEO[^\]]*\]\s*\n?", "", body, flags=re.M)
    return body


def rewrite_links(body: str, current_rel: Path, docset_prefix: str) -> str:
    """Relative .md links -> absolute learn.microsoft.com URLs.

    docset_prefix is the on-site path prefix, e.g. 'microsoft-365/admin'.
    """

    def repl(m):
        text, url = m.group(1), m.group(2)
        if re.match(r"https?://|mailto:", url) or url.startswith("#"):
            return m.group(0)
        url_no_anchor, _, anchor = url.partition("#")
        if not url_no_anchor.lower().endswith((".md", ".yml")):
            return m.group(0)  # non-doc asset paths were handled elsewhere
        base_parts = [p for p in docset_prefix.split("/") if p]
        parent = current_rel.parent.as_posix()
        if parent not in ("", "."):
            base_parts += [p for p in parent.split("/") if p]
        target = base_parts + [p for p in url_no_anchor.split("/") if p]
        parts = []
        for part in target:
            if part == ".":
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        rel = "/".join(parts)
        rel = re.sub(r"\.(md|yml)$", "", rel)
        if rel != docset_prefix.split("/")[0] and not rel.startswith(docset_prefix.split("/")[0] + "/"):
            # link escaped the docset; keep text, drop the broken target
            return text
        abs_url = f"{LEARN_BASE}/{rel}"
        abs_url = abs_url + ("#" + anchor if anchor else "")
        return f"[{text}]({abs_url})"

    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", repl, body)


def collapse_blank_lines(body: str) -> str:
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip() + "\n"


def convert_file(src: Path, src_root: Path, docset_prefix: str, out_root: Path) -> tuple:
    rel = src.relative_to(src_root)
    meta, body = parse_front_matter(src.read_text(encoding="utf-8"))
    body = strip_html_comments(body)
    body = resolve_includes(body, src_root, src.parent)
    body = clean_monikers(body)
    body = clean_images(body)
    body = clean_alerts(body)
    body = rewrite_links(body, rel, docset_prefix)
    body = collapse_blank_lines(body)

    title = meta.get("title", src.stem)
    if not re.search(r"^#\s+", body, flags=re.M):
        body = f"# {title}\n\n" + body

    learn_rel = f"{docset_prefix}/{rel.as_posix()}"
    learn_rel = re.sub(r"\.md$", "", learn_rel)
    source_url = f"{LEARN_BASE}/{learn_rel}"
    footer = (
        "\n\n---\n\n"
        f"> Source: [Microsoft Learn]({source_url}) "
        "(Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))\n"
    )
    out_path = out_root / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body + footer, encoding="utf-8")
    return title, source_url


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("src_dir", type=Path, help="subset root, e.g. .../microsoft-365-docs/microsoft-365/admin")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--docset-prefix", default=None,
                    help="on-site path prefix, e.g. microsoft-365/admin (default: last two path parts of src_dir)")
    args = ap.parse_args(argv)

    src_root = args.src_dir.resolve()
    out_root = args.out_dir.resolve()
    if not src_root.is_dir():
        print(f"src_dir not found: {src_root}", file=sys.stderr)
        return 2

    docset_prefix = args.docset_prefix or "/".join(src_root.parts[-2:])
    md_files = sorted(
        p for p in src_root.rglob("*.md") if p.is_file()
        if "includes" not in p.relative_to(src_root).parts
        and not p.name.lower().startswith("toc")
    )
    ok, failed = 0, []
    for src in md_files:
        try:
            convert_file(src, src_root, docset_prefix, out_root)
            ok += 1
        except Exception as exc:  # keep batch going, report at the end
            failed.append((src, exc))
    print(f"converted: {ok} files -> {out_root}")
    for src, exc in failed:
        print(f"FAILED {src}: {exc}", file=sys.stderr)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())


