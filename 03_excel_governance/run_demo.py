"""
Excel (.xlsx) 格式专项治理演示脚本：
演示【纯明细表走 Text2SQL 确定性计算】与【业务规则表转行级自包含切片】双轨落地。
"""

import json
import os
from generate_sample_excel import create_sample_excel
from excel_dual_governor import ExcelDualGovernanceEngine


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_excel = os.path.join(current_dir, "enterprise_data.xlsx")

    print("=" * 70)
    print("🚀 [Demo 3] Excel (.xlsx) 专项治理双轨策略工程落地演示")
    print("=" * 70)

    # 1. 自动生成测试 Excel
    if not os.path.exists(sample_excel):
        print("\n[Step 1] 正在生成包含明细流水与业务规则的仿真 EXCEL 文件...")
        create_sample_excel(sample_excel)
    else:
        print(f"\n[Step 1] 检测到现有样本 EXCEL: {sample_excel}")

    engine = ExcelDualGovernanceEngine(sample_excel)

    # 2. 策略 A: 纯明细表走 Text2SQL 数据库计算
    print("\n" + "=" * 50)
    print("📊 策略 A: 纯明细表专项治理 —— 归因走 Text2SQL (关系数据库计算)")
    print("痛点说明: 严禁将上百行流水表格盲目切词丢给大模型心算，否则必发生算术幻觉！")
    print("=" * 50)

    row_count = engine.setup_detail_table_sql("order_sales_details")
    print(f"[OK] 成功将 {row_count} 条销售流水导入 SQLite 数据库表 `sales_orders`！\n")

    # 模拟场景 1: 多条件聚合统计
    q1 = "统计 2024 年华东大区在政企客户上的销售总额与毛利润是多少？"
    sql1 = """
    SELECT 
        region AS 销售大区,
        client_type AS 客户行业,
        COUNT(*) AS 订单总数,
        ROUND(SUM(sales_amount), 2) AS 总销售额_元,
        ROUND(SUM(sales_amount - cost_amount), 2) AS 预估毛利_元
    FROM sales_orders
    WHERE region = '华东大区' AND client_type = '政企客户'
    GROUP BY region, client_type;
    """
    res1 = engine.execute_text2sql_query(q1, sql1.strip())
    print(f"❓ 用户提问: {res1['user_question']}")
    print(f"🤖 Text2SQL 转换生成 SQL:\n{res1['generated_sql']}")
    print(f"🎯 数据库确定性计算结果:\n{json.dumps(res1['data'], ensure_ascii=False, indent=2)}")

    # 模拟场景 2: 状态分组与平均值
    q2 = "第三季度 (Q3) 各大区已回款订单的平均销售额是多少？"
    sql2 = """
    SELECT 
        region AS 销售大区,
        COUNT(*) AS 回款订单数,
        ROUND(AVG(sales_amount), 2) AS 平均销售额_元
    FROM sales_orders
    WHERE quarter = 'Q3' AND payment_status = '已回款'
    GROUP BY region
    ORDER BY 平均销售额_元 DESC;
    """
    res2 = engine.execute_text2sql_query(q2, sql2.strip())
    print(f"\n❓ 用户提问: {res2['user_question']}")
    print(f"🤖 Text2SQL 转换生成 SQL:\n{res2['generated_sql']}")
    print(f"🎯 数据库确定性计算结果:\n{json.dumps(res2['data'], ensure_ascii=False, indent=2)}")

    # 3. 策略 B: 业务知识与对照表转化为行级自包含切片
    print("\n" + "=" * 50)
    print("📋 策略 B: 业务规则对照表专项治理 —— 转换为【行级自包含切片】")
    print("优势说明: 每一行均显式绑定全量列名表头，即使被单独召回，上下文也 100% 完整自洽！")
    print("=" * 50)

    rule_chunks = engine.generate_row_level_self_contained_chunks("reimbursement_policy")
    print(f"[OK] 成功将规则对照表拆解为 {len(rule_chunks)} 个高内聚自包含切片：\n")

    for i, c in enumerate(rule_chunks):
        print(f"--- [自包含切片 #{i+1} / ID: {c['chunk_id']}] ---")
        print(c["markdown_chunk"])
        print("  -> 附带 Metadata (供向量库精准过滤):", json.dumps(c["json_chunk"]["metadata"], ensure_ascii=False))
        print()

    print("=" * 70)
    print("✅ [Demo 3] Excel 双轨治理流程执行完毕！")
    print("=" * 70)


if __name__ == "__main__":
    main()
