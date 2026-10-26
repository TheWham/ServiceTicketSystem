# analytics_service —— 跨工单宏观聚合归纳

回答「请根据全部网络与打印设备工单，总结本季度共性根因并给出备件建议」这类
**跨多记录宏观归纳**问题。现有 RAG 链路答不了这类问题，且不是调参能解决的：
`retrieval.top_k = 3` + `rerank_granularity = parent` 意味着最多 3 张父卡进生成层，
评测也是单卡命中口径；而**工单从不进入知识库**（知识库语料是 35 张 Wiki 卡片，
工单在 `ticket` 表）。检索器只会捞回 3 条孤立的单次维修记录，模型基于这 3 条硬凑
"三大根因"，是以偏概全的系统性来源。

## 与 agent_service 的区别

| | agent_service | analytics_service |
|---|---|---|
| 形态 | 模型驱动的 ReAct 工具循环 | **确定性节点链** |
| 谁决定"做什么" | 模型（调哪个工具、调几次） | 代码与词表 |
| 模型调用点 | 每一轮 ReAct | **两处**：意图二分类、归因叙事 |
| 数字从哪来 | 工具返回 | **Python 算出，模型无权修改** |

为什么不做成 agent 工具：ReAct 把"调几次、怎么归纳"交给模型，与"聚合维度必须定死"
根本冲突；且 `agent_service/tests/test_tool_contract.py` 断言工具白名单与 Java 侧
严格相等，加工具要同步改两端四文件。

## 五段链路

```
A 意图路由     模型主判 + 规则兜底 + 安全闸（越权在模型调用之前判死）
B 投影扫描     只按时间窗取数，★不做子域粗筛、不做 GROUP BY
C 确定性聚合   ★零模型调用：词表抽取 / 双分母占比 / 覆盖率 / 小样本闸门 / 备件决策表
D 归因叙事     唯一一处叙事模型调用，只喂"已算好的结论"
E 输出门禁     数字与单号必须可溯源；剔除后不足则整体退回确定性模板
```

## 几个关键设计

**子域过滤走词典，不走 `category_id`。** 实测唯一那张打印机工单的 `category_id`
是 `C_HW_PC`（提交人手选的），而 `C_HW_PR` 分类 0 张 —— 按分类过滤会静默漏掉它。
且 Node B **不得**按 category 粗筛：那样它在数据库层就被滤掉，根本活不到 Node C。

**词表禁用裸泛化词。** `无反应` / `无法调节` 这类词单独出现时不构成症状判据。实测反例：
「打印机再次脱机」的描述里同时有"打印机"和"无反应"，「电脑音量无法调节」的描述里也有
"无反应"，任何一条裸泛化词都会把它们从正确标签下抢走。泛化词必须写成复合词
（`电源无反应`）或标注 `requires_device`，加载时校验、违规即抛错。

**双分母。** 每条分布同时给"占本维度"与"占全部工单"两种口径 ——
"打印机故障占 42%"读法是前者，"占本季度全部工单 18%"是后者，口径不明是宏观归纳
最常见的偷换。

**样本不足只降级、不静默。** 全库低于 `MIN_UNIVERSE` 整体拒答并说明原因；条目分母低于
`MIN_DENOM` 或命中低于 `MIN_LABEL_HITS` 时**只给计数、不给占比**。子域样本少是用户
自己限定范围造成的，直接拒答没有信息量，所以不设子域专用阈值，复用 `MIN_DENOM`。

**根因只从 `ticket_resolution` 抽取。** 从工单描述推断根因正是幻觉的主要来源。当前远程库
该表为 0 行，本维度如实声明"无解决方案记录，不可归纳"；词表与读取路径已提前就位，
数据到位即零代码改动生效。

## 词表演化

受控词表的两个需求互相拉扯：口径要**稳定**（否则历史统计不可比、评测不可回归），
覆盖要**演化**（新故障类型出现时词表得跟上）。所以词表外置于
`configs/taxonomy.yaml`，并配一个发现新词的机制：

```bash
python -m analytics_service.pipelines.unmatched_report
```

未命中工单落盘到 `artifacts/analytics/unmatched_<窗口>.jsonl` 并给出词频候选，
经人工确认后入词表、版本 +1。**打标本身只由词典完成** —— LLM 可以提候选，
不参与判定，否则口径不可复现。`taxonomy_coverage_rate` 是这项工作的验收指标（门槛 ≥ 80%）。

## 运行

```bash
# HTTP 服务（默认 127.0.0.1:8340）
python -m analytics_service

# 跑一次链路（默认走 ticket-service 投影扫描接口）
python -m analytics_service.pipelines.demo_analytics --role ENGINEER

# 离线跑（无 Java 服务时），含降级分支
python -m analytics_service.pipelines.demo_analytics \
    --fixture analytics_service/tests/fixtures/tickets_mini.json

# 单测（零网络）
python -m pytest analytics_service/tests -q
```

## 配置

见 `config.py`。生成模型走 `ANALYTICS_LLM_*`，缺省回退 `.env` 的 `LLM_*`；
取数走 `ANALYTICS_TICKET_BASE_URL`（默认 `http://127.0.0.1:8201`）。
统计闸门阈值均可用环境变量覆盖：`ANALYTICS_MIN_UNIVERSE` / `MIN_DENOM` /
`MIN_LABEL_HITS` / `MIN_COVERAGE_WARN`。

**权限**：仅 `ENGINEER` / `PLATFORM_ADMIN` 可调用（`ANALYTICS_ALLOWED_ROLES`）。
跨人聚合是本服务唯一新增权限面，权威判定在 Java 侧，Python 侧这道只用于早退省钱。

## 依赖的上游接口

`GET /api/internal/tickets/analytics/scan`（ticket-service，只读投影扫描）——
按时间窗返回脱敏明细，**不做聚合、不返回姓名与联系方式**。见
`it-ticket-cloud/ticket-service/.../controller/InternalTicketController.java`。

**架构 8.1**：工单是 ticket-service 的事实源，本服务不跨库读 `ticket` 表。