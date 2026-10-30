package com.itticket.consultation.adapter.generation;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagCaller;
import com.itticket.consultation.adapter.RagExecutionAudit;
import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.adapter.model.DependencyHttpClient;
import com.itticket.consultation.adapter.model.OpenAiCompatibleModelClient;
import com.itticket.consultation.adapter.retrieval.RetrievedKnowledge;
import com.itticket.consultation.config.ConsultationProperties;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 生成器材料主次标注(Task 13)。
 *
 * <p>走到生成器的 material 数组是带身份标注的投影:基础条目 {"role":"SOURCE", ...原字段},
 * 扩展邻居条目 {"role":"NEIGHBOR", "expandedFrom":…, "relation":…, ...原字段};
 * systemPrompt 新增邻居关联知识规则——邻居引用归邻居自身的 versionId,
 * 不得把邻居卡的操作步骤陈述为源卡内容;无邻居时字段与行为和现状逐一等价。</p>
 */
class AnswerGeneratorMaterialLabelingTest {

    /** 引用 V1(源卡)的合法 6 键回答,契约不变。 */
    private static final String REPLY =
            "{\"replyType\":\"ANSWER\",\"answerText\":\"检查打印机连接。\",\"usedVersionIds\":[\"V1\"]"
                    + ",\"confidence\":0.9,\"knowledgeConflict\":false,\"offTopic\":false}";

    private final ObjectMapper json = new ObjectMapper();
    private final List<JsonNode> requestBodies = new ArrayList<>();
    private HttpServer server;
    private OpenAiCompatibleAnswerGenerator generator;

    @BeforeEach
    void startProvider() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/chat/completions", exchange -> {
            requestBodies.add(json.readTree(exchange.getRequestBody().readAllBytes()));
            byte[] response = json.writeValueAsBytes(Map.of("choices", List.of(Map.of(
                    "finish_reason", "stop", "message", Map.of("content", REPLY)))));
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        server.start();
        ConsultationProperties config = new ConsultationProperties();
        config.getAi().setBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
        config.getAi().setApiKey("test-only");
        generator = new OpenAiCompatibleAnswerGenerator(
                new OpenAiCompatibleModelClient(config, new DependencyHttpClient()), config, null);
    }

    @AfterEach
    void stopProvider() { server.stop(0); }

    /** 断言 ①:material 数组 SOURCE/NEIGHBOR 身份标注与字段正确,邻居 versionId 归其自身。 */
    @Test
    void materialArrayCarriesSourceAndNeighborIdentityLabels() {
        JsonNode input = generate(List.of(
                base("C1", "A1", "V1", "0.8"),
                neighbor("C2", "A2", "V2", "0.4", "RELATED", "A1")));
        JsonNode material = input.path("material");
        assertThat(material).hasSize(2);

        JsonNode source = material.get(0);
        assertThat(source.path("role").asText()).isEqualTo("SOURCE");
        assertThat(source.path("chunkId").asText()).isEqualTo("C1");
        assertThat(source.path("articleId").asText()).isEqualTo("A1");
        assertThat(source.path("versionId").asText()).isEqualTo("V1");
        assertThat(source.path("title").asText()).isEqualTo("标题");
        assertThat(source.path("snippet").asText()).isEqualTo("摘要");
        assertThat(source.path("content").asText()).isEqualTo("正文");
        assertThat(source.path("categoryId").asText()).isEqualTo("C_NET");
        assertThat(source.path("score").decimalValue()).isEqualByComparingTo("0.8");
        // 基础条目不应携带图扩展三字段(NON_NULL 投影,与准入谓词的 null 保证一致)。
        assertThat(source.has("graphExpanded")).isFalse();
        assertThat(source.has("expandedFrom")).isFalse();
        assertThat(source.has("relation")).isFalse();

        JsonNode neighborEntry = material.get(1);
        assertThat(neighborEntry.path("role").asText()).isEqualTo("NEIGHBOR");
        assertThat(neighborEntry.path("chunkId").asText()).isEqualTo("C2");
        // 邻居条目的 versionId 是其自身的 V2(引用归邻居卡),不是源卡的 V1;
        // expandedFrom 指向源卡的 articleId,relation 保留边语义。
        assertThat(neighborEntry.path("versionId").asText()).isEqualTo("V2");
        assertThat(neighborEntry.path("expandedFrom").asText()).isEqualTo("A1");
        assertThat(neighborEntry.path("relation").asText()).isEqualTo("RELATED");
        assertThat(neighborEntry.path("score").decimalValue()).isEqualByComparingTo("0.4");
        // 邻居原常规字段原样保留。
        assertThat(neighborEntry.path("articleId").asText()).isEqualTo("A2");
        assertThat(neighborEntry.path("content").asText()).isEqualTo("正文");
    }

    /** 断言 ②:systemPrompt 新增关联知识规则(关键词「关联知识」「不得」),且旧规则不丢。 */
    @Test
    void systemPromptAddsNeighborKnowledgeRuleWithoutDroppingExistingRules() {
        generate(List.of(base("C1", "A1", "V1", "0.8")));
        String prompt = capturedSystemPrompt();
        assertThat(prompt)
                .contains("material 中 role=NEIGHBOR 的是源命中卡的关联知识")
                .contains("回答可参考")
                .contains("引用时引其自身的 versionId")
                .contains("不得把邻居卡的操作步骤陈述为源卡内容");
        // 现有规则原样保留(规则 1 与输出契约)。
        assertThat(prompt).contains("优先使用【参考资料】中的内容作答");
        assertThat(prompt).contains("只输出一个 JSON 对象");
    }

    /** 断言 ③:无邻居时行为与现状逐一等价——仅新增 role=SOURCE,字段一个不少一个不多。 */
    @Test
    void baseOnlyMaterialStaysEquivalentToCurrentBehaviorFieldByField() {
        JsonNode input = generate(List.of(
                base("C1", "A1", "V1", "0.8"),
                base("C5", "A5", "V5", "0.8")));
        // 输入其余部分不变。
        assertThat(input.path("question").asText()).isEqualTo("打印机连不上怎么办");
        assertThat(input.path("priorTurns").isArray()).isTrue();
        JsonNode material = input.path("material");
        assertThat(material).hasSize(2);
        for (JsonNode entry : material) {
            assertThat(entry.path("role").asText()).isEqualTo("SOURCE");
            // 字段集 = 原反序列化字段 + role,一个不少(NON_NULL 下 null 三字段本就不出现)一个不多。
            Set<String> keys = new TreeSet<>();
            entry.fieldNames().forEachRemaining(keys::add);
            assertThat(keys).containsExactlyInAnyOrder(
                    "role", "chunkId", "articleId", "versionId", "title",
                    "snippet", "content", "categoryId", "score", "indexVersion");
            assertThat(entry.path("chunkId").asText()).startsWith("C");
            assertThat(entry.path("versionId").asText()).startsWith("V");
        }
        assertThat(material.get(0).path("chunkId").asText()).isEqualTo("C1");
        assertThat(material.get(1).path("chunkId").asText()).isEqualTo("C5");
        // 生成契约照常履行(结果校验与引用走通)。
        GenerationResult result = lastResult;
        assertThat(result.replyType()).isEqualTo(com.itticket.consultation.enums.AiReplyType.ANSWER);
        assertThat(result.usedVersionIds()).containsExactly("V1");
    }

    private GenerationResult lastResult;

    /** 生成一次并取回捕获的 user input(messages[1] 解析后的节点)。 */
    private JsonNode generate(List<RetrievedKnowledge> material) {
        requestBodies.clear();
        RagQuery query = new RagQuery("S-1", "打印机连不上怎么办", null, null, 5,
                new RagCaller("U_EMP01", "EMPLOYEE"));
        lastResult = generator.generate(query, material, new RagCallContext(
                "material-labeling", System.nanoTime() + 5_000_000_000L, new RagExecutionAudit()));
        assertThat(requestBodies).hasSize(1);
        JsonNode messages = requestBodies.get(0).path("messages");
        assertThat(messages).hasSize(2);
        assertThat(messages.get(0).path("role").asText()).isEqualTo("system");
        assertThat(messages.get(1).path("role").asText()).isEqualTo("user");
        try {
            return json.readTree(messages.get(1).path("content").asText());
        } catch (com.fasterxml.jackson.core.JsonProcessingException invalid) {
            throw new IllegalStateException("user input 不是合法 JSON", invalid);
        }
    }

    private String capturedSystemPrompt() {
        return requestBodies.get(0).path("messages").get(0).path("content").asText();
    }

    /** 基础条目:图扩展三字段为 null(准入谓词对基础条目的保证)。 */
    private static RetrievedKnowledge base(String chunk, String article, String version, String score) {
        return new RetrievedKnowledge(chunk, article, version, "标题", "摘要", "正文", "C_NET",
                new BigDecimal(score), version, null, null, null);
    }

    /** 扩展邻居条目:三字段真值(准入谓词对扩展条目的保证)。 */
    private static RetrievedKnowledge neighbor(String chunk, String article, String version,
            String score, String relation, String expandedFrom) {
        return new RetrievedKnowledge(chunk, article, version, "标题", "摘要", "正文", "C_NET",
                new BigDecimal(score), version, Boolean.TRUE, expandedFrom, relation);
    }
}
