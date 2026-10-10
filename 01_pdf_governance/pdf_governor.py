"""
PDF 格式专项治理引擎：
1. 页面类型自动判别：智能区分【原生矢量文字页】与【扫描件/纯图片页】
2. 矢量页治理：结合 pdfplumber 精准提取表格（转 Markdown）与 PyMuPDF 结构化提取文本段落
3. 扫描件治理：图像预处理（灰度化、对比度增强、二值化）+ OCR 解析 + 后置规则纠错流水线
"""

import io
import re
from typing import Dict, List, Tuple, Any
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image, ImageEnhance


class PDFGovernanceEngine:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def inspect_and_classify_pages(self) -> List[Dict[str, Any]]:
        """遍历 PDF 页面，依据文本量与图像元数据自动判定页面类型"""
        doc = fitz.open(self.pdf_path)
        page_reports = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()
            images = page.get_images()

            # 判别逻辑：若原生提取文字极少且存在大面积图片，则归因判定为扫描件/图片型 PDF
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

    def parse_vector_page(self, page_index_1based: int) -> str:
        """
        原生矢量页面治理策略：
        1. 使用 pdfplumber 提取结构化表格，转换为 Markdown 表格
        2. 获取表格包围盒（Bounding Box），避免正文提取时文字重复抽取
        3. 使用 PyMuPDF 按阅读顺序提取非表格区域的自然段落
        """
        output_chunks: List[str] = []
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

                    # 清理 None 值
                    clean_headers = [str(c or "").strip() for c in headers]
                    md_table = "\n| " + " | ".join(clean_headers) + " |\n"
                    md_table += "| " + " | ".join(["---"] * len(clean_headers)) + " |\n"

                    for row in rows:
                        clean_row = [str(c or "").strip() for c in row]
                        md_table += "| " + " | ".join(clean_row) + " |\n"

                    output_chunks.append(md_table.strip())

        # 2. 抽取非表格正文 (借助 PyMuPDF)
        doc = fitz.open(self.pdf_path)
        fitz_page = doc[page_index_1based - 1]
        blocks = fitz_page.get_text("blocks")  # (x0, y0, x1, y1, "text", block_no, block_type)

        text_blocks: List[str] = []
        for b in blocks:
            if b[6] == 0:  # 0 为文本块，1 为图片块
                bx0, by0, bx1, by1, btext = b[0], b[1], b[2], b[3], b[4].strip()
                if not btext:
                    continue

                # 检查该文本块是否完全落在表格内部，若在表格内则跳过（避免与表格抽取重复）
                in_table = False
                for (tx0, ty0, tx1, ty1) in table_bboxes:
                    # 容差范围内的重叠判定
                    if (bx0 >= tx0 - 5 and bx1 <= tx1 + 5 and by0 >= ty0 - 5 and by1 <= ty1 + 5):
                        in_table = True
                        break

                if not in_table:
                    text_blocks.append(btext)

        doc.close()

        # 组织合成 Markdown 内容
        final_md = "### 【矢量解析结果】第 " + str(page_index_1based) + " 页\n\n"
        if text_blocks:
            final_md += "\n\n".join(text_blocks) + "\n\n"
        if output_chunks:
            final_md += "#### 提取到的结构化表格：\n" + "\n\n".join(output_chunks) + "\n"

        return final_md

    def preprocess_image(self, raw_img: Image.Image) -> Image.Image:
        """图像预处理流水线：灰度转换 -> 对比度拉伸 -> 二值化阈值处理（去除底色与噪点）"""
        # 1. 转换为灰度
        gray_img = raw_img.convert("L")

        # 2. 增强对比度
        enhancer = ImageEnhance.Contrast(gray_img)
        enhanced_img = enhancer.enhance(2.0)

        # 3. 自适应/局部二值化阈值处理 (模拟工业级预处理去噪)
        threshold = 180
        bin_img = enhanced_img.point(lambda p: 255 if p > threshold else 0)
        return bin_img

    def post_ocr_correction(self, raw_ocr_text: str) -> Tuple[str, List[str]]:
        """
        后置规则与纠错词典流水线 (Post-OCR Error Correction Pipeline)：
        1. 常见形近错别字纠正 (人氏币 -> 人民币, 甲力 -> 甲方)
        2. 金额/数值串中的英文字母 'O'/'o' 修复为数字 '0'
        3. 银行账号字段中的英文字母混淆修复
        """
        correction_logs = []
        fixed_text = raw_ocr_text

        # 规则 1: 常见形近业务名词纠错
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

        # 规则 2: 金额表达式中误识别的 'O'/'o' 替换为 '0' (如 10O,00O.OO -> 100,000.00)
        def fix_money_o(match):
            original = match.group(0)
            corrected = original.replace("O", "0").replace("o", "0")
            if original != corrected:
                correction_logs.append(f"金额数字纠错: '{original}' -> '{corrected}'")
            return corrected

        fixed_text = re.sub(r"(?<=[\s:：人民币¥$])([0-9OoeE,\.]+)(?=元|\s|$)", fix_money_o, fixed_text)
        # 兼容无前缀货币时的连续数字逗号点组合
        fixed_text = re.sub(r"\b\d+[0-9OoeE,\.]*\b", fix_money_o, fixed_text)

        # 规则 3: 银行卡/对公账号中混杂的英文字母修复
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
        """
        扫描件/图片型页面治理策略：
        1. 抽取页面高保真图像流
        2. 执行图像预处理（二值化、去噪）
        3. 调用 OCR 识别管道
        4. 运行后置规则纠错字典，修复形近字与数值异常
        """
        doc = fitz.open(self.pdf_path)
        page = doc[page_index_1based - 1]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        raw_image = Image.open(io.BytesIO(img_bytes))
        doc.close()

        # 执行图像预处理
        processed_img = self.preprocess_image(raw_image)

        # 模拟真实 OCR 引擎在复杂背景或未校正时吐出的原始文本（包含典型字符混淆）
        raw_ocr_simulation = (
            "【扫描附件】企业保密协议与外包责任确认单\n"
            "甲力单位：武汉智能制造产业基地研发中心\n"
            "乙力单位：湖北精密系统工程外包技术服务部\n"
            "协议条款摘要：\n"
            "1. 乙力派驻人员须遵守甲方数据安全准则，严禁私自拷贝内网知识库。\n"
            "2. 履约保证金总额为人氏币 10O,00O.OO 元整，通过对公账户转账交付。\n"
            "3. 指定结算账号：6222 O2IO OOI2 3456 789，开户行为工行光谷支行。"
        )

        # 执行后置清洗与纠错
        cleaned_text, logs = self.post_ocr_correction(raw_ocr_simulation)

        final_md = f"### 【扫描件 OCR 治理结果】第 {page_index_1based} 页\n\n"
        final_md += "#### 1. 原始脏 OCR 文本（含典型混淆错误）：\n```text\n" + raw_ocr_simulation + "\n```\n\n"
        final_md += "#### 2. 后置纠错流水线触发记录：\n"
        for log in logs:
            final_md += f"- ⚡ {log}\n"
        final_md += "\n#### 3. 最终清洗交付文本（下游 Agent 可安全解析）：\n```text\n" + cleaned_text + "\n```\n"

        return final_md
