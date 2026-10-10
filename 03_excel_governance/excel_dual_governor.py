"""
Excel (.xlsx) 格式专项治理双轨引擎：
1. 策略 A (纯明细表)：接入 SQLite 关系引擎执行 Text2SQL，实现确定性数值统计计算（杜绝大模型算术幻觉）
2. 策略 B (业务规则表)：转换为【行级自包含语义切片】(Markdown & JSON)，确保任意行单独召回时均具备完整表头上下文
"""

import json
import sqlite3
from typing import Dict, List, Any
import pandas as pd


class ExcelDualGovernanceEngine:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.conn = sqlite3.connect(":memory:")

    # ==================== 策略 A: 纯明细表走 Text2SQL ====================

    def setup_detail_table_sql(self, sheet_name: str = "order_sales_details") -> int:
        """将上百行流水明细表导入内存 SQLite，构建结构化查询引擎"""
        df = pd.read_excel(self.excel_path, sheet_name=sheet_name)
        # 重命名为简洁英文字段，便于编写 SQL
        rename_map = {
            "订单流水号": "order_id",
            "销售大区": "region",
            "业务季度": "quarter",
            "客户行业类别": "client_type",
            "合同销售额(元)": "sales_amount",
            "履约交付成本(元)": "cost_amount",
            "回款结算状态": "payment_status",
        }
        df = df.rename(columns=rename_map)
        df.to_sql("sales_orders", self.conn, if_exists="replace", index=False)
        return len(df)

    def execute_text2sql_query(self, user_question: str, sql_query: str) -> Dict[str, Any]:
        """模拟 Text2SQL 逻辑：接收业务提问 -> 转换为确定性 SQL -> 在数据库中执行精准聚合计算"""
        cursor = self.conn.cursor()
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        result_records = [dict(zip(columns, r)) for r in rows]
        return {
            "user_question": user_question,
            "generated_sql": sql_query,
            "row_count": len(result_records),
            "data": result_records,
        }

    # ==================== 策略 B: 规则表转化为行级自包含切片 ====================

    def generate_row_level_self_contained_chunks(
        self, sheet_name: str = "reimbursement_policy"
    ) -> List[Dict[str, Any]]:
        """
        将业务规则/配置对照表逐行转化为自包含 Chunk：
        1. 每一个切片均显式绑定全量列名（表头语义）；
        2. 生成 Markdown 结构化切片（供 RAG 文本检索与 LLM 阅读）；
        3. 生成 JSON 元数据切片（供向量库精确过滤 Filter & 混合检索）。
        """
        df = pd.read_excel(self.excel_path, sheet_name=sheet_name)
        chunks = []

        headers = list(df.columns)

        for idx, row in df.iterrows():
            level_code = str(row.get("职级代码", ""))
            level_name = str(row.get("职级名称", ""))

            # 1. 构造行级自包含 Markdown
            md_lines = [
                f"### [差旅报销与审批规则] 职级代码: {level_code} ({level_name})",
                f"- **基准归属**: 集团财务与差旅管理规定附表",
            ]
            for col in headers:
                val = row[col]
                md_lines.append(f"- **{col}**: {val}")

            md_content = "\n".join(md_lines)

            # 2. 构造带元数据的 JSON 结构
            meta_dict = {
                "chunk_id": f"chunk_policy_{level_code.lower().replace('-', '_')}",
                "level_code": level_code,
                "level_name": level_name,
                "max_stay_first_tier": row.get("一类城市住宿上限(元/天)"),
                "approver": row.get("审批决策人"),
            }

            chunks.append({
                "chunk_id": meta_dict["chunk_id"],
                "markdown_chunk": md_content,
                "json_chunk": {
                    "text": md_content,
                    "metadata": meta_dict,
                }
            })

        return chunks
