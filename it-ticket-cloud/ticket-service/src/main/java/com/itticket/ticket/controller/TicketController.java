package com.itticket.ticket.controller;

import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.ActionRequest;
import com.itticket.ticket.dto.AssignRequest;
import com.itticket.ticket.dto.CreateTicketRequest;
import com.itticket.ticket.dto.RatingRequest;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.service.TicketService;
import com.itticket.ticket.vo.TicketListVO;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** 工单全部对外接口 —— 路径与旧版 /api/v1/tickets 完全一致 */
@RestController
@RequestMapping("/api/v1/tickets")
@RequiredArgsConstructor
public class TicketController {

    private final TicketService ticketService;

    @PostMapping
    public ResponseEntity<Result<Map<String, Object>>> create(@RequestBody CreateTicketRequest request) {
        UserContext.CurrentUser user = UserContext.get();
        TicketService.CreateOutcome outcome = ticketService.create(user, request);
        if (outcome.duplicated()) {
            // 幂等命中:HTTP 200,与旧版一致
            return ResponseEntity.ok(Result.ok("重复提交(幂等)", Map.of("ticket_id", outcome.ticketId())));
        }
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(Result.ok("创建成功", Map.of(
                        "ticket_id", outcome.ticketId(),
                        "status", TicketStatus.PENDING.getValue(),
                        "title", outcome.title())));
    }

    @GetMapping
    public Result<TicketListVO> list(@RequestParam(required = false) String status,
                                     @RequestParam(required = false) String category,
                                     @RequestParam(required = false) String assignee_id,
                                     @RequestParam(required = false) String creator_id,
                                     @RequestParam(required = false) String priority,
                                     @RequestParam(required = false) String unassigned,
                                     @RequestParam(required = false) String mine_or_pool,
                                     @RequestParam(defaultValue = "1") int page,
                                     @RequestParam(defaultValue = "20") int page_size) {
        return Result.ok(ticketService.list(status, category, assignee_id, creator_id, priority,
                unassigned, mine_or_pool, page, page_size));
    }

    @GetMapping("/{id}")
    public Result<Map<String, Object>> detail(@PathVariable String id) {
        return Result.ok(ticketService.get(id));
    }

    @PostMapping("/{id}/assign")
    public Result<Map<String, Object>> assign(@PathVariable String id, @RequestBody AssignRequest request) {
        TicketService.AssignOutcome outcome = ticketService.assign(UserContext.get(), id, request);
        return Result.ok(outcome.reassign() ? "改派成功" : "派单成功",
                Map.of("ticket_id", outcome.ticketId(), "status", TicketStatus.PROCESSING.getValue(),
                        "assignee_id", outcome.assigneeId()));
    }

    @PostMapping("/{id}/claim")
    public Result<Map<String, Object>> claim(@PathVariable String id) {
        return Result.ok("领取成功", ticketService.claim(UserContext.get(), id));
    }

    @PostMapping("/{id}/actions")
    public Result<Map<String, Object>> action(@PathVariable String id, @RequestBody ActionRequest request) {
        return Result.ok("操作成功", ticketService.action(UserContext.get(), id, request));
    }

    @PostMapping("/{id}/rating")
    public Result<Void> rating(@PathVariable String id, @RequestBody RatingRequest request) {
        ticketService.rate(id, request);
        return Result.ok("评价成功", null);
    }
}
