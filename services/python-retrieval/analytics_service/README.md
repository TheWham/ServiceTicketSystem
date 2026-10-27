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
| 模型调用点 | 每一轮 ReAct | **两处**：请求理解（意图 + 槽位）、归因叙事 |
| 数字从哪来 | 工具返回 | **Python 算出，模型无权修改** |
| 时间口径从哪来 | — | **模型给语义槽位（"本季度"），区间由 `timewindow` 算** |

为什么不做成 agent 工具：ReAct 把"调几次、怎么归纳"交给模型，与"聚合维度必须定死"
根本冲突；且 `agent_service/tests/test_tool_contract.py` 断言工具白名单与 Java 侧
严格相等，加工具要同步改两端四文件。

## 五段链路

```
A 请求理解     模型同时出「意图判定」与「槽位」（时间窗 / 范围限定 / 关注维度）
               + 规则兜底 + 安全闸（越权在模型调用之前判死）
               └ 判为非分析型 → **熔断**：REFUSE + OUT_OF_SCOPE，只留 2 个 span
B 投影扫描     定时间口径（模型槽位优先、正则兜底与对照），只按时间窗取数，
               ★不做子域粗筛、不做 GROUP BY
C 确定性聚合   ★零模型调用：词表抽取 / 双分母占比 / 覆盖率 / 小样本闸门 / 备件决策表
D 归因叙事     唯一一处叙事模型调用，只喂"已算好的结论"
E 输出门禁     数字与单号必须可溯源；剔除后不足则整体退回确定性模板
```

**短路出口不回退知识问答。** 判为非分析型时熔断（`REFUSE` / `refusalReason=OUT_OF_SCOPE`）
并在正文里指路，而不是切换成另一套链路。理由是同一个 HTTP 入口若按措辞换链路，答复类型
（统计结论 / 单卡排查步骤）会随用户措辞漂移，前端无从预期渲染哪一套结构 —— 而把
"统计"与"问答"分开正是这条链路存在的理由。

**两个入口的意图归属不同**：看板入口**不预设** `upstreamIntent`，由本链路自行判定、
判非分析型即熔断；客服入口由 Java 分类器先定性并透传 `upstreamIntent=ANALYTICS`，
本链路据此锁死意图、不翻案。两者的差别是刻意的：看板上工程师可能问了具体故障，
而客服入口判错时若也熔断，用户问的本是能正常回答的问题。

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

**根因只从 `ticket_resolution` 抽取。** 从工单描述推断根因正是幻觉的主要来源，所以这条
红线不放松：**没有处置记录就不给根因**，如实声明"无解决方案记录，不可归纳"。

当前库里这条链路是通的——`tools/seed_ticket_resolutions.py` 已写入 28 条处置记录。
> ⚠️ **那 28 条是按工单实际症状写的演示数据，不是真实业务沉淀**（主键 `DEMO-RES-<ticket_id>`
> 前缀，可一键 `--rollback`）。仓库里没有真实处置记录的来源，别把它当历史数据引用。
> 数据一旦换成真实的，链路零代码改动即可生效。

**模型给语义槽位，代码算日期。** 请求里的时间说法（"本季度""第三季度""自9月以来"
"近两周"）由 Node A 的模型抽成 `kind/anchor/quarter/amount` 这类槽位，`Window.start/end`
仍由 `timewindow` 算。理由是模型算错季度边界**不会报错**，只会安静地给一个错误的分母。
唯一例外是用户原话给了两个日期（`EXPLICIT_RANGE`），模型复述 ISO 日期、代码校验格式与量程。

三道配套纪律：

1. **`rawText` 必须在提问里字面出现**，否则整个时间槽位作废、退回正则 —— 与 Node E
   「数字必须可溯源」同构，模型编一个用户没说过的"最近30天"会被当场拦下；
2. **正则解析保留为兜底与对照**。`parse_window` 在没命中时返回的是**默认窗口而不是
   `None`**，所以"两者区间不同"只有在**两边都从字面命中**时才算冲突 —— 否则每一条靠
   模型立功救回来的提问都会误报 `WINDOW_CONFLICT`；
3. **意图判定与槽位抽取相互独立**，提示词里写死了这条。模型一旦把 `intent` 判成
   `NOT_ANALYTICS` 就顺手把槽位全填 `NONE` 是它的常见习性，代码这一侧也不因意图被定性
   而丢弃槽位。

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

**两侧都要配**——Python 侧是服务本身，Java 侧是「要不要把请求分流过来」。

Java 侧（[consultation-service/application.yml](../../../it-ticket-cloud/consultation-service/src/main/resources/application.yml)）：

| 键 | 默认 | 说明 |
|---|---|---|
| `AI_ANALYTICS_ENABLED` | **`true`** | 判定为 ANALYTICS 的请求分流到本服务 |
| `ANALYTICS_SERVICE_BASE_URL` | `http://127.0.0.1:8340` | 本服务基址 |

> ⚠️ **默认开着 = 本服务是硬依赖**。它没启动时，分析型提问会返回 `503 AI_UNAVAILABLE`
> —— 如实拒绝，**不回退成知识问答**。只跑其余链路时设 `AI_ANALYTICS_ENABLED=false`。
> 这与仓库既有约定一致（`retrieval-provider=rag-service` 同样是默认值，同样要求依赖在线）。

Python 侧见 `config.py`。生成模型走 `ANALYTICS_LLM_*`，缺省回退 `.env` 的 `LLM_*`；
取数走 `ANALYTICS_TICKET_BASE_URL`（默认 `http://127.0.0.1:8201`，**必须 ticket-service 在线**）。
统计闸门阈值可用环境变量覆盖：`ANALYTICS_MIN_UNIVERSE` / `MIN_DENOM` / `MIN_LABEL_HITS` / `MIN_COVERAGE_WARN`。

请求理解侧三个开关：

| 键 | 默认 | 说明 |
|---|---|---|
| `ANALYTICS_MODEL_ROUTING` | `1` | 置 `0` 则 Node A 不调模型：意图走规则、时间走正则、子域走词表匹配。**纯确定性演示与回归基线走它** |
| `ANALYTICS_ROUTER_MAX_OUTPUT_TOKENS` | `2048` | 路由调用的输出预算。取代了原来的 `max_tokens=16` —— 本端点的模型是推理模型，思维链会先吃掉额度，16 个 token 很可能连正文都留不下 |
| `ANALYTICS_ROUTER_TIMEOUT` | `60` | 路由调用独立超时，**必须小于** `ANALYTICS_LLM_TIMEOUT`（180）：它跑在取数之前，卡在这里会在做任何实事之前先烧掉这份预算。超时即退回正则 |

> 代价要说清楚：**每次分析请求多一次模型调用**（改造前规则命中时是 0 次）。分析请求本身
> 已要付一次叙事推理，这一趟是小头；想恢复零调用就设 `ANALYTICS_MODEL_ROUTING=0`。

**两份外置配置，都参与配置指纹**（改了口径就不可复现，与索引配置同等对待）：

| 文件 | 管什么 | 注意 |
|---|---|---|
| `configs/taxonomy.yaml` | 受控词表（症状/设备/根因 + 子域） | 词表改了，历史统计口径不可追溯 |
| `configs/analytics.yaml` | 备件系数 | ⚠️ **系数是演示值**，按工程直觉选的，真实场景应改用历史备件消耗数据反推 |

`GET /api/health` 会同时报出两份配置的版本与指纹，运维一眼能看到当前生效的是哪个版本。

**权限**：**仅 `ENGINEER` 可调用**（`ANALYTICS_ALLOWED_ROLES`）。
跨人聚合是本服务唯一新增权限面，权威判定在 Java 侧，Python 侧这道只用于早退省钱。
**改这个白名单要三处一起改**：ticket-service `ANALYTICS_ROLES`、consultation 控制器守卫、
前端 `/analytics` 路由的 `meta.role` 与 `navigationFor` 菜单项 —— 少改一处就会出现
"菜单能进、接口 403"或反过来的割裂。

## 依赖的上游接口

`GET /api/internal/tickets/analytics/scan`（ticket-service，只读投影扫描）——
按时间窗返回脱敏明细，**不做聚合、不返回姓名与联系方式**。见
`it-ticket-cloud/ticket-service/.../controller/InternalTicketController.java`。

**架构 8.1**：工单是 ticket-service 的事实源，本服务不跨库读 `ticket` 表。