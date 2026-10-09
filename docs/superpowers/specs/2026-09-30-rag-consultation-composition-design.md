# RAG 与 AI 客服完整组合方案：父级裁决

## 授权与实施约束

用户要求一个子代理读取项目、另一个子代理编码，由父级代理裁决。只读评审已完成；用户于 2026-09-30 明确选择完整组合方案，并要求本次及后续工作不得为兼容省事牺牲代码结构。

本轮同步迁移内部调用方和测试，不新增旧签名构造器、重复适配器、静默回退或双轨业务流程。保留有实际产品用途的本地检索和本地知识拼装策略，通过统一接口组合；它们不是兼容层。保留现有对外 AI DTO、咨询生命周期、消息持久化、幂等、SSE 和知识搜索协议。用户已有前端修改不得覆盖。工作在当前项目中，交付可评审的未提交改动，不自动提交、推送或发布。

## 根因与附件评审

当前 OpenAiCompatibleRagAdapter 同时负责语义分类、MySQL 检索、HTTP 模型调用、生成协议和引用重建；KnowledgeRagAdapter 另有本地检索/拼装实现。RagAdapter 的真实方法为 answer，而不是附件所述 retrieve。仅插入远端分支会继续扩大原类并维持重复链路。

附件的服务边界正确：rag-service 负责检索，consultation-service 负责生成和会话。但存在以下实际差异：

- RAG 检索接口需要认证身份；GuardedRagClient 的工作线程无法直接读取请求线程的 ThreadLocal 身份。
- RagRetrievalService.toResponse 未调用 buildVerifiedCitations；后者也仅校验文章发布状态，没有核对当前 versionId。因此 publishedOnly 只是声明，不能替代数据库复核。
- ES 检索异常也被捕获为 HTTP 200 + MODEL_UNAVAILABLE；文章搜索端点与检索端点不能混用故障语义。
- 附件可靠阈值为 0.70，运行 YAML 为 0.65，属性类默认为 0.70。以服务配置的 reliable/refusalReason 为策略依据，不用模型置信度覆盖检索裁决。
- 检索 score 已是余弦相似度，不得再执行 MySQL 的 s/(s+1)。纯 BM25 命中 score 可为 null，应接受真实协议但不得伪造置信度或引用。
- EMBEDDING_API_KEY 缺少 YAML 显式绑定；Nacos 网关模板缺 RAG 路由。
- RAG 领域分类目前为关键词规则，不能替代当前独立模型语义分类。

## 组件与数据流

唯一 RagAdapter 实现 ComposedRagAdapter 负责顺序编排：领域/风险判定 → KnowledgeRetriever → RetrievalPolicy（拒答、可靠性与生成前版本复核）→ AnswerGenerator → 从实际资料重建引用 → 现有 AiAnswerGuard 输出复核。

组件约定：

1. KnowledgeRetriever：仅获取标准化、不可变 RetrievalResult。MySqlKnowledgeRetriever 在边界归一化 MySQL 原始相关度；RagServiceKnowledgeRetriever 解析 HTTP 包络、保留远端分数、indexVersion、策略和 nullable BM25 score。不生成答案、不修改业务数据。
2. AnswerGenerator：仅接收通过检索策略的资料并生成标准化 GenerationResult。OpenAiCompatibleAnswerGenerator 不检索、不决定引用元数据；LocalKnowledgeAnswerGenerator 只拼装已验证资料，无资料时拒答，不伪装具有模型通用能力。
3. OfficeDomainClassifier：在生成前独立判断四态。外部模型模式使用独立语义分类；纯本地模式使用明确的保守规则，不能宣传为语义模型。远端 RAG 的 OFF_TOPIC/HIGH_RISK/UNCERTAIN 裁决可收紧，不能放宽已作出的裁决。
4. OpenAiCompatibleModelClient：分类器与生成器共用 HTTP、协议解析、有限错误分类和取消支持；它不访问知识库，不参与业务策略。
5. RetrievalPolicy：独立于生成策略的统一闸门。RAG LOW_CONFIDENCE 必须原样拒答；服务故障不能解释为无命中。只有 OFFICE_IT、正常检索且无相关依据时才允许无引用通用生成。
6. AiAnswerGuard：输出阶段的最终闸门，保留当前发布版本复核、模型置信度和结构化拒答。RagResult 使用显式 refusalReason，迁移掉可互相矛盾的 offTopic/highRiskTopic/knowledgeConflict 标记和旧构造器。生成文本无来源时由服务稳定添加“无知识库依据”的说明。

RagQuery 显式携带不可变的已认证调用身份（仅 userId、role），在请求线程由服务构造。工作线程不读取 Servlet/ThreadLocal，不转发完整个人信息或模型密钥。RagCallContext 携带 requestId 和单一业务请求的总体截止时间，所有分类、检索、生成与有限重试共享预算。保留 GuardedRagClient 并发、熔断、取消能力；401/403 和其他永久错误不重试。

## 检索策略与引用

- 可靠批次中的 score=null 资料不作为知识依据；有效数字分数直接保留。当前服务契约严格要求 indexVersion == versionId，客户端核验相等。
- 远端 reliable 是整批最高分策略，不代表全部候选可靠。当前接口不提供阈值元数据，本轮只选 score == topScore 的最高分有效资料（同分稳定处理）作为生成依据，不在消费端复制 0.65/0.70。本地检索的材料选择由本地检索策略确定。
- 同版本多切片不能由 map 后写覆盖随机选择；同分以稳定 chunkId 排序选取，正文和 snippet 来自同一实际传给生成器的有效资料。相同 versionId 对应不同 articleId、相同 chunkId 的矛盾内容或元数据视为协议失败。
- 截断后的资料是引用重建的唯一来源，snippet 必须存在于实际生成输入，不能从未传入模型的完整内容重建来源。
- 可靠资料进入模型前逐条检查 articleId/versionId 为 PUBLISHED 当前版本；任一选用资料失效则整体拒答，不滤空后冒充正常无命中。数据库失败明确降级。
- 可靠命中如果没有任何可使用依据，拒答，不生成通用答案。真正不相关批次不向模型发送知识正文。
- 远端四态、suggestedReplyType、refusalReason、reliable 和 publishedOnly 的组合必须一致；矛盾字段明确判为非法响应，不允许进入生成。无故障正常空检索与依赖拒答分开处理。
- 模型声明的 versionId 必须来自本次实际送入生成器的资料；不存在即无效输出，不能静默丢弃。引用 title/snippet/score 从资料重建。生成后由 AiAnswerGuard 再核对发布状态，覆盖生成期间下线场景。
- 已检索版本及耗时沿用现有审计；不保存完整 prompt、内部推理、认证头或知识正文。

纯本地拼装结果不存在模型自评。本地策略的 confidence 明确定义为基于检索依据的保守答案相关度估计，modelVersion 标记 local-extractive；可以取最主要依据的相关度，但不能声称是模型概率，也不能覆盖 RetrievalPolicy 的拒答。外部生成的 confidence 则只来自通过协议校验的模型输出，与引用 score 分开保留。

本地摘录不具备语义冲突检测能力。父级裁决不恢复旧实现中“同分类、不同标题、分数接近即判知识冲突”的标题近似规则；该规则不能证明内容互斥。外部模型生成仍必须保留知识冲突拒答，部署说明应如实注明本地模式的能力边界。

## 最终审查追加裁决

最终发布复核必须绕过咨询幂等事务的旧一致性快照。使用直接查询当前发布 `version_id` 的 `FOR SHARE NOWAIT`，保留文章/版本归属和 current_version_id 条件；MyBatis 查询不使用缓存并清除会话缓存。生成前工作线程自动提交查询结束即释放锁；生成后的共享锁只在回答落库阶段持有至事务提交。锁冲突显式降级，不将旧快照结果当成当前事实，也不额外开启占用连接池的新事务。

该取舍依据 [MySQL 一致性读](https://dev.mysql.com/doc/refman/8.0/en/innodb-consistent-read.html) 和 [锁定读](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html)：普通 RR 查询沿用首次快照，锁定读读取当前状态。验收使用隔离的本机 MySQL 8.0.43 与真实 Spring 事务、SqlSession 和 mapper，覆盖并发下线、会话缓存和锁冲突，不操作远端业务库。

依赖失败和非法生成结果须保留已经取得的检索版本审计，失败分类及重试属性保持真实。每个业务调用创建独立、线程安全的 `RagExecutionAudit`，与不可变身份和截止时间分离；检索返回时即时记录已取得版本，隔离壳正常返回、硬超时和有限重试的退出都取稳定快照。不能等待已取消任务来补审计或延长截止时间。后一次更早失败不得抹去前一次已取得版本；汇总仅用于审计，引用仍只能来自本次实际传给生成器的资料。

## 配置、上线范围与非目标

AI_PROVIDER 选择生成/分类策略，AI_RETRIEVAL_PROVIDER 独立选择 local/rag-service；默认实际应用配置使用 rag-service，AI_RAG_BASE_URL 指定受信任的服务基址，默认 http://127.0.0.1:8302，AI_RAG_REQUEST_TIMEOUT_MS 为检索单调用上限且受总截止时间约束。策略选择发生在 Spring 装配阶段，不在业务方法中堆积供应商判断。不引入新运行依赖。

补齐 EMBEDDING_API_KEY 绑定和 Nacos RAG 路由；配置说明记录当前运行阈值与保守本地领域策略。当前桌面服务使用 28302 端口，启动脚本可明确设置 AI_RAG_BASE_URL=http://127.0.0.1:28302，不能硬编码为所有环境的默认值。

本轮不扩展 rag_index_pointer、Outbox 消费者、provider 配置管理或知识生命周期，也不修改远端数据库、上传/发布知识、运行真实高风险操作或自动切换正在运行的服务。

## 验收

本地 HTTP stub 与真实组合组件验证：远端请求参数和身份、四态领域、可靠命中直接分数、nullable BM25、重复切片、LOW_CONFIDENCE 拒答、正常空检索通用回答、HTTP/包络/业务降级错误、401 不重试、共同超时预算、旧版本不能进入模型、伪造引用不能输出、生成期间下线最终拒答、两种检索与两种生成可独立组合。Spring 上下文验证每种受支持配置仅装配一个检索器、分类器、生成器和 RagAdapter。

修改前基线：consultation-service 165 项、common/common-web 各 3 项测试通过。实施后运行 consultation-service、rag-service、gateway 相关 Maven 测试，以及 docs/tests 契约检查；只在出现新改动或失败时重复相关检查。真实 ES/embedding/model 未验证时须明确说明，不把 stub 测试称为真实端到端联调。

## 交付结果

父级最终裁决通过。独立只读复核确认事务当前读和失败审计两项问题均已解决，未发现修复引入的新问题。

- 有效 Maven 测试共 262 项：consultation 206、rag 48、gateway 2、common/common-web 各 3；全部通过，包含真实本机 MySQL 事务回归 4 项。
- 文档契约 6 项通过；硬超时变异恢复后的针对性 40 项再次通过，未重复计入 262 项。
- 三个可执行候选包位于 `.devtools/rag-composition-package/` 对应服务的 `target/`。原目录 RAG JAR 被正在运行的服务占用，因此使用隔离的源码副本打包。父级复核 233 个源码/POM 哈希与工作区一致，三个候选包哈希与 artifacts.json 一致。
- 现有服务未重启，真实 ES、embedding 与生成模型尚未端到端联调。前端原有未提交修改保留，代码未提交或推送。
- 临时 MySQL 已停止；目录删除被工具安全策略拦截，测试数据保留在忽略的 `.devtools/rag-mysql-test-d8fd5f52a9a44fadb354073589fd2e1a/`。

详细日志与构建清单见 `.devtools/rag-composition-report.md`；部署变量和策略说明见 `it-ticket-cloud/consultation-service/README.md`。
