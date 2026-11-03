# services/python-retrieval/knowledge_flow/checkpointer.py
"""多模持久化 Checkpointer 适配器。

支持将 LangGraph 运行快照落入：
1. MySQL 数据库（生产环境共享持久化）；
2. 本地 SQLite 文件（单机或边缘离线部署）；
3. 纯内存 MemorySaver（单测与隔离运行）。
"""

import os
import json
import sqlite3
import copy
from typing import Dict, Any, List, Optional
from datetime import datetime

# 尝试载入 pymysql
try:
    import pymysql
    from pymysql.cursors import DictCursor
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False


class BaseFlowCheckpointer:
    """Checkpointer 基础接口协议。"""

    def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        state: Dict[str, Any],
        next_node: str,
        interrupted: bool = False,
        interrupt_value: Any = None
    ) -> None:
        raise NotImplementedError

    def get_latest_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def get_checkpoint_by_id(self, thread_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError


class MemoryFlowCheckpointer(BaseFlowCheckpointer):
    """内存 Checkpointer 实现（用于单测与隔离测试）。"""

    def __init__(self):
        # thread_id -> list of checkpoint dicts
        self.storage: Dict[str, List[Dict[str, Any]]] = {}

    def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        state: Dict[str, Any],
        next_node: str,
        interrupted: bool = False,
        interrupt_value: Any = None
    ) -> None:
        history = self.storage.setdefault(thread_id, [])
        history.append({
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "state": copy.deepcopy(state),
            "next_node": next_node,
            "interrupted": interrupted,
            "interrupt_value": copy.deepcopy(interrupt_value),
            "created_at": datetime.now().isoformat()
        })

    def get_latest_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        history = self.storage.get(thread_id, [])
        return copy.deepcopy(history[-1]) if history else None

    def get_checkpoint_by_id(self, thread_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        history = self.storage.get(thread_id, [])
        for item in history:
            if item["checkpoint_id"] == checkpoint_id:
                return copy.deepcopy(item)
        return None

    def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        history = self.storage.get(thread_id, [])
        # 返回从新到旧的排序历史
        return [copy.deepcopy(x) for x in reversed(history)]


class SqliteFlowCheckpointer(BaseFlowCheckpointer):
    """本地 SQLite 文件 Checkpointer（保证服务重启快照不丢失）。"""

    def __init__(self, db_path: str = "artifacts/knowledge_flow_checkpoints.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_flow_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    next_node TEXT NOT NULL,
                    interrupted INTEGER NOT NULL DEFAULT 0,
                    interrupt_value_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_thread ON knowledge_flow_checkpoints (thread_id)")

    def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        state: Dict[str, Any],
        next_node: str,
        interrupted: bool = False,
        interrupt_value: Any = None
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO knowledge_flow_checkpoints
                (thread_id, checkpoint_id, state_json, next_node, interrupted, interrupt_value_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                thread_id,
                checkpoint_id,
                json.dumps(state, ensure_ascii=False),
                next_node,
                1 if interrupted else 0,
                json.dumps(interrupt_value, ensure_ascii=False) if interrupt_value is not None else None,
                datetime.now().isoformat()
            ))

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "thread_id": row[1],
            "checkpoint_id": row[2],
            "state": json.loads(row[3]),
            "next_node": row[4],
            "interrupted": bool(row[5]),
            "interrupt_value": json.loads(row[6]) if row[6] else None,
            "created_at": row[7]
        }

    def get_latest_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, thread_id, checkpoint_id, state_json, next_node, interrupted, interrupt_value_json, created_at
                FROM knowledge_flow_checkpoints
                WHERE thread_id = ?
                ORDER BY id DESC LIMIT 1
            """, (thread_id,))
            row = cur.fetchone()
            return self._row_to_dict(row) if row else None

    def get_checkpoint_by_id(self, thread_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, thread_id, checkpoint_id, state_json, next_node, interrupted, interrupt_value_json, created_at
                FROM knowledge_flow_checkpoints
                WHERE thread_id = ? AND checkpoint_id = ?
                ORDER BY id DESC LIMIT 1
            """, (thread_id, checkpoint_id))
            row = cur.fetchone()
            return self._row_to_dict(row) if row else None

    def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, thread_id, checkpoint_id, state_json, next_node, interrupted, interrupt_value_json, created_at
                FROM knowledge_flow_checkpoints
                WHERE thread_id = ?
                ORDER BY id DESC
            """, (thread_id,))
            rows = cur.fetchall()
            return [self._row_to_dict(r) for r in rows]


class MySqlFlowCheckpointer(BaseFlowCheckpointer):
    """MySQL 数据库 Checkpointer 实现（自动建表并提供优雅降级）。"""

    def __init__(self, fallback: Optional[BaseFlowCheckpointer] = None):
        self.fallback = fallback or SqliteFlowCheckpointer()
        self.host = os.environ.get("DB_HOST") or os.environ.get("MYSQL_HOST") or "120.92.138.195"
        self.port = int(os.environ.get("DB_PORT") or os.environ.get("MYSQL_PORT") or 3306)
        self.user = os.environ.get("DB_USER") or os.environ.get("MYSQL_USERNAME") or "root"
        self.password = os.environ.get("DB_PASSWORD") or os.environ.get("MYSQL_PASSWORD") or "clt123456"
        self.database = os.environ.get("DB_NAME") or os.environ.get("MYSQL_DATABASE") or "it_ticket_system"
        self._available = False
        self._init_mysql()

    def _get_connection(self):
        if not PYMYSQL_AVAILABLE:
            raise RuntimeError("pymysql 未安装")
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            cursorclass=DictCursor,
            connect_timeout=3
        )

    def _init_mysql(self):
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS knowledge_flow_checkpoints (
                            id BIGINT AUTO_INCREMENT PRIMARY KEY,
                            thread_id VARCHAR(64) NOT NULL,
                            checkpoint_id VARCHAR(64) NOT NULL,
                            state_json LONGTEXT NOT NULL,
                            next_node VARCHAR(64) NOT NULL,
                            interrupted TINYINT(1) NOT NULL DEFAULT 0,
                            interrupt_value_json LONGTEXT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_thread (thread_id),
                            INDEX idx_checkpoint (checkpoint_id)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """)
                conn.commit()
            self._available = True
        except Exception:
            # MySQL 暂时不可连时，无缝切换至 fallback 本地 Checkpointer
            self._available = False

    def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        state: Dict[str, Any],
        next_node: str,
        interrupted: bool = False,
        interrupt_value: Any = None
    ) -> None:
        if not self._available:
            return self.fallback.save_checkpoint(thread_id, checkpoint_id, state, next_node, interrupted, interrupt_value)
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO knowledge_flow_checkpoints
                        (thread_id, checkpoint_id, state_json, next_node, interrupted, interrupt_value_json)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        thread_id,
                        checkpoint_id,
                        json.dumps(state, ensure_ascii=False),
                        next_node,
                        1 if interrupted else 0,
                        json.dumps(interrupt_value, ensure_ascii=False) if interrupt_value is not None else None
                    ))
                conn.commit()
        except Exception:
            self._available = False
            self.fallback.save_checkpoint(thread_id, checkpoint_id, state, next_node, interrupted, interrupt_value)

    def get_latest_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        if not self._available:
            return self.fallback.get_latest_checkpoint(thread_id)
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT thread_id, checkpoint_id, state_json, next_node, interrupted, interrupt_value_json, created_at
                        FROM knowledge_flow_checkpoints
                        WHERE thread_id = %s
                        ORDER BY id DESC LIMIT 1
                    """, (thread_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    return {
                        "thread_id": row["thread_id"],
                        "checkpoint_id": row["checkpoint_id"],
                        "state": json.loads(row["state_json"]),
                        "next_node": row["next_node"],
                        "interrupted": bool(row["interrupted"]),
                        "interrupt_value": json.loads(row["interrupt_value_json"]) if row["interrupt_value_json"] else None,
                        "created_at": str(row["created_at"])
                    }
        except Exception:
            self._available = False
            return self.fallback.get_latest_checkpoint(thread_id)

    def get_checkpoint_by_id(self, thread_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        if not self._available:
            return self.fallback.get_checkpoint_by_id(thread_id, checkpoint_id)
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT thread_id, checkpoint_id, state_json, next_node, interrupted, interrupt_value_json, created_at
                        FROM knowledge_flow_checkpoints
                        WHERE thread_id = %s AND checkpoint_id = %s
                        ORDER BY id DESC LIMIT 1
                    """, (thread_id, checkpoint_id))
                    row = cur.fetchone()
                    if not row:
                        return None
                    return {
                        "thread_id": row["thread_id"],
                        "checkpoint_id": row["checkpoint_id"],
                        "state": json.loads(row["state_json"]),
                        "next_node": row["next_node"],
                        "interrupted": bool(row["interrupted"]),
                        "interrupt_value": json.loads(row["interrupt_value_json"]) if row["interrupt_value_json"] else None,
                        "created_at": str(row["created_at"])
                    }
        except Exception:
            self._available = False
            return self.fallback.get_checkpoint_by_id(thread_id, checkpoint_id)

    def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        if not self._available:
            return self.fallback.get_history(thread_id)
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT thread_id, checkpoint_id, state_json, next_node, interrupted, interrupt_value_json, created_at
                        FROM knowledge_flow_checkpoints
                        WHERE thread_id = %s
                        ORDER BY id DESC
                    """, (thread_id,))
                    rows = cur.fetchall()
                    res = []
                    for row in rows:
                        res.append({
                            "thread_id": row["thread_id"],
                            "checkpoint_id": row["checkpoint_id"],
                            "state": json.loads(row["state_json"]),
                            "next_node": row["next_node"],
                            "interrupted": bool(row["interrupted"]),
                            "interrupt_value": json.loads(row["interrupt_value_json"]) if row["interrupt_value_json"] else None,
                            "created_at": str(row["created_at"])
                        })
                    return res
        except Exception:
            self._available = False
            return self.fallback.get_history(thread_id)
