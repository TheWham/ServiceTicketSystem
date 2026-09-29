package com.itticket.ticket.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.SaveDraftRequest;
import com.itticket.ticket.entity.TicketDraft;
import com.itticket.ticket.mapper.TicketDraftMapper;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DuplicateKeyException;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class TicketDraftCompatibilityTest {
    private final TicketDraftMapper mapper = mock(TicketDraftMapper.class);
    private final TicketDraftService service = new TicketDraftService(mapper, new ObjectMapper());
    private final UserContext.CurrentUser user = new UserContext.CurrentUser("U_EMP01", "Employee", "EMPLOYEE", "IT");

    private TicketDraft draft() {
        TicketDraft draft = new TicketDraft();
        draft.setDraftId("old-draft"); draft.setCreatorId(user.getUserId());
        draft.setNature("INCIDENT"); draft.setTitle("Original title");
        return draft;
    }

    @Test void loadsColumnBasedDraftFromMainWithoutLosingFields() {
        when(mapper.selectById("old-draft")).thenReturn(draft());
        var loaded = service.load(user, "old-draft");
        assertEquals("INCIDENT", loaded.payload().get("nature"));
        assertEquals("Original title", loaded.payload().get("title"));
    }

    @Test void concurrentCreateUpdatesTheExistingUsersDraftInsteadOfInsertingAnother() {
        TicketDraft concurrent = draft();
        when(mapper.selectOne(any())).thenReturn(null, concurrent);
        when(mapper.insert(any(TicketDraft.class))).thenThrow(new DuplicateKeyException("user_id"));
        SaveDraftRequest req = new SaveDraftRequest();
        req.setPayload(Map.of("title", "Updated", "nature", "INCIDENT", "source_session_id", "CS001"));
        var saved = service.save(user, "new-draft", req);
        assertEquals("old-draft", saved.draftId());
        assertEquals("Updated", concurrent.getTitle());
        assertTrue(concurrent.getPayloadJson().contains("CS001"));
        verify(mapper, times(1)).insert(any(TicketDraft.class));
        verify(mapper).updateById(concurrent);
    }

    @Test void anotherUsersDraftCannotBeReadOrDeleted() {
        TicketDraft other = draft(); other.setCreatorId("U_OTHER");
        when(mapper.selectById("old-draft")).thenReturn(other);
        assertNull(service.load(user, "old-draft"));
        service.delete(user, "old-draft");
        verify(mapper, never()).deleteById(anyString());
    }
}
