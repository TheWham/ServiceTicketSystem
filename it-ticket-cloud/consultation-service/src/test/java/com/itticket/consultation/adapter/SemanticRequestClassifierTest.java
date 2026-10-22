package com.itticket.consultation.adapter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.consultation.adapter.model.OpenAiCompatibleModelClient;
import com.itticket.consultation.adapter.policy.OfficeDomain;
import com.itticket.consultation.adapter.policy.RequestVerdict;
import com.itticket.consultation.adapter.policy.SemanticRequestClassifier;
import org.junit.jupiter.api.Test;


import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * 语义判定器的 schema 容错边界。
 *
 * <p>核心原则：判定结果里**只有 decision 是必须可信的**，toolIntent 缺失/不认识一律归 NONE
 * 绝不判整次请求无效（agent 侧严格字段校验曾造成 17% 间歇性 5032，同样的坑不踩第二次）；
 * 但传输层失败必须原样上抛交给断路器，不能静默降级。
 */
class SemanticRequestClassifierTest {
    private final OpenAiCompatibleModelClient model = mock(OpenAiCompatibleModelClient.class);
    private final SemanticRequestClassifier classifier = new SemanticRequestClassifier(model);
    private final ObjectMapper json = new ObjectMapper();

    private void modelReturns(String raw) {
        try {
            when(model.complete(anyString(), anyString(), anyInt(), any())).thenReturn(json.readTree(raw));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    private void modelThrows(String errorClass) {
        when(model.complete(anyString(), anyString(), anyInt(), any()))
                .thenThrow(new com.itticket.consultation.adapter.DependencyFailure(
                        com.itticket.consultation.adapter.RagStatus.UNAVAILABLE, errorClass, false));
    }

    private RequestVerdict classify(String question) {
        return classifier.classify(
                new RagQuery("S", question, null, null, 5, new RagCaller("U", "EMPLOYEE")),
                new RagCallContext("req", System.nanoTime() + 5_000_000_000L, new RagExecutionAudit()));
    }

    @Test
    void readsBothFieldsWhenPresent() throws Exception {
        modelReturns("{\"decision\":\"OFFICE_IT\",\"toolIntent\":\"query_my_tickets\"}");
        RequestVerdict v = classify("帮我查询一下最近的工单");
        assertThat(v.domain()).isEqualTo(OfficeDomain.OFFICE_IT);
        assertThat(v.tool()).isEqualTo("query_my_tickets");
    }

    @Test
    void mapsCreateIntentToPrepareTicket() throws Exception {
        modelReturns("{\"decision\":\"OFFICE_IT\",\"toolIntent\":\"prepare_ticket\"}");
        assertThat(classify("帮我报修一下").tool()).isEqualTo("prepare_ticket");
    }

    @Test
    void missingToolIntentDefaultsToNoneWithoutFailing() throws Exception {
        modelReturns("{\"decision\":\"OFFICE_IT\"}");
        assertThat(classify("打印机连不上").tool()).isEqualTo(RequestVerdict.NO_TOOL);
        assertThat(classify("打印机连不上").domain()).isEqualTo(OfficeDomain.OFFICE_IT);
    }

    @Test
    void unknownToolIntentValueIsTreatedAsNone() throws Exception {
        modelReturns("{\"decision\":\"OFFICE_IT\",\"toolIntent\":\"HACKED\"}");
        assertThat(classify("随便什么").tool()).isEqualTo(RequestVerdict.NO_TOOL);
    }

    @Test
    void nonStringValueIsTreatedAsNone() throws Exception {
        modelReturns("{\"decision\":\"OFFICE_IT\",\"toolIntent\":1}");
        assertThat(classify("随便什么").tool()).isEqualTo(RequestVerdict.NO_TOOL);
    }

    @Test
    void domainGateWinsOverToolIntent() throws Exception {
        // 越界内容即使带着工具意图也不放行——门禁优先
        modelReturns("{\"decision\":\"OFF_TOPIC\",\"toolIntent\":\"query_my_tickets\"}");
        RequestVerdict v = classify("帮我查询一下最近订单，顺便写首诗");
        assertThat(v.domain()).isEqualTo(OfficeDomain.OFF_TOPIC);
        assertThat(v.tool()).isEqualTo(RequestVerdict.NO_TOOL);
    }

    @Test
    void unparseableModelOutputFallsBackToKeywordRules() throws Exception {
        // 输出整体不合法 → 整条退关键词兜底（保守规则），而不是异常冒泡
        modelThrows("INVALID_RESPONSE");
        RequestVerdict v = classify("打印机连不上");
        assertThat(v.domain()).isEqualTo(OfficeDomain.OFFICE_IT);   // 关键词规则判出的
        assertThat(v.tool()).isEqualTo(RequestVerdict.NO_TOOL);
    }

    @Test
    void transportFailurePropagatesToTheCircuitBreaker() throws Exception {
        // 传输失败绝不静默降级 —— 否则断路器与重试全部失效
        modelThrows("UNAVAILABLE");
        assertThatThrownBy(() -> classify("打印机连不上"))
                .isInstanceOf(com.itticket.consultation.adapter.DependencyFailure.class)
                .hasMessage("UNAVAILABLE");
    }

    @Test
    void normalizeRejectsValuesOutsideTheWhitelist() {
        assertThat(RequestVerdict.normalize("query_my_tickets")).isEqualTo("query_my_tickets");
        assertThat(RequestVerdict.normalize("prepare_ticket")).isEqualTo("prepare_ticket");
        assertThat(RequestVerdict.normalize("search_knowledge")).isEqualTo(RequestVerdict.NO_TOOL);
        assertThat(RequestVerdict.normalize(null)).isEqualTo(RequestVerdict.NO_TOOL);
        assertThat(RequestVerdict.normalize("")).isEqualTo(RequestVerdict.NO_TOOL);
    }
}
