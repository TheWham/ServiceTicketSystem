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

/**
 * 咨询会话“结束”生命周期回归：
 *  - 结束动作必须落一条 SYSTEM 类型的结束消息（重开/翻历史时双方都能看到会话是因何结束的）；
 *  - 结束后工程师仍保留只读访问（参与人权限不被回收）；
 *  - 结束后双方发消息一律被拒（ILLEGAL_STATE_TRANSITION）；
 *  - 竞态防护：AI 答复生成期间会话被关闭时，必须用写锁读到最新状态，
 *    不允许生成完毕的“滞后答复”在关闭之后落库。
 */
class ConsultationCloseTest {
    private final CurrentUser employee = new CurrentUser("U1", RoleCode.EMPLOYEE, Actor.EMPLOYEE);
    private final CurrentUser engineer = new CurrentUser("E1", RoleCode.ENGINEER, Actor.ENGINEER);
    private final ConsultationProperties properties = new ConsultationProperties();
    private final AuthzService authz = new AuthzService(properties);

    /** 造一条指定状态的会话：员工 U1 创建，当前服务工程师 E1 */
    private Consultation consultation(ConsultationStatus status) {
        Consultation c = new Consultation();
        c.setSessionId("S1");
        c.setCreatorId("U1");
        c.setCurrentEngineerId("E1");
        c.setStatus(status);
        c.setVersion(0L);
        return c;
    }

    /** 投影契约：工程师侧列表/详情必须能看到会话发起人 creator_id（排队列表需要展示申请人） */
    @Test
    void projection_identifies_applicant_for_engineer_list_and_detail() {
        String json = Json.write(ConsultationProjection.of(consultation(ConsultationStatus.WAITING_ENGINEER)));
        assertTrue(json.contains("\"creator_id\":\"U1\""), json);
    }

    /**
     * 员工结束会话的主流程断言：
     *  1) 状态变为 CLOSED；2) 投影仍带当前工程师（详情页可回显）；
     *  3) 工程师对 CLOSED 会话的参与人校验通过（可回看历史）；
     *  4) 持久化恰好一条 SYSTEM 消息“员工已结束对话，会话已断开。”；
     *  5) 派单与 SLA 实例被清理（activeAssignment 查询 + cancel 调用发生）。
     */
    @Test
    void closing_persists_a_system_message_visible_in_history_and_keeps_engineer_access() {
        ConsultationTransitionService transitions = mock(ConsultationTransitionService.class);
        when(transitions.load("S1")).thenReturn(consultation(ConsultationStatus.HUMAN_ACTIVE));
        when(transitions.loadForUpdate("S1")).thenReturn(consultation(ConsultationStatus.HUMAN_ACTIVE));
        when(transitions.apply(any(), any())).thenReturn(consultation(ConsultationStatus.CLOSED));
        ConsultationMessageMapper messages = mock(ConsultationMessageMapper.class);
        List<ConsultationMessage> stored = new ArrayList<>();
        doAnswer(call -> {
            stored.add(call.getArgument(0));
            return 1;
        }).when(messages).insert(any(ConsultationMessage.class));
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
        // 结束后工程师仍属参与人（可读历史），但会话已终止
        assertDoesNotThrow(() -> authz.requireParticipant(engineer, consultation(ConsultationStatus.CLOSED)));
        // 结束通知至少一条且为 SYSTEM 类型——重新打开仍可看到
        assertEquals(1, stored.size(), "结束通知必须持久化，重新打开仍可看到");
        assertEquals(MessageSenderType.SYSTEM, stored.get(0).getSenderType());
        assertEquals("员工已结束对话，会话已断开。", stored.get(0).getContent());
        verify(assignments).activeAssignment("S1");
        verify(sla).cancel("S1");
    }

    /** CLOSED 之后员工与工程师发消息都必须拒绝（ILLEGAL_STATE_TRANSITION），会话真正终结 */
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

    /**
     * 竞态防护（关键）：
     * 进入 chat 时机读状态是 AI_ACTIVE 放行，随后用户关闭了会话；
     * 模型答复生成完毕准备落库前，必须用写锁重新读状态并看到 CLOSED，
     * 返回 AI_SESSION_NOT_ACTIVE，且绝不能把滞后答复写进消息表。
     */
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