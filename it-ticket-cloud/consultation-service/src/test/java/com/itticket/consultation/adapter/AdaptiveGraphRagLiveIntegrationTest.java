package com.itticket.consultation.adapter;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.consultation.adapter.generation.AnswerGenerator;
import com.itticket.consultation.adapter.generation.GenerationResult;
import com.itticket.consultation.adapter.model.DependencyHttpClient;
import com.itticket.consultation.adapter.policy.OfficeDomain;
import com.itticket.consultation.adapter.policy.RequestClassifier;
import com.itticket.consultation.adapter.policy.RequestVerdict;
import com.itticket.consultation.adapter.retrieval.*;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.service.KnowledgeQueryService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * 真实全链路集成测试：Java 咨询服务（consultation-service）接入 Python 检索内核（rag-service :8310）
 * 检验自适应 GraphRAG、契约严格校验、MySQL 发布版本核验与因果链无损透传。
 */
public class AdaptiveGraphRagLiveIntegrationTest {

    private static final String RAG_BASE_URL = "http://127.0.0.1:8310";

    private ConsultationProperties config;
    private DependencyHttpClient http;
    private KnowledgeQueryService knowledgeService;
    private RagServiceKnowledgeRetriever retriever;

    @BeforeEach
    void setUp() {
        config = new ConsultationProperties();
        config.getAi().setRagBaseUrl(RAG_BASE_URL);
        config.getAi().setRagRequestTimeoutMs(5000);
        config.getAi().setTopK(3);

        http = new DependencyHttpClient();
        knowledgeService = mock(KnowledgeQueryService.class);
        // 模拟 MySQL 数据库当前发布版本核验：真实卡片（ITKB-前缀对应真实 articleId）均通过校验
        when(knowledgeService.isPublishedCurrentVersion(anyString(), anyString())).thenReturn(true);

        retriever = new RagServiceKnowledgeRetriever(config, http);
    }

    private boolean isRagServiceOnline() {
        try {
            HttpClient client = HttpClient.newHttpClient();
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(RAG_BASE_URL + "/api/health"))
                    .GET()
                    .build();
            HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString());
            return resp.statusCode() == 200;
        } catch (Exception e) {
            return false;
        }
    }

    @Test
    @DisplayName("集成测试 1：单维事实查询自适应分流 —— 纯双路召回，不注入图谱因果链，契约字段严密对齐")
    void testSingleDimensionQueryThroughJavaRetriever() {
        assertThat(isRagServiceOnline())
                .as("Python 检索服务 (http://127.0.0.1:8310) 必须处于运行状态")
                .isTrue();

        RagQuery query = new RagQuery("SESSION_001", "VPN客户端在哪里下载？", "C_NET", "DEV_01", 3,
                new RagCaller("U_EMP01", "EMPLOYEE"));
        long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(5);
        RagCallContext context = new RagCallContext("REQ_SINGLE_001", deadline, new RagExecutionAudit());

        RetrievalResult result = retriever.retrieve(query, context);

        assertThat(result.domain()).isEqualTo(OfficeDomain.OFFICE_IT);
        assertThat(result.reliable()).isTrue();
        assertThat(result.refusalReason()).isNull();
        assertThat(result.items()).isNotEmpty();
        assertThat(result.topScore().compareTo(BigDecimal.ZERO)).isGreaterThan(0);

        RetrievedKnowledge topItem = result.items().get(0);
        assertThat(topItem.chunkId()).isNotBlank();
        assertThat(topItem.articleId()).isNotBlank().isNotEqualTo("unknown");
        assertThat(topItem.versionId()).isNotBlank().isNotEqualTo("unknown");
        assertThat(topItem.indexVersion()).isEqualTo(topItem.versionId()); // 契约：indexVersion 严格等于 versionId
        assertThat(topItem.title()).isNotBlank();
        assertThat(topItem.snippet().length()).isLessThanOrEqualTo(1000);

        // 核心验证：单维简单查询严格不注入图谱因果推导，避免无谓增加 Token
        assertThat(topItem.content()).doesNotContain("【知识图谱因果推导】");
    }

    @Test
    @DisplayName("集成测试 2：多维复合因果查询自适应分流 —— 触发 GraphRAG 拓扑推理，注入结构化因果链，且保证真实 articleId 与 versionId")
    void testMultiDimensionalQueryWithGraphCausalChainInjection() {
        assertThat(isRagServiceOnline())
                .as("Python 检索服务 (http://127.0.0.1:8310) 必须处于运行状态")
                .isTrue();

        String complexQuery = "在家连不上公司VPN，提示错误代码691认证失败，今天早上手机企业邮箱也提示凭据失效";
        RagQuery query = new RagQuery("SESSION_002", complexQuery, "C_NET", "DEV_01", 3,
                new RagCaller("U_EMP01", "EMPLOYEE"));
        long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(5);
        RagCallContext context = new RagCallContext("REQ_MULTI_001", deadline, new RagExecutionAudit());

        RetrievalResult result = retriever.retrieve(query, context);

        assertThat(result.domain()).isEqualTo(OfficeDomain.OFFICE_IT);
        assertThat(result.reliable()).isTrue();
        assertThat(result.refusalReason()).isNull();
        assertThat(result.items()).isNotEmpty();
        assertThat(result.topScore().compareTo(BigDecimal.ZERO)).isGreaterThan(0);

        RetrievedKnowledge topItem = result.items().get(0);
        assertThat(topItem.chunkId()).isNotBlank();
        assertThat(topItem.articleId()).isNotBlank().isNotEqualTo("unknown");
        assertThat(topItem.versionId()).isNotBlank().isNotEqualTo("unknown");
        assertThat(topItem.indexVersion()).isEqualTo(topItem.versionId()); // 确保一致性

        // 核心验证 1：首条切片必须包含图谱拓扑推导结论
        assertThat(topItem.content()).contains("【知识图谱因果推导】");
        assertThat(topItem.content()).satisfiesAnyOf(
                c -> assertThat(c).contains("AD域账号锁定"),
                c -> assertThat(c).contains("移动端邮件客户端旧密码轮询"),
                c -> assertThat(c).contains("诱发根因")
        );

        // 核心验证 2：摘要长度严格遵循 Java 约束 (<= 1000)
        assertThat(topItem.snippet().length()).isLessThanOrEqualTo(1000);
    }

    @Test
    @DisplayName("集成测试 3：Java ComposedRagAdapter 完整编排测试 —— 真实检索 + 策略材料筛选 + 生成守卫全链路")
    void testFullComposedRagAdapterWithRealKernel() {
        assertThat(isRagServiceOnline()).isTrue();

        // 1. 组装 RetrievalPolicy（核验当前发布版本）
        RetrievalPolicy policy = new RetrievalPolicy(knowledgeService, java.util.Set.of(), new BigDecimal("0.10"), 2);

        // 2. 模拟请求判定器
        RequestClassifier classifier = (query, ctx) -> new RequestVerdict(OfficeDomain.OFFICE_IT, RequestVerdict.NO_TOOL, false);

        // 3. 模拟 AnswerGenerator：验证它接收到了前置注入了因果链的材料
        AnswerGenerator mockGenerator = (query, material, ctx, sink) -> {
            assertThat(material).isNotEmpty();
            RetrievedKnowledge mat0 = material.get(0);
            assertThat(mat0.content()).contains("【知识图谱因果推导】");

            // 按照契约声明使用了该版本的切片
            return new GenerationResult(
                    AiReplyType.ANSWER,
                    "【综合诊断】：由于您修改密码后手机邮箱旧密码后台轮询导致 AD 域账号锁定，进而引发 VPN 691 认证失败。\n【建议流程】：1. 先关闭手机邮件同步；2. 前往自助平台或联系系统组解锁域账号；3. 更新手机邮箱密码后重新拨号。",
                    List.of(mat0.versionId()),
                    new BigDecimal("0.9500"),
                    null,
                    "deepseek-v4-flash"
            );
        };

        // 4. 组装完整的 ComposedRagAdapter
        ComposedRagAdapter adapter = new ComposedRagAdapter(
                classifier,
                retriever,
                policy,
                mockGenerator,
                false,
                null,
                com.itticket.consultation.adapter.cache.SemanticAnswerCache.disabled()
        );

        GuardedRagClient client = new GuardedRagClient(adapter, config);

        String complexQuery = "在家连不上公司VPN，提示错误代码691认证失败，今天早上手机企业邮箱也提示凭据失效";
        RagQuery query = new RagQuery("SESSION_003", complexQuery, "C_NET", "DEV_01", 3,
                new RagCaller("U_EMP01", "EMPLOYEE"));

        RagResult ragResult = client.answer(query, "REQ_COMPOSED_001", com.itticket.consultation.adapter.TokenSink.discarding(), System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(60));

        // 5. 校验 AI 客服最终返回
        assertThat(ragResult.status()).isEqualTo(RagStatus.SUCCESS);
        assertThat(ragResult.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(ragResult.answerText()).contains("AD 域账号锁定");
        assertThat(ragResult.confidence()).isEqualByComparingTo("0.9500");
        assertThat(ragResult.citations()).isNotEmpty();

        KnowledgeCitationDto citation = ragResult.citations().get(0);
        assertThat(citation.articleId()).isNotBlank().isNotEqualTo("unknown");
        assertThat(citation.score().compareTo(BigDecimal.ZERO)).isGreaterThan(0);

        client.shutdown();
    }
}
