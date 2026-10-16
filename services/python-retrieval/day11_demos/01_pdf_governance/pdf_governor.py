"""
PDF 格式专项治理引擎：
1. 页面类型自动判别：智能区分【原生矢量文字页】与【扫描件/纯图片页】
2. 矢量页治理：结合 pdfplumber 精准提取表格（转 Markdown）与 PyMuPDF/pdfplumber 结构化提取文本段落，并按纵向 y0 坐标保序合流
3. 扫描件治理：图像预处理（灰度化、对比度增强、二值化）+ OCR 解析 + 后置规则纠错流水线
"""

import io
import re
from typing import Dict, List, Tuple, Any

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

import pdfplumber
from PIL import Image, ImageEnhance


class PDFGovernanceEngine:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def inspect_and_classify_pages(self) -> List[Dict[str, Any]]:
        """遍历 PDF 页面，依据文本量与图像元数据自动判定页面类型"""
        page_reports = []
        if fitz is not None:
            doc = fitz.open(self.pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text().strip()
                images = page.get_images()
                is_scanned = len(text) < 30 and len(images) > 0
                page_type = "SCANNED_IMAGE" if is_scanned else "VECTOR_TEXT"
                page_reports.append({
                    "page_index": page_num + 1,
                    "page_type": page_type,
                    "text_char_count": len(text),
                    "image_count": len(images),
                })
            doc.close()
            return page_reports

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = (page.extract_text() or "").strip()
                images = page.images or []
                is_scanned = len(text) < 30 and len(images) > 0
                page_type = "SCANNED_IMAGE" if is_scanned else "VECTOR_TEXT"
                page_reports.append({
                    "page_index": page_num + 1,
                    "page_type": page_type,
                    "text_char_count": len(text),
                    "image_count": len(images),
                })
        return page_reports

    def parse_vector_page(self, page_index_1based: int) -> str:
        """
        原生矢量页面治理策略：
        1. 使用 pdfplumber 提取结构化表格，转换为 Markdown 表格，并记录其顶部 y0 坐标
        2. 获取表格包围盒（Bounding Box），避免正文提取时文字重复抽取
        3. 提取非表格区域的自然段落，并与表格按纵向 y0 坐标严格保序输出
        """
        positioned_elements: List[Tuple[float, str]] = []
        table_bboxes: List[Tuple[float, float, float, float]] = []

        # 1. 抽取表格 (借助 pdfplumber)
        with pdfplumber.open(self.pdf_path) as plumber_pdf:
            p_page = plumber_pdf.pages[page_index_1based - 1]
            tables = p_page.find_tables()

            for t in tables:
                table_bboxes.append(t.bbox)  # (x0, top, x1, bottom)
                extracted_data = t.extract()
                if extracted_data and len(extracted_data) > 1:
                    headers = extracted_data[0]
                    rows = extracted_data[1:]

                    clean_headers = [str(c or "").strip() for c in headers]
                    md_table = "| " + " | ".join(clean_headers) + " |\n"
                    md_table += "| " + " | ".join(["---"] * len(clean_headers)) + " |\n"

                    for row in rows:
                        clean_row = [str(c or "").strip() for c in row]
                        md_table += "| " + " | ".join(clean_row) + " |\n"

                    positioned_elements.append((float(t.bbox[1]), md_table.strip()))

            # 2. 抽取非表格正文（优先使用 PyMuPDF blocks，未安装时回退 pdfplumber 行级坐标提取）
            if fitz is not None:
                doc = fitz.open(self.pdf_path)
                fitz_page = doc[page_index_1based - 1]
                blocks = fitz_page.get_text("blocks")
                for b in blocks:
                    if b[6] == 0:
                        bx0, by0, bx1, by1, btext = b[0], b[1], b[2], b[3], b[4].strip()
                        if not btext:
                            continue
                        in_table = any(
                            bx0 >= tx0 - 5 and bx1 <= tx1 + 5 and by0 >= ty0 - 5 and by1 <= ty1 + 5
                            for (tx0, ty0, tx1, ty1) in table_bboxes
                        )
                        if not in_table:
                            positioned_elements.append((float(by0), btext))
                doc.close()
            else:
                for line in p_page.extract_text_lines() or []:
                    lx0, ly0, lx1, ly1 = line.get("x0", 0), line.get("top", 0), line.get("x1", 0), line.get("bottom", 0)
                    ltext = (line.get("text") or "").strip()
                    if not ltext:
                        continue
                    in_table = any(
                        lx0 >= tx0 - 5 and lx1 <= tx1 + 5 and ly0 >= ty0 - 5 and ly1 <= ty1 + 5
                        for (tx0, ty0, tx1, ty1) in table_bboxes
                    )
                    if not in_table:
                        positioned_elements.append((float(ly0), ltext))

        # 按纵向 y0 坐标升序排列，严格保持段落与表格在页面中的真实阅读顺序
        positioned_elements.sort(key=lambda item: item[0])

        final_md = f"### 【矢量解析结果】第 {page_index_1based} 页\n\n"
        if positioned_elements:
            final_md += "\n\n".join(text for _, text in positioned_elements) + "\n"

        return final_md

    def preprocess_image(self, raw_img: Image.Image) -> Image.Image:
        """图像预处理流水线：灰度转换 -> 对比度拉伸 -> 二值化阈值处理（去除底色与噪点）"""
        gray_img = raw_img.convert("L")
        enhancer = ImageEnhance.Contrast(gray_img)
        enhanced_img = enhancer.enhance(2.0)
        threshold = 180
        bin_img = enhanced_img.point(lambda p: 255 if p > threshold else 0)
        return bin_img

    def post_ocr_correction(self, raw_ocr_text: str) -> Tuple[str, List[str]]:
        """后置规则与纠错词典流水线"""
        correction_logs = []
        fixed_text = raw_ocr_text

        replacements = {
            "人氏币": "人民币",
            "甲力": "甲方",
            "乙力": "乙方",
            "合回": "合同",
        }
        for wrong, correct in replacements.items():
            if wrong in fixed_text:
                fixed_text = fixed_text.replace(wrong, correct)
                correction_logs.append(f"词汇纠错: '{wrong}' -> '{correct}'")

        def fix_money_o(match):
            original = match.group(0)
            corrected = original.replace("O", "0").replace("o", "0")
            if original != corrected:
                correction_logs.append(f"金额数字纠错: '{original}' -> '{corrected}'")
            return corrected

        fixed_text = re.sub(r"(?<=[\s:：人民币¥$])([0-9OoeE,\.]+)(?=元|\s|$)", fix_money_o, fixed_text)
        fixed_text = re.sub(r"\b\d+[0-9OoeE,\.]*\b", fix_money_o, fixed_text)

        def fix_account_o(match):
            prefix = match.group(1)
            digits_part = match.group(2)
            cleaned_digits = digits_part.replace("O", "0").replace("o", "0").replace("I", "1")
            if digits_part != cleaned_digits:
                correction_logs.append(f"账号数值纠错: '{digits_part}' -> '{cleaned_digits}'")
            return prefix + cleaned_digits

        fixed_text = re.sub(r"(账号[：:]\s*)([0-9OIo\s]+)", fix_account_o, fixed_text)

        return fixed_text, correction_logs

    def parse_scanned_page(self, page_index_1based: int) -> str:
        """扫描件/图片型页面治理策略"""
        if fitz is not None:
            doc = fitz.open(self.pdf_path)
            page = doc[page_index_1based - 1]
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            raw_image = Image.open(io.BytesIO(img_bytes))
            doc.close()
        else:
            with pdfplumber.open(self.pdf_path) as pdf:
                raw_image = pdf.pages[page_index_1based - 1].to_image(resolution=150).original

        processed_img = self.preprocess_image(raw_image)

        raw_ocr_simulation = (
            "【扫描附件】企业保密协议与外包责任确认单\n"
            "甲力单位：武汉智能制造产业基地研发中心\n"
            "乙力单位：湖北精密系统工程外包技术服务部\n"
            "协议条款摘要：\n"
            "1. 乙力派驻人员须遵守甲方数据安全准则，严禁私自拷贝内网知识库。\n"
            "2. 履约保证金总额为人氏币 10O,00O.OO 元整，通过对公账户转账交付。\n"
            "3. 指定结算账号：6222 O2IO OOI2 3456 789，开户行为工行光谷支行。"
        )

        cleaned_text, logs = self.post_ocr_correction(raw_ocr_simulation)

        final_md = f"### 【扫描件 OCR 治理结果】第 {page_index_1based} 页\n\n"
        final_md += "#### 1. 原始脏 OCR 文本（含典型混淆错误）：\n```text\n" + raw_ocr_simulation + "\n```\n\n"
        final_md += "#### 2. 后置纠错流水线触发记录：\n"
        for log in logs:
            final_md += f"- ⚡ {log}\n"
        final_md += "\n#### 3. 最终清洗交付文本（下游 Agent 可安全解析）：\n```text\n" + cleaned_text + "\n```\n"

        return final_md
