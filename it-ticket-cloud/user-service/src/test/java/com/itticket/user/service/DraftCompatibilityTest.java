package com.itticket.user.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.user.dto.DraftRequest;
import com.itticket.user.entity.TicketDraft;
import com.itticket.user.mapper.TicketDraftMapper;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class DraftCompatibilityTest {
    @Test void legacySaveMergesFieldsAndKeepsConsultationContext() throws Exception {
        TicketDraftMapper mapper = mock(TicketDraftMapper.class);
        ObjectMapper json = new ObjectMapper();
        DraftService service = new DraftService(mapper, json);
        TicketDraft existing = new TicketDraft();
        existing.setDraftId("draft-1"); existing.setUserId("U_EMP01");
        existing.setPayloadJson("{\"source_session_id\":\"CS001\",\"field_values\":{\"summary\":\"AI summary\"},\"title\":\"old\"}");
        when(mapper.selectOne(any())).thenReturn(existing);
        DraftRequest req = new DraftRequest(); req.setTitle("Updated"); req.setTicketNature("INCIDENT");
        service.saveDraft("U_EMP01", req);
        var payload = json.readTree(existing.getPayloadJson());
        assertEquals("CS001", payload.get("source_session_id").asText());
        assertEquals("AI summary", payload.get("field_values").get("summary").asText());
        assertEquals("Updated", payload.get("title").asText());
        assertNotNull(existing.getLastSavedAt()); assertNotNull(existing.getExpiresAt());
        verify(mapper).updateById(existing);
    }
}
