package com.itticket.user.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import java.util.Map;
import java.util.LinkedHashMap;
import com.itticket.user.dto.DraftRequest;
import com.itticket.user.entity.TicketDraft;
import com.itticket.user.mapper.TicketDraftMapper;
import com.itticket.user.vo.DraftVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/** 提单草稿 CRUD(每用户一条,UPSERT) —— 字段对齐新提单 §10.2 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DraftService {

    private final TicketDraftMapper draftMapper;
    private final ObjectMapper objectMapper;

    public DraftVO getDraft(String userId) {
        TicketDraft draft = draftMapper.selectOne(new QueryWrapper<TicketDraft>().eq("creator_id", userId));
        if (draft == null || (draft.getExpiresAt() != null && draft.getExpiresAt().isBefore(LocalDateTime.now(java.time.ZoneOffset.UTC)))) {
            return null;
        }
        DraftVO vo = new DraftVO();
        vo.setDraftId(draft.getDraftId());
        vo.setUserId(draft.getUserId());
        vo.setNature(draft.getNature());
        vo.setCategoryId(draft.getCategoryId());
        vo.setTitle(draft.getTitle());
        vo.setDescription(draft.getDescription());
        vo.setImpactDescription(draft.getImpactDescription());
        vo.setUrgencyDescription(draft.getUrgencyDescription());
        vo.setLocation(draft.getLocation());
        vo.setContact(draft.getContact());
        vo.setAssetId(draft.getAssetId());
        vo.setUpdatedAt(draft.getUpdatedAt());
        return vo;
    }

    public void saveDraft(String userId, DraftRequest req) {
        TicketDraft existing = draftMapper.selectOne(new QueryWrapper<TicketDraft>().eq("creator_id", userId));
        if (existing == null) {
            TicketDraft draft = new TicketDraft();
            draft.setUserId(userId);
            draft.setCreatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
            draft.setVersion(0L);
            applyFields(draft, req);
            draft.setUpdatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
            draftMapper.insert(draft);
        } else {
            applyFields(existing, req);
            existing.setUpdatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
            draftMapper.updateById(existing);
        }
    }

    public void deleteDraft(String userId) {
        draftMapper.delete(new QueryWrapper<TicketDraft>().eq("creator_id", userId));
    }

    private void applyFields(TicketDraft draft, DraftRequest req) {
        draft.setNature(req.getNature());
        draft.setCategoryId(req.getCategoryId());
        draft.setTitle(req.getTitle());
        draft.setDescription(req.getDescription());
        draft.setImpactDescription(req.getImpactDescription());
        draft.setUrgencyDescription(req.getUrgencyDescription());
        draft.setLocation(req.getLocation());
        draft.setContact(req.getContact());
        draft.setAssetId(req.getAssetId());
        Map<String, Object> payload;
        try {
            payload = draft.getPayloadJson() == null ? new LinkedHashMap<>()
                    : objectMapper.readValue(draft.getPayloadJson(), new TypeReference<Map<String, Object>>() {});
            payload.put("nature", req.getNature());
            payload.remove("ticket_nature");
            payload.put("category_id", req.getCategoryId());
            payload.put("title", req.getTitle());
            payload.put("description", req.getDescription());
            payload.put("impact_description", req.getImpactDescription());
            payload.put("urgency_description", req.getUrgencyDescription());
            payload.put("location", req.getLocation());
            payload.put("contact", req.getContact());
            payload.put("asset_id", req.getAssetId());
            draft.setPayloadJson(objectMapper.writeValueAsString(payload));
        } catch (JsonProcessingException ex) {
            throw new BizException(ErrorCode.PARAM_INVALID, "Invalid draft payload");
        }
        draft.setLastSavedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        draft.setExpiresAt(draft.getLastSavedAt().plusDays(7));
    }
}
