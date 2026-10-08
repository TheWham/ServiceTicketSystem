package com.itticket.user.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.user.dto.DraftRequest;
import com.itticket.user.entity.TicketDraft;
import com.itticket.user.mapper.TicketDraftMapper;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 工单草稿保存的合并语义测试（员工端“暂存草稿”功能）。
 *
 * 历史行为（必须保持的兼容点）：再次保存草稿时是“字段级合并”而不是整体覆盖 ——
 * 草稿 payload 里由AI咨询会话写入的 source_session_id、field_values 等上下文
 * 不能因为用户只改了标题就被抹掉，否则咨询转工单链路会丢失来源信息。
 */
class DraftCompatibilityTest {

    /**
     * 场景：已有草稿带有咨询会话上下文（source_session_id=CS001、AI 摘要），
     * 用户再次保存只更新了 title 和 nature。
     * 期望：合并后 payload 仍保留会话上下文与字段值，仅 title 被更新；
     * 同时刷新 last_saved_at / expires_at，并走 updateById（同一草稿更新而非新建）。
     */
    @Test
    void legacySaveMergesFieldsAndKeepsConsultationContext() throws Exception {
        TicketDraftMapper mapper = mock(TicketDraftMapper.class);
        ObjectMapper json = new ObjectMapper();
        DraftService service = new DraftService(mapper, json);
        TicketDraft existing = new TicketDraft();
        existing.setDraftId("draft-1");
        existing.setUserId("U_EMP01");
        existing.setPayloadJson("{\"source_session_id\":\"CS001\",\"field_values\":{\"summary\":\"AI summary\"},\"title\":\"old\"}");
        when(mapper.selectOne(any())).thenReturn(existing);
        DraftRequest req = new DraftRequest();
        req.setTitle("Updated");
        req.setTicketNature("INCIDENT");
        service.saveDraft("U_EMP01", req);
        // 合并后的 payload：会话上下文与自定义字段必须原样保留，标题被更新
        var payload = json.readTree(existing.getPayloadJson());
        assertEquals("CS001", payload.get("source_session_id").asText());
        assertEquals("AI summary", payload.get("field_values").get("summary").asText());
        assertEquals("Updated", payload.get("title").asText());
        // 保存时间与过期时间必须刷新（草稿有有效期，防无限堆积）
        assertNotNull(existing.getLastSavedAt());
        assertNotNull(existing.getExpiresAt());
        verify(mapper).updateById(existing);
    }
}