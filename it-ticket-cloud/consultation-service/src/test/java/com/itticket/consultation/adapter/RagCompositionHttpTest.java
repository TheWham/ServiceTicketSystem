package com.itticket.consultation.adapter;

import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.*;
import com.itticket.consultation.adapter.generation.*;
import com.itticket.consultation.adapter.model.*;
import com.itticket.consultation.adapter.policy.*;
import com.itticket.consultation.adapter.retrieval.*;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.enums.*;
import com.itticket.consultation.service.*;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import com.itticket.consultation.config.AiCompositionConfig;
import com.itticket.consultation.dto.KnowledgeHit;
import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class RagCompositionHttpTest {
    private final ObjectMapper json = new ObjectMapper();
    private HttpServer server;
    private ConsultationProperties config;
    private KnowledgeQueryService knowledge;
    private ObjectNode envelope;
    private ObjectNode modelReply;
    private String classification;
    private int ragStatus;
    private int generationStatus;
    private int subsequentClassificationStatus;
    private long ragDelay;
    private long modelDelay;
    private final List<JsonNode> ragRequests = new CopyOnWriteArrayList<>();
    private final List<JsonNode> generationInputs = new CopyOnWriteArrayList<>();
    private final List<JsonNode> classificationInputs = new CopyOnWriteArrayList<>();
    private final List<Map<String, String>> ragHeaders = new CopyOnWriteArrayList<>();
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
        classification = "OFFICE_IT"; ragStatus = 200; generationStatus = 200;
        subsequentClassificationStatus = 200;
        server.createContext("/api/v1/rag/retrievals", exchange -> {
            ragRequests.add(json.readTree(exchange.getRequestBody()));
            Map<String, String> headers = new HashMap<>();
            for (String header : List.of("X-User-Id", "X-User-Role", "X-Request-Id", "Authorization"))
                headers.put(header, exchange.getRequestHeaders().getFirst(header));
            ragHeaders.add(headers);
            pause(ragDelay);
            byte[] response = json.writeValueAsBytes(envelope);
            exchange.sendResponseHeaders(ragStatus, response.length);
            exchange.getResponseBody().write(response); exchange.close();
        });
        server.createContext("/chat/completions", exchange -> {
            JsonNode request = json.readTree(exchange.getRequestBody());
            JsonNode input = json.readTree(request.path("messages").get(1).path("content").textValue());
            JsonNode content;
            int responseStatus;
            if (input.has("material")) {
                generationInputs.add(input); pause(modelDelay); content = modelReply;
                responseStatus = generationStatus;
            } else {
                classificationInputs.add(input);
                content = json.createObjectNode().put("decision", classification);
                responseStatus = classificationInputs.size() == 1 ? 200 : subsequentClassificationStatus;
            }
            byte[] response = json.writeValueAsBytes(Map.of("choices", List.of(Map.of("finish_reason", "stop",
                    "message", Map.of("content", content.toString(), "reasoning_content", "never expose")))));
            exchange.sendResponseHeaders(responseStatus, response.length);
            exchange.getResponseBody().write(response); exchange.close();
        });
        server.start();
        config = new ConsultationProperties();
        config.getAi().setBaseUrl(baseUrl()); config.getAi().setRagBaseUrl(baseUrl());
        config.getAi().setApiKey("model-only-test-token"); config.getAi().setRequestTimeoutMs(3000);
        knowledge = mock(KnowledgeQueryService.class);
        when(knowledge.isPublishedCurrentVersion(anyString(), anyString())).thenReturn(true);
        assemble();
    }
    @AfterEach void stop() { if (client != null) client.shutdown(); server.stop(0); }
    private void assemble() {
        if (client != null) client.shutdown();
        var http = new DependencyHttpClient();
        var model = new OpenAiCompatibleModelClient(config, http);
        client = new GuardedRagClient(new ComposedRagAdapter(new SemanticOfficeDomainClassifier(model),
                new RagServiceKnowledgeRetriever(config, http), new RetrievalPolicy(knowledge),
                new OpenAiCompatibleAnswerGenerator(model, config)), config);
    }
    private RagResult ask() {
        return client.answer(new RagQuery("S1", "开会别人听不到我", "C_NET", "ASSET1", 5,
                new RagCaller("U_EMP01", "EMPLOYEE")), "request-1");
    }
    private ObjectNode data() { return (ObjectNode) envelope.get("data"); }
    private ArrayNode items() { return (ArrayNode) data().get("items"); }
    private ObjectNode item(String chunk, String article, String version, BigDecimal score, String content) {
        ObjectNode node = json.createObjectNode().put("chunkId", chunk).put("articleId", article).put("versionId", version)
                .put("indexVersion", version).put("title", "会议音频排障").put("snippet", "不应复制未送入模型的摘要")
                .put("content", content).put("categoryId", "C_NET");
        if (score == null) node.putNull("score"); else node.put("score", score);
        return node;
    }
    private String baseUrl() { return "http://127.0.0.1:" + server.getAddress().getPort(); }
    private static void pause(long delay) {
        try { if (delay > 0) Thread.sleep(delay); }
        catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
    }

    @Test void remoteScoresArePreservedAndModelConfidenceIsIndependent() {
        RagResult result = ask();
        assertThat(result.status()).isEqualTo(RagStatus.SUCCESS);
        assertThat(result.confidence()).isEqualByComparingTo("0.9100");
        assertThat(result.citations()).singleElement().satisfies(c -> {
            assertThat(c.score()).isEqualByComparingTo("0.7503");
            assertThat(c.articleId()).isEqualTo("A1");
            assertThat(c.snippet()).isEqualTo("检查会议应用的输入设备。");
        });
        assertThat(ragRequests).singleElement().satisfies(r -> {
            assertThat(r.size()).isEqualTo(3);
            assertThat(r.path("categoryId").asText()).isEqualTo("C_NET");
            assertThat(r.path("topK").asInt()).isEqualTo(5);
        });
        assertThat(ragHeaders.get(0)).containsEntry("X-User-Id", "U_EMP01")
                .containsEntry("X-User-Role", "EMPLOYEE").containsEntry("X-Request-Id", "request-1");
        assertThat(ragHeaders.get(0).get("Authorization")).isNull();
        assertThat(generationInputs.get(0).path("assetId").textValue()).isEqualTo("ASSET1");
        verify(knowledge, never()).retrieve(any(), any(), anyInt());
    }
    @Test void nullBm25AndLowerScoresAreNotCreditedByTheReliableTopHit() {
        items().add(item("BM25", "A2", "V2", null, "仅全文命中"));
        items().add(item("LOW", "A3", "V3", new BigDecimal("0.2"), "完全无关内容"));
        assertThat(ask().citations()).hasSize(1);
        assertThat(generationInputs.get(0).path("material")).hasSize(1);
        assertThat(generationInputs.get(0).toString()).doesNotContain("仅全文命中", "完全无关内容");
    }
    @Test void duplicatesChooseStableChunkAndBoundedContentSuppliesTheSnippet() {
        items().removeAll();
        items().add(item("Z", "A1", "V1", new BigDecimal("0.7503"), "错误的同分后写正文"));
        String body = "实际传入正文".repeat(300);
        items().add(item("A", "A1", "V1", new BigDecimal("0.7503"), body));
        RagResult result = ask();
        JsonNode material = generationInputs.get(0).path("material").get(0);
        assertThat(material.path("content").textValue()).hasSize(1200).isEqualTo(body.substring(0, 1200));
        assertThat(result.citations().get(0).snippet()).isEqualTo(body.substring(0, 1000));
        assertThat(material.path("content").textValue()).contains(result.citations().get(0).snippet());
    }
    @Test void sameVersionWithDifferentArticleIsRejectedBeforeGeneration() {
        items().add(item("OTHER", "A9", "V1", new BigDecimal("0.7503"), "矛盾归属"));
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
        assertThat(generationInputs).isEmpty();
    }
    @Test void sameChunkWithConflictingMetadataIsRejected() {
        items().add(item("C1", "A1", "V1", new BigDecimal("0.7503"), "不同正文"));
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
    }
    @Test void lowConfidenceRetrievalCannotBeOverriddenByConfidentGeneration() {
        data().put("reliable", false).put("suggestedReplyType", "REFUSE")
                .put("suggestedRefusalReason", "LOW_CONFIDENCE");
        RagResult result = ask();
        assertThat(result.refusalReason()).isEqualTo(AiRefusalReason.LOW_CONFIDENCE);
        assertThat(generationInputs).isEmpty();
        assertThat(AiAnswerGuard.evaluate(result, config.getAi(), (a, v) -> true).refusalReason())
                .isEqualTo(AiRefusalReason.LOW_CONFIDENCE);
    }
    @Test void normalEmptyRetrievalGeneratesGeneralAnswerWithServiceDisclosure() {
        items().removeAll(); data().put("reliable", false).put("topScore", 0);
        modelReply.putArray("usedVersionIds");
        RagResult result = ask();
        assertThat(result.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(result.generalAnswer()).isTrue();
        assertThat(result.citations()).isEmpty();
        assertThat(result.answerText()).contains("无知识库依据");
        assertThat(generationInputs.get(0).path("material")).isEmpty();
    }
    @Test void irrelevantRetrievalDoesNotLeakKnowledgeIntoGeneralGeneration() {
        data().put("reliable", false).put("topScore", new BigDecimal("0.2"));
        ((ObjectNode) items().get(0)).put("score", new BigDecimal("0.2"));
        modelReply.putArray("usedVersionIds");
        assertThat(ask().generalAnswer()).isTrue();
        assertThat(generationInputs.get(0).path("material")).isEmpty();
        verify(knowledge, never()).isPublishedCurrentVersion(anyString(), anyString());
    }
    @Test void legitimateBm25OnlyBatchIsAcceptedButProducesNoCitations() {
        data().put("reliable", false).put("topScore", 0);
        ((ObjectNode) items().get(0)).putNull("score"); modelReply.putArray("usedVersionIds");
        assertThat(ask().replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(generationInputs.get(0).path("material")).isEmpty();
    }
    @Test void reliableWithoutNumericEvidenceIsNotGeneralAnswer() {
        items().removeAll(); data().put("topScore", 0);
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
        assertThat(generationInputs).isEmpty();
    }
    @Test void dependencyFailureInsideHttp200IsNotEmptySuccess() {
        items().removeAll(); data().put("reliable", false).put("topScore", 0)
                .put("suggestedReplyType", "REFUSE").put("suggestedRefusalReason", "MODEL_UNAVAILABLE");
        assertThat(ask().status()).isEqualTo(RagStatus.UNAVAILABLE);
        assertThat(generationInputs).isEmpty();
        assertThat(ragRequests).hasSize(2);
        verify(knowledge, never()).retrieve(any(), any(), anyInt());
    }
    @Test void authenticationFailureIsNeverRetriedAndNeverFallsBackToMysql() {
        ragStatus = 401;
        RagResult result = ask();
        assertThat(result.status()).isEqualTo(RagStatus.UNAVAILABLE);
        assertThat(result.errorClass()).isEqualTo("AUTH_FAILED");
        assertThat(ragRequests).hasSize(1);
        assertThat(generationInputs).isEmpty();
        verify(knowledge, never()).retrieve(any(), any(), anyInt());
    }
    @Test void permanentHttpFailureIsNeverRetried() {
        ragStatus = 404;
        assertThat(ask().status()).isEqualTo(RagStatus.UNAVAILABLE);
        assertThat(ragRequests).hasSize(1);
    }
    @Test void nonzeroEnvelopeCodeIsUnavailableAndNotRetried() {
        envelope.put("code", 40001);
        assertThat(ask().errorClass()).isEqualTo("RAG_BUSINESS_ERROR");
        assertThat(ragRequests).hasSize(1);
    }
    @Test void malformedEnvelopeIsInvalidNotGenericGeneration() {
        envelope.remove("code");
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
        assertThat(generationInputs).isEmpty();
    }
    @Test void inconsistentDomainDecisionIsRejectedBeforeGeneration() {
        data().put("domain", "OFF_TOPIC");
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
        assertThat(generationInputs).isEmpty();
    }
    @Test void publishedOnlyFalseIsRejected() {
        data().put("publishedOnly", false);
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
    }
    @Test void indexVersionMustEqualKnowledgeVersion() {
        ((ObjectNode) items().get(0)).put("indexVersion", "V0");
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
        assertThat(generationInputs).isEmpty();
    }
    @Test void staleKnowledgeNeverEntersModelGeneration() {
        when(knowledge.isPublishedCurrentVersion("A1", "V1")).thenReturn(false);
        assertThat(ask().refusalReason()).isEqualTo(AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
        assertThat(generationInputs).isEmpty();
    }
    @Test void databaseFailureIsDependencyUnavailable() {
        when(knowledge.isPublishedCurrentVersion("A1", "V1")).thenThrow(new IllegalStateException("test"));
        assertThat(ask().errorClass()).isEqualTo("KNOWLEDGE_DATABASE_UNAVAILABLE");
        assertThat(generationInputs).isEmpty();
    }
    @Test void fabricatedVersionCannotEscapeEvenWhenEmptyRetrievalAllowsGeneralAnswer() {
        items().removeAll(); data().put("reliable", false).put("topScore", 0);
        modelReply.putArray("usedVersionIds").add("FORGED");
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
    }
    @Test void generationHttpFailurePreservesRetrievedVersionsForAudit() {
        generationStatus = 503;
        RagResult result = ask();
        assertThat(result.status()).isEqualTo(RagStatus.UNAVAILABLE);
        assertThat(result.errorClass()).isEqualTo("UNAVAILABLE");
        assertThat(result.retryableFailure()).isTrue();
        assertThat(result.retrievedVersionIds()).containsExactly("V1");
        assertThat(generationInputs).hasSize(2);
    }
    @Test void fabricatedVersionPreservesActualRetrievedVersionsForAudit() {
        modelReply.putArray("usedVersionIds").add("FORGED");
        RagResult result = ask();
        assertThat(result.status()).isEqualTo(RagStatus.INVALID_RESPONSE);
        assertThat(result.errorClass()).isEqualTo("INVALID_RESPONSE");
        assertThat(result.retryableFailure()).isFalse();
        assertThat(result.retrievedVersionIds()).containsExactly("V1");
        assertThat(result.citations()).isEmpty();
    }
    @Test void laterFailureBeforeRetrievalDoesNotEraseEarlierAttemptAudit() {
        generationStatus = 503;
        subsequentClassificationStatus = 401;
        RagResult result = ask();
        assertThat(result.status()).isEqualTo(RagStatus.UNAVAILABLE);
        assertThat(result.errorClass()).isEqualTo("AUTH_FAILED");
        assertThat(result.retryableFailure()).isFalse();
        assertThat(result.retrievedVersionIds()).containsExactly("V1");
        assertThat(result.citations()).isEmpty();
        assertThat(ragRequests).hasSize(1);
        assertThat(generationInputs).hasSize(1);
    }
    @Test void versionInvalidatedDuringGenerationIsRefusedByFinalGuard() {
        when(knowledge.isPublishedCurrentVersion("A1", "V1")).thenReturn(true, false);
        RagResult result = ask();
        assertThat(result.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(AiAnswerGuard.evaluate(result, config.getAi(), knowledge::isPublishedCurrentVersion).refusalReason())
                .isEqualTo(AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }
    @Test void noEvidenceDisclosureCannotPushAnswerPastProtocolLimit() {
        items().removeAll(); data().put("reliable", false).put("topScore", 0);
        modelReply.putArray("usedVersionIds"); modelReply.put("answerText", "a".repeat(12000));
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
    }
    @Test void retrievalAndGenerationShareTheOverallDeadline() {
        config.getAi().setRequestTimeoutMs(650); config.getAi().setRagRequestTimeoutMs(5000);
        ragDelay = 350; modelDelay = 450; assemble();
        long start = System.nanoTime();
        RagResult result = ask();
        assertThat(result.status()).isEqualTo(RagStatus.TIMEOUT);
        assertThat((System.nanoTime() - start) / 1_000_000).isLessThan(1100);
        assertThat(ragRequests).hasSize(1);
        assertThat(result.retrievedVersionIds()).containsExactly("V1");
    }
    @Test void modelDomainRefusalNeverCallsRetrieval() {
        classification = "HIGH_RISK";
        assertThat(ask().refusalReason()).isEqualTo(AiRefusalReason.HIGH_RISK_TOPIC);
        assertThat(ragRequests).isEmpty();
    }
    @Test void remoteUncertainDomainAsksForClarificationWithoutGeneration() {
        items().removeAll(); data().put("domain", "UNCERTAIN").put("suggestedReplyType", "CLARIFY")
                .put("reliable", false).put("topScore", 0);
        assertThat(ask().replyType()).isEqualTo(AiReplyType.CLARIFY);
        assertThat(generationInputs).isEmpty();
    }
    @ParameterizedTest
    @CsvSource({"local,local", "local,openai-compatible", "rag-service,local", "rag-service,openai-compatible"})
    void springAssemblyIndependentlyCombinesEachRetrieverAndGenerator(String retrievalProvider, String provider) {
        config.getAi().setRetrievalProvider(retrievalProvider); config.getAi().setProvider(provider);
        KnowledgeHit hit = new KnowledgeHit();
        hit.setArticleId("A1"); hit.setVersionId("V1"); hit.setTitle("会议音频排障");
        hit.setBody("检查输入设备"); hit.setSummary("检查输入设备"); hit.setScore(9);
        when(knowledge.retrieve(anyString(), nullable(String.class), anyInt())).thenReturn(List.of(hit));
        try (var context = new AnnotationConfigApplicationContext()) {
            context.registerBean(ConsultationProperties.class, () -> config);
            context.registerBean(KnowledgeQueryService.class, () -> knowledge);
            context.register(AiCompositionConfig.class); context.refresh();
            assertThat(context.getBeansOfType(KnowledgeRetriever.class)).hasSize(1);
            assertThat(context.getBeansOfType(OfficeDomainClassifier.class)).hasSize(1);
            assertThat(context.getBeansOfType(AnswerGenerator.class)).hasSize(1);
            assertThat(context.getBeansOfType(RagAdapter.class)).hasSize(1);
            RagResult result = context.getBean(RagAdapter.class).answer(new RagQuery("S1", "开会别人听不到我", null,
                    null, 5, new RagCaller("U_EMP01", "EMPLOYEE")),
                    new RagCallContext("composition", System.nanoTime() + 3_000_000_000L, new RagExecutionAudit()));
            assertThat(result.replyType()).isEqualTo(AiReplyType.ANSWER);
            assertThat(result.citations()).hasSize(1);
            assertThat(result.modelVersion()).isEqualTo("local".equals(provider) ? "local-extractive" : config.getAi().getModel());
        }
    }
}
