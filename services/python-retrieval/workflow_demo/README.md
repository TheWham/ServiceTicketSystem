# workflow_demo · 确定性工作流编排与链路追踪（IT 工单业务）

把课程 Day17 的「Anthropic 四大确定性编排模式 + Langfuse 式 APM 链路追踪」落到本项目的
**真实业务与真实规则**上：IT 服务台的意图路由 → 并行扇出 → 确定性裁决 → 动作门禁。

> 核心原则与项目既有约定一致：**模型只把已有文本说得更顺，不决定发生什么**。
> 状态怎么流转、分到哪个组、SLA 多久、算不算重复单、能不能碰敏感操作 —— 全部由代码判定。

## 快速开始

```bash
cd services/python-retrieval
pip install -r workflow_demo/requirements.txt
python -m workflow_demo            # → http://127.0.0.1:8330
```

打开浏览器就是可视化演示页：左侧点用例 → 右侧出结论、链路甘特图、节点明细与规则依据。

> ⚠️ **必须通过服务地址打开**（`http://127.0.0.1:8330`），不要双击 `static/index.html`。
> 以 `file://` 打开时页面没有 origin，浏览器无法解析 `/api/…` 这类相对地址，
> 会报 `Failed to parse URL`。这种情况页面会直接给出提示和启动命令。

没有浏览器时用终端跑同一套流程（数据和网页是同一份 `Tracer.summary()`）：

```bash
python -m workflow_demo.cli                # 跑全部 7 个用例 + ASCII 大盘
python -m workflow_demo.cli kb-version     # 跑单个用例
python -m workflow_demo.cli --ask "VPN 连不上怎么办"
```

不配模型也能跑：此时走确定性兜底（规则分类 + 模板文案），Token 标记为 `estimated`。

要接真模型，**沿用项目已有的凭据即可**，不必另配一套。读取顺序（与 `rag_pipeline.config` 同款）：

```
进程环境变量 > 仓库根 .env > 服务目录 .env
键名：LLM_BASE_URL / LLM_API_KEY / LLM_CHAT_MODEL   （项目全局，.env 里配的就是这套）
      AGENT_LLM_BASE_URL / AGENT_LLM_API_KEY / AGENT_LLM_MODEL  （agent_service 专用，优先级更高）
```

也就是说，仓库根 `.env` 里填好 `LLM_*` 之后：

```bash
cd services/python-retrieval
python -m workflow_demo            # → http://127.0.0.1:8330
```

页面上顶部提示会由黄转绿：「所有 Token 均来自模型服务端回传的 usage，成本可直接对账」。

> ⚠️ **费率必须按你实际用的模型改**：`TRACE_PRICE_INPUT_PER_M` / `TRACE_PRICE_OUTPUT_PER_M`
> 默认 0.15/0.60 只是占位。Token 数是真的，单价不是 —— 不改费率，金额照样不对。
>
> 另外：本 demo 用 `LLM_CHAT_MODEL` 做普通对话补全（不需要原生 tools）。
> 部分模型（如 kimi-k3）不接受 `temperature` 参数，所以默认不传；
> 要固定随机性再设 `WORKFLOW_DEMO_TEMPERATURE=0`。

也可以从仓库根目录直接起：

```bash
python -m uvicorn workflow_demo.app:app --app-dir services/python-retrieval --host 127.0.0.1 --port 8330
```

## 工作流拓扑

```
用户请求 ──> Node 1 意图路由 [ROUTER]
              ├─ UNSUPPORTED ──────┐
              └─ 红线操作 ────────┤──> 短路拒答（不查库、不建单，只有 2 个 span）
                                  │
   KNOWLEDGE_QA / MY_TICKETS / CREATE_TICKET ──> Node 2 并行扇出 [PARALLEL_TASK ×2 + Reducer]
                                                     ├─ 知识检索（只取 PUBLISHED 当前版本）
                                                     └─ 本人工单（creator 由身份绑定）
                                                                │
                                        Node 3 确定性裁决 [EVALUATOR] + 模型终审 [GENERATION]
                                                                │
                                              Node 4 动作门禁 [GATE]
                                                 ├─ DRAFT_READY → 只产草稿，等员工确认
                                                 ├─ BLOCKED     → 零副作用
                                                 └─ ANSWERED / NEEDS_INFO
```

四个模式与 Day17 讲义的对应：Node 1 是 **Routing**，主干是 **Prompt Chaining**，
Node 2 是 **Parallelization**，Node 3 的「规则算 + 模型写」是 **Evaluator-Optimizer**。

**Node 1 与 Node 3 是仅有的两处模型调用**；其余节点是纯代码，Token 恒为 0。
注意：路由若走了模型，它的 Token 同样计入成本 —— 大盘里的「模型调用」计数按
「Token 来源非 none」统计，不按节点类型。

## 演示用例

| 用例 | 走哪条路 | 看点 |
|---|---|---|
| ① 知识问答 | KNOWLEDGE_QA → ANSWERED | 只召回 v2 现行版本；v1 旧版与 OFFLINE 文章不出现 |
| ② 查我的工单 | MY_TICKETS → ANSWERED | 只返回本人数据；并行扇出第二路真正起作用 |
| ③ 建单放行 | CREATE_TICKET → DRAFT_READY | 决策表路由到 T_HW；HIGH → 完成 SLA 4 个工作小时 |
| ④ 重复单拦截 | CREATE_TICKET → BLOCKED | 24h 内同分类未结束工单 → 门禁拦截，零副作用 |
| ⑤ 敏感操作 | 前置安全闸 → REFUSED | 提权红线就地拦下，不给模型翻案机会 |
| ⑥ 信息不足 | CREATE_TICKET → NEEDS_INFO | 字段不全不是违规：回问员工（replyType = CLARIFY） |
| ⑦ 越界拒答 | UNSUPPORTED → REFUSED | 短路返回，跳过并行扇出 |

跑完用例后，左侧「多次运行对比」会把它们的时延与成本并排画出来 ——
⑥ 的 span 数只有 2，直观看到路由分流省掉了什么。

## 目录

| 文件 | 职责 |
|---|---|
| `engine.py` | 工作流骨架：节点按硬编码顺序串起来，挂上追踪，节点失败降级继续 |
| `nodes.py` | 四个节点的业务实现 |
| `rules.py` | 确定性规则层：分类、优先级、SLA、重复单、敏感拦截、引用守卫 |
| `tracer.py` | Trace → Span → Generation 追踪内核（零依赖，字段对齐 Langfuse 语义） |
| `data_source.py` | **接入点**：`DataSource` 协议 + 本地 SQLite 实现 |
| `cases.py` | 演示用例清单 |
| `app.py` / `static/index.html` | FastAPI 出口 + 单文件可视化页 |
| `cli.py` | 终端入口：跑用例并打印 ASCII 大盘 |
| `schema.sql` | 本地种子库（表结构与数据照抄项目事实源） |
| `tests/` | 85 条单测 |

## 追踪器：三处刻意不照抄 Day17 讲义

1. **计时用 `time.perf_counter()`**（单调时钟）。讲义用 `time.time()`，会被系统时钟调整影响。
2. **Token 标注来源**：`reported`（模型 API 回传的 `usage`）/ `estimated`（本地估算）/
   `none`（本节点不涉模型）。讲义把硬编码的假数字和真实 usage 用同样方式打印，
   看起来一样可信；这里两者在页面与大盘上分开显示。
3. **费率配置化**（`TRACE_PRICE_INPUT_PER_M` / `TRACE_PRICE_OUTPUT_PER_M`），不硬编码。
   默认值 0.15/0.60 只是占位，**必须按你实际模型的定价改**。

## 接入产品（替换点）

工作流、节点、追踪器都不依赖具体数据来源。要接到真实系统，只需新增一个 `HttpDataSource`：

| `DataSource` 方法 | 接入目标 |
|---|---|
| `search_knowledge` | consultation-service `GET /api/v1/knowledge/search` |
| `list_my_tickets` | ticket-service `GET /api/internal/tickets`（透传 `X-User-Id`） |
| `find_open_tickets` | ticket-service 工单列表 + 状态过滤（或在 ticket-service 侧加专用内部接口） |
| `resolve_team` / `sla_targets` | 平台配置域的 `category_route` / SLA 目标表 |
| `create_draft` | **保持不落库**：真正建单仍由员工在 Java 侧确认触发 |

`agent_service/tools.py` 里已有这几条 HTTP 调用的写法与 `X-User-Id` 透传约定，照抄即可。
追踪器可以原样被 `agent_service` 复用。

## 边界与已知取舍

- **本地 SQLite 不引入向量库**：本 demo 演示的是编排与观测，不是检索质量。
  检索是「关键词字段命中，或标题命中两个以上二元组」的简单匹配 ——
  正文里只出现一个泛词（如「排查」）不算命中，宁可说没命中也不给不相关依据。
- **敏感操作判定是「红线词 且 带动手语气」的合取**，所以「VPN 需要管理员权限吗」
  这类正常咨询不会被误伤。这是保守策略的取舍：宁可拒答，不可放行。
- **并行扇出的收益在本地是看不全的**：任务只有几毫秒时，线程池开销会吃掉大部分收益
  （页面上会如实显示「串行等效 Xms → 并行墙钟 Yms」）。换成真实 HTTP 数据源后，
  墙钟≈两路中较慢者，才是净赚。
- **草稿只存内存**：进程重启即清空，这正是「不落库」的证明。
- **真 Langfuse SDK 上报未实现**，只按 Langfuse 语义预留了字段与结构。

## 测试

```bash
cd services/python-retrieval
python -m pytest workflow_demo/tests -q
```