#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_pipeline.py — 企业脏文档物理层清洗与 PII 脱敏管道 (Day 11 工作坊 · 步骤 2)

职责边界（对应《数据清洗与知识消歧规格说明书》§3）：
    1. 文本抽取   extract_text()      —— .txt / .md / .pdf / .docx 多格式入口
    2. 噪音剔除   strip_layout_noise() —— 页眉/页脚/水印横幅/页码分隔线/密级横幅/控制字符
    3. 表格缝合   stitch_tables()      —— 跨页表格拼接 + 表头注入 + Markdown 还原
    4. PII 脱敏   mask_pii()           —— 手机号 / 身份证 / 银行卡 100% 打码
    5. 空白压缩   compress_whitespace() —— 收敛多余换行与零宽字符

设计约束：
    * 不为外部依赖故障做静默回退：缺 pdfplumber 而输入 PDF 时直接抛错并给出原因；
    * 清洗过程输出统计报告（命中条数），供质量负责人验收对账。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# §3.1 物理噪音模式库（页眉页脚 / 水印 / 页码 / 密级横幅 / 美编标记）
# ---------------------------------------------------------------------------
NOISE_LINE_PATTERNS = [
    re.compile(r"^\[.*?(内部绝密|内部机密|严禁外传|严禁拍照).*?\]\s*$"),   # 水印横幅
    re.compile(r"^-+\s*第\s*\d+\s*页\s*(共\s*\d+\s*页)?\s*-+\s*$"),          # 页码分隔线
    re.compile(r"^【.*?底稿.*?】\s*$"),                                      # 审计底稿密级横幅
    re.compile(r"^--\s*\d+\s*--\s*$"),                                       # pdfplumber 风格页码
    re.compile(r"^\s{0,4}\d+\s*/\s*\d+\s*$"),                                # "3 / 12" 裸页码
    re.compile(r"^[─═━\-–—_=*]{8,}$"),                          # 整行装饰分隔线（DOCX/排版边框）
]
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ZERO_WIDTH_RE = re.compile(r"[​‌‍﻿]")
SOFT_HYPHEN_BREAK_RE = re.compile(r"(?<=[A-Za-z])-\n(?=[a-z])")             # 断字连字符

# ---------------------------------------------------------------------------
# §3.3 PII 正则（脱敏规则：保留首尾可追责片段，中间星号打码）
# ---------------------------------------------------------------------------
ID_CARD_RE = re.compile(r"(?<![\d*])([1-9]\d{5})\d{8}(\d{3}[\dXx])(?![\d*])")
BANK_CARD_RE = re.compile(r"(?<![\d*])(\d{6})\d{6,9}(\d{4})(?![\d*])")
PHONE_RE = re.compile(r"(?<![\d*])(1[3-9]\d)\d{4}(\d{4})(?![\d*])")

# ---------------------------------------------------------------------------
# §3.2 跨页表格缝合
# ---------------------------------------------------------------------------
TABLE_BEGIN_RE = re.compile(r"^\[表格开始.*?\]\s*$")
TABLE_END_RE = re.compile(r"^\[表格结束\]\s*$")


@dataclass
class CleanReport:
    source: str
    noise_lines_removed: int = 0
    tables_stitched: int = 0
    table_rows_stitched: int = 0
    pii_masked: dict = field(default_factory=lambda: {"phone": 0, "id_card": 0, "bank_card": 0})
    out_path: str = ""


class DocumentCleaningPipeline:
    """物理层清洗管道：抽取 -> 降噪 -> 缝合 -> 脱敏 -> 压缩。"""

    # ------------------------------------------------------------------
    def extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in (".txt", ".md"):
            return self._read_text_with_encoding(path)
        if suffix == ".pdf":
            try:
                import pdfplumber  # noqa
            except ImportError as exc:
                raise RuntimeError(
                    f"输入为 PDF 但未安装 pdfplumber，无法进行版面解析：{exc}"
                ) from exc
            return self._extract_pdf(path)
        if suffix == ".docx":
            try:
                import docx  # python-docx  # noqa
            except ImportError as exc:
                raise RuntimeError(
                    f"输入为 DOCX 但未安装 python-docx：{exc}"
                ) from exc
            return self._extract_docx(path)
        raise ValueError(f"不支持的文件格式：{path.name}")

    def _extract_docx(self, path: Path) -> str:
        """DOCX 入口：按文档 body 原始顺序输出段落与表格。

        与 PDF 通道的差异：DOCX 段落/表格结构完整，不存在跨页断裂，
        因此表格直接落成 Markdown（首行作表头），无需经缝合器；
        Heading N 样式段落转为对应层级 Markdown 标题，供下游按章节切分合集文档。
        """
        import docx

        doc = docx.Document(str(path))
        try:
            blocks = list(doc.iter_inner_content())
        except AttributeError:  # python-docx < 1.1 无 iter_inner_content
            from docx.table import Table as _Table
            from docx.text.paragraph import Paragraph as _Para
            blocks = []
            for child in doc.element.body.iterchildren():
                if child.tag.endswith("}p"):
                    blocks.append(_Para(child, doc))
                elif child.tag.endswith("}tbl"):
                    blocks.append(_Table(child, doc))
        out: list[str] = []
        for block in blocks:
            text = getattr(block, "text", None)
            if text is not None:  # 段落
                stripped = text.strip()
                if not stripped:
                    out.append("")
                    continue
                style = block.style.name if block.style is not None else ""
                m = re.match(r"^Heading (\d)$", style)
                if m:
                    out.append("#" * min(int(m.group(1)), 6) + " " + stripped)
                elif style.startswith("List Bullet"):
                    out.append("- " + stripped)
                else:
                    out.append(stripped)
            else:  # 表格
                out.extend(self._docx_table_to_markdown(block))
                out.append("")
        return "\n".join(out)

    @staticmethod
    def _docx_table_to_markdown(table) -> list[str]:
        def cell_text(cell) -> str:
            return cell.text.replace("|", "\\|").replace("\n", "<br>").strip()

        rows = [[cell_text(c) for c in row.cells] for row in table.rows]
        if not rows:
            return []
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        md = ["| " + " | ".join(rows[0]) + " |",
              "| " + " | ".join(["---"] * width) + " |"]
        md += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return md

    @staticmethod
    def _read_text_with_encoding(path: Path) -> str:
        raw = path.read_bytes()
        for enc in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("unknown", raw, 0, 1, f"无法识别编码：{path.name}")

    def _extract_pdf(self, path: Path) -> str:
        """PDF 入口：逐页抽文本；表格以 [表格开始-跨页断行待处理] 标记包裹，交给缝合器。"""
        import pdfplumber

        pages_out: list[str] = []
        prev_header_cols: int | None = None
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                body = page.extract_text() or ""
                pages_out.append(body)
                for table in page.extract_tables() or []:
                    rows = [[str(c or "").replace("\n", " ").strip() for c in r] for r in table]
                    if rows and prev_header_cols == len(rows[0]):
                        # 表头注入策略：与本页首个同列表格沿用上一页表头语义由缝合器统一处理
                        pass
                    lines = ["[表格开始-跨页断行待处理]"]
                    lines += ["\t".join(r) for r in rows]
                    lines.append("[表格结束]")
                    prev_header_cols = len(rows[0]) if rows else None
                    pages_out.append("\n".join(lines))
        return "\n".join(pages_out)

    # ------------------------------------------------------------------
    def strip_layout_noise(self, text: str, report: CleanReport) -> str:
        text = CONTROL_CHAR_RE.sub("", text)
        text = ZERO_WIDTH_RE.sub("", text)
        text = SOFT_HYPHEN_BREAK_RE.sub("", text)
        kept: list[str] = []
        for line in text.splitlines():
            if any(p.match(line) for p in NOISE_LINE_PATTERNS):
                report.noise_lines_removed += 1
                continue
            kept.append(line.rstrip())
        return "\n".join(kept)

    # ------------------------------------------------------------------
    def stitch_tables(self, text: str, report: CleanReport) -> str:
        """把 [表格开始]/[表格结束] 之间的（可能跨页断裂的）表行缝合为单张 Markdown 表。

        缝合规则：
        * 空行与残留噪音行视为跨页断缝，直接跳过（即"拼接"动作）；
        * 收集到的第一行作为表头，后续页若无表头则强制沿用（表头注入）。
        """
        lines = text.splitlines()
        out: list[str] = []
        i = 0
        while i < len(lines):
            if TABLE_BEGIN_RE.match(lines[i]):
                rows: list[list[str]] = []
                j = i + 1
                while j < len(lines) and not TABLE_END_RE.match(lines[j]):
                    raw = lines[j].strip()
                    if raw and not any(p.match(raw) for p in NOISE_LINE_PATTERNS):
                        cells = [c.strip() for c in raw.split("\t")]
                        rows.append(cells)
                    j += 1
                if rows:
                    n_cols = max(len(r) for r in rows)
                    rows = [r + [""] * (n_cols - len(r)) for r in rows]
                    report.tables_stitched += 1
                    report.table_rows_stitched += max(0, len(rows) - 1)
                    out.append(self._rows_to_markdown(rows))
                i = j + 1
            else:
                out.append(lines[i])
                i += 1
        return "\n".join(out)

    @staticmethod
    def _rows_to_markdown(rows: list[list[str]]) -> str:
        header, body = rows[0], rows[1:]
        md = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join([":---"] * len(header)) + " |",
        ]
        md += ["| " + " | ".join(r) + " |" for r in body]
        return "\n".join(md)

    # ------------------------------------------------------------------
    def mask_pii(self, text: str, report: CleanReport) -> str:
        """脱敏顺序：身份证(18位) -> 银行卡(16~19位) -> 手机号(11位)，长号优先避免误切分。"""
        text, n1 = ID_CARD_RE.subn(r"\1********\2", text)
        text, n2 = BANK_CARD_RE.subn(r"\1****\2", text)
        text, n3 = PHONE_RE.subn(r"\1****\2", text)
        report.pii_masked["id_card"] += n1
        report.pii_masked["bank_card"] += n2
        report.pii_masked["phone"] += n3
        return text

    # ------------------------------------------------------------------
    @staticmethod
    def compress_whitespace(text: str) -> str:
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"

    # ------------------------------------------------------------------
    def process_file(self, src: Path, out_dir: Path) -> CleanReport:
        report = CleanReport(source=src.name)
        try:
            raw = self.extract_text(src)
        except Exception as exc:  # 显式失败，不做静默回退
            raise RuntimeError(f"[抽取失败] {src}: {exc}") from exc
        text = self.strip_layout_noise(raw, report)
        text = self.stitch_tables(text, report)
        text = self.mask_pii(text, report)
        text = self.compress_whitespace(text)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (src.stem + ".md")
        out_path.write_text(text, encoding="utf-8")
        report.out_path = str(out_path)
        return report


def main() -> int:
    ap = argparse.ArgumentParser(description="企业脏文档物理层清洗与 PII 脱敏管道")
    ap.add_argument("--input", required=True, help="脏文档目录")
    ap.add_argument("--output", required=True, help="清洗结果输出目录")
    args = ap.parse_args()

    src_dir, out_dir = Path(args.input), Path(args.output)
    if not src_dir.is_dir():
        print(f"[失败] 输入目录不存在：{src_dir}", file=sys.stderr)
        return 2

    pipeline = DocumentCleaningPipeline()
    reports: list[CleanReport] = []
    failures = 0
    for f in sorted(src_dir.iterdir()):
        if f.suffix.lower() not in (".txt", ".md", ".pdf", ".docx"):
            continue
        try:
            r = pipeline.process_file(f, out_dir)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            failures += 1
            continue
        reports.append(r)
        p = r.pii_masked
        print(f"[OK] {f.name} -> {Path(r.out_path).name} | "
              f"噪音行 {r.noise_lines_removed} | "
              f"缝合表格 {r.tables_stitched}(数据行 {r.table_rows_stitched}) | "
              f"PII(手机 {p['phone']}/身份证 {p['id_card']}/银行卡 {p['bank_card']})")

    (out_dir / "_clean_report.json").write_text(
        json.dumps([asdict(r) for r in reports], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if failures:
        print(f"[警告] {failures} 个文件处理失败，详见上方错误。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
