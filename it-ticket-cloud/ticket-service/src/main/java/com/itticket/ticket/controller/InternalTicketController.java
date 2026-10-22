package com.itticket.ticket.controller;

import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.CreateTicketRequest;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.service.TicketService;
import com.itticket.ticket.vo.TicketListVO;
import com.itticket.ticket.vo.TicketVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 内部接口:供其他服务(consultation-service 的 AI 客服工具 / ai-service 的人力客服)查询与创建工单。
 *
 * <p>经服务发现直连,不经网关;主体由 {@code X-User-Id}/{@code X-User-Role} 头透传组装
 * {@link UserContext},归属安全由 {@link TicketService} 保证。工单是 ticket-service 的事实源,
 * 其他服务不得跨库读 ticket 表(架构 8.1),一律走本接口。
 *
 * <p>约定:请求体 snake_case(与 ai-service 既有 TicketClient 一致);响应遵循 {@code {code,msg,data}} 信封。
 */
@RestController
@RequestMapping("/api/internal/tickets")
@RequiredArgsConstructor
public class InternalTicketController {

    private static final int MAX_LIMIT = 50;
    private static final int DEFAULT_LIMIT = 20;

    private final TicketService ticketService;

    /** 查工单列表(按 creator_id / status 过滤),供「查我的工单」工具。
     *
     *  槽位化查询：SQL 骨架在 TicketService.list 的 Wrapper 里固定，这里只收「值槽」——
     *  模型（agent_service 的 query_my_tickets）填参，非法值一律弃用该槽位回默认，
     *  绝不让模型输出参与 SQL 结构。槽位与 agent_service tool_specs() 的参数一一对应。
     */
    @GetMapping
    public Result<List<TicketVO>> list(@RequestParam("creator_id") String creatorId,
                                       @RequestParam(required = false) String status,
                                       @RequestParam(required = false) String category,
                                       @RequestParam(required = false) String created_after,
                                       @RequestParam(defaultValue = "20") int limit) {
        int size = Math.max(1, Math.min(MAX_LIMIT, limit <= 0 ? DEFAULT_LIMIT : limit));
        // status 枚举校验：不在九态里就弃用该槽位（而非报错），模型填错最多查得宽一点
        String validStatus = TicketStatus.fromValue(status) == null ? null : status;
        TicketListVO page = ticketService.list(UserContext.get(), validStatus, category, null, creatorId,
                null, null, null, created_after, 1, size);
        return Result.ok(page == null || page.getList() == null ? new ArrayList<>() : page.getList());
    }

    /** 建单(员工确认 AI 草稿后由 consultation-service 触发;ai-service 人力客服转单亦复用)。 */
    @PostMapping
    public Result<Map<String, Object>> create(@RequestBody Map<String, Object> body) {
        CreateTicketRequest request = new CreateTicketRequest();
        request.setNature(text(body, "nature", "INCIDENT"));
        request.setCategoryId(text(body, "category", null));
        request.setTitle(text(body, "title", null));
        String description = text(body, "description", null);
        request.setDescription(description);
        // ticket-service 建单契约要求 impact/urgency 必填;草稿未提供时以描述兜底
        request.setImpactDescription(text(body, "impact_description", description));
        request.setUrgencyDescription(text(body, "urgency_description", description));
        request.setLocation(text(body, "location", null));
        request.setContact(text(body, "contact", null));
        request.setAssetId(text(body, "asset_id", null));
        request.setSourceSessionId(text(body, "source_session_id", null));
        request.setIdempotencyKey(text(body, "client_token", null));
        TicketService.CreateOutcome outcome = ticketService.create(UserContext.get(), request,
                request.getIdempotencyKey());
        return Result.ok(Map.of("ticket_id", outcome.ticketId()));
    }

    private static String text(Map<String, Object> body, String key, String fallback) {
        Object value = body == null ? null : body.get(key);
        return value == null || String.valueOf(value).isBlank() ? fallback : String.valueOf(value);
    }
}
