# -*- coding: utf-8 -*-
"""graph 配置段（rag_pipeline.config）的守护测试（Task 8）。

钉死四条不变量：
1. **默认关**：`graph.enabled` 默认 false（Ruling 19：写而不启用）——
   真实 pipeline.yaml 与「无 graph 段」两种形态都必须装出 enabled=False，
   升级本任务对现网零行为变化；
2. **凭证走环境变量**：`password` 直填仅限本地测试且优先级更高；
   为空时从 `password_env` 指名的环境变量取；两者皆空且 enabled=true
   → 加载期抛错（不静默带空密码去连 Neo4j）；
3. **decay 界内**：必须严格 0<decay<1——decay=1.0 会让扩展分=源卡分，
   破坏「扩展分严格低于基础分」与 topScore 语义（Review Focus 4）；
4. **REPLACES 拒绝**：REPLACES 永不进热路径白名单，配了即视为配错，
   加载期 ValueError 拒绝；不含 REPLACES 时打告警日志说明其不参与扩展。
"""

import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_pipeline.config import load_config  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_YAML = REPO_ROOT / "configs" / "pipeline.yaml"

# 测试专用 env 名：绝不与仓库 .env / 真实 NEO4J_PASSWORD 撞车
TEST_PW_ENV = "ITKB_TEST_NEO4J_PASSWORD"

# graph 段模板：enabled 默认 true（便于测凭证/校验），各用例按需覆写
GRAPH_TMPL = """
graph:
  enabled: {enabled}
  neo4j:
    uri: "bolt://localhost:7687"
    username: "neo4j"
    password_env: "{pw_env}"
    password: "{password}"
  expansion:
    edge_whitelist: [{whitelist}]
    max_neighbors: 2
    decay: {decay}
    score_floor: 0.10
    timeout_ms: 300
"""


def graph_yaml(*, enabled="true", password="", pw_env=TEST_PW_ENV,
               whitelist="SAME_ROOT_CAUSE, RELATED, PROCESS_APPLIES",
               decay="0.5") -> str:
    return GRAPH_TMPL.format(enabled=enabled, password=password, pw_env=pw_env,
                             whitelist=whitelist, decay=decay)


def write_yaml(tmp_path, text: str) -> str:
    p = tmp_path / "pipeline.yaml"
    p.write_text(text, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------- 默认关

def test_real_yaml_ships_graph_disabled():
    """真实 pipeline.yaml 的 graph 段逐值对账（spec 配置汇总逐字）。"""
    cfg = load_config(str(REAL_YAML))
    assert cfg.graph.enabled is False
    assert cfg.graph.neo4j.uri == "bolt://localhost:7687"
    assert cfg.graph.neo4j.username == "neo4j"
    assert cfg.graph.neo4j.password_env == "NEO4J_PASSWORD"
    assert cfg.graph.expansion.edge_whitelist == [
        "SAME_ROOT_CAUSE", "RELATED", "PROCESS_APPLIES"]
    assert cfg.graph.expansion.max_neighbors == 2
    assert cfg.graph.expansion.decay == 0.5
    assert cfg.graph.expansion.score_floor == pytest.approx(0.10)
    assert cfg.graph.expansion.timeout_ms == 300


def test_missing_graph_section_defaults_off(tmp_path):
    """无 graph 段：全部走 dataclass 内置默认（enabled=False，= 现网行为）。"""
    p = tmp_path / "p.yaml"
    p.write_text("chunking:\n  child_size: 128\n", encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg.graph.enabled is False
    assert cfg.graph.expansion.decay == 0.5
    assert cfg.graph.neo4j.password_env == "NEO4J_PASSWORD"


# ---------------------------------------------------------------- 凭证

def test_password_taken_from_named_env(tmp_path, monkeypatch):
    """password 为空 → 从 password_env 指名的环境变量取。"""
    monkeypatch.setenv(TEST_PW_ENV, "env-secret")
    cfg = load_config(write_yaml(tmp_path, graph_yaml(password="")))
    assert cfg.graph.neo4j.password == "env-secret"


def test_password_direct_fill_wins_over_env(tmp_path, monkeypatch):
    """password 直填（本地测试）优先级高于环境变量。"""
    monkeypatch.setenv(TEST_PW_ENV, "env-secret")
    cfg = load_config(write_yaml(tmp_path, graph_yaml(password="local-only")))
    assert cfg.graph.neo4j.password == "local-only"


def test_enabled_without_any_credential_raises(tmp_path, monkeypatch):
    """enabled=true 且 password/env 皆空 → 加载期抛错，不带空密码上路。"""
    monkeypatch.delenv(TEST_PW_ENV, raising=False)
    with pytest.raises(ValueError):
        load_config(write_yaml(tmp_path, graph_yaml(password="")))


def test_disabled_without_credential_loads_fine(tmp_path, monkeypatch):
    """enabled=false 且无凭证 → 正常加载（默认形态本就没有凭证）。"""
    monkeypatch.delenv(TEST_PW_ENV, raising=False)
    cfg = load_config(write_yaml(tmp_path, graph_yaml(enabled="false", password="")))
    assert cfg.graph.enabled is False
    assert cfg.graph.neo4j.password == ""


# ---------------------------------------------------------------- 校验

@pytest.mark.parametrize("bad_decay", ["1.0", "0", "1.5", "-0.1"])
def test_degenerate_decay_rejected(tmp_path, bad_decay):
    """decay ≥1 或 ≤0 → ValueError（Review Focus 4：扩展分必须严格低于源卡）。"""
    with pytest.raises(ValueError):
        load_config(write_yaml(tmp_path, graph_yaml(decay=bad_decay)))


def test_replaces_in_whitelist_rejected(tmp_path):
    """REPLACES 进白名单 → 加载期 ValueError（永不进热路径，配了就是配错）。"""
    with pytest.raises(ValueError):
        load_config(write_yaml(tmp_path,
                               graph_yaml(whitelist="SAME_ROOT_CAUSE, REPLACES")))


def test_whitelist_without_replaces_logs_warning(tmp_path, caplog, monkeypatch):
    """不含 REPLACES 的白名单 → 告警日志说明 REPLACES 不参与图扩展。"""
    monkeypatch.setenv(TEST_PW_ENV, "env-secret")  # enabled=true 需有凭证，否则先被凭证校验拒
    with caplog.at_level(logging.WARNING, logger="rag_pipeline.config"):
        cfg = load_config(write_yaml(tmp_path, graph_yaml()))
    assert cfg.graph.enabled is True  # 前置：确实加载成功
    assert any("REPLACES" in r.getMessage() for r in caplog.records), (
        "白名单不含 REPLACES 时应打告警日志，当前 records: "
        f"{[r.getMessage() for r in caplog.records]}" )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
