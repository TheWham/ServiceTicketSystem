# Day 17 汇报讲稿 · 确定性工作流编排与链路追踪

> **代码位置**：`services/python-retrieval/workflow_demo/`
> **实跑记录**：`artifacts/output/workflow_demo_run_20261020_fixed.txt`（7 个用例全过）
> **演示命令**：`cd services/python-retrieval && python -m workflow_demo`
> **建议时长**：10 分钟（正文 5 节），附录备查

---

## 0. 一句话主张

> **流程骨架由 Python 锁死，模型只在两个点上充当语义单元。**
> 状态怎么流转、分到哪个组、SLA 多久、算不算重复单、能不能碰敏感操作 —— 全部由代码判定。
> 模型只把已有文本说得更顺，不决定发生什么。

这句话是整份汇报的主轴，每个技术点最后都要能落回它。

---

## 1. 开场（1 分钟）：从「自由 ReAct」到「确定性工作流」

先讲问题。让模型自由决定调什么工具、调几次，有三个后果：

| 后果 | 现场表现 |
|---|---|
| **顺序不确定** | 同一个问题两次跑出不同路径，没法回归测试 |
| **可能死循环** | 模型反复调同一个工具，吃掉时延和成本 |
| **出事查不出** | 只看到一句「AI 答错了」，不知道错在第几步 |

> 我们这一版做的事，是**把「发生什么」从模型手里拿走，交给代码**。

---

## 2. 设计（3 分钟）：四个节点，一条链路

```
用户请求 ──> Node 1 意图路由 [ROUTER]
              ├─ UNSUPPORTED / 红线操作 ──> 短路拒答（2 个 span，零副作用）
              │
   KNOWLEDGE_QA / MY_TICKETS / CREATE_TICKET ──> Node 2 并行扇出 [PARALLEL_TASK ×2 + Reducer]
                                                     ├─ 知识检索（只取 PUBLISHED 当前版本）
                                                     └─ 本人工单（creator 由身份绑定）
                                                                │
                                        Node 3 确定性裁决 [EVALUATOR] + 模型终审 [GENERATION]
                                                                │
                                              Node 4 动作门禁 [GATE]
                                                 ├─ DRAFT_READY → 只产草稿，等员工确认
                                                 ├─ BLOCKED / REFUSED → 零副作用
                                                 └─ ANSWERED / NEEDS_INFO
```

**四个模式与 Day17 讲义的对应**（[README.md](../services/python-retrieval/workflow_demo/README.md)）：

| 节点 | 模式 | 说明 |
|---|---|---|
| Node 1 | **Routing** | 意图分类网关，前置分流 |
| 主干 | **Prompt Chaining** | 状态对象在节点间递进 |
| Node 2 | **Parallelization** | 并发查规章 + 查数据库，Reducer 汇聚 |
| Node 3 | **Evaluator** | 规则算 + 模型写，生成前后双重审计 |

**全场最重要的一条约束**：

> **Node 1 和 Node 3 是整条链路上仅有的两处模型调用**，其余节点是纯代码，Token 恒为 0。
> 而且 Node 1 还有一道前置闸：**红线请求和越界请求根本不调模型** ——
> 先调模型再拒绝，等于为一个注定被拦的请求付一次推理费。

---

## 3. 代码走读（4 分钟）：链路过程具体在哪

按执行顺序讲，每段说清「谁在哪、负责什么」。

### ① 入口层

| 位置 | 负责什么 |
|---|---|
| [app.py:70](../services/python-retrieval/workflow_demo/app.py:70) | HTTP 出口，校验 `question`/`caseId`，套统一 `{code,msg,data}` 包络 |
| [app.py:94](../services/python-retrieval/workflow_demo/app.py:94) | 调 `wf.run(...)` |
| [cli.py:33](../services/python-retrieval/workflow_demo/cli.py:33) | 终端入口；与网页吃的是**同一份** `Tracer.summary()` |

> 对外字段刻意复用项目既有词汇（`ReplyType` / `RefusalReason`，见 [contract.py:33](../services/python-retrieval/workflow_demo/contract.py:33)），
> 接 Java 侧不用新造枚举。

### ② 引擎骨架 —— 唯一决定「发生什么」的地方

[engine.py:42 `DeterministicWorkflow.run`](../services/python-retrieval/workflow_demo/engine.py:42)，20 多行，是全场的中枢：

- **建 Tracer**，生成 traceId —— 一次请求一棵 Trace 树
- **装配** `WorkflowContext`（数据源 + 模型 + 追踪器）与 `WorkflowState`（状态对象，Chaining 的载体）
- **跑 Node 1** → 判短路 → 依次跑 Node 2 / 3 / 4
- **兜底**：万一没产出裁决，给 `NEEDS_INFO` 而不是崩

**最值得讲的一处**是 [engine.py:120 `_step`](../services/python-retrieval/workflow_demo/engine.py:120)：

> 节点异常**不向上抛**，记进 `state.errors` 后降级继续。
> 理由写在注释里 —— **「单节点失败不得让整条链路无观测数据」**。

### ③ Node 1 意图路由 [ROUTER] —— 模式 2 Routing

[nodes.py:77 `route_intent`](../services/python-retrieval/workflow_demo/nodes.py:77)。**顺序是重点**：

1. 先跑规则路由（[rules.py:143](../services/python-retrieval/workflow_demo/rules.py:143)）
2. 再跑前置安全闸（[rules.py:107 `guard_sensitive`](../services/python-retrieval/workflow_demo/rules.py:107)）—— 命中红线记 `BLOCK`
3. **这两类规则已能判死，直接跳过模型调用**，省下真金白银
4. 只有需要语义分类时才真调模型
5. 仲裁在 [nodes.py:62 `resolve_intent`](../services/python-retrieval/workflow_demo/nodes.py:62)：

> **规则判越界时模型没有翻案权**（安全优先）；其余情况以模型为准，规则兜底。

安全闸的判定是「**红线词 且 带动手语气**」的合取（见 [rules.py:107](../services/python-retrieval/workflow_demo/rules.py:107) 注释）：

> 所以「VPN 需要管理员权限吗」这类正常咨询**不会**被误伤。

### ④ 短路分支 —— 路由分流的收益就体现在这

[engine.py:136 `_refuse_short_circuit`](../services/python-retrieval/workflow_demo/engine.py:136)：只开一个 `2.Safety_Refusal_FastPath` span，
**一次运行只有 2 个 span**（对比正常路径的 7 个），不查库、不建单。

### ⑤ Node 2 并行扇出 [PARALLEL_TASK] —— 模式 3 Parallelization

[nodes.py:193 `fork_join`](../services/python-retrieval/workflow_demo/nodes.py:193)：

- Reducer span 包住整个 fork→join，它的 duration 就是**真实墙钟耗时**
- `ThreadPoolExecutor(max_workers=2)` 并发跑两路：
  [知识检索 nodes.py:156](../services/python-retrieval/workflow_demo/nodes.py:156) / [本人工单 nodes.py:175](../services/python-retrieval/workflow_demo/nodes.py:175)

**这里有一处很诚实的设计，讲出来加分**：同时记下 `serialEstimateMs`（串行等效）与 `parallelWallMs`（并行墙钟）。

> 本地 SQLite 只有几毫秒时，线程池开销会吃掉大部分收益 ——
> **这个事实被摆在盘面上，而不是藏起来**。换成真实 HTTP 数据源（几十~几百毫秒）时，并行才是净赚。

### ⑥ Node 3 确定性裁决 + 模型终审 —— 模式 4 Evaluator

这是整条链路的灵魂，切成两半讲。

**前半：规则算，模型不参与** —— [nodes.py:259 `evaluate_and_synthesize`](../services/python-retrieval/workflow_demo/nodes.py:259)

- 分类：检索命中的高置信分类优先于关键词规则
- 建单专属三项：优先级 → 支持组（查 `category_route` 决策表）→ SLA（查 `sla_target` 决策表）
- 重复单检测、字段完备性检查
- 得出 `verdict`：`DRAFT_READY` / `BLOCKED` / `NEEDS_INFO` / `ANSWERED`

> 所有判定依据都进 `state.findings` 随响应返回 —— **每一条结论都能追到是哪条规则算的**。

**后半：模型写** —— [nodes.py:424 `_synthesize`](../services/python-retrieval/workflow_demo/nodes.py:424)

- 提示词里那句 **「下面的事实全部由系统规则算出，不得修改、不得补充」**
- 交接边界在 [nodes.py:358 `_facts_block`](../services/python-retrieval/workflow_demo/nodes.py:358)：

> **模型手上根本没有原始数据，只有结论** —— 所以它想改数字也无从改起。

- **引用守卫**（[rules.py:256 `verify_citation`](../services/python-retrieval/workflow_demo/rules.py:256)）：

> 模型声称依据的 versionId 必须在**本次检索结果**里，编造的直接剔除并记一条 finding。

### ⑦ Node 4 动作门禁 [GATE] —— 副作用的总闸

[nodes.py:543 `action_gate`](../services/python-retrieval/workflow_demo/nodes.py:543)：

> **它只读 `state.verdict`（Node 3 定的），不看模型写了什么** ——
> 所以模型再怎么措辞，都推不动这道闸。

- `DRAFT_READY` → 产草稿（[data_source.py:258](../services/python-retrieval/workflow_demo/data_source.py:258)，**只存内存、不落库**）
- `BLOCKED` / `REFUSED` → 标 `INTERCEPTED`，**零副作用**
- 其余 → 只读答复

### ⑧ 两条横切

**追踪内核** [tracer.py](../services/python-retrieval/workflow_demo/tracer.py) —— Trace → Span → Generation 三级拓扑：

| 位置 | 职责 |
|---|---|
| [tracer.py:211 `span`](../services/python-retrieval/workflow_demo/tracer.py:211) / [:218 `generation`](../services/python-retrieval/workflow_demo/tracer.py:218) | 上下文管理器，块结束自动落库 |
| [tracer.py:161 `__exit__`](../services/python-retrieval/workflow_demo/tracer.py:161) | 用 `time.perf_counter()` 单调时钟计时 |
| [tracer.py:245 `summary`](../services/python-retrieval/workflow_demo/tracer.py:245) | 总时延 / Token / 成本 / 最慢节点 |
| [tracer.py:289 `print_trace_dashboard`](../services/python-retrieval/workflow_demo/tracer.py:289) | 终端 ASCII 大盘 |

**数据源接缝** [data_source.py:25 `DataSource`](../services/python-retrieval/workflow_demo/data_source.py:25)：

> 把工作流需要的事实收拢成 6 个查询。换成 `HttpDataSource` 就接上真实系统，**节点代码一行不动**。

---

## 4. 证据（1.5 分钟）：实跑数据

真实模型（kimi-k3），Token 全部来自服务端回传的 `usage`（`reported`），7/7 与预期一致：

| 用例 | 裁决 | 端到端 | 成本 | Router 出 | Synth 出 | 门禁 |
|---|---|---|---|---|---|---|
| ① 知识问答 | ANSWERED | 13787 ms | $0.000546 | 69 | 665 | SUCCESS |
| ② 查我的工单 | ANSWERED | 17672 ms | $0.000875 | 99 | 1184 | SUCCESS |
| ③ 建单放行 | DRAFT_READY | 6527 ms | $0.000514 | 63 | 608 | SUCCESS |
| ④ 重复单拦截 | BLOCKED | 7240 ms | $0.000551 | 161 | 534 | **INTERCEPTED** |
| ⑤ 敏感操作 | REFUSED | **0.11 ms** | **$0** | 0 | — | INTERCEPTED |
| ⑦ 信息不足 | NEEDS_INFO | 6262 ms | $0.000417 | 67 | 443 | SUCCESS |
| ⑥ 越界拒答 | REFUSED | **0.15 ms** | **$0** | 0 | — | INTERCEPTED |

**核心对比（这是全场最有说服力的一组数字）**：

> 主干路径均时延 **10298 ms**、均成本 **$0.00058**；
> 短路路径 **0.13 ms**、**$0** —— 路由分流省掉约 **8 万倍**的时延。
> 7 个用例总花费 **$0.0029**。

④ 的门禁状态是 `INTERCEPTED`，且 `ticketDraft` 为 `null`、`ds.drafts() == []` —— **零副作用有测试兜着**。

> ⚠️ **演示时别承诺具体秒数**：模型时延波动很大（② 在不同轮次跑出 5.4s / 9.9s / 17.7s），
> 因为思维链长度不稳定。讲数量级，不讲精确值。

---

## 5. 收获（1.5 分钟）：两个真实发现

这一段比念数据有分量 —— 讲我们**在真实模型上撞到了什么**。

### 发现一：`max_tokens` 限制的是「思维链 + 正文」的总和

实测 kimi-k3 的响应：

```
message 字段: ['role', 'content', 'reasoning_content', 'tool_calls']
completion_tokens: 234  ← 其中 reasoning_tokens: 213（思维链占 91%）
```

原代码按「分类任务只需几个字」把路由额度设成 **16**，结果**思维链把额度全部吃光、`content` 返回空串**，
`normalize_model_intent` 收敛成 `None`，静默退回规则路由 ——

> **Node 1 的模型语义分类从来没有生效过，而且大盘上完全看不出来**（状态照样 `SUCCESS`），
> 只有翻 span detail 才看得到 `modelNote: "模型原始输出：''"`。

终审额度 512 同样不够：JSON 被拦腰截断，而 [_parse_synthesis](../services/python-retrieval/workflow_demo/nodes.py:511) 当时**把原始文本直接当答复返回** ——

> 员工看到的是 `{"answerText": "您的建单请求未受理：24小时内已有同分类`，
> 或者干脆是一片空白。而链路里记的是 `SUCCESS`。

**修复**（已提交，测试兜底）：

| 改动 | 位置 | 说明 |
|---|---|---|
| 额度按「思维链留够 + 正文够用」取值 | [config.py:88](../services/python-retrieval/workflow_demo/config.py:88) | 路由 16 → 512，终审 512 → 4096 |
| `ModelReply` 带上 `finish_reason` | [model_client.py:50](../services/python-retrieval/workflow_demo/model_client.py:50) | 截断（`length`）才能被上游看见 |
| 解析不出正文时显式降级 | [nodes.py:511](../services/python-retrieval/workflow_demo/nodes.py:511) / [nodes.py:472](../services/python-retrieval/workflow_demo/nodes.py:472) | 改返回 `(正文, 引用, 是否可用)`，拿不出正文**绝不回传原始文本** |
| 降级留痕 | [nodes.py:472](../services/python-retrieval/workflow_demo/nodes.py:472) | span 记 `FAILED` + `degradedReason` + `rawOutput` |

修复后默认配置实测：**7/7 通过、零 JSON 残片、零空答复**，模型路由真实生效
（`modelNote: 模型原始输出：'KNOWLEDGE_QA'`，`decision: 模型与规则判定一致`）。

### 发现二：按项目约定，这不能叫「回退」

项目的 `AGENTS.md` 有一条硬约束：

> **不为外部依赖故障添加静默回退。明确区分失败、正常空结果与业务拒绝，并保留真实原因。**

所以修法不是「悄悄换个模板文案了事」，而是：

> **显式记 `FAILED`、把真实原因和模型原始输出留在链路上，员工拿到可读文案，排查的人拿到证据。**

这正是确定性工作流的价值 —— **失败也是可观测、可归因的**。

### 这一点支撑了汇报主轴

> 我们不是在链路上加一个兜底，而是在**给「不确定性」装上围栏**：
> 模型可以出错，但出错的位置、原因、影响范围，全都留在 Trace 上。

---

## 附录 A · 现场演示步骤

```bash
cd services/python-retrieval && python -m workflow_demo
```

打开 `http://127.0.0.1:8330`，左侧点用例 → 右侧出结论、链路甘特图、节点明细与规则依据。

没有浏览器时用终端（数据与网页是同一份）：

```bash
cd services/python-retrieval && python -m workflow_demo.cli
```

单跑一个用例（**推荐用这个演示短路对比**）：

```bash
cd services/python-retrieval && python -m workflow_demo.cli off-topic
```

**演示顺序建议**：① 知识问答（看正常链路）→ ⑥ 越界拒答（看 2 个 span 的短路）→ ④ 重复单拦截（看门禁零副作用）→ ⑤ 敏感操作（看红线就地拦下）。

> ⚠️ 必须通过服务地址打开，**不要双击 `static/index.html`** ——
> 以 `file://` 打开时页面没有 origin，会报 `Failed to parse URL`。

---

## 附录 B · 可能被问到的问题

**Q：并行扇出到底快了多少？**
A：本地 SQLite 只有 0.6–0.9 ms，线程池开销会吃掉大部分收益，盘面上如实显示「串行等效 Xms → 并行墙钟 Yms」。
换真实 HTTP 数据源（几十~几百毫秒）后墙钟≈两路中较慢者，才是净赚。**不要夸大成"快一倍"。**

**Q：为什么 Node 1 不用 RAG？**
A：意图分类是闭集四选一，提示词 + 规则兜底足够；上 RAG 反而引入检索开销和不确定性。

**Q：模型答错了怎么办？**
A：三段防线 —— 提示词约束「不得修改事实」（事实包里只有结论、没有原始数据）、
引用守卫剔除编造的 versionId、Node 4 门禁不看模型措辞只读 `verdict`。

**Q：成本怎么算的？**
A：`completion_tokens` 含 `reasoning_tokens`，成本按它算没错（思维链确实计费）。
但**别把「输出 token」说成「答复长度」** —— ② 那 1184 个 token 里，大部分是思维链。

**Q：费率准吗？**
A：`TRACE_PRICE_INPUT_PER_M` / `TRACE_PRICE_OUTPUT_PER_M` 默认 0.15/0.60 **只是占位**，
必须按实际模型定价改。**Token 数是真的，单价不是。**

**Q：能接真实系统吗？**
A：新增一个 `HttpDataSource` 实现 [data_source.py:25](../services/python-retrieval/workflow_demo/data_source.py:25) 的协议即可，节点代码一行不动。
`agent_service/tools.py` 里已有这几条 HTTP 调用的写法照抄。
追踪器可以原样被 `agent_service` 复用。

---

## 附录 C · 已知不一致（讲之前先统一口径）

1. **用例编号在 README 与代码里对调了**：
   [cases.py](../services/python-retrieval/workflow_demo/cases.py) 是「⑦ 信息不足」在前、「⑥ 越界拒答」在后，
   而 [README.md:98](../services/python-retrieval/workflow_demo/README.md:98) 的编号正好相反。
   README 那句「⑥ 的 span 数只有 2」按它自己的编号指的是信息不足，但 span 只有 2 的其实是**越界拒答**。
   → 讲的时候统一用本讲稿的顺序：越界拒答 = ⑥，信息不足 = ⑦。

2. **真 Langfuse SDK 上报未实现**，只按 Langfuse 语义预留了字段与结构（`traceId` / `spanName` / `totalCostUsd`）。
   → 被问到就明说：「零依赖本地实现，接真 SDK 只需新增一个 Exporter，业务代码不动」。

3. **本地检索是简单匹配**（关键词字段命中，或标题命中两个以上二元组），不是向量检索。
   → 本 demo 演示的是**编排与观测**，不是检索质量。这点要主动交代，别等人问。

---

## 附：单测

```bash
cd services/python-retrieval && python -m pytest workflow_demo/tests -q
```

当前 **89 passed**（含为本次降级修复新增的 3 条）。