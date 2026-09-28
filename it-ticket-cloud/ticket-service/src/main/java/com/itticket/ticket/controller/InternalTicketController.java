package com.itticket.ticket.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.api.Result;
import com.itticket.common.user.UserInfo;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.CreateTicketRequest;
import com.itticket.ticket.dto.InternalCreateRequest;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.mapper.TicketMapper;
import com.itticket.ticket.service.TicketService;
import com.itticket.ticket.vo.SolvedTicketVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 内部工单接口,供 ai-service 调用(知识回流拉取已完成工单 / 人工客服转工单)。
 * 路径以 /api/internal 开头,网关不配置该路由 → 外部无法经网关触达。
 */
@RestController
@RequestMapping("/api/internal/tickets")
@RequiredArgsConstructor
public class InternalTicketController {

    private final TicketService ticketService;
    private final TicketMapper ticketMapper;
    private final TicketFlowLogMapper flowLogMapper;
    private final UserClient userClient;

    /**
     * 内部建单(人工客服把咨询会话转为工单)。
     * 复用 TicketService.create 的全部校验/幂等/通知逻辑,仅 creator 由调用方指定。
     */
    @PostMapping
    public Result<Map<String, Object>> createInternal(@RequestBody InternalCreateRequest request) {
        // 查询创建人信息,组装 TicketService.create 需要的 CurrentUser
        Result<UserInfo> userResult = userClient.getUser(request.getCreatorId());
        UserInfo creator = userResult == null ? null : userResult.getData();
        if (creator == null || !"active".equals(creator.getStatus())) {
            throw new BizException(ErrorCode.USER_INVALID);
        }

        CreateTicketRequest createRequest = new CreateTicketRequest();
        createRequest.setTitle(request.getTitle());
        createRequest.setCategory(request.getCategory());
        createRequest.setDescription(request.getDescription());
        createRequest.setPriority(request.getPriority());
        createRequest.setClientToken(request.getClientToken());

        UserContext.CurrentUser currentUser = new UserContext.CurrentUser(
                creator.getUserId(), creator.getName(), creator.getRole(), creator.getDepartment());
        TicketService.CreateOutcome outcome = ticketService.create(currentUser, createRequest);
        return Result.ok(outcome.duplicated() ? "重复提交(幂等)" : "创建成功",
                Map.of("ticket_id", outcome.ticketId()));
    }

    /**
     * 拉取已完成工单(知识回流数据源)。
     * @param since 可选,只返回 solved_at 晚于该时间的工单(ISO 格式,如 2026-09-24T00:00:00)
     */
    @GetMapping("/solved")
    public Result<List<SolvedTicketVO>> solved(@RequestParam(required = false) String since,
                                               @RequestParam(defaultValue = "100") int limit) {
        QueryWrapper<Ticket> query = new QueryWrapper<>();
        query.eq("status", TicketStatus.DONE.getValue());
        if (since != null && !since.isBlank()) {
            query.gt("solved_at", parseSince(since.trim()));
        }
        query.orderByAsc("solved_at").last("LIMIT " + Math.min(Math.max(limit, 1), 500));
        List<Ticket> tickets = ticketMapper.selectList(query);

        List<SolvedTicketVO> result = tickets.stream()
                .map(t -> new SolvedTicketVO(t.getTicketId(), t.getTitle(), t.getCategory(),
                        t.getDescription(), findSolutionRemark(t.getTicketId()), t.getSolvedAt()))
                .toList();
        return Result.ok(result);
    }

    /** since 参数兼容 ISO(2026-09-24T10:00:00)与展示格式(2026-09-24 10:00:00) */
    private static LocalDateTime parseSince(String since) {
        try {
            return LocalDateTime.parse(since);
        } catch (Exception e) {
            return LocalDateTime.parse(since,
                    java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        }
    }

    /** 取最后一条流转到「已完成」的处理记录备注,作为工程师的解决方案 */
    private String findSolutionRemark(String ticketId) {
        QueryWrapper<TicketFlowLog> query = new QueryWrapper<>();
        query.eq("ticket_id", ticketId)
                .eq("to_status", TicketStatus.DONE.getValue())
                .orderByDesc("log_id")
                .last("LIMIT 1");
        TicketFlowLog log = flowLogMapper.selectOne(query);
        return log == null ? null : log.getRemark();
    }
}
