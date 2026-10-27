# -*- coding: utf-8 -*-
"""analytics_service —— 跨工单宏观聚合归纳（确定性节点链）。

与 agent_service 的区别：agent_service 让模型决定"调哪个工具、调几次"；本服务把
"聚合维度、占比算法、建议条目"全部固化在代码与词表里，模型只负责最后的措辞。

链路：意图路由 → 投影扫描取数 → 词表抽取 + 聚合（零模型）→ 归因叙事 → 数字/单号门禁。
"""

__all__ = ["config", "taxonomy", "timewindow", "aggregate", "contract", "rules",
           "classifier", "data_source", "nodes", "engine"]