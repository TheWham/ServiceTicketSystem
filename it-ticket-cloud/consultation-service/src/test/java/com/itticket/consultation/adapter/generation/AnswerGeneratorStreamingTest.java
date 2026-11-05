package com.itticket.consultation.adapter.generation;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagExecutionAudit;
import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.adapter.RagCaller;
import com.itticket.consultation.adapter.TokenSink;
import com.itticket.consultation.adapter.agent.PythonAgentClient;
import com.itticket.consultation.adapter.model.DependencyHttpClient;
import com.itticket.consultation.adapter.model.OpenAiCompatibleModelClient;
import com.itticket.consultation.adapter.retrieval.RetrievedKnowledge;
import com.itticket.consultation.config.ConsultationProperties;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Task 3 RED:TokenSink 贯通生成侧。
 * 红线:本地路径走 completeStream,answerText 增量经 sink 外发(打字机);
 * agent 路径整文单次 accept(无增量可流);本地抽取式生成器忽略 sink 且 emitted() 保持 false。
 */
class AnswerGeneratorStreamingTest {

    private final ObjectMapper om = new ObjectMapper();
    private HttpServer server;

    @AfterEach
    void stop() {
        if (server != null) server.stop(0);
    }

    // ======== 装配 ========

    private static ConsultationProperties config(String baseUrl) {
        ConsultationProperties properties = new ConsultationProperties();
        properties.getAi().setBaseUrl(baseUrl);
        properties.getAi().setApiKey("test-token");
        properties.getAi().setRequestTimeoutMs(3000);
        return properties;
    }

    private static RagCallContext context() {
        return new RagCallContext("req-1", System.nanoTime() + 60_000_000_000L, new RagExecutionAudit());
    }

    private static RagQuery query() {
        return new RagQuery("S1", "开会别人听不到我", "C_NET", null, 3, new RagCaller("U1", "EMPLOYEE"));
    }

    private static List<RetrievedKnowledge> material() {
        return List.of(new RetrievedKnowledge("K1", "A1", "V1", "会议音频排障", "摘要", "完整内容",
                "C_NET", new BigDecimal("0.85"), "v1", null, null, null));
    }

    private String sixKeyAnswerJson() {
        return "{\"replyType\":\"ANSWER\",\"answerText\":\"第一步\\n第二步\","
                + "\"usedVersionIds\":[\"V1\"],\"confidence\":0.9,"
                + "\"knowledgeConflict\":false,\"offTopic\":false}";
    }

    // ======== 用例 ========

    @Test
    void localPathStreamsDecodedAnswerTokensThroughSink() throws Exception {
        String full = sixKeyAnswerJson();
        int cut = full.indexOf("第一步") + "第一步".length();
        HttpServer s = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server = s;
        s.createContext("/chat/completions", ex -> {
            ex.getResponseHeaders().add("Content-Type", "text/event-stream; charset=utf-8");
            ex.sendResponseHeaders(200, 0);
            OutputStream body = ex.getResponseBody();
            for (String payload : List.of(
                    "{\"choices\":[{\"delta\":{\"role\":\"assistant\"},\"finish_reason\":null}]}",
                    "{\"choices\":[{\"delta\":{\"content\":" + quote(full.substring(0, cut))
                            + "},\"finish_reason\":null}]}",
                    "{\"choices\":[{\"delta\":{\"content\":" + quote(full.substring(cut))
                            + "},\"finish_reason\":null}]}",
                    "{\"choices\":[{\"delta\":{},\"finish_reason\":\"stop\"}]}")) {
                body.write(("data: " + payload + "\n\n").getBytes(StandardCharsets.UTF_8));
                body.flush();
            }
            body.write("data: [DONE]\n\n".getBytes(StandardCharsets.UTF_8));
            ex.close();
        });
        s.start();
        OpenAiCompatibleAnswerGenerator generator = new OpenAiCompatibleAnswerGenerator(
                new OpenAiCompatibleModelClient(config("http://127.0.0.1:" + s.getAddress().getPort()),
                        new DependencyHttpClient()),
                config("http://127.0.0.1:" + s.getAddress().getPort()), null);
        List<String> tokens = new ArrayList<>();
        TokenSink sink = TokenSink.of(tokens::add);

        GenerationResult result = generator.generate(query(), material(), context(), sink);

        assertThat(tokens).containsExactly("第一步", "\n第二步");
        assertThat(sink.emitted()).isTrue();
        assertThat(result.replyType().name()).isEqualTo("ANSWER");
        assertThat(result.answerText()).isEqualTo("第一步\n第二步");
        assertThat(result.usedVersionIds()).containsExactly("V1");
    }

    @Test
    void agentPathEmitsWholeAnswerExactlyOnce() {
        PythonAgentClient agent = mock(PythonAgentClient.class);
        when(agent.enabled()).thenReturn(true);
        ObjectNode payload = om.createObjectNode().put("replyType", "ANSWER")
                .put("answerText", "整段答案文本")
                .put("confidence", 0.9).put("knowledgeConflict", false).put("offTopic", false);
        payload.set("usedVersionIds", om.createArrayNode().add("V1"));
        when(agent.chat(any(), anyList(), any()))
                .thenReturn(new PythonAgentClient.AgentResult(payload, null));
        OpenAiCompatibleAnswerGenerator generator = new OpenAiCompatibleAnswerGenerator(
                new OpenAiCompatibleModelClient(new ConsultationProperties(), new DependencyHttpClient()),
                new ConsultationProperties(), agent);
        List<String> tokens = new ArrayList<>();
        TokenSink sink = TokenSink.of(tokens::add);

        GenerationResult result = generator.generate(query(), material(), context(), sink);

        assertThat(tokens).containsExactly("整段答案文本");
        assertThat(sink.emitted()).isTrue();
        assertThat(result.answerText()).isEqualTo("整段答案文本");
    }

    @Test
    void localPathArmsFirstTokenGuardBeforeStreamingOut() throws Exception {
        // 2026-11-05 评审 C1:首字节哨兵必须由生成本地路径武装,而非只依赖编排器测试手工布设。
        String full = sixKeyAnswerJson();
        server = startSseAnswerServer(full);
        int port = server.getAddress().getPort();
        OpenAiCompatibleAnswerGenerator generator = new OpenAiCompatibleAnswerGenerator(
                new OpenAiCompatibleModelClient(config("http://127.0.0.1:" + port),
                        new DependencyHttpClient()),
                config("http://127.0.0.1:" + port), null);
        List<String> order = new ArrayList<>();
        TokenSink sink = new GuardRecordingSink(order);

        generator.generate(query(), material(), context(), sink);

        assertThat(order).containsExactly("arm", "token", "token");
    }

    private static final class GuardRecordingSink extends TokenSink {
        private final List<String> order;
        GuardRecordingSink(List<String> order) { super(null); this.order = order; }
        @Override public void accept(String token) { if (token != null && !token.isEmpty()) order.add("token"); }
        @Override public void armFirstTokenGuard() { order.add("arm"); }
    }

    @Test
    void agentPathNeverArmsFirstTokenGuard() {
        // agent 路径豁免首字节哨兵(裁决①):Python ReAct 无流,不应武装。
        PythonAgentClient agent = mock(PythonAgentClient.class);
        when(agent.enabled()).thenReturn(true);
        ObjectNode payload = om.createObjectNode().put("replyType", "ANSWER")
                .put("answerText", "整段答案文本")
                .put("confidence", 0.9).put("knowledgeConflict", false).put("offTopic", false);
        payload.set("usedVersionIds", om.createArrayNode().add("V1"));
        when(agent.chat(any(), anyList(), any()))
                .thenReturn(new PythonAgentClient.AgentResult(payload, null));
        OpenAiCompatibleAnswerGenerator generator = new OpenAiCompatibleAnswerGenerator(
                new OpenAiCompatibleModelClient(new ConsultationProperties(), new DependencyHttpClient()),
                new ConsultationProperties(), agent);
        List<String> order = new ArrayList<>();
        TokenSink sink = new GuardRecordingSink(order);

        generator.generate(query(), material(), context(), sink);

        assertThat(order).containsExactly("token");
    }

    @Test
    void extractiveGeneratorIgnoresSinkAndStaysUnemitted() {
        LocalKnowledgeAnswerGenerator generator = new LocalKnowledgeAnswerGenerator();
        List<String> tokens = new ArrayList<>();
        TokenSink sink = TokenSink.of(tokens::add);

        GenerationResult result = generator.generate(query(), material(), context(), sink);

        assertThat(tokens).isEmpty();
        assertThat(sink.emitted()).isFalse();
        assertThat(result.answerText()).isEqualTo("完整内容");
        assertThat(result.usedVersionIds()).containsExactly("V1");
    }

    /** 起一个 SSE 生成存根:把 full 切成两帧增量后 [DONE] 收尾。 */
    private HttpServer startSseAnswerServer(String full) throws IOException {
        int cut = full.indexOf("第一步") + "第一步".length();
        HttpServer s = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        s.createContext("/chat/completions", ex -> {
            ex.getResponseHeaders().add("Content-Type", "text/event-stream; charset=utf-8");
            ex.sendResponseHeaders(200, 0);
            OutputStream body = ex.getResponseBody();
            for (String payload : List.of(
                    "{\"choices\":[{\"delta\":{\"role\":\"assistant\"},\"finish_reason\":null}]}",
                    "{\"choices\":[{\"delta\":{\"content\":" + quote(full.substring(0, cut))
                            + "},\"finish_reason\":null}]}",
                    "{\"choices\":[{\"delta\":{\"content\":" + quote(full.substring(cut))
                            + "},\"finish_reason\":null}]}",
                    "{\"choices\":[{\"delta\":{},\"finish_reason\":\"stop\"}]}")) {
                body.write(("data: " + payload + "\n\n").getBytes(StandardCharsets.UTF_8));
                body.flush();
            }
            body.write("data: [DONE]\n\n".getBytes(StandardCharsets.UTF_8));
            ex.close();
        });
        s.start();
        return s;
    }

    /** JSON 文本片段包成字符串字面量。 */
    private String quote(String text) {
        return om.createObjectNode().put("v", text).get("v").toString();
    }
}
