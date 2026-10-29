# -*- coding: utf-8 -*-
"""端到端跑一次分析链路，并打印结论 + facts + 链路大盘。

默认走 ticket-service 的真实投影扫描接口；`--fixture` 可改读离线 JSON
（用于没有 Java 服务的环境下验证整条链路，包括降级分支）。

用法（在 services/python-retrieval 目录下）：
    python -m analytics_service.pipelines.demo_analytics \
        --question "请根据全部网络与打印设备工单，总结本季度共性根因并给出备件建议"
    python -m analytics_service.pipelines.demo_analytics --fixture tests/fixtures/tickets.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _print_result(result: dict) -> None:
    print("=" * 88)
    print(f"问题：{result.get('question')}")
    print(f"意图：{result.get('intent')}    裁决：{result.get('verdict')}"
          f"    replyType：{result.get('replyType')}    置信度：{result.get('confidence')}")
    win = result.get("window") or {}
    print(f"口径：{win.get('label')}（{win.get('start')} ~ {win.get('end')}）"
          f"  来源：{win.get('source')}")
    if result.get("scope"):
        print(f"范围限定：{'、'.join(result['scope'])}")
    if result.get("degradedReason"):
        print(f"降级原因：{result['degradedReason']}")

    facts = result.get("analyticsFacts") or {}
    if facts:
        uni = facts.get("universe") or {}
        cov = facts.get("coverage") or {}
        print(f"\n样本：时间窗内有效 {uni.get('total')} 单 / 纳入统计 {uni.get('scoped')} 单"
              f"  |  标签覆盖率 {cov.get('ratio')}%")

        for dim in facts.get("dimensions") or []:
            entries = dim.get("entries") or []
            if not entries:
                print(f"\n[{dim.get('axis')}] 该维度无法归纳（无可用来源）")
                continue
            print(f"\n[{dim.get('axis')}]")
            for e in entries:
                if e.get("ratio") is not None:
                    print(f"  {e['label']:<22} {e['count']:>3} 单   "
                          f"占本维度 {e['ratio']}%  占全部 {e['ratioOfAll']}%")
                else:
                    print(f"  {e['label']:<22} {e['count']:>3} 单   （样本不足，不出占比）")

        if facts.get("recommendations"):
            print("\n[建议（由决策表产出，模型无权增删）]")
            for r in facts["recommendations"]:
                print(f"  [{r.get('kind')}] {r.get('text')}")

        if facts.get("gates"):
            print("\n[闸门]")
            for g in facts["gates"]:
                print(f"  {g.get('severity'):<5} {g.get('code'):<24} {g.get('message')}")

    print("\n[结论正文]")
    print(result.get("answerText") or "(空)")

    if result.get("findings"):
        print("\n[判定依据]")
        for f in result["findings"]:
            print(f"  {f.get('severity'):<5} {f.get('code'):<24} {f.get('message')}")
    if result.get("errors"):
        print("\n[节点异常]")
        for e in result["errors"]:
            print(f"  {e}")


def main(argv=None) -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="跑一次跨工单聚合分析链路")
    parser.add_argument("--question", default=(
        "请根据知识库中记录的全部网络与打印设备维护工单，全面总结本季度暴露出的共性根因，"
        "并给出下季度的预防性备件采购与巡检建议。"))
    parser.add_argument("--role", default="ENGINEER", help="调用方角色（EMPLOYEE 会被拒答）")
    parser.add_argument("--user-id", default="U_ENG01")
    parser.add_argument("--fixture", default="", help="离线 fixture JSON 路径（不连 ticket-service）")
    parser.add_argument("--json", action="store_true", help="只输出原始 JSON")
    parser.add_argument("--dashboard", action="store_true", help="额外打印终端链路大盘")
    args = parser.parse_args(argv)

    from ..contract import TicketRow
    from ..data_source import FixtureDataSource, HttpDataSource
    from ..engine import AnalyticsWorkflow

    ds = None
    if args.fixture:
        ds = FixtureDataSource.from_json(Path(args.fixture))
    else:
        ds = HttpDataSource(user_id=args.user_id, role=args.role)

    wf = AnalyticsWorkflow(ds=ds)
    result = wf.run(args.question, user_id=args.user_id, role=args.role)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    _print_result(result)
    if args.dashboard:
        from ..engine import print_dashboard
        print()
        print_dashboard(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())