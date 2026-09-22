package com.itticket.user.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.user.dto.DraftRequest;
import com.itticket.user.entity.TicketDraft;
import com.itticket.user.mapper.TicketDraftMapper;
import com.itticket.user.vo.DraftVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

/** 提单草稿 CRUD(每用户一条,UPSERT) —— 对应旧版 userController 的草稿方法 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DraftService {

    private final TicketDraftMapper draftMapper;
    private final ObjectMapper objectMapper;

    public DraftVO getDraft(String userId) {
        TicketDraft draft = draftMapper.selectOne(new QueryWrapper<TicketDraft>().eq("user_id", userId));
        if (draft == null) {
            return null;
        }
        DraftVO vo = new DraftVO();
        vo.setDraftId(draft.getDraftId());
        vo.setUserId(draft.getUserId());
        vo.setTitle(draft.getTitle());
        vo.setCategory(draft.getCategory());
        vo.setSubCategory(draft.getSubCategory());
        vo.setPriority(draft.getPriority());
        vo.setDescription(draft.getDescription());
        vo.setAttachmentUrls(parseAttachments(draft.getAttachmentUrls()));
        vo.setAssetId(draft.getAssetId());
        vo.setExpectedFinishTime(draft.getExpectedFinishTime());
        vo.setUpdatedAt(draft.getUpdatedAt());
        return vo;
    }

    public void saveDraft(String userId, DraftRequest req) {
        TicketDraft existing = draftMapper.selectOne(new QueryWrapper<TicketDraft>().eq("user_id", userId));
        String attachmentJson = toJson(req.getAttachmentUrls());
        String priority = req.getPriority() == null || req.getPriority().isBlank() ? "中" : req.getPriority();

        if (existing == null) {
            TicketDraft draft = new TicketDraft();
            draft.setUserId(userId);
            applyFields(draft, req, attachmentJson, priority);
            draft.setUpdatedAt(LocalDateTime.now());
            draftMapper.insert(draft);
        } else {
            applyFields(existing, req, attachmentJson, priority);
            existing.setUpdatedAt(LocalDateTime.now());
            draftMapper.updateById(existing);
        }
    }

    public void deleteDraft(String userId) {
        draftMapper.delete(new QueryWrapper<TicketDraft>().eq("user_id", userId));
    }

    private void applyFields(TicketDraft draft, DraftRequest req, String attachmentJson, String priority) {
        draft.setTitle(req.getTitle());
        draft.setCategory(req.getCategory());
        draft.setSubCategory(req.getSubCategory());
        draft.setPriority(priority);
        draft.setDescription(req.getDescription());
        draft.setAttachmentUrls(attachmentJson);
        draft.setAssetId(req.getAssetId());
        draft.setExpectedFinishTime(req.getExpectedFinishTime());
    }

    private String toJson(List<String> urls) {
        if (urls == null) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(urls);
        } catch (Exception e) {
            log.error("[DRAFT] 序列化附件失败: {}", e.getMessage());
            return null;
        }
    }

    private List<String> parseAttachments(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, objectMapper.getTypeFactory().constructCollectionType(List.class, String.class));
        } catch (Exception e) {
            return List.of();
        }
    }
}
