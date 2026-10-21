# -*- coding: utf-8 -*-
"""split_by_h1.py — 按一级标题(# )切分合集式清洗文档，产出"一篇一卡"输入集。

用法：
    python split_by_h1.py <cleaned_md> <out_dir>

规则：
    * 首个 H1 之前的全局抬头（文档名/版本/适用范围）注入每个分片开头，
      保证每张卡都能锚定原始版本与生效信息；
    * 每个 H1 区块（至下一个 H1 或文末）落为一个独立 md 文件；
    * 无 H1 的文档原样复制（幂等兜底）。
"""
import re
import sys
from pathlib import Path

SAFE_NAME_RE = re.compile(r'[\\/:*?"<>|\s]+')


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 3:
        print("用法: python split_by_h1.py <cleaned_md> <out_dir>", file=sys.stderr)
        return 2
    src, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    boundaries = [m.start() for m in re.finditer(r"(?m)^# ", text)]
    if not boundaries:
        (out_dir / src.name).write_text(text, encoding="utf-8")
        print(f"[无H1原样复制] {src.name}")
        return 0
    preamble = text[: boundaries[0]].strip()
    bounds = boundaries + [len(text)]
    for idx, (start, end) in enumerate(zip(bounds, bounds[1:]), 1):
        block = text[start:end].strip()
        title = block.splitlines()[0].lstrip("# ").strip()
        name = SAFE_NAME_RE.sub("_", title)[:40].strip("_") or f"part{idx}"
        content = (preamble + "\n\n" + block) if preamble else block
        (out_dir / f"{idx:02d}_{name}.md").write_text(content + "\n", encoding="utf-8")
        print(f"[切分] {idx:02d}_{name}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
