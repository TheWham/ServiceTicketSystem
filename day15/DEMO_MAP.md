# Day15 演示页面 → 代码位置对照表（演讲速查）

> 按讲解顺序排列。启动：`python -m day15` → 浏览器开 `http://127.0.0.1:8320/`
> 行号已按最新代码核准（含详细 docstring 之后）。

## ① 提问框 + 三个预置按钮（页面顶部）

- **前端**：预置问题定义 `api.py:20` `PRESET_QUESTIONS` → 按钮渲染 `api.py:212` `renderPresets()` → 点击提问 `api.py:218` `ask()`
- **后端接口**：`api.py:58` `POST /api/v1/knowledge/chat` → 进 `service.py:302` `answer()`

## ② 答案区（受约束生成 + 角标徽章）—— 核心

- **前端渲染**：`api.py:234` `render()`；把正文 `[来源: 卡片id - 章节名]` 转成蓝色徽章的正则是 `api.py:184` `CITE_RE` + `api.py:188` `fmtAnswer()`
- **后端生成**：防幻觉提示词（三大军规）`prompts.py:12` `STRICT_GROUNDING_PROMPT`；LLM 调用+缓存+离线兜底 `llm.py:88` `GroundingGenerator.generate()`
- **角标抽取**：`service.py:59` `parse_inline_citations()` + `service.py:122` `canonicalize_answer_citations()`（把模型写歪的 `ITKB · ACC-002` 回正成 `ITKB-ACC-002`）

## ③ 检索链路漏斗（双路召回→RRF→Rerank→门控→拒答门）

- **前端**：漏斗五格定义 `api.py:245` `stages`，渲染 `api.py:252`
- **数据来源**：候选明细表 `api.py:254` 渲染 `trace.candidates`，由后端 `service.py:150` `build_trace()` 从内核 `hybrid_rerank_search` 返回（`scored_all` 等）组装——**没给内核加任何埋点**

## ④ 来源 Citation 卡片列表

- **前端**：`api.py:261` 渲染 `d.citations`
- **后端**：`service.py:75` `build_citations()` —— 五字段全取自检索命中的 metadata，**不依赖 LLM 打角标**（讲点：就算模型不写角标，来源列表也永远完整）

## ⑤ 切片演示区（父子 Small-to-Big）

- **前端**：`api.py:269` `loadChunk()`
- **后端**：`service.py:451` `chunk_demo()` —— 现场用 `build_chunker(cfg)` 把一张卡切成"父卡+子块"，与建库用的是**同一个工厂**（讲点：切片一致性）

---

## 主链路核心逻辑 `answer()`（service.py:302-414，一句话指路）

| 步骤 | 位置 | 一句话 |
|---|---|---|
| 复用检索装配 | `service.py:220` `__init__` | 持 `ServiceAssembly`，检索参数全读 `configs/pipeline.yaml` |
| 检索锁串行 | `service.py:237` `_search` | 内核有状态单例，并发经锁串行，超时抛 LockBusy |
| 调检索内核 | `service.py:265` `_run_search` | BM25+Dense+RRF+Rerank+门控，零硬编码 |
| 拒答不生成 | `service.py:347` | 内核拒答 → 直接返回，**不调 LLM** |
| 拼上下文 | `service.py:359` / `417` `_build_contexts` | 取 `parent_content` 整卡全文 |
| LLM 生成 | `service.py:363` | 缓存 → 在线 → 离线兜底（绝不编造） |
| 角标对齐 | `service.py:380` | 回正 + 诚实拒答二次识别 |

## 一句话回答"代码在哪"

- **前端页面**：`day15/api.py`（HTML/CSS/JS 全内嵌，72-289 行）
- **业务逻辑**：`day15/service.py`（`answer()` 主流程，302 行起）
- **防幻觉规则**：`day15/prompts.py`
- **LLM 调用与离线**：`day15/llm.py`
- **检索底座**：不在 day15，复用 `rag_service/assembly.py` + `rag_pipeline/retrieval/hybrid.py`
