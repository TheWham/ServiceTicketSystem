# -*- coding: utf-8 -*-
"""终端演示入口：跑一条链路并打印 ASCII 大盘。

    python -m workflow_demo.cli                # 跑全部用例
    python -m workflow_demo.cli create-ok      # 跑单个用例
    python -m workflow_demo.cli --ask "VPN 连不上怎么办"

没有浏览器时用它看链路；也是排查「页面没数据但接口有数据」的第一步。
"""

from __future__ import annotations

import argparse
import sys

from .cases import DEMO_CASES, get_case
from .engine import DeterministicWorkflow
from .tracer import print_trace_dashboard


def _print_result(result: dict) -> None:
    """打印结论行。verdict / intent / replyType / refusalReason 四项一起给，
    是因为它们分别代表「链路判了什么、走的哪条岔路、怎么回给员工、为什么被拦」。"""
    print(f"\n🎯 裁决：{result['verdict']}  (intent={result['intent']} / "
          f"replyType={result['replyType']}"
          + (f" / {result['refusalReason']}" if result["refusalReason"] else "") + ")")
    if result.get("expected"):
        mark = "✓ 与预期一致" if result["matched"] else f"✗ 预期是 {result['expected']}"
        print(f"   {mark}")
    print(f"   {result['answerText']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="确定性工作流终端演示")
    parser.add_argument("case_id", nargs="?", help="用例 ID；不给则跑全部用例")
    parser.add_argument("--ask", help="自由输入一句话，走与用例相同的流程")
    parser.add_argument("--no-dashboard", action="store_true", help="不打印链路大盘")
    args = parser.parse_args(argv)

    wf = DeterministicWorkflow()   # 进程内复用：数据源与模型客户端只装配一次

    # --ask 与用例走的是同一个 run()，区别只在有没有 case_id（仅影响 Trace 命名与预期比对）
    if args.ask:
        result = wf.run(args.ask)
        _print_result(result)
        if not args.no_dashboard:
            _dashboard(result)
        return 0

    case_ids = [args.case_id] if args.case_id else [c.case_id for c in DEMO_CASES]
    for cid in case_ids:
        if get_case(cid) is None:
            print(f"未知用例：{cid}；可用：{', '.join(c.case_id for c in DEMO_CASES)}")
            return 2
    for cid in case_ids:
        case = get_case(cid)
        print("\n" + "▶" * 28 + f" [{case.label}] " + "◀" * 28)
        result = wf.run_case(cid)
        _print_result(result)
        if not args.no_dashboard:
            _dashboard(result)
    return 0


def _dashboard(result: dict) -> None:
    """响应里的 `trace` 字段就是 Tracer.summary() 的产物，直接喂给大盘渲染。"""
    print_trace_dashboard(result["trace"])


if __name__ == "__main__":
    sys.exit(main())