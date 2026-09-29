package com.itticket.consultation.service;

import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.adapter.GuardedRagClient;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.ConsultationProjection;
import com.itticket.consultation.dto.ContentRequest;
import com.itticket.consultation.dto.AiChatRequest;
import com.itticket.consultation.dto.AiChatResponse;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.enums.MessageSenderType;
import com.itticket.consultation.enums.RoleCode;
import com.itticket.consultation.mapper.ConsultationMapper;
import com.itticket.consultation.mapper.AiInteractionMapper;
import com.itticket.consultation.mapper.ConsultationMessageMapper;
import com.itticket.consultation.statemachine.Actor;
import com.itticket.consultation.support.Json;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ConsultationCloseTest {
    private final CurrentUser employee = new CurrentUser("U1", RoleCode.EMPLOYEE, Actor.EMPLOYEE);
    private final CurrentUser engineer = new CurrentUser("E1", RoleCode.ENGINEER, Actor.ENGINEER);
    private final ConsultationProperties properties = new ConsultationProperties();
    private final AuthzService authz = new AuthzService(properties);

    private Consultation consultation(ConsultationStatus status) {
        Consultation c = new Consultation();
        c.setSessionId("S1");
        c.setCreatorId("U1");
        c.setCurrentEngineerId("E1");
        c.setStatus(status);
        c.setVersion(0L);
        return c;
    }

    @Test
    void projection_identifies_applicant_for_engineer_list_and_detail() {
        String json = Json.write(ConsultationProjection.of(consultation(ConsultationStatus.WAITING_ENGINEER)));
        assertTrue(json.contains("\"creator_id\":\"U1\""), json);
    }

    @Test
    void closing_persists_a_system_message_visible_in_history_and_keeps_engineer_access() {
        ConsultationTransitionService transitions = mock(ConsultationTransitionService.class);
        when(transitions.load("S1")).thenReturn(consultation(ConsultationStatus.HUMAN_ACTIVE));
        when(transitions.loadForUpdate("S1")).thenReturn(consultation(ConsultationStatus.HUMAN_ACTIVE));
        when(transitions.apply(any(), any())).thenReturn(consultation(ConsultationStatus.CLOSED));
        ConsultationMessageMapper messages = mock(ConsultationMessageMapper.class);
        List<ConsultationMessage> stored = new ArrayList<>();
        doAnswer(call -> { stored.add(call.getArgument(0)); return 1; })
                .when(messages).insert(any(ConsultationMessage.class));
        AssignmentService assignments = mock(AssignmentService.class);
        ConsultationSlaService sla = mock(ConsultationSlaService.class);
        ConsultationMessageService messageService = new ConsultationMessageService(messages, transitions, assignments, sla, authz);
        IdempotencyService idempotency = mock(IdempotencyService.class);
        when(idempotency.execute(anyString(), anyString(), anyString(), any(), eq(ConsultationProjection.class), any()))
                .thenAnswer(call -> new IdempotentResult<>(((Supplier<?>) call.getArgument(5)).get(), false));
        ConsultationService service = new ConsultationService(mock(ConsultationMapper.class), transitions,
                messageService, assignments, sla, authz, idempotency, mock(OutboxService.class), properties);

        ConsultationProjection result = service.close(employee, "S1", "close-1");

        assertEquals("CLOSED", result.status());
        assertEquals("E1", result.currentEngineerId());
        assertDoesNotThrow(() -> authz.requireParticipant(engineer, consultation(ConsultationStatus.CLOSED)));
        assertEquals(1, stored.size(), "结束通知必须持久化，重新打开仍可看到");
        assertEquals(MessageSenderType.SYSTEM, stored.get(0).getSenderType());
        assertEquals("员工已结束对话，会话已断开。", stored.get(0).getContent());
        verify(assignments).activeAssignment("S1");
        verify(sla).cancel("S1");
    }

    @Test
    void neither_employee_nor_engineer_can_send_after_close() {
        ConsultationMessageService service = new ConsultationMessageService(mock(ConsultationMessageMapper.class),
                mock(ConsultationTransitionService.class), mock(AssignmentService.class), mock(ConsultationSlaService.class), authz);
        for (CurrentUser user : List.of(employee, engineer)) {
            ApiException error = assertThrows(ApiException.class, () -> service.send(user,
                    consultation(ConsultationStatus.CLOSED), new ContentRequest("消息", "M1", null)));
            assertEquals(ApiCode.ILLEGAL_STATE_TRANSITION, error.getCode());
        }
    }

    @Test
    void ai_answer_finishing_after_close_is_rejected_before_persisting_the_reply() {
        ConsultationTransitionService transitions = mock(ConsultationTransitionService.class);
        when(transitions.load("S1")).thenReturn(consultation(ConsultationStatus.AI_ACTIVE));
        // 模型调用期间关闭已提交；写锁读必须看到 CLOSED，而非事务早期的 AI_ACTIVE。
        when(transitions.loadForUpdate("S1")).thenReturn(consultation(ConsultationStatus.CLOSED));
        IdempotencyService idempotency = mock(IdempotencyService.class);
        when(idempotency.execute(anyString(), anyString(), anyString(), any(), eq(AiChatResponse.class), any()))
                .thenAnswer(call -> new IdempotentResult<>(((Supplier<?>) call.getArgument(5)).get(), false));
        ConsultationMessageService messages = mock(ConsultationMessageService.class);
        AiConsultationService service = new AiConsultationService(transitions, messages,
                mock(KnowledgeQueryService.class), mock(GuardedRagClient.class), mock(AiInteractionMapper.class),
                authz, idempotency, properties);

        ApiException error = assertThrows(ApiException.class, () -> service.chat(employee, "S1",
                new AiChatRequest("打印机离线", null), "ai-1"));
        assertEquals(ApiCode.AI_SESSION_NOT_ACTIVE, error.getCode());
        verify(messages, never()).appendAiMessage(anyString(), anyString(), anyString(), any());
    }
}
