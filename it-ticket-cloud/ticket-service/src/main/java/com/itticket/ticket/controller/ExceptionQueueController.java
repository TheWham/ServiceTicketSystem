package com.itticket.ticket.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.common.api.Result;
import com.itticket.ticket.entity.ExceptionQueue;
import com.itticket.ticket.mapper.ExceptionQueueMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * 异常队列查询接口（PRD §4）—— 仅平台管理员可查看。
 * 异常来源：NOTIFICATION / AI / ASSIGNMENT / SCHEDULER / SYSTEM。
 * 进入即通知平台管理员；处理时限与升级属管理侧配置。
 */
@RestController
@RequestMapping("/api/exceptions")
@RequiredArgsConstructor
public class ExceptionQueueController {

    private final ExceptionQueueMapper exceptionQueueMapper;

    /** 异常队列分页查询（默认按创建时间倒序，未处理优先） */
    @GetMapping
    public Result<Map<String, Object>> list(
            @RequestParam(required = false) String source,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int pageSize) {
        QueryWrapper<ExceptionQueue> qw = new QueryWrapper<>();
        if (source != null && !source.isBlank()) qw.eq("source", source);
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
        Long cnt = exceptionQueueMapper.selectCount(new QueryWrapper<ExceptionQueue>()
                .eq("status", "OPEN"));
        return Result.ok(cnt == null ? 0 : cnt);
    }
}
