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

/**
 * 工单草稿（ticket-service 侧）的兼容与并发回归：
 *  - 列式草稿与 payload JSON 双通道互相归一（ticket_nature 为规范字段，nature 为历史字段）；
 *  - 同一用户“一人一草稿”：并发插入撞唯一键时降级为更新既有草稿；
 *  - 越权防护：他人草稿不可读、不可删。
 */
class TicketDraftCompatibilityTest {
    private final TicketDraftMapper mapper = mock(TicketDraftMapper.class);
    private final TicketDraftService service = new TicketDraftService(mapper, new ObjectMapper());
    private final UserContext.CurrentUser user = new UserContext.CurrentUser("U_EMP01", "Employee", "EMPLOYEE", "IT");

    /** 造一条既有草稿：带规范 nature 列与标题，用于加载/合并场景 */
    private TicketDraft draft() {
        TicketDraft draft = new TicketDraft();
        draft.setDraftId("old-draft");
        draft.setCreatorId(user.getUserId());
        draft.setTicketNature("INCIDENT");
        draft.setTitle("Original title");
        return draft;
    }

    /** 加载草稿时列字段（ticket_nature / title）必须完整映射回 payload，前端表单据此回显 */
    @Test
    void loadsColumnBasedDraftFromMainWithoutLosingFields() {
        when(mapper.selectById("old-draft")).thenReturn(draft());
        var loaded = service.load(user, "old-draft");
        assertEquals("INCIDENT", loaded.payload().get("ticket_nature"));
        assertEquals("Original title", loaded.payload().get("title"));
    }

    /**
     * 并发/双击场景：两次保存几乎同时到达，selectOne 第一次查无 ->
     * insert 时撞 user_id 唯一键 -> 必须降级为“查回旧草稿并 updateById”，
     * 且新内容（标题/会话上下文）合并进旧草稿，绝不能出现同一用户两条草稿。
     */
    @Test
    void concurrentCreateUpdatesTheExistingUsersDraftInsteadOfInsertingAnother() {
        TicketDraft concurrent = draft();
        // 第一次查询为空（正常新建路径），撞唯一键后的第二次查询返回已被并发方创建的草稿
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

    /** 越权防护：草稿归属他人时 load 返回 null、delete 静默跳过（不泄露存在性，也绝不执行删除） */
    @Test
    void anotherUsersDraftCannotBeReadOrDeleted() {
        TicketDraft other = draft();
        other.setCreatorId("U_OTHER");
        when(mapper.selectById("old-draft")).thenReturn(other);
        assertNull(service.load(user, "old-draft"));
        service.delete(user, "old-draft");
        verify(mapper, never()).deleteById(anyString());
    }

    /**
     * 规范字段归一双向契约：
     *  保存时：payload 同时携带 ticket_nature 与历史 nature 时，ticket_nature 胜出，
     *          落库 payload 中历史 nature 键必须被清除；
     *  加载时：库里残留历史 nature 键的 payload 要归一为 ticket_nature，
     *          且咨询会话上下文（source_session_id）不得丢失。
     */
    @Test
    void canonicalDraftNatureWinsAndLegacyPayloadIsNormalized() {
        TicketDraft existing = draft();
        when(mapper.selectOne(any())).thenReturn(existing);
        SaveDraftRequest request = new SaveDraftRequest();
        request.setPayload(Map.of("ticket_nature", "SERVICE_REQUEST", "nature", "INCIDENT", "title", "Updated"));
        var saved = service.save(user, "old-draft", request);
        assertEquals("SERVICE_REQUEST", existing.getTicketNature());
        assertEquals("SERVICE_REQUEST", saved.payload().get("ticket_nature"));
        assertFalse(saved.payload().containsKey("nature"));

        // 反向：历史 payload 加载时也归一为 ticket_nature
        existing.setPayloadJson("{\"nature\":\"INCIDENT\",\"source_session_id\":\"CS001\"}");
        when(mapper.selectById("old-draft")).thenReturn(existing);
        var loaded = service.load(user, "old-draft");
        assertEquals("INCIDENT", loaded.payload().get("ticket_nature"));
        assertEquals("CS001", loaded.payload().get("source_session_id"));
        assertFalse(loaded.payload().containsKey("nature"));
    }
}