# -*- coding: utf-8 -*-
"""SQLite 存储层（SPEC §1.1~§1.6）。铁律：所有 SQL 一律参数化绑定，禁止字符串拼接。"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS ticket (
  ticket_id            TEXT PRIMARY KEY,
  title                TEXT NOT NULL,
  category             TEXT NOT NULL,
  asset_id             TEXT,
  description          TEXT NOT NULL,
  attachment_urls      TEXT,
  priority             TEXT NOT NULL DEFAULT 'MEDIUM',
  expected_finish_time TEXT,
  ticket_status        TEXT NOT NULL DEFAULT 'CREATED',
  creator_id           TEXT NOT NULL,
  assignee_id          TEXT,
  reject_count         INTEGER NOT NULL DEFAULT 0,
  version              INTEGER NOT NULL DEFAULT 0,
  create_time          TEXT NOT NULL,
  update_time          TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_log (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id       TEXT NOT NULL,
  operator_id     TEXT NOT NULL,
  operator_name   TEXT,
  action          TEXT NOT NULL,
  from_status     TEXT,
  to_status       TEXT,
  remark          TEXT,
  attachment_urls TEXT,
  create_time     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notify_record (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id       TEXT NOT NULL,
  event_type      TEXT NOT NULL,
  receiver_id     TEXT NOT NULL,
  channel_used    TEXT NOT NULL DEFAULT 'LOG',
  is_fallback     INTEGER NOT NULL DEFAULT 0,
  delivery_status TEXT NOT NULL,
  title           TEXT,
  content         TEXT,
  dedup_key       TEXT,
  create_time     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS asset (
  asset_id    TEXT PRIMARY KEY,
  asset_name  TEXT NOT NULL,
  brand_model TEXT,
  owner_id    TEXT,
  status      TEXT NOT NULL DEFAULT 'IN_USE',
  create_time TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dedup_lock (
  lock_key    TEXT PRIMARY KEY,
  expires_at  TEXT NOT NULL,
  create_time TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_id_seq (
  seq_date TEXT PRIMARY KEY,
  seq      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ticket_draft (
  creator_id    TEXT PRIMARY KEY,
  draft_content TEXT,
  update_time   TEXT NOT NULL
);
"""


class SQLiteStore:
    """单连接 SQLite 封装；query_* 返回 dict 行。所有写操作参数化。"""

    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self):
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def execute(self, sql: str, params: tuple = ()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def query_one(self, sql: str, params: tuple = ()):
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def query_all(self, sql: str, params: tuple = ()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]
