package com.itticket.rag;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.rag.client.PythonRetrievalClient;
import com.itticket.rag.config.RagRetrievalProperties;
import com.itticket.rag.enums.AiReplyType;
import com.itticket.rag.enums.OfficeDomain;
import com.itticket.rag.vo.RagRetrievalResponse;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Python 检索内核客户端测试：用 JDK HttpServer 打桩，断言出站请求体与响应解析/异常语义。
 *
 * <p>契约对齐（Python 侧 rag_service/contract.py）：请求 {question,topK,categoryId?}；
 * 响应 Result 包络 {code,msg,data}，code != 0 视为业务错误。</p>
 */
public class PythonRetrievalClientTest {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final RagRetrievalProperties properties = new RagRetrievalProperties();
    private HttpServer server;
    private final AtomicReference<String> lastBody = new AtomicReference<>();
    private final AtomicReference<String> lastPath = new AtomicReference<>();
    private int statusCode = 200;
    private String responseBody = "";

    @BeforeEach
    public void startServer() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/api/v1/rag/retrievals", this::handle);
        server.start();
        properties.setPythonBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
        properties.setPythonTimeoutMs(4200);
        properties.setPythonConnectTimeoutMs(500);
    }

    private void handle(HttpExchange exchange) throws IOException {
        lastPath.set(exchange.getRequestURI().getPath());
        lastBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
        byte[] out = responseBody.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().add("Content-Type", "application/json");
        exchange.sendResponseHeaders(statusCode, out.length);
        exchange.getResponseBody().write(out);
        exchange.close();
    }

    @AfterEach
    public void stopServer() {
        if (server != null) {
            server.stop(0);
        }
    }

    private PythonRetrievalClient client() {
        return new PythonRetrievalClient(properties, objectMapper);
    }

    @Test
    public void sendsContractRequestAndParsesAnswer() throws Exception {
        responseBody = """
                {"code":0,"msg":"success","data":{
                  "items":[{"chunkId":"ITKB-ACC-002#c1","articleId":"art-1","versionId":"ver-1",
                            "indexVersion":"ver-1","title":"密码重置与过期处理","snippet":"片段",
                            "content":"整卡正文","categoryId":"C_ACC","score":0.8123}],
                  "domain":"OFFICE_IT","suggestedReplyType":"ANSWER","topScore":0.8123,
                  "reliable":true,"publishedOnly":true}}""";

        RagRetrievalResponse response = client().retrieve("密码过期怎么办", "C_ACC", 3);

        Assertions.assertEquals("/api/v1/rag/retrievals", lastPath.get());
        JsonNode sent = objectMapper.readTree(lastBody.get());
        Assertions.assertEquals("密码过期怎么办", sent.path("question").asText());
        Assertions.assertEquals(3, sent.path("topK").asInt());
        Assertions.assertEquals("C_ACC", sent.path("categoryId").asText());

        Assertions.assertEquals(OfficeDomain.OFFICE_IT, response.domain());
        Assertions.assertEquals(AiReplyType.ANSWER, response.suggestedReplyType());
        Assertions.assertTrue(response.reliable());
        Assertions.assertEquals(1, response.items().size());
        Assertions.assertEquals("ver-1", response.items().get(0).indexVersion());
    }

    @Test
    public void omitsBlankCategoryIdFromRequest() throws Exception {
        responseBody = """
                {"code":0,"msg":"success","data":{"items":[],"domain":"OFFICE_IT",
                 "suggestedReplyType":"REFUSE","suggestedRefusalReason":"LOW_CONFIDENCE",
                 "topScore":0.0,"reliable":false,"publishedOnly":true}}""";

        client().retrieve("随便问问", "  ", 5);

        JsonNode sent = objectMapper.readTree(lastBody.get());
        Assertions.assertFalse(sent.has("categoryId"));
    }

    @Test
    public void parsesRefusalEnvelope() throws Exception {
        responseBody = """
                {"code":0,"msg":"success","data":{"items":[],"domain":"OFFICE_IT",
                 "suggestedReplyType":"REFUSE","suggestedRefusalReason":"LOW_CONFIDENCE",
                 "topScore":0.0,"reliable":false,"publishedOnly":true}}""";

        RagRetrievalResponse response = client().retrieve("知识库没有的问题", null, 3);

        Assertions.assertEquals(AiReplyType.REFUSE, response.suggestedReplyType());
        Assertions.assertEquals("LOW_CONFIDENCE", response.suggestedRefusalReason().getValue());
        Assertions.assertFalse(response.reliable());
        Assertions.assertTrue(response.items().isEmpty());
    }

    @Test
    public void nonSuccessBusinessCodeThrows() {
        responseBody = "{\"code\":5000,\"msg\":\"boom\"}";

        IllegalStateException ex = Assertions.assertThrows(IllegalStateException.class,
                () -> client().retrieve("q", null, 3));
        Assertions.assertTrue(ex.getMessage().contains("5000"), ex.getMessage());
    }

    @Test
    public void non200StatusThrows() {
        statusCode = 503;
        responseBody = "{\"code\":5031,\"msg\":\"busy\"}";

        Assertions.assertThrows(IllegalStateException.class, () -> client().retrieve("q", null, 3));
    }

    /**
     * 跨语言冒烟暴露的坑（回归锁定）：JDK HttpClient 默认优先 HTTP/2，对明文 http://
     * 会先做 h2c Upgrade 协商；协商不成立时请求体被静默丢弃（Python/FastAPI 只读到空 body → 400）。
     * 必须显式固定 HTTP/1.1。
     */
    @Test
    public void pinsHttp11ForCleartextUpgradeCompatibility() throws Exception {
        responseBody = """
                {"code":0,"msg":"success","data":{"items":[],"domain":"OFFICE_IT",
                 "suggestedReplyType":"REFUSE","suggestedRefusalReason":"LOW_CONFIDENCE",
                 "topScore":0.0,"reliable":false,"publishedOnly":true}}""";
        PythonRetrievalClient instance = client();
        instance.retrieve("q", null, 3);

        java.lang.reflect.Field field = PythonRetrievalClient.class.getDeclaredField("httpClient");
        field.setAccessible(true);
        HttpClient http = (HttpClient) field.get(instance);
        Assertions.assertEquals(HttpClient.Version.HTTP_1_1, http.version(),
                "必须固定 HTTP/1.1，否则明文 h2c 协商会丢请求体");
    }

    @Test
    public void connectionFailureThrows() {
        properties.setPythonBaseUrl("http://127.0.0.1:1");   // 不可达端口

        Assertions.assertThrows(IllegalStateException.class, () -> client().retrieve("q", null, 3));
    }
}
