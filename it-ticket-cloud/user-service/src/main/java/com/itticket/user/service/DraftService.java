package com.itticket.user.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
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

    public DraftVO getDraft(String userId) {
        TicketDraft draft = draftMapper.selectOne(new QueryWrapper<TicketDraft>().eq("user_id", userId));
        if (draft == null) {
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
        TicketDraft existing = draftMapper.selectOne(new QueryWrapper<TicketDraft>().eq("user_id", userId));
        if (existing == null) {
            TicketDraft draft = new TicketDraft();
            draft.setUserId(userId);
            applyFields(draft, req);
            draft.setUpdatedAt(LocalDateTime.now());
            draftMapper.insert(draft);
        } else {
            applyFields(existing, req);
            existing.setUpdatedAt(LocalDateTime.now());
            draftMapper.updateById(existing);
        }
    }

    public void deleteDraft(String userId) {
        draftMapper.delete(new QueryWrapper<TicketDraft>().eq("user_id", userId));
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
    }
}
