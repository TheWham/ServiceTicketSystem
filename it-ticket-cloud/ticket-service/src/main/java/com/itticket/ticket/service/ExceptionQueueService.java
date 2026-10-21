package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.ticket.entity.ExceptionQueue;
import com.itticket.ticket.mapper.ExceptionQueueMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.UUID;

/**
 * 异常队列服务 —— PRD §4 / §18.2。
 * 无人响应 / 路由失败 / 长期挂起 / 通知失败 / 超限 统一落库，
 * 平台管理员在专用队列处理（可审计、可干预、原因必填）。
 * 同一业务同一类型的 OPEN 异常只保留一条（避免重复刷队列）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ExceptionQueueService {

    public static final String TYPE_NO_RESPONSE = "NO_RESPONSE";
    public static final String TYPE_ROUTE_FAILED = "ROUTE_FAILED";
    public static final String TYPE_LONG_PENDING = "LONG_PENDING";
    public static final String TYPE_NOTIFY_FAILED = "NOTIFY_FAILED";
    public static final String TYPE_LIMIT_EXCEEDED = "LIMIT_EXCEEDED";

    public static final String STATUS_OPEN = "OPEN";
    public static final String STATUS_RESOLVED = "RESOLVED";
    public static final String STATUS_DISMISSED = "DISMISSED";

    private final ExceptionQueueMapper exceptionQueueMapper;

    /**
     * 落库异常（幂等：同 bizType+bizId+exceptionType 的 OPEN 记录只保留一条）
     *
     * @return true 新插入 / false 已存在 OPEN 记录（跳过）
     */
    public boolean raise(String bizType, String bizId, String exceptionType,
                         String title, String detail, String priority) {
        Long exist = exceptionQueueMapper.selectCount(new QueryWrapper<ExceptionQueue>()
                .eq("object_type", bizType)
                .eq("object_id", bizId)
                .eq("reason_code", exceptionType)
                .eq("status", STATUS_OPEN));
        if (exist != null && exist > 0) {
            log.debug("[EXCEPTION] 已存在 OPEN 异常，跳过: {}/{} {}", bizType, bizId, exceptionType);
            return false;
        }
        ExceptionQueue e = new ExceptionQueue();
        e.setExceptionId("EX" + UUID.randomUUID().toString().replace("-", "").substring(0, 30));
        e.setBizType(bizType);
        e.setBizId(bizId);
        e.setExceptionType(exceptionType);
        e.setTitle(title);
        e.setDetail(detail);
        e.setPriority(priority);
        e.setStatus(STATUS_OPEN);
        e.setCreatedAt(LocalDateTime.now(ZoneOffset.UTC));
        e.setUpdatedAt(LocalDateTime.now(ZoneOffset.UTC));
        exceptionQueueMapper.insert(e);
        log.warn("[EXCEPTION] 异常入队: [{}] {} {} - {}", exceptionType, bizType, bizId, title);
        return true;
    }

    /**
     * 认领异常（OPEN → 由操作人独占）。
     *
     * <p>认领是状态占用，用于多人同时处理队列时避免重复处置。已认领或已结案的异常
     * 不可再认领 —— 必须明确失败而不是静默覆盖，否则两个管理员会各自以为持有处置权。
     *
     * @return 认领后的实体；异常不存在或不可认领时返回 null
     */
    public ExceptionQueue claim(String exceptionId, String operatorId) {
        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        int rows = exceptionQueueMapper.update(null, new UpdateWrapper<ExceptionQueue>()
                .eq("exception_id", exceptionId)
                .eq("status", STATUS_OPEN)
                .isNull("claimed_by")
                .set("claimed_by", operatorId)
                .set("claimed_at", now)
                .set("updated_at", now));
        if (rows != 1) {
            log.warn("[EXCEPTION] 认领失败（不存在/已结案/已被认领）: {} by {}", exceptionId, operatorId);
            return null;
        }
        log.info("[EXCEPTION] 已认领: {} by {}", exceptionId, operatorId);
        return exceptionQueueMapper.selectById(exceptionId);
    }

    /**
     * 结案异常：置为终态并记录处置人、处置原因（原因必填，PRD §4/§18.2 可审计）。
     *
     * @param dismissed true 表示不成立/忽略（DISMISSED），false 表示已处置（RESOLVED）
     * @return 是否结案成功（仅 OPEN 且认领人一致时允许）
     */
    public boolean settle(String exceptionId, String operatorId, String reason, boolean dismissed) {
        if (reason == null || reason.isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "异常处理原因必填");
        }
        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        int rows = exceptionQueueMapper.update(null, new UpdateWrapper<ExceptionQueue>()
                .eq("exception_id", exceptionId)
                .eq("status", STATUS_OPEN)
                .eq("claimed_by", operatorId)
                .set("status", dismissed ? STATUS_DISMISSED : STATUS_RESOLVED)
                .set("resolved_by", operatorId)
                .set("resolved_at", now)
                .set("reason", reason)
                .set("updated_at", now));
        if (rows != 1) {
            log.warn("[EXCEPTION] 结案失败（未认领/非 OPEN/认领人不符）: {} by {}", exceptionId, operatorId);
            return false;
        }
        log.info("[EXCEPTION] 已结案: {} by {} -> {}", exceptionId, operatorId,
                dismissed ? STATUS_DISMISSED : STATUS_RESOLVED);
        return true;
    }
}