# -*- coding: utf-8 -*-
"""Langfuse 配置必须同时支持环境变量与 .env 回退。"""

from agent_service import config as c


def test_langfuse_bool_reads_dotenv(monkeypatch):
    monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
    monkeypatch.setitem(c._DOTENV, "LANGFUSE_ENABLED", "true")
    assert c._langfuse_bool("LANGFUSE_ENABLED", False) is True

    monkeypatch.setitem(c._DOTENV, "LANGFUSE_ENABLED", "false")
    assert c._langfuse_bool("LANGFUSE_ENABLED", False) is False


def test_langfuse_host_alias(monkeypatch):
    monkeypatch.setitem(c._DOTENV, "LANGFUSE_HOST", "")
    monkeypatch.setitem(c._DOTENV, "LANGFUSE_BASE_URL", "https://dotenv.example")
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)
    assert c._langfuse_host() == "https://dotenv.example"

    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://env-base.example")
    assert c._langfuse_host() == "https://env-base.example"

    monkeypatch.setenv("LANGFUSE_HOST", "https://env-host.example")
    assert c._langfuse_host() == "https://env-host.example"
