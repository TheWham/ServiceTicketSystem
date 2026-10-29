package com.itticket.ticket.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.DecideDispatchRequest;
import com.itticket.ticket.dto.DispatchDraftPayload;
import com.itticket.ticket.entity.DispatchDraft;
import com.itticket.ticket.mapper.DispatchDraftMapper;
import com.itticket.ticket.service.DispatchDraftService;
import com.itticket.ticket.service.TicketService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * 派单草案（HITL 写操作门禁）接口 —— 仅平台管理员可查看与裁决。
 *
 * <p>需求依据 docs/IT服务工单系统-需求归因文档.md:50「强制 Human-in-the-Loop 人机确认
 * （派单草案主管点击才生效）；派单幂等防重与失败补偿」。
 *
 * <p>审批角色：PRD §「系统不设置主管和坐台客服角色」，故审批人取 PLATFORM_ADMIN。
 *
 * <p>端点语义（对齐讲义第三篇「写操作刹车片」四步）：
 * GET    /api/v1/dispatch-drafts             待办列表（挂起态，供管理员认领前浏览）
 * GET    /api/v1/dispatch-drafts/{id}        草案详情（含结构化载荷，供审批人核对）
 * POST   /api/v1/dispatch-drafts/{id}/claim  认领，占用待办避免并行裁决
 * POST   /api/v1/dispatch-drafts/{id}/decide 裁决，approve 才真正放行分派
 */
@RestController
@RequestMapping("/api/v1/dispatch-drafts")
@RequiredArgsConstructor
public class DispatchDraftController {

    private final DispatchDraftMapper dispatchDraftMapper;
    private final DispatchDraftService dispatchDraftService;
    private final TicketService ticketService;

    /** 待确认派单草案列表（管理员待办） */
    @GetMapping
    public Result<Map<String, Object>> list(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String ticketId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int pageSize) {
        UserContext.checkRole(UserContext.get(), "PLATFORM_ADMIN");
        QueryWrapper<DispatchDraft> qw = new QueryWrapper<>();
        qw.eq("status", status == null || status.isBlank()
                ? DispatchDraft.STATUS_PENDING : status);
        if (ticketId != null && !ticketId.isBlank()) {
            qw.eq("ticket_id", ticketId);
        }
        qw.orderByAsc("expires_at").orderByDesc("created_at");
        Page<DispatchDraft> result = dispatchDraftMapper.selectPage(new Page<>(page, pageSize), qw);
        Map<String, Object> data = new HashMap<>();
        data.put("list", result.getRecords());
        data.put("total", result.getTotal());
        data.put("page", page);
        data.put("pageSize", pageSize);
        return Result.ok(data);
    }

    /** 草案详情 —— 审批人核对载荷后再裁决 */
    @GetMapping("/{draftId}")
    public Result<DispatchDraftPayload> detail(@PathVariable String draftId) {
        UserContext.checkRole(UserContext.get(), "PLATFORM_ADMIN");
        DispatchDraft d = dispatchDraftService.get(draftId);
        return Result.ok(dispatchDraftService.toPayload(d));
    }

    /** 认领草案 —— 同一草案同一时刻只允许一个管理员裁决 */
    @PostMapping("/{draftId}/claim")
    public Result<Void> claim(@PathVariable String draftId) {
        String adminId = UserContext.get().getUserId();
        UserContext.checkRole(UserContext.get(), "PLATFORM_ADMIN");
        dispatchDraftService.claim(draftId, adminId);
        return Result.ok();
    }

    /**
     * 裁决草案 —— 门禁放行点。
     *
     * <p>approve：先执行分派（TicketService.confirmDispatch），工单 NEW → ASSIGNED；
     * reject：仅驳回草案，工单保持 NEW，由管理员改派或重新路由。
     * 两者都在 DispatchDraftService.decide 的同一事务内完成。
     */
    @PostMapping("/{draftId}/decide")
    public Result<DispatchDraftPayload> decide(
            @PathVariable String draftId,
            @RequestBody DecideDispatchRequest body) {
        String adminId = UserContext.get().getUserId();
        UserContext.checkRole(UserContext.get(), "PLATFORM_ADMIN");
        DispatchDraft d = dispatchDraftService.decide(
                draftId, body.reason(), body.approve(), adminId,
                ticketService::confirmDispatch);
        return Result.ok(dispatchDraftService.toPayload(d));
    }
}