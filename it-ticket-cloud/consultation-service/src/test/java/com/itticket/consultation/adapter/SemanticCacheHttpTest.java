package com.itticket.consultation.adapter;

import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.*;
import com.itticket.consultation.adapter.cache.CacheStats;
import com.itticket.consultation.adapter.cache.SemanticAnswerCache;
import com.itticket.consultation.adapter.generation.*;
import com.itticket.consultation.adapter.model.*;
import com.itticket.consultation.adapter.policy.*;
import com.itticket.consultation.adapter.retrieval.*;
import com.itticket.consultation.config.AiCompositionConfig;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.enums.*;
import com.itticket.consultation.service.AiAnswerGuard;
import com.itticket.consultation.service.KnowledgeQueryService;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 语义缓存端到端 HTTP 场景:真实装配(AiCompositionConfig.semanticAnswerCache + OpenAiCompatibleEmbeddingClient
 * 指向本地 /embeddings stub)。验收 spec 场景:同义改写命中、哨兵失效驱逐、拒答/澄清不写、
 * 嵌入依赖失败按依赖失败计数并穿透实时链路、命中结果可过输出守卫。
 */
class SemanticCacheHttpTest {
    private final ObjectMapper json = new ObjectMapper();
    private HttpServer server;
    private ConsultationProperties config;
    private KnowledgeQueryService knowledge;
    private ObjectNode envelope;
    private ObjectNode modelReply;
    private String classification;
    private int embeddingStatus;
    private final List<JsonNode> ragRequests = new CopyOnWriteArrayList<>();
    private final List<JsonNode> generationInputs = new CopyOnWriteArrayList<>();
    private final List<JsonNode> classificationInputs = new CopyOnWriteArrayList<>();
    private final List<JsonNode> embeddingRequests = new CopyOnWriteArrayList<>();
    private SemanticAnswerCache cache;
    private GuardedRagClient client;

    @BeforeEach void start() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        envelope = json.createObjectNode().put("code", 0);
        ObjectNode data = envelope.putObject("data");
        data.put("domain", "OFFICE_IT").put("suggestedReplyType", "ANSWER")
                .putNull("suggestedRefusalReason").put("topScore", new BigDecimal("0.7503"))
                .put("reliable", true).put("publishedOnly", true);
        data.putArray("items").add(item("C1", "A1", "V1", new BigDecimal("0.7503"), "检查会议应用的输入设备。"));
        modelReply = json.createObjectNode().put("replyType", "ANSWER").put("answerText", "检查输入设备。")
                .put("confidence", new BigDecimal("0.9100")).put("knowledgeConflict", false).put("offTopic", false);
        modelReply.putArray("usedVersionIds").add("V1");
        classification = "OFFICE_IT";
        embeddingStatus = 200;
        server.createContext("/api/v1/rag/retrievals", exchange -> {
            ragRequests.add(json.readTree(exchange.getRequestBody()));
            respond(exchange, json.writeValueAsBytes(envelope), 200);
        });
        server.createContext("/chat/completions", exchange -> {
            JsonNode request = json.readTree(exchange.getRequestBody());
            JsonNode input = json.readTree(request.path("messages").get(1).path("content").textValue());
            byte[] response;
            if (input.has("material")) {
                // 生成调用已切换 completeStream:SSE 帧 delta.content 返回整段 modelReply。
                generationInputs.add(input);
                ObjectNode frame = json.createObjectNode();
                ObjectNode choice = frame.putArray("choices").addObject();
                choice.putObject("delta").put("content", modelReply.toString());
                choice.put("finish_reason", "stop");
                exchange.getResponseHeaders().add("Content-Type", "text/event-stream; charset=utf-8");
                response = ("data: " + frame + "\n\n" + "data: [DONE]\n\n").getBytes(StandardCharsets.UTF_8);
            } else {
                // 分类调用仍走非流式 complete(),保持单 JSON 形状。
                classificationInputs.add(input);
                JsonNode content = json.createObjectNode().put("decision", classification);
                response = json.writeValueAsBytes(Map.of("choices", List.of(Map.of("finish_reason", "stop",
                        "message", Map.of("content", content.toString(), "reasoning_content", "never expose")))));
            }
            respond(exchange, response, 200);
        });
        server.createContext("/embeddings", exchange -> {
            embeddingRequests.add(json.readTree(exchange.getRequestBody()));
            ObjectNode body = json.createObjectNode().put("model", "bge-m3");
            ObjectNode datum = body.putArray("data").addObject();
            datum.put("index", 0).putArray("embedding").add(0.6).add(0.8);
            respond(exchange, json.writeValueAsBytes(body), embeddingStatus);
        });
        server.start();
        config = new ConsultationProperties();
        config.getAi().setBaseUrl(baseUrl());
        config.getAi().setRagBaseUrl(baseUrl());
        config.getAi().setApiKey("model-only-test-token");
        config.getAi().setRequestTimeoutMs(3000);
        config.getAi().getCache().setEnabled(true);
        config.getAi().getCache().setEmbeddingModel("bge-m3"); // embeddingBaseUrl 留空 → 装配回退 ai.baseUrl
        knowledge = mock(KnowledgeQueryService.class);
        when(knowledge.isPublishedCurrentVersion(anyString(), anyString())).thenReturn(true);
        assemble();
    }

    @AfterEach void stop() {
        if (client != null) client.shutdown();
        server.stop(0);
    }

    private void assemble() {
        if (client != null) client.shutdown();
        DependencyHttpClient http = new DependencyHttpClient();
        OpenAiCompatibleModelClient model = new OpenAiCompatibleModelClient(config, http);
        cache = new AiCompositionConfig().semanticAnswerCache(config, http, knowledge);
        client = new GuardedRagClient(new ComposedRagAdapter(new SemanticRequestClassifier(model),
                new RagServiceKnowledgeRetriever(config, http),
                new RetrievalPolicy(knowledge, Set.of("SAME_ROOT_CAUSE", "RELATED", "PROCESS_APPLIES"),
                        new BigDecimal("0.10"), 2),
                new OpenAiCompatibleAnswerGenerator(model, config, null), false, cache), config);
    }

    private RagResult ask(String question, String requestId) {
        return client.answer(new RagQuery("S1", question, "C_NET", "ASSET1", 5,
                new RagCaller("U_EMP01", "EMPLOYEE")), requestId);
    }

    private ObjectNode item(String chunk, String article, String version, BigDecimal score, String content) {
        ObjectNode node = json.createObjectNode().put("chunkId", chunk).put("articleId", article).put("versionId", version)
                .put("indexVersion", version).put("title", "会议音频排障").put("snippet", "摘要")
                .put("content", content).put("categoryId", "C_NET");
        if (score == null) node.putNull("score"); else node.put("score", score);
        return node;
    }

    private void respond(com.sun.net.httpserver.HttpExchange exchange, byte[] body, int status)
            throws java.io.IOException {
        exchange.sendResponseHeaders(status, body.length);
        exchange.getResponseBody().write(body);
        exchange.close();
    }

    private String baseUrl() { return "http://127.0.0.1:" + server.getAddress().getPort(); }

    @Test
    void synonymRewriteHitsCacheAndSkipsRetrievalAndGeneration() {
        RagResult first = ask("开会别人听不到我", "request-1");
        assertThat(first.cacheHit()).isNull();
        assertThat(first.replyType()).isEqualTo(AiReplyType.ANSWER);
        int retrievals = ragRequests.size();
        int generations = generationInputs.size();
        assertThat(embeddingRequests.size()).isEqualTo(2); // 未命中 lookup 1 次 + 生成后 write 1 次

        RagResult hit = ask("会议时对方听不清我说话", "request-2");

        assertThat(hit.cacheHit()).isNotNull();
        assertThat(hit.cacheHit().similarity()).isCloseTo(1.0, org.assertj.core.data.Offset.offset(1e-6));
        assertThat(hit.citations()).isEqualTo(first.citations());
        assertThat(hit.answerText()).isEqualTo(first.answerText());
        assertThat(ragRequests.size()).isEqualTo(retrievals);      // 检索零新增
        assertThat(generationInputs.size()).isEqualTo(generations); // 生成零新增
        assertThat(classificationInputs.size()).isEqualTo(2);      // 域判定每问必做(安全裁决不做缓存)
        assertThat(embeddingRequests.size()).isEqualTo(3);         // 命中轮仅 lookup 的 1 次嵌入
        CacheStats stats = cache.stats();
        assertThat(stats.hits()).isEqualTo(1L);
        assertThat(stats.realMisses()).isEqualTo(1L);
        assertThat(stats.depFailures()).isZero();
        assertThat(stats.entries()).isEqualTo(1L);
        // spec 软验收目标 <300ms(空闲本机实测~几十ms);上限放宽到 1s 仅防共享执行器抖动
        assertThat(hit.latencyMs()).isLessThan(1000);
    }

    @Test
    void sentinelInvalidationEvictsStaleEntryThenRefillsAfterRepublish() {
        ask("开会别人听不到我", "request-1");
        assertThat(cache.stats().entries()).isEqualTo(1L);

        // 知识版本翻转失效:命中条目被哨兵驱逐,按未命中穿透,StaleKnowledge 拒答(无旧答案出库)
        when(knowledge.isPublishedCurrentVersion(anyString(), anyString())).thenReturn(false);
        RagResult stale = ask("会议时对方听不清我说话", "request-2");
        assertThat(stale.cacheHit()).isNull();
        assertThat(stale.replyType()).isEqualTo(AiReplyType.REFUSE);
        assertThat(stale.refusalReason()).isEqualTo(AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
        assertThat(ragRequests.size()).isEqualTo(2); // 真实时链路重查检索
        CacheStats staleStats = cache.stats();
        assertThat(staleStats.evictionsSentinel()).isEqualTo(1L);
        assertThat(staleStats.entries()).isZero();
        assertThat(staleStats.hits()).isZero();
        assertThat(staleStats.realMisses()).isEqualTo(2L); // 首问未命中 + 哨兵驱逐穿透各计一次

        // 知识重新发布后:同问恢复实时作答并重建缓存
        when(knowledge.isPublishedCurrentVersion(anyString(), anyString())).thenReturn(true);
        RagResult fresh = ask("开会别人听不到我", "request-3");
        assertThat(fresh.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(fresh.cacheHit()).isNull();
        assertThat(generationInputs.size()).isEqualTo(2);
        assertThat(cache.stats().entries()).isEqualTo(1L);
    }

    @Test
    void refusalsAndClarificationsAreNeverCached() {
        classification = "OFF_TOPIC";
        RagResult refused = ask("帮我写毕业论文", "request-1");
        assertThat(refused.replyType()).isEqualTo(AiReplyType.REFUSE);
        classification = "UNCERTAIN";
        RagResult clarified = ask("麻烦处理一下", "request-2");
        assertThat(clarified.replyType()).isEqualTo(AiReplyType.CLARIFY);

        assertThat(cache.stats().entries()).isZero();
        assertThat(embeddingRequests).isEmpty(); // 域门禁在缓存之前,离题/追问连嵌入都不发生
        assertThat(ragRequests).isEmpty();
    }

    @Test
    void embeddingOutageFallsThroughToRealtimeWithDependencyCounter() {
        ask("开会别人听不到我", "request-1");
        embeddingStatus = 500;

        RagResult answered = ask("会议时对方听不清我说话", "request-2");

        assertThat(answered.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(answered.cacheHit()).isNull();
        assertThat(ragRequests.size()).isEqualTo(2);
        assertThat(generationInputs.size()).isEqualTo(2);
        CacheStats stats = cache.stats();
        assertThat(stats.depFailures()).isEqualTo(2L); // lookup+write 各失败一次
        assertThat(stats.hits()).isZero();
        assertThat(stats.entries()).isEqualTo(1L); // 首问条目不受嵌入故障影响
    }

    @Test
    void hitResultPassesOutputGuard() {
        RagResult first = ask("开会别人听不到我", "request-1");
        RagResult hit = ask("会议时对方听不清我说话", "request-2");

        AiAnswerGuard.Verdict verdict = AiAnswerGuard.evaluate(hit, config.getAi(), (a, v) -> true);
        assertThat(verdict.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(verdict.citations()).isNotEmpty();
        assertThat(verdict.citations()).isEqualTo(first.citations());
        assertThat(verdict.suggestTransfer()).isFalse();
    }
}
