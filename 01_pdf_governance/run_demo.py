"""
PDF 格式专项治理演示脚本：
自动生成样本 PDF，识别页面类型，分别执行矢量提取与扫描件 OCR 治理。
"""

import os
from generate_sample_pdf import create_sample_pdf
from pdf_governor import PDFGovernanceEngine


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_pdf = os.path.join(current_dir, "enterprise_sample.pdf")

    print("=" * 70)
    print("🚀 [Demo 1] PDF 专项治理策略工程落地演示")
    print("=" * 70)

    # 1. 生成样本文件
    if not os.path.exists(sample_pdf):
        print("\n[Step 1] 正在生成仿真测试 PDF 文件...")
        create_sample_pdf(sample_pdf)
    else:
        print(f"\n[Step 1] 检测到现有样本 PDF: {sample_pdf}")

    # 2. 页面类型自动化判别
    engine = PDFGovernanceEngine(sample_pdf)
    print("\n[Step 2] 执行页面类型自动扫描与智能分类...")
    reports = engine.inspect_and_classify_pages()
    for rep in reports:
        print(
            f"  - 页面 {rep['page_index']}: 类型 = {rep['page_type']} "
            f"(字符数: {rep['text_char_count']}, 图片数: {rep['image_count']})"
        )

    # 3. 针对不同页面执行专业提取策略
    print("\n[Step 3] 执行专项策略提取与结构化对齐...")
    for rep in reports:
        p_idx = rep["page_index"]
        p_type = rep["page_type"]
        print("-" * 50)
        if p_type == "VECTOR_TEXT":
            print(f"📄 正在对第 {p_idx} 页执行【矢量提取 + 表格结构化 (pdfplumber)】...")
            res = engine.parse_vector_page(p_idx)
            print(res)
        else:
            print(f"🖼️ 正在对第 {p_idx} 页执行【图像预处理 + OCR + 后置规则纠错】...")
            res = engine.parse_scanned_page(p_idx)
            print(res)

    print("=" * 70)
    print("✅ [Demo 1] PDF 专项治理流程执行完毕！")
    print("=" * 70)


if __name__ == "__main__":
    main()
