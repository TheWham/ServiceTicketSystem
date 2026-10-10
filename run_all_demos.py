"""
Day 11 格式专项治理工程落地：一键执行全部三大 Demo
1. PDF 治理：文字矢量提取 (pdfplumber) 与 扫描件图像预处理 + OCR + 后置纠错流水线
2. Word 治理：底层 XML 元素流式保序遍历 (维持图文与表格紧密上下文)
3. Excel 治理：纯明细表 Text2SQL 数据库计算 + 业务规则表转换为行级自包含语义切片
"""

import os
import subprocess
import sys


def run_sub_demo(demo_dir: str, script_name: str, title: str):
    print("\n" + "#" * 80)
    print(f"▶️  正在启动: {title}")
    print("#" * 80 + "\n")
    script_path = os.path.join(demo_dir, script_name)
    ret = subprocess.run([sys.executable, script_path], cwd=demo_dir)
    if ret.returncode != 0:
        print(f"\n❌ 执行异常中断: {title}")
        sys.exit(ret.returncode)


def main():
    root_demos = os.path.dirname(os.path.abspath(__file__))

    demos = [
        ("01_pdf_governance", "run_demo.py", "Demo 1: PDF 文件格式专项治理 (矢量/扫描判别 + 结构化提取 + OCR纠错)"),
        ("02_docx_governance", "run_demo.py", "Demo 2: Word (.docx) 文件格式专项治理 (XML 流式保序遍历与上下文对齐)"),
        ("03_excel_governance", "run_demo.py", "Demo 3: Excel (.xlsx) 格式专项治理 (纯明细 Text2SQL + 规则表行级自包含切片)"),
    ]

    for d_dir, s_name, title in demos:
        full_dir = os.path.join(root_demos, d_dir)
        run_sub_demo(full_dir, s_name, title)

    print("\n" + "=" * 80)
    print("🎉🎉 全部 3 大格式专项治理实战 Demo 均已成功执行完毕！")
    print("=" * 80)


if __name__ == "__main__":
    main()
