package com.itticket.consultation.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.ContentRequest;
import com.itticket.consultation.dto.MessageProjection;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.enums.*;
import com.itticket.consultation.mapper.ConsultationMessageMapper;
import com.itticket.consultation.statemachine.Actor;
import com.itticket.consultation.support.Json;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ConsultationAttachmentMessageTest {
    private final ConsultationMessageMapper mapper = mock(ConsultationMessageMapper.class);
    private final ConsultationAttachmentService attachments = mock(ConsultationAttachmentService.class);
    private final ConsultationMessageService messages = new ConsultationMessageService(mapper,
            mock(ConsultationTransitionService.class), mock(AssignmentService.class),
            mock(ConsultationSlaService.class), new AuthzService(new ConsultationProperties()), attachments);
    private final CurrentUser creator = new CurrentUser("U1", RoleCode.EMPLOYEE, Actor.EMPLOYEE);

    @Test
    void attachment_only_message_is_a_valid_human_message() {
        when(attachments.bind(any(), any(), anyString(), eq(List.of("A1")))).thenReturn(List.of(
                new com.itticket.consultation.dto.AttachmentProjection("A1", "report.pdf", "application/pdf", 42, false)));
        Consultation c = session(ConsultationStatus.HUMAN_ACTIVE);
        MessageProjection sent = assertDoesNotThrow(() -> messages.send(creator, c, new ContentRequest(null, "C1", List.of("A1"))));
        assertEquals("A1", sent.attachments().get(0).attachmentId());
        assertEquals("", sent.content());
    }

    @Test
    void ai_phase_rejects_attachments_before_any_message_write() {
        ApiException error = assertThrows(ApiException.class, () -> messages.send(creator,
                session(ConsultationStatus.AI_ACTIVE), new ContentRequest(null, "C1", List.of("A1"))));
        assertEquals(ApiCode.ILLEGAL_STATE_TRANSITION, error.getCode());
        verify(mapper, never()).insert(any(ConsultationMessage.class));
    }

    @Test
    void history_projects_persisted_attachment_snapshot_with_ai_metadata_intact() {
        ConsultationMessage row = new ConsultationMessage();
        row.setCitationJson("""
                {"schemaVersion":1,"citations":[],"interactionId":"AI1","replyType":"ANSWER",
                 "attachments":[{"attachment_id":"A1","file_name":"report.pdf",
                 "content_type":"application/pdf","size":42,"is_image":false}]}
                """);
        JsonNode result = Json.read(Json.write(MessageProjection.of(row)), JsonNode.class);
        assertEquals("A1", result.path("attachments").path(0).path("attachment_id").asText());
        assertEquals("application/pdf", result.path("attachments").path(0).path("content_type").asText());
        assertEquals("AI1", result.path("interaction_id").asText());
        row.setWithdrawnAt(java.time.LocalDateTime.now());
        assertEquals(0, Json.read(Json.write(MessageProjection.of(row)), JsonNode.class).path("attachments").size());
    }

    private Consultation session(ConsultationStatus status) {
        Consultation c = new Consultation();
        c.setSessionId("S1");
        c.setCreatorId("U1");
        c.setCurrentEngineerId("E1");
        c.setStatus(status);
        return c;
    }

    @Test void legacy_idempotency_result_replays_an_empty_attachment_list() {
        MessageProjection result = Json.read("""
                {"message_id":"old","sender_type":"EMPLOYEE","content":"text","sent_at":null,"withdrawn_at":null}
                """, MessageProjection.class);
        assertEquals(List.of(),result.attachments());
    }
}
