package com.itticket.consultation.service;

import com.itticket.consultation.adapter.model.TicketServiceClient;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.TicketDraftResponse;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.enums.MessageSenderType;
import com.itticket.consultation.enums.RoleCode;
import com.itticket.consultation.mapper.ConsultationMapper;
import com.itticket.consultation.statemachine.Actor;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

/**
 * 咨询转单预填（/consultations/{id}/ticket-draft）回归：
 *  - 优先读取 AI 消息里持久化的建单草稿，保证预填与员工看到的草稿一致；
 *  - 没有 AI 草稿时，从员工本人消息里抽取显式字段（“标题为X 内容为Y”）；
 *  - 描述绝不拼接完整会话时间线（AI 回复 / 排查建议 / 引用不得进入输入框）。
 */
class ConsultationTicketDraftTest {

    private final CurrentUser employee = new CurrentUser("U1", RoleCode.EMPLOYEE, Actor.EMPLOYEE);
    private final ConsultationProperties properties = new ConsultationProperties();
    private final AuthzService authz = new AuthzService(properties);

    private Consultation consultation() {
        Consultation c = new Consultation();
        c.setSessionId("S1");
        c.setCreatorId("U1");
        c.setStatus(ConsultationStatus.AI_ACTIVE);
        c.setCategoryId("C_OTH");
        c.setVersion(0L);
        return c;
    }

    private ConsultationMessage message(MessageSenderType type, String content, String metadata) {
        ConsultationMessage m = new ConsultationMessage();
        m.setMessageId("M-" + type + "-" + content.hashCode());
        m.setSenderType(type);
        m.setContent(content);
        m.setCitationJson(metadata);
        return m;
    }

    private TicketDraftResponse draft(List<ConsultationMessage> timeline) {
        ConsultationTransitionService transitions = mock(ConsultationTransitionService.class);
        when(transitions.load("S1")).thenReturn(consultation());
        ConsultationMessageService messages = mock(ConsultationMessageService.class);
        when(messages.loadTimeline("S1")).thenReturn(timeline);
        ConsultationService service = new ConsultationService(mock(ConsultationMapper.class), transitions, messages,
                mock(AssignmentService.class), mock(ConsultationSlaService.class), authz, mock(IdempotencyService.class),
                mock(OutboxService.class), properties, mock(TicketServiceClient.class));
        return service.ticketDraft(employee, "S1");
    }

    @Test
    void prefersPersistedAiDraftOverTimeline() {
        String metadata = """
                {"schemaVersion":1,"citations":[],"interactionId":"AI1","replyType":"ANSWER",
                 "generalAnswer":false,
                 "ticketDraft":{"title":"vpn连不上","category":"C_NET","description":"vpn连不上","priority":"MEDIUM"}}
                """;
        List<ConsultationMessage> timeline = List.of(
                message(MessageSenderType.EMPLOYEE, "新建一个工单 标题为vpn连不上 内容为vpn连不上", null),
                message(MessageSenderType.AI, "请先重启 VPN 客户端并检查网络设置。", metadata));

        TicketDraftResponse draft = draft(timeline);

        assertThat(draft.title()).isEqualTo("vpn连不上");
        assertThat(draft.description()).isEqualTo("vpn连不上");
        assertThat(draft.categoryId()).isEqualTo("C_NET");
        assertThat(draft.description()).doesNotContain("重启").doesNotContain("员工：");
    }

    @Test
    void extractsExplicitFieldsFromEmployeeMessageWhenNoAiDraft() {
        List<ConsultationMessage> timeline = List.of(
                message(MessageSenderType.EMPLOYEE, "新建一个工单 标题为vpn连不上 内容为vpn连不上", null),
                message(MessageSenderType.AI, "建议重启 VPN 客户端。", """
                        {"schemaVersion":1,"citations":[],"interactionId":"AI1","replyType":"ANSWER","generalAnswer":true}
                        """));

        TicketDraftResponse draft = draft(timeline);

        assertThat(draft.title()).isEqualTo("vpn连不上");
        assertThat(draft.description()).isEqualTo("vpn连不上");
        assertThat(draft.categoryId()).isEqualTo("C_OTH");
    }

    @Test
    void descriptionNeverContainsFullTimelineContext() {
        List<ConsultationMessage> timeline = List.of(
                message(MessageSenderType.EMPLOYEE, "电脑蓝屏", null),
                message(MessageSenderType.AI, "请拍照记录错误代码，并运行 sfc /scannow。", """
                        {"schemaVersion":1,"citations":[],"interactionId":"AI1","replyType":"ANSWER","generalAnswer":true}
                        """));

        TicketDraftResponse draft = draft(timeline);

        assertThat(draft.description()).isEqualTo("电脑蓝屏");
        assertThat(draft.description()).doesNotContain("AI").doesNotContain("sfc").doesNotContain("员工：");
    }
}