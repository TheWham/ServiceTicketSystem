# RAG 知识库微服务 (it-ticket-rag-service)

本项目为 IT 服务工单系统的 RAG 知识库微服务模块，负责文档摄入解析、智能切片、Elasticsearch 向量/全文索引构建与全链路追踪。

AI 客服对接契约见 [INTEGRATION.md](INTEGRATION.md)，客服侧配置及验收方式见 [RAG-INTEGRATION.md](../consultation-service/RAG-INTEGRATION.md)。

---

## 📦 架构与技术栈

* **核心框架**：Spring Boot 3.2.5 + Spring Cloud Alibaba (Nacos)
* **数据库**：MySQL 8.x（持久化 `knowledge_article` 与 `knowledge_version` 表）
* **全文与向量检索**：Elasticsearch 8.11.3
* **可视化控制台**：Kibana 8.11.3 (简体中文)
* **服务端口**：
  * `rag-service`：`8302`
  * `Elasticsearch`：`9200`
  * `Kibana`：`5601`

---

## 🚀 启动本地 Elasticsearch 与 Kibana

进入 `rag-service` 模块目录，使用 Docker Compose 一键启动：

```bash
cd it-ticket-cloud/rag-service
docker compose up -d
```

### 访问地址
* **Elasticsearch 健康检查**：[http://localhost:9200](http://localhost:9200)
* **Kibana 控制台**：[http://localhost:5601](http://localhost:5601)

### 常用命令
```bash
# 查看容器运行状态
docker compose ps

# 查看 ES 运行日志
docker compose logs -f elasticsearch

# 停止并移除容器
docker compose down
```

---

## 🔌 核心 API 接口

| 接口方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| `POST` | `/api/v1/rag/documents/upload` | 上传文档并执行切片、入库 ES 完整链路 |
| `GET` | `/api/v1/rag/traces/{traceId}` | 获取指定 TraceId 的全链路明细与切片列表 |
| `GET` | `/api/v1/rag/traces` | 获取最近执行的历史链路报告列表 |
| `POST` | `/api/v1/rag/indices/init` | 手动初始化/新建 Elasticsearch 知识切片索引 |
| `GET` | `/api/health` | 服务健康检查 |

## AI 客服反馈沉淀与 Redis 缓存

本地 Redis 的启动、停止、自动启动、健康检查及 Docker 部署见 [Redis 服务说明](../redis/README.md)。

员工在咨询页点击 AI 通用回答的“已解决”后，consultation-service 持久化 `HELPFUL` 反馈。
本服务每 5 秒扫描一次，每批最多 100 条；正常无积压时约 5–10 秒进入
**知识管理 → 待审核**，管理员刷新列表即可查看，详情的“变更说明”保留来源会话和回答 ID。
首次启动也会补处理历史反馈，不需要员工重复点击。

消费者只接收 `ANSWER + generalAnswer=true + citations=[] + HELPFUL`，按同一会话的
`ai-q:/ai-a:` 请求键准确配对问题和回答，排除撤回、拒答、追问和负面反馈。
入队前对手机号、邮箱、工号及资产编号脱敏，含提示注入特征或缺失正文的记录跳过并记录来源 ID。
文章、版本、提审审计、`KNOWLEDGE_SUBMITTED` 事件在同一事务中提交；管理员审核通过后才发布和索引。
同一回答使用确定性文章 ID，重复反馈、重启、审核驳回或发布后均不重复提审。

Redis 缓存处理标记（不保存问答正文），键为 `its:{env}:cache:ai-feedback:{interactionId}`，
默认 TTL 300 秒，事务提交后才写入。MySQL 保存反馈和待审内容，是幂等与故障恢复的依据。
Redis 不可用时熔断 30 秒并回退 MySQL；数据库失败不写成功缓存，后续扫描重试。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `REDIS_HOST` / `REDIS_PORT` | `127.0.0.1` / `6379` | Redis 地址 |
| `REDIS_PASSWORD` / `REDIS_DATABASE` | 空 / `0` | Redis 认证和数据库 |
| `CACHE_ENVIRONMENT` | 当前 Spring profile 或 `dev` | 缓存环境隔离 |
| `AI_FEEDBACK_CACHE_TTL_SECONDS` | `300` | 缓存 TTL，必须大于 0 |
| `AI_FEEDBACK_CAPTURE_ENABLED` | `true` | 反馈消费开关 |
| `AI_FEEDBACK_POLL_DELAY_MS` | `5000` | 扫描间隔 |

重新构建并重启 rag-service 后生效，无新增数据库迁移。
既有数据库需已具备知识生命周期的 `knowledge_transition` 等表。

验证：`mvn -pl rag-service,consultation-service -am test`。
可选真实 MySQL 测试设置 `AI_FEEDBACK_MYSQL_TEST=true`、`MYSQL_PASSWORD`，
必要时指定 `MYSQL_TEST_URL` / `MYSQL_USERNAME`，运行
`mvn -pl rag-service -am -Dtest=AiFeedbackSourceMysqlTest,AiFeedbackTransactionMysqlTest -Dsurefire.failIfNoSpecifiedTests=false test`。
这两项测试只创建连接私有临时表，不修改已有业务数据；断开连接后临时表自动清理。
