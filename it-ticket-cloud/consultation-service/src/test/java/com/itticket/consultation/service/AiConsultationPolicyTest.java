package com.itticket.consultation.service;

import com.itticket.consultation.adapter.*;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.*;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.enums.*;
import com.itticket.consultation.mapper.AiInteractionMapper;
import com.itticket.consultation.statemachine.Actor;
import com.itticket.consultation.support.Json;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * AI 咨询应答策略（AiConsultationService）的护栏行为回归：
 *  - 正常答复：答复元数据（interactionId / replyType / generalAnswer）必须随消息一并落库，
 *    历史回显与“有用/无用”反馈链路依赖这些字段；
 *  - 越界拒答：拒答原因 OFF_TOPIC 透出给前端，且落库文案必须明确宣告“只答复办公 IT 问题”的
 *    服务边界（不能让用户对拒答原因产生误解）。
 *
 * 测试不启动 Spring：用固件 Fixture 直接装配服务与内存桩
 * （会话状态机、幂等执行器、被护栏包裹的 RAG 客户端均为 mock）。
 */
class AiConsultationPolicyTest {

    /**
     * 正常答复路径：含“密码”关键词（高风险）但属常规故障排查，仍走语义护栏正常答复；
     * 断言持久化的消息 metadata 完整携带答复身份三要素 —— 反馈接口按 interactionId 反查。
     */
    @Test
    void ordinaryPasswordTroubleshootingUsesSemanticGuardAndPersistsAnswerMetadata() {
        ConsultationProperties properties = new ConsultationProperties();
        properties.getAi().setAnswerEnabled(true);
        properties.getAi().setProvider("openai-compatible");
        // 适配器层已完成语义判定的“可发布的通用答复”
        RagResult answer = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER,
                "通用建议：检查输入法与大小写锁定。", List.of(), BigDecimal.ONE,
                null, "model", List.of(), 10, null, true, false);
        Fixture fixture = new Fixture(properties, answer);
        AiChatResponse response = fixture.chat("我的密码没改过却登录不上了");
        assertThat(response.replyType()).isEqualTo(AiReplyType.ANSWER);
        // 追加到消息表的 AI 消息 metadata 必须带答复身份（历史/反馈链路都按这些键读取）
        ArgumentCaptor<String> metadata = ArgumentCaptor.forClass(String.class);
        verify(fixture.messages).appendAiMessage(eq("S1"), anyString(), eq(response.answerText()), metadata.capture());
        Map<?, ?> saved = Json.read(metadata.getValue(), Map.class);
        assertThat(saved.get("interactionId")).isEqualTo(response.interactionId());
        assertThat(saved.get("replyType")).isEqualTo("ANSWER");
        assertThat(saved.get("generalAnswer")).isEqualTo(true);
    }

    /**
     * 越界拒答路径：模型判定 OFF_TOPIC 拒答 ->
     * 响应透出 refusalReason=OFF_TOPIC（前端展示“非业务范围”徽标），
     * 落库给用户的拒答文案必须同时出现“办公 IT”与“不能答复”，明示服务边界。
     */
    @Test
    void offTopicRefusalHistoryExplicitlyStatesServiceBoundary() {
        ConsultationProperties properties = new ConsultationProperties();
        properties.getAi().setAnswerEnabled(true);
        Fixture fixture = new Fixture(properties,
                RagResult.refuse(AiRefusalReason.OFF_TOPIC, "model", List.of()));
        AiChatResponse response = fixture.chat("推荐电影");
        assertThat(response.refusalReason()).isEqualTo(AiRefusalReason.OFF_TOPIC);
        ArgumentCaptor<String> content = ArgumentCaptor.forClass(String.class);
        verify(fixture.messages).appendAiMessage(eq("S1"), anyString(), content.capture(), anyString());
        assertThat(content.getValue()).contains("办公 IT").contains("不能答复");
    }

    /**
     * 测试固件：手动装配 AiConsultationService 的最小上下文。
     *  - transitions.load*: 永远返回同一个 AI_ACTIVE 会话（跳过状态机细节）；
     *  - idempotency.execute: 直通执行业务函数并标记“非重放”（绕过幂等存储）;
     *  - rag.answer: 返回用例预置的适配器结果（模拟两阶段协议已完成）。
     */
    private static class Fixture {
        final ConsultationMessageService messages = mock(ConsultationMessageService.class);
        final AiConsultationService service;

        Fixture(ConsultationProperties properties, RagResult answer) {
            Consultation c = new Consultation();
            c.setSessionId("S1");
            c.setCreatorId("U1");
            c.setStatus(ConsultationStatus.AI_ACTIVE);
            ConsultationTransitionService transitions = mock(ConsultationTransitionService.class);
            when(transitions.load("S1")).thenReturn(c);
            when(transitions.loadForUpdate("S1")).thenReturn(c);
            IdempotencyService idempotency = mock(IdempotencyService.class);
            when(idempotency.execute(anyString(), anyString(), anyString(), any(), eq(AiChatResponse.class), any()))
                    .thenAnswer(call -> new IdempotentResult<>(((Supplier<?>) call.getArgument(5)).get(), false));
            GuardedRagClient rag = mock(GuardedRagClient.class);
            when(rag.answer(any(), nullable(String.class))).thenReturn(answer);
            service = new AiConsultationService(transitions, messages, mock(KnowledgeQueryService.class), rag,
                    mock(AiInteractionMapper.class), new AuthzService(properties), idempotency, properties);
        }

        /** 员工身份发一条问题（固定幂等键 idempotent-1） */
        AiChatResponse chat(String question) {
            return service.chat(new CurrentUser("U1", RoleCode.EMPLOYEE, Actor.EMPLOYEE),
                    "S1", new AiChatRequest(question, null), "idempotent-1");
        }
    }
}