# day15 · 企业知识库问答服务层（演示版）

在 `rag_pipeline` 检索基座（父子切片 + 混合检索 + RRF + Rerank + 拒答门控）之上，
封装成"提问 → 检索 → 受约束生成 → 溯源角标"的企业级问答服务，并带**浏览器演示页**。

## 快速启动（演示）

```bash
python -m day15
```

浏览器打开 http://127.0.0.1:8320/

页面四区块：
1. **状态条** — 切片数 / 卡片数 / LLM 在线状态 / 缓存答案数；
2. **提问区** — 输入框 + 三个预置演示问题按钮；
3. **答案区** — 受约束生成的答案（正文内 `[来源: 卡片id - 章节名]` 角标）+ 结构化 Citation 卡片；
4. **检索链路 + 切片演示** — 双路召回 → RRF → Rerank → 门控 → 拒答门 的漏斗与候选明细；
   下拉任选一张卡片，现场展示"父卡（整卡）+ 子块（512 字符 H2 分节）"的父子切片结构。

## 三个预置演示问题

| 类型 | 问题 | 期望表现 |
|---|---|---|
| 正例 | 公司密码策略要求每隔多少天定期更换密码？密码复杂度有什么要求？ | 命中 `ITKB-ACC-002`，答案带角标 |
| 版本冲突 | 出差在酒店连公司 VPN 报错 806，现行 v1.0 推荐改用哪种 VPN 协议？旧版 PPTP 是否有效？ | 引现行 `ITKB-VPN-001`，废止卡 `ITKB-LEG-VPN-001` 被 `default_exclude` 滤除 |
| 越界拒答 | 是否允许员工使用个人住房公积金申请企业内部低息购房贷款？ | 诚实拒答（`is_refused=true`），不编造 |

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 演示页 |
| POST | `/api/v1/knowledge/chat` | 主问答：`{query, top_k?, metadata_filter?, include_trace?}` → `{answer, is_refused, citations, trace, latency_ms, mode}` |
| GET | `/api/v1/knowledge/chunk_demo?card=ITKB-VPN-001` | 现场切一张卡，返回父卡 + 子块列表 |
| GET | `/api/v1/knowledge/cards` | 卡片清单 |
| GET | `/api/v1/knowledge/health` | 健康检查 |

## 离线彩排 / 断网兜底

三层兜底（联网优先）：

```bash
# 演示前一晚联网跑一遍预置问题，把答案/改写/嵌入三处缓存预热
python day15/run_day15_pipeline.py --limit 3

# 彩排或现场断网时强制离线：命中缓存的题照常作答，未缓存的题返回检索切片并明示离线
DAY15_OFFLINE=1 python -m day15
```

LLM 生成不可用时（断网 / 网关异常）服务**不会编造答案**，只返回诚实文案 + 命中的知识片段与结构化来源。
rerank 断网时内核自动降级为启发式打分，服务层在 `notes` 与链路区明示。

## 黄金集回归

```bash
python day15/run_day15_pipeline.py            # 20 题全量，报告 → artifacts/day15/Day15_黄金集回归报告.md
python day15/run_day15_pipeline.py --limit 3  # 只跑前 3 题（调试）
python day15/run_day15_pipeline.py --serve    # 等价 python -m day15
```

## 一致性契约（不复制检索参数）

- 配置唯一真源：`configs/pipeline.yaml`；
- 检索装配整体复用 `rag_service.assembly.ServiceAssembly`（其构造即 `load_config` →
  `load_corpus_with_deterministic_ids`（内部 `build_chunker`）→ manifest 指纹校验 →
  `IndustrialHybridRetriever` → `QueryRewriter` → 检索锁）；
- 本层只在其上加 grounding 生成与 Citation 抽取，检索参数全部从 `asm.cfg.retrieval` 读，零硬编码。

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `DAY15_HOST` / `DAY15_PORT` | 127.0.0.1 / 8320 | 服务绑定（与 `rag_service` 的 8310 错开） |
| `DAY15_OFFLINE` | 0 | 置 1 强制离线（跳过 LLM 生成，彩排用） |
| `DAY15_LLM_TIMEOUT` / `DAY15_LLM_RETRIES` | 30 / 2 | 生成调用预算 |
| `DAY15_ANSWER_CACHE_DIR` | `artifacts/day15/.answer_cache` | 答案缓存目录 |
| `LLM_*` / `EMBED_*` / `RERANK_*` | — | 三类模型独立配置（根目录 `.env`） |
