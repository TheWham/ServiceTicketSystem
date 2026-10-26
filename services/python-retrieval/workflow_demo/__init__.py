# -*- coding: utf-8 -*-
"""workflow_demo —— 确定性工作流编排 + 链路追踪演示（IT 工单业务）。

把课程 Day17 的「Anthropic 四大确定性编排模式 + Langfuse 式 APM 追踪」落到本项目
的真实业务与真实规则上：意图路由 → 并行扇出 → 确定性裁决 → 动作门禁。

与产品的接入点见 `data_source.DataSource`：本次实现 `SqliteDataSource`（本地种子库），
上线时新增 `HttpDataSource` 指向 ticket-service / consultation-service 即可，节点与追踪器不变。
"""

__all__ = ["__version__"]

__version__ = "0.1.0"