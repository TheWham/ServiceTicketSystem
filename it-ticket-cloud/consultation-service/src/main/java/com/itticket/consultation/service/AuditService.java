package com.itticket.consultation.service;

import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.entity.AuditLog;
import com.itticket.consultation.mapper.AuditLogMapper;
import com.itticket.consultation.support.Ids;
import com.itticket.consultation.support.Json;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 审计写入(PRD 23 / DM-004)。只追加,任何角色不得删除(SM-ROLE-001)。
 *
 * <p>before/after 只记录状态投影字段,不记录聊天正文、知识正文或令牌(RD-013)。
 */
@Service
@RequiredArgsConstructor
public class AuditService {

    public static final String OBJECT_CONSULTATION = "CONSULTATION";

    private final AuditLogMapper auditLogMapper;

    public void record(String actorId, String action, String objectType, String objectId,
                       Map<String, Object> before, Map<String, Object> after, String reason) {
        LocalDateTime now = Times.nowUtc();
        AuditLog log = new AuditLog();
        log.setAuditId(Ids.auditId());
        log.setActorId(actorId);
        log.setAction(action);
        log.setObjectType(objectType);
        log.setObjectId(objectId);
        log.setBeforeJson(before == null ? null : Json.write(before));
        log.setAfterJson(after == null ? null : Json.write(after));
        log.setReason(reason);
        log.setRequestId(RequestContext.get());
        log.setOccurredAt(now);
        log.setCreatedAt(now);
        log.setUpdatedAt(now);
        auditLogMapper.insert(log);
    }
}
