# -*- coding: utf-8 -*-
"""Docstore（文档存储）模块：支持 MySQL 持久化与内存兜底/测试实现。

用于父子切片（Small-to-Big）架构下的父块存储：
- 向量库只索引子块向量与基础元数据（parent_id 等），不再内嵌巨幅 parent_content；
- 父块正文统一由 Docstore 托管，检索命中后按 parent_id 批量回溯。
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymysql
from pymysql.cursors import DictCursor

from .chunking.structure_aware import Document

logger = logging.getLogger(__name__)


class BaseDocstore(ABC):
    """Docstore 统一抽象接口。"""

    @abstractmethod
    def get(self, parent_id: str) -> Optional[str]:
        """按 parent_id 获取父块正文全文。"""
        pass

    @abstractmethod
    def mget(self, parent_ids: List[str]) -> Dict[str, str]:
        """批量获取父块正文，返回 {parent_id: content}。"""
        pass

    @abstractmethod
    def save_documents(self, documents: List[Document]) -> None:
        """批量保存/更新父块文档。"""
        pass


class InMemoryDocstore(BaseDocstore):
    """纯内存文档存储，供单元测试与独立离线运行。"""

    def __init__(self, initial_docs: Optional[Dict[str, str]] = None) -> None:
        self._store: Dict[str, str] = dict(initial_docs or {})

    def get(self, parent_id: str) -> Optional[str]:
        return self._store.get(parent_id)

    def mget(self, parent_ids: List[str]) -> Dict[str, str]:
        return {pid: self._store[pid] for pid in parent_ids if pid in self._store}

    def save_documents(self, documents: List[Document]) -> None:
        for doc in documents:
            pid = doc.metadata.get("parent_id") or doc.metadata.get("wiki_id")
            if pid:
                self._store[pid] = doc.page_content


class MySqlDocstore(BaseDocstore):
    """基于 MySQL 的持久化文档存储（企业级标准方案）。

    存储在 `rag_parent_docstore` 表中。
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        table_name: str = "rag_parent_docstore",
        mapping_path: Optional[Path] = None,
    ) -> None:
        self.host = host or os.environ.get("DB_HOST") or os.environ.get("MYSQL_HOST") or "120.92.138.195"
        self.port = int(port or os.environ.get("DB_PORT") or os.environ.get("MYSQL_PORT") or 3306)
        self.user = user or os.environ.get("DB_USER") or os.environ.get("MYSQL_USERNAME") or "root"
        self.password = password or os.environ.get("DB_PASSWORD") or os.environ.get("MYSQL_PASSWORD") or "clt123456"
        self.database = database or os.environ.get("DB_NAME") or os.environ.get("MYSQL_DATABASE") or "it_ticket_system"
        self.table_name = table_name
        self.mapping_path = mapping_path or (
            Path(__file__).resolve().parents[1] / "data" / "wiki_article_mapping.json"
        )
        self._mapping_cache: Optional[Dict[str, Any]] = None
        self._ensure_table()

    def _get_connection(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            cursorclass=DictCursor,
            connect_timeout=3,
            read_timeout=5,
            write_timeout=5,
            autocommit=True,
        )

    def _ensure_table(self) -> None:
        """确保底层存储表结构存在。"""
        sql = f"""
        CREATE TABLE IF NOT EXISTS `{self.table_name}` (
            `parent_id` VARCHAR(64) PRIMARY KEY,
            `title` VARCHAR(255) NOT NULL DEFAULT '',
            `content` MEDIUMTEXT NOT NULL,
            `metadata` JSON,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RAG 父块文档库 (Small-to-Big Docstore)';
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
        except Exception as e:
            logger.warning("确保 MySQL 父块表存在时发生警告: %s", e)

    def _get_mapping(self) -> Dict[str, Any]:
        if self._mapping_cache is None:
            if self.mapping_path and self.mapping_path.exists():
                try:
                    self._mapping_cache = json.loads(self.mapping_path.read_text(encoding="utf-8"))
                except Exception:
                    self._mapping_cache = {}
            else:
                self._mapping_cache = {}
        return self._mapping_cache

    def save_documents(self, documents: List[Document]) -> None:
        """批量将父块持久化到 MySQL。"""
        if not documents:
            return

        sql = f"""
        INSERT INTO `{self.table_name}` (`parent_id`, `title`, `content`, `metadata`, `updated_at`)
        VALUES (%s, %s, %s, %s, NOW(6))
        ON DUPLICATE KEY UPDATE
            `title` = VALUES(`title`),
            `content` = VALUES(`content`),
            `metadata` = VALUES(`metadata`),
            `updated_at` = NOW(6)
        """
        rows = []
        for doc in documents:
            pid = doc.metadata.get("parent_id") or doc.metadata.get("wiki_id")
            if not pid:
                continue
            title = doc.metadata.get("Header_1") or doc.metadata.get("title") or pid
            # 序列化元数据（移除庞大的重复字段）
            meta_to_save = {k: v for k, v in doc.metadata.items() if k != "parent_content"}
            meta_json = json.dumps(meta_to_save, ensure_ascii=False)
            rows.append((pid, str(title)[:255], doc.page_content, meta_json))

        if not rows:
            return

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, rows)

    def get(self, parent_id: str) -> Optional[str]:
        """获取单个父块全文。"""
        res = self.mget([parent_id])
        return res.get(parent_id)

    def mget(self, parent_ids: List[str]) -> Dict[str, str]:
        """批量获取父块全文，未命中时尝试从 knowledge_version 二级复核。"""
        if not parent_ids:
            return {}

        unique_pids = list(dict.fromkeys(parent_ids))
        results: Dict[str, str] = {}

        print(f"📦 [MySQL Docstore] 触发父块回溯: 正在从 `{self.table_name}` 批量读取 {len(unique_pids)} 个父卡 -> {unique_pids}")

        # 1. 优先从 rag_parent_docstore 批量查询
        format_strings = ",".join(["%s"] * len(unique_pids))
        sql = f"SELECT `parent_id`, `content` FROM `{self.table_name}` WHERE `parent_id` IN ({format_strings})"

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, unique_pids)
                for row in cur.fetchall():
                    results[row["parent_id"]] = row["content"]

        print(f"✅ [MySQL Docstore] 成功从 `{self.table_name}` 获取 {len(results)}/{len(unique_pids)} 个父卡全文")

        missing_pids = [pid for pid in unique_pids if pid not in results]
        if not missing_pids:
            return results

        # 2. 如果 docstore 未命中，尝试根据 wiki_article_mapping 从 knowledge_version 回溯
        mapping = self._get_mapping()
        version_to_pid = {}
        for pid in missing_pids:
            entry = mapping.get(pid)
            if entry and entry.get("versionId"):
                version_to_pid[entry["versionId"]] = pid

        if version_to_pid:
            v_format_strings = ",".join(["%s"] * len(version_to_pid))
            kv_sql = f"SELECT `version_id`, `content` FROM `knowledge_version` WHERE `version_id` IN ({v_format_strings})"
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(kv_sql, list(version_to_pid.keys()))
                    for row in cur.fetchall():
                        vid = row["version_id"]
                        raw_c = row["content"]
                        c_dict = json.loads(raw_c) if isinstance(raw_c, str) else raw_c
                        body = c_dict.get("body", "")
                        # 若正文包含 frontmatter，温和剥离
                        if body.startswith("---"):
                            parts = body.split("---", 2)
                            if len(parts) >= 3:
                                body = parts[2].lstrip()
                        pid = version_to_pid[vid]
                        results[pid] = body

        return results


def build_docstore(cfg: Optional[Any] = None) -> BaseDocstore:
    """根据配置或环境变量构建 Docstore 实例。"""
    docstore_type = "mysql"
    if cfg is not None and hasattr(cfg, "docstore") and isinstance(cfg.docstore, dict):
        docstore_type = cfg.docstore.get("type", docstore_type)
    elif os.environ.get("RAG_DOCSTORE_TYPE"):
        docstore_type = os.environ.get("RAG_DOCSTORE_TYPE", "mysql")

    if docstore_type.lower() == "memory":
        return InMemoryDocstore()

    return MySqlDocstore()
