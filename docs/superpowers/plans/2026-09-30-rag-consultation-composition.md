# RAG 与 AI 客服完整组合实施计划

> **For agentic workers:** 使用 subagent-driven-development：一个编码子代理完成本任务，父级裁决与审查；只读项目子代理协助独立评审。步骤使用 checkbox 跟踪。

**Goal:** 将 rag-service 检索接入 AI 客服，并用可独立组合的检索、生成和策略组件替换原包办适配器。

**Architecture:** 单一 ComposedRagAdapter 编排 OfficeDomainClassifier、KnowledgeRetriever、RetrievalPolicy 和 AnswerGenerator。生成前及输出前分别核验当前发布版本；独立服务故障显式降级。HTTP 调用使用不可变身份与统一截止时间。

**Tech Stack:** Java 17、Spring Boot 3.2.5、现有 MyBatis、JDK HttpClient、JUnit 5/AssertJ、JDK HttpServer 测试 stub；不增加依赖。

## Global Constraints

- 必须遵循 `docs/superpowers/specs/2026-09-30-rag-consultation-composition-design.md` 的父级裁决。
- 不新增旧签名构造器、重复适配器、静默回退或双轨业务流程。内部调用方和测试同步迁移。
- 不覆盖用户前端未提交改动，不改变对外 AI DTO、会话、消息、幂等、SSE 或知识搜索契约。
- 不自动提交、推送、发布、重启正在运行的服务或写远端数据库；代码留在当前项目供评审。
- 不引入新运行依赖，不记录密钥、身份认证头、prompt、知识正文或内部推理。
- 不把检索相似度当作模型回答置信度；不二次归一化远端 score。

---

### Task 1: 完整组合链路与配置接线

**Files:**
- 创建 `it-ticket-cloud/consultation-service/src/main/java/com/itticket/consultation/adapter/ComposedRagAdapter.java`，作为唯一 RagAdapter。
- 创建 `adapter/RagCaller.java`、`adapter/RagCallContext.java`、`adapter/RagExecutionAudit.java`；修改 `RagAdapter.java`、`RagQuery.java`、`RagResult.java`、`GuardedRagClient.java`。
- 创建 `adapter/retrieval/KnowledgeRetriever.java`、`RetrievedKnowledge.java`、`RetrievalResult.java`、`MySqlKnowledgeRetriever.java`、`RagServiceKnowledgeRetriever.java`、`RetrievalPolicy.java`。
- 创建 `adapter/generation/AnswerGenerator.java`、`GenerationResult.java`、`OpenAiCompatibleAnswerGenerator.java`、`LocalKnowledgeAnswerGenerator.java`。
- 创建 `adapter/policy/OfficeDomain.java`、`OfficeDomainClassifier.java`、`SemanticOfficeDomainClassifier.java`、`LocalOfficeDomainClassifier.java`。
- 创建 `adapter/model/OpenAiCompatibleModelClient.java`；按实际共用需求创建有限依赖故障类型，避免重复 HTTP 错误解析。
- 删除旧 `adapter/OpenAiCompatibleRagAdapter.java`、`adapter/KnowledgeRagAdapter.java`，同步迁移其必要生成/传输/引用逻辑，不留下兼容壳。
- 修改 `config/ConsultationProperties.java`、`service/AiConsultationService.java`、`service/AiAnswerGuard.java`、`dto/KnowledgeHit.java` 注释和必要接口。
- 修改 `src/main/resources/application.yml`、consultation README；补 `it-ticket-cloud/rag-service/src/main/resources/application.yml` embedding api-key 接线及阈值说明、`it-ticket-cloud/nacos-config/gateway.yaml` RAG 路由。
- 可修改忽略的 `.devtools/start-remote.ps1` 设置本机 RAG 地址；不得自动执行该启动脚本。
- 在 `consultation-service/src/test/java/com/itticket/consultation/adapter/` 创建对应 HTTP/编排/装配测试；迁移原 adapter 与 guard/service 测试。
- 报告写入 `.devtools/rag-composition-report.md`，保留测试命令、红绿证据、结果与限制。

**Interfaces:**
- `KnowledgeRetriever.retrieve(RagQuery query, RagCallContext context)` 返回不可变 `RetrievalResult`，包含统一四态领域、可靠性、显式拒答原因、依赖状态、候选资料与 topScore。
- `AnswerGenerator.generate(RagQuery query, List<RetrievedKnowledge> material, RagCallContext context)` 返回 `GenerationResult`，包含回复类型、文本、使用版本 ID、模型置信度、冲突/超范围判定与模型版本；不得访问知识表或生成引用元数据。
- `OfficeDomainClassifier.classify(RagQuery query, RagCallContext context)` 返回四态，不接收资料。统一 HTTP 客户端仅提供受约束 JSON 请求/响应。
- `RagAdapter.answer(RagQuery query, RagCallContext context)` 返回 `RagResult`；GuardedRagClient 的服务入口仍为 `answer(query, requestId)`，在此冻结统一总截止时间并复用身份，不依赖工作线程 ThreadLocal。
- RagResult 使用明确的 `refusalReason`；移除旧的多构造器及重复风险/领域/冲突布尔表达，所有实际调用方和测试迁移。

- [x] **Step 1: 先写体现已裁决行为的失败测试，保存红阶段结果。**

测试从消费者结果与真实 HTTP 边界判断，而非断言源代码字符串。示例核心断言：

```java
assertThat(response.replyType()).isEqualTo(AiReplyType.REFUSE);
assertThat(response.refusalReason()).isEqualTo(AiRefusalReason.LOW_CONFIDENCE);
assertThat(modelGenerationRequests).isEmpty();
assertThat(ragRequest.path("categoryId").asText()).isEqualTo("C_NET");
assertThat(ragRequest.path("topK").asInt()).isEqualTo(5);
assertThat(ragUserIdHeader).isEqualTo("U_EMP01");
assertThat(response.citations().get(0).score()).isEqualByComparingTo("0.7503");
```

添加低置信拒答映射测试可先使用当前 RagResult 表达缺失的行为，再迁移结构；新组件尚不存在时，先针对已有真实入口复现缺口，而不是把编译错误当红阶段证明。使用完整 RAG 响应 fixtures，允许合法 score=null 项。必须覆盖设计的主要失败分支、真实模型 stub 的请求资料及最终引用。

- [x] **Step 2: 建立类型、装配与职责边界。**

通过 `@ConditionalOnProperty` 选择策略（或集中配置类装配），业务方法不判断供应商名。创建标准化记录，在 MySQL 适配器边界完成 `raw/(raw+1)`；远端保留原分数。统一调用上下文：

```java
public record RagCaller(String userId, String role) {}
public record RagCallContext(String requestId, long deadlineNanos, RagExecutionAudit audit) {
    public long remainingMillis() {
        return Math.max(0, java.util.concurrent.TimeUnit.NANOSECONDS.toMillis(deadlineNanos - System.nanoTime()));
    }
}
```

实际服务从已认证 CurrentUser 构造身份，所有 internal constructor 调用同步修改。每次 HTTP 的超时不得超过 context 剩余预算；达到截止时间不再重试或请求下一阶段。

- [x] **Step 3: 实现 HTTP 检索、统一策略与模型生成组合。**

`POST {AI_RAG_BASE_URL}/api/v1/rag/retrievals` 只发 question/categoryId/topK，传认证 userId/role 和 requestId，不跟随重定向。区分 HTTP 失败、code!=0、非法 JSON/字段、200 MODEL_UNAVAILABLE，均不能变成正常空检索。永久错误不重试。

策略控制流程：

```java
if (retrieval.refusalReason() != null) {
    return refuseWith(retrieval.refusalReason());
}
if (!retrieval.reliable()) {
    return generateWith(List.of()); // 仅正常 OFFICE_IT、无故障且没有拒答原因时可到达
}
List<RetrievedKnowledge> material = selectStableVerifiedMaterial(retrieval.items());
if (material.isEmpty()) {
    return refuseWith(AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
}
return generateWith(material);
```

`selectStableVerifiedMaterial` 在生成前核验每条实际依据，失效整批拒答而不是滤空。模型仅声明 usedVersionIds，编排器从真实资料重建引用。非本次资料版本拒绝；所有空引用通用回答服务添加依据说明；最终 guard 复核发布状态和模型置信度。

- [x] **Step 4: 同步迁移测试、删除旧实现与兼容代码。**

原12项模型协议测试保留有效行为并迁移至分类器/生成器/完整编排测试；原37项输出守卫测试迁移显式 refusalReason，不降级原覆盖。补装配组合测试，验证 local/rag-service × local/openai-compatible 四组可独立选择；客户端故障时没有隐式本地搜索。

- [x] **Step 5: 配置与文档交付。**

配置增加 `retrieval-provider: ${AI_RETRIEVAL_PROVIDER:rag-service}`、独立检索 endpoint/timeout；补 embedding 的 `api-key: ${EMBEDDING_API_KEY:}`。README 记录部署所需变量、当前阈值来源、身份信任边界、不可用与空检索差异、真实服务未验证情况及完整分层结构。不要把未实现的索引生命周期写成交付。

- [x] **Step 6: 验证与交付父级审查。**

```powershell
$env:JAVA_HOME='C:\Users\admin\Desktop\project\ServiceTicketSystem\.devtools\jdk-17.0.20.1+1'
& 'C:\Users\admin\Desktop\project\ServiceTicketSystem\.devtools\apache-maven-3.9.16\bin\mvn.cmd' -f it-ticket-cloud/pom.xml -pl consultation-service,rag-service,gateway -am test '-Dfile.encoding=UTF-8'
python -m unittest discover -s docs/tests -p 'test_*.py'
git diff --check
```

生成报告，返回状态、改动摘要、测试计数及尚未验证的环境条件。父级审查方案符合性和代码质量；如有重要缺口由同一编码子代理修复，随后进行针对性复核。
