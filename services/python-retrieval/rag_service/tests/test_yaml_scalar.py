# -*- coding: utf-8 -*-
r"""wiki_generator._yaml_scalar 转义单测(Task 2b 裁决 9 加固)。

背景:旧实现只把 `"` 转成 `\"`、不转义反斜杠,值含 `\` 时重写后的
frontmatter 不可解析(ScannerError)或双反斜杠静默变单反斜杠;
render_obj_list 同用该转义,Task 7 批量就地增补前必须修。
标准:标量经 `_yaml_scalar` 渲染后必须能被 `yaml.safe_load` 原样读回。
"""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_pipeline.ingestion.wiki_generator import _yaml_scalar  # noqa: E402


def _roundtrip(value):
    return yaml.safe_load(_yaml_scalar(value))


def test_quote_escaped_roundtrip():
    value = '含"引号"的值'
    assert _roundtrip(value) == value


def test_backslash_escaped_roundtrip():
    value = "C:\\Users\\we12\\path"
    assert _roundtrip(value) == value


def test_double_backslash_roundtrip_not_collapsed():
    value = "a\\\\b"  # 字面双反斜杠,不得静默塌缩成单反斜杠
    assert _roundtrip(value) == "a\\\\b"


def test_backslash_and_quote_combined_roundtrip():
    value = 'C:\\Users\\we1"2\\path'
    assert _roundtrip(value) == value


def test_non_string_scalar_still_quoted():
    assert _yaml_scalar(123) == '"123"'
    assert _yaml_scalar(None) == "null"
    assert _yaml_scalar("") == "null"
