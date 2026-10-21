package com.itticket.ticket.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.DecideDispatchRequest;
import com.itticket.ticket.entity.ExceptionQueue;
import com.itticket.ticket.mapper.ExceptionQueueMapper;
import com.itticket.ticket.service.ExceptionQueueService;
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
 * 异常队列接口（PRD §4）—— 仅平台管理员可查看与处理。
 * 异常来源：NOTIFICATION / AI / ASSIGNMENT / SCHEDULER / SYSTEM。
 * 进入即通知平台管理员；处理时限与升级属管理侧配置。
 *
 * <p>认领（claim）与裁决（decide）为 PRD §18.2「异常需可审计、可干预」提供闭环：
 * 认领占用待办，裁决必填原因，两者都要求 PLATFORM_ADMIN。
 */
@RestController
@RequestMapping("/api/v1/exceptions")
@RequiredArgsConstructor
public class ExceptionQueueController {

    private final ExceptionQueueMapper exceptionQueueMapper;
    private final ExceptionQueueService exceptionQueueService;

    /** 异常队列分页查询（默认按创建时间倒序，未处理优先） */
    @GetMapping
    public Result<Map<String, Object>> list(
            @RequestParam(required = false) String source,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int pageSize) {
        UserContext.checkRole(UserContext.get(), "PLATFORM_ADMIN");
        QueryWrapper<ExceptionQueue> qw = new QueryWrapper<ExceptionQueue>().eq("object_type", "TICKET");
        if (source != null && !source.isBlank()) qw.eq("reason_code", source);
        if (status != null && !status.isBlank()) qw.eq("status", status);
        qw.orderByAsc("status").orderByDesc("created_at");
        Page<ExceptionQueue> result = exceptionQueueMapper.selectPage(new Page<>(page, pageSize), qw);
        Map<String, Object> data = new HashMap<>();
        data.put("list", result.getRecords());
        data.put("total", result.getTotal());
        data.put("page", page);
        data.put("pageSize", pageSize);
        return Result.ok(data);
    }

    /** 未处理异常数量（管理员工作台角标） */
    @GetMapping("/pending-count")
    public Result<Long> pendingCount() {
        UserContext.checkRole(UserContext.get(), "PLATFORM_ADMIN");
        Long cnt = exceptionQueueMapper.selectCount(new QueryWrapper<ExceptionQueue>()
                .eq("object_type", "TICKET").eq("status", "OPEN"));
        return Result.ok(cnt == null ? 0 : cnt);
    }

    /** 认领异常 —— OPEN → 由当前管理员独占处理 */
    @PostMapping("/{exceptionId}/claim")
    public Result<Void> claim(@PathVariable String exceptionId) {
        String adminId = UserContext.get().getUserId();
        UserContext.checkRole(UserContext.get(), "PLATFORM_ADMIN");
        if (exceptionQueueService.claim(exceptionId, adminId) == null) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION,
                    "异常不存在、已结案或已被他人认领");
        }
        return Result.ok();
    }

    /**
     * 裁决异常 —— 结案必填原因（PRD §18.2 可审计）。
     *
     * <p>resolution：RESOLVED（已处理）或 DISMISSED（判定无需处理）。
     * 未认领或认领人不符时明确失败，不做静默结案。
     */
    @PostMapping("/{exceptionId}/decide")
    public Result<Void> decide(
            @PathVariable String exceptionId,
            @RequestBody DecideDispatchRequest body) {
        String adminId = UserContext.get().getUserId();
        UserContext.checkRole(UserContext.get(), "PLATFORM_ADMIN");
        if (body.reason() == null || body.reason().isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "异常结案必须填写原因");
        }
        String resolution = body.resolution();
        boolean dismissed = ExceptionQueueService.STATUS_DISMISSED.equals(resolution)
                || !body.approve();
        if (!exceptionQueueService.settle(exceptionId, adminId, body.reason(), dismissed)) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION,
                    "异常不存在、已结案或非本人认领，无法结案");
        }
        return Result.ok();
    }
}