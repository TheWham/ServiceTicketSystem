package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.DraftPayload;
import com.itticket.ticket.dto.SaveDraftRequest;
import com.itticket.ticket.entity.TicketDraft;
import com.itticket.ticket.mapper.TicketDraftMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.LinkedHashMap;
import java.util.UUID;

/**
 * 提单草稿(spec 05 saveTicketDraft / SQL-010)。
 *
 * <p>每员工一个活动草稿(uk_active_draft);保存草稿不创建工单,正式提交时从草稿
 * 生成一次性快照(DM-005)。残缺字段也允许保存(PRD 10.4)。draft_id 由客户端持有,
 * 登录过期后重新登录凭同一 id 恢复(PRD 10.4)。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class TicketDraftService {

    /** 草稿默认 7 天过期 */
    private static final long DEFAULT_TTL_DAYS = 7;

    private final TicketDraftMapper draftMapper;
    private final ObjectMapper objectMapper;

    /** 保存(UPSERT by creator):返回服务端实际持有的草稿编号。 */
    public DraftPayload save(UserContext.CurrentUser user, String draftId, SaveDraftRequest request) {
        if (draftId == null || draftId.isBlank() || draftId.length() > 64) {
            throw new BizException(ErrorCode.PARAM_INVALID, "草稿编号无效");
        }
        Map<String, Object> payload = canonicalPayload(request == null ? null : request.getPayload());
        LocalDateTime now = LocalDateTime.now(java.time.ZoneOffset.UTC);
        LocalDateTime expiresAt = (request != null && request.getExpiresAt() != null)
                ? request.getExpiresAt() : now.plusDays(DEFAULT_TTL_DAYS);

        TicketDraft existing = selectByCreator(user.getUserId());
        if (existing == null) {
            TicketDraft draft = new TicketDraft();
            draft.setDraftId(draftId);
            draft.setCreatorId(user.getUserId());
            draft.setPayloadJson(toJson(payload));
            applyLegacyFields(draft, payload);
            draft.setLastSavedAt(now);
            draft.setExpiresAt(expiresAt);
            draft.setVersion(0L);
            draft.setCreatedAt(now);
            draft.setUpdatedAt(now);
            try {
                draftMapper.insert(draft);
            } catch (DuplicateKeyException e) {
                // Another request may already have created this user's active draft.
                TicketDraft concurrent = selectByCreator(user.getUserId());
                if (concurrent != null) {
                    return updateDraft(concurrent, payload, now, expiresAt);
                }
                // A draft id owned by a different user must never be overwritten.
                draft.setDraftId("draft-" + UUID.randomUUID());
                draftMapper.insert(draft);
            }
            return toPayload(draft, payload);
        }
        return updateDraft(existing, payload, now, expiresAt);
    }

    private DraftPayload updateDraft(TicketDraft existing, Map<String, Object> payload,
                                     LocalDateTime now, LocalDateTime expiresAt) {
        existing.setPayloadJson(toJson(payload));
        applyLegacyFields(existing, payload);
        existing.setLastSavedAt(now);
        existing.setExpiresAt(expiresAt);
        existing.setVersion((existing.getVersion() == null ? 0L : existing.getVersion()) + 1);
        existing.setUpdatedAt(now);
        draftMapper.updateById(existing);
        return toPayload(existing, payload);
    }

    /** 读取:编号必须属于本人且未过期;不存在返回 null(前端据此不展示恢复横幅)。 */
    public DraftPayload load(UserContext.CurrentUser user, String draftId) {
        TicketDraft draft = draftMapper.selectById(draftId);
        if (draft == null || !user.getUserId().equals(draft.getCreatorId())) {
            return null;
        }
        if (draft.getExpiresAt() != null && draft.getExpiresAt().isBefore(LocalDateTime.now(java.time.ZoneOffset.UTC))) {
            return null;
        }
        return toPayload(draft, draft.getPayloadJson() == null ? legacyPayload(draft) : fromJson(draft.getPayloadJson()));
    }

    public void delete(UserContext.CurrentUser user, String draftId) {
        TicketDraft draft = draftMapper.selectById(draftId);
        if (draft != null && user.getUserId().equals(draft.getCreatorId())) {
            draftMapper.deleteById(draftId);
        }
    }

    private TicketDraft selectByCreator(String creatorId) {
        return draftMapper.selectOne(new QueryWrapper<TicketDraft>().eq("creator_id", creatorId));
    }

    private DraftPayload toPayload(TicketDraft draft, Map<String, Object> payload) {
        return new DraftPayload(draft.getDraftId(), canonicalPayload(payload), draft.getLastSavedAt() == null ? draft.getUpdatedAt() : draft.getLastSavedAt(), draft.getExpiresAt());
    }

    private Map<String, Object> canonicalPayload(Map<String, Object> source) {
        Map<String, Object> payload = new LinkedHashMap<>(source == null ? Map.of() : source);
        if (!payload.containsKey("ticket_nature") && payload.containsKey("nature")) {
            payload.put("ticket_nature", payload.get("nature"));
        }
        payload.remove("nature");
        return payload;
    }

    /** Keep the original /users/me/draft projection in sync with the JSON draft API. */
    private void applyLegacyFields(TicketDraft draft, Map<String, Object> payload) {
        draft.setTicketNature(text(payload.getOrDefault("ticket_nature", payload.get("nature")), 16));
        draft.setCategoryId(text(payload.get("category_id"), 64));
        draft.setTitle(text(payload.get("title"), 100));
        draft.setDescription(text(payload.get("description"), 5000));
        draft.setImpactDescription(text(payload.get("impact_description"), 2000));
        draft.setUrgencyDescription(text(payload.get("urgency_description"), 2000));
        draft.setLocation(text(payload.get("location"), 255));
        draft.setContact(text(payload.get("contact"), 255));
        draft.setAssetId(text(payload.get("asset_id"), 64));
    }

    private Map<String, Object> legacyPayload(TicketDraft draft) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("ticket_nature", draft.getTicketNature());
        payload.put("category_id", draft.getCategoryId());
        payload.put("title", draft.getTitle());
        payload.put("description", draft.getDescription());
        payload.put("impact_description", draft.getImpactDescription());
        payload.put("urgency_description", draft.getUrgencyDescription());
        payload.put("location", draft.getLocation());
        payload.put("contact", draft.getContact());
        payload.put("asset_id", draft.getAssetId());
        return payload;
    }

    // The JSON payload retains incomplete/overlong form input; old columns are a bounded projection.
    private String text(Object value, int limit) {
        if (value == null) return null;
        String text = String.valueOf(value);
        return text.substring(0, Math.min(text.length(), limit));
    }

    private String toJson(Map<String, Object> payload) {
        try {
            return objectMapper.writeValueAsString(payload == null ? Map.of() : payload);
        } catch (Exception e) {
            log.error("[TICKET] 草稿序列化失败: {}", e.getMessage());
            return "{}";
        }
    }

    private Map<String, Object> fromJson(String json) {
        if (json == null || json.isBlank()) return Map.of();
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {
            });
        } catch (Exception e) {
            return Map.of();
        }
    }
}
