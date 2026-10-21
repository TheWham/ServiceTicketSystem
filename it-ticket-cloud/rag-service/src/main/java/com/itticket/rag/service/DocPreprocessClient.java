package com.itticket.rag.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.config.PreprocessProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * ============================================================================
 * doc-ingest-service HTTP 客户端 (DocPreprocessClient)
 * ============================================================================
 *
 * 【职责】：将 DOCX 上传文件转发给预处理服务执行 L1 规则清洗，并把清洗后的
 * 条目列表还原为 {@link CleanedEntry}。本类不实现任何本地解析逻辑。
 *
 * 【装配时机供应商选择】：仅当 rag.preprocess.base-url 已配置时本 Bean 才被
 * 装配（@ConditionalOnProperty）；未配置时 DocumentParserService 对 DOCX 上传
 * 显式拒绝，不存在"远端不可达再悄悄回退本地解析"的双链路。
 *
 * 【失败语义】（对应 specs/04-resilience-degradation 依赖失败显式化）：
 * - 网络/超时异常      -> BizException(SYSTEM_ERROR)，原因保留真实异常信息
 * - HTTP 非 2xx        -> BizException(SYSTEM_ERROR)，透传服务端 detail
 * - 响应包络结构异常   -> BizException(SYSTEM_ERROR)
 */
@Slf4j
@Service
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "rag.preprocess", name = "base-url")
public class DocPreprocessClient implements DocPreprocessPort {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static final String CLEAN_ENDPOINT = "/v1/preprocess/docx-clean";

    private final PreprocessProperties properties;

    @Override
    public List<CleanedEntry> cleanDocx(String filename, byte[] fileBytes) {
        String baseUrl = properties.getBaseUrl();
        if (baseUrl == null || baseUrl.isBlank()) {
            throw new BizException(ErrorCode.SYSTEM_ERROR, "rag.preprocess.base-url 未配置，无法执行 DOCX 清洗");
        }
        long start = System.currentTimeMillis();
        try {
            String boundary = "itticket-preprocess-" + UUID.randomUUID();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl.replaceAll("/+$", "") + CLEAN_ENDPOINT))
                    .timeout(Duration.ofSeconds(properties.getTimeoutSeconds()))
                    .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                    .POST(HttpRequest.BodyPublishers.ofByteArray(buildMultipartBody(boundary, filename, fileBytes)))
                    .build();

            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                String detail = extractDetail(response.body());
                throw new BizException(ErrorCode.SYSTEM_ERROR,
                        "文档预处理服务清洗失败 (HTTP " + response.statusCode() + "): " + detail);
            }

            JsonNode root = OBJECT_MAPPER.readTree(response.body());
            JsonNode entriesNode = root.path("entries");
            if (!entriesNode.isArray()) {
                throw new BizException(ErrorCode.SYSTEM_ERROR, "文档预处理服务响应结构异常：缺失 entries 数组");
            }
            List<CleanedEntry> entries = new ArrayList<>();
            for (JsonNode node : entriesNode) {
                List<String> keywords = new ArrayList<>();
                node.path("keywords").forEach(k -> keywords.add(k.asText()));
                entries.add(CleanedEntry.builder()
                        .code(node.path("code").asText())
                        .title(node.path("title").asText())
                        .category(node.path("category").asText())
                        .keywords(keywords)
                        .markdown(node.path("markdown").asText())
                        .build());
            }
            log.info("DOCX preprocess succeeded: {} entries from [{}], took {}ms",
                    entries.size(), filename, System.currentTimeMillis() - start);
            if (entries.isEmpty()) {
                throw new BizException(ErrorCode.PARAM_INVALID, "DOCX 清洗结果为空：未从文档中切出任何条目");
            }
            return entries;
        } catch (BizException e) {
            throw e;
        } catch (IOException e) {
            throw new BizException(ErrorCode.SYSTEM_ERROR,
                    "文档预处理服务不可达或响应异常：" + e.getMessage());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new BizException(ErrorCode.SYSTEM_ERROR, "文档预处理调用被中断");
        }
    }

    /** 手工构造 multipart/form-data（JDK HttpClient 无内建 multipart 支持）。 */
    private byte[] buildMultipartBody(String boundary, String filename, byte[] fileBytes) {
        try {
            ByteArrayOutputStream body = new ByteArrayOutputStream();
            String header = "--" + boundary + "\r\n"
                    + "Content-Disposition: form-data; name=\"file\"; filename=\""
                    + filename.replace("\"", "") + "\"\r\n"
                    + "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n";
            body.write(header.getBytes(StandardCharsets.UTF_8));
            body.write(fileBytes);
            body.write(("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));
            return body.toByteArray();
        } catch (IOException e) {
            throw new BizException(ErrorCode.SYSTEM_ERROR, "构造预处理请求体失败：" + e.getMessage());
        }
    }

    /** 从 FastAPI 错误报文中提取 detail 字段，保留真实失败原因。 */
    private String extractDetail(String responseBody) {
        try {
            JsonNode node = OBJECT_MAPPER.readTree(responseBody);
            JsonNode detail = node.path("detail");
            return detail.isMissingNode() ? responseBody : detail.asText();
        } catch (Exception e) {
            return responseBody;
        }
    }
}
