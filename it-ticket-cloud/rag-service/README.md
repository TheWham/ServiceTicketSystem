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
