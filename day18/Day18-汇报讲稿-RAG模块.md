# Day 18 汇报讲稿 · RAG 模块（版本消歧查询）

> **代码位置**：`services/python-retrieval/rag_pipeline/policy.py`、`rag_service/`
> **实跑记录**：`artifacts/output/day18_rag_policy_run_20261021.txt`（5 个用例，打真服务）
> **演示命令**：见「附录 A · 现场演示步骤」
> **建议时长**：8 分钟（正文 5 节），附录备查
> **交付位置**：本模块的两个提交在 `main` 上 —— `e321982`（能力）、`c1dde79`（HTTP 出口）

---

## 0. 一句话主张

> **「哪一版规约有效」由代码按时间点判定，不由模型猜。
> 判不出来就说判不出来，不假装知道。**

Day18 第一阶要的是「按实体属性 + 时间点查出一条适用规约」。我们做的就是这个：
给检索内核补上**时间维度**。它不给答案填空，它给的是**依据 + 角标 + 版本号**，
后面第三阶的交叉裁决拿这些去算。

---

## 1. 开场（1 分钟）：这个模块补的是哪块空缺

Day18 四阶动线的**第一阶是「规则认知（Knowledge RAG）」**，教材里它长这样：

```python
# day18/run_day18_triad_agent.py:305
def _stage1_knowledge_rag(city_tier, employee_role, expense_date):
    """检索企业 Wiki 资产库，严格区分新老制度分水岭 (2024-03-01)"""
    is_after_new_policy = (expense_date >= "2024-03-01")
    ...
```

教材里这一阶是**硬编码 if-else**，实际并没有去检索知识库（`citation` 那是写死的字符串）。
但它的**需求是真的**：给定一个时间点，判断该用哪一版规约。

我们已有的检索内核能做什么、不能做什么：

| 能力 | 现状 |
|---|---|
| 语义检索（BM25 + Dense + RRF + Cross-Encoder 精排） | ✅ 有 |
| 溯源角标（`articleId@versionId 《标题》`） | ✅ 有 |
| **按时间点判定版本** | ❌ **缺** |

已有的「版本消歧」是**另一回事**：`retrieval.default_exclude` 会在召回**前置**物理屏蔽
`wiki_status ∈ {已废止, 已下线}` 的卡。那回答的是「**别把废止做法教给员工**」。

我们要回答的是「**2024-02-20 那天，该用哪一版**」——它必须**看得见旧版**，
才能判断旧版在那一刻是否还有效。**两者需求相反，不能共用一套召回配置。**

这是我们这次动的第一处，也是最小的一处：给检索器的三个方法加了
`include_excluded: bool = False`，默认值保持改前行为。

---

## 2. 设计（2 分钟）：一条链、四种结论

```
                     query（主题）  +  at（时间点）
                            │
        ┌───────────────────┴───────────────────┐
        │ ① 召回候选（include_excluded=True）    │  ← 必须看得见废止卡
        │    hybrid_rerank_search()              │
        └───────────────────┬───────────────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │ ② 定主题：按分数最高的候选作为锚点     │
        │    沿它的 replaces 版本链展开           │  ← 只走已声明的边，不软匹配
        └───────────────────┬───────────────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │ ③ 链内选版本：effective_date <= at 的  │
        │    最新一版                             │
        └───────────────────┬───────────────────┘
                            ▼
              版本号 + 生效日 + 被取代日 + 溯源角标 + 条文
```

### 四种结论，不互相冒充

| status | 含义 | 为什么要单独分出来 |
|---|---|---|
| `RESOLVED` | 选中该时刻有效的一版 | 正常路径 |
| `NO_EFFECTIVE_VERSION` | 相关规约在该时刻**尚未生效** | 制度还没出台，不是「没找到」 |
| `UNDATED` | 版本链上**没有任何一张带生效日期** | **无法判定**——不猜 |
| `NO_MATCH` | 检索零命中 | 知识库里真的没有 |

> `UNDATED` 是这套设计里最要紧的一态。39 张卡里只有 6 张带生效日期，
> 其余 33 张没有。对没日期的卡，唯一诚实的回答是「无法判定」，
> **不能默认它永远有效**——那等于给一个没依据的结论发通行证。

### 一个容易被忽略的实现点：为什么是「沿链选」而不是「全局取日期最大」

一开始我们写的是「在全部候选里挑 `effective_date` 最大且不超过 `at` 的那张」。
写测试时发现它**不稳定**：一次检索会捎回若干不相关卡片，当两条不同的版本链
恰好日期相同、版本号也相同时，`max()` 取谁取决于遍历顺序——同样的输入两次跑可能给不同答案。

改成「先按相关度定主题，再在它的链内选」之后，顺序无关了。

---

## 3. 代码走读（2 分钟）：具体在哪

| 位置 | 做什么 |
|---|---|
| `rag_pipeline/policy.py` · `PolicyResolver` | 消歧主体 |
| `rag_pipeline/policy.py` · `PolicyResolution` | 输出类型——**先讲这个**，四态就在它的 docstring 里 |
| `rag_pipeline/policy.py` · `PolicyResolver.resolve()` | 入口：四态判定都在这里，**建议从这里开始走读** |
| `rag_pipeline/policy.py` · `PolicyResolver._search()` | 关键一行：`include_excluded=True` —— 看不见废止卡就无从消歧 |
| `rag_pipeline/policy.py` · `PolicyResolver._chain()` | 沿 `replaces` 向上/向下展开版本链 |
| `rag_pipeline/retrieval/hybrid.py` · 三个检索方法 | `include_excluded` 形参（默认 `False`，行为不变） |
| `rag_service/assembly.py` · `ServiceAssembly.resolve_policy()` | 装配接线，与 `search()` **共用同一把检索锁** |
| `rag_service/app.py` · `POST /api/v1/policy/resolve` | HTTP 出口 |

> 行号会随编辑漂移，讲的时候**按函数名找**更稳；上面的路径在 IDE 里直接跳即可。

**`_chain()` 值得单独说一句**：它只沿 `replaces` 这条**已声明的边**连接，
不做标题/关键词的软匹配。猜出来的版本关系会悄悄把不相干的卡串成一链，
**比「没有关系」更危险**——它会产出一个看起来合理、实则无依据的结论。

**为什么 `include_excluded` 默认是 `False`**：普通检索路径必须保持原行为，
否则员工问答会突然看到废止卡的做法。这一点有实测钉住（见第 4 节）。

---

## 4. 证据（1.5 分钟）：实跑数据

**环境**：`python -m rag_service`（`RAG_HOME=services/python-retrieval`，`127.0.0.1:8310`）
**完整记录**：`artifacts/output/day18_rag_policy_run_20261021.txt`

| # | query | at | status | 结论 |
|---|---|---|---|---|
| 1 | 域账号锁定 解锁 | 2024-01-15 | `RESOLVED` | **旧规** `ITKB-LEG-ACC-001 v0.9`，`supersededAt=2024-03-01` |
| 2 | 域账号锁定 解锁 | 2024-06-01 | `RESOLVED` | **新规** `ITKB-ACC-001 v1.0` |
| 3 | VPN 连接失败 | 2023-05-01 | `RESOLVED` | **旧规** `ITKB-LEG-VPN-001 v0.9` |
| 4 | 打印机脱机无法打印 | 2024-06-01 | `UNDATED` | 无法判定，`citation=null` |
| 5 | 域账号锁定 解锁 | （留空取当天） | `RESOLVED` | 新规 |

第 1 条的原始响应（可直接投屏）：

```json
{"code":0,"msg":"success","data":{
  "status":"RESOLVED",
  "citation":"[来源: ITKB-LEG-ACC-001@v0.9 《域账号锁定处理（旧版·宽松策略，已废止）》]",
  "articleId":"ITKB-LEG-ACC-001","version":"v0.9",
  "effectiveDate":"2022-01-01","supersededAt":"2024-03-01",
  "reason":"2024-01-15 时刻适用 ITKB-LEG-ACC-001 v0.9（自 2022-01-01 起生效）",
  "chain":[{"articleId":"ITKB-ACC-001","version":"v1.0","effectiveDate":"2024-03-01"},
           {"articleId":"ITKB-LEG-ACC-001","version":"v0.9","effectiveDate":"2022-01-01"}],
  "candidates":[ ... 6 张 ... ]}}
```

**测试**（`rag_service/tests`）：**68 passed**
- `test_policy.py` — 21 个用例（分水岭边界、链式选择稳定性、四态、角标格式、真实语料契约）
- `test_policy_endpoint.py` — 14 个用例（HTTP 形状、错误映射、锁释放）
- 既有 31 个用例全过 —— **回归证据**

**回归实测**：`include_excluded=False` 时，`ITKB-LEG-*` 仍不出现在结果里。

---

## 5. 收获（1 分钟）：两个真实发现

### 发现一：语料里根本没有日期，这个"空"是设计使然

动手前我们查了三处，**一个日期都没有**：

| 来源 | 结果 |
|---|---|
| 源文档 `IT常见问题RAG知识库.docx` | 0 个日期、0 个版本号 |
| 清洗中间产物（35 个 `clean_*.json`） | 0 个日期 |
| wiki 卡（39 张） | `effective_date` **0 / 39** |

查了源码才明白这是**有意为之**：

- `wiki_generator.py:38` ——「effective_date 为 None 时整行省略——**不编造日期是防幻觉约束的一部分**」
- `llm_synthesizer.py:55` 铁律 1 ——「不得编造原文中不存在的日期、金额、版本号」

所以分水岭的日期，是**显式构造的课程演示数据**，只补了 3 组 6 张卡
（`ACC` / `NET` / `VPN` 各一组 v0.9→v1.0），并在卡里用
`effective_date_source: "demo-constructed"` **标明来源**。

这与那条铁律不冲突：铁律管的是**模型自动抽取环节不许幻觉**；
人工显式声明的演示数据是另一回事——**只要标明白**。

### 发现二：跑一次服务就会把已提交的索引改脏

`artifacts/indexing/` 是**活库**且已入库。只要服务打开过它，Chroma 就会重排 SQLite 页面，
`chroma.sqlite3` / `length.bin` 显示 modified —— 但**数据一行没变**：

```
HEAD  : {'embeddings': 144, 'embedding_metadata': 3216, 'collections': 1}
工作区: {'embeddings': 144, 'embedding_metadata': 3216, 'collections': 1}
```

**判断「是不是真变了」用行数比对，别看 `git status`。**
这类噪音 `git checkout --` 回滚即可。演示完记得回滚，别让它混进提交。

---

## 附录 A · 现场演示步骤

### 前置：环境变量必须设对（**最容易翻车的一步**）

`RAG_HOME` 一个变量同时定位三样东西，而它们在仓库里**不在同一个根**：

- `configs/pipeline.yaml`、`artifacts/` → 在 `services/python-retrieval/`
- `.env`（嵌入/精排凭据）→ 在**仓库根**

```bash
cd <repo>/services/python-retrieval

# 1) 先把根 .env 的键导出为进程环境变量（config.py 优先读进程环境变量）
export $(grep -v '^#' ../../.env | xargs)      # 或手动 export EMBED_* / RERANK_*

# 2) 再指向服务目录（保证 configs/ 与 artifacts/ 路径正确）
export RAG_HOME=$PWD

# 3) 起服务
python -m rag_service
```

**没设对会怎样**：嵌入网关不可用时 `KspEmbeddingProvider` 会**静默降级**为本地
hash 兜底向量——不报错、不告警，只是检索质量变差、角标不相关。
**演示前务必看一眼健康检查**：

```bash
curl -s http://127.0.0.1:8310/api/health
# status 应为 UP；DEGRADED 只说明 mappingLoaded=false（消歧用不到，可忽略）
# 关键是 rerankAvailable=true 且 rerankProvider=ksp
```

### 演示：四个用例

> ⚠️ **Windows Git Bash 下别用内联中文 body**。`curl -d '{"query":"域账号锁定"}'`
> 会按控制台代码页转码，FastAPI 直接报 `There was an error parsing the body`。
> 用 `--data-binary @文件`（UTF-8）—— 这个坑我们踩过，写进记录了。

```bash
# 把 body 写成 UTF-8 文件再发
printf '%s' '{"query":"域账号锁定 解锁","at":"2024-01-15","topK":6}' > p.json
curl -s -X POST http://127.0.0.1:8310/api/v1/policy/resolve \
     -H 'Content-Type: application/json' --data-binary @p.json
```

| 演示顺序 | body 里的 `at` | 讲什么 |
|---|---|---|
| 1 | `2024-01-15` | **分水岭之前 → 命中已废止的旧规**（反直觉，最有冲击力） |
| 2 | `2024-06-01` | 同一主题、换个日期 → 命中现行新规，且带 `replacedArticles` |
| 3 | `2023-05-01`（query 换 VPN） | 换一条链，结论同样正确 |
| 4 | `2024-06-01`（query 换打印机） | **`UNDATED`** —— 主动讲「判不出来就说判不出来」 |

第 4 个用例是**加分项**，建议一定讲：它展示的是系统**知道自己不知道**。

**演示完记得回滚索引噪音**：

```bash
git checkout -- services/python-retrieval/artifacts/indexing
```

---

## 附录 B · 可能被问到的问题

**Q：为什么不让模型来判断用哪一版？**
A：版本判定是**规则**问题，不是语义问题——给定日期和版本链，答案是确定的。
交给模型只会引入不确定性。这也对齐项目既有约定：**模型只把已有文本说得更顺，
不决定发生什么**。（注：本模块全程不调用模型。）

**Q：不是已经有版本消歧了吗（`default_exclude`）？**
A：那是**召回前置的物理屏蔽**，回答「别把废止做法教给员工」；我们回答
「某时刻哪一版有效」。前者要**看不见**旧版，后者要**看得见**旧版。需求相反。

**Q：为什么返回 HTTP 200 而不是 404？**
A：`UNDATED` / `NO_MATCH` 是**结论**，不是请求失败。请求本身完全合法、
依赖也都正常。把它当 4xx/5xx 会让调用方误以为该重试或告警。

**Q：39 张卡只有 6 张有日期，这个能力有多大用？**
A：对没日期的卡它**如实说判不了**（`UNDATED`），不编。这恰恰是它比
「默认所有卡永远有效」更可信的地方。要扩大覆盖面，得补语料的生效日期——
而这件事被「不得编造日期」的铁律挡着，需要业务方给真实生效日期，不是技术问题。

**Q：版本链断了怎么办？**
A：链靠 `replaces` 声明。没有声明的两版之间**不会被连起来**——宁可判不出，
也不靠标题相似度猜。当前 3 组链的完整性有测试钉住
（`test_real_corpus_keeps_the_three_demo_version_chains`），重跑语料丢了日期会立刻报红。

---

## 附录 C · 讲之前先统一口径

**这几条必须主动说明，不然被问到会很被动：**

1. **演示用的日期是构造的。** 源文档里一个日期都没有（我们查过三处）。
   3 组链的 `effective_date` 是本组为演示显式构造的，卡里用
   `effective_date_source: "demo-constructed"` 标了来源。
   **不要把它说成「从知识库读到的」**。

2. **本模块不改 Java 侧、不接 `it-ticket-cloud`。** 交付物全在
   `services/python-retrieval` 里，是一个可独立起停的 Python 检索服务。
   真实接入（consultation-service 等）是另一件事。

3. **本模块不做裁决、不做动作。** 它只产出「哪一版有效 + 角标 + 条文」。
   交叉裁决是第三阶，HITL 门禁是第四阶——**那是其他同学的部分**。

4. **`UNDATED` 不是 bug**，是设计里刻意保留的一态。

5. **`include_excluded` 默认 `False`**，普通检索路径行为与改前逐字一致——
   如果有人担心「改动影响了线上检索」，这条能直接回答。

6. 卡里 `replaces` 字段原本 38 张全是空数组，我们只填了 3 张现行卡。
   所以**能演示的只有这 3 组链**，别的主题会是 `UNDATED`，这是预期。

---

## 附：单测

```bash
cd services/python-retrieval
RAG_HOME=$PWD python -m pytest rag_service/tests -q
# 68 passed
```

只看本次新增：

```bash
RAG_HOME=$PWD python -m pytest rag_service/tests/test_policy.py \
                                rag_service/tests/test_policy_endpoint.py -q
# 37 passed（含 3 个参数化用例）
```
