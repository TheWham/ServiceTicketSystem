# -*- coding: utf-8 -*-
"""SafeText2SQLEngine — 企业级安全 Text2SQL 拦截器（五重门禁 + 真实业务库）。

查询目标是企业真实业务库 `it_ticket_system`（IT 服务工单系统，MySQL 8）。大模型生成的
SQL 在真正 `cursor.execute` 之前经过一道只读门禁，杜绝「删库灾难」与 SQL 注入：

  防线 1：分号多语句拼接拦截（严禁 `;` 批量执行）
  防线 2：危险动词全量扫描（DROP/DELETE/UPDATE/INSERT/ALTER/TRUNCATE/...）
  防线 3：必须 SELECT 开头
  防线 4：表名白名单校验（仅允许授权只读业务表）
  防线 5：强制注入 LIMIT 50（防止无索引大表全量拖库）

说明：本层做应用级门禁（防线 2~5）；防线 1（只读专用账号 + 从库）在生产环境下沉到
连接层——用一个仅 GRANT SELECT 的账号连接，即便门禁被绕过也改不了数据。
"""

import datetime
import decimal
import re
from typing import Any, Dict, Tuple

import pymysql

from . import config as dcfg


def _json_safe(value: Any) -> Any:
    """把 MySQL 返回的 datetime/date/Decimal/bytes 转成 JSON 可序列化类型。"""
    if isinstance(value, datetime.datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


class SafeText2SQLEngine:
    """企业级安全 Text2SQL 拦截器：连真实业务库，只读 SQL 门禁 + 白名单 + 行数熔断。

    白名单聚焦 Day16 教学两大业务域：
      - 工单故障流程：ticket / ticket_transition / ticket_resolution / ticket_acceptance
        / ticket_message / consultation / consultation_message / assignment / sla_instance
        / supplement_request / external_wait / exception_queue / category / support_team / user
      - 知识库卡片：knowledge_article / knowledge_version / knowledge_cluster / rag_index_pointer
    """

    ALLOWED_TABLES = {
        # 工单故障流程
        "ticket", "ticket_transition", "ticket_resolution", "ticket_acceptance",
        "ticket_message", "ticket_field_value", "ticket_duplicate", "ticket_draft",
        "consultation", "consultation_message", "assignment", "sla_instance", "sla_pause",
        "supplement_request", "external_wait", "exception_queue",
        "category", "category_route", "support_team", "team_member", "user",
        # 知识库卡片
        "knowledge_article", "knowledge_version", "knowledge_cluster", "rag_index_pointer",
    }

    DANGEROUS_KEYWORDS = {
        "drop", "delete", "update", "insert", "alter", "truncate",
        "create", "replace", "grant", "revoke", "attach", "detach", "pragma",
        "set", "call", "lock", "unlock",
    }

    def __init__(self, host: str = None, port: int = None, db: str = None,
                 user: str = None, password: str = None):
        self._conn_args = {
            "host": host or dcfg.DB_HOST,
            "port": port or dcfg.DB_PORT,
            "database": db or dcfg.DB_NAME,
            "user": user or dcfg.DB_USER,
            "password": password or dcfg.DB_PASSWORD,
            "charset": "utf8mb4",
            "connect_timeout": 8,
        }

    def _connect(self):
        return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **self._conn_args)

    def validate_sql(self, sql: str) -> Tuple[bool, str, str]:
        """SQL 语法与安全策略门禁验证。返回 (是否通过, 判定信息, 加固后的安全 SQL)。"""
        cleaned_sql = sql.strip().rstrip(";")

        # 防线 1：拦截分号多语句拼接注入
        if ";" in cleaned_sql:
            return False, "【安全违规】检测到多语句分号拼接，严禁批量执行 SQL！", ""

        # 防线 2：危险动词全量扫描
        tokens = re.findall(r"\b[A-Za-z]+\b", cleaned_sql.lower())
        for kw in tokens:
            if kw in self.DANGEROUS_KEYWORDS:
                return False, f"【安全违规】检测到危险操作动词 [{kw.upper()}]，当前接口仅允许只读 SELECT！", ""

        # 防线 3：必须以 SELECT 开头
        if not cleaned_sql.lower().startswith("select"):
            return False, "【安全违规】SQL 必须以标准的 SELECT 关键字开头！", ""

        # 防线 4：检查涉及的表名是否全部在白名单中（兼容反引号 `` `ticket` ``）
        table_matches = re.findall(
            r"(?:from|join)\s+`?([a-zA-Z0-9_]+)`?", cleaned_sql, re.IGNORECASE)
        if not table_matches:
            return False, "【语法异常】未在 SQL 中检测到合法的 FROM/JOIN 数据表声明！", ""
        for t in table_matches:
            if t.lower() not in self.ALLOWED_TABLES:
                return False, f"【权限越界】目标表 [{t}] 未在授权白名单内，禁止访问该数据表！", ""

        # 防线 5：强制注入 LIMIT 限制（防止无索引大表全量拖库）
        if "limit" not in cleaned_sql.lower():
            cleaned_sql += " LIMIT 50"

        return True, "验证通过", cleaned_sql

    def execute_query(self, sql: str) -> Dict[str, Any]:
        """在防御门禁保护下安全执行 SQL（任何非法 SQL 都在门禁处被拦下，绝不落地）。"""
        is_valid, msg, safe_sql = self.validate_sql(sql)
        if not is_valid:
            return {"success": False, "error": msg, "data": []}

        conn = None
        try:
            conn = self._connect()
            with conn.cursor() as cursor:
                cursor.execute(safe_sql)
                rows = cursor.fetchall()
            # 逐行把 datetime/Decimal/bytes 转成 JSON 安全类型（供 role="tool" 回传与出参）
            data = [{k: _json_safe(v) for k, v in row.items()} for row in rows]
            return {
                "success": True,
                "executed_sql": safe_sql,
                "row_count": len(data),
                "data": data,
            }
        except pymysql.Error as e:
            return {
                "success": False,
                "error": f"【SQL 执行期异常】：{str(e)}",
                "data": [],
            }
        finally:
            if conn is not None:
                conn.close()
