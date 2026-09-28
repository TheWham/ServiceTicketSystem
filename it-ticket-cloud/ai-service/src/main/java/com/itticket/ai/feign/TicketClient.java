package com.itticket.ai.feign;

import com.itticket.common.api.Result;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;
import java.util.Map;

/** 调用 ticket-service 的内部接口(经 Nacos 服务发现直连,不经网关) */
@FeignClient(name = "ticket-service", contextId = "ticketClient")
public interface TicketClient {

    /**
     * 内部建单(人工客服转工单)
     * body 字段(snake_case):creator_id/title/category/description/priority/client_token
     * @return data.ticket_id 为工单号
     */
    @PostMapping("/api/internal/tickets")
    Result<Map<String, Object>> createTicket(@RequestBody Map<String, Object> request);

    /**
     * 拉取已完成工单(知识回流)
     * @param since 只取 solved_at 晚于该时间的(ISO 格式),可为空
     */
    @GetMapping("/api/internal/tickets/solved")
    Result<List<SolvedTicket>> solvedTickets(@RequestParam(value = "since", required = false) String since,
                                             @RequestParam(value = "limit", defaultValue = "100") int limit);

    /** 已完成工单摘要(与 ticket-service 的 SolvedTicketVO 对应,JSON 为 snake_case) */
    @com.fasterxml.jackson.databind.annotation.JsonNaming(
            com.fasterxml.jackson.databind.PropertyNamingStrategies.SnakeCaseStrategy.class)
    record SolvedTicket(String ticketId, String title, String category, String description,
                        String solutionRemark, String solvedAt) {
    }
}
