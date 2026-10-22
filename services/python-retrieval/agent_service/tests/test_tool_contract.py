# -*- coding: utf-8 -*-
"""工具契约防漂移测试：Java 侧判定白名单 与 Python 侧 tool_specs() 必须一致。

consultation-service 的 `RequestVerdict.TOOLS`（Java 白名单）与
`agent_service/tools.py::tool_specs()`（工具 schema）各定义了一次工具名。
任何一侧加/改/删工具而另一侧没跟上，判定就会静默失效（plan 里的「契约防漂移」）。
这里把两份名单拉到一起比对，漂移直接红。
"""

import re
from pathlib import Path

import pytest

from agent_service.tools import tool_specs

JAVA_VERDICT = (Path(__file__).resolve().parents[4]
                / "it-ticket-cloud" / "consultation-service" / "src" / "main" / "java"
                / "com" / "itticket" / "consultation" / "adapter" / "policy" / "RequestVerdict.java")


def _python_tool_names() -> set:
    """tool_specs() 里可被路由的工具名（search_knowledge 由 agent 自主补搜，不在 Java 判定空间）。"""
    return {spec["function"]["name"] for spec in tool_specs()} - {"search_knowledge"}


def _java_whitelist() -> set:
    text = JAVA_VERDICT.read_text(encoding="utf-8")
    match = re.search(r"Set\.of\(([^)]*)\)", text)
    assert match, f"RequestVerdict.java 里找不到 Set.of(...) 白名单: {JAVA_VERDICT}"
    return {name.strip().strip('"') for name in match.group(1).split(",") if name.strip()}


@pytest.mark.skipif(not JAVA_VERDICT.exists(), reason="monorepo 布局变化：找不到 RequestVerdict.java")
def test_java_whitelist_matches_python_tool_specs():
    java = _java_whitelist()
    python = _python_tool_names()
    assert java == python, (
        "工具名单两端漂移了：\n"
        f"  仅 Java 有: {sorted(java - python)}\n"
        f"  仅 Python 有: {sorted(python - java)}\n"
        "两侧应同时增删（RequestVerdict.TOOLS ↔ tool_specs()）。")


def test_python_tools_all_have_schema_and_handler():
    """每个工具都要有 description 和参数定义，且在派发表里注册了实现（漏注册会静默失败）。"""
    from agent_service import tools
    registered = tools._HANDLERS
    for spec in tools.tool_specs():
        fn = spec["function"]
        assert fn.get("description"), f"工具 {fn['name']} 缺 description（模型靠它决定调不调）"
        assert "properties" in fn.get("parameters", {}), f"工具 {fn['name']} 缺参数 schema"
        assert fn["name"] in registered, f"工具 {fn['name']} 没有注册 handler（dispatch 会报未知工具）"
