# -*- coding: utf-8 -*-
"""追踪器单测：成本换算、Token 来源标注、异常标记与汇总归因。"""

import pytest

from workflow_demo.tracer import (KIND_GENERATION, KIND_PARALLEL, STATUS_FAILED, STATUS_INTERCEPTED,
                                  TOKENS_ESTIMATED, TOKENS_NONE, TOKENS_REPORTED, Tracer)


@pytest.fixture()
def tracer():
    t = Tracer(trace_id="trace-test", name="wf", workflow="单测", user_id="U1", session_id="S1")
    # 费率取整方便断言：$1/1M 输入，$2/1M 输出
    t.price_input_per_m = 1.0
    t.price_output_per_m = 2.0
    return t


def test_成本按费率折算(tracer):
    with tracer.generation("gen") as g:
        g.record(tokens_in=1_000_000, tokens_out=500_000, tokens_source=TOKENS_REPORTED)
    summary = tracer.summary()
    assert summary["totalCostUsd"] == pytest.approx(1.0 + 1.0, rel=1e-9)
    assert summary["totalTokens"] == 1_500_000


def test_token来源如实标注(tracer):
    with tracer.span("code-only") as s:
        s.record(output={"ok": True})
    with tracer.generation("estimated") as g:
        g.record(tokens_in=100, tokens_out=20, tokens_source=TOKENS_ESTIMATED)

    spans = {s.name: s for s in tracer.spans}
    assert spans["code-only"].tokens_source == TOKENS_NONE
    assert spans["estimated"].tokens_source == TOKENS_ESTIMATED
    assert tracer.summary()["estimatedSpans"] == 1


def test_无token的节点即使声明来源也归为none(tracer):
    """防止把「没调模型的节点」算成模型调用，污染模型调用计数。"""
    with tracer.generation("no-tokens") as g:
        g.record(tokens_source=TOKENS_REPORTED)
    assert tracer.spans[0].tokens_source == TOKENS_NONE
    assert tracer.summary()["modelCallCount"] == 0


def test_异常被标记为FAILED且不外抛(tracer):
    with pytest.raises(ValueError):
        with tracer.span("boom"):
            raise ValueError("炸了")
    span = tracer.spans[0]
    assert span.status == STATUS_FAILED
    assert "ValueError" in span.error


def test_拦截状态与成功状态共存(tracer):
    with tracer.span("blocked") as s:
        s.record(status=STATUS_INTERCEPTED, output={"action": "ABORTED"})
    with tracer.span("ok") as s:
        s.record()
    statuses = {s.name: s.status for s in tracer.spans}
    assert statuses == {"blocked": STATUS_INTERCEPTED, "ok": "SUCCESS"}


def test_汇总给出最慢与最贵节点(tracer):
    with tracer.span("fast") as s:
        s.record()
    with tracer.generation("slow-and-costly") as g:
        g.record(tokens_in=2000, tokens_out=1000, tokens_source=TOKENS_REPORTED)
    summary = tracer.summary()
    assert summary["costliestSpan"]["spanName"] == "slow-and-costly"
    assert summary["slowestSpan"]["spanName"] in ("fast", "slow-and-costly")


def test_甘特偏移单调不减(tracer):
    for i in range(3):
        with tracer.span(f"s{i}") as s:
            s.record()
    offsets = [s.start_offset_ms for s in tracer.spans]
    assert offsets == sorted(offsets)


def test_输入输出摘要被截断(tracer):
    """长 prompt 不得整段回传前端。"""
    long_text = "甲" * 5000
    with tracer.generation("gen") as g:
        g.record(input={"prompt": long_text})
    payload = tracer.spans[0].input["prompt"]
    assert len(payload) < 400
    assert "…(+" in payload


def test_终端大盘渲染同一份摘要(tracer, capsys):
    """网页与终端必须看到同一份数据：大盘只吃 summary() 的产物。"""
    with tracer.generation("3.Answer_Synthesis") as g:
        g.record(tokens_in=500, tokens_out=100, tokens_source=TOKENS_REPORTED)
    tracer.print_dashboard()
    out = capsys.readouterr().out
    assert "链路追踪大盘" in out
    assert "3.Answer_Synthesis" in out
    assert "GENERATION" in out
    assert "reported" in out
    # 有 reported token 时不应出现「含估算」的提示
    assert "含估算" not in out


def test_parallel_span_可并发写入(tracer):
    """并行扇出的两个子任务会在不同线程同时写 tracer，不能丢记录。"""
    import threading
    threads = [threading.Thread(target=lambda n=i: _write_span(tracer, n)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(tracer.spans) == 8
    assert all(s.kind == KIND_PARALLEL for s in tracer.spans)


def _write_span(tracer: Tracer, n: int) -> None:
    with tracer.span(f"p{n}", kind=KIND_PARALLEL) as s:
        s.record(output={"n": n})