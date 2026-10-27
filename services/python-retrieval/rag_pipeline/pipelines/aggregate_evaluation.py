"""跨工单聚合归纳评测 CLI 装配入口。

    python -m rag_pipeline.pipelines.aggregate_evaluation

与 `golden_evaluation` 并列但**互不依赖**：聚合链路走确定性聚合、不走向量检索，
所以这里既不需要向量库、也不需要 embedding / reranker 配置 —— 启动成本几乎为零。
两者评测的题目由黄金集的 `is_aggregate_check` 字段分流，索引共享一份 JSON。

默认读 `evals/golden_dataset_v2.1.json` 并走 ticket-service 的真实投影扫描接口；
`--fixture` 可在没有 Java 服务的环境下跑完整评测（用于 CI 与本地验证）。
"""

import argparse
import sys
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

from ..config import REPO_ROOT


def _resolve_dataset(raw: str) -> Path:
    """解析黄金集路径。仓库里 evals/ 有两处，按相对路径都能找到：

      · `services/python-retrieval/evals/` —— Python 侧本地副本（v1.0）
      · `<monorepo>/evals/`                 —— DB 闭环的导出目标（v1.1/v2.0/v2.1）

    两处并存是既有事实（`golden_export.py` 写仓库根、检索评测读本地），
    这里按顺序回退而不是把默认值写死成绝对路径 —— 写死会在换机器时静默找不到文件。
    """
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    for base in (REPO_ROOT, REPO_ROOT.parents[1] if len(REPO_ROOT.parents) > 1 else REPO_ROOT):
        path = base / candidate
        if path.exists():
            return path
    return REPO_ROOT / candidate      # 都不存在时返回首选路径，由调用方报错


def run_aggregate_evaluation() -> int:
    parser = argparse.ArgumentParser(description="跨工单聚合归纳评测流水线")
    parser.add_argument("--golden-dataset", default="evals/golden_dataset_v2.1.json",
                        help="黄金问题集路径（取其中 is_aggregate_check=true 的题）")
    parser.add_argument("--output-dir", default="artifacts/evaluation", help="评测产物输出目录")
    parser.add_argument("--fixture", default="",
                        help="离线工单 fixture JSON（不连 ticket-service）")
    parser.add_argument("--role", default="ENGINEER", help="默认调用角色（题目可自带 run_role 覆盖）")
    parser.add_argument("--no-model", action="store_true",
                        help="禁用归因叙事模型（验证确定性模板路径下的指标）")
    args = parser.parse_args()

    print("=" * 80)
    print("🎯 跨工单聚合归纳评测基准流水线")
    print("=" * 80)

    from rag_pipeline.evaluation.aggregate import AggregateSetEvaluator, THRESHOLDS
    from analytics_service.data_source import FixtureDataSource, HttpDataSource
    from analytics_service.model_client import ModelClient, NullModelClient

    golden_path = _resolve_dataset(args.golden_dataset)
    output_path = REPO_ROOT / args.output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    if not golden_path.exists():
        print(f"❌ 找不到黄金问题集：{golden_path}", file=sys.stderr)
        return 1

    if args.fixture:
        ds = FixtureDataSource.from_json(_resolve_dataset(args.fixture))
        print(f"\n[1/2] 取数：离线 fixture {args.fixture}")
    else:
        # 真实路径：按运行时身份走 ticket-service 只读投影扫描接口（架构 8.1，不跨库读）
        ds = HttpDataSource(role=args.role)
        print("\n[1/2] 取数：ticket-service 只读投影扫描接口")

    model = NullModelClient() if args.no_model else ModelClient()
    print(f"       归因叙事模型：{'禁用（走确定性模板）' if args.no_model else (model.model if model.available else '未配置（走确定性模板）')}")

    print(f"\n[2/2] 启动 AggregateSetEvaluator 对《{golden_path.name}》进行量化评估...")
    evaluator = AggregateSetEvaluator(str(golden_path))
    try:
        summary = evaluator.run_evaluation(ds=ds, role=args.role, model=model)
    except Exception as e:  # noqa: BLE001 —— 取数不可用等环境问题要给可读结论而不是栈
        print(f"\n❌ 评测未跑完：{type(e).__name__}: {e}", file=sys.stderr)
        print("   提示：ticket-service 未启动时用 --fixture 跑离线评测。", file=sys.stderr)
        return 1

    report_file = output_path / "跨工单聚合归纳评测报告.md"
    evaluator.generate_markdown_report(report_file, summary)
    print(f"\n🎉 评测报告已成功落盘至：{report_file}")
    print("=" * 80)

    thresholds = THRESHOLDS
    failed = [k for k, v in thresholds.items()
              if summary.get(k) is not None and summary[k] < v]
    if failed:
        print(f"⚠️ 未达标指标：{', '.join(failed)}", file=sys.stderr)
        return 1
    print("✅ 全部指标达标")
    return 0


if __name__ == "__main__":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(run_aggregate_evaluation())