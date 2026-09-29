package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.ticket.entity.ExceptionQueue;
import com.itticket.ticket.mapper.ExceptionQueueMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
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
                .eq("status", "OPEN"));
        if (exist != null && exist > 0) {
            log.debug("[EXCEPTION] 已存在 OPEN 异常，跳过: {}", bizType, bizId, exceptionType);
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
        e.setStatus("OPEN");
        e.setCreatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        e.setUpdatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        exceptionQueueMapper.insert(e);
        log.warn("[EXCEPTION] 异常入队: [{}] {} {} - {}", exceptionType, bizType, bizId, title);
        return true;
    }
}
