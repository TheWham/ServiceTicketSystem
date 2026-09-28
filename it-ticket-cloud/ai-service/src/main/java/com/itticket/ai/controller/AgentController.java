package com.itticket.ai.controller;

import com.itticket.ai.dto.RejectRequest;
import com.itticket.ai.dto.ToTicketRequest;
import com.itticket.ai.entity.ChatMessage;
import com.itticket.ai.entity.ChatSession;
import com.itticket.ai.service.ChatSessionService;
import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 人工客服工作台接口(角色:customer_service)。
 * 流程:队列 → 接入 → WebSocket 沟通 → 标记解决 / 转工单 / 驳回。
 */
@RestController
@RequestMapping("/api/v1/ai/agent")
@RequiredArgsConstructor
public class AgentController {

    private final ChatSessionService sessionService;

    /** 会话队列:全部待接入 + 我处理中的  PUSH4 */
    @GetMapping("/queue")
    public Result<List<ChatSession>> queue() {
        UserContext.CurrentUser user = checkAgent();
        return Result.ok(sessionService.agentQueue(user.getUserId()));
    }

    /** 接入会话(带原子更新防抢单) */
    @PostMapping("/sessions/{id}/accept")
    public Result<ChatSession> accept(@PathVariable Long id) {
        UserContext.CurrentUser user = checkAgent();
        return Result.ok("已接入", sessionService.accept(id, user.getUserId(), user.getName()));
    }

    /** 标记已解决(人工沟通后员工确认) */
    @PostMapping("/sessions/{id}/resolve")
    public Result<ChatSession> resolve(@PathVariable Long id) {
        UserContext.CurrentUser user = checkAgent();
        return Result.ok("已标记解决", sessionService.resolveByAgent(id, user.getUserId()));
    }

    /** 驳回(判定为重复/无效/已自行解决) */
    @PostMapping("/sessions/{id}/reject")
    public Result<ChatSession> reject(@PathVariable Long id, @RequestBody RejectRequest request) {
        UserContext.CurrentUser user = checkAgent();
        return Result.ok("已驳回", sessionService.reject(id, user.getUserId(), request.getReason()));
    }

    /** 转工单:调用 ticket-service 内部接口建单,员工侧可在「我的工单」查看 */
    @PostMapping("/sessions/{id}/to-ticket")
    public Result<ChatSession> toTicket(@PathVariable Long id, @RequestBody ToTicketRequest request) {
        UserContext.CurrentUser user = checkAgent();
        return Result.ok("已生成工单", sessionService.toTicket(id, user.getUserId(),
                request.getCategory(), request.getPriority(), request.getTitle(), request.getDescription()));
    }

    /** 会话消息记录(客服查看上下文) */
    @GetMapping("/sessions/{id}/messages")
    public Result<List<ChatMessage>> messages(@PathVariable Long id) {
        checkAgent();
        return Result.ok(sessionService.listMessages(id));
    }

    /** 角色守卫:仅人工客服 */
    private UserContext.CurrentUser checkAgent() {
        UserContext.CurrentUser user = UserContext.get();
        UserContext.checkRole(user, "customer_service");
        return user;
    }
}
