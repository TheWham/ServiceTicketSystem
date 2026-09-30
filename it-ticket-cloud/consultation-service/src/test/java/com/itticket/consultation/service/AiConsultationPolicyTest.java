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

class AiConsultationPolicyTest {
    @Test
    void ordinaryPasswordTroubleshootingUsesSemanticGuardAndPersistsAnswerMetadata() {
        ConsultationProperties properties = new ConsultationProperties();
        properties.getAi().setAnswerEnabled(true);
        properties.getAi().setProvider("openai-compatible");
        RagResult answer = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, "通用建议：检查输入法与大小写锁定。", List.of(), BigDecimal.ONE, null, "model", List.of(), 10, null, true, false);
        Fixture fixture = new Fixture(properties, answer);
        AiChatResponse response = fixture.chat("我的密码没改过却登录不上了");
        assertThat(response.replyType()).isEqualTo(AiReplyType.ANSWER);
        ArgumentCaptor<String> metadata = ArgumentCaptor.forClass(String.class);
        verify(fixture.messages).appendAiMessage(eq("S1"), anyString(), eq(response.answerText()), metadata.capture());
        Map<?, ?> saved = Json.read(metadata.getValue(), Map.class);
        assertThat(saved.get("interactionId")).isEqualTo(response.interactionId());
        assertThat(saved.get("replyType")).isEqualTo("ANSWER");
        assertThat(saved.get("generalAnswer")).isEqualTo(true);
    }

    @Test
    void offTopicRefusalHistoryExplicitlyStatesServiceBoundary() {
        ConsultationProperties properties = new ConsultationProperties();
        properties.getAi().setAnswerEnabled(true);
        Fixture fixture = new Fixture(properties, new RagResult(RagStatus.SUCCESS, AiReplyType.REFUSE, null, List.of(), BigDecimal.ZERO, AiRefusalReason.OFF_TOPIC, "model", List.of(), 10, null, false, false));
        AiChatResponse response = fixture.chat("推荐电影");
        assertThat(response.refusalReason()).isEqualTo(AiRefusalReason.OFF_TOPIC);
        ArgumentCaptor<String> content = ArgumentCaptor.forClass(String.class);
        verify(fixture.messages).appendAiMessage(eq("S1"), anyString(), content.capture(), anyString());
        assertThat(content.getValue()).contains("办公 IT").contains("不能答复");
    }

    private static class Fixture {
        final ConsultationMessageService messages = mock(ConsultationMessageService.class);
        final AiConsultationService service;
        Fixture(ConsultationProperties properties, RagResult answer) {
            Consultation c = new Consultation(); c.setSessionId("S1"); c.setCreatorId("U1");
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
        AiChatResponse chat(String question) {
            return service.chat(new CurrentUser("U1", RoleCode.EMPLOYEE, Actor.EMPLOYEE),
                    "S1", new AiChatRequest(question, null), "idempotent-1");
        }
    }
}
