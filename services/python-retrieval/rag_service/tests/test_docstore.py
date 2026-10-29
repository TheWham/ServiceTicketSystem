# -*- coding: utf-8 -*-
"""Docstore 模块单元测试：InMemoryDocstore 与 MySqlDocstore 功能验证。"""

import os
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from rag_pipeline.chunking.structure_aware import Document
from rag_pipeline.docstore import InMemoryDocstore, MySqlDocstore, build_docstore


def test_in_memory_docstore_crud():
    docstore = InMemoryDocstore()
    doc1 = Document(page_content="正文1", metadata={"parent_id": "P1", "Header_1": "标题1"})
    doc2 = Document(page_content="正文2", metadata={"parent_id": "P2", "Header_1": "标题2"})

    docstore.save_documents([doc1, doc2])

    assert docstore.get("P1") == "正文1"
    assert docstore.get("P2") == "正文2"
    assert docstore.get("NON_EXIST") is None

    batch = docstore.mget(["P1", "P2", "NON_EXIST"])
    assert batch == {"P1": "正文1", "P2": "正文2"}


def test_build_docstore_factory():
    os.environ["RAG_DOCSTORE_TYPE"] = "memory"
    try:
        ds = build_docstore()
        assert isinstance(ds, InMemoryDocstore)
    finally:
        os.environ.pop("RAG_DOCSTORE_TYPE", None)


def test_mysql_docstore_integration():
    """验证与实际 MySQL 交互的 save/get/mget 能力。"""
    try:
        docstore = MySqlDocstore(table_name="rag_parent_docstore_test")
    except Exception as e:
        pytest.skip(f"MySQL 无法连接或不可用: {e}")

    test_pid = "TEST-PARENT-001"
    test_content = "# 测试父块\n\n这是用于验证 Docstore 的父块正文全文。"
    doc = Document(page_content=test_content, metadata={"parent_id": test_pid, "Header_1": "测试标题"})

    docstore.save_documents([doc])

    fetched = docstore.get(test_pid)
    assert fetched == test_content

    m_fetched = docstore.mget([test_pid, "UNKNOWN-ID"])
    assert m_fetched.get(test_pid) == test_content
    assert "UNKNOWN-ID" not in m_fetched

    # 清理测试数据
    with docstore._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM `{docstore.table_name}` WHERE `parent_id` = %s", (test_pid,))
            cur.execute(f"DROP TABLE IF EXISTS `{docstore.table_name}`")
