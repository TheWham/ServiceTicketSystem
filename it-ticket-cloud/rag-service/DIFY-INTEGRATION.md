# Dify 知识库通道接入说明

在自研「解析 ➔ 切片 ➔ Embedding ➔ ES 混合检索」链路之外，rag-service 新增一条 **Dify 通道**：
文档上传、解析、分块、向量化与混合索引全部由 Dify 平台完成，便于做召回质量对比。
两条通道相互独立，Dify 通道不写 MySQL/ES、不受知识生命周期状态机约束。

## 配置

| 配置项（application.yml `rag.dify.*`） | 环境变量 | 默认值 | 说明 |
|---|---|---|---|
| `enabled` | `DIFY_ENABLED` | `true` | 通道开关，false 时相关端点直接拒绝 |
| `base-url` | `DIFY_BASE_URL` | `http://120.92.138.195/v1` | Dify Dataset API 基础地址 |
| `api-key` | `DIFY_API_KEY` | 空 | **必填**，Dify 知识库页面「服务 API」创建的密钥（`dataset-` 开头） |
| `dataset-id` | `DIFY_DATASET_ID` | 空 | 目标知识库 ID；留空按 `dataset-name` 自动创建并复用 |
| `dataset-name` | `DIFY_DATASET_NAME` | `it-ticket-knowledge` | 自动创建知识库时的名称 |
| `indexing-technique` | `DIFY_INDEXING_TECHNIQUE` | `high_quality` | 索引技术（向量+关键词混合索引） |
| `search-method` | `DIFY_SEARCH_METHOD` | `hybrid_search` | 默认检索方式 |
| `top-k` | `DIFY_TOP_K` | `5` | 默认召回条数 |
| `score-threshold` | `DIFY_SCORE_THRESHOLD` | `0.3` | 默认分数阈值 |
| `timeout-seconds` | `DIFY_TIMEOUT_SECONDS` | `30` | HTTP 超时 |

本地启动沿用 `rag-service/ai-secrets.yml`（已被 Git 忽略）：在 `dify.api-key` 引号内填入真实 Key 即可。
密钥禁止入库/入 Git/入日志（对齐 MR-002 密钥治理）。

## 接口（均需网关鉴权，与既有 /api/v1/rag/** 一致）

```bash
# 1) 初始化/复用知识库（留空 dataset-id 时自动创建）
curl -X POST http://{gateway}/api/v1/rag/dify/datasets -H "Authorization: Bearer {token}"

# 2) 上传文档（Dify 完成解析/分块/向量化/混合索引；waitSeconds>0 时请求内轮询至 completed/error）
curl -X POST http://{gateway}/api/v1/rag/dify/documents/upload \
  -H "Authorization: Bearer {token}" \
  -F "file=@wifi故障排查.md" -F "chunkSize=0" -F "waitSeconds=60"

# 3) 纯文本创建文档
curl -X POST http://{gateway}/api/v1/rag/dify/documents/text \
  -H "Authorization: Bearer {token}" -H "Content-Type: application/json" \
  -d '{"name":"vpn.md","text":"VPN 配置步骤……","waitSeconds":60}'

# 4) 查询批次索引状态（waiting➔parsing➔cleaning➔splitting➔indexing➔completed/error）
curl http://{gateway}/api/v1/rag/dify/documents/{batch}/status -H "Authorization: Bearer {token}"

# 5) 混合召回（hybrid_search / semantic_search / full_text_search）
curl -X POST http://{gateway}/api/v1/rag/dify/retrievals \
  -H "Authorization: Bearer {token}" -H "Content-Type: application/json" \
  -d '{"query":"打印机离线怎么办","searchMethod":"hybrid_search","topK":5,"scoreThreshold":0.3}'
```

## 设计说明

- `DifyDatasetClient`：薄 HTTP 客户端（java.net.http），覆盖创建知识库、按文件/文本创建文档、
  索引状态轮询、retrieve 召回四类端点；失败一律抛 `BizException`，不静默吞错（对齐 RD-006）。
- `DifyKnowledgeService`：编排层，负责启用校验、索引完成等待轮询（2s 间隔，默认最长 60s）与响应映射。
- 上传 `chunkSize<=0` 时使用 Dify 自动分段；>0 时走 custom `max_tokens`/`chunk_overlap` 分段规则。
- **边界**：Dify 通道不含 articleId/versionId 映射，未接入 `/api/v1/rag/retrievals` 的
  PUBLISHED 校验（AI-001），后续若转为正式检索出口需先补齐该映射。
- 测试：`rag-service/src/test/java/com/itticket/rag/DifyKnowledgeServiceTest.java`（6 项，纯 Mockito）。
