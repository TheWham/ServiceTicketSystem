# agent_service · Function Calling 智能体（ReAct + 白名单工具）

企业 IT 客服的「生成侧」：把大模型 + Function Calling（原生 tools 协议 + ReAct 循环）+
白名单工具下沉为一个独立 Python 服务，由 Java `consultation-service` 通过 HTTP 调用。

## 分工

| 层 | 归属 | 职责 |
|---|---|---|
| **脑+手** | **本服务（Python）** | LLM 调用、tools schema、ReAct 多轮循环、工具执行 |
| **门禁+账本** | Java `consultation-service` | 身份鉴权、会话状态、引用守卫（`AiAnswerGuard`）、**建单确认**、落库 |

Java 侧 `OpenAiCompatibleAnswerGenerator` 调本服务（`POST /api/v1/agent/chat`），拿回
**6 键结构化 JSON**（replyType/answerText/usedVersionIds/confidence/knowledgeConflict/offTopic）
+ **带外建单草稿**（`ticketDraft`），再走原有的守卫 → 溯源 → 落库链路。

## 快速启动

```bash
cd services/python-retrieval
pip install -r agent_service/requirements.txt

# 生成模型（OpenAI 兼容）
export AGENT_LLM_BASE_URL=https://your-endpoint/v1
export AGENT_LLM_API_KEY=sk-...
export AGENT_LLM_MODEL=deepseek-v4-flash        # 需支持原生 tools

# 工具依赖（可选；不配则对应工具返回明确错误）
export TICKET_SERVICE_BASE_URL=http://127.0.0.1:8201     # 查工单 / 建单（ticket-service 事实源）
export KNOWLEDGE_SEARCH_BASE_URL=http://127.0.0.1:8301   # 查知识库（consultation-service）

python -m agent_service                          # 默认 127.0.0.1:8320
```

Java 侧开启（`consultation-service/src/main/resources/application.yml`）：

```yaml
itticket:
  consultation:
    ai:
      agent:
        enabled: true
        service-base-url: http://127.0.0.1:8320
        ticket-service-base-url: http://127.0.0.1:8201
```

## 部署（Docker / compose）

镜像（`services/python-retrieval/Dockerfile`，一个镜像承载本服务）：

```bash
docker build -t <IMAGE_PREFIX>/it-ticket-python-ai services/python-retrieval
docker push <IMAGE_PREFIX>/it-ticket-python-ai
```

已并入 `it-ticket-cloud/deploy/docker-compose.yml`（服务名 `agent-service`，容器内 8320）：

- `consultation-service` 侧注入 `AI_AGENT_ENABLED` / `AGENT_SERVICE_BASE_URL` / `TICKET_SERVICE_BASE_URL`；
- `agent-service` 侧注入模型凭据 + `TICKET_SERVICE_BASE_URL` / `KNOWLEDGE_SEARCH_BASE_URL`（容器名互访）；
- 开关默认 `AI_AGENT_ENABLED=false`（不影响现有 AI 客服），确认可用后打开。
- 相关变量见 `it-ticket-cloud/deploy/.env.example`。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/agent/chat` | ReAct 生成；主体经 `X-User-Id` / `X-User-Role` 头透传 |
| GET | `/api/health` | 自检（模型/工具是否已配置），不调模型 |

请求体：`{question, history[], material[], categoryId?, assetId?}`
响应：`{code, msg, data:{replyType, answerText, usedVersionIds, confidence, knowledgeConflict, offTopic, ticketDraft?}}`

## 白名单工具

| 工具 | 能力 | 安全边界 |
|---|---|---|
| `search_knowledge` | 查已发布知识库 | 走 consultation 知识搜索接口，只返回 PUBLISHED 当前版本 |
| `query_my_tickets` | 查**本人**工单状态/流转 | 走 ticket-service 内部接口；creator 由 `X-User-Id` 绑定，模型无法查他人 |
| `prepare_ticket` | **只产建单草稿、不落库** | 人机回环：草稿随响应返回，**员工确认后**才由 Java 侧真正建单 |

## 设计要点

- **不跨库读工单**：工单是 ticket-service 的事实源（架构 8.1），一律走其内部接口；
- **人机回环**：AI 无法自行建单——`prepare_ticket` 只产草稿，建单必须由员工在 Java 侧
  `POST /api/v1/consultations/{id}/ticket-draft/confirm` 显式确认触发；
- **失败即对象**：工具失败返回 `{success:false,error:...}`（不抛），以 `role="tool"` 回传模型触发反思自愈；
- **轮次熔断**：最后一轮以 `tool_choice=none` 强制出最终答案，防工具调用死循环（RD-007）。