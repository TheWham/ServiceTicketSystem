# 客服与 RAG 联调

本实现遵循 [RAG 对接说明](../rag-service/INTEGRATION.md)。检索和生成是两个独立配置项：

| 环境变量 | 默认值 | 用途 |
|---|---|---|
| `AI_RETRIEVAL_PROVIDER` | `rag-service` | `rag-service` 调混合检索；`mysql` 显式兼容旧检索 |
| `RAG_BASE_URL` | `http://127.0.0.1:8302` | RAG 服务内网根地址，不带 `/api/v1/rag/retrievals` |
| `RAG_RETRIEVAL_TIMEOUT_MS` | `20000` | 单次向量及检索的 HTTP 超时 |
| `RAG_CONFIDENCE_THRESHOLD` | `0.70` | 两个服务保持一致；客服逐条过滤低于该分数的引用 |
| `AI_PROVIDER` | `openai-compatible` | `openai-compatible` 调模型；`local` 只拼接检索正文 |
| `AI_BASE_URL` / `AI_MODEL` / `AI_API_KEY` | 沿用现有配置，key 默认空 | 对话模型，base URL 不含 `/chat/completions` |
| `AI_REQUEST_TIMEOUT_MS` | `120000` | 包含 RAG、生成、重试在内的总预算 |
| `AI_SECRETS_FILE` | `./ai-secrets.yml` | 客服本地配置文件，建议使用绝对路径 |
| `RAG_SECRETS_FILE` | `./ai-secrets.yml` | RAG 本地配置文件，建议使用绝对路径 |

两个服务可读取同一个本地文件，模板见 [ai-secrets.example.yml](../ai-secrets.example.yml)。复制为 `ai-secrets.yml` 后配置对话模型、Embedding、ES。模型 key 与 Embedding key 必须各自配置，不假设二者相同。共享数据库沿用既有配置。

`RAG_BASE_URL` 必须是可信内网服务地址：该调用按项目现有服务间约定透传已认证的 `X-User-Id`、`X-User-Role`，并带 `X-Request-Id`。身份在请求线程中取自 CurrentUser 后显式传入执行线程，不使用请求体里的身份。服务端口应由内网访问控制保护；此地址不能填网关地址（网关需要 JWT）或第三方地址。模型 API Key 不会发送给 RAG。

## 数据流与错误处理

1. 员工从 `/consultation` 发起问题，会话消息正常落库。
2. 客服调用 RAG，严格解析 `{code:0,data}`；HTTP/业务失败不会当作零命中，也不会自动切换 MySQL。
3. `OFF_TOPIC`、`HIGH_RISK`、`UNCERTAIN` 不调生成模型；分别拒答、转人工建议、追问。
4. `LOW_CONFIDENCE`、`CONFLICTING_KNOWLEDGE` 等保留原拒答原因；向量/检索故障显示 `MODEL_UNAVAILABLE`。
5. `reliable=false` 且允许回答时丢弃不相关资料；模型只能生成明确标注“无知识库依据”的通用建议。`provider=local` 无生成能力，零命中仍拒答。
6. 可靠命中按版本去重，保留最高分片段；不再次将余弦分数按 SQL 相关度归一化。`indexVersion` 必须匹配 `versionId`。
7. 模型引用从检索集合重建，返回员工前仍由数据库复核 PUBLISHED 当前版本；历史消息保留引用、交互 ID 和拒答类型。
8. 总超时包含重试。配置/鉴权错误不重试。前端的 180 秒等待上限大于默认后端总预算。

`GET /api/v1/knowledge/search` 仍由 consultation-service 提供；对话生成的检索已切换至 RAG。未改动知识发布审批、SSE、工单或转人工状态机。

## 验证

从 `it-ticket-cloud` 执行：

```text
mvn -pl consultation-service,rag-service -am test
```

HTTP fixture 测试覆盖身份与追踪、真实引用、四种领域、置信度拒答、依赖故障、通用回答、伪造引用、超时与重试。它验证协议集成，不代表真实模型及 ES 可用。

本地网关与两个服务启动后，从仓库根目录执行：

```text
node acceptance/ai-rag-smoke.mjs
node acceptance/ai-rag-smoke.mjs --require-answer
```

账号来自 `IT_TEST_USER_ID` / `IT_TEST_PASSWORD`，默认使用 README 中的演示员工。只创建并结束测试自身的咨询，不修改已有会话。加 `--require-answer` 时，若真实问答没有返回 ANSWER 则失败；未加该选项时允许断言明确的依赖降级。脚本不打印 token、凭据或回答正文。
