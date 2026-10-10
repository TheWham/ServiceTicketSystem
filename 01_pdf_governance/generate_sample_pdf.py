"""
生成用于 PDF 治理测试的样本文件：
1. 第 1 页：文字型原生矢量页面（包含多段标题、正文、以及包含完整网格线的财务收支表格）
2. 第 2 页：模拟扫描件页面（将文本栅格化渲染为纯位图图片，内部不含直接可选文本）
"""

import os
import fitz  # PyMuPDF


def create_sample_pdf(output_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = fitz.open()

    # ==================== 第 1 页：原生矢量文字与表格页 ====================
    page1 = doc.new_page(width=595, height=842)  # A4 尺寸 (pt)

    # 1. 标题与正文
    page1.insert_text((50, 60), "XX 集团数字化转型专项预算与决议报告", fontname="china-s", fontsize=16)
    page1.insert_text((50, 95), "签发部门：集团战略与信息化委员会    日期：2024-10-15", fontname="china-s", fontsize=10)
    page1.insert_text(
        (50, 130),
        "一、项目背景：本阶段重点围绕企业非结构化数据治理与大模型应用落地展开。",
        fontname="china-s",
        fontsize=11,
    )
    page1.insert_text(
        (50, 150),
        "二、预算明细：各业务板块申报与复核结果汇总如下表所示，需严格按批复执行：",
        fontname="china-s",
        fontsize=11,
    )

    # 2. 绘制规范矢量表格（有边框线，方便 pdfplumber 精准识别 cell）
    table_x0, table_y0 = 50, 180
    row_height = 28
    col_widths = [110, 160, 115, 110]  # 总宽 495
    headers = ["科目代码", "费用核算大类", "审批预算(万元)", "合规评级"]
    data = [
        ["RD-2024-01", "核心大模型微调算力", "1,250.00", "准予立项"],
        ["RD-2024-02", "知识图谱与向量库扩容", "480.00", "准予立项"],
        ["OP-2024-03", "业务人员智能化培训", "95.00", "按期拨付"],
        ["OP-2024-04", "外部数据合规审计评估", "120.00", "按期拨付"],
    ]

    all_rows = [headers] + data

    # 绘制表格边框和文字
    for row_idx, row_data in enumerate(all_rows):
        cur_y0 = table_y0 + row_idx * row_height
        cur_y1 = cur_y0 + row_height
        cur_x = table_x0

        for col_idx, text in enumerate(row_data):
            cell_w = col_widths[col_idx]
            rect = fitz.Rect(cur_x, cur_y0, cur_x + cell_w, cur_y1)
            page1.draw_rect(rect, color=(0.2, 0.2, 0.2), width=0.8)
            text_x = cur_x + 8
            text_y = cur_y0 + 18
            page1.insert_text((text_x, text_y), text, fontname="china-s", fontsize=10)
            cur_x += cell_w

    page1.insert_text(
        (50, table_y0 + len(all_rows) * row_height + 30),
        "三、结论：各业务中心须于第四季度末提交验收报告。",
        fontname="china-s",
        fontsize=11,
    )

    # ==================== 第 2 页：扫描件/图像型 PDF 模拟页 ====================
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((50, 60), "【扫描附件】企业保密协议与外包责任确认单", fontname="china-s", fontsize=15)
    page2.insert_text((50, 100), "甲方单位：武汉智能制造产业基地研发中心", fontname="china-s", fontsize=11)
    page2.insert_text((50, 130), "乙方单位：湖北精密系统工程外包技术服务部", fontname="china-s", fontsize=11)
    page2.insert_text((50, 170), "协议条款摘要：", fontname="china-s", fontsize=11)
    page2.insert_text((50, 200), "1. 乙方派驻人员须遵守甲方数据安全准则，严禁私自拷贝内网知识库。", fontname="china-s", fontsize=10)
    page2.insert_text((50, 230), "2. 履约保证金总额为人民币 100,000.00 元整，通过对公账户转账交付。", fontname="china-s", fontsize=10)
    page2.insert_text((50, 260), "3. 指定结算账号：6222 0210 0012 3456 789，开户行为工行光谷支行。", fontname="china-s", fontsize=10)

    # 将 page2 渲染为位图图片
    pix = page2.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")

    # 移除 page2，新建一个只插入纯图片的页面（模拟真实的扫描 PDF）
    doc.delete_page(1)
    scanned_page = doc.new_page(width=595, height=842)
    img_rect = fitz.Rect(0, 0, 595, 842)
    scanned_page.insert_image(img_rect, stream=img_bytes)

    doc.save(output_path)
    doc.close()
    print(f"[SUCCESS] 样本 PDF 成功生成至: {output_path}")


if __name__ == "__main__":
    sample_file = os.path.join(os.path.dirname(__file__), "enterprise_sample.pdf")
    create_sample_pdf(sample_file)
