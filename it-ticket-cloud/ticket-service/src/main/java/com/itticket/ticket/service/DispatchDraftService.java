package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.api.Result;
import com.itticket.common.user.UserInfo;
import com.itticket.ticket.dto.DispatchDraftPayload;
import com.itticket.ticket.entity.DispatchDraft;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.DispatchDraftMapper;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.mapper.TicketMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;

/**
 * 派单草案服务 —— 写操作门禁（Human-in-the-Loop）。
 *
 * <p>需求依据：docs/IT服务工单系统-需求归因文档.md:50
 * 「强制 Human-in-the-Loop 人机确认（派单草案主管点击才生效）；派单幂等防重与失败补偿」。
 *
 * <p>机制（对齐 Day18 讲义「写操作前刹车片」三要素）：
 * <ol>
 *   <li><b>刹车片</b>：路由不再直接写 assignment，只产出 PENDING 草案，工单保持 NEW；</li>
 *   <li><b>状态持久化挂起</b>：草案落库（非内存），进程重启不丢；</li>
 *   <li><b>凭证 + 失效</b>：logical idempotency_key 保证同一轮路由只落一份草案，
 *       expires_at 到期即失效（对应讲义 Token 超时语义）。</li>
 *   <li><b>恢复</b>：审批人确认后调 {@link RoutingService#assign} 真正落库；驳回则工单回到可重新路由状态。</li>
 * </ol>
 *
 * <p>审批人取 PLATFORM_ADMIN：PRD-Ultimate §98「系统不设置主管和坐台客服角色」，
 * 需求归因文档里的「主管确认」为非正式表述，角色以 PRD 定义为准。
 *
 * <p>红线：AI 与系统自身都不能直接落分派，必须由人点击才生效
 * （docs/specs/02-ai-api-json-schema.md:18）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DispatchDraftService {

    private final DispatchDraftMapper dispatchDraftMapper;
    private final TicketFlowLogMapper flowLogMapper;
    private final NotificationService notificationService;
    private final ExceptionQueueService exceptionQueueService;
    private final UserClient userClient;
    private final ObjectMapper objectMapper;

    /** 草案有效期（默认 30 分钟，对齐讲义「专属 Token 含超时失效」）。 */
    @Value("${ticket.dispatch-draft.ttl-minutes:30}")
    private long ttlMinutes = 30;

    /**
     * 生成待确认的派单草案（幂等）。
     *
     * <p>同一工单同一轮路由只落一份：DB 生成列唯一键 uk_dispatch_draft_pending 保证
     * 「同一工单同时只有一份 PENDING」，uk_dispatch_draft_idem 保证「同一轮只插一次」。
     * 已存在 PENDING 草案时直接返回既有草案，不重复通知审批人。
     *
     * @param idempotencyKey 本轮路由的幂等键（调用方给出，重复调用视为同一轮）
     * @return 草案；工单已终态或不满足挂起条件时返回 null
     */
    @Transactional
    public DispatchDraft createDraft(Ticket ticket, String engineerId, String idempotencyKey, String selectionNote) {
        if (ticket == null || ticket.getStatus() == null || ticket.getStatus().isTerminal()) {
            return null;
        }
        // 已有待确认草案：不重复生成（幂等防重 —— 派单幂等防重与失败补偿）
        DispatchDraft existing = findPendingByTicket(ticket.getTicketId());
        if (existing != null) {
            log.info("[派单草案] 已存在待确认草案，跳过重复生成: {}", existing.getDraftId());
            return existing;
        }

        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        DispatchDraft draft = new DispatchDraft();
        draft.setDraftId("DD" + UUID.randomUUID().toString().replace("-", "").substring(0, 30));
        draft.setTicketId(ticket.getTicketId());
        draft.setStatus(DispatchDraft.STATUS_PENDING);
        draft.setEngineerId(engineerId);
        draft.setEngineerName(resolveEngineerName(engineerId));
        draft.setPriority(ticket.getPriority());
        draft.setCategoryId(ticket.getCategoryId());
        draft.setSelectionNote(selectionNote);
        draft.setIdempotencyKey(idempotencyKey);
        draft.setVersion(0L);
        draft.setExpiresAt(now.plusMinutes(ttlMinutes));
        draft.setCreatedAt(now);
        draft.setUpdatedAt(now);
        draft.setPayloadJson(buildPayload(ticket, draft));

        try {
            dispatchDraftMapper.insert(draft);
        } catch (DuplicateKeyException e) {
            // 并发下另一个线程已落草案：返回既有那份，不产生第二份
            DispatchDraft raced = findPendingByTicket(ticket.getTicketId());
            log.warn("[派单草案] 并发生成冲突，复用既有草案: {}", raced == null ? "-" : raced.getDraftId());
            return raced;
        }

        insertFlowLog(ticket.getTicketId(), ticket.getStatus().getValue(), ticket.getStatus().getValue(),
                "TICKET_DISPATCH_DRAFT_CREATED", "SYSTEM",
                "派单草案待确认: " + engineerId + " (草案 " + draft.getDraftId() + ")");
        notifyApprovers(draft);
        log.info("[派单草案] 已挂起待确认: {} -> {} 草案={}", ticket.getTicketId(), engineerId, draft.getDraftId());
        return draft;
    }

    /** 查该工单当前待确认草案。 */
    public DispatchDraft findPendingByTicket(String ticketId) {
        return dispatchDraftMapper.selectOne(new QueryWrapper<DispatchDraft>()
                .eq("ticket_id", ticketId)
                .eq("status", DispatchDraft.STATUS_PENDING)
                .orderByDesc("created_at")
                .last("limit 1"));
    }

    /** 待确认草案列表（审批人待办）。 */
    public List<DispatchDraft> listPending() {
        return dispatchDraftMapper.selectList(new QueryWrapper<DispatchDraft>()
                .eq("status", DispatchDraft.STATUS_PENDING)
                .orderByAsc("created_at"));
    }

    public DispatchDraft get(String draftId) {
        DispatchDraft d = dispatchDraftMapper.selectById(draftId);
        if (d == null) {
            throw new BizException(ErrorCode.TICKET_NOT_FOUND, "派单草案不存在");
        }
        return d;
    }

    /**
     * 还原草案的结构化载荷（审批人核对用）。
     *
     * <p>读的是落库时的快照 payload_json，而不是按当前数据重算 ——
     * 审批人看到的必须是他裁决那一刻的依据，事后人员/负载变化不得改写历史草案。
     */
    public DispatchDraftPayload toPayload(DispatchDraft draft) {
        if (draft.getPayloadJson() == null || draft.getPayloadJson().isBlank()) {
            throw new BizException(ErrorCode.SYSTEM_ERROR, "派单草案缺少载荷快照");
        }
        try {
            return objectMapper.readValue(draft.getPayloadJson(), DispatchDraftPayload.class);
        } catch (JsonProcessingException e) {
            throw new BizException(ErrorCode.SYSTEM_ERROR, "派单草案载荷解析失败");
        }
    }

    /**
     * 认领草案：审批人先认领再裁决，避免两人同时裁决同一条。
     * 认领失败（已被他人认领 / 已裁决）必须明确失败，不静默放行。
     */
    @Transactional
    public DispatchDraft claim(String draftId, String operatorId) {
        DispatchDraft draft = get(draftId);
        if (!DispatchDraft.STATUS_PENDING.equals(draft.getStatus())) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, "草案已裁决，无法认领");
        }
        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        int rows = dispatchDraftMapper.update(null, new UpdateWrapper<DispatchDraft>()
                .eq("draft_id", draftId)
                .eq("status", DispatchDraft.STATUS_PENDING)
                .isNull("claimed_by")
                .set("claimed_by", operatorId)
                .set("claimed_at", now)
                .set("updated_at", now));
        if (rows != 1) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, "草案已被他人认领");
        }
        // 复核失效：认领瞬间已过期则直接置 EXPIRED，不允许批准一份失效草案
        DispatchDraft fresh = dispatchDraftMapper.selectById(draftId);
        if (fresh.getExpiresAt() != null && fresh.getExpiresAt().isBefore(now)) {
            expire(draftId, "认领时已超时失效");
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, "草案已超时失效，请重新路由");
        }
        log.info("[派单草案] 已认领: {} by {}", draftId, operatorId);
        return fresh;
    }

    /**
     * 裁决草案 —— 门禁的核心状态机，只负责草案自身的流转。
     *
     * <p>approve：草案置 APPROVED；reject：草案置 REJECTED（原因必填）。
     * <b>放行后的实际分派由调用方在同一事务内执行</b>
     * （{@code TicketService.confirmDispatch} 调 {@code RoutingService.assign}），
     * 这样门禁与工单生命周期各自单一职责，且不产生服务间循环依赖。
     *
     * <p>并发与幂等：裁决用 status=PENDING 的条件更新做乐观锁，重复裁决明确失败，
     * 不会二次分派（派单幂等防重）。
     *
     * @return 裁决后的草案实体
     */
    @Transactional
    public DispatchDraft decide(String draftId, String reason, boolean approve, String operatorId,
                                java.util.function.Consumer<String> onApproved) {
        DispatchDraft draft = get(draftId);
        if (!DispatchDraft.STATUS_PENDING.equals(draft.getStatus())) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, "草案已裁决，不可重复操作");
        }
        if (!approve && (reason == null || reason.isBlank())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "驳回必须说明原因");
        }
        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        if (draft.getExpiresAt() != null && draft.getExpiresAt().isBefore(now)) {
            expire(draftId, "裁决时已超时失效");
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, "草案已超时失效，请重新路由");
        }

        String target = approve ? DispatchDraft.STATUS_APPROVED : DispatchDraft.STATUS_REJECTED;
        int rows = dispatchDraftMapper.update(null, new UpdateWrapper<DispatchDraft>()
                .eq("draft_id", draftId)
                .eq("status", DispatchDraft.STATUS_PENDING)
                .set("status", target)
                .set("resolved_by", operatorId)
                .set("resolved_at", now)
                .set("reason", reason)
                .set("updated_at", now));
        if (rows != 1) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, "草案已被他人裁决");
        }

        if (!approve) {
            insertFlowLog(draft.getTicketId(), "NEW", "NEW", "TICKET_DISPATCH_REJECTED", operatorId,
                    "派单草案驳回: " + reason + " (草案 " + draftId + ")");
            notifyApproversResult(draft, "派单草案被驳回，工单保持待路由");
            log.info("[派单草案] 已驳回: {} by {} 原因={}", draftId, operatorId, reason);
        } else {
            // 放行：在本事务内执行真正的分派。回调失败（如工单已离开 NEW）会抛出，
            // 整笔事务回滚，草案状态一并撤销 —— 不留「已批准但没分派」的半截状态。
            onApproved.accept(draftId);
            log.info("[派单草案] 已批准并放行分派: {} by {}", draftId, operatorId);
        }
        return dispatchDraftMapper.selectById(draftId);
    }

    /**
     * 失效扫描（每 1 分钟）：PENDING 且 expires_at 已过 → EXPIRED + 通知审批人重新路由。
     * 对应讲义的「Token 超时失效」，以及需求归因文档的「失败补偿」。
     */
    @Scheduled(fixedDelay = 60000, initialDelay = 75000)
    @Transactional
    public void scanExpired() {
        List<DispatchDraft> expired = dispatchDraftMapper.selectList(new QueryWrapper<DispatchDraft>()
                .eq("status", DispatchDraft.STATUS_PENDING)
                .le("expires_at", LocalDateTime.now(ZoneOffset.UTC)));
        for (DispatchDraft d : expired) {
            try {
                expire(d.getDraftId(), "草案超时未确认，自动失效");
            } catch (Exception e) {
                log.error("[派单草案] 失效处理异常: " + d.getDraftId(), e);
            }
        }
    }

    /** 将草案置为 EXPIRED（条件更新，已裁决的不会被覆盖）。 */
    @Transactional
    public boolean expire(String draftId, String reason) {
        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        int rows = dispatchDraftMapper.update(null, new UpdateWrapper<DispatchDraft>()
                .eq("draft_id", draftId)
                .eq("status", DispatchDraft.STATUS_PENDING)
                .set("status", DispatchDraft.STATUS_EXPIRED)
                .set("resolved_at", now)
                .set("reason", reason)
                .set("updated_at", now));
        if (rows != 1) {
            return false;
        }
        DispatchDraft d = dispatchDraftMapper.selectById(draftId);
        insertFlowLog(d.getTicketId(), "NEW", "NEW", "TICKET_DISPATCH_DRAFT_EXPIRED", "SYSTEM",
                "派单草案超时失效: " + draftId);
        notifyApproversResult(d, "派单草案已超时失效，工单仍待路由，请重新处理");
        log.warn("[派单草案] 已失效: {} 原因={}", draftId, reason);
        return true;
    }

    // ---------------- 内部 ----------------

    private String buildPayload(Ticket ticket, DispatchDraft draft) {
        DispatchDraftPayload payload = new DispatchDraftPayload();
        payload.setDraftId(draft.getDraftId());
        payload.setTicketId(ticket.getTicketId());
        payload.setTitle(ticket.getTitle());
        payload.setPriority(ticket.getPriority());
        payload.setCategoryId(ticket.getCategoryId());
        payload.setProposedEngineerId(draft.getEngineerId());
        payload.setProposedEngineerName(draft.getEngineerName());
        payload.setSelectionNote(draft.getSelectionNote());
        payload.setExpiresAt(draft.getExpiresAt());
        payload.setGeneratedAt(draft.getCreatedAt());
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (JsonProcessingException e) {
            // 载荷无法序列化属于编码缺陷，必须显式失败而不是写一份空载荷
            throw new BizException(ErrorCode.SYSTEM_ERROR, "派单草案载荷序列化失败");
        }
    }

    /** 通知所有平台管理员有待确认草案（PRD §14.2 查看≠行动，带待办入口）。 */
    private void notifyApprovers(DispatchDraft draft) {
        try {
            List<UserInfo> admins = admins();
            for (UserInfo admin : admins) {
                notificationService.sendInbox("DISPATCH_DRAFT_PENDING:" + draft.getDraftId(),
                        admin.getUserId(),
                        "【派单待确认】" + draft.getEngineerId(),
                        "工单 " + draft.getTicketId() + " 的派单草案待确认，截止 "
                                + draft.getExpiresAt() + "，逾期自动失效。",
                        "/supervisor?draft=" + draft.getDraftId());
            }
            if (admins.isEmpty()) {
                log.warn("[派单草案] 无平台管理员可通知（草案仍可在待办列表处理）: {}", draft.getDraftId());
            }
        } catch (Exception e) {
            // 通知失败落异常队列做补偿，但草案本身已落库可用，不阻断主流程
            log.error("[派单草案] 通知审批人失败（草案已落库，不阻断）: {}", e.getMessage());
            exceptionQueueService.raise("DISPATCH_DRAFT", draft.getDraftId(),
                    ExceptionQueueService.TYPE_NOTIFY_FAILED,
                    "派单草案通知审批人失败", e.getMessage(), draft.getPriority());
        }
    }

    private void notifyApproversResult(DispatchDraft draft, String message) {
        try {
            for (UserInfo admin : admins()) {
                notificationService.sendInbox("DISPATCH_DRAFT_RESULT:" + draft.getDraftId() + ":" + draft.getStatus(),
                        admin.getUserId(), "【派单草案】" + draft.getTicketId(), message,
                        "/supervisor?draft=" + draft.getDraftId());
            }
        } catch (Exception e) {
            log.error("[派单草案] 通知结果失败（不阻断）: {}", e.getMessage());
        }
    }

    private List<UserInfo> admins() {
        Result<List<UserInfo>> res = userClient.admins();
        return (res != null && res.getData() != null) ? res.getData() : List.of();
    }

    private String resolveEngineerName(String engineerId) {
        try {
            Result<List<UserInfo>> res = userClient.engineers();
            if (res != null && res.getData() != null) {
                for (UserInfo u : res.getData()) {
                    if (engineerId.equals(u.getUserId())) {
                        return u.getName();
                    }
                }
            }
        } catch (Exception e) {
            log.warn("[派单草案] 查询工程师姓名失败（草案仍可生成）: {}", e.getMessage());
        }
        return null;
    }

    private void insertFlowLog(String ticketId, String fromStatus, String toStatus,
                               String eventCode, String operatorId, String remark) {
        TicketFlowLog flow = new TicketFlowLog();
        flow.setTicketId(ticketId);
        flow.setFromStatus(fromStatus);
        flow.setToStatus(toStatus);
        flow.setEvent(eventCode);
        flow.setOperatorId(operatorId);
        flow.setReason(remark);
        flow.setOccurredAt(LocalDateTime.now(ZoneOffset.UTC));
        flowLogMapper.insert(flow);
    }
}