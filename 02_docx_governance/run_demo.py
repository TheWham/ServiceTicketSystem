"""
Word (.docx) 格式专项治理演示脚本：
对比朴素分离提取 vs 保序流式提取效果。
"""

import os
from generate_sample_docx import create_sample_docx
from docx_stream_parser import DocxGovernanceEngine


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_docx = os.path.join(current_dir, "enterprise_sla.docx")

    print("=" * 70)
    print("🚀 [Demo 2] Word (.docx) 专项治理策略工程落地演示")
    print("=" * 70)

    # 1. 自动生成测试 DOCX
    if not os.path.exists(sample_docx):
        print("\n[Step 1] 正在生成仿真测试 DOCX 文件...")
        create_sample_docx(sample_docx)
    else:
        print(f"\n[Step 1] 检测到现有样本 DOCX: {sample_docx}")

    engine = DocxGovernanceEngine(sample_docx)

    # 2. 演示朴素分离提取的缺陷
    print("\n" + "-" * 50)
    print("🔴 策略 A: 传统朴素分离遍历 (paragraphs + tables)")
    print("痛点说明: 表格全部坠落到文档末尾，上下文严重割裂，大模型读完正文找不到表，读完表找不到前面的限制条件！")
    print("-" * 50)
    naive_res = engine.parse_naive_separated()
    print(naive_res)

    # 3. 演示推荐的 XML 流式保序提取
    print("\n" + "=" * 50)
    print("🟢 策略 B: 推荐的底层 XML 元素保序流式提取 (doc.element.body)")
    print("优势说明: 严格维持真实物理排版顺序，标题、前导正文、表格、后继声明无缝串联！")
    print("=" * 50)
    stream_res = engine.parse_stream_ordered()
    print(stream_res)

    print("=" * 70)
    print("✅ [Demo 2] Word 专项治理流程执行完毕！")
    print("=" * 70)


if __name__ == "__main__":
    main()
