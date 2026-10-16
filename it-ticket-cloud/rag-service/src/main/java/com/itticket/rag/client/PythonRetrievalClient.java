package com.itticket.rag.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.rag.config.RagRetrievalProperties;
import com.itticket.rag.vo.RagRetrievalResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

/**
 * ============================================================================
 * Python 检索内核客户端 (PythonRetrievalClient)
 * ============================================================================
 *
 * <p>provider=python 时，RagRetrievalService 的 ②向量化 + ③ES 检索 由外置 Python 检索
 * 内核服务承担（rag_pipeline：BM25+Dense 双路 + RRF + Cross-Encoder 精排 + 低置信拒答）。
 * 本客户端只做协议适配，不重新解释远端结论（RD-006 边界）：
 * 非 200 / 业务码非 0 / 响应不可解析一律抛异常，由调用方按依赖不可用降级。</p>
 *
 * <p>契约（对齐 Python 侧 rag_service/contract.py 与 consultation 侧强校验）：</p>
 * <pre>
 * POST {pythonBaseUrl}/api/v1/rag/retrievals
 * 请求 {"question": "...", "topK": 5, "categoryId": "C_NET"}
 * 响应 Result 包络 {"code":0,"msg":"success","data":{items[],domain,suggestedReplyType,
 *              suggestedRefusalReason,topScore,reliable,publishedOnly}}
 * </pre>
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class PythonRetrievalClient {

    private static final String RETRIEVALS_PATH = "/api/v1/rag/retrievals";

    private final RagRetrievalProperties properties;
    private final ObjectMapper objectMapper;

    /** 连接超时可配置，客户端按需惰性构建并复用 */
    private volatile HttpClient httpClient;

    /**
     * 调用 Python 检索内核。
     *
     * @param question   用户问题（必填）
     * @param categoryId 可选类目编码（空白视为不传）
     * @param topK       返回条数（由调用方钳制到 maxTopK 内）
     * @throws IllegalStateException 网络异常 / 非 200 / 业务码非 0 / 响应不可解析
     */
    public RagRetrievalResponse retrieve(String question, String categoryId, int topK) {
        try {
            ObjectNode body = objectMapper.createObjectNode();
            body.put("question", question);
            body.put("topK", topK);
            if (categoryId != null && !categoryId.isBlank()) {
                body.put("categoryId", categoryId);
            }

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl() + RETRIEVALS_PATH))
                    .timeout(Duration.ofMillis(timeoutMs()))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body.toString(), StandardCharsets.UTF_8))
                    .build();
            HttpResponse<String> response = client().send(request,
                    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));

            if (response.statusCode() != 200) {
                throw new IllegalStateException("Python 检索返回 HTTP " + response.statusCode());
            }
            JsonNode root = objectMapper.readTree(response.body());
            if (root.path("code").asInt(-1) != 0) {
                throw new IllegalStateException("Python 检索业务码非 0：" + root.path("code").asInt());
            }
            JsonNode data = root.path("data");
            if (data.isMissingNode() || data.isNull()) {
                throw new IllegalStateException("Python 检索响应缺少 data");
            }
            return objectMapper.treeToValue(data, RagRetrievalResponse.class);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Python 检索调用被中断", e);
        } catch (Exception e) {
            log.warn("Python 检索内核调用失败: {}", e.getMessage());
            throw new IllegalStateException("Python 检索调用失败: " + e.getMessage(), e);
        }
    }

    /** 出站端点（日志/排障用） */
    public String endpoint() {
        return baseUrl() + RETRIEVALS_PATH;
    }

    private HttpClient client() {
        HttpClient current = httpClient;
        if (current == null) {
            synchronized (this) {
                if (httpClient == null) {
                    // 必须显式 HTTP/1.1：JDK 默认优先 HTTP/2，对明文 http:// 会先做 h2c
                    // Upgrade 协商，未升级成功时请求体被静默丢弃，Python 侧只能读到空 body。
                    // 跨语言冒烟实测：默认版本 → FastAPI 报 body missing（400）；1.1 → 正常。
                    httpClient = HttpClient.newBuilder()
                            .version(HttpClient.Version.HTTP_1_1)
                            .connectTimeout(Duration.ofMillis(connectTimeoutMs()))
                            .build();
                }
                current = httpClient;
            }
        }
        return current;
    }

    private String baseUrl() {
        String base = properties.getPythonBaseUrl();
        return (base == null ? "" : base.trim()).replaceAll("/+$", "");
    }

    private int timeoutMs() {
        return properties.getPythonTimeoutMs() == null ? 4200 : properties.getPythonTimeoutMs();
    }

    private int connectTimeoutMs() {
        return properties.getPythonConnectTimeoutMs() == null ? 500 : properties.getPythonConnectTimeoutMs();
    }
}
