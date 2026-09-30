# RAG 检索服务对接说明（给 AI 客服 / consultation-service）

> rag-service 提供**知识库生命周期管理 + ES 混合检索（向量 + BM25）**，本模块不做大模型生成与对话状态。
> 本文是给 AI 客服服务对接方的集成契约与切换指南。
> 权威契约见 `docs/specs/`（复数目录）与 `docs/IT服务工单系统PRD-Ultimate.md`，本文不重复定义，只落对接细节。

---

## 1. 模块边界与路由

| 服务 | 职责 | 端口 | 对外路由 |
|---|---|---|---|
| **rag-service** | 知识入库/切片/向量化、ES 索引、生命周期、RAG 检索 | **8302** | `/api/v1/rag/**` |
| consultation-service | AI 问答、转人工、会话、**`ai-messages`**、**`/api/v1/knowledge/search`** | 8301 | `/api/v1/consultations/**`、`/api/v1/knowledge/**` |

- **不重复实现**：rag-service 不提供 `POST /api/v1/consultations/{id}/ai-messages` 与 `GET /api/v1/knowledge/search`（已在合并时移除，避免与 consultation-service 撞车）。
- rag-service 保留两个对外检索出口（见下）供对接与运维使用。

---

## 2. 对外检索接口

### 2.1 `POST /api/v1/rag/retrievals` —— RAG 检索（供对话生成取依据）

请求：

```json
{
  "question": "VPN 客户端提示证书过期怎么处理",   // 必填，1-8000
  "categoryId": "C_NET",                         // 可选，按分类过滤
  "topK": 5                                       // 可选，默认 5，上限 20
}
```

响应（`Result<RagRetrievalResponse>`，统一包络）：

```json
{
  "code": 0, "msg": "success",
  "data": {
    "items": [
      {
        "chunkId": "chk-090cce37ab6a443b",
        "articleId": "art-1790701708099-830",
        "versionId": "ver-1790701708101-783",
        "title": "企业网络与 VPN 故障排查手册",
        "snippet": "……",
        "content": "……",
        "categoryId": "C_NET",
        "score": 0.7503,
        "indexVersion": "ver-1790701708101-783"
      }
    ],
    "domain": "OFFICE_IT",
    "suggestedReplyType": "ANSWER",
    "suggestedRefusalReason": null,
    "topScore": 0.7503,
    "reliable": true,
    "publishedOnly": true
  }
}
```

### 2.2 `GET /api/v1/rag/articles/search` —— 文章级检索（运维/验收视图）

`query / category / page / pageSize`；按 `article_id` 折叠去重，total 为文章数（cardinality 聚合）。
**契约路径 `GET /api/v1/knowledge/search` 由 consultation-service 提供**，本端点是 ES 侧的等价能力，用于核对索引与下线联动，不作为对外契约。

---

## 3. 领域判定与阈值语义（对接方必读）

### 3.1 领域四态（`domain` 字段，MR-004）

判定**先于检索、独立于检索结果**。检索资料与用户输入都不得覆盖领域规则。

| domain | 含义 | 对接方建议动作 |
|---|---|---|
| `OFFICE_IT` | 办公 IT 范围 | 可生成回答；有引用带引用，无命中/不相关也可通用回答（见 3.2） |
| `OFF_TOPIC` | 领域外（周报/翻译/订餐/股票…） | **REFUSE + `OFF_TOPIC`**，明确告知不能答复 |
| `HIGH_RISK` | 高风险（权限变更/数据恢复/高风险命令/硬件拆修等） | **REFUSE + `HIGH_RISK_TOPIC`**，提供人工入口 |
| `UNCERTAIN` | 语义不清 | **CLARIFY**，先追问，不生成解决步骤 |

### 3.2 阈值与可靠命中（AI-001 冷启动修订 + MR-001）

- 可靠命中阈值 `confidenceThreshold = 0.70`，无可靠下限 `lowConfidenceThreshold = 0.45`（均可配置 `RAG_CONFIDENCE_THRESHOLD` / `RAG_LOW_CONFIDENCE_THRESHOLD`）。
- `reliable=true`：最高相似度 ≥ 0.70 → 可据此生成**带引用**的回答。
- 介于 0.45–0.70：`suggestedRefusalReason=LOW_CONFIDENCE`、`reliable=false` → **仍拒答**。
- **无命中或 < 0.45 的不相关命中：不强制拒答**（`reliable=false`、`suggestedRefusalReason=null`、domain 仍为 `OFFICE_IT`）——此时允许上层给出**空引用的通用回答**，但必须明确标注"无知识库依据"。

> ⚠️ 这与旧版"无引用一律拒答"不同：2026-09-29 修订后，办公 IT 冷启动允许通用回答。只有领域外、高风险、置信度不足、模型不可用、知识冲突才拒答。

### 3.3 建议回答类型（`suggestedReplyType`）

供参考，最终决定权在对话层：`ANSWER` / `CLARIFY` / `REFUSE`。`REFUSE` 时必带 `suggestedRefusalReason`。

---

## 4. 引用与可追溯性

- 每条命中携带 `articleId / versionId / score / snippet / indexVersion`（MR-004）。
- **`indexVersion` 恒等于 `knowledge_version.version_id`**（RAG 索引版本可追溯到知识版本，DM-004）。
- 生成回答时，只要声明引用，**必须复核该版本仍为 PUBLISHED**（rag-service 内部已做一层校验，对接方生成端仍须按 AI-008 再校验）。
- 引用片段 `snippet` ≤ 1000，标题 `title` ≤ 200，已做非空兜底。

---

## 5. 状态与可见性（AC-27 / AI-001）

- 检索强制过滤 ES `status = PUBLISHED`；**下线/回滚的知识不再返回**。
- 草稿（DRAFT）不进 ES；发布（publish）时才写索引；下线（offline）把切片置 `OFFLINE` 并写 `offline_at`。
- 高风险知识发布需平台管理员复核（`platform_reviewer_id`），作者不得自审（AC-25，403）。

---

## 6. 降级语义（RD-006）

| 故障 | 表现 | 对接方 |
|---|---|---|
| 向量/检索服务不可用 | HTTP 200，`domain=OFFICE_IT`、`suggestedReplyType=REFUSE`、`suggestedRefusalReason=MODEL_UNAVAILABLE`、`reliable=false` | 转 `AI_UNAVAILABLE` 拒答，保留转人工/提单 |
| ES 不可达（检索） | HTTP 500，`code=50000`，不伪装空成功 | 同上做依赖降级 |

---

## 7. 对接方切换步骤（consultation-service → 使用 rag-service 检索）

当前 consultation-service 的 `KnowledgeRagAdapter`（`provider=local`）**直接在 MySQL 检索**；`OpenAiCompatibleRagAdapter` 只把"生成"外包，检索仍走本地。要改用 rag-service 的混合检索：

1. 新增一个 `RagServiceAdapter implements RagAdapter`（或给现有 adapter 加一个检索来源分支），把 `retrieve()` 改为调用 `POST /api/v1/rag/retrievals`（HTTP，或经网关）。
2. 用返回的 `items[].articleId/versionId/title/snippet/score` 组装 `KnowledgeCitationDto`；用 `topScore/reliable/domain/suggestedRefusalReason` 做拒答判定。
3. 保留你们现有的 `AiInteraction` 落库与 SSE 协议不变（rag-service 只提供检索依据，不动对话侧）。
4. 高风险拦截：可直接复用我返回的 `domain=HIGH_RISK`，不必重复实现词表。

> 本步属于你们服务的改动，我这边接口已就绪，联调时我配合。

---

## 8. 环境变量与启动

| 变量 | 用途 | 缺省行为 |
|---|---|---|
| `MYSQL_PASSWORD` | 数据源口令 | 默认 clt123456，可用环境变量覆盖 |
| `EMBEDDING_API_KEY` | 向量化凭据 | **无默认值**，未注入时向量化按 RD-006 降级 |

启动：`java -jar it-ticket-rag-service-1.0.0.jar`（端口 8302），依赖 Nacos + ES + 远端库。

---

## 9. 本轮范围说明（明确的边界）

- 已交付：生命周期四态（submit/publish/reject/offline）+ 审计 + 领域事件 + ES 索引（含 status/hash/indexVersion/时间戳）+ 混合检索 + 领域判定 + 阈值分档 + 引用校验 + AC-27 下线联动。
- 未做（下一轮）：`rag_index_pointer` 表与 `IndexActivator`/`IndexRefreshWorker`（MR-011 完整形态）、Outbox 消费者、咨询/AI 侧改动。
