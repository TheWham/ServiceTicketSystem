# 语义答案缓存（带知识版本哨兵）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 consultation-service 增加"查询向量余弦相似度命中、MySQL 知识当前版本哨兵前置复核"的进程内答案缓存，默认关闭，命中 0 次模型调用直出历史成功回答。

**Architecture:** 两个新组件（`EmbeddingClient`、`SemanticAnswerCache`）在装配期注入唯一编排器 `ComposedRagAdapter`：lookup 插在域闸门之后、检索之前（安全裁决永不被缓存短路），write 插在成功结果组装之后。命中条目出缓存前对每条 citation 的 versionId 做本地 SQL 当前读复核（复用 `KnowledgeQueryService.isPublishedCurrentVersion`），失效即驱逐并按未命中穿透。

**Tech Stack:** Java 17、JDK HttpClient（复用 `DependencyHttpClient`）、Jackson、无新增第三方依赖；测试用 JDK HttpServer stub + Mockito/AssertJ（存量惯例）。

**Spec:** `docs/superpowers/specs/2026-11-04-semantic-answer-cache-design.md`（论证以 spec 为准，本文与其冲突时以 spec 为准，但以下三条**有意细化**除外，均已在下文标注）。

**与 spec 的三条有意细化（其余一字不差执行）：**
1. spec 中 `embed(String text)` 失败签名写作"抛 EmbeddingUnavailable"——实现**统一抛既有 `DependencyFailure`**（本模块依赖失败的唯一载体，不新增异常类）；缓存侧捕获并计入 depFailures。
2. `CachedAnswer` 值载荷直接承载不可变的 `RagResult`（字段集与 spec 列举一致：answerText/citations/confidence/modelVersion/retrievedVersionIds），不再逐字段抄写。
3. spec 要求"命中信息进 `persistAiMessage` metadata"且"不在 RagResult 上新增**对外**字段"的具体落地：`RagResult` 追加内部组件 `cacheHit`（默认 null，`AiChatResponse` 对外契约不变；K medios hit 信息随结果流到 service 层）。

## Global Constraints

- 默认 `itticket.consultation.ai.cache.enabled=false`，此时行为与现状**完全一致**（既有 206 项测试不回归）。
- `enabled=true` 且 `embedding-model` 为空 → 启动失败（fail-fast，不做半启用）；`threshold` 必须在 [0.90, 1.0]。
- 缓存只写 `status==SUCCESS && replyType==ANSWER && refusalReason==null && citations 非空 && !generalAnswer` 的结果；拒答/CLARIFY/generalAnswer/降级**永不缓存**。
- 多轮追问（`priorTurns` 非空）永不 lookup、永不 write。
- 缓存任何阶段失败（嵌入、哨兵 SQL）只降级为本次不使用缓存 + depFailures 计数 + WARN 留因，**绝不阻断实时链路、绝不伪装普通未命中**；也不允许被 `ComposedRagAdapter` 的 `catch (DependencyFailure)` 折叠成降级 RagResult。
- 域闸门（`restrict`）永远先于缓存执行：HIGH_RISK/OFF_TOPIC 实时拒答，缓存不能短路安全裁决。
- 不新增 Maven 依赖；中文 javadoc 沿用模块惯例。
- 构造器签名变更同步迁移**全部**调用点（`AiCompositionConfig` + 4 个测试文件的 5 处 `new ComposedRagAdapter`），不留旧构造器/兼容壳。
- 提交只含本任务文件，不混入工作区已有的他人未提交修改（`deploy/README.md`、`services/python-retrieval/rag_pipeline/ingestion/wiki_generator.py`、release 系列、specs/2026-10-*）。

## Review Focus

1. **嵌入端点故障**（enabled=true 但 `/embeddings` 不可用/超时/畸形响应）：必须实时回答照常成功、depFailures++，异常不得穿破到编排器被折叠成降级。→ Task 2（畸形/超时/错误码单测）、Task 5（Task 5c 步骤）、Task 9（HTTP 场景 4）。
2. **相似度边界**：恰等于 threshold 命中，略低不命中。→ Task 4a。
3. **高危/离题问题即使缓存池有相似条目也实时拒答**。→ Task 5（Task 5d 步骤）。
4. **工具旁路（build 单/查工单）既不 lookup 也不 write**。→ Task 5（Task 5e 步骤）。
5. **命名空间漂移**：`embedding-model` 配置变更后旧条目不命中（向量不可比）。→ Task 4b。
6. **TTL/LRU/哨兵三类驱逐分别计数**，不能混成一个数字。→ Task 3b、Task 4c。
7. **哨兵 SQL 异常**（validator 抛 RuntimeException）：按未命中穿透 + depFailures++，不放出不完整答案也不报错。→ Task 4c。

---

### Task 1: 配置项 `ConsultationProperties.Ai.Cache`

**Files:**
- Modify: `it-ticket-cloud/consultation-service/src/main/java/com/itticket/consultation/config/ConsultationProperties.java`（`Ai` 类内加嵌套 `Cache` 字段）
- Modify: `it-ticket-cloud/consultation-service/src/main/resources/application.yml`（`itticket.consultation.ai.cache` 块）
- Test: `it-ticket-cloud/consultation-service/src/test/java/com/itticket/consultation/config/AiCachePropertiesTest.java`

**Interfaces:**
- Produces: `ConsultationProperties.Ai.Cache`（getter：`isEnabled()`,`getThreshold()`,`getMaxEntries()`,`getTtlSeconds()`,`getEmbeddingModel()`,`getEmbeddingBaseUrl()`,`getEmbeddingTimeoutMs()`,`getMinWriteIntervalSeconds()`），后续所有任务经 `properties.getAi().getCache()` 消费。

- [ ] **Step 1: 写失败测试**（`AiCachePropertiesTest`）：纯 `new ConsultationProperties().getAi().getCache()` 断言默认值：enabled=false、threshold=0.93、maxEntries=500、ttlSeconds=604800、embeddingModel=null、embeddingBaseUrl=null、embeddingTimeoutMs=1000、minWriteIntervalSeconds=0。

- [ ] **Step 2: 跑测试确认编译失败**（类不存在）

Run: `mvn -q test -Dtest=AiCachePropertiesTest -pl it-ticket-cloud/consultation-service`（下同，省略 -pl）
Expected: 编译错误 `cannot find symbol: method getCache()`

- [ ] **Step 3: 实现**：`Ai` 内加 `private Cache cache = new Cache();` + `@Data public static class Cache { private boolean enabled = false; private double threshold = 0.93; private int maxEntries = 500; private long ttlSeconds = 604800; private String embeddingModel; private String embeddingBaseUrl; private long embeddingTimeoutMs = 1000; private long minWriteIntervalSeconds = 0; }`（javadoc 说明域名来源与"不同模型向量不可比→模型名进命名空间"）。yml 在 `itticket.consultation.ai:` 末尾加 `cache:` 块：`enabled: ${AI_SEMANTIC_CACHE_ENABLED:false}`、`threshold: ${AI_SEMANTIC_CACHE_THRESHOLD:0.93}`、`max-entries: ${AI_SEMANTIC_CACHE_MAX_ENTRIES:500}`、`ttl-seconds: ${AI_SEMANTIC_CACHE_TTL_SECONDS:604800}`、`embedding-model: ${AI_CACHE_EMBEDDING_MODEL:}`、`embedding-base-url: ${AI_CACHE_EMBEDDING_BASE_URL:}`（注释注明为空回退 `ai.base-url`，前提=同供应商族提供 `/embeddings`，与 Python `KspEmbeddingProvider` 同族）、`embedding-timeout-ms: ${AI_CACHE_EMBEDDING_TIMEOUT_MS:1000}`。

- [ ] **Step 4: 测试通过后提交**：`git add` 上述两文件 + 测试 → `git commit -m "feat(cache): 语义答案缓存配置项(默认关闭)"`

---

### Task 2: `EmbeddingClient` + `OpenAiCompatibleEmbeddingClient`

**Files:**
- Create: `src/main/java/com/itticket/consultation/adapter/embedding/EmbeddingClient.java`
- Create: `src/main/java/com/itticket/consultation/adapter/embedding/OpenAiCompatibleEmbeddingClient.java`
- Create: `src/main/java/com/itticket/consultation/adapter/embedding/package-info.java`（中文说明该包职责）
- Test: `src/test/java/com/itticket/consultation/adapter/embedding/OpenAiCompatibleEmbeddingClientTest.java`

**Interfaces:**
- Consumes: `DependencyHttpClient.post(URI, JsonNode, Map<String,String>, RagCallContext, long)`；Task 1 的 `Cache` 配置（由调用方传入，本类不读 properties）。
- Produces: `public interface EmbeddingClient { /** 归一化（L2=1）向量；失败抛 DependencyFailure（见 Global Constraints 细化 1）。 */ float[] embed(String text, RagCallContext context); }`；`public OpenAiCompatibleEmbeddingClient(String baseUrl, String model, String apiKey, long timeoutMillis, DependencyHttpClient http)`。

- [ ] **Step 1: 写失败测试**（`OpenAiCompatibleEmbeddingClientTest`，JDK HttpServer 模板照抄 `RagCompositionHttpTest` 的 start/stop 惯例）：
  - 成功：stub `/embeddings` 回 `{"data":[{"embedding":[3.0,4.0]}]}` → 断言返回 `[0.6,0.8]`（L2 归一化），且请求体为 `{"model":"...","input":["..."]}`、带 `Authorization: Bearer` 头、带 `X-Request-Id`。
  - 畸形：`{"data":[]}`、缺 `data`、`embedding` 含非数字、零向量 `{"data":[{"embedding":[0,0]}]}` → 各自 `DependencyFailure`。
  - 错误码：401 → `DependencyFailure`（errorClass=AUTH_FAILED）；500 → UNAVAILABLE。
  - 超时：stub `Thread.sleep(400)` 且 timeoutMillis=200 + `RagCallContext` deadline 充足 → `DependencyFailure`（errorClass=TIMEOUT）。
  - 预算耗尽：`RagCallContext` 已过期（`deadlineNanos=System.nanoTime()-1`）→ `DependencyFailure` TIMEOUT（嵌入计入统一预算的证明）。

- [ ] **Step 2: 跑测试确认失败**（类不存在，编译错误）

- [ ] **Step 3: 实现**：POST `{baseUrl}/embeddings`，body `{"model":...,"input":[text]}`（照 `OpenAiCompatibleModelClient` 用 `JsonNodeFactory` 组装），`http.post(...)` 时长上限传 timeoutMillis；解析 `data[0].embedding` 为 float[]，空/缺/非数字/零范数 `DependencyFailure.invalid()`（缩 kebab 为既有惯例）；最后 L2 归一化后返回。

- [ ] **Step 4: 测试通过 → 提交**：`git commit -m "feat(cache): OpenAI 兼容嵌入客户端(L2 归一化/统一预算)"`

---

### Task 3: `SemanticAnswerCache` —— 存储与 write 路径

**Files:**
- Create: `src/main/java/com/itticket/consultation/adapter/cache/CachedAnswer.java`
- Create: `src/main/java/com/itticket/consultation/adapter/cache/CacheHitInfo.java`
- Create: `src/main/java/com/itticket/consultation/adapter/cache/CacheStats.java`
- Create: `src/main/java/com/itticket/consultation/adapter/cache/SemanticAnswerCache.java`
- Create: `src/main/java/com/itticket/consultation/adapter/cache/package-info.java`
- Test: `src/test/java/com/itticket/consultation/adapter/cache/SemanticAnswerCacheTest.java`

**Interfaces:**
- Consumes: Task 1 `Cache` 配置；Task 2 `EmbeddingClient`；`BiPredicate<String,String> versionCheck`（哨兵，Task 4 才用）；`java.time.Clock`（可注入，TTL 测试）。
- Produces（后续任务的依赖契约）：
  - `public record CachedAnswer(RagResult result, double similarity) {}`
  - `public record CacheHitInfo(double similarity, String scope) {}`（Task 5 挂到 `RagResult`）
  - `public record CacheStats(long hits, long realMisses, long depFailures, long evictionsTtl, long evictionsLru, long evictionsSentinel, long entries, double hitRate, double maxHitSimilarity, List<Double> recentSimilarities) {}`（hitRate=hits/(hits+realMisses)，分母 0 取 0；recentSimilarities=最近 50 次命中相似度）
  - `public SemanticAnswerCache(ConsultationProperties.Ai.Cache config, EmbeddingClient embeddings, BiPredicate<String, String> versionCheck, Clock clock)`；`public static SemanticAnswerCache disabled()`（停用实例，lookup/write 全直通，供 `enabled=false` 默认装配与测试占位）
  - `public Optional<CachedAnswer> lookup(RagQuery query, RagCallContext context)`（Task 4 实现）；`public void write(RagQuery query, RagResult result)`（本任务实现）；`public CacheStats stats()`

- [ ] **Step 1: 写失败测试** —— write 路径（固定 `EmbeddingClient` lambda 返回受控向量；`versionCheck` 先传 `(a,v)->true`；`Clock.fixed`）：
  - 成功写入：合法 `RagResult`（SUCCESS/ANSWER/citations 非空）→ `stats().entries()==1`，无任何计数（hits/realMisses/depFailures 均 0；write 不计数）。
  - 五类不写：拒答、CLARIFY、`generalAnswer=true`（citations 空）、降级（TIMEOUT/UNAVAILABLE）、citations 空 → entries 0。
  - 追问不写：`RagQuery.priorTurns` 非空 → entries 0。
  - 嵌入失败：lambda 抛 `DependencyFailure`（用 `DependencyFailure.invalid()` 或 new）→ 不写 + `depFailures==1`，且**不向外抛**。
  - disabled 实例：`disabled().write(...)` 与 `disabled().stats()` 正常，lookup 恒 empty。
  - 去重替换：同义问题（相似度≥threshold）再写 → 仍 1 条且内容为新值（借 lookup 验证：见 Task 4 命中后替换断言；此处仅断言 entries 仍为 1）。
  - LRU 淘汰：`maxEntries=2` 写 3 条 → entries==2，最久未访问者被逐，`evictionsLru==1`。
  - TTL 懒清理：`ttlSeconds=3600`，写入后把 Clock 拨过期，再 lookup/write 时驱逐，`evictionsTtl==1`。
  - `minWriteIntervalSeconds=60`：同条目替换窗口内再写 → 内容不刷新、无计数。

- [ ] **Step 2: 跑测试确认失败**（类不存在）

- [ ] **Step 3: 实现**：内部 `private static final class Entry { String questionText; float[] questionVector; String embeddingModel; String categoryId; String assetId; RagResult result; Instant createdAt; volatile Instant lastAccessed; long hitCount; }`，`ArrayList<Entry>` 容器；方法级 `synchronized` 保护容器（**嵌入调用必须在锁外**，`embed` 不进临界区）；计数器用 `AtomicLong`（hits/realMisses/depFailures/evictionsTtl/evictionsLru/evictionsSentinel/replaces）+ 最近相似度有界队列。文本规范化 = trim + 连续空白折叠为单空格。哨兵查询写在 Javadoc：本任务不调 versionCheck。write 门槛顺序：enabled → 结果五条件 → history 空 → embed（锁外，catch `DependencyFailure`→depFailures++/WARN/log requestId/context.errorClass() 不吞错）→ 锁内：懒清理过期条目 → 查同命名空间+同作用域+相似度≥threshold 的替换位（在 `minWriteInterval` 窗口内则跳过）→ 有则原位替换 → 无则超上限先 LRU 逐出再追加。

- [ ] **Step 4: 测试通过 → 提交**：`git commit -m "feat(cache): 语义缓存存储与写路径(准入门槛/LRU/TTL/替换)"`

---

### Task 4: `SemanticAnswerCache` —— lookup 路径与哨兵

**Files:**
- Modify: `src/main/java/com/itticket/consultation/adapter/cache/SemanticAnswerCache.java`
- Test: `src/test/java/com/itticket/consultation/adapter/cache/SemanticAnswerCacheTest.java`（追加）

**Interfaces:**
- Consumes: Task 3 全部；`BiPredicate<String,String> versionCheck`（注入 `KnowledgeQueryService::isPublishedCurrentVersion`）。
- Produces: `lookup` 完整语义（Task 5 的 ComposedRagAdapter 只调 `lookup`/`write`，门控 history/tool 由 Task 5 侧分担：tool 由编排器判定，lookup 内部不再重复判 tool）。

- [ ] **Step 1: 写失败测试**：
  - **边界**：构造向量对使余弦恰 = 0.93 → 命中；0.929… → 不命中（realMisses++）。
  - **命名空间**：写入后把 `config.getEmbeddingModel()` 换名重配一个 cache 实例（同容器不可行——新实例）……改为：直接用**同一实例、两批向量维度不同**的 embed stub（模拟模型切换）→ 不命中且维度不匹配条目跳过；再如 `config.embeddingModel` 换名重启进程语义，用两个实例分别验证互不可见（namespace 隔离靠配置模型名）。
  - **作用域**：条目 category="C_NET" 与查询 category="C_OTHER" → 不命中；entry 存 category、查询 category=null → 命中（null 通配，spec 规则）；assetId 同理。
  - **哨兵驱逐**：写入 2 条，翻转 `versionCheck` 对某 versionId 返回 false → 询问该条目 → 不命中 + `evictionsSentinel==1` + `realMisses==1` + 条目从 stats().entries() 消失；另一条不受影响。
  - **哨兵异常**：`versionCheck` 抛 `RuntimeException("db down")` → lookup 返回 empty，`depFailures==1`（不计 realMisses——注意：这是"依赖失败"，不是未命中）。
  - **命中刷新**：命中后命中条目 hitCount/lastAccess 刷新可通过后续 LRU 淘汰顺序间接断言（先写 A、命中 A、写 B、写 C（maxEntries=2）→ 被逐的是 B 不是 A）。
  - **嵌入失败**：stab 抛 `DependencyFailure` → empty + `depFailures==1`（不计 realMisses）。
  - **追问不查**：priorTurns 非空 → empty 且**无任何计数**（不参与）。
  - **命中产出**：返回的 `CachedAnswer.result()` 与写入的 RagResult 字段逐一相等，`similarity` 值正确；stats 的 hits/recentSimilarities/maxHitSimilarity 更新。

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** lookup：enabled（disabled 实例直接 empty）→ history 空（否则 empty 不计数）→ 规范化文本/空白返 empty 不计数 → **锁外** embed（catch `DependencyFailure`→depFailures++/WARN(errorClass+requestId)→empty）→ 锁内：懒清理过期（evictionsTtl）；过滤同模型命名空间（`embeddingModel` 相等且向量维度一致）+ 作用域匹配（null 通配）→ 余弦最高分 ≥ threshold 的条目快照（拷贝引用出锁）→ 无则 realMisses++/empty → **锁外**哨兵：逐条 `versionCheck.test(citation.articleId(), citation.versionId())`，任一 false → 锁内按引用驱逐该条 + evictionsSentinel++ + realMisses++ + empty；`RuntimeException` → depFailures++/WARN/empty → 全真 → hits++、锁内刷新 lastAccess/hitCount、依次记录 recentSimilarities（≤50）与 maxHitSimilarity → `Optional.of(new CachedAnswer(entry.result, best))`。

- [ ] **Step 4: 测试通过 → 提交**：`git commit -m "feat(cache): lookup 相似度命中 + 知识版本哨兵复核驱逐"`

---

### Task 5: `RagResult.cacheHit` + `ComposedRagAdapter` 接线

**Files:**
- Modify: `src/main/java/com/itticket/consultation/adapter/RagResult.java`（加第 14 组件 `CacheHitInfo cacheHit`，末位；既有 12/13 参便捷构造保留并委托 `cacheHit=null`；`withLatency`/`withRetrievedVersionIds`/`withTicketDraft` 透传新组件；新增 `withCacheHit(double similarity, String scope)`）
- Modify: `src/main/java/com/itticket/consultation/adapter/ComposedRagAdapter.java`（构造器 + 两个插点）
- Modify: `src/main/java/com/itticket/consultation/config/AiCompositionConfig.java`（ragAdapter bean 加 cache 参数；新增 cache 构建——**完整 fail-fast 校验放 Task 8**，本任务先做基本接线）
- Modify 测试调用点（全部传 `SemanticAnswerCache.disabled()`）：`src/test/.../adapter/ComposedModelProtocolTest.java:52`、`GuardedRagDeadlineTest.java:66`、`RagCompositionHttpTest.java:102`（assemble()）、`ToolIntentBypassTest.java:50/127/152`
- Test: `src/test/java/com/itticket/consultation/adapter/ComposedRagCacheTest.java`（新建，Mockito 惯例参照 `ToolIntentBypassTest`）

**Interfaces:**
- Consumes: Task 3/4 `SemanticAnswerCache`、`CachedAnswer`、`CacheHitInfo`。
- Produces: `new ComposedRagAdapter(RequestClassifier, KnowledgeRetriever, RetrievalPolicy, AnswerGenerator, boolean toolBypassEnabled, SemanticAnswerCache cache)`；`RagResult.cacheHit()`（null 或 CacheHitInfo）；命中路径返回带真实测量 latency 的结果。

- [ ] **Step 1: 写失败测试**（`ComposedRagCacheTest`：Mockito mock classifier/retriever/policy/generator；`RetrievalResult` 构造按 `ToolIntentBypassTest` 现有桩）：
  - **未落缓存**：cache=disabled()，OFFICE_IT+NO_TOOL 成功作答 → 行为与现状一致且 write 未增条目。
  - **先 miss 后 hit**：可注入 fake `EmbeddingClient` 的 enabled `SemanticAnswerCache`（versionCheck 全 true）第一次 answer → retriever/generator 各调 1 次且条目已写（stats().entries()==1）；同问再 answer → retriever/generator **零调用**，answerText 与 citations 逐一相等，`result.cacheHit().similarity()==1.0`，latency 为非负真实值。
  - **域拒答不进缓存**：classifier 返回 HIGH_RISK → refuse 结果；且**预先已 hand-seed** 一条语义相同题目（借 write 写入正常作答）；classifier 再返回同问题 HIGH_RISK → refute：认拒答，stats().hits==0——闸门先于缓存。
  - **工具旁路双跳过**：`toolBypassEnabled=true` 且 verdict.tool()=="query_my_tickets" → 不 lookup（无 hit 可见）、不 write（entries==0），chain 走通。
  - **嵌入失败**：embed stub 抛 `DependencyFailure.invalid()` → 实时链路照常返回生成 SUCCESS，无降级 status；stats().depFailures==1。
  - **写门槛生效**：UNCERTAIN→CLARIFY 结果不写（entries==0）；降级 RagStatus 不写。
  - **成功后写透传**：含 ticketDraft 成功结果 write 进缓存原样保留；hit 返回结果无 draft（`write` 条件含 citations 非空——若 ticketDraft 成功结果 citations 为空（工具实据），不写由门槛保护，断言之）。

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现**：
  - `RagResult` 组件追加（细化 3）。
  - `ComposedRagAdapter.answer`：`restrict` 判定后新增 `boolean toolBypass = toolBypassEnabled && !RequestVerdict.NO_TOOL.equals(verdict.tool());`（从原检索后的计算处**上提**，检索后直接复用，行为不变）；紧随其后：
    ```
    if (!toolBypass) {
        long startedAt = System.nanoTime();
        CachedAnswer hit = cache.lookup(query, context).orElse(null);
        if (hit != null) {
            context.audit().recordRetrievedVersions(hit.result().retrievedVersionIds());
            return hit.result().withLatency(ms elapsed).withCacheHit(hit.similarity(), scopeOf(query));
        }
    }
    ```
    `scopeOf(query)` 私有静态：`category/assetId` 都 null → null，否则 `"category=<v>;asset=<v>"`。
  - 出口：`RagResult finalResult = ticketDraft==null ? answered : answered.withTicketDraft(...)` 后 `if (!toolBypass) cache.write(query, finalResult); return finalResult;`
  - `AiCompositionConfig.ragAdapter(...)` 加第 6 参 `SemanticAnswerCache cache` 并传入；本任务先在 config 中以 `SemanticAnswerCache.disabled()` 填充（Task 8 换成真构建）。
  - 5 处测试调用点补 `SemanticAnswerCache.disabled()`。
  - 类级 javadoc 更新：七步编排前插"语义缓存（默认关）"一步，注明安全裁决先序与检索侧 HIGH_RISK 收紧跳过之取舍（spec 已裁决接受）。

- [ ] **Step 4: 跑新测试 + 存量 `mvn -q test -Dtest='*Rag*'` 全绿**

- [ ] **Step 5: 提交**：`git commit -m "feat(cache): ComposedRagAdapter 接入语义缓存(闸门保序/旁路跳过/门控写入)"`

---

### Task 6: 命中审计落 `persistAiMessage` metadata

**Files:**
- Modify: `src/main/java/com/itticket/consultation/service/AiConsultationService.java`（`persistAiMessage` 签名加 `RagResult result` 参数，`doChat` 调用处传入）
- Test: `src/test/java/com/itticket/consultation/service/AiConsultationPolicyTest.java`（追加用例）

**Interfaces:**
- Consumes: Task 5 `RagResult.cacheHit()`；存量 `Json.write`。

- [ ] **Step 1: 写失败测试**（Fixture 惯例）：
  - `fixture.rag` 返回带 `.withCacheHit(0.97, "category=C_NET")` 的成功 RagResult → `messages.appendAiMessage` 捕获 metadata JSON：含 `"cacheHit":true`、`"cacheSimilarity":0.97`、`"cacheScope":"category=C_NET"`，且 schemaVersion 仍为 1。
  - 无 cacheHit 的普通结果 → metadata **不含** `cacheHit` 键（历史留白，避免把"未参与"伪装成"未命中"）。
  - `result == null`（answerEnabled=false 语义）路径不炸。

- [ ] **Step 2: 跑测试确认失败/编译错误**

- [ ] **Step 3: 实现**：`persistAiMessage(sessionId, idempotencyKey, interactionId, RagResult result, Verdict verdict)`，`doChat` 中 `persistAiMessage(sessionId, idempotencyKey, interactionId, result, verdict)`；metadata 组装在 `generalAnswer` 之后追加：`if (result != null && result.cacheHit() != null) { metadata.put("cacheHit", true); metadata.put("cacheSimilarity", result.cacheHit().similarity()); metadata.put("cacheScope", result.cacheHit().scope()); }`。javadoc 注明 schemaVersion=1 追加字段（spec 审计节）。`ai_interaction` 不动表结构。

- [ ] **Step 4: 测试通过（含存量用例不回归）→ 提交**：`git commit -m "feat(cache): 命中元数据(cacheHit/cacheSimilarity/cacheScope)入消息审计"`

---

### Task 7: 指标导出端点（只读/管理员）

**Files:**
- Create: `src/main/java/com/itticket/consultation/dto/AiCacheStatsResponse.java`（record，字段同 `CacheStats`）
- Modify: `src/main/java/com/itticket/consultation/service/AuthzService.java`（加 `requirePlatformAdmin(CurrentUser user)`）
- Create: `src/main/java/com/itticket/consultation/controller/AiCacheAdminController.java`
- Test: `src/test/java/com/itticket/consultation/controller/AiCacheAdminControllerTest.java`（直接 new + Mockito，不启动 Spring，跟随 `AuthzService` 既有 require* 方法风格）

**Interfaces:**
- Consumes: Task 3/4 `SemanticAnswerCache.stats()`；`ApiCode.FORBIDDEN("forbidden",403)`；`ApiException(ApiCode, String)` 既有构造。
- Produces: `GET /api/v1/consultations/ai/cache/export` → `ApiEnvelope<AiCacheStatsResponse>`；`AuthzService.requirePlatformAdmin(CurrentUser)`（非 PLATFORM_ADMIN → `ApiException(ApiCode.FORBIDDEN, ...)`）。

- [ ] **Step 1: 写失败测试**：真实 `SemanticAnswerCache`（fake embed）做几次 hit/miss → 控制器导出：管理员（CurrentUser role=PLATFORM_ADMIN）→ code=0 载荷各计数正确、hitRate=hits/(hits+realMisses)；员工 → `ApiException`（FORBIDDEN）。`AuthzService.requirePlatformAdmin` 纯直测：EMPLOYEE 抛 / PLATFORM_ADMIN 过。

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现**：控制器 `@Validated @RestController @RequestMapping("/api/v1/consultations/ai/cache")` + `@RequiredArgsConstructor`，方法 `export()`：`authzService.requirePlatformAdmin(authzService.currentUser())` → `ok(cache.stats())`（`CacheStats` 直接作为响应 record 或经 `AiCacheStatsResponse` 映射——二选一，选**直接暴露 CacheStats**into envelope、不另造 DTO 冗余字段（YAGNI）；如 Jackson 对 record 无碍即删 `AiCacheStatsResponse.java`）。

- [ ] **Step 4: 测试通过 → 提交**：`git commit -m "feat(cache): 只读缓存指标导出端点(经济條=PLATFORM_ADMIN)"`（修正错字后用）`feat(cache): 只读缓存指标导出端点(仅平台管理员)`

---

### Task 8: 装配 fail-fast + `AiCompositionConfig` 真实构建

**Files:**
- Modify: `src/main/java/com/itticket/consultation/config/AiCompositionConfig.java`（新增 `semanticAnswerCache` bean；`ragAdapter` 注入该 bean）
- Test: `src/test/java/com/itticket/consultation/config/AiCacheAssemblyTest.java`（直接 `new AiCompositionConfig()` 调 bean 方法，不启动 Spring）

**Interfaces:**
- Consumes: Task 1-5 全部。
- Produces: `@Bean public SemanticAnswerCache semanticAnswerCache(ConsultationProperties properties, DependencyHttpClient http, KnowledgeQueryService knowledge)`。

- [ ] **Step 1: 写失败测试**：
  - enabled=false（默认）→ 返回 disabled 实例，`lookup(...)` 恒 empty。
  - enabled=true 且 embeddingModel 空 → `IllegalArgumentException`（信息含配置键名）。
  - enabled=true 且 threshold=0.5 → `IllegalArgumentException`。
  - enabled=true 且 model/baseUrl 均给 → 返回 enabled 实例（`stats().entries()==0`）；`embeddingBaseUrl` 为空回退 `ai.baseUrl` 的分支被覆盖。
  - enabled=true 且 base-url 与 embedding-base-url 均空 → `IllegalArgumentException`。

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现** bean：`!enabled → disabled()`；校验顺序 model→threshold∈[0.90,1.0]→base（embeddingBaseUrl 空回退 ai.baseUrl，仍空抛）→ `new OpenAiCompatibleEmbeddingClient(base, model, ai.apiKey, cache.embeddingTimeoutMs, http)` → `new SemanticAnswerCache(cacheConfig, embeddings, knowledge::isPublishedCurrentVersion, Clock.systemUTC())`。`ragAdapter` bean 改注入此 bean。

- [ ] **Step 4: 测试通过 → 提交**：`git commit -m "feat(cache): 装配期构建与 fail-fast(缺嵌入模型启动失败)"`

---

### Task 9: HTTP 级集成 `SemanticCacheHttpTest`

**Files:**
- Test: `src/test/java/com/itticket/consultation/adapter/SemanticCacheHttpTest.java`（骨架全盘照抄 `RagCompositionHttpTest`：`RagServiceKnowledgeRetriever` + `/chat/completions` stub + mock `KnowledgeQueryService` + `GuardedRagClient`；新增 `/embeddings` stub 与 enabled cache 下的真装配——`AiCompositionConfig` 产物或手工等价装配）

**Interfaces:** Consumes 全部前序产物；无新生产物。

- [ ] **Step 1: 写测试（场景即 spec 验收 2 的全部条目）**：
  1. 未命中→生成→写→**同义改写命中**：先问"开会别人听不到我"→ 正常答复；再问"会议时对方听不清我说话"（embed stub 对两问返回同向量）→ 命中：`/chat/completions` 的**生成分支**（请求体含 material）零新增调用，检索端点零新增调用，`/embeddings` 每次 lookup+write 各 1 次；结果 citations 与首次逐一相等。
  2. **哨兵失效驱逐**：翻转 knowledge mock `isPublishedCurrentVersion` 为 false → 同义问题再问 → 真实时链路（retrieval+generation 各再起 1 次）→ 且之后 stats().entries() 减 1（驱逐）。
  3. **拒答/CLARIFY 不写**：OFF_TOPIC 与 UNCERTAIN 问法 → 条目数不变。
  4. **嵌入故障=依赖失败**：`/embeddings` 改 500 → 同义问题 → 实时回答照常成功，`stats().depFailures>=1` 且 hits 不变。
  5. **命中结果可过输出守卫**：`AiAnswerGuard.evaluate(hitResult, config.getAi(), (a,v)->true)` → ANSWER（+citations 非空）。
  6. 命中延迟断言（软验收）：< 300ms（含嵌入往返，本地 stub 环境下断言成立）。

- [ ] **Step 2: 跑测试确认失败/修正桩**

- [ ] **Step 3: 实现只允许改测试桩与装配参数，不改主代码**（若主代码有缺陷，修主代码并回补 Task 3-5 对应单测）

- [ ] **Step 4: 提交**：`git commit -m "test(cache): 语义缓存端到端HTTP场景(命中/驱逐/拒答不写/依赖失败)"`

---

### Task 10: 全量回归、部署说明与收尾

**Files:**
- Modify: `release/` 或 `docs/superpowers/specs/2026-11-04-semantic-answer-cache-design.md`（补"部署说明"一节——若 spec 已有等价段落则只核对）
- 无代码

- [ ] **Step 1**: `mvn -q test`（it-ticket-cloud/consultation-service 全量）→ 全绿，记录测试总数（基线 206，只增不减）。
- [ ] **Step 2**: `git status` 核对提交只含本任务文件（未混入 `deploy/README.md`/`wiki_generator.py`/release 未跟踪件）。
- [ ] **Step 3**: spec 补部署说明四点：默认关闭/开启前置（embedding-model 必填 + base-url 同族 `/embeddings` 实施期验证结论）/命中跳过检索侧 HIGH_RISK 收紧的取舍/未来按角色裁剪检索时缓存 key 必须加 scope 维度。
- [ ] **Step 4**: 收尾提交：`git commit -m "docs(cache): 语义缓存部署说明(开关/前置/取舍/演进注意事项)"`

---

## Self-Review 记录

- Spec 覆盖：配置(1/8)、嵌入客户端(2)、write 规则+存储(3)、lookup+哨兵+三态计数(4)、编排接点与调用点迁移(5)、审计 metadata(6)、导出端点(7)、fail-fast(8)、验收 2 全场景(9)、验收 3/4(1/5/8/10) 均有任务承接；验收 5（指标基线/压测报告）属运行期产物，不在代码计划内——已在 spec 标注由 Task 7 端点供数。
- 类型一致：`CachedAnswer(result,similarity)`、`CacheHitInfo(similarity,scope)`、`withCacheHit(double,String)`、`stats()` 全链一致；`requirePlatformAdmin(CurrentUser)` 与存量 require* 同形。
- 有意偏差 3 条已列头部，其余与 spec 逐条对齐。
