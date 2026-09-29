package com.itticket.ticket.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.common.api.Result;
import com.itticket.ticket.entity.SlaInstance;
import com.itticket.ticket.mapper.SlaInstanceMapper;
import com.itticket.ticket.service.WorkCalendarService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * SLA 计时查询 —— 前端工单卡片倒计时徽章 + 详情页完整计时。
 * 返回目标时刻/已用工时/状态，倒计时由前端按 targetAt 轮询计算（工作时长口径）。
 */
@RestController
@RequestMapping("/api/v1/sla")
@RequiredArgsConstructor
public class SlaController {

    private final SlaInstanceMapper slaInstanceMapper;
    private final WorkCalendarService workCalendarService;

    /**
     * 查工单当前 SLA 实例（完成类 COMPLETION 为主）。
     * 返回：目标时刻、已用工时秒、状态、违约时间、剩余工作秒（服务端基准，避免前端时钟漂移）。
     */
    @GetMapping("/{ticketId}")
    public Result<Map<String, Object>> getByTicket(@PathVariable String ticketId) {
        SlaInstance sla = slaInstanceMapper.selectOne(new QueryWrapper<SlaInstance>()
                .eq("biz_type", "TICKET").eq("biz_id", ticketId).eq("sla_type", "TICKET_COMPLETION")
                .orderByDesc("created_at").last("LIMIT 1"));
        if (sla == null) {
            return Result.ok(null); // 无 SLA（如取消的工单）——前端不显示计时
        }
        Map<String, Object> data = new HashMap<>();
        data.put("sla_id", sla.getSlaId());
        data.put("ticket_id", sla.getTicketId());
        data.put("priority_snapshot", sla.getPrioritySnapshot());
        data.put("target_at", sla.getTargetAt());
        data.put("elapsed_work_seconds", sla.getElapsedWorkSeconds());
        data.put("paused_seconds", sla.getPausedSeconds());
        data.put("breach_at", sla.getBreachAt());
        data.put("breached_at", sla.getBreachAt());
        data.put("status", sla.getStatus());
        // 服务端基准剩余工作秒（前端以此为起点本地倒计时，避免时钟漂移）
        LocalDateTime now = LocalDateTime.now(java.time.ZoneOffset.UTC);
        long remaining = 0;
        if (sla.getTargetAt() != null && "RUNNING".equals(sla.getStatus())) {
            remaining = workCalendarService.workSecondsBetween(now, sla.getTargetAt());
        }
        data.put("remaining_work_seconds", remaining);
        data.put("server_now", now);
        return Result.ok(data);
    }
}
