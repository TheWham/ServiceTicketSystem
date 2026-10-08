# RAG 与智能客服联调

契约来源：用户提供的 `INTEGRATION.md`（2026-10-08）。

目标：客服通过 `POST /api/v1/rag/retrievals` 取知识依据，生成回答并展示引用；RAG 管理索引及领域判定，客服管理会话、生成、反馈与转人工。

- [x] 新增 HTTP 检索客户端，传递认证后的用户上下文和请求 ID，严格识别 `{code:0,data}` 与 HTTP/业务失败。
- [x] 检索模式显式可配（默认 rag-service，mysql 仅兼容）；保留生成 provider=local/openai-compatible。
- [x] OFF_TOPIC/HIGH_RISK/UNCERTAIN 短路；LOW_CONFIDENCE、依赖失败不得进入通用生成；不相关命中不放入生成提示词。
- [x] 可靠知识转换为真实引用，保留余弦分数，不重复做 SQL 相关度归一化；返回前复核发布状态及当前版本。
- [x] 前端区分 ANSWER 与 CLARIFY，反馈提示只陈述已实现行为。
- [x] 覆盖 HTTP 联调测试、组件测试、构建及实际服务验证，记录缺失的外部依赖。
- [x] 真实 ES / Embedding / 模型的成功回答验收：模型配置已加载，本地 ES 已启动并重建发布知识索引。

初次联调环境发现：对话及 Embedding key 均缺失，本地 ES 9200 未监听。配置缺失须明确报错，不能借自动切换 MySQL 或模拟模型宣称全链路成功。

验证记录（2026-10-08）：
- Maven package 成功：rag-service 51 项、consultation-service 182 项测试通过。
- 客服前端相关 24 项测试通过，Vite build 通过；浏览器回归无运行时错误。
- 本地新版本服务已启动，真实网关验证 OFF_TOPIC / HIGH_RISK / UNCERTAIN 到客服及历史落库均通过。
- `node acceptance/ai-rag-smoke.mjs --require-answer` 在真实回答阶段按预期报失败：MODEL_UNAVAILABLE，RAG 日志明确为 EMBEDDING_API_KEY 缺失。所有本次测试创建的咨询均已结束。
- 新增总超时预算、配置错误不重试的回归；补齐明确授予管理员权限/感染病毒的风险识别，保持普通权限申请流程和软件更新排障不误拦。
- RAG YAML、Java 默认值和客服逐条引用门槛统一为 0.70；支持用同一个 RAG_CONFIDENCE_THRESHOLD 配置。代码审查发现的弱引用、冲突判断、权限申请误拦均已补回归并修复。

配置模板：`it-ticket-cloud/ai-secrets.example.yml`；详细对接与执行说明：`it-ticket-cloud/consultation-service/RAG-INTEGRATION.md`。

后续恢复记录（2026-10-08）：用户补齐模型配置后，重启客服与 RAG，直接验证对话模型 HTTP 200、Embedding HTTP 200 / 1024 维。按现有 localhost 配置部署 Elasticsearch 8.11.3（官方 ZIP 经 SHA-512 校验），仅绑定 127.0.0.1，初始化 knowledge_chunk，并通过 reindex 接口为两篇 PUBLISHED 当前版本知识重建本地索引。未修改知识内容与发布状态。真实“电脑坏了”返回通用 ANSWER；“VPN 无法连接的排查步骤”和“办公室 WiFi 速度慢的处理方式”均返回 ANSWER 及真实引用，分数分别为 0.8265 / 0.8414。信息不足时仍可能按既有置信度策略请求补充，不降低阈值绕过判断。

本地 ES 启动脚本：`it-ticket-cloud/scripts/start-elasticsearch.ps1`。数据保存在 `.devtools/elasticsearch-8.11.3/data`，重复启动会检查并复用现有本地集群。
