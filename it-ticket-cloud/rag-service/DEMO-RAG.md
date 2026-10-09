# RAG 知识库模块 · 演示代码跳转地图

> **用法**：在 IDEA 中打开本文件，点编辑器右上角的 **分屏预览图标**（Split / Preview），
> 在右侧预览面板里点击下面的链接即可跳转到对应代码行。
> 链接格式为 IDEA 原生支持的 `文件路径#L行号`。
>
> 演示顺序：① 上传切片 → ② 链路追踪 → ③ 生命周期详情 → ④ 状态流转 → 加分项。

---

## ① 上传文档：开始切片并写入 ES 知识库

界面操作：知识库工作台 →「文档上传与链路追踪」页签 → 选文件 → 入库方式（存为草稿 / 直接发布）→「开始切片并写入 ES 知识库」。

| 环节 | 代码位置 |
|---|---|
| 前端提交表单 | [KnowledgeAdminView.vue#L639](frontend/src/views/KnowledgeAdminView.vue#L639) `submitUploadAndProcess()` |
| 前端 API 封装 | [api/index.js#L91](frontend/src/api/index.js#L91) `ragApi.uploadDocument` |
| 后端入口（作者取网关 JWT） | [RagDocumentController.java#L103](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/controller/RagDocumentController.java#L103) `uploadDocument()` |
| 流水线编排（四阶段） | [RagPipelineService.java#L87](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/RagPipelineService.java#L87) `processDocumentUpload()` |
| 步骤1 文档解析（UTF-8/GBK 兼容） | [DocumentParserService.java#L76](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/DocumentParserService.java#L76) `parse()` |
| 步骤2 智能切片（标题层级+滑动窗口） | [DocumentChunkerService.java#L47](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/DocumentChunkerService.java#L47) `chunkDocument()` |
| 步骤3 向量化（1024 维，百炼/Maas） | [EmbeddingClientService.java#L76](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/EmbeddingClientService.java#L76) `generateEmbeddings()` |
| 步骤4 入库分支（草稿不写 ES） | [RagPipelineService.java#L209](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/RagPipelineService.java#L209) `publishNow` 分支 |
| ES 切片写入（发布通道） | [ElasticsearchIndexService.java#L147](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/ElasticsearchIndexService.java#L147) `indexChunks()` |

**讲点**：选「存为草稿」时步骤4显示 SKIPPED —— 草稿不进检索索引（AI-001：未发布内容不得被 AI 读到）。

---

## ② 右侧链路追踪详情（Pipeline Trace）

界面操作：上传完成后右侧四张步骤卡片；或左下角「最近执行链路记录」点一条。

| 环节 | 代码位置 |
|---|---|
| 各阶段度量组装（耗时/字符/Token） | [RagPipelineService.java#L87](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/RagPipelineService.java#L87)（每阶段一个 `PipelineStageVO`） |
| 链路查询接口 | [RagDocumentController.java#L144](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/controller/RagDocumentController.java#L144) `getTrace()` |
| 内存 traceStore 读取 | [RagPipelineService.java#L460](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/RagPipelineService.java#L460) `getTraceById()` |

**讲点**：毫秒级可观测性；注意 trace 只存内存，服务重启即清空（演示用设计，不入库）。

---

## ③ 知识生命周期管理 → 查看知识详情

界面操作：「知识生命周期管理」页签 → 列表按状态过滤 → 某行「详情 / 操作」打开抽屉。

| 环节 | 代码位置 |
|---|---|
| 文章列表（状态过滤+分页） | [KnowledgeArticleController.java#L112](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/controller/KnowledgeArticleController.java#L112) `listArticles()` |
| 前端打开抽屉 | [KnowledgeAdminView.vue#L741](frontend/src/views/KnowledgeAdminView.vue#L741) `openDetail()` |
| 详情接口（文章+版本+审计三段） | [KnowledgeArticleController.java#L128](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/controller/KnowledgeArticleController.java#L128) `detail()` |
| 正文展示（解析 content JSON 四键） | [KnowledgeAdminView.vue#L902](frontend/src/views/KnowledgeAdminView.vue#L902) `versionContent` |

**讲点**：审核人看着「📄 知识内容（审核对象）」做决定；下方流转审计时间线不可篡改（SM-001）。

---

## ④ 状态流转：提审 / 发布 / 驳回 / 下线

状态机本体在 [KnowledgeStore.java](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/KnowledgeStore.java)（事务内守卫），ES 联动编排在 [KnowledgeLifecycleService.java](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/KnowledgeLifecycleService.java)（事务提交后执行）。

| 操作 | 前端按钮 | 后端守卫（重点） | 系统联动 |
|---|---|---|---|
| 草稿 → 待审核 | [doSubmit#L762](frontend/src/views/KnowledgeAdminView.vue#L762) | [submitForReview#L104](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/KnowledgeStore.java#L104) 仅 DRAFT 可提审 | 审计 + `KNOWLEDGE_SUBMITTED` 事件 |
| 待审核 → 已发布 | [doPublish#L777](frontend/src/views/KnowledgeAdminView.vue#L777) | [approveAndPublish#L133](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/KnowledgeStore.java#L133)：状态校验 + **AC-25 自审拦截** + **高风险须平台管理员** + 乐观锁 | 事务后切片写 ES（[indexVersion#L435](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/RagPipelineService.java#L435)），失败标待补偿不回滚 |
| 待审核 → 草稿 | [doReject#L811](frontend/src/views/KnowledgeAdminView.vue#L811) | [rejectToDraft#L182](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/KnowledgeStore.java#L182) 原因必填 | 原因写入审计表 |
| 已发布 → 已下线 | [doOffline#L839](frontend/src/views/KnowledgeAdminView.vue#L839) | [offline#L207](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/KnowledgeStore.java#L207) 原因必填 | ES 切片置 OFFLINE（[updateChunkStatusByArticleId#L537](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/ElasticsearchIndexService.java#L537)）→ 搜索/AI 立刻不可见（AC-27） |

审计与事件写入：[insertTransition#L240](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/KnowledgeStore.java#L240)、[insertEvent#L268](it-ticket-cloud/rag-service/src/main/java/com/itticket/rag/service/KnowledgeStore.java#L268)（EV-001 信封，aggregate_version 单调递增）。

---