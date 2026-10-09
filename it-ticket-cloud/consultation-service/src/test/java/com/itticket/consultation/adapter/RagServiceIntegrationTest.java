package com.itticket.consultation.adapter;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.service.AiAnswerGuard;
import com.itticket.consultation.service.KnowledgeQueryService;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

/** Real HTTP between adapter and contract fixtures; no external model/ES/DB needed. */
class RagServiceIntegrationTest {
    private final ObjectMapper json = new ObjectMapper();
    private final ConsultationProperties config = new ConsultationProperties();
    private final KnowledgeQueryService knowledge = mock(KnowledgeQueryService.class);
    private final AtomicInteger modelCalls = new AtomicInteger();
    private final AtomicInteger classificationCalls = new AtomicInteger();
    private String domainDecision = "OFFICE_IT";
    private String standaloneQuestion;
    private String classificationRequest;
    private HttpServer server;
    private String retrievalBody;
    private int retrievalStatus = 200;
    private JsonNode retrievalRequest;
    private String callerId, callerRole, requestId, modelRequest;
    private String usedVersions = "[\"V1\"]";

    @BeforeEach
    void start() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/api/v1/rag/retrievals", exchange -> {
            retrievalRequest = json.readTree(exchange.getRequestBody());
            callerId = exchange.getRequestHeaders().getFirst("X-User-Id");
            callerRole = exchange.getRequestHeaders().getFirst("X-User-Role");
            requestId = exchange.getRequestHeaders().getFirst("X-Request-Id");
            byte[] bytes = retrievalBody.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(retrievalStatus, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        server.createContext("/chat/completions", exchange -> {
            String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            String content;
            if (json.readTree(body).path("messages").get(0).path("content").asText().contains("范围与风险分类器")) {
                classificationCalls.incrementAndGet();
                classificationRequest = body;
                var decision = json.createObjectNode().put("decision", domainDecision);
                if (standaloneQuestion != null) decision.put("retrievalQuestion", standaloneQuestion);
                content = decision.toString();
            } else {
                modelCalls.incrementAndGet();
                modelRequest = body;
                content = "{\"replyType\":\"ANSWER\",\"answerText\":\"检查 VPN 网络连接。\",\"usedVersionIds\":" + usedVersions
                        + ",\"confidence\":0.9,\"knowledgeConflict\":false,\"offTopic\":false}";
            }
            byte[] bytes = json.writeValueAsBytes(Map.of("choices", List.of(Map.of("finish_reason", "stop", "message", Map.of("content", content)))));
            exchange.sendResponseHeaders(200, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        server.start();
        String base = "http://127.0.0.1:" + server.getAddress().getPort();
        config.getAi().setRetrievalProvider("rag-service");
        config.getAi().setRagBaseUrl(base);
        config.getAi().setBaseUrl(base);
        config.getAi().setApiKey("fixture-only");
        config.getAi().setProvider("openai-compatible");
        retrievalBody = response("OFFICE_IT", "ANSWER", null, true, "0.82", items());
    }

    @AfterEach void stop() { server.stop(0); }

    @Test
    void remoteKnowledgeSuppliesGenerationWithIdentityTraceAndOriginalCosineScore() {
        RagResult result = ask();
        assertThat(result.status()).isEqualTo(RagStatus.SUCCESS);
        assertThat(result.citations()).singleElement().satisfies(c -> {
            assertThat(c.articleId()).isEqualTo("A1");
            assertThat(c.versionId()).isEqualTo("V1");
            assertThat(c.score()).isEqualByComparingTo("0.82");
            assertThat(c.snippet()).isEqualTo("检查 VPN 网络连接。");
        });
        assertThat(modelCalls).hasValue(1);
        assertThat(classificationCalls).hasValue(1);
        assertThat(modelRequest).contains("检查 VPN 网络连接", "V1");
        assertThat(callerId).isEqualTo("U_TEST");
        assertThat(callerRole).isEqualTo("EMPLOYEE");
        assertThat(requestId).isEqualTo("req-integration");
        assertThat(retrievalRequest.path("categoryId").asText()).isEqualTo("C_NET");
        assertThat(retrievalRequest.path("topK").asInt()).isEqualTo(3);
        verifyNoInteractions(knowledge);
    }

    @ParameterizedTest
    @CsvSource({"OFFICE_IT,CONFLICTING_KNOWLEDGE", "OFFICE_IT,MODEL_UNAVAILABLE"})
    void ragRefusalIsPreservedAndNeverCallsGeneration(String domain, String reason) {
        retrievalBody = response(domain, "REFUSE", reason, false, "0.55", "[]");
        RagResult result = ask();
        assertThat(AiAnswerGuard.evaluate(result, config.getAi(), false, (a, v) -> true).refusalReason())
                .isEqualTo(AiRefusalReason.valueOf(reason));
        assertThat(modelCalls).hasValue(0);
        verifyNoInteractions(knowledge);
    }

    @Test
    void missingModelCredentialsAreExplicitDependencyFailure() {
        config.getAi().setApiKey("");
        retrievalBody = response("UNCERTAIN", "CLARIFY", null, false, "0", "[]");
        RagResult result = ask();
        assertThat(result.status()).isEqualTo(RagStatus.UNAVAILABLE);
        assertThat(result.answerText()).isNull();
        assertThat(modelCalls).hasValue(0);
    }

    @ParameterizedTest
    @CsvSource({"OFF_TOPIC,REFUSE,OFF_TOPIC", "HIGH_RISK,REFUSE,HIGH_RISK_TOPIC", "UNCERTAIN,CLARIFY,", "OFFICE_IT,REFUSE,LOW_CONFIDENCE"})
    void semanticItDecisionAllowsGeneralAnswerDespiteLegacyKeywordOrScoreDecision(String domain, String type, String reason) {
        usedVersions = "[]";
        retrievalBody = response(domain, type, reason, false, "0.55", "[]");
        RagResult result = new OpenAiCompatibleRagAdapter(knowledge, config).answer(
                new RagQuery("S1", "周报文件打不开，怎么排查电脑问题", List.of(), null, null, 3, "U_TEST", "EMPLOYEE"), "req-integration");
        assertThat(result.status()).isEqualTo(RagStatus.SUCCESS);
        assertThat(result.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(result.generalAnswer()).isTrue();
        assertThat(result.citations()).isEmpty();
        assertThat(classificationCalls).hasValue(1);
        assertThat(modelCalls).hasValue(1);
    }

    @ParameterizedTest
    @CsvSource({"OFF_TOPIC,OFF_TOPIC", "HIGH_RISK,HIGH_RISK_TOPIC"})
    void semanticRefusalNeverRetrievesOrGenerates(String decision, String reason) {
        domainDecision = decision;
        RagResult result = ask();
        assertThat(AiAnswerGuard.evaluate(result, config.getAi(), false, (a,v) -> true).refusalReason())
                .isEqualTo(AiRefusalReason.valueOf(reason));
        assertThat(classificationCalls).hasValue(1);
        assertThat(modelCalls).hasValue(0);
        assertThat(retrievalRequest).isNull();
    }

    @Test
    void remoteFollowUpRetrievesStandaloneQuestionAndGeneratesWithOriginalHistory() {
        standaloneQuestion = "Windows 11 VPN 重启后仍无法连接";
        RagResult result = new OpenAiCompatibleRagAdapter(knowledge, config).answer(new RagQuery(
                "S1", "重启过了还是不行", List.of(new RagQuery.Turn("user", "Windows 11 VPN 无法连接"),
                new RagQuery.Turn("assistant", "先重启客户端。")), "C_NET", null, 3, "U_TEST", "EMPLOYEE"), "req-integration");
        assertThat(result.status()).isEqualTo(RagStatus.SUCCESS);
        assertThat(retrievalRequest.path("question").asText()).isEqualTo(standaloneQuestion);
        assertThat(classificationRequest).contains("Windows 11 VPN 无法连接", "先重启客户端", "重启过了还是不行");
        assertThat(modelRequest).contains("Windows 11 VPN 无法连接", "先重启客户端", "重启过了还是不行");
    }

    @Test
    void irrelevantHitsAreNotUsedAsSourcesForGeneralAnswer() {
        usedVersions = "[]";
        retrievalBody = response("OFFICE_IT", "ANSWER", null, false, "0.2", items().replace("0.82", "0.2"));
        RagResult result = ask();
        assertThat(result.generalAnswer()).isTrue();
        assertThat(result.citations()).isEmpty();
        assertThat(modelRequest).doesNotContain("V1");
    }

    @Test
    void madeUpCitationCannotEscapeTheRemoteRetrievalSet() {
        usedVersions = "[\"INVENTED\"]";
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
    }

    @Test
    void dependencyFailureDoesNotFallBackToMysqlOrGeneralGeneration() {
        retrievalStatus = 500;
        retrievalBody = "{\"code\":50000,\"msg\":\"internal details must not escape\"}";
        assertThat(ask().status()).isEqualTo(RagStatus.UNAVAILABLE);
        assertThat(modelCalls).hasValue(0);
        verifyNoInteractions(knowledge);
    }

    @Test
    void businessFailureInHttp200IsNotAnEmptySuccess() {
        retrievalBody = "{\"code\":50000,\"data\":null}";
        assertThat(ask().status()).isEqualTo(RagStatus.UNAVAILABLE);
        assertThat(modelCalls).hasValue(0);
    }

    @Test
    void unpublishedOrUntraceableResultsAreRejected() {
        retrievalBody = retrievalBody.replace("\"publishedOnly\":true", "\"publishedOnly\":false");
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
        retrievalBody = response("OFFICE_IT", "ANSWER", null, true, "0.82", items().replace("\"indexVersion\":\"V1\"", "\"indexVersion\":\"OLD\""));
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
        assertThat(modelCalls).hasValue(0);
    }

    @Test
    void localGeneratorCanUseRemoteRetrievalWithoutRenormalizingCosine() {
        RagResult result = new KnowledgeRagAdapter(knowledge, config).answer(query(), "req-integration");
        assertThat(result.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(result.confidence()).isEqualByComparingTo("0.82");
        assertThat(modelCalls).hasValue(0);
        verifyNoInteractions(knowledge);
    }

    @Test
    void reliableBatchDoesNotMakeEveryChunkAValidSource() {
        String unrelated = items().replace("A1", "A2").replace("V1", "V2").replace("0.82", "0.20");
        retrievalBody = response("OFFICE_IT", "ANSWER", null, true, "0.82", items().replace("]", "," + unrelated.substring(1)));
        assertThat(ask().citations()).extracting(c -> c.versionId()).containsExactly("V1");
        assertThat(modelRequest).doesNotContain("V2");
        usedVersions = "[\"V2\"]";
        assertThat(ask().status()).isEqualTo(RagStatus.INVALID_RESPONSE);
    }

    @Test
    void localGeneratorRetainsConflictGuardForRemoteKnowledge() {
        String conflicting = items().replace("A1", "A2").replace("V1", "V2").replace("0.82", "0.81")
                .replace("VPN 排查", "其他 VPN 配置");
        retrievalBody = response("OFFICE_IT", "ANSWER", null, true, "0.82", items().replace("]", "," + conflicting.substring(1)));
        RagResult result = new KnowledgeRagAdapter(knowledge, config).answer(query(), "req-integration");
        assertThat(AiAnswerGuard.evaluate(result, config.getAi(), false, (a, v) -> true).refusalReason())
                .isEqualTo(AiRefusalReason.CONFLICTING_KNOWLEDGE);
    }

    private RagResult ask() { return new OpenAiCompatibleRagAdapter(knowledge, config).answer(query(), "req-integration"); }
    private RagQuery query() { return new RagQuery("S1", "VPN 无法连接", List.of(), "C_NET", null, 3, "U_TEST", "EMPLOYEE"); }
    private String items() { return "[{\"chunkId\":\"C1\",\"articleId\":\"A1\",\"versionId\":\"V1\",\"indexVersion\":\"V1\",\"title\":\"VPN 排查\",\"snippet\":\"检查 VPN 网络连接。\",\"content\":\"检查 VPN 网络连接。\",\"categoryId\":\"C_NET\",\"score\":0.82}]"; }
    private String response(String domain, String type, String reason, boolean reliable, String score, String items) {
        return "{\"code\":0,\"data\":{\"domain\":\"" + domain + "\",\"suggestedReplyType\":\"" + type
                + "\",\"suggestedRefusalReason\":" + (reason == null ? "null" : "\"" + reason + "\"")
                + ",\"topScore\":" + score + ",\"reliable\":" + reliable + ",\"publishedOnly\":true,\"items\":" + items + "}}";
    }
}
