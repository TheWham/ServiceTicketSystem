package com.itticket.ticket.controller;

import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.AcceptRequest;
import com.itticket.ticket.dto.ActionRequest;
import com.itticket.ticket.dto.AssignRequest;
import com.itticket.ticket.dto.CreateTicketRequest;
import com.itticket.ticket.dto.EditTicketRequest;
import com.itticket.ticket.dto.ContractEnvelope;
import com.itticket.ticket.dto.TicketProjection;
import com.itticket.ticket.dto.RatingRequest;
import com.itticket.ticket.dto.UpdateTicketRequest;
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
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** 工单全部对外接口 —— 路径与 /api/v1/tickets 完全一致 */
@RestController
@RequestMapping("/api/v1/tickets")
@RequiredArgsConstructor
public class TicketController {

    private final TicketService ticketService;

    @PostMapping
    public ResponseEntity<ContractEnvelope<TicketProjection>> create(
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @RequestHeader(value = "X-Request-Id", required = false) String requestId,
            @RequestBody CreateTicketRequest request) {
        TicketService.CreateOutcome outcome = ticketService.create(UserContext.get(), request, idempotencyKey);
        return ResponseEntity.status(outcome.duplicated() ? HttpStatus.OK : HttpStatus.CREATED)
                .body(ContractEnvelope.ok(requestId, outcome.duplicated() ? "Already created" : "Created",
                        TicketProjection.of(outcome.ticket())));
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
        return Result.ok(ticketService.list(UserContext.get(), status, category, assignee_id, creator_id, priority,
                unassigned, mine_or_pool, page, page_size));
    }

    @GetMapping("/{id}")
    public Result<Map<String, Object>> detail(@PathVariable String id) {
        return Result.ok(ticketService.get(UserContext.get(), id));
    }

    @PostMapping("/{id}/withdraw")
    public Result<Map<String, Object>> withdraw(@PathVariable String id) {
        return Result.ok("工单已撤回，记录已保留", ticketService.withdraw(UserContext.get(), id));
    }

    @PutMapping("/{id}/content")
    public Result<Void> edit(@PathVariable String id, @RequestBody EditTicketRequest request) {
        ticketService.edit(UserContext.get(), id, request);
        return Result.ok("修改已保存", null);
    }

    /** 提单人编辑工单并重新提交（新建/已分配可改内容；待补充提交后回到处理中） */
    @PutMapping("/{id}")
    public Result<Map<String, Object>> update(@PathVariable String id, @RequestBody UpdateTicketRequest request) {
        Map<String, Object> result = ticketService.update(UserContext.get(), id, request);
        boolean resubmitted = TicketStatus.IN_PROGRESS.getValue().equals(result.get("status"));
        return Result.ok(resubmitted ? "已重新提交，工单回到处理中" : "工单已更新", result);
    }

    @PostMapping("/{id}/assign")
    public Result<Map<String, Object>> assign(@PathVariable String id, @RequestBody AssignRequest request) {
        TicketService.AssignOutcome outcome = ticketService.assign(UserContext.get(), id, request);
        return Result.ok(outcome.reassign() ? "改派成功" : "派单成功",
                Map.of("ticket_id", outcome.ticketId(), "status", TicketStatus.ASSIGNED.getValue(),
                        "assignee_id", outcome.assigneeId()));
    }

    @PostMapping("/{id}/claim")
    public Result<Map<String, Object>> claim(@PathVariable String id, @RequestBody AcceptRequest request) {
        return Result.ok("接单成功", ticketService.claim(UserContext.get(), id, request));
    }

    @PostMapping("/{id}/actions")
    public Result<Map<String, Object>> action(@PathVariable String id, @RequestBody ActionRequest request) {
        return Result.ok("操作成功", ticketService.action(UserContext.get(), id, request));
    }
    /** 删除工单（PLATFORM_ADMIN 专属，物理删除不可恢复） */
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable("id") String id) {
        ticketService.delete(UserContext.get(), id);
        return Result.ok("工单已删除", null);
    }


    @PostMapping("/{id}/rating")
    public Result<Void> rating(@PathVariable String id, @RequestBody RatingRequest request) {
        ticketService.rate(id, request);
        return Result.ok("评价成功", null);
    }
}
