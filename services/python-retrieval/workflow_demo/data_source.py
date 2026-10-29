# -*- coding: utf-8 -*-
"""数据源：工作流与底层事实之间的唯一接缝（这也是接入产品的替换点）。

`DataSource` 协议把工作流需要的事实收拢成 6 个查询。本次实现 `SqliteDataSource`
（本地种子库，一键可跑、不依赖 MySQL）。接入产品时新增 `HttpDataSource`：
- `search_knowledge`   → consultation-service `GET /api/v1/knowledge/search`
- `list_my_tickets`    → ticket-service `GET /api/internal/tickets`
- `create_draft`       → 人机回环：只产草稿，真正建单仍由 Java 侧员工确认触发

边界约定（与项目一致）：
- **数值与路由规则走决策表（SQL）**，不进知识库让模型心算；
- **知识只返回 PUBLISHED 文章的 current_version_id**，历史版本与已下线文章永不外泄
  （项目验收 AC-27 / RD-006）。
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Protocol, Tuple

from . import config as cfg
from .contract import KnowledgeItem, TicketDraft, TicketSummary


class DataSource(Protocol):
    """工作流依赖的全部事实读取入口。实现可换，节点代码不动。"""

    def search_knowledge(self, query: str, category_id: Optional[str] = None,
                         limit: int = 3) -> List[KnowledgeItem]: ...

    def list_my_tickets(self, user_id: str, limit: int = 10) -> List[TicketSummary]: ...

    def find_open_tickets(self, user_id: str, category_id: str,
                          within_hours: int) -> List[TicketSummary]: ...

    def resolve_team(self, category_id: str) -> Optional[Tuple[str, str]]: ...

    def sla_targets(self) -> Dict[str, Dict[str, int]]: ...

    def service_calendar(self) -> Dict[str, Any]: ...

    def create_draft(self, user_id: str, draft: TicketDraft) -> Dict[str, Any]: ...


# ------------------------------------------------------------------ SQLite 实现

def _bigrams(text: str) -> List[str]:
    """中文无分词器下的兜底切分：相邻两字符滑窗，过滤空白。"""
    compact = "".join(ch for ch in text.lower() if not ch.isspace())
    return [compact[i:i + 2] for i in range(len(compact) - 1)]


# 命中判据：关键词字段至少中一个，或标题里至少中两个二元组。
#
# 只靠正文里出现一个泛词不算命中 —— 否则「排查」「申请」这类词会让任何长文档
# 都被召回。与其给员工一条不相关的依据，不如如实说知识库没命中。
_MIN_TITLE_HITS = 2


class SqliteDataSource:
    """本地种子库实现。只读为主；`create_draft` 刻意只存内存（人机回环，不落库）。

    下面几个方法的调用方在链路上是固定的，改动时注意别把查询挪错了节点：
    - `search_knowledge`     → Node 2 并行扇出**左路**
    - `list_my_tickets`      → Node 2 并行扇出**右路**
    - `find_open_tickets`    → Node 3 建单路径（重复单检测）
    - `resolve_team`         → Node 3 建单路径（决策表路由）
    - `sla_targets` / `service_calendar` → Node 3 建单路径（SLA 查表）
    - `create_draft`         → Node 4 门禁**放行分支**，链路上唯一的写操作
    """

    def __init__(self, db_path: Optional[str] = None, schema_path: Optional[str] = None):
        self.db_path = str(db_path or cfg.DB_PATH)
        self.schema_path = str(schema_path or cfg.SCHEMA_PATH)
        self._drafts: List[Dict[str, Any]] = []
        self._draft_seq = 0
        self._ensure_db()
        self._warmup()

    def _warmup(self) -> None:
        """预热：先把连接建立与文件缓存的开销付掉。

        否则第一次请求的并行扇出里，快慢差异会被"谁先抢到连接"掩盖，
        大盘上看到的时延就不反映真实业务分布了。
        """
        conn = self._connect()
        try:
            conn.execute("SELECT 1").fetchall()
        finally:
            conn.close()

    # ---------------------------------------------------------- 建库
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self) -> None:
        import os
        if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0:
            return
        self.rebuild()

    def rebuild(self) -> None:
        """按 schema.sql 重建种子库（演示数据可随时重置）。"""
        with open(self.schema_path, "r", encoding="utf-8") as f:
            script = f.read()
        conn = self._connect()
        try:
            conn.executescript(script)
            conn.commit()
        finally:
            conn.close()

    # ---------------------------------------------------------- 查询
    def search_knowledge(self, query: str, category_id: Optional[str] = None,
                         limit: int = 3) -> List[KnowledgeItem]:
        """只认 PUBLISHED 且只认 current_version_id —— 旧版与已下线文章在 SQL 层就被排除。

        由 Node 2 并行扇出的**左路**调用；命中结果进 state.knowledge，
        后续 Node 3 既拿它定分类，也拿它当引用守卫的白名单。
        """
        sql = (
            "SELECT a.article_id, a.category_id, a.current_version_id, "
            "       v.version_no, v.title, v.summary, v.keywords, v.body "
            "FROM knowledge_article a JOIN knowledge_version v "
            "  ON v.version_id = a.current_version_id "
            "WHERE a.status = 'PUBLISHED'"
        )
        params: List[Any] = []
        if category_id:
            sql += " AND a.category_id = ?"
            params.append(category_id)

        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()

        q_lower = query.lower()
        grams = set(_bigrams(query))
        scored: List[Tuple[float, KnowledgeItem]] = []
        for row in rows:
            keywords = [k for k in str(row["keywords"]).split() if k]
            kw_hits = sum(1 for k in keywords if k.lower() in q_lower)
            title = str(row["title"])
            title_hits = sum(1 for g in grams if g in title.lower())
            body_hits = sum(1 for g in grams if g in str(row["body"]).lower())
            raw = kw_hits * 2 + title_hits * 1.5 + body_hits * 0.5
            if kw_hits == 0 and title_hits < _MIN_TITLE_HITS:
                continue
            score = round(min(1.0, raw / 6.0), 3)
            scored.append((score, KnowledgeItem(
                article_id=row["article_id"],
                version_id=row["current_version_id"],
                version_no=int(row["version_no"]),
                title=title,
                summary=str(row["summary"]),
                body=str(row["body"]),
                category_id=row["category_id"],
                score=score,
            )))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def _ticket_rows(self, sql: str, params: List[Any]) -> List[TicketSummary]:
        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        out: List[TicketSummary] = []
        for r in rows:
            out.append(TicketSummary(
                ticket_id=r["ticket_id"], title=r["title"],
                category_id=r["category_id"], category_name=r["category_name"] or r["category_id"],
                status=r["status"], priority=r["priority"], created_at=r["created_at"],
                assignee_id=r["assignee_id"],
            ))
        return out

    _TICKET_SQL = (
        "SELECT t.*, c.name AS category_name FROM ticket t "
        "LEFT JOIN category c ON c.category_id = t.category_id "
    )

    def list_my_tickets(self, user_id: str, limit: int = 10) -> List[TicketSummary]:
        return self._ticket_rows(
            self._TICKET_SQL + "WHERE t.creator_id = ? ORDER BY t.created_at DESC LIMIT ?",
            [user_id, max(1, min(50, limit))],
        )

    def find_open_tickets(self, user_id: str, category_id: str,
                          within_hours: int) -> List[TicketSummary]:
        """重复单判定依据：同一人、同一分类、窗口内**未结束**的工单。

        CLOSED / CANCELLED 是终态，不算重复。
        """
        return self._ticket_rows(
            self._TICKET_SQL
            + "WHERE t.creator_id = ? AND t.category_id = ? "
              "AND t.status NOT IN ('CLOSED','CANCELLED') "
              "AND t.created_at >= datetime('now', ?) "
              "ORDER BY t.created_at DESC",
            [user_id, category_id, f"-{max(1, within_hours)} hours"],
        )

    def resolve_team(self, category_id: str) -> Optional[Tuple[str, str]]:
        """分类 → 支持组。走 category_route 决策表，不是向量检索。"""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT r.team_id, s.name FROM category_route r "
                "JOIN support_team s ON s.team_id = r.team_id "
                "WHERE r.category_id = ? AND s.status = 'ACTIVE' "
                "ORDER BY r.route_order ASC LIMIT 1",
                [category_id],
            ).fetchone()
        finally:
            conn.close()
        return (row["team_id"], row["name"]) if row else None

    def sla_targets(self) -> Dict[str, Dict[str, int]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT priority, response_target_seconds, completion_target_seconds FROM sla_target"
            ).fetchall()
        finally:
            conn.close()
        return {
            r["priority"]: {
                "responseTargetSeconds": int(r["response_target_seconds"]),
                "completionTargetSeconds": int(r["completion_target_seconds"]),
            }
            for r in rows
        }

    def service_calendar(self) -> Dict[str, Any]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM service_calendar WHERE calendar_id = 'DEFAULT'").fetchone()
        finally:
            conn.close()
        if row is None:
            return {}
        return {
            "calendarId": row["calendar_id"],
            "workWeek": row["work_week"],
            "workStart": row["work_start"],
            "workEnd": row["work_end"],
            "lunchStart": row["lunch_start"],
            "lunchEnd": row["lunch_end"],
            "workdaySeconds": int(row["workday_seconds"]),
        }

    def create_draft(self, user_id: str, draft: TicketDraft) -> Dict[str, Any]:
        """**只产草稿、不落库**：真正建单必须由员工在 Java 侧显式确认触发。

        链路上唯一的写操作，且只可能被 Node 4 的放行分支调到 ——
        拦截/拒答路径连这个方法都不会进，这就是「零副作用」在数据源层的体现。
        """
        self._draft_seq += 1
        record = {
            "draftId": f"DRAFT-{self._draft_seq:04d}",
            "userId": user_id,
            "title": draft.title,
            "description": draft.description,
            "categoryId": draft.category_id,
            "priority": draft.priority,
            "status": "PENDING_EMPLOYEE_CONFIRM",
            "note": "草稿已生成，尚未建单；需员工确认后才会真正创建工单。",
        }
        self._drafts.append(record)
        return record

    def drafts(self) -> List[Dict[str, Any]]:
        """内存中的草稿（进程重启即清空，证明「不落库」）。"""
        return list(self._drafts)